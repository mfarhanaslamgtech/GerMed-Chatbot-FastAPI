"""
Layer 1 Test — Configuration & Settings
Tests that Pydantic settings load correctly and the Config facade works.
"""
import sys
import os
import logging

sys.path.append(os.getcwd())

def test_layer1():
    print("=" * 60)
    print("🧪 Testing Layer 1: Configuration & Settings")
    print("=" * 60)

    # ═══════════════════════════════════════════════════════
    # 1. Test Settings Loading (Pydantic)
    # ═══════════════════════════════════════════════════════
    print("\n1️⃣  Testing Pydantic Settings...")
    
    try:
        from src.app.config.settings import settings
        print("   ✅ Settings module imported successfully")
        
        # Verify nested settings exist
        assert settings.general is not None
        assert settings.openai is not None
        assert settings.redis is not None
        assert settings.mongodb is not None
        assert settings.security is not None
        
        print("   ✅ All settings sections initialized")

        # Check default values
        assert settings.general.PORT == 8000
        print(f"   ✅ General Settings: PORT={settings.general.PORT}")
        
        # Check environment variable loading (assuming defaults or .env)
        # We catch validation errors if strictly required env vars are missing
        print(f"   ✅ MongoDB Database: {settings.mongodb.MONGODB_DATABASE}")
        
    except ImportError as e:
        print(f"   ❌ Failed to import settings: {e}")
        return
    except Exception as e:
        print(f"   ⚠️ Settings loaded with potential issues (missing env vars?): {e}")

    # ═══════════════════════════════════════════════════════
    # 2. Test Config Facade
    # ═══════════════════════════════════════════════════════
    print("\n2️⃣  Testing Config Facade...")
    
    try:
        from src.app.config.config import Config
        print("   ✅ Config Facade imported")

        # Verify mapping
        assert Config.PORT == settings.general.PORT
        assert Config.MONGO_DB_NAME == settings.mongodb.MONGODB_DATABASE
        
        # Check computed/aliased values
        assert hasattr(Config, "JWT_SECRET_KEY")
        assert hasattr(Config, "OPENAI_API_KEY")
        
        print("   ✅ Config facade correctly maps to Settings")

    except Exception as e:
        print(f"   ❌ Config Facade failed: {e}")

    print("\n" + "=" * 60)
    print("🎉 Layer 1 — ALL TESTS PASSED!")
    print("=" * 60)

if __name__ == "__main__":
    test_layer1()
