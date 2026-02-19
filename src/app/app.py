"""
╔══════════════════════════════════════════════════════════════════════════╗
║                GerMed ChatBot — Application Factory (FastAPI)           ║
╠══════════════════════════════════════════════════════════════════════════╣
║                                                                        ║
║  🎓 WHAT YOU'RE LEARNING HERE:                                         ║
║                                                                        ║
║  THE FACTORY PATTERN:                                                  ║
║  Both Flask and FastAPI use a function called create_app() that builds ║
║  and configures the entire application. This is critical because:      ║
║   1. It keeps configuration centralized in one place                   ║
║   2. It allows creating multiple app instances (e.g., for testing)     ║
║   3. It controls initialization order (config → DB → routes → start)  ║
║                                                                        ║
║  KEY DIFFERENCES FROM FLASK:                                           ║
║                                                                        ║
║  ┌─────────── Flask ────────────┐    ┌──────── FastAPI ────────────┐   ║
║  │ app = Flask(__name__)        │    │ app = FastAPI(...)          │   ║
║  │ CORS(app)                    │    │ CORSMiddleware              │   ║
║  │ JWTManager(app)              │    │ Custom Depends() (Phase 6)  │   ║
║  │ container = AppContainer()   │    │ Depends() chains (Phase 7)  │   ║
║  │ register_blueprints(app)     │    │ app.include_router(...)     │   ║
║  │ @app.before_request          │    │ Middleware class / Depends() │   ║
║  │ register_error_handlers(app) │    │ @app.exception_handler(...)  │   ║
║  │ app.run(host, port)          │    │ uvicorn.run(app, host, port) │   ║
║  └──────────────────────────────┘    └─────────────────────────────┘   ║
║                                                                        ║
║  LIFESPAN EVENTS (NEW concept in FastAPI):                             ║
║  Instead of @app.before_first_request, FastAPI uses a "lifespan"       ║
║  context manager that runs code:                                       ║
║   - BEFORE the app starts accepting requests (startup)                 ║
║   - AFTER the app stops (shutdown / cleanup)                           ║
║  This is where you'll initialize DB connections, load ML models, etc.  ║
║                                                                        ║
╚══════════════════════════════════════════════════════════════════════════╝
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv, find_dotenv
import logging

from src.app.config.config import Config
from src.app.config.settings import settings
from src.app.utils.logger import setup_logging
from src.app.core.redis_connector import RedisConnection
from src.app.middlewares.auth_middleware import AuthMiddleware


# ─── Lifespan Context Manager ──────────────────────────────────────────
#
# 🎓 This is how FastAPI handles startup and shutdown events.
#
# In Flask, you'd do setup inside create_app() directly.
# In FastAPI, you use an async context manager:
#   - Code BEFORE `yield` runs on startup
#   - Code AFTER `yield` runs on shutdown
#
# This is cleaner because it guarantees cleanup happens, even if the
# app crashes (like Python's `with` statement for files).

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager.
    
    Startup: Initialize DB connections, load ML models, start schedulers
    Shutdown: Close connections, stop schedulers, cleanup resources
    """
    logger = logging.getLogger(__name__)
    
    # ═══════ STARTUP ═══════
    logger.info("🚀 GerMed ChatBot starting up...")
    
    # 📝 Infrastructure Startup (Layer 2 & 3)
    try:
        # 1. Initialize MongoDB (via DI Container — Singleton)
        container = app.container
        db = container.database()
        # Verify connection with a ping (catches auth failures early)
        try:
            await db.client.admin.command('ping')
            logger.info("✅ MongoDB Connection initialized and verified.")
        except Exception as mongo_err:
            logger.error(f"❌ MongoDB ping failed: {mongo_err}")
            from src.app.config.settings import settings
            logger.error(f"   MONGO_URI: {settings.mongodb.MONGO_URI}")
            raise

        # 3. Initialize & Verify All Redis Connections (FAST)
        # 🎓 We do this early so the logs show connectivity immediately.
        container.redis_textbot()
        container.redis_imagebot()
        container.redis_rate_limit()
        container.redis_token_manager()

        await RedisConnection.ping_all()
        logger.info("✅ All Redis connections verified.")

        # 4. Pre-load AI Models & Vector Store (HEAVY)
        logger.info("💾 Loading AI Models (CLIP, SentenceTransformer)...")
        container.text_embedding_model()
        container.image_embedding_model()
        
        logger.info("📡 Initializing Vector Store (Pinecone) & AI Clients...")
        container.vector_store()
        container.openai_client()
        container.openai_llm()

        # 5. Ensure Database Indexes (Async)
        await container.chat_repository().ensure_indexes()
        await container.user_repository().ensure_unique_email_index()

        # 4. Background Catalog Sync (Layer 9)
        import asyncio
        try:
            catalog_service = container.catalog_service()
            asyncio.create_task(catalog_service.fetch_catalogs_and_products())
            logger.info("📦 Catalog sync started in background.")
            
            # Embeddings Sync (Layer 9 - Background Task)
            sync_manager = container.embeddings_sync_manager()
            asyncio.create_task(sync_manager.run_sync_task())
            logger.info("🧠 Embeddings sync started in background.")
        except Exception as e:
            logger.warning(f"⚠️ Initial sync tasks skipped: {e}")
        
    except Exception as e:
        logger.critical(f"❌ Startup Failed: {e}")
        # In production, you might want to stop the app here
        # raise e
    
    logger.info("✅ GerMed ChatBot is ready to accept requests!")
    
    yield  # ← App runs here, serving requests
    
    # ═════ SHUTDOWN ═════
    logger.info("🛑 GerMed ChatBot shutting down...")
    
    # 📝 Cleanup Resources
    try:
        container = app.container
        
        await RedisConnection.close_all()
        await container.database().close()
        
        logger.info("👋 GerMed ChatBot shutdown complete.")
    except Exception as e:
        logger.error(f"⚠️ Error during shutdown cleanup: {e}")


# ─── Application Factory ───────────────────────────────────────────────

def create_app() -> FastAPI:
    """
    Application factory — creates and configures the FastAPI application.
    
    🎓 COMPARISON:
    
    Flask version (Gervet-ChatBot):
        app = Flask(__name__)
        app.config.from_object(Config)
        CORS(app)
        JWTManager(app)
        container = AppContainer()
        register_error_handlers(app)
        register_blueprints(app)
        return app
    
    FastAPI version (GerMed-ChatBot):
        app = FastAPI(title=..., lifespan=lifespan)
        app.add_middleware(CORSMiddleware, ...)
        # No JWTManager needed — we'll use Depends() in Phase 6
        # No DI container needed — we'll use Depends() in Phase 7
        # register_routers(app)  ← Phase 8
        return app
    """
    # Load environment variables
    load_dotenv(find_dotenv())
    setup_logging()

    logger = logging.getLogger(__name__)

    # ── Create the FastAPI application ──────────────────────────
    #
    # 🎓 FastAPI() accepts metadata that generates the OpenAPI docs
    #    automatically. Flask has no equivalent — you'd need Flask-Swagger.
    #
    #    Visit http://localhost:8000/docs after starting the server!

    app = FastAPI(
        title="GerMed ChatBot API",
        description=(
            "AI-powered chatbot API for GerMed — featuring text search, "
            "visual search (CLIP), FAQ answering (RAG), and audio call support."
        ),
        version="1.0.0",
        lifespan=lifespan,
        docs_url="/docs",              # Swagger UI (Flask had none by default)
        redoc_url="/redoc",            # ReDoc alternative docs
    )

    # ── CORS Middleware ─────────────────────────────────────────
    #
    # 🎓 Production Security:
    #    We parse the ALLOWED_ORIGINS string into a list.
    #    If wildcard "*" is present, we allow all (DEV mode).
    #    Otherwise, we strictly allow only the listed domains.

    origins_list = [origin.strip() for origin in settings.general.ALLOWED_ORIGINS.split(",")]

    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ── Root Route ──────────────────────────────────────────────
    #
    # 🎓 Flask version:  @app.route('/')
    #    FastAPI version: @app.get('/')
    #
    #    Notice: FastAPI uses @app.get() / @app.post() instead of
    #    @app.route(). The HTTP method is explicit in the decorator.

    @app.get("/", tags=["Health"])
    async def root():
        """Health check / welcome endpoint."""
        return {
            "message": "Welcome to GerMed ChatBot API!",
            "docs": "/docs",
            "status": "healthy"
        }

    @app.get("/health", tags=["Health"])
    async def health_check():
        """Detailed health check endpoint."""
        return {
            "status": "healthy",
            "service": "GerMed ChatBot API",
            "version": "1.0.0",
        }

    # ── Register Routers ────────────────────────────────────────
    from src.app.api.v1.routers import register_routers
    register_routers(app)

    # ── Register Error Handlers ─────────────────────────────────
    from src.app.error_handlers.error_handlers import register_exception_handlers
    register_exception_handlers(app)

    # ── Auth Middleware ──────────────────────────────────────────
    # 🎓 NOTE: Middleware is added AFTER routers so it wraps all routes.
    app.add_middleware(AuthMiddleware)

    # ─── Dependency Injection Container ───────────────────────────
    from src.app.containers.app_container import AppContainer
    container = AppContainer()
    
    # Wire the container to the routers so @inject works
    container.wire(modules=[
        "src.app.api.v1.routers.auth_router",
        "src.app.api.v1.routers.chat_router",
        "src.app.api.v1.routers.audio_call_router",
        "src.app.api.v1.routers.asset_router",
        "src.app.api.v1.routers.twilio_router",
    ])
    
    # Store container in app state so lifespan can access it
    app.container = container

    logger.info(f"🏗️  GerMed ChatBot app created (debug={Config.DEBUG})")
    return app

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("src.app.app:create_app", host="0.0.0.0", port=8000, reload=True)
