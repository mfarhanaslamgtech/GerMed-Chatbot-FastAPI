"""
User Schemas — Pydantic v2 (migrated from Marshmallow).

🎓 MIGRATION COMPARISON:
┌──────── Marshmallow (Gervet) ──────────┐   ┌──────── Pydantic v2 (GerMed) ────────┐
│ class UserSignupSchema(Schema):        │ → │ class UserSignupSchema(BaseModel):    │
│   email = fields.Email(required=True)  │   │   email: EmailStr                     │
│   class Meta:                          │   │   model_config = ConfigDict(...)       │
│     unknown = EXCLUDE                  │   │   # Extra fields auto-forbidden       │
└────────────────────────────────────────┘   └───────────────────────────────────────┘

Pydantic v2 gives us:
  ✅ Auto-validation on assignment
  ✅ Fast JSON serialization
  ✅ OpenAPI schema generation (appears in /docs)
  ✅ No separate schema library needed
"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr, Field, ConfigDict


# ─── Request Schemas ──────────────────────────────────────────

class UserSignupSchema(BaseModel):
    """Schema for user login/signup requests."""
    email: EmailStr = Field(..., examples=["user@example.com"])

    model_config = ConfigDict(
        extra="ignore",  # Equivalent to Marshmallow's unknown=EXCLUDE
        json_schema_extra={
            "example": {
                "email": "user@example.com"
            }
        }
    )


class UserLoginRequest(BaseModel):
    """Explicit login request body."""
    email: EmailStr = Field(..., description="User's email address")


class RefreshTokenRequest(BaseModel):
    """Request body for token refresh."""
    refresh_token: str = Field(..., description="The refresh token received during login")


# ─── Response Schemas ──────────────────────────────────────────

class UserResponseSchema(BaseModel):
    """Schema for user API responses."""
    user_id: str = Field(..., examples=["user_123456"])
    user_email: EmailStr = Field(..., examples=["user@example.com"])
    region: Optional[str] = Field(None, examples=["Asia/Karachi"])
    created_at: Optional[datetime] = Field(None, examples=["2024-01-01T00:00:00Z"])
    updated_at: Optional[datetime] = Field(None, examples=["2024-01-01T00:00:00Z"])

    model_config = ConfigDict(
        extra="ignore",
        from_attributes=True,
    )


class TokenPayloadSchema(BaseModel):
    """Schema for JWT token payload (for documentation/validation)."""
    session_id: str = Field(..., examples=["session_abc123"])
    user_id: str = Field(..., examples=["user_123456"])
    user_email: EmailStr = Field(..., examples=["user@example.com"])
    region: Optional[str] = Field(None, examples=["Asia/Karachi"])
    iat: Optional[int] = Field(None, examples=[1672444800])
    exp: Optional[int] = Field(None, examples=[1672531200])

    model_config = ConfigDict(extra="ignore")


class TokenResponseSchema(BaseModel):
    """Schema for token API responses."""
    access_token: str = Field(..., examples=["eyJhbGciOi..."])
    refresh_token: str = Field(..., examples=["eyJhbGciOi..."])
    user: Optional[UserResponseSchema] = None

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "access_token": "eyJhbGciOi...",
                "refresh_token": "eyJhbGciOi...",
                "user": {
                    "user_id": "user_123456",
                    "user_email": "user@example.com",
                    "region": "Asia/Karachi",
                    "created_at": "2024-01-01T00:00:00Z"
                }
            }
        }
    )
