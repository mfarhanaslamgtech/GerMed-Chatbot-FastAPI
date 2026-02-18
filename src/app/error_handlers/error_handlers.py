import logging
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from src.app.exceptions.custom_exceptions import APIException

logger = logging.getLogger(__name__)


def register_exception_handlers(app: FastAPI):
    """
    Register global exception handlers for the FastAPI app.
    
    🎓 MIGRATION NOTE:
    Flask used @app.errorhandler(404), etc.
    FastAPI uses @app.exception_handler(ExceptionClass).
    """

    @app.exception_handler(APIException)
    async def api_exception_handler(request: Request, exc: APIException):
        """Handle our custom APIException and subclasses."""
        logger.warning(f"APIException: {exc.detail} | Path: {request.url.path}")
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "status": "error",
                "error": exc.detail if isinstance(exc.detail, dict) else {"message": str(exc.detail)}
            }
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        """Handle Pydantic/FastAPI request validation errors."""
        logger.warning(f"Validation Error: {exc.errors()} | Path: {request.url.path}")
        errors = []
        for error in exc.errors():
            errors.append({
                "field": " -> ".join(str(loc) for loc in error.get("loc", [])),
                "message": error.get("msg", ""),
                "type": error.get("type", "")
            })
        return JSONResponse(
            status_code=422,
            content={
                "status": "error",
                "error": {
                    "code": "VALIDATION_422",
                    "type": "validation_error",
                    "message": "Request validation failed.",
                    "details": errors
                }
            }
        )

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException):
        """Handle standard HTTP exceptions (404, 405, etc.)."""
        logger.warning(f"HTTP {exc.status_code}: {exc.detail} | Path: {request.url.path}")
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "status": "error",
                "error": {
                    "code": f"HTTP_{exc.status_code}",
                    "type": "http_error",
                    "message": exc.detail if isinstance(exc.detail, str) else str(exc.detail)
                }
            }
        )

    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        """Catch-all for unhandled exceptions — prevents raw tracebacks in responses."""
        logger.error(f"Unhandled Exception: {str(exc)} | Path: {request.url.path}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={
                "status": "error",
                "error": {
                    "code": "INTERNAL_500",
                    "type": "server_error",
                    "message": "An unexpected error occurred. Please try again later."
                }
            }
        )
