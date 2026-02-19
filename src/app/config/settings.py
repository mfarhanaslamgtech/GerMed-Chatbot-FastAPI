"""
╔══════════════════════════════════════════════════════════════════════════╗
║                    GerMed ChatBot — Settings (FastAPI)                  ║
╠══════════════════════════════════════════════════════════════════════════╣
║                                                                        ║
║  🎓 WHAT YOU'RE LEARNING HERE:                                         ║
║                                                                        ║
║  In the Gervet-ChatBot (Flask version), settings used Python's          ║
║  @dataclass + manual os.getenv() calls. Every field had to manually:   ║
║   1. Call os.getenv("VAR_NAME")                                        ║
║   2. Cast the type: int(os.getenv(...)), float(os.getenv(...))         ║
║   3. Validate that required vars aren't None (custom _validate())      ║
║                                                                        ║
║  In FastAPI, we use Pydantic's BaseSettings which gives us:            ║
║   ✅ Automatic .env file loading (no manual load_dotenv() needed)      ║
║   ✅ Automatic type casting (str → int, str → float, etc.)             ║
║   ✅ Automatic validation (required fields raise clear errors)          ║
║   ✅ Type safety enforced by Pydantic validators                        ║
║   ✅ IDE autocomplete on all config values                              ║
║                                                                        ║
║  Flask version:  DEBUG: bool = bool(strtobool(os.getenv('DEBUG',...))) ║
║  FastAPI version: DEBUG: bool = False  ← That's it! Pydantic handles  ║
║                                          env loading + type casting.   ║
║                                                                        ║
╚══════════════════════════════════════════════════════════════════════════╝
"""

from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field
from typing import Optional


# ─── Settings Sections ──────────────────────────────────────────────────
# Each group inherits from Pydantic's BaseSettings instead of a custom @dataclass.
# KEY DIFFERENCE: In Pydantic BaseSettings, field names automatically map to environment variable names. So: OPENAI_API_KEY: str automatically reads os.environ["OPENAI_API_KEY"] — no os.getenv() needed!


class GeneralSettings(BaseSettings):
    """
    General application settings.
    """
    DEBUG: bool = False
    HOST: str = "0.0.0.0"
    PORT: int = 8000                   # ← FastAPI convention is 8000, not 5000
    BASE_URL: str = "http://localhost:8000/v1/assets/public"
    BASE_UPLOAD_DIR: str = "./uploads"
    ALLOWED_ORIGINS: str = "*"  # Comma-separated list of origins, e.g., "https://myapp.com,https://api.myapp.com"
    HF_TOKEN: Optional[str] = None

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


class OpenAISettings(BaseSettings):
    """
    OpenAI API configuration.

    These control the LLM behavior — temperature, token limits, timeouts.
    """
    OPENAI_API_KEY: str                # Required — no default (will fail if missing)
    MODEL_NAME: str = "gpt-4o"
    OPENAI_TEMPERATURE: float = 0.0
    MAX_TOKENS: Optional[int] = 8000
    REQUEST_TIMEOUT: Optional[int] = 600

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


class PineconeSettings(BaseSettings):
    """Pinecone vector database for FAQ embeddings."""
    PINECONE_API_KEY: str
    PINECONE_INDEX_NAME: str = "germed-faqs-index"
    PINECONE_NAMESPACE: str = "germed-faqs-namespace"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


class EmbeddingModelsSettings(BaseSettings):
    """
    Controls which embedding models are used for text and image search.

    - TRANSFORMERS_EMBEDDING_MODEL: Sentence-Transformers model for text vectors
    - IMAGE_EMBEDDING_MODEL: CLIP model for image vectors
    - SIMILARITY_THRESHOLD: Minimum cosine similarity to consider a match
    """
    IMAGE_EMBEDDING_MODEL: str = "openai/clip-vit-base-patch32"
    OPENAI_EMBEDDING_MODEL: Optional[str] = "text-embedding-3-large"
    TRANSFORMERS_EMBEDDING_MODEL: Optional[str] = "sentence-transformers/all-distilroberta-v1"
    SIMILARITY_THRESHOLD: float = 0.7
    CLIP_TOP_K: int = 5

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


class RedisSettings(BaseSettings):
    """
    Redis connection settings for 4 separate Redis instances:

    1. TEXT_REDIS_*   → Stores text embedding vectors for product search
    2. IMAGE_REDIS_*  → Stores image embedding vectors (CLIP) for visual search
    3. RATE_LIMIT_*   → Rate limiting counters per user
    4. TOKEN_*        → JWT token storage for auth (blacklist/whitelist)

    🎓 WHY 4 SEPARATE INSTANCES?
    Separation of concerns — each Redis DB serves a different domain.
    In production, these could even be separate Redis clusters for
    independent scaling.
    """
    TEXT_REDIS_HOST: str = "127.0.0.1"
    TEXT_REDIS_PORT: int = 6379
    TEXT_REDIS_PASSWORD: Optional[str] = None
    TEXT_REDIS_DB: int = 0

    IMAGE_REDIS_HOST: str = "127.0.0.1"
    IMAGE_REDIS_PORT: int = 6379
    IMAGE_REDIS_PASSWORD: Optional[str] = None
    IMAGE_REDIS_DB: int = 2

    RATE_LIMIT_REDIS_HOST: str = "127.0.0.1"
    RATE_LIMIT_REDIS_PORT: int = 6379
    RATE_LIMIT_REDIS_PASSWORD: Optional[str] = None
    RATE_LIMIT_REDIS_DB: int = 1

    TOKEN_REDIS_HOST: str = "127.0.0.1"
    TOKEN_REDIS_PORT: int = 6379
    TOKEN_REDIS_PASSWORD: Optional[str] = None
    TOKEN_REDIS_DB: int = 3

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


class MongoDBSettings(BaseSettings):
    """
    MongoDB connection configuration.

    🎓 KEY CONCEPT — Connection Pooling:
    - MAX_POOL_SIZE: Max simultaneous connections to MongoDB
    - MIN_POOL_SIZE: Connections kept alive even when idle
    - CONNECT_TIMEOUT: How long to wait for initial connection
    - SERVER_SELECTION_TIMEOUT: How long to wait to find a suitable server

    In the Gervet version (pymongo), these are sync connections.
    In our FastAPI version (Phase 2), we'll use `motor` for async connections.
    """
    MONGO_URI: str = "mongodb://localhost:27017"
    MONGODB_DATABASE: str = "germed-chatbot"
    MONGODB_MAX_POOL_SIZE: int = 100
    MONGODB_MIN_POOL_SIZE: int = 10
    MONGODB_CONNECT_TIMEOUT: int = Field(default=5000, alias="MONGODB_CONNECT_TIMEOUT")
    MONGODB_SERVER_SELECTION_TIMEOUT: int = Field(default=5000, alias="MONGODB_SERVER_SELECTION_TIMEOUT")

    model_config = SettingsConfigDict(
        env_file=".env", 
        env_file_encoding="utf-8", 
        extra="ignore", 
        populate_by_name=True
    )


class SecuritySettings(BaseSettings):
    """
    JWT and authentication configuration.

    🎓 KEY CONCEPT — Token Expiry:
    - ACCESS_TOKEN: Short-lived (e.g., 24h), used for API requests
    - REFRESH_TOKEN: Long-lived (e.g., 30 days), used to get new access tokens
    - The unit+value pattern allows flexible expiry configuration
    """
    JWT_SECRET_KEY: str                # Required — no default for security reasons
    ACCESS_TOKEN_EXPIRY_UNIT: str = "seconds"
    ACCESS_TOKEN_EXPIRY_VALUE: int = 86400       # 24 hours
    REFRESH_TOKEN_EXPIRY_UNIT: str = "seconds"
    REFRESH_TOKEN_EXPIRY_VALUE: int = 2592000    # 30 days

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


class RateLimitSettings(BaseSettings):
    """Rate limiting: Max N requests per TIME_WINDOW (in minutes)."""
    RATE_LIMIT: int = 3
    TIME_WINDOW: int = 30

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


class Settings(BaseSettings):
    """
    Root settings aggregator.
    In FastAPI, we just instantiate Settings() — Pydantic handles everything.
    """
    general: GeneralSettings = GeneralSettings()
    openai: OpenAISettings = None       # type: ignore — initialized below
    pinecone: PineconeSettings = None   # type: ignore
    redis: RedisSettings = RedisSettings()
    mongodb: MongoDBSettings = MongoDBSettings()
    security: SecuritySettings = None   # type: ignore
    ratelimit: RateLimitSettings = RateLimitSettings()
    embedding_models: EmbeddingModelsSettings = EmbeddingModelsSettings()

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    def __init__(self, **kwargs):
        # Initialize sub-settings that require env vars
        super().__init__(
            general=GeneralSettings(),
            openai=OpenAISettings(),
            pinecone=PineconeSettings(),
            redis=RedisSettings(),
            mongodb=MongoDBSettings(),
            security=SecuritySettings(),
            ratelimit=RateLimitSettings(),
            embedding_models=EmbeddingModelsSettings(),
            **kwargs
        )


# ─── Singleton Instance ────────────────────────────────────────────────
# Loaded once at import time, just like the Flask version.
# If any required env var is missing, Pydantic raises a clear
# ValidationError at startup — fail fast!

import logging

try:
    settings = Settings()
    logging.info("✅ All settings loaded successfully.")
except Exception as e:
    logging.critical(f"❌ Startup failed due to missing settings: {e}")
    raise
