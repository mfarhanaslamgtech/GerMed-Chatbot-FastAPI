"""
VisualSearchService — Async-first CLIP-based Image Search.

🎓 MIGRATION NOTES (Gervet → GerMed):
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
1. All I/O methods are now `async`:
   - Redis operations → `await`
   - OpenAI API → `await` (async client)
   - Image download → `httpx` (replaces `requests`)
   - Repository saves → `await` (async MongoDB)
   - Asset uploads → `await` (async UploadFile)
2. ThreadPoolExecutor removed — no need for background threads
   when everything is natively async.
3. `requests.get()` → `httpx.AsyncClient()` for image downloads.
4. `run_in_threadpool()` used for CPU-bound CLIP inference.
5. `model_dump()` replaces `dict()` (Pydantic v2).
"""
import numpy as np
import logging
import torch
import base64
import json
import re
import ast
import httpx
from io import BytesIO, IOBase
from PIL import Image
from typing import Union, List, Dict, Any, Optional, IO

from redis.commands.search.query import Query
from fastapi import UploadFile
from fastapi.concurrency import run_in_threadpool

from src.app.config.config import Config
from src.app.api.v1.repositories.chat_repository import ChatRepository
from src.app.api.v1.models.chat_model import (
    UserContent, AssistantContent, RoleEnum, ChatMessages
)

logger = logging.getLogger(__name__)


class VisualSearchService:
    """
    Service for visual search using CLIP image embeddings + Redis vector search.
    
    Pipeline:
    1. User uploads image (+optional question)
    2. CLIP generates image embedding
    3. Redis KNN finds similar product images
    4. OpenAI GPT-4o analyzes image + context
    5. Structured JSON response returned
    """

    def __init__(
        self,
        redis_client,
        processor,
        model,
        device: str,
        asset_uploader,
        repository: ChatRepository,
        openai_client  # Async OpenAI client
    ):
        self.redis = redis_client
        self.processor = processor
        self.model = model
        self.device = device
        self.asset_uploader = asset_uploader
        self.repository = repository
        self.openai_client = openai_client
        self.IMAGE_EMBEDDING_FIELD = "image_vector"
        self.SIMILARITY_THRESHOLD = 0.2
        self.TOP_K = 20
        self.CATALOG_REDIS_KEY = "gervet:catalogs"

    # ═══════════════════════════════════════════════════════════
    # MAIN ENTRY POINT
    # ═══════════════════════════════════════════════════════════

    async def answer_question(
        self,
        user_id: str,
        user_email: str,
        image_input: Optional[Union[UploadFile, bytes]],
        question: Optional[str]
    ) -> dict:
        """
        Process a visual query (image + optional question).
        
        Handles:
          ✅ New image + question
          ✅ New image only (auto-generates question)
          ✅ Follow-up question (loads previous image from Redis)
        """
        try:
            save_image = False
            save_question = False

            # ───────────────────────────────────────────
            # 1. Load image (new or from Redis)
            # ───────────────────────────────────────────
            if image_input:
                loaded_image = await self._load_image(image_input)

                if isinstance(image_input, UploadFile):
                    image_url = await self.asset_uploader.upload(image_input)
                else:
                    image_url = await self.asset_uploader.upload_bytes(
                        image_input, f"user_{user_id}.jpg"
                    )

                await self.redis.set(f"user:{user_id}:last_image_url", image_url)
                save_image = True
            else:
                # Follow-up question — load previous image
                image_url = await self.redis.get(f"user:{user_id}:last_image_url")
                if isinstance(image_url, bytes):
                    image_url = image_url.decode("utf-8")

                if not image_url:
                    return await self._handle_no_image_fallback(
                        user_id, user_email, question
                    )

                image_bytes = await self._download_image_from_url(image_url)
                loaded_image = await self._load_image(image_bytes)

            # ───────────────────────────────────────────
            # 2. Handle question
            # ───────────────────────────────────────────
            if not question or not question.strip():
                question = "I have sent you the image"
                save_question = False
            else:
                save_question = True

            # ───────────────────────────────────────────
            # 3. Retrieve visual context (CLIP + Redis KNN)
            # ───────────────────────────────────────────
            context = await self._retrieve_documents(loaded_image)

            if isinstance(context, dict) and "error" in context:
                logger.error(f"Context retrieval error: {context['error']}")
                context = []

            # ───────────────────────────────────────────
            # 4. PDF/Video/Catalog enrichment
            # ───────────────────────────────────────────
            has_pdf_request = self._detect_pdf_in_query(question)
            has_video_request = self._detect_video_in_query(question)
            catalog_url = await self._search_catalog_pdf(question)

            # ───────────────────────────────────────────
            # 5. Build prompt + call LLM
            # ───────────────────────────────────────────
            past_messages = await self.repository.get_clean_chat_history(user_email)
            history_str = self._format_chat_history(past_messages)
            prompt = self._generate_prompt(context, history_str, question)

            base64_image = await run_in_threadpool(
                self._image_to_base64, loaded_image
            )

            answer = await self._call_openai_api(base64_image, prompt)
            response = self.safe_parse_json(answer)

            # ───────────────────────────────────────────
            # 6. Post-process: PDF/Video enrichment
            # ───────────────────────────────────────────
            response = self._enrich_response(
                response, catalog_url, has_pdf_request, has_video_request
            )

            response_dict = {"message": response, "show_pagination": False}

            # ───────────────────────────────────────────
            # 7. Save conversation (async)
            # ───────────────────────────────────────────
            await self._save_conversation(
                user_id, user_email,
                question if save_question else None,
                image_url if save_image else None,
                response
            )

            return response_dict

        except Exception as e:
            logger.error(f"Failed to answer question: {str(e)}", exc_info=True)
            return {
                "message": {
                    "start_message": "Sorry, unable to process your question, please try again later",
                    "core_message": {"product": [], "options": ["Yes", "No"]},
                    "end_message": None,
                    "more_prompt": None
                },
                "show_pagination": False
            }

    # ═══════════════════════════════════════════════════════════
    # OPENAI VISION API
    # ═══════════════════════════════════════════════════════════

    async def _call_openai_api(self, base64_image: str, prompt: str) -> str:
        """Call OpenAI GPT-4o with image + text prompt (async)."""
        try:
            logger.debug("[Visual Search] Calling OpenAI API...")

            response = await self.openai_client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are a professional Veterinary Instrument Specialist for GerVetUSA. "
                            "Analyze the provided image and instrument database context to identify and explain products. "
                            "IMPORTANT: You MUST always respond in valid JSON format. "
                            "Ensure your response is helpful, accurate, and follows the requested JSON schema strictly."
                        )
                    },
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}
                        ]
                    }
                ],
                max_tokens=4096,
                response_format={"type": "json_object"}
            )

            response_content = response.choices[0].message.content
            if not response_content or response_content.strip() == "{}":
                finish_reason = response.choices[0].finish_reason if response.choices else "unknown"
                logger.warning(f"[Visual Search] OpenAI returned empty content. finish_reason: {finish_reason}")
                return "{}"

            return response_content

        except Exception as e:
            logger.error(f"OpenAI Vision API error: {str(e)}", exc_info=True)
            return '{"error": "Unable to analyze image. Please try again."}'

    # ═══════════════════════════════════════════════════════════
    # IMAGE PROCESSING
    # ═══════════════════════════════════════════════════════════

    async def _download_image_from_url(self, image_url: str) -> BytesIO:
        """Download image asynchronously using httpx."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(image_url)
            response.raise_for_status()
            return BytesIO(response.content)

    async def _load_image(
        self, image_input: Union[str, IO[bytes], Image.Image, UploadFile, bytes, BytesIO]
    ) -> Image.Image:
        """
        Load image from various input types.
        
        🎓 KEY CHANGE: UploadFile handling is now async-aware.
        """
        if isinstance(image_input, Image.Image):
            return image_input
        elif isinstance(image_input, UploadFile):
            await image_input.seek(0)
            content = await image_input.read()
            await image_input.seek(0)  # Reset for potential re-use
            return Image.open(BytesIO(content))
        elif isinstance(image_input, str):
            if image_input.startswith(("http://", "https://")):
                img_bytes = await self._download_image_from_url(image_input)
                return Image.open(img_bytes)
            return Image.open(image_input)
        elif isinstance(image_input, (BytesIO, IOBase)):
            image_input.seek(0)
            return Image.open(image_input)
        elif isinstance(image_input, bytes):
            return Image.open(BytesIO(image_input))
        else:
            raise ValueError(f"Invalid image input type: {type(image_input).__name__}")

    def _get_image_embedding(self, image: Image.Image) -> bytes:
        """Generate CLIP image embedding (CPU-bound, runs in threadpool)."""
        try:
            inputs = self.processor(images=image, return_tensors="pt", padding=True)
            inputs = {k: v.to(self.device) for k, v in inputs.items()}

            with torch.no_grad():
                embedding = self.model.get_image_features(**inputs)

            features = embedding.cpu().numpy().astype(np.float32).flatten()

            # L2 Normalization
            norm = np.linalg.norm(features)
            if norm > 0:
                features = features / norm

            return features.tobytes()
        except Exception as e:
            raise RuntimeError(f"Image embedding failed: {str(e)}")

    def _image_to_base64(self, image: Image.Image) -> str:
        """Convert PIL Image to base64 string."""
        try:
            if image.mode in ("RGBA", "LA", "P"):
                if image.mode == "P":
                    image = image.convert("RGBA")
                background = Image.new("RGB", image.size, (255, 255, 255))
                if image.mode == "RGBA":
                    background.paste(image, mask=image.split()[3])
                else:
                    background.paste(image)
                image = background
            elif image.mode != "RGB":
                image = image.convert("RGB")

            buffered = BytesIO()
            image.save(buffered, format="JPEG")
            return base64.b64encode(buffered.getvalue()).decode("utf-8")
        except Exception as e:
            logger.error(f"Failed to convert image to base64: {str(e)}")
            raise

    # ═══════════════════════════════════════════════════════════
    # REDIS VECTOR SEARCH
    # ═══════════════════════════════════════════════════════════

    async def _retrieve_documents(
        self, image_input: Union[str, IO[bytes], Image.Image, UploadFile]
    ) -> Union[List[Dict[str, Any]], Dict[str, str]]:
        """
        Run CLIP embedding + Redis KNN search for similar products.
        
        🎓 MIGRATION: CLIP inference is CPU-bound, so we run it in a threadpool.
        Redis search is sync (redis-py), so also runs in threadpool.
        """
        try:
            image = await self._load_image(image_input)
            # CPU-bound CLIP inference → threadpool
            query_vector = await run_in_threadpool(
                self._get_image_embedding, image
            )
        except Exception as e:
            logger.error(f"Image processing failed: {str(e)}")
            return {"error": f"Image processing failed: {str(e)}"}

        query = Query(
            f'*=>[KNN {self.TOP_K} @{self.IMAGE_EMBEDDING_FIELD} $vec_param AS vector_distance]'
        ).sort_by("vector_distance") \
         .paging(0, self.TOP_K) \
         .return_fields(
             "vector_distance", "product_name", "product_url", "image_url",
             "video_url", "pdf_url", "item_keywords", "sub_products",
             "categories", "short_description", "full_description", "sku"
         ) \
         .dialect(2)

        try:
            # Redis sync client → run in threadpool
            results = await run_in_threadpool(
                self.redis.ft().search, query,
                {"vec_param": query_vector}
            )
            logger.info(f"[Visual Search] Found {len(results.docs)} results from Redis KNN")

            similar_products = []
            for doc in results.docs:
                try:
                    vector_distance = float(getattr(doc, "vector_distance", 1.0))
                    similarity = 1 - vector_distance
                except:
                    similarity = 0.0

                product_name = getattr(doc, "product_name", "Unknown")

                if similarity < self.SIMILARITY_THRESHOLD:
                    logger.debug(
                        f"[Visual Search] Skipping '{product_name}' - "
                        f"similarity {similarity:.4f} below threshold {self.SIMILARITY_THRESHOLD}"
                    )
                    continue

                raw_image = getattr(doc, "image_url", None)
                image_url = self._extract_image_url(raw_image)

                raw_video = getattr(doc, "video_url", None)
                video_info = self._extract_video_info(raw_video)

                pdf_url = getattr(doc, "pdf_url", None)
                if pdf_url and isinstance(pdf_url, str):
                    pdf_url = pdf_url.strip() if pdf_url.strip() else None
                else:
                    pdf_url = None

                sub_products = self._parse_json_field(getattr(doc, "sub_products", []))
                categories = self._parse_json_field(getattr(doc, "categories", []))

                similar_products.append({
                    "name": product_name,
                    "url": getattr(doc, "product_url", None),
                    "image_url": image_url,
                    "video_url": video_info,
                    "pdf_url": pdf_url,
                    "description": getattr(doc, "short_description", None),
                    "full_description": getattr(doc, "full_description", None),
                    "product_variations": sub_products,
                    "categories": categories,
                    "sku": getattr(doc, "sku", None),
                    "similarity_score": round(similarity, 4)
                })

            return similar_products

        except Exception as e:
            logger.error(f"Redis search failed: {str(e)}", exc_info=True)
            return {"error": f"Redis search failed: {str(e)}"}

    # ═══════════════════════════════════════════════════════════
    # QUERY DETECTION HELPERS
    # ═══════════════════════════════════════════════════════════

    def _detect_pdf_in_query(self, query: str) -> bool:
        """Detect if user is asking for PDF or document links."""
        pdf_keywords = [
            "pdf", "document", "link", "url", "file",
            "brochure", "guide", "catalog", "catalogs"
        ]
        query_lower = query.lower()
        return any(keyword in query_lower for keyword in pdf_keywords)

    def _detect_video_in_query(self, query: str) -> bool:
        """Detect if user is asking for video/demo content."""
        video_keywords = [
            "video", "demo", "tutorial", "youtube", "vimeo",
            "visualization", "visual", "demonstration"
        ]
        query_lower = query.lower()
        return any(keyword in query_lower for keyword in video_keywords)

    async def _search_catalog_pdf(self, query: str) -> Optional[str]:
        """Search for a matching catalog PDF in Redis using fuzzy matching."""
        if not query or not isinstance(query, str):
            return None
        try:
            catalogs = await self.redis.hgetall(self.CATALOG_REDIS_KEY)
            if not catalogs:
                return None

            query_lower = query.lower()
            stop_words = {
                "can", "you", "please", "provide", "me", "the", "for",
                "with", "show", "tell", "about", "file", "download",
                "gervetusa", "of", "in", "is", "it", "to", "give",
                "want", "search", "find"
            }

            query_clean = re.sub(r"[^a-zA-Z0-9\s]", " ", query_lower)
            query_tokens = set(
                word for word in query_clean.split()
                if word not in stop_words and len(word) >= 2
            )
            if not query_tokens:
                return None

            best_match_url, best_match_score = None, 0
            for key_bytes, url_bytes in catalogs.items():
                key = key_bytes.decode("utf-8") if isinstance(key_bytes, bytes) else key_bytes
                url = url_bytes.decode("utf-8") if isinstance(url_bytes, bytes) else url_bytes

                key_clean = re.sub(r"[^a-zA-Z0-9\s]", " ", key.lower())
                if key_clean in query_clean:
                    return url

                key_tokens = set(word for word in key_clean.split() if len(word) >= 2)
                score = len(query_tokens.intersection(key_tokens)) / len(query_tokens)
                if score >= 0.5 and score > best_match_score:
                    best_match_score, best_match_url = score, url

            return best_match_url
        except Exception as e:
            logger.error(f"Error searching catalog PDF: {e}")
            return None

    # ═══════════════════════════════════════════════════════════
    # DATA EXTRACTION HELPERS
    # ═══════════════════════════════════════════════════════════

    @staticmethod
    def _parse_json_field(val: Any) -> Any:
        """Parse a field that might be a JSON string."""
        if isinstance(val, str):
            try:
                return json.loads(val)
            except:
                try:
                    return ast.literal_eval(val)
                except:
                    return val
        return val

    @staticmethod
    def _extract_image_url(val: Any) -> Optional[str]:
        """Extract a single string URL from potentially complex structures."""
        if not val:
            return None

        if isinstance(val, str) and val.strip().startswith(("[", "{")):
            try:
                val = ast.literal_eval(val)
            except:
                try:
                    val = json.loads(val)
                except:
                    pass

        if isinstance(val, list) and len(val) > 0:
            val = val[0]

        if isinstance(val, dict):
            return (
                val.get("medium") or val.get("large") or
                val.get("thumbnail") or val.get("image_url") or val.get("url")
            )

        if isinstance(val, str) and val.startswith("http"):
            return val

        return None

    @staticmethod
    def _extract_video_info(val: Any) -> Dict[str, Optional[str]]:
        """Extract YouTube and Vimeo URLs from potentially complex structures."""
        video_data = {"youtube": None, "vimeo": None}
        if not val:
            return video_data

        if isinstance(val, str) and val.strip().startswith(("[", "{")):
            try:
                val = ast.literal_eval(val)
            except:
                try:
                    val = json.loads(val)
                except:
                    pass

        videos = val if isinstance(val, list) else [val] if isinstance(val, dict) else []

        for v in videos:
            if not isinstance(v, dict):
                continue

            url = v.get("video_url") or v.get("url")
            source = str(v.get("video_source", "")).lower() or str(v.get("source", "")).lower()

            if not url:
                continue

            if "youtube" in source or "youtu.be" in url or "youtube.com" in url:
                video_data["youtube"] = url
            elif "vimeo" in source or "vimeo.com" in url:
                video_data["vimeo"] = url

        return video_data

    # ═══════════════════════════════════════════════════════════
    # CHAT HISTORY & PROMPT
    # ═══════════════════════════════════════════════════════════

    @staticmethod
    def _format_chat_history(messages: List) -> str:
        """Convert list of LangChain messages to a clean string for prompts."""
        formatted = []
        for m in messages:
            role = "User" if m.type == "human" else "Assistant"
            content = m.content
            if not isinstance(content, str):
                content = str(content)

            if role == "Assistant" and (content.startswith("{") or content.startswith("[")):
                try:
                    data = json.loads(content)
                    if isinstance(data, dict):
                        content = data.get("start_message", content)
                except:
                    pass

            formatted.append(f"{role}: {content}")
        return "\n".join(formatted)

    def _generate_prompt(
        self, context: List[Dict[str, Any]], chat_history: str, question: str
    ) -> str:
        """Generate a structured prompt for GPT-4o visual recognition."""
        if question == "I have sent you the image" or not question.strip():
            user_intent = "Identify the instrument in this image and provide its details from the provided context."
        else:
            user_intent = question

        qa_prompt_template = """
        Analyze the user's uploaded image and the provided instrument matches (CONTEXT). 
        
        -------------------------
        🛒 PRODUCTS IN CONTEXT (JSON):
        -------------------------
        {context_json}

        -------------------------
        💬 PREVIOUS CONVERSATION:
        -------------------------
        {chat_history}

        -------------------------
        👤 USER QUERY:
        -------------------------
        {user_intent}

        -------------------------
        🚀 WORKFLOW & INSTRUCTIONS:
        -------------------------
        1. Historical Independence: Focus ONLY on the CURRENT image. Ignore previous instruments discussed if they don't match this visual.
        2. Categorization: First, identify the core category (Scissors, Forceps, Needle Holder, Mallet, etc.).
        3. Identification Scenarios:
           - EXACT MATCH (Similarity >= 0.85): Use its details. Start with: "Yes, we certainly have this product!"
           - SIMILAR MATCH (Similarity < 0.85): Use visual reasoning. Start with: "Based on your image, here are the closest matches we have."
           - NON-VET: If not a surgical instrument, say: "No, we only offer veterinary products."
        4. Detail Validation: Verify features from the descriptions against the image.

        REQUIRED JSON SCHEMA:
        {{
            "start_message": "...",
            "core_message": {{
                "product": [{{ ... }}],
                "options": ["Yes", "No"]
            }},
            "end_message": "...",
            "more_prompt": "..."
        }}
        """

        return qa_prompt_template.format(
            context_json=json.dumps(context, ensure_ascii=False, indent=2),
            chat_history=chat_history or "No previous history.",
            user_intent=user_intent
        ).strip()

    # ═══════════════════════════════════════════════════════════
    # RESPONSE POST-PROCESSING
    # ═══════════════════════════════════════════════════════════

    def _enrich_response(
        self,
        response: dict,
        catalog_url: Optional[str],
        has_pdf_request: bool,
        has_video_request: bool
    ) -> dict:
        """Enrich response with PDF/Video links if detected in query."""
        if not response or not isinstance(response, dict):
            return response

        start_msg = response.get("start_message", "") or ""
        more_prompts = []

        existing_prompt = response.get("more_prompt")
        if existing_prompt and isinstance(existing_prompt, str):
            more_prompts.append(existing_prompt.replace("(YES/NO)", "").strip())

        # 📄 Handle PDF/Catalog links
        if catalog_url:
            core_products = response.get("core_message", {}).get("product", [])
            link_in_start = catalog_url in start_msg
            link_in_card = any(
                p.get("pdf_url") == catalog_url
                for p in core_products if isinstance(p, dict)
            )

            if has_pdf_request and not (link_in_start or link_in_card):
                pdf_line = f"Technical PDF: {catalog_url}"

                affirmations = [
                    "Yes, we certainly have this product!",
                    "Yes, we certainly have those available!",
                    "Yes, we have it!"
                ]
                inserted = False
                for aff in affirmations:
                    if aff in start_msg:
                        response["start_message"] = start_msg.replace(
                            aff, f"{aff} {pdf_line}\n"
                        )
                        inserted = True
                        break

                if not inserted:
                    response["start_message"] = f"{pdf_line}\n{start_msg}"

                start_msg = response["start_message"]

        # 🎥 Handle Video links
        if has_video_request:
            video_link = "https://www.gervetusa.com/pages/videos"
            if video_link not in start_msg and video_link not in str(more_prompts):
                more_prompts.append(f"Watch Videos: {video_link}")
            response["end_message"] = "Click any product to explore more details."

        # Join prompts
        if more_prompts:
            unique_prompts = list(dict.fromkeys(more_prompts))
            response["more_prompt"] = ". ".join(unique_prompts)
        else:
            response["more_prompt"] = None

        return response

    # ═══════════════════════════════════════════════════════════
    # CONVERSATION PERSISTENCE
    # ═══════════════════════════════════════════════════════════

    async def _save_conversation(
        self,
        user_id: str,
        user_email: str,
        question: Optional[str],
        image_url: Optional[str],
        response: dict
    ):
        """Save user + assistant messages (async, no threadpool needed)."""
        try:
            user_message = ChatMessages(
                user_id=user_id,
                user_email=user_email,
                role=RoleEnum.user,
                content=UserContent.create(text=question, image=image_url)
            )
            assistant_message = ChatMessages(
                user_id=user_id,
                user_email=user_email,
                role=RoleEnum.assistant,
                content=AssistantContent.create(answer=response)
            )
            await self.repository.save_bulk_messages(
                [user_message, assistant_message]
            )
        except Exception as e:
            logger.error(f"[Visual Search] Save conversation error: {e}")

    async def _handle_no_image_fallback(
        self, user_id: str, user_email: str, question: Optional[str]
    ) -> dict:
        """Return fallback when no image is found for a follow-up question."""
        fallback = "Please upload an image so I can assist you with your question."
        response_error = {
            "start_message": fallback,
            "core_message": {"product": [], "options": ["Yes", "No"]},
            "end_message": None,
            "more_prompt": None
        }

        await self._save_conversation(
            user_id, user_email,
            question if question else None,
            None,
            response_error
        )

        return {"message": response_error, "show_pagination": False}

    # ═══════════════════════════════════════════════════════════
    # JSON PARSING
    # ═══════════════════════════════════════════════════════════

    @staticmethod
    def safe_parse_json(raw_response: str) -> dict:
        """Safely parse JSON string and normalize the structure."""
        fallback_error = {
            "start_message": "I'm sorry, I encountered an issue while processing the product information.",
            "core_message": {"product": [], "options": ["Yes", "No"]},
            "end_message": None,
            "more_prompt": None
        }

        try:
            if isinstance(raw_response, dict):
                return raw_response
            if not raw_response or not isinstance(raw_response, str) or raw_response.strip() == "":
                return fallback_error

            cleaned = re.sub(
                r"^```(?:json)?|```$", "", raw_response.strip(), flags=re.MULTILINE
            ).strip()
            return json.loads(cleaned)
        except Exception as e:
            logger.error(f"JSON Parse Error: {e}")
            return fallback_error
