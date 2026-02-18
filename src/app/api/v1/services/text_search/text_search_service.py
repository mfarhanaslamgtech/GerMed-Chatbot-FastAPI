import json
import logging
import re
import uuid
import time
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
                    "product": search_results["products"][:5],
                    "categories": search_results["categories"][:5]
                },
                "end_message": "Would you like to see more details on any of these?",
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
        """Parallel discovery of products and categories."""
        # 🎓 PRO TIP: In a real high-scale app, we'd run these in asyncio.gather
        exact_matches = await self._retrieve_exact(question)
        category_matches = await self._retrieve_categories(question)
        
        return {
            "products": exact_matches,
            "categories": category_matches
        }

    async def _retrieve_exact(self, query: str) -> List[Dict[str, Any]]:
        """Vector search for exact products."""
        try:
            # Generate Embedding
            query_vector = self.model.encode(query).astype(np.float32).tobytes()
            
            # RediSearch KNN Query
            q = (
                Query(f"*=>[KNN {self.EXACT_MAX_RESULTS} @{self.ITEM_KEYWORD_EMBEDDING_FIELD} $vec AS score]")
                .sort_by("score")
                .return_fields("item_name", "product_name", "product_url", "product_image", "sku", "score")
                .dialect(2)
            )
            
            # Execute Search
            # IMPORTANT: redis-py's ft().search is now awaitable in async mode
            res = await self.redis.ft().search(q, query_params={"vec": query_vector})
            
            products = []
            for doc in res.docs:
                score = 1 - float(doc.score)
                if score < self.SIMILARITY_THRESHOLD:
                    continue
                
                products.append({
                    "name": getattr(doc, "product_name", getattr(doc, "item_name", "Unknown")),
                    "url": getattr(doc, "product_url", "#"),
                    "image_url": getattr(doc, "product_image", None),
                    "sku": getattr(doc, "sku", None)
                })
            return products
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
            
            res = await self.redis.ft().search(q, query_params={"vec": query_vector})
            
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
