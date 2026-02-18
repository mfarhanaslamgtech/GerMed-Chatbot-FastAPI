from fastapi import HTTPException, status
from typing import Any, Dict, Optional

class APIException(HTTPException):
    """
    Base exception for all GerMed API errors.
    Automatically maps to FastAPI's HTTPException for consistent responses.
    """
    def __init__(
        self, 
        message: str, 
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        details: Optional[Any] = None
    ):
        super().__init__(status_code=status_code, detail={"message": message, "details": details})

class DatabaseException(APIException):
    """Raised when database operations fail."""
    def __init__(self, message: str = "Database operation failed", details: Any = None):
        super().__init__(message, status_code=status.HTTP_503_SERVICE_UNAVAILABLE, details=details)

class RepositoryException(APIException):
    """Raised for errors within the repository layer."""
    def __init__(self, message: str, details: Any = None):
        super().__init__(message, status_code=status.HTTP_400_BAD_REQUEST, details=details)

class TokenGenerationException(APIException):
    """Raised when JWT token generation fails."""
    def __init__(self, message: str = "Token generation failed", details: Any = None):
        super().__init__(message, status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, details=details)

class TokenStorageException(APIException):
    """Raised when token storage (Redis) operations fail."""
    def __init__(self, message: str = "Token storage error", details: Any = None):
        super().__init__(message, status_code=status.HTTP_503_SERVICE_UNAVAILABLE, details=details)

class InvalidTokenException(APIException):
    """Raised when a JWT token is invalid or expired."""
    def __init__(self, message: str = "Invalid token", details: Any = None):
        super().__init__(message, status_code=status.HTTP_401_UNAUTHORIZED, details=details)

class InvalidAccessTokenException(InvalidTokenException):
    """Raised specifically for invalid access tokens."""
    def __init__(self, message: str = "Invalid access token", details: Any = None):
        super().__init__(message, details=details)

class MissingFieldException(APIException):
    """Raised when a required field is missing from the request."""
    def __init__(self, message: str = "Required field missing", details: Any = None):
        super().__init__(message, status_code=422, details=details)

class InvalidImageException(APIException):
    """Raised when an uploaded image fails validation."""
    def __init__(self, message: str = "Invalid image", details: Any = None):
        super().__init__(message, status_code=422, details=details)

class InvalidQuestionTypeException(APIException):
    """Raised when a question field is not the expected type."""
    def __init__(self, field: str = "question", details: Any = None):
        super().__init__(f"'{field}' must be a string", status_code=422, details=details)

class InvalidQuestionLengthException(APIException):
    """Raised when a question field exceeds length bounds."""
    def __init__(self, field: str = "question", min_len: int = 1, max_len: int = 500, details: Any = None):
        super().__init__(
            f"'{field}' must be between {min_len} and {max_len} characters",
            status_code=422,
            details=details
        )

