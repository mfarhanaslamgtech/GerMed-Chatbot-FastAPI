import json
import logging
import re
import uuid
import time
import difflib
import numpy as np
from typing import List, Dict, Any, Optional, Union
from redis.commands.search.query import Query

from langchain_openai import ChatOpenAI
from langchain_core.messages import BaseMessage

from src.app.api.v1.repositories.chat_repository import ChatRepository
from src.app.api.v1.models.chat_model import ChatMessages, RoleEnum, UserContent, AssistantContent
from src.app.exceptions.custom_exceptions import APIException

class TextSearchService:
    """
    Asynchronous Product Search Service using RediSearch (Vector & Text).
    Handles Broader, Category, and Exact product matches.
    """

    # Redis Index Field Names (should match what's in text_embedding.py / Redis)
    ITEM_KEYWORD_EMBEDDING_FIELD = "item_keyword_vector"
    CATEGORY_NAME_EMBEDDING_FIELD = "category_name_vector"
    INDEX_NAME = "idx"
    
    SIMILARITY_THRESHOLD = 0.65
    EXACT_MAX_RESULTS = 10
    CATEGORY_MAX_RESULTS = 20
    BROADER_MAX_RESULTS = 15
    STATE_TTL_SECONDS = 1800 # 30 mins

    def __init__(
        self,
        redis_client: Any, 
        embedding_model: Any,
        openai_llm: ChatOpenAI,
        chat_repository: ChatRepository
    ):
        self.redis = redis_client
        self.model = embedding_model
        self.llm = openai_llm
        self.repository = chat_repository

    async def answer_question(
        self, 
        user_id: str, 
        user_email: str, 
        question: str, 
        history: List[BaseMessage]
    ) -> Dict[str, Any]:
        """
        Main entry point for Product Search.
        """
        try:
            logging.info(f"🔎 Product Search: '{question}' for {user_email}")

            # 1. Intent & Context Discovery
            # For Phase 4, we use a simplified discovery logic. 
            # In Phase 9, this would call LLM to refine the search.
            search_results = await self._discover_context(question)
            
            # 2. Generate Response (Placeholder for Phase 4)
            # In Phase 9, we will use individual prompt templates for Broader/Category/Exact
            answer = {
                "start_message": f"I found some products related to '{question}'.",
                "core_message": {
                    "product": search_results["products"],
                    "categories": search_results["categories"]
                },
                "end_message": "Click any product to explore more details.",
                "more_prompt": None
            }

            # 3. Save Conversation
            await self._save_chat(user_id, user_email, question, answer)

            return {
                "message": "Product search processed.",
                "data": answer,
                "show_pagination": len(search_results["products"]) > 5
            }

        except Exception as e:
            logging.error(f"❌ TextSearchService Error: {e}", exc_info=True)
            return self._fallback_response(question)

    async def _discover_context(self, question: str) -> Dict[str, Any]:
        """Parallel discovery of products and categories, prioritizing SKU matches."""
        # 1. Check if query is likely a SKU
        sku_matches = []
        clean_q = question.strip().upper()
        
        # Simple SKU regex or check (G46-765, etc.)
        is_sku = self._is_sku_pattern(clean_q)
        if is_sku:
            sku_matches = await self._retrieve_by_sku(clean_q)
            if sku_matches:
                logging.info(f"✅ Exact SKU match found for {clean_q}")

        # 2. Parallel discovery for others
        category_matches = await self._retrieve_categories(question)
        
        # If we have SKU matches, we skip vector search to avoid 'irrelevant' noise
        # unless search results are too few.
        if sku_matches:
            final_products = sku_matches
            logging.info(f"🎯 SKU search prioritized. Skipping vector search to reduce noise.")
        else:
            # Fallback to semantic vector search
            logging.info(f"🔍 No SKU match found. Falling back to vector search.")
            final_products = await self._retrieve_exact(question)
        
        return {
            "products": final_products,
            "categories": category_matches
        }

    def _is_sku_pattern(self, query: str) -> bool:
        """Heuristic to detect if query is an instrument SKU."""
        # GerVet/GerMed SKUs often look like G12-345, GD50-1234, etc.
        return bool(re.search(r'[A-Z]+\d*-\d+', query)) or len(query.split('-')) > 1

    async def _retrieve_by_sku(self, sku: str) -> List[Dict[str, Any]]:
        """
        Refined retrieval for exact SKU using Filtered KNN for dynamic scoring.
        """
        try:
            logging.info(f"🔎 [SKU Match] Attempting exact lookup for: '{sku}'")
            
            # Generate query vector to get real vector scores even for SKU matches
            query_vector = self.model.encode(sku).astype(np.float32).tobytes()
            sanitized_sku = sku.replace("-", "\\-")

            # Redis Filtered KNN: restricted to SKU matching records but returns dynamic score
            # We check both the main SKU and the variations tag
            filter_str = f"(@sku:{{{sanitized_sku}}} | @sub_products:{{*{sanitized_sku}*}})"
            q_str = f"{filter_str}=>[KNN 10 @{self.ITEM_KEYWORD_EMBEDDING_FIELD} $vec AS score]"
            
            q = (
                Query(q_str)
                .sort_by("score")
                .return_fields(
                    "product_name", "product_url", "product_image", "sku", 
                    "pdf_link", "sub_products", "short_description", 
                    "full_description", "video_url", "score"
                )
                .dialect(2)
            )
            
            res = await self.redis.ft(self.INDEX_NAME).search(q, query_params={"vec": query_vector})
            
            if res.total > 0:
                logging.info(f"✅ [SKU Match] Found {res.total} matches.")
                return self._process_docs(res.docs, is_vector=False, query_sku=sku)

            logging.info(f"❌ [SKU Match] No exact SKU records found for: '{sku}'")
            return []
        except Exception as e:
            logging.warning(f"⚠️ [SKU Match] Error during SKU search: {e}")
            return []

    def _merge_results(self, priority: List[Dict], regular: List[Dict]) -> List[Dict]:
        """Merge matches, removing duplicates by URL."""
        seen = set()
        merged = []
        for item in priority + regular:
            url = item.get("url")
            if url and url not in seen:
                seen.add(url)
                merged.append(item)
        return merged

    def _process_docs(self, docs: List[Any], is_vector: bool = True, query_sku: str = None) -> List[Dict[str, Any]]:
        """Common logic to convert Redis docs to product dictionaries with SKU Promotion."""
        products = []
        for doc in docs:
            score = 1.0
            if is_vector:
                try: score = 1 - float(getattr(doc, "score", 0.0))
                except: score = 0.0
                if score < self.SIMILARITY_THRESHOLD and not query_sku: continue
            
            # --- PRODUCT PROMOTION & ALGORITHMIC SCORING ---
            p_name = getattr(doc, "product_name", "Unknown")
            p_url = getattr(doc, "product_url", "#")
            p_image = getattr(doc, "product_image", None)
            p_sku = getattr(doc, "sku", None)
            
            sub_products = getattr(doc, "sub_products", "[]")
            if isinstance(sub_products, str):
                try: sub_products = json.loads(sub_products)
                except: sub_products = []

            # If searching by SKU, calculate an algorithmic similarity score
            if query_sku:
                target = query_sku.strip().upper()
                # 1. Check parent SKU similarity
                parent_sku_val = str(p_sku or "").strip().upper()
                score = difflib.SequenceMatcher(None, target, parent_sku_val).ratio()
                
                # 2. Check variation SKU similarity and Promote if better
                for sub in sub_products:
                    s_sku = str(sub.get("sku", "")).strip().upper()
                    # Calculate granular similarity for this variation
                    variation_score = difflib.SequenceMatcher(None, target, s_sku).ratio()
                    
                    if variation_score > score:
                        score = variation_score
                    
                    # Promotion logic: 
                    # 1. EXACT match -> Score 1.0
                    if s_sku == target:
                        logging.info(f"⭐ [Exact] Promoting sub-product details for SKU '{target}'")
                        p_name = sub.get("name") or p_name
                        p_sku = s_sku
                        score = 1.0 
                        break
                    
                    # 2. PREFIX Match (Partial SKU) -> Score 0.95
                    # Ensuring target has enough substance to avoid false positives (e.g. just "G")
                    elif len(target) >= 3 and s_sku.startswith(target):
                        # Only promote if we haven't found a better match yet (like an exact one)
                        if score < 0.95:
                            logging.info(f"⭐ [Prefix] Promoting sub-product details for Partial SKU '{target}' matched with '{s_sku}'")
                            p_name = sub.get("name") or p_name
                            p_sku = s_sku
                            score = 0.95
                        # Don't break immediately, in case a full exact match exists later in the list
            
            raw_video = getattr(doc, "video_url", "[]")
            video_info = self._extract_video_info(raw_video)

            products.append({
                "name": p_name,
                "url": p_url,
                "image_url": p_image,
                "pdf_url": getattr(doc, "pdf_link", None),
                "video_url": video_info,
                "description": getattr(doc, "short_description", None),
                "full_description": getattr(doc, "full_description", None),
                "sku": p_sku,
                "product_variations": sub_products,
                "similarity_score": round(score, 4)
            })
        return products

    def _extract_video_info(self, video_data: Any) -> Dict[str, Optional[str]]:
        """Parse video JSON into YouTube/Vimeo format."""
        info = {"youtube": None, "vimeo": None}
        if not video_data: return info
        
        try:
            videos = video_data
            if isinstance(video_data, str):
                videos = json.loads(video_data)
            
            if not isinstance(videos, list): return info

            for v in videos:
                url = v.get("video_url", "")
                if "youtube.com" in url or "youtu.be" in url:
                    info["youtube"] = url
                elif "vimeo.com" in url:
                    info["vimeo"] = url
        except: pass
        return info

    async def _retrieve_exact(self, query: str) -> List[Dict[str, Any]]:
        """Vector search for exact products."""
        try:
            # Generate Embedding
            query_vector = self.model.encode(query).astype(np.float32).tobytes()
            
            # RediSearch KNN Query
            q = (
                Query(f"*=>[KNN {self.EXACT_MAX_RESULTS} @{self.ITEM_KEYWORD_EMBEDDING_FIELD} $vec AS score]")
                .sort_by("score")
                .return_fields(
                    "product_name", "product_url", "product_image", "sku", 
                    "pdf_link", "sub_products", "short_description", 
                    "full_description", "video_url", "score"
                )
                .dialect(2)
            )
            
            # Execute Search
            res = await self.redis.ft(self.INDEX_NAME).search(q, query_params={"vec": query_vector})
            
            return self._process_docs(res.docs, is_vector=True)
        except Exception as e:
            logging.warning(f"⚠️ Redis Exact Search failed: {e}")
            return []

    async def _retrieve_categories(self, query: str) -> List[Dict[str, Any]]:
        """Vector search for broader categories."""
        try:
            query_vector = self.model.encode(query).astype(np.float32).tobytes()
            q = (
                Query(f"*=>[KNN {self.BROADER_MAX_RESULTS} @{self.CATEGORY_NAME_EMBEDDING_FIELD} $vec AS score]")
                .sort_by("score")
                .return_fields("category_names", "categories", "score")
                .dialect(2)
            )
            
            res = await self.redis.ft(self.INDEX_NAME).search(q, query_params={"vec": query_vector})
            
            categories = []
            seen = set()
            for doc in res.docs:
                score = 1 - float(doc.score)
                if score < self.SIMILARITY_THRESHOLD:
                    continue
                
                # Handle potentially multiple categories per doc
                cat_names = self._parse_redis_list(getattr(doc, "category_names", "[]"))
                cat_urls = self._parse_redis_list(getattr(doc, "categories", "[]"))
                
                for name, url in zip(cat_names, cat_urls):
                    if url not in seen:
                        seen.add(url)
                        categories.append({
                            "name": name,
                            "url": url,
                            "data-prompt": f"Show me {name}"
                        })
            return categories
        except Exception as e:
            logging.warning(f"⚠️ Redis Category Search failed: {e}")
            return []

    def _parse_redis_list(self, val: str) -> List[str]:
        if not val: return []
        try:
            if val.startswith("["): return json.loads(val)
            return [val]
        except: return [val]

    async def _save_chat(self, user_id: str, user_email: str, question: str, answer: Dict[str, Any]):
        try:
            messages = [
                ChatMessages(
                    user_id=user_id, user_email=user_email, role=RoleEnum.user,
                    content=UserContent.create(text=question)
                ),
                ChatMessages(
                    user_id=user_id, user_email=user_email, role=RoleEnum.assistant,
                    content=AssistantContent.create(answer=answer)
                )
            ]
            await self.repository.save_bulk_messages(messages)
        except Exception as e:
            logging.error(f"Failed to save search chat: {e}")

    def _fallback_response(self, question: str) -> Dict[str, Any]:
        return {
            "message": "I'm having trouble searching right now.",
            "data": {
                "start_message": f"I couldn't find exact matches for '{question}' right now.",
                "core_message": {"product": [], "categories": []},
                "end_message": "Please try a different term or visit GerVetUSA.com",
            },
            "show_pagination": False
        }
