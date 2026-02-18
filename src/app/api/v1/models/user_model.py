from datetime import datetime
from typing import Optional, Annotated
from pydantic import BaseModel, Field, EmailStr, ConfigDict, BeforeValidator
from bson import ObjectId
import uuid

# 🎓 PRO TIP: Pydantic v2 handles ObjectId slightly differently.
# We use Annotated with a validator to ensure MongoDB ObjectIds are handled as strings in JSON.
PyObjectId = Annotated[str, BeforeValidator(str)]

class UserBase(BaseModel):
    """Base model shared by all User models"""
    user_email: EmailStr
    region: Optional[str] = None

class UserCreate(UserBase):
    """Model for user creation"""
    pass

class UserDB(UserBase):
    """
    Database model for MongoDB.
    
    🎓 FASTAPI MIGRATION NOTE:
    In Pydantic v2, we use 'model_config' instead of 'class Config'.
    'populate_by_name' allows using '_id' and 'id' interchangeably.
    """
    id: Optional[PyObjectId] = Field(alias="_id", default=None)
    user_id: str = Field(default_factory=lambda: f"user_{uuid.uuid4().hex[:8]}")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    login_history: list[datetime] = Field(default_factory=list)

    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True,
        json_schema_extra={
            "example": {
                "user_id": "user_a1b2c3d4",
                "user_email": "user@example.com",
                "region": "USA",
                "created_at": "2024-01-01T00:00:00"
            }
        }
    )

class UserOut(UserBase):
    """Output model for API responses"""
    user_id: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
