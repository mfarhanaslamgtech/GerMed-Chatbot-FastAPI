import logging
from typing import Optional, Any
from fastapi import UploadFile
from src.app.api.v1.controllers.chat.text_query_handler import TextQueryHandler
from src.app.api.v1.controllers.chat.image_query_handler import ImageQueryHandler
from src.app.exceptions.custom_exceptions import APIException

class ChatController:
    """
    Primary Controller for all Chat-related operations.
    Orchestrates between Text and Image query handlers.
    
    🎓 PRO TIP: Using a central Controller class makes unit testing 
    much easier because we can mock the entire handler layer in one go.
    """

    def __init__(
        self,
        text_handler: TextQueryHandler,
        image_handler: Optional[ImageQueryHandler] = None
    ):
        self.text_handler = text_handler
        self.image_handler = image_handler

    async def process_chat(
        self,
        user_id: str,
        user_email: str,
        question: Optional[str] = None,
        image: Optional[UploadFile] = None
    ):
        """
        Routes the request to the correct sub-handler based on input type.
        """
        try:
            # 1. Image + Text or just Image query
            if image:
                if not self.image_handler:
                    logging.warning("⚠️ Visual search handler not yet initialized.")
                    raise APIException("Visual search is currently unavailable.", status_code=503)
                
                return await self.image_handler.handle(
                    user_id=user_id,
                    user_email=user_email,
                    image_query=image,
                    question=question
                )

            # 2. Pure Text query
            if question:
                return await self.text_handler.handle_text_query(
                    user_id, user_email, question
                )

            # 3. Validation fallback
            raise APIException("Please provide either a question or an image.", status_code=400)

        except APIException:
            raise
        except Exception as e:
            logging.error(f"❌ ChatController Error: {e}")
            raise APIException("Internal server error during chat processing", status_code=500)

