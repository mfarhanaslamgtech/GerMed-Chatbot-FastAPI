import logging
import asyncio
from typing import Set, Optional
from redis.asyncio import Redis
from jose import jwt, JWTError
from src.app.config.settings import settings
from src.app.exceptions.custom_exceptions import APIException

class TokenRepository:
    """
    Handles token storage and validation in Redis (Async).
    
    🎓 PRO TIP:
    Using Redis sets (SADD) to manage user sessions allows us 
    to invalidate all sessions for a user instantly (e.g., on password change).
    """

    ALGORITHM = "HS256"

    def __init__(self, redis_conn: Redis):
        self.redis = redis_conn
        self.secret_key = settings.security.JWT_SECRET_KEY

    async def store_token_data(self, session_id: str, access_token: str, refresh_token: str) -> None:
        """Store access and refresh token JTIs in Redis asynchronously."""
        try:
            access_data = self._decode_token(access_token)
            refresh_data = self._decode_token(refresh_token)

            # Calculate actual TTL from token timestamps
            access_ttl = access_data['exp'] - access_data['iat']
            refresh_ttl = refresh_data['exp'] - refresh_data['iat']

            # Pipeline for atomic operations
            async with self.redis.pipeline(transaction=True) as pipe:
                pipe.setex(f"access:{session_id}", access_ttl, access_data['jti'])
                pipe.setex(f"refresh:{session_id}", refresh_ttl, refresh_data['jti'])
                await pipe.execute()
                
            logging.info(f"🔑 Tokens stored for session: {session_id}")
        except Exception as e:
            logging.error(f"❌ Failed to store tokens for session {session_id}: {str(e)}")
            raise APIException("Failed to store security tokens", status_code=500)

    async def is_valid_refresh_token(self, session_id: str, token_jti: str) -> bool:
        """Validate a refresh token JTI against stored JTI."""
        try:
            stored_jti = await self.redis.get(f"refresh:{session_id}")
            return str(stored_jti) == token_jti if stored_jti else False
        except Exception as e:
            logging.error(f"❌ Redis error validating refresh token: {e}")
            return False

    async def is_valid_access_token(self, session_id: str, token_jti: str) -> bool:
        """Validate an access token JTI against stored JTI."""
        try:
            stored_jti = await self.redis.get(f"access:{session_id}")
            return str(stored_jti) == token_jti if stored_jti else False
        except Exception as e:
            logging.error(f"❌ Redis error validating access token: {e}")
            return False

    async def invalidate_tokens(self, session_id: str) -> None:
        """Remove access and refresh token JTIs from Redis."""
        try:
            await self.redis.delete(f"access:{session_id}", f"refresh:{session_id}")
            logging.info(f"🚫 Tokens invalidated for session: {session_id}")
        except Exception as e:
            logging.error(f"❌ Failed to invalidate tokens: {e}")

    async def add_user_session(self, user_id: str, session_id: str) -> None:
        """Add a session ID to a user's active session set."""
        try:
            await self.redis.sadd(f"user_sessions:{user_id}", session_id)
        except Exception as e:
            logging.error(f"❌ Failed to add session for user {user_id}: {e}")

    async def remove_user_session(self, user_id: str, session_id: str) -> None:
        """Remove a session ID from a user's active session set."""
        try:
            await self.redis.srem(f"user_sessions:{user_id}", session_id)
        except Exception as e:
            logging.error(f"❌ Failed to remove session for user {user_id}: {e}")

    async def get_user_sessions(self, user_id: str) -> Set[str]:
        """Get all session IDs for a user."""
        try:
            sessions = await self.redis.smembers(f"user_sessions:{user_id}")
            return {s if isinstance(s, str) else s.decode('utf-8') for s in sessions}
        except Exception as e:
            logging.error(f"❌ Failed to get sessions for user {user_id}: {e}")
            return set()

    def _decode_token(self, token: str) -> dict:
        """Decode a JWT token safely."""
        try:
            return jwt.decode(token, self.secret_key, algorithms=[self.ALGORITHM])
        except JWTError as e:
            logging.error(f"❌ JWT Decode Error: {e}")
            raise APIException("Invalid or expired token", status_code=401)
