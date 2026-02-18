"""
FAQ Request Validator.

🎓 MIGRATION NOTE:
Same logic as original, just using updated exception imports.
No Flask dependencies — pure Python validation.
"""
from src.app.exceptions.custom_exceptions import (
    InvalidQuestionTypeException,
    InvalidQuestionLengthException,
    MissingFieldException
)


def validate_faqs_agent_request(request_data: dict) -> dict:
    """
    Validates FAQ agent request data.
    
    Ensures 'text_query' field exists, is a string, and is within length bounds.
    
    Args:
        request_data: Dict containing at minimum a 'text_query' key.
        
    Returns:
        The validated request_data dict.
    """
    if "text_query" not in request_data:
        raise MissingFieldException("'text_query' field is required")

    if not isinstance(request_data["text_query"], str):
        raise InvalidQuestionTypeException("text_query")

    if not (1 <= len(request_data["text_query"]) <= 500):
        raise InvalidQuestionLengthException("text_query")

    return request_data
