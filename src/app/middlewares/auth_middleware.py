import logging
from typing import Optional

from fastapi import Request, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError, ExpiredSignatureError
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from src.app.config.config import Config

# Security scheme for Swagger UI (shows the lock icon)
bearer_scheme = HTTPBearer(auto_error=False)


class AuthMiddleware(BaseHTTPMiddleware):
    """
    FastAPI Middleware for JWT authentication.
    
    🎓 MIGRATION NOTE:
    Original Gervet used a custom __call__ approach.
    FastAPI's BaseHTTPMiddleware provides a cleaner interface via dispatch().
    """
    
    PUBLIC_PATHS = [
        "/",
        "/docs",
        "/redoc",
        "/openapi.json",
        "/v1/auth/login",
        "/v1/assets/public",
        "/health",
    ]

    async def dispatch(self, request: Request, call_next):
        """Middleware entry point — runs for every request."""
        path = request.url.path
        method = request.method

        # Allow CORS preflight
        if method == "OPTIONS":
            return await call_next(request)

        # Allow public paths
        if self._is_public_path(path):
            return await call_next(request)

        # Allow refresh token endpoint (it has its own token validation)
        if path == "/v1/auth/refresh_token":
            return await call_next(request)

        # Validate access token
        token = None
        auth_header = request.headers.get("Authorization")
        
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ")[1]
        else:
            # Fallback to cookie
            token = request.cookies.get("access_token")

        if not token:
            return self._error_response(
                "AUTH_401_MISSING_TOKEN",
                "Missing Authorization token. Please provide it in header (Bearer) or cookies (access_token).",
                401
            )

        try:
            payload = self._decode_token(token)
            
            # Ensure it's an access token
            if payload.get("type") == "refresh":
                 return self._error_response(
                    "AUTH_401_WRONG_TOKEN_TYPE",
                    "Expected access token, but received refresh token.",
                    401
                )

            # Attach user info to request state for downstream use
            request.state.user = payload

        except ExpiredSignatureError:
            return self._error_response(
                "AUTH_401_EXPIRED_TOKEN",
                "Token has expired. Please log in again.",
                401
            )
        except JWTError as e:
            logging.error(f"JWT Error: {e}")
            return self._error_response(
                "AUTH_401_INVALID_TOKEN",
                "Invalid token. Please provide a valid token.",
                401
            )
        except Exception as e:
            logging.error(f"Auth middleware error: {e}")
            return self._error_response(
                "AUTH_401_UNAUTHORIZED",
                "Unauthorized access.",
                401
            )

        return await call_next(request)

    def _is_public_path(self, path: str) -> bool:
        return any(path.startswith(p) for p in self.PUBLIC_PATHS)

    def _decode_token(self, token: str) -> dict:
        return jwt.decode(token, Config.JWT_SECRET_KEY, algorithms=["HS256"])

    def _error_response(self, code: str, message: str, status_code: int) -> JSONResponse:
        return JSONResponse(
            status_code=status_code,
            content={
                "status": "error",
                "error": {
                    "code": code,
                    "type": "authentication_error",
                    "message": message,
                    "suggestion": "Ensure that you include a valid Authorization token in the request headers."
                }
            }
        )


# ─── FastAPI Dependencies (for route-level auth) ──────────────────────

async def get_current_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme)
) -> dict:
    """
    Dependency for protected routes — extracts and validates the JWT.
    Supports token in:
    1. Request state (from middleware)
    2. Authorization header (Bearer)
    3. Cookies (access_token)
    """
    # 1. If middleware already validated (attached to state)
    if hasattr(request.state, "user") and request.state.user:
        return request.state.user

    token = None
    
    # 2. Check Authorization Header
    if credentials:
        token = credentials.credentials
    
    # 3. Check Cookies
    if not token:
        token = request.cookies.get("access_token")

    if not token:
        raise HTTPException(
            status_code=401,
            detail={
                "code": "AUTH_401_MISSING_TOKEN", 
                "message": "Missing Authorization token. Provide it in header or cookies."
            }
        )

    try:
        payload = jwt.decode(token, Config.JWT_SECRET_KEY, algorithms=["HS256"])
        return payload
    except ExpiredSignatureError:
        raise HTTPException(
            status_code=401,
            detail={"code": "AUTH_401_EXPIRED_TOKEN", "message": "Token has expired."}
        )
    except JWTError:
        raise HTTPException(
            status_code=401,
            detail={"code": "AUTH_401_INVALID_TOKEN", "message": "Invalid token."}
        )


async def get_refresh_token_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme)
) -> dict:
    """
    Dependency for the refresh token endpoint.
    Validates the token is specifically a 'refresh' type.
    Supports token in:
    1. Authorization Header (Bearer)
    2. JSON Body {"refresh_token": "..."}
    3. Cookies (refresh_token)
    """
    token = None
    
    # 1. Check Authorization Header
    if credentials:
        token = credentials.credentials
        logging.debug("Refresh token found in Authorization header")
    
    # 2. Check Cookies
    if not token:
        token = request.cookies.get("refresh_token")
        if token:
            logging.debug("Refresh token found in cookies")

    # 3. Check JSON Body
    if not token:
        try:
            # We use a try-except because json() might fail if body is empty/not JSON
            body = await request.json()
            token = body.get("refresh_token")
            if token:
                logging.debug("Refresh token found in JSON body")
        except Exception:
            # Body might be empty or invalid JSON
            pass

    if not token:
        logging.warning(f"Refresh token missing. Headers: {dict(request.headers.items())}")
        raise HTTPException(
            status_code=401,
            detail={
                "code": "AUTH_401_MISSING_TOKEN", 
                "message": "Missing refresh token. Provide it in Authorization header, JSON body, or cookies."
            }
        )

    try:
        payload = jwt.decode(token, Config.JWT_SECRET_KEY, algorithms=["HS256"])

        if payload.get("type") != "refresh":
            logging.warning(f"Invalid token type provided to refresh endpoint: {payload.get('type')}")
            raise HTTPException(
                status_code=401,
                detail={"code": "AUTH_401_WRONG_TOKEN_TYPE", "message": "Invalid token type. Refresh token required."}
            )

        return payload

    except ExpiredSignatureError:
        raise HTTPException(
            status_code=401,
            detail={"code": "AUTH_401_EXPIRED_TOKEN", "message": "Refresh token has expired."}
        )
    except JWTError as e:
        logging.error(f"JWT Decode error in refresh: {e}")
        raise HTTPException(
            status_code=401,
            detail={"code": "AUTH_401_INVALID_TOKEN", "message": "Invalid refresh token."}
        )
