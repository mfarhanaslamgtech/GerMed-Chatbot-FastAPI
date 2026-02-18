"""
Layer 8 Test — Visual Search Service & Image Query Handler
Tests the async visual search pipeline without requiring CLIP/Redis/OpenAI.
"""
import asyncio
import sys
import os
import json
import re

sys.path.append(os.getcwd())


def test_layer8():
    print("=" * 60)
    print("🧪 Testing Layer 8: Visual Search & Image Query Handler")
    print("=" * 60)

    # ═══════════════════════════════════════════════════════════
    # 1. Test Imports
    # ═══════════════════════════════════════════════════════════
    print("\n1️⃣  Testing Imports...")

    from src.app.api.v1.services.visual_search.visual_search_service import VisualSearchService
    print("   ✅ VisualSearchService imported")

    from src.app.api.v1.controllers.chat.image_query_handler import ImageQueryHandler
    print("   ✅ ImageQueryHandler imported")

    from src.app.api.v1.controllers.chat.chat_controller import ChatController
    print("   ✅ ChatController imported (with ImageQueryHandler support)")

    # ═══════════════════════════════════════════════════════════
    # 2. Test Static Helper Methods
    # ═══════════════════════════════════════════════════════════
    print("\n2️⃣  Testing Static Helper Methods...")

    # safe_parse_json
    valid_json = '{"start_message": "Hello", "core_message": {"product": []}}'
    parsed = VisualSearchService.safe_parse_json(valid_json)
    assert parsed["start_message"] == "Hello"
    print("   ✅ safe_parse_json: valid JSON parsed")

    # safe_parse_json with markdown code block
    markdown_json = '```json\n{"start_message": "Test"}\n```'
    parsed = VisualSearchService.safe_parse_json(markdown_json)
    assert parsed["start_message"] == "Test"
    print("   ✅ safe_parse_json: markdown-wrapped JSON parsed")

    # safe_parse_json with invalid input
    parsed = VisualSearchService.safe_parse_json("")
    assert "start_message" in parsed
    print("   ✅ safe_parse_json: empty input returns fallback")

    parsed = VisualSearchService.safe_parse_json(None)
    assert "core_message" in parsed
    print("   ✅ safe_parse_json: None returns fallback")

    # ═══════════════════════════════════════════════════════════
    # 3. Test Image URL Extraction
    # ═══════════════════════════════════════════════════════════
    print("\n3️⃣  Testing Image URL Extraction...")

    # Simple URL
    url = VisualSearchService._extract_image_url("https://example.com/img.jpg")
    assert url == "https://example.com/img.jpg"
    print("   ✅ Simple URL extracted")

    # From dict
    url = VisualSearchService._extract_image_url(
        {"medium": "https://example.com/medium.jpg", "large": "https://example.com/large.jpg"}
    )
    assert url == "https://example.com/medium.jpg"
    print("   ✅ URL from dict (medium priority)")

    # From list
    url = VisualSearchService._extract_image_url(
        [{"large": "https://example.com/large.jpg"}]
    )
    assert url == "https://example.com/large.jpg"
    print("   ✅ URL from list of dicts")

    # From JSON string
    url = VisualSearchService._extract_image_url(
        '[{"medium": "https://example.com/m.jpg"}]'
    )
    assert url == "https://example.com/m.jpg"
    print("   ✅ URL from JSON string")

    # None
    url = VisualSearchService._extract_image_url(None)
    assert url is None
    print("   ✅ None input returns None")

    # ═══════════════════════════════════════════════════════════
    # 4. Test Video Info Extraction
    # ═══════════════════════════════════════════════════════════
    print("\n4️⃣  Testing Video Info Extraction...")

    video = VisualSearchService._extract_video_info(None)
    assert video == {"youtube": None, "vimeo": None}
    print("   ✅ None returns empty video dict")

    video = VisualSearchService._extract_video_info([
        {"video_url": "https://youtube.com/watch?v=abc", "video_source": "youtube"},
        {"video_url": "https://vimeo.com/123456", "video_source": "vimeo"}
    ])
    assert video["youtube"] == "https://youtube.com/watch?v=abc"
    assert video["vimeo"] == "https://vimeo.com/123456"
    print("   ✅ YouTube + Vimeo extracted from list")

    # ═══════════════════════════════════════════════════════════
    # 5. Test Query Detection
    # ═══════════════════════════════════════════════════════════
    print("\n5️⃣  Testing Query Detection...")

    # Create a minimal mock service for testing instance methods
    class MockService(VisualSearchService):
        def __init__(self):
            # Skip parent __init__ — we just need the methods
            pass

    mock = MockService()

    assert mock._detect_pdf_in_query("Show me the catalog pdf") == True
    assert mock._detect_pdf_in_query("What scissors do you have") == False
    print("   ✅ PDF detection")

    assert mock._detect_video_in_query("Show me a demo video") == True
    assert mock._detect_video_in_query("Find forceps") == False
    print("   ✅ Video detection")

    # ═══════════════════════════════════════════════════════════
    # 6. Test Response Enrichment
    # ═══════════════════════════════════════════════════════════
    print("\n6️⃣  Testing Response Enrichment...")

    response = {
        "start_message": "Yes, we certainly have this product!",
        "core_message": {"product": [], "options": ["Yes", "No"]},
        "end_message": None,
        "more_prompt": None
    }

    enriched = mock._enrich_response(
        response.copy(),
        catalog_url="https://example.com/catalog.pdf",
        has_pdf_request=True,
        has_video_request=False
    )
    assert "catalog.pdf" in enriched["start_message"]
    print("   ✅ PDF link inserted into start_message")

    enriched = mock._enrich_response(
        response.copy(),
        catalog_url=None,
        has_pdf_request=False,
        has_video_request=True
    )
    assert "videos" in (enriched.get("more_prompt") or "").lower()
    print("   ✅ Video link added to more_prompt")

    # ═══════════════════════════════════════════════════════════
    # 7. Test JSON Field Parsing
    # ═══════════════════════════════════════════════════════════
    print("\n7️⃣  Testing JSON Field Parsing...")

    assert VisualSearchService._parse_json_field('["foo", "bar"]') == ["foo", "bar"]
    print("   ✅ JSON list string parsed")

    assert VisualSearchService._parse_json_field('{"key": "val"}') == {"key": "val"}
    print("   ✅ JSON dict string parsed")

    assert VisualSearchService._parse_json_field([1, 2, 3]) == [1, 2, 3]
    print("   ✅ Non-string passthrough")

    # ═══════════════════════════════════════════════════════════
    # 8. Test Prompt Generation
    # ═══════════════════════════════════════════════════════════
    print("\n8️⃣  Testing Prompt Generation...")

    prompt = mock._generate_prompt(
        context=[{"name": "Scissors", "similarity_score": 0.91}],
        chat_history="User: Hello",
        question="What is this instrument?"
    )
    assert "What is this instrument?" in prompt
    assert "PRODUCTS IN CONTEXT" in prompt
    assert "Scissors" in prompt
    print("   ✅ Prompt generated with context and question")

    prompt = mock._generate_prompt(
        context=[],
        chat_history="",
        question=""
    )
    assert "Identify the instrument" in prompt
    print("   ✅ Empty question defaults to identification intent")

    # ═══════════════════════════════════════════════════════════
    # 9. Test Chat History Formatting
    # ═══════════════════════════════════════════════════════════
    print("\n9️⃣  Testing Chat History Formatting...")

    from langchain_core.messages import HumanMessage, AIMessage

    messages = [
        HumanMessage(content="Hello"),
        AIMessage(content='{"start_message": "Hi there!"}')
    ]
    formatted = VisualSearchService._format_chat_history(messages)
    assert "User: Hello" in formatted
    assert "Hi there!" in formatted
    print("   ✅ Chat history formatted with JSON extraction")

    # ═══════════════════════════════════════════════════════════
    # 10. Test DI Container Wiring
    # ═══════════════════════════════════════════════════════════
    print("\n🔟  Testing DI Container Wiring...")

    from src.app.containers.app_container import AppContainer
    container = AppContainer()

    # Verify providers exist
    assert hasattr(container, "visual_search_service"), "Missing visual_search_service provider"
    print("   ✅ visual_search_service provider registered")

    assert hasattr(container, "image_query_handler"), "Missing image_query_handler provider"
    print("   ✅ image_query_handler provider registered")

    assert hasattr(container, "chat_controller"), "Missing chat_controller provider"
    print("   ✅ chat_controller provider registered")

    # ═══════════════════════════════════════════════════════════
    # 11. Test ChatController Integration
    # ═══════════════════════════════════════════════════════════
    print("\n1️⃣ 1️⃣  Testing ChatController with ImageQueryHandler...")

    from src.app.api.v1.controllers.chat.chat_controller import ChatController as CC
    from src.app.api.v1.controllers.chat.image_query_handler import ImageQueryHandler as IQH

    # Both handlers should be accepted
    # (Can't fully instantiate without real services, but verify constructor accepts it)
    import inspect
    sig = inspect.signature(CC.__init__)
    params = list(sig.parameters.keys())
    assert "text_handler" in params
    assert "image_handler" in params
    print("   ✅ ChatController accepts text_handler + image_handler")

    sig = inspect.signature(IQH.__init__)
    params = list(sig.parameters.keys())
    assert "visual_search_service" in params
    print("   ✅ ImageQueryHandler accepts visual_search_service")

    # Verify handle method is async
    assert asyncio.iscoroutinefunction(IQH.handle)
    print("   ✅ ImageQueryHandler.handle is async")

    assert asyncio.iscoroutinefunction(VisualSearchService.answer_question)
    print("   ✅ VisualSearchService.answer_question is async")

    print("\n" + "=" * 60)
    print("🎉 Layer 8 — ALL TESTS PASSED!")
    print("=" * 60)


test_layer8()
