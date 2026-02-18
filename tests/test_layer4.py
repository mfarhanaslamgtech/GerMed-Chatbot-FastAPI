import asyncio
import logging
import sys
import os

# Set up paths
sys.path.append(os.getcwd())

from src.app.containers.app_container import AppContainer

async def test_layer4():
    logging.basicConfig(level=logging.INFO)
    container = AppContainer()
    
    print("🔍 Testing Layer 4: Controllers & Handlers...")
    
    try:
        # 1. Get ChatController from DI
        chat_controller = container.chat_controller()
        print(f"✅ ChatController loaded: {chat_controller}")
        
        # 2. Mock a basic chat request
        print("📡 Simulating Chat Request...")
        response = await chat_controller.process_chat(
            user_id="user_123",
            user_email="test@example.com",
            question="Find surgical scissors"
        )
        
        print(f"🎉 Controller Response: {response}")
        
        # Verify the structure matches our expectations
        assert "message" in response
        assert "data" in response
        print("✅ Response structure verified!")

    except Exception as e:
        print(f"❌ Layer 4 Test Failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_layer4())
