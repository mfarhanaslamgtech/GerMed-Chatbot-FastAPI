"""
TwilioController — Async Twilio Call Handler.

🎓 MIGRATION NOTES (Gervet → GerMed):
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
1. Flask-RESTful `Resource` → plain class with async method
2. `flask.request.form` → receives validated dict from router
3. `flask_jwt_extended` → JWT payload injected by router
4. `@inject` → constructor DI via AppContainer
5. `TwilioCallService` (missing) → uses existing `AudioCallService`
6. `audio_text_validator` still used for form data validation
7. Response uses `success_response` pattern → direct dict return

Original route: POST /v1/agent/twilio-call
"""
import logging
from typing import Dict, Any

from src.app.api.v1.services.audio_call.audio_call_service import AudioCallService
from src.app.api.v1.validators.audio_text_validator import audio_text_validator
from src.app.exceptions.custom_exceptions import APIException

logger = logging.getLogger(__name__)


class TwilioController:
    """
    Controller for handling Twilio voice call queries.
    
    Receives audio-transcribed text, validates it, queries the AudioCallService,
    and returns a speech-friendly response.
    """

    def __init__(self, audio_call_service: AudioCallService):
        self.audio_call_service = audio_call_service

    async def handle_twilio_call(
        self,
        user_id: str,
        user_email: str,
        form_data: Dict[str, Any],
        history: list = None
    ) -> Dict[str, Any]:
        """
        Process a Twilio call query.

        Args:
            user_id: User's unique identifier (from JWT)
            user_email: User's email (from JWT)
            form_data: Dict containing 'question' field
            history: Optional chat history for context

        Returns:
            Dict with answer key containing speech-friendly text
        """
        try:
            # 1. Validate input (reuses existing validator)
            validated_data = audio_text_validator(form_data)
            text_query = validated_data["text_query"]

            # 2. Call AudioCallService (async)
            answer = await self.audio_call_service.answer_question(
                user_id=user_id,
                user_email=user_email,
                question=text_query,
                history=history or []
            )

            return {
                "message": "Audio call processed successfully",
                "data": {"answer": answer}
            }

        except APIException:
            raise
        except Exception as e:
            logger.error(f"❌ TwilioController Error: {e}", exc_info=True)
            raise APIException("Internal server error during Twilio call processing", status_code=500)
