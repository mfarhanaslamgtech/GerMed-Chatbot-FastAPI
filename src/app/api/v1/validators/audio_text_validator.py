"""
Audio Text Validator.

🎓 MIGRATION NOTE:
Original validated 'question' key and returned as 'text_query'.
Logic preserved exactly. No Flask imports needed.
"""
from src.app.exceptions.custom_exceptions import (
    InvalidQuestionTypeException,
    MissingFieldException
)


def audio_text_validator(request_data: dict) -> dict:
    """
    Validates audio chatbot input.
    
    Ensures 'question' field exists and is a string.
    Returns dict with 'text_query' key for downstream services.
    
    Args:
        request_data: Dict containing a 'question' key.
        
    Returns:
        dict with {'text_query': <validated_question>}
    """
    if "question" not in request_data:
        raise MissingFieldException("'question' field is required")

    value = request_data["question"]

    if not isinstance(value, str):
        raise InvalidQuestionTypeException("question")

    return {"text_query": value}
