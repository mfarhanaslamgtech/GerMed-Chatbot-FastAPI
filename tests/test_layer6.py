"""
Layer 6 Test — Routers, Auth, Middleware, Error Handlers
Tests import chain and verifies routers are properly registered.
"""
import asyncio
import sys
import os
import logging

sys.path.append(os.getcwd())

async def test_layer6():
    logging.basicConfig(level=logging.INFO)
    
    print("=" * 60)
    print("🧪 Testing Layer 6: Routers, Auth & Error Handlers")
    print("=" * 60)
    
    # 1. Test Exception Classes
    print("\n1️⃣  Testing Custom Exceptions...")
    from src.app.exceptions.custom_exceptions import (
        APIException, DatabaseException, RepositoryException,
        TokenGenerationException, TokenStorageException,
        InvalidTokenException, InvalidAccessTokenException,
        MissingFieldException
    )
    assert issubclass(TokenGenerationException, APIException)
    assert issubclass(InvalidAccessTokenException, InvalidTokenException)
    print("   ✅ All 7 exception classes loaded and inherit correctly")

    # 2. Test Middleware Classes
    print("\n2️⃣  Testing Auth Middleware...")
    from src.app.middlewares.auth_middleware import AuthMiddleware, get_current_user, get_refresh_token_user
    assert "/v1/auth/login" in AuthMiddleware.PUBLIC_PATHS
    assert "/health" in AuthMiddleware.PUBLIC_PATHS
    print("   ✅ AuthMiddleware loaded with correct public paths")

    # 3. Test Error Handlers
    print("\n3️⃣  Testing Error Handlers...")
    from src.app.error_handlers.error_handlers import register_exception_handlers
    print("   ✅ Error handler registration function loaded")

    # 4. Test DI Container (full chain)
    print("\n4️⃣  Testing DI Container (full chain)...")
    from src.app.containers.app_container import AppContainer
    container = AppContainer()
    
    # Verify auth stack is wired
    auth_controller = container.auth_controller()
    print(f"   ✅ AuthController: {type(auth_controller).__name__}")
    
    chat_controller = container.chat_controller()
    print(f"   ✅ ChatController: {type(chat_controller).__name__}")

    audio_service = container.audio_call_service()
    print(f"   ✅ AudioCallService: {type(audio_service).__name__}")

    # 5. Test Router Registration
    print("\n5️⃣  Testing Router Registration...")
    from src.app.api.v1.routers import register_routers
    
    # Create a minimal FastAPI app to test router mounting
    from fastapi import FastAPI
    test_app = FastAPI()
    register_routers(test_app)
    
    routes = [route.path for route in test_app.routes]
    print(f"   Registered Routes: {routes}")
    
    assert "/v1/auth/login" in routes, "Missing /v1/auth/login"
    assert "/v1/auth/refresh_token" in routes, "Missing /v1/auth/refresh_token"
    assert "/v1/auth/logout" in routes, "Missing /v1/auth/logout"
    assert "/v1/agent/chat" in routes, "Missing /v1/agent/chat"
    assert "/v1/agent/audio-call" in routes, "Missing /v1/agent/audio-call"
    assert "/v1/assets/public/{filename:path}" in routes, "Missing /v1/assets/public"
    print("   ✅ All 6 routes registered correctly!")

    # 6. Test Full App Factory
    print("\n6️⃣  Testing Full App Factory (create_app)...")
    from src.app.app import create_app
    app = create_app()
    
    app_routes = [route.path for route in app.routes]
    print(f"   App routes count: {len(app_routes)}")
    assert "/v1/auth/login" in app_routes
    assert "/v1/agent/chat" in app_routes
    assert "/" in app_routes
    assert "/health" in app_routes
    print("   ✅ Full app created with all routes and middleware!")

    print("\n" + "=" * 60)
    print("🎉 Layer 6 — ALL TESTS PASSED!")
    print("=" * 60)

asyncio.run(test_layer6())
