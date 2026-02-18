import logging
from uuid import uuid4

from fastapi import Request
from starlette.responses import JSONResponse

from src.app.api.v1.services.auth.auth_service import AuthService
from src.app.api.v1.schemas.user_schema import UserLoginRequest
from src.app.exceptions.custom_exceptions import APIException, MissingFieldException

logger = logging.getLogger(__name__)


class AuthController:
    """
    Async Auth Controller — handles login, refresh, and logout.
    
    🎓 KEY MIGRATION CHANGE:
    Original Gervet project used free functions with @inject decorators.
    Now we use a class that receives AuthService via DI container.
    This makes it testable and decoupled from the container.
    """

    def __init__(self, auth_service: AuthService):
        self.auth_service = auth_service

    async def login(self, request: Request, login_request: UserLoginRequest):
        """Handle user login/session initialization."""
        try:
            email = login_request.email
            validated_data = {"email": str(email)}
            ip_address = request.client.host if request.client else "127.0.0.1"

            user = await self.auth_service.get_or_create_user(validated_data, ip_address)

            session_id = str(uuid4())
            access_token, refresh_token = await self.auth_service.generate_tokens(user, session_id)

            response = JSONResponse(content={
                "access_token": access_token,
                "refresh_token": refresh_token,
                "user": {
                    "user_id": user.user_id,
                    "user_email": user.user_email,
                    "region": user.region
                }
            })

            # Set cookies for easier testing/frontend use
            response.set_cookie(
                key="access_token", 
                value=access_token, 
                httponly=True, 
                max_age=int(self.auth_service.access_expiry.total_seconds()),
                samesite="lax"
            )
            response.set_cookie(
                key="refresh_token", 
                value=refresh_token, 
                httponly=True, 
                max_age=int(self.auth_service.refresh_expiry.total_seconds()),
                samesite="lax"
            )

            return response

        except APIException:
            raise
        except Exception as e:
            logger.error(f"Login failed: {str(e)}", exc_info=True)
            raise APIException("Internal server error during login", status_code=500)

    async def refresh_token(self, token_data: dict):
        """Handle token refresh."""
        try:
            session_id = token_data.get("sub") or token_data.get("session_id")
            if not session_id:
                raise APIException("Invalid token payload: session_id missing", status_code=401)

            access_token, refresh_token = await self.auth_service.refresh(session_id, token_data)

            response = JSONResponse(content={
                "access_token": access_token,
                "refresh_token": refresh_token
            })

            # Update cookies
            response.set_cookie(
                key="access_token", 
                value=access_token, 
                httponly=True, 
                max_age=int(self.auth_service.access_expiry.total_seconds()),
                samesite="lax"
            )
            response.set_cookie(
                key="refresh_token", 
                value=refresh_token, 
                httponly=True, 
                max_age=int(self.auth_service.refresh_expiry.total_seconds()),
                samesite="lax"
            )

            return response

        except APIException:
            raise
        except Exception as e:
            logger.error(f"Token refresh failed: {str(e)}", exc_info=True)
            raise APIException("Internal server error during token refresh", status_code=500)

    async def logout(self, token_data: dict):
        """Handle user logout."""
        try:
            session_id = token_data.get("sub") or token_data.get("session_id")
            user_id = token_data.get("user_id")

            if not session_id or not user_id:
                raise APIException("Invalid token payload", status_code=401)

            await self.auth_service.logout(session_id, user_id)

            response = JSONResponse(content={"message": "Logged out successfully"})
            response.delete_cookie("access_token")
            response.delete_cookie("refresh_token")
            
            return response

        except APIException:
            raise
        except Exception as e:
            logger.error(f"Logout failed: {str(e)}", exc_info=True)
            raise APIException("Internal server error during logout", status_code=500)
