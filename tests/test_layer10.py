"""
Layer 10 Test — Twilio Controller & Router
Tests the async TwilioController and router registration.
"""
import asyncio
import sys
import os
import inspect

sys.path.append(os.getcwd())


async def test_layer10():
    print("=" * 60)
    print("🧪 Testing Layer 10: Twilio Controller & Router")
    print("=" * 60)

    # ═══════════════════════════════════════════════════════
    # 1. Test Imports
    # ═══════════════════════════════════════════════════════
    print("\n1️⃣  Testing Imports...")

    from src.app.api.v1.controllers.twilio.twilio_controller import TwilioController
    print("   ✅ TwilioController imported")

    from src.app.api.v1.routers.twilio_router import router as twilio_router
    print("   ✅ twilio_router imported")

    # ═══════════════════════════════════════════════════════
    # 2. Test TwilioController Structure
    # ═══════════════════════════════════════════════════════
    print("\n2️⃣  Testing TwilioController Structure...")

    # Constructor
    sig = inspect.signature(TwilioController.__init__)
    params = list(sig.parameters.keys())
    assert "audio_call_service" in params
    print("   ✅ Constructor accepts audio_call_service")

    # handle_twilio_call is async
    assert asyncio.iscoroutinefunction(TwilioController.handle_twilio_call)
    print("   ✅ handle_twilio_call is async")

    # Verify method signature
    sig = inspect.signature(TwilioController.handle_twilio_call)
    params = list(sig.parameters.keys())
    assert "user_id" in params
    assert "user_email" in params
    assert "form_data" in params
    assert "history" in params
    print(f"   ✅ handle_twilio_call params: {params}")

    # ═══════════════════════════════════════════════════════
    # 3. Test TwilioController with Mock Service
    # ═══════════════════════════════════════════════════════
    print("\n3️⃣  Testing TwilioController with Mock...")

    class MockAudioCallService:
        async def answer_question(self, user_id, user_email, question, history=None):
            return f"Mock answer for: {question}"

    controller = TwilioController(audio_call_service=MockAudioCallService())

    # Valid call
    result = await controller.handle_twilio_call(
        user_id="test_user",
        user_email="test@example.com",
        form_data={"question": "What scissors do you have?"},
        history=[]
    )
    assert result["message"] == "Audio call processed successfully"
    assert "Mock answer" in result["data"]["answer"]
    print(f"   ✅ Valid call → {result['data']['answer']}")

    # Invalid call (missing question)
    from src.app.exceptions.custom_exceptions import MissingFieldException
    try:
        await controller.handle_twilio_call(
            user_id="test_user",
            user_email="test@example.com",
            form_data={},
            history=[]
        )
        assert False, "Should have raised"
    except MissingFieldException:
        print("   ✅ Missing question → MissingFieldException raised")

    # Invalid call (non-string question)
    from src.app.exceptions.custom_exceptions import InvalidQuestionTypeException
    try:
        await controller.handle_twilio_call(
            user_id="test_user",
            user_email="test@example.com",
            form_data={"question": 12345},
            history=[]
        )
        assert False, "Should have raised"
    except InvalidQuestionTypeException:
        print("   ✅ Non-string question → InvalidQuestionTypeException raised")

    # ═══════════════════════════════════════════════════════
    # 4. Test Router Configuration
    # ═══════════════════════════════════════════════════════
    print("\n4️⃣  Testing Router Configuration...")

    # Check route exists
    routes = [r.path for r in twilio_router.routes]
    assert "/twilio-call" in routes
    print(f"   ✅ Route /twilio-call registered")

    # Check it's a POST route
    for route in twilio_router.routes:
        if hasattr(route, "path") and route.path == "/twilio-call":
            assert "POST" in route.methods
            print(f"   ✅ Method: POST")

            # Check handler is async
            assert asyncio.iscoroutinefunction(route.endpoint)
            print(f"   ✅ Endpoint is async: {route.endpoint.__name__}")
            break

    # ═══════════════════════════════════════════════════════
    # 5. Test Router Registration
    # ═══════════════════════════════════════════════════════
    print("\n5️⃣  Testing Router Registration...")

    from src.app.api.v1.routers import register_routers
    from fastapi import FastAPI

    test_app = FastAPI()
    register_routers(test_app)

    all_routes = [r.path for r in test_app.routes]
    assert "/v1/agent/twilio-call" in all_routes
    print(f"   ✅ /v1/agent/twilio-call registered in app")

    # Verify all other routes are still there
    assert "/v1/auth/signup" in all_routes or any("/v1/auth" in r for r in all_routes)
    print(f"   ✅ Auth routes still registered")

    assert "/v1/agent/audio-call" in all_routes
    print(f"   ✅ Audio call route still registered")

    # ═══════════════════════════════════════════════════════
    # 6. Test Complete Route List
    # ═══════════════════════════════════════════════════════
    print("\n6️⃣  All Registered Routes:")

    api_routes = [r.path for r in test_app.routes if hasattr(r, "methods")]
    for route in sorted(api_routes):
        print(f"   📍 {route}")

    print(f"\n   Total API routes: {len(api_routes)}")

    print("\n" + "=" * 60)
    print("🎉 Layer 10 — ALL TESTS PASSED!")
    print("=" * 60)
    print("\n🏁 ALL 10 LAYERS MIGRATED SUCCESSFULLY! 🏁")


asyncio.run(test_layer10())
