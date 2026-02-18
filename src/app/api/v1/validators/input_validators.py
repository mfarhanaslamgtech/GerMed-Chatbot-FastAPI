"""
General Input Validators.

🎓 MIGRATION NOTE:
Original used a regex function. We keep it for places where
Pydantic's EmailStr doesn't apply (e.g. raw dict parsing).
FastAPI routes should prefer Pydantic's `EmailStr` type hint instead.
"""
import re

from src.app.exceptions.custom_exceptions import MissingFieldException


EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$")


def validate_email(email: str) -> str:
    """
    Validate email format using regex.
    Returns the email if valid, raises MissingFieldException if not.
    
    🎓 TIP: Prefer Pydantic's EmailStr in route schemas.
    Use this only for manual validation in services/controllers.
    """
    if not email or not EMAIL_REGEX.match(email):
        raise MissingFieldException(f"Invalid email format: '{email}'")
    return email


def validate_required_string(value: str, field_name: str, min_len: int = 1, max_len: int = 500) -> str:
    """
    Validate that a value is a non-empty string within length bounds.
    Generic utility for any string field.
    """
    if value is None:
        raise MissingFieldException(f"'{field_name}' is required")
    
    if not isinstance(value, str):
        from src.app.exceptions.custom_exceptions import InvalidQuestionTypeException
        raise InvalidQuestionTypeException(field_name)
    
    if not (min_len <= len(value) <= max_len):
        from src.app.exceptions.custom_exceptions import InvalidQuestionLengthException
        raise InvalidQuestionLengthException(field_name, min_len, max_len)
    
    return value
