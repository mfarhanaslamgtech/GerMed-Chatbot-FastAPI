import logging
import json
from typing import Dict, Any, List
from src.app.api.v1.repositories.chat_repository import ChatRepository
from src.app.exceptions.custom_exceptions import APIException

class TextQueryHandler:
    """
    Orchestrates traditional text query processing:
    1. Fetches Chat History (Layer 3)
    2. Classifies Intent (Layer 5 - Classification Service)
    3. Routes to appropriate search service (Layer 5 - TextBot/FAQ Service)
    
    🎓 PRO TIP: We keep Orchestration in 'Handlers' to keep 'Services' pure 
    and focused on a single task (like RAG or Search).
    """

    def __init__(
        self,
        chat_repository: ChatRepository,
        classification_service: Any,  # To be injected
        text_search_service: Any,      # To be injected
        faqs_service: Any             # To be injected
    ):
        self.repository = chat_repository
        self.classification_service = classification_service
        self.text_search_service = text_search_service
        self.faqs_service = faqs_service

    async def handle_text_query(self, user_id: str, user_email: str, text_query: str) -> Dict[str, Any]:
        """
        Main entry point for text-based chat queries.
        """
        try:
            # 1. Fetch Chat History (Async)
            # We fetch cleaned LangChain messages for LLM context
            history = await self.repository.get_clean_chat_history(user_email, limit=5)
            logging.info(f"📜 History fetched for {user_email}: {len(history)} messages")

            # 2. Classify intent (Async - if service supports it)
            # 🎓 Note: In standard production code, we want our LLM calls to be awaited.
            label = await self.classification_service.classify_request(text_query, history)
            logging.info(f"🎯 Intent Classified: {label}")

            # 3. Route to specific Service
            if label == "text_product_search":
                result = await self.text_search_service.answer_question(
                    user_id, user_email, text_query, history
                )
                message = "Product search processed."
            
            elif label == "faqs_search":
                result = await self.faqs_service.answer_question(
                    user_id, user_email, text_query, history
                )
                message = "FAQ answered."
                
            else:
                # Default fallback or error
                logging.warning(f"⚠️ Unhandled classification label: {label}")
                raise APIException(f"Sorry, I couldn't understand the request type: {label}", status_code=400)

            # 4. Standardized Return
            return {
                "message": message,
                "data": result,
                "show_pagination": result.get("show_pagination", False) if isinstance(result, dict) else False
            }

        except Exception as e:
            logging.error(f"❌ TextQueryHandler failed: {str(e)}", exc_info=True)
            if isinstance(e, APIException):
                raise e
            raise APIException("An error occurred during query processing", status_code=500)
