"""
ImageQueryHandler — Routes image-based chat queries to VisualSearchService.

🎓 MIGRATION NOTES:
- Original was sync, now fully async.
- Image validation uses our async validator.
- VisualSearchService.answer_question is now async.
"""
import logging
from typing import Optional, Any, Dict

from fastapi import UploadFile

from src.app.api.v1.services.visual_search.visual_search_service import VisualSearchService
from src.app.api.v1.validators.image_validator import validate_image_upload

logger = logging.getLogger(__name__)


class ImageQueryHandler:
    """
    Handles image-based queries by delegating to VisualSearchService.
    
    Supports:
      ✅ Image only (question auto-generated)
      ✅ Image + question
      ✅ Text-only follow-up on previous image
    """

    def __init__(self, visual_search_service: VisualSearchService):
        self.visual_search_service = visual_search_service

    async def handle(
        self,
        user_id: str,
        user_email: str,
        image_query: Optional[UploadFile] = None,
        question: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Process an image-based query.
        
        Args:
            user_id: User's unique identifier
            user_email: User's email
            image_query: Optional uploaded image file
            question: Optional text question
            
        Returns:
            Dict with message and data keys
        """
        # Validate image if provided
        if image_query:
            validate_image_upload(image_query)

        # Delegate to visual search service (fully async)
        result = await self.visual_search_service.answer_question(
            user_id=user_id,
            user_email=user_email,
            image_input=image_query,
            question=question
        )

        return {
            "message": "Query processed successfully",
            "data": result
        }
