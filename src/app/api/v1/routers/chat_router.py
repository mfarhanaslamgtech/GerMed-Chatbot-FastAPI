from fastapi import APIRouter, Depends, UploadFile, File, Form
from typing import Optional
from dependency_injector.wiring import inject, Provide

from src.app.middlewares.auth_middleware import get_current_user
from src.app.containers.app_container import AppContainer
from src.app.api.v1.controllers.chat.chat_controller import ChatController

router = APIRouter()


@router.post("/chat")
@inject
async def chat(
    question: Optional[str] = Form(None),
    image: Optional[UploadFile] = File(None),
    token_data: dict = Depends(get_current_user),
    chat_controller: ChatController = Depends(Provide[AppContainer.chat_controller]),
):
    """
    Handle POST requests for chatbot queries (text or image).
    Returns query results based on the input type.
    
    🎓 MIGRATION NOTE:
    Original used `request: Request` to manually extract form data.
    FastAPI auto-extracts Form() and File() fields with type validation.
    """
    # chat_controller is now injected! No need to instantiate container.

    user_id = token_data.get("user_id")
    user_email = token_data.get("user_email")

    return await chat_controller.process_chat(
        user_id=user_id,
        user_email=user_email,
        question=question,
        image=image
    )
