"""
Layer 7 Test — Validators & Schemas
Tests all validators and Pydantic schemas work correctly.
"""
import asyncio
import sys
import os
import io

sys.path.append(os.getcwd())


async def test_layer7():
    print("=" * 60)
    print("🧪 Testing Layer 7: Validators & Schemas")
    print("=" * 60)

    # ═══════════════════════════════════════════════════════
    # 1. Test Exception Classes
    # ═══════════════════════════════════════════════════════
    print("\n1️⃣  Testing Validation Exceptions...")
    from src.app.exceptions.custom_exceptions import (
        InvalidImageException,
        InvalidQuestionTypeException,
        InvalidQuestionLengthException,
        MissingFieldException
    )

    # Test InvalidImageException
    exc = InvalidImageException("Bad image")
    assert exc.status_code == 422
    print("   ✅ InvalidImageException (422)")

    # Test InvalidQuestionTypeException
    exc = InvalidQuestionTypeException("text_query")
    assert exc.status_code == 422
    assert "text_query" in str(exc.detail)
    print("   ✅ InvalidQuestionTypeException (422)")

    # Test InvalidQuestionLengthException
    exc = InvalidQuestionLengthException("question", 1, 500)
    assert exc.status_code == 422
    assert "500" in str(exc.detail)
    print("   ✅ InvalidQuestionLengthException (422)")

    # ═══════════════════════════════════════════════════════
    # 2. Test Input Validators
    # ═══════════════════════════════════════════════════════
    print("\n2️⃣  Testing Input Validators...")
    from src.app.api.v1.validators.input_validators import validate_email, validate_required_string

    # Valid email
    assert validate_email("user@example.com") == "user@example.com"
    print("   ✅ validate_email('user@example.com') → passed")

    # Invalid email
    try:
        validate_email("not-an-email")
        assert False, "Should have raised"
    except MissingFieldException:
        print("   ✅ validate_email('not-an-email') → MissingFieldException raised")

    # Valid string
    assert validate_required_string("hello", "test_field") == "hello"
    print("   ✅ validate_required_string('hello', 'test_field') → passed")

    # Missing string
    try:
        validate_required_string(None, "test_field")
        assert False, "Should have raised"
    except MissingFieldException:
        print("   ✅ validate_required_string(None) → MissingFieldException raised")

    # ═══════════════════════════════════════════════════════
    # 3. Test Text Search Validator
    # ═══════════════════════════════════════════════════════
    print("\n3️⃣  Testing Text Search Validator...")
    from src.app.api.v1.validators.text_search_validator import validate_textbot_request

    # Valid
    result = validate_textbot_request({"question": "Find scissors"})
    assert result["question"] == "Find scissors"
    print("   ✅ Valid request passed")

    # Missing field
    try:
        validate_textbot_request({})
        assert False
    except MissingFieldException:
        print("   ✅ Missing 'question' → MissingFieldException raised")

    # Wrong type
    try:
        validate_textbot_request({"question": 12345})
        assert False
    except InvalidQuestionTypeException:
        print("   ✅ Non-string 'question' → InvalidQuestionTypeException raised")

    # Too long
    try:
        validate_textbot_request({"question": "x" * 501})
        assert False
    except InvalidQuestionLengthException:
        print("   ✅ 501-char 'question' → InvalidQuestionLengthException raised")

    # ═══════════════════════════════════════════════════════
    # 4. Test FAQ Validator
    # ═══════════════════════════════════════════════════════
    print("\n4️⃣  Testing FAQ Validator...")
    from src.app.api.v1.validators.faqs_validator import validate_faqs_agent_request

    result = validate_faqs_agent_request({"text_query": "How to return?"})
    assert result["text_query"] == "How to return?"
    print("   ✅ Valid FAQ request passed")

    try:
        validate_faqs_agent_request({})
        assert False
    except MissingFieldException:
        print("   ✅ Missing 'text_query' → raised correctly")

    # ═══════════════════════════════════════════════════════
    # 5. Test Audio Text Validator
    # ═══════════════════════════════════════════════════════
    print("\n5️⃣  Testing Audio Text Validator...")
    from src.app.api.v1.validators.audio_text_validator import audio_text_validator

    result = audio_text_validator({"question": "What is gervetusa?"})
    assert result["text_query"] == "What is gervetusa?"
    print("   ✅ Valid audio request → text_query extracted")

    try:
        audio_text_validator({"question": 999})
        assert False
    except InvalidQuestionTypeException:
        print("   ✅ Non-string → InvalidQuestionTypeException raised")

    # ═══════════════════════════════════════════════════════
    # 6. Test Image Validator (sync check)
    # ═══════════════════════════════════════════════════════
    print("\n6️⃣  Testing Image Validator...")
    from src.app.api.v1.validators.image_validator import (
        validate_image_upload, validate_image_bytes, ALLOWED_IMAGE_TYPES
    )

    # Test allowed types
    assert "image/jpeg" in ALLOWED_IMAGE_TYPES
    assert "image/png" in ALLOWED_IMAGE_TYPES
    assert "image/webp" in ALLOWED_IMAGE_TYPES
    print(f"   ✅ Allowed types: {ALLOWED_IMAGE_TYPES}")

    # Test None file
    try:
        validate_image_upload(None)
        assert False
    except InvalidImageException:
        print("   ✅ None file → InvalidImageException raised")

    # Test empty bytes
    try:
        validate_image_bytes(b"")
        assert False
    except InvalidImageException:
        print("   ✅ Empty bytes → InvalidImageException raised")

    # Test invalid bytes (not an image)
    try:
        validate_image_bytes(b"not an image at all")
        assert False
    except InvalidImageException:
        print("   ✅ Invalid bytes → InvalidImageException raised")

    # ═══════════════════════════════════════════════════════
    # 7. Test User Schemas (Marshmallow → Pydantic)
    # ═══════════════════════════════════════════════════════
    print("\n7️⃣  Testing User Schemas (Pydantic v2)...")
    from src.app.api.v1.schemas.user_schema import (
        UserSignupSchema, UserResponseSchema, TokenPayloadSchema, TokenResponseSchema
    )

    # Valid signup
    signup = UserSignupSchema(email="test@example.com")
    assert signup.email == "test@example.com"
    print("   ✅ UserSignupSchema: valid email accepted")

    # Invalid signup
    try:
        UserSignupSchema(email="not-valid")
        assert False
    except Exception as e:
        print(f"   ✅ UserSignupSchema: invalid email rejected ({type(e).__name__})")

    # Extra fields ignored (like Marshmallow's EXCLUDE)
    signup = UserSignupSchema(email="test@example.com", extra_field="should be ignored")
    assert not hasattr(signup, "extra_field")
    print("   ✅ UserSignupSchema: extra fields ignored (matches EXCLUDE behavior)")

    # User response
    user_resp = UserResponseSchema(
        user_id="user_abc123",
        user_email="test@example.com",
        region="Asia/Karachi"
    )
    assert user_resp.user_id == "user_abc123"
    print("   ✅ UserResponseSchema: valid response created")

    # Token payload
    token_payload = TokenPayloadSchema(
        session_id="sess_123",
        user_id="user_abc",
        user_email="test@example.com"
    )
    assert token_payload.session_id == "sess_123"
    print("   ✅ TokenPayloadSchema: valid payload created")

    # Token response
    token_resp = TokenResponseSchema(
        access_token="eyJ...",
        refresh_token="eyJ..."
    )
    assert token_resp.access_token.startswith("eyJ")
    print("   ✅ TokenResponseSchema: valid response created")

    # ═══════════════════════════════════════════════════════
    # 8. Test Chat Schemas (existing)
    # ═══════════════════════════════════════════════════════
    print("\n8️⃣  Testing Chat Schemas (existing)...")
    from src.app.api.v1.schemas.chat_schema import ChatRequest, AudioChatRequest, ChatResponse

    chat_req = ChatRequest(question="Find scissors")
    assert chat_req.question == "Find scissors"
    print("   ✅ ChatRequest: valid")

    audio_req = AudioChatRequest(text_query="Hello")
    assert audio_req.text_query == "Hello"
    print("   ✅ AudioChatRequest: valid")

    chat_resp = ChatResponse(message="ok", data={"answer": "test"})
    assert chat_resp.show_pagination == False
    print("   ✅ ChatResponse: valid with default show_pagination=False")

    print("\n" + "=" * 60)
    print("🎉 Layer 7 — ALL TESTS PASSED!")
    print("=" * 60)


asyncio.run(test_layer7())
