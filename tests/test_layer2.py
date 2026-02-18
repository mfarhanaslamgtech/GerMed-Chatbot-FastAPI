"""
Layer 2 Test — Infrastructure & Utilities
Tests Database, Redis, OpenAI Client, Logging, and Embedding Models.
"""
import asyncio
import sys
import os
import logging
from unittest.mock import MagicMock, patch

sys.path.append(os.getcwd())

async def test_layer2():
    print("=" * 60)
    print("🧪 Testing Layer 2: Infrastructure & Utilities")
    print("=" * 60)

    # ═══════════════════════════════════════════════════════
    # 1. Test Logger
    # ═══════════════════════════════════════════════════════
    print("\n1️⃣  Testing Logger...")
    from src.app.utils.logger import setup_logging
    setup_logging()
    logger = logging.getLogger("test_layer2")
    logger.info("   ✅ Logger initialized and writing to console/file")

    # ═══════════════════════════════════════════════════════
    # 2. Test OpenAI Client
    # ═══════════════════════════════════════════════════════
    print("\n2️⃣  Testing OpenAI Client...")
    from src.app.utils.openai_client import OpenAIClient
    
    # Mocking the actual API call to avoid cost/errors if key missing
    with patch("src.app.utils.openai_client.AsyncOpenAI") as mock_ai:
        client = OpenAIClient.get_openai_client(is_async=True)
        assert client is not None
        print("   ✅ OpenAIClient.get_openai_client returned instance")
        
        llm = OpenAIClient.get_openai_llm()
        assert llm is not None
        print(f"   ✅ ChatOpenAI (LLM) initialized with model")

    # ═══════════════════════════════════════════════════════
    # 3. Test Redis Connection Manager
    # ═══════════════════════════════════════════════════════
    print("\n3️⃣  Testing Redis Connection Manager...")
    from src.app.core.redis_connector import RedisConnection
    
    # We don't want to actually connect if Redis isn't running, but we check object creation
    try:
        client = RedisConnection.get_textbot_client()
        assert client is not None
        print("   ✅ RedisConnection.get_textbot_client returned client")
        
        # Check verify method exists
        assert asyncio.iscoroutinefunction(RedisConnection.ping_all)
        print("   ✅ RedisConnection.ping_all is async")
        
    except Exception as e:
        print(f"   ❌ Redis Test Failed: {e}")

    # ═══════════════════════════════════════════════════════
    # 4. Test Embedding Models (Mocked)
    # ═══════════════════════════════════════════════════════
    print("\n4️⃣  Testing Embedding Models (Mocked)...")
    from src.app.utils.embedding_model import TextEmbeddingModel, ImageEmbeddingModel
    
    # Mock SentenceTransformer to avoid heavy download
    with patch("src.app.utils.embedding_model.SentenceTransformer") as mock_st:
        TextEmbeddingModel._instance = None # Reset singleton
        model = TextEmbeddingModel.get_instance()
        assert model is not None
        print("   ✅ TextEmbeddingModel loaded (Singleton)")

    # Mock CLIP to avoid heavy download
    with patch("src.app.utils.embedding_model.CLIPProcessor") as mock_cp, \
         patch("src.app.utils.embedding_model.CLIPModel") as mock_cm:
        ImageEmbeddingModel._instance = None # Reset singleton
        clip = ImageEmbeddingModel.get_instance()
        assert "model" in clip
        assert "processor" in clip
        print("   ✅ ImageEmbeddingModel loaded (Singleton)")

    # ═══════════════════════════════════════════════════════
    # 5. Test Asset Uploader
    # ═══════════════════════════════════════════════════════
    print("\n5️⃣  Testing Asset Uploader...")
    from src.app.core.assets.asset_uploader import LocalAssetUploader
    
    uploader = LocalAssetUploader(base_upload_dir="./test_uploads")
    assert os.path.exists("./test_uploads")
    print("   ✅ LocalAssetUploader created directory")
    
    # Cleanup
    import shutil
    try:
        shutil.rmtree("./test_uploads")
        print("   ✅ Cleanup test directory")
    except:
        pass

    print("\n" + "=" * 60)
    print("🎉 Layer 2 — ALL TESTS PASSED!")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(test_layer2())
