import logging
from datetime import datetime, timedelta, timezone
from uuid import uuid4
from typing import Tuple, Optional, Dict, Any

from jose import jwt

from src.app.config.config import Config
from src.app.exceptions.custom_exceptions import (
    APIException,
    TokenGenerationException,
    TokenStorageException,
    InvalidTokenException,
)
from src.app.api.v1.models.user_model import UserDB, UserOut
from src.app.api.v1.repositories.token_repository import TokenRepository
from src.app.api.v1.repositories.user_repository import UserRepository
from src.app.api.v1.services.geo.geo_service import GeoService


class AuthService:
    """
    Async Authentication service for handling user sessions and JWT tokens.
    
    🎓 KEY MIGRATION CHANGES:
    - All DB/Redis calls are now awaited (async)
    - Uses timezone-aware UTC (no deprecated datetime.utcnow())
    - GeoService is now async (httpx instead of requests)
    """
    
    ALGORITHM = "HS256"
    
    def __init__(
        self,
        token_repository: TokenRepository,
        user_repository: UserRepository,
        geo_service: GeoService
    ):
        self.token_repository = token_repository
        self.user_repository = user_repository
        self.geo_service = geo_service
        self.access_expiry = timedelta(**{Config.ACCESS_TOKEN_EXPIRY_UNIT: Config.ACCESS_TOKEN_EXPIRY_VALUE})
        self.refresh_expiry = timedelta(**{Config.REFRESH_TOKEN_EXPIRY_UNIT: Config.REFRESH_TOKEN_EXPIRY_VALUE})
        self.secret_key = Config.JWT_SECRET_KEY

    async def get_or_create_user(self, validated_data: dict, ip_address: str) -> UserOut:
        """Returns or creates a user based on validated data (Async)."""
        try:
            email = validated_data.get("email")
            
            # Check if user exists (Async)
            existing_user = await self.user_repository.find_user_by_email(email)
            if existing_user:
                logging.info(f"User already exists: {existing_user.user_id}")
                return UserOut(**existing_user.model_dump())

            # Create new user (Async GeoService + Async Repository)
            user_id = f"user_{uuid4()}"
            region = await self.geo_service.get_region_from_ip(ip_address)
            
            created_user = await self.user_repository.create_user(
                user_email=email,
                user_id=user_id,
                region=region
            )
            if not created_user:
                raise APIException("User creation failed")
                
            return UserOut(**created_user.model_dump())
            
        except APIException:
            raise
        except Exception as e:
            logging.error(f"User creation failed: {str(e)}")
            raise APIException("User creation process failed")

    async def generate_tokens(self, user: UserOut, session_id: str = None) -> Tuple[str, str]:
        """Generate and store access and refresh tokens (Async Redis)."""
        try:
            claims = {
                "user_email": user.user_email,
                "user_id": user.user_id,
                "region": user.region,
                "session_id": session_id
            }

            access_token = self._create_access_token(session_id, claims)
            refresh_token = self._create_refresh_token(session_id, claims)

            # Store token JTIs in Redis (Async)
            await self.token_repository.store_token_data(session_id, access_token, refresh_token)
            await self.token_repository.add_user_session(user.user_id, session_id)

            return access_token, refresh_token

        except Exception as e:
            logging.error(f"Token generation failed for session {session_id}: {str(e)}")
            raise TokenGenerationException("Failed to generate tokens")

    async def refresh(self, session_id: str, additional_claims: Dict[str, Any]) -> Tuple[str, str]:
        """Refresh tokens for a specific session (Async)."""
        try:
            await self._invalidate_tokens(session_id)

            access_token = self._create_access_token(session_id, additional_claims)
            refresh_token = self._create_refresh_token(session_id, additional_claims)
            await self.token_repository.store_token_data(session_id, access_token, refresh_token)

            return access_token, refresh_token

        except InvalidTokenException:
            raise
        except Exception as e:
            logging.error(f"Token refresh failed for session {session_id}: {str(e)}")
            raise TokenGenerationException("Failed to refresh tokens")

    async def logout(self, session_id: str, user_id: str) -> bool:
        """Invalidate tokens for a session (Async)."""
        try:
            await self._invalidate_tokens(session_id)
            await self.token_repository.remove_user_session(user_id, session_id)
            return True
        except Exception as e:
            logging.error(f"Logout failed for session {session_id}: {str(e)}")
            raise APIException("Logout failed")

    # ─── Token Creation (CPU-bound, remains sync) ──────────────────

    def _create_access_token(
        self, session_id: str, additional_claims: Optional[Dict[str, Any]] = None
    ) -> str:
        try:
            now = datetime.now(timezone.utc)
            expire = now + self.access_expiry
            
            payload = {
                "sub": session_id,
                "iat": now,
                "exp": expire,
                "jti": str(uuid4()),
                "type": "access",
                **(additional_claims or {})
            }
            return jwt.encode(payload, self.secret_key, algorithm=self.ALGORITHM)
        except Exception as e:
            logging.error(f"Access token creation failed: {str(e)}")
            raise TokenGenerationException("Failed to create access token")

    def _create_refresh_token(
        self, session_id: str, additional_claims: Optional[Dict[str, Any]] = None
    ) -> str:
        try:
            now = datetime.now(timezone.utc)
            expire = now + self.refresh_expiry
            
            payload = {
                "sub": session_id,
                "iat": now,
                "exp": expire,
                "jti": str(uuid4()),
                "type": "refresh",
                **(additional_claims or {})
            }
            return jwt.encode(payload, self.secret_key, algorithm=self.ALGORITHM)
        except Exception as e:
            logging.error(f"Refresh token creation failed: {str(e)}")
            raise TokenGenerationException("Failed to create refresh token")

    async def _invalidate_tokens(self, session_id: str) -> None:
        try:
            await self.token_repository.invalidate_tokens(session_id)
        except Exception as e:
            logging.error(f"Failed to invalidate tokens for session {session_id}: {str(e)}")
            raise TokenStorageException("Failed to delete token from Redis")
