from fastapi import APIRouter, Depends, Request
from dependency_injector.wiring import inject, Provide

from src.app.middlewares.auth_middleware import get_current_user, get_refresh_token_user
from src.app.containers.app_container import AppContainer
from src.app.api.v1.controllers.auth.auth_controller import AuthController
from src.app.api.v1.schemas.user_schema import UserLoginRequest, RefreshTokenRequest

router = APIRouter()


@router.post("/login")
@inject
async def login_endpoint(
    request: Request,
    login_request: UserLoginRequest,
    auth_controller: AuthController = Depends(Provide[AppContainer.auth_controller])
):
    """Login endpoint to generate tokens."""
    return await auth_controller.login(request, login_request)


@router.post("/refresh_token")
@inject
async def refresh(
    refresh_request: RefreshTokenRequest,
    token_data: dict = Depends(get_refresh_token_user),
    auth_controller: AuthController = Depends(Provide[AppContainer.auth_controller])
):
    """Refresh tokens endpoint."""
    return await auth_controller.refresh_token(token_data)


@router.post("/logout")
@inject
async def logout_user(
    token_data: dict = Depends(get_current_user),
    auth_controller: AuthController = Depends(Provide[AppContainer.auth_controller])
):
    """Logout endpoint to invalidate tokens."""
    return await auth_controller.logout(token_data)
