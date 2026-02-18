"""
Twilio Call Router — POST /v1/agent/twilio-call

🎓 MIGRATION NOTES:
- Flask Blueprint → FastAPI APIRouter
- @jwt_required() → Depends(get_current_user)
- request.form.to_dict() → Form(...) parameters
- Flask-RESTful Resource.post() → @router.post() async function
"""
from fastapi import APIRouter, Depends, Form
from src.app.middlewares.auth_middleware import get_current_user
from src.app.containers.app_container import AppContainer

router = APIRouter()


@router.post("/twilio-call")
async def twilio_call(
    question: str = Form(..., description="Transcribed audio text from Twilio"),
    token_data: dict = Depends(get_current_user)
):
    """
    Handle POST requests for Twilio voice call queries.
    
    Receives transcribed audio text, validates it, and returns
    a speech-friendly text response (no markdown/JSON).
    
    🎓 COMPARISON:
    Flask:   TwilioCallResource(Resource).post() + @jwt_required()
    FastAPI: @router.post() + Depends(get_current_user)
    """
    container = AppContainer()
    
    # Build controller with DI
    from src.app.api.v1.controllers.twilio.twilio_controller import TwilioController
    audio_service = container.audio_call_service()
    controller = TwilioController(audio_call_service=audio_service)

    user_id = token_data.get("user_id")
    user_email = token_data.get("user_email")

    # Fetch chat history for context
    chat_repository = container.chat_repository()
    history = await chat_repository.get_clean_chat_history(user_email, limit=3)

    return await controller.handle_twilio_call(
        user_id=user_id,
        user_email=user_email,
        form_data={"question": question},
        history=history
    )
