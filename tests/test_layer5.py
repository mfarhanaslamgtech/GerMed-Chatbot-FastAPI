"""
Layer 5 Test — Services
Tests the Business Logic Layer (Auth, FAQ, TextSearch, Geo, Classification).
"""
import asyncio
import sys
import os
import logging
from unittest.mock import MagicMock, AsyncMock

sys.path.append(os.getcwd())

async def test_layer5():
    print("=" * 60)
    print("🧪 Testing Layer 5: Services (Business Logic)")
    print("=" * 60)

    # ═══════════════════════════════════════════════════════
    # 1. Test GeoService
    # ═══════════════════════════════════════════════════════
    print("\n1️⃣  Testing GeoService...")
    from src.app.api.v1.services.geo.geo_service import GeoService
    
    geo = GeoService()
    # Test localhost fallback
    region = await geo.get_region_from_ip("127.0.0.1")
    assert region == GeoService.DEFAULT_TIMEZONE
    print(f"   ✅ Localhost IP returns default timezone: {region}")

    # ═══════════════════════════════════════════════════════
    # 2. Test Request Classification Service
    # ═══════════════════════════════════════════════════════
    print("\n2️⃣  Testing Classification Service...")
    from src.app.api.v1.services.request_classification.request_classification_service import RequestClassificationService
    
    # Mock LLM
    mock_llm = MagicMock()
    mock_chain = AsyncMock()
    mock_chain.ainvoke.return_value.content = '{"label": "text_product_search"}'
    
    # We need to mock the prompt | llm chain
    # In the service: self.chain = self.prompt | self.llm
    # We will assume we can mock invoke on the chain
    
    service = RequestClassificationService(openai_llm=mock_llm)
    service.chain = mock_chain # Inject mock chain
    
    label = await service.classify_request("Find scissors")
    assert label == "text_product_search"
    print(f"   ✅ Classification result: {label}")

    # ═══════════════════════════════════════════════════════
    # 3. Test Auth Service (Partial)
    # ═══════════════════════════════════════════════════════
    print("\n3️⃣  Testing Auth Service (Structure)...")
    from src.app.api.v1.services.auth.auth_service import AuthService
    
    mock_token_repo = MagicMock()
    mock_user_repo = MagicMock()
    mock_geo_service = MagicMock()
    
    auth_service = AuthService(mock_token_repo, mock_user_repo, mock_geo_service)
    
    # Test token creation logic (pure python)
    access = auth_service._create_access_token("sess_123", {"role": "user"})
    assert isinstance(access, str) and len(access) > 10
    print("   ✅ Access token generated")

    refresh = auth_service._create_refresh_token("sess_123")
    assert isinstance(refresh, str) and len(refresh) > 10
    print("   ✅ Refresh token generated")

    # ═══════════════════════════════════════════════════════
    # 4. Test FAQ Service (Structure)
    # ═══════════════════════════════════════════════════════
    print("\n4️⃣  Testing FAQ Service...")
    from src.app.api.v1.services.faqs.faq_service import FaqService
    
    service = FaqService(
        vector_store=MagicMock(),
        openai_llm=MagicMock(),
        chat_repository=MagicMock()
    )
    # Verify methods exist
    assert asyncio.iscoroutinefunction(service.answer_question)
    print("   ✅ FaqService initialized correctly")

    # ═══════════════════════════════════════════════════════
    # 5. Test Text Search Service (Structure)
    # ═══════════════════════════════════════════════════════
    print("\n5️⃣  Testing Text Search Service...")
    from src.app.api.v1.services.text_search.text_search_service import TextSearchService
    
    service = TextSearchService(
        redis_client=MagicMock(),
        embedding_model=MagicMock(),
        openai_llm=MagicMock(),
        chat_repository=MagicMock()
    )
    assert asyncio.iscoroutinefunction(service.answer_question)
    print("   ✅ TextSearchService initialized correctly")

    # ═══════════════════════════════════════════════════════
    # 6. Test DI Container Wiring for Services
    # ═══════════════════════════════════════════════════════
    print("\n6️⃣  Testing Service Wiring in Container...")
    from src.app.containers.app_container import AppContainer
    container = AppContainer()
    
    assert hasattr(container, "auth_service")
    assert hasattr(container, "classification_service")
    assert hasattr(container, "faq_service")
    assert hasattr(container, "text_search_service")
    print("   ✅ All services registered in AppContainer")

    print("\n" + "=" * 60)
    print("🎉 Layer 5 — ALL TESTS PASSED!")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(test_layer5())
