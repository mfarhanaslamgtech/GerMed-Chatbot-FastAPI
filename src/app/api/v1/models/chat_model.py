from datetime import datetime
from typing import Optional, Union, Dict, Any, Annotated
from pydantic import BaseModel, Field, EmailStr, ConfigDict, BeforeValidator
from enum import Enum
from bson import ObjectId

# 🎓 Pro Tip: Handle ObjectIds as strings in JSON
PyObjectId = Annotated[str, BeforeValidator(str)]

class RoleEnum(str, Enum):
    user = "user"
    assistant = "assistant"

class QuestionContent(BaseModel):
    text: Optional[str] = None
    image: Optional[str] = None

class UserContent(BaseModel):
    question: Optional[QuestionContent] = None

    @classmethod
    def create(cls, text: Optional[str] = None, image: Optional[str] = None):
        """Factory method for user content"""
        if text or image:
            return cls(question=QuestionContent(text=text, image=image))
        return cls()

class AssistantContent(BaseModel):
    answer: Union[str, Dict[str, Any]]

    @classmethod
    def create(cls, answer: Union[str, Dict[str, Any]]):
        """Factory method for assistant response"""
        return cls(answer=answer)

class ChatMessages(BaseModel):
    """
    Core Chat Message model for MongoDB storage.
    """
    id: Optional[PyObjectId] = Field(alias="_id", default=None)
    user_id: Optional[str] = None
    user_email: EmailStr
    role: RoleEnum
    content: Union[UserContent, AssistantContent]
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True,
        json_schema_extra={
            "example": {
                "user_email": "user@example.com",
                "role": "user",
                "content": {
                    "question": {"text": "Hello bot", "image": None}
                }
            }
        }
    )
