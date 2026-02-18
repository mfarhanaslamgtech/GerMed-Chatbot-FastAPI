from fastapi import APIRouter, Depends, Form
from src.app.middlewares.auth_middleware import get_current_user
from src.app.containers.app_container import AppContainer

router = APIRouter()


@router.post("/audio-call")
async def audio_call(
    text_query: str = Form(...),
    token_data: dict = Depends(get_current_user)
):
    """
    Handle POST requests for audio chatbot queries.
    Returns a speech-friendly text response (no markdown/JSON).
    """
    container = AppContainer()
    audio_service = container.audio_call_service()

    user_id = token_data.get("user_id")
    user_email = token_data.get("user_email")

    # Fetch chat history for context
    chat_repository = container.chat_repository()
    history = await chat_repository.get_clean_chat_history(user_email, limit=3)

    answer = await audio_service.answer_question(
        user_id=user_id,
        user_email=user_email,
        question=text_query,
        history=history
    )

    return {"answer": answer}
