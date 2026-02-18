from typing import Any, Dict, Optional, List
from pydantic import BaseModel, Field, EmailStr

# ─── Request Schemas ──────────────────────────────────────────

class ChatRequest(BaseModel):
    """Schema for incoming chat requests."""
    question: Optional[str] = Field(None, example="Find budget surgical kits")
    # Note: Images are handled via UploadFile in FastAPI, not in this JSON schema.

class AudioChatRequest(BaseModel):
    """Schema for audio-based chat queries."""
    text_query: str = Field(..., example="I need medical supplies")

# ─── Response Schemas ──────────────────────────────────────────

class ChatResponse(BaseModel):
    """
    Standardized Success Response for Chat queries.
    
    🎓 PRO TIP: Using a structured schema ensures the frontend always
    receives the same data format, reducing client-side errors.
    """
    message: str = Field(..., example="Query processed successfully")
    data: Dict[str, Any] = Field(..., description="The AI response data")
    show_pagination: bool = Field(default=False)
    
    class Config:
        json_schema_extra = {
            "example": {
                "message": "Product search processed.",
                "data": {
                    "answer": "Here are some surgical kits...",
                    "products": [{"sku": "SKU123", "name": "Kit A"}]
                },
                "show_pagination": False
            }
        }

class BaseAPIResponse(BaseModel):
    """Generic wrapper for all API responses."""
    success: bool = True
    message: str
    data: Optional[Any] = None
