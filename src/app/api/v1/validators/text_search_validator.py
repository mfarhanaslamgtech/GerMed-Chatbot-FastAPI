"""
Text Search Request Validator.

🎓 MIGRATION NOTE:
Original used Flask's `request` object and werkzeug's BadRequest.
Now uses pure Python dict validation — no framework dependency.

In most cases, FastAPI's Form()/Body() + Pydantic schema handles this
automatically. This validator exists for manual validation in services.
"""
from src.app.exceptions.custom_exceptions import (
    InvalidQuestionTypeException,
    InvalidQuestionLengthException,
    MissingFieldException
)


def validate_textbot_request(request_data: dict) -> dict:
    """
    Validates textbot request data dictionary.
    
    Ensures 'question' field exists, is a string, and is within length bounds.
    
    Args:
        request_data: Dict containing at minimum a 'question' key.
        
    Returns:
        The validated request_data dict.
        
    Raises:
        MissingFieldException, InvalidQuestionTypeException, InvalidQuestionLengthException
    """
    if "question" not in request_data:
        raise MissingFieldException("'question' field is required")

    if not isinstance(request_data["question"], str):
        raise InvalidQuestionTypeException("question")

    if not (1 <= len(request_data["question"]) <= 500):
        raise InvalidQuestionLengthException("question")

    return request_data
