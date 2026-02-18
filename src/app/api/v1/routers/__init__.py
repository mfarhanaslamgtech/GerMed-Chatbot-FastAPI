from fastapi import FastAPI
from src.app.api.v1.routers.auth_router import router as auth_router
from src.app.api.v1.routers.chat_router import router as chat_router
from src.app.api.v1.routers.asset_router import router as asset_router
from src.app.api.v1.routers.audio_call_router import router as audio_call_router
from src.app.api.v1.routers.twilio_router import router as twilio_router


def register_routers(app: FastAPI):
    """
    Register all API routers with the FastAPI application.
    
    🎓 COMPARISON:
    Flask:   register_blueprints(app) → app.register_blueprint(bp, url_prefix="/v1/auth")
    FastAPI: register_routers(app) → app.include_router(router, prefix="/v1/auth")
    
    Same concept, different name. Routers are FastAPI's version of Blueprints.
    """
    app.include_router(auth_router, prefix="/v1/auth", tags=["Authentication"])
    app.include_router(chat_router, prefix="/v1/agent", tags=["Chatbot"])
    app.include_router(asset_router, prefix="/v1/assets", tags=["Assets"])
    app.include_router(audio_call_router, prefix="/v1/agent", tags=["Audio Call"])
    app.include_router(twilio_router, prefix="/v1/agent", tags=["Twilio Call"])

