import asyncio
import logging
import sys
import os

# Set up paths
sys.path.append(os.getcwd())

from src.app.containers.app_container import AppContainer

async def test_layer3():
    logging.basicConfig(level=logging.INFO)
    container = AppContainer()
    
    print("🔍 Testing Layer 3: Repositories...")
    
    try:
        # 1. Test UserRepository
        user_repo = container.user_repository()
        print(f"✅ UserRepository loaded: {user_repo}")
        
        # 2. Test TokenRepository
        # Note: Since redis_token_manager is a callable returning a coroutine, 
        # we need to await it before passing to TokenRepository if we want it to work correctly.
        # However, for testing the wiring:
        token_repo = container.token_repository()
        print(f"✅ TokenRepository loaded: {token_repo}")
        
        # 3. Test ChatRepository
        chat_repo = container.chat_repository()
        print(f"✅ ChatRepository loaded: {chat_repo}")
        
        # Let's try a real async call for UserRepository
        user = await user_repo.find_user_by_email("test@example.com")
        print(f"📡 DB Query Result (User): {user}")
        
    except Exception as e:
        print(f"❌ Layer 3 Test Failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_layer3())
