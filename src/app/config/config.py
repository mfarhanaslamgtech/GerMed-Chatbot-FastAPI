"""
╔══════════════════════════════════════════════════════════════════════════╗
║                    GerMed ChatBot — Config Facade                      ║
╠══════════════════════════════════════════════════════════════════════════╣
║                                                                        ║
║  🎓 WHAT YOU'RE LEARNING HERE:                                         ║
║                                                                        ║
║  This is a FACADE PATTERN — it gives a flat, convenient interface      ║
║  to the nested settings structure from settings.py.                    ║
║                                                                        ║
║  Instead of writing: settings.openai.OPENAI_API_KEY everywhere,       ║
║  you can write:      Config.OPENAI_API_KEY                             ║
║                                                                        ║
║  In the Flask version, this file looked almost identical. The key      ║
║  difference is that our settings.py now uses Pydantic (auto-validated) ║
║  instead of raw os.getenv() calls.                                     ║
║                                                                        ║
║  ⚠️ NOTE: In FastAPI, you could also skip this facade entirely         ║
║  and use Depends() to inject settings directly. We keep it here        ║
║  for compatibility with the Gervet-ChatBot architecture during         ║
║  the migration. You can refactor later.                                ║
║                                                                        ║
╚══════════════════════════════════════════════════════════════════════════╝
"""

from src.app.config.settings import settings


class Config:
    """
    Application-wide configuration loaded from validated settings.
    """

    # ── General ──────────────────────────────────────────────────
    DEBUG = settings.general.DEBUG
    HOST = settings.general.HOST
    PORT = settings.general.PORT
    BASE_URL = settings.general.BASE_URL
    BASE_UPLOAD_DIR = settings.general.BASE_UPLOAD_DIR
    HF_TOKEN = settings.general.HF_TOKEN

    # ── OpenAI ───────────────────────────────────────────────────
    OPENAI_API_KEY = settings.openai.OPENAI_API_KEY
    MODEL_NAME = settings.openai.MODEL_NAME
    OPENAI_TEMPERATURE = settings.openai.OPENAI_TEMPERATURE
    MAX_TOKENS = settings.openai.MAX_TOKENS
    REQUEST_TIMEOUT = settings.openai.REQUEST_TIMEOUT

    # ── Pinecone ─────────────────────────────────────────────────
    PINECONE_API_KEY = settings.pinecone.PINECONE_API_KEY
    PINECONE_INDEX_NAME = settings.pinecone.PINECONE_INDEX_NAME
    PINECONE_NAMESPACE = settings.pinecone.PINECONE_NAMESPACE

    # ── Redis (4 instances) ──────────────────────────────────────
    TEXT_REDIS_HOST = settings.redis.TEXT_REDIS_HOST
    TEXT_REDIS_PORT = settings.redis.TEXT_REDIS_PORT
    TEXT_REDIS_PASSWORD = settings.redis.TEXT_REDIS_PASSWORD
    TEXT_REDIS_DB = settings.redis.TEXT_REDIS_DB

    IMAGE_REDIS_HOST = settings.redis.IMAGE_REDIS_HOST
    IMAGE_REDIS_PORT = settings.redis.IMAGE_REDIS_PORT
    IMAGE_REDIS_PASSWORD = settings.redis.IMAGE_REDIS_PASSWORD
    IMAGE_REDIS_DB = settings.redis.IMAGE_REDIS_DB

    RATE_LIMIT_REDIS_HOST = settings.redis.RATE_LIMIT_REDIS_HOST
    RATE_LIMIT_REDIS_PORT = settings.redis.RATE_LIMIT_REDIS_PORT
    RATE_LIMIT_REDIS_PASSWORD = settings.redis.RATE_LIMIT_REDIS_PASSWORD
    RATE_LIMIT_REDIS_DB = settings.redis.RATE_LIMIT_REDIS_DB

    TOKEN_REDIS_HOST = settings.redis.TOKEN_REDIS_HOST
    TOKEN_REDIS_PORT = settings.redis.TOKEN_REDIS_PORT
    TOKEN_REDIS_PASSWORD = settings.redis.TOKEN_REDIS_PASSWORD
    TOKEN_REDIS_DB = settings.redis.TOKEN_REDIS_DB

    # ── MongoDB ──────────────────────────────────────────────────
    MONGO_URI = settings.mongodb.MONGO_URI
    MONGO_DB_NAME = settings.mongodb.MONGODB_DATABASE
    MONGO_MAX_POOL_SIZE = settings.mongodb.MONGODB_MAX_POOL_SIZE
    MONGO_MIN_POOL_SIZE = settings.mongodb.MONGODB_MIN_POOL_SIZE
    MONGO_CONNECT_TIMEOUT_MS = settings.mongodb.MONGODB_CONNECT_TIMEOUT
    MONGO_SERVER_SELECTION_TIMEOUT_MS = settings.mongodb.MONGODB_SERVER_SELECTION_TIMEOUT

    # ── Security ─────────────────────────────────────────────────
    JWT_SECRET_KEY = settings.security.JWT_SECRET_KEY
    ACCESS_TOKEN_EXPIRY_VALUE = settings.security.ACCESS_TOKEN_EXPIRY_VALUE
    ACCESS_TOKEN_EXPIRY_UNIT = settings.security.ACCESS_TOKEN_EXPIRY_UNIT
    REFRESH_TOKEN_EXPIRY_VALUE = settings.security.REFRESH_TOKEN_EXPIRY_VALUE
    REFRESH_TOKEN_EXPIRY_UNIT = settings.security.REFRESH_TOKEN_EXPIRY_UNIT

    # ── Rate Limit ───────────────────────────────────────────────
    RATE_LIMIT = settings.ratelimit.RATE_LIMIT
    TIME_WINDOW = settings.ratelimit.TIME_WINDOW

    # ── Embedding Models ─────────────────────────────────────────
    IMAGE_EMBEDDING_MODEL_NAME = settings.embedding_models.IMAGE_EMBEDDING_MODEL
    SIMILARITY_THRESHOLD = settings.embedding_models.SIMILARITY_THRESHOLD
    CLIP_TOP_K = settings.embedding_models.CLIP_TOP_K
    OPENAI_EMBEDDING_MODEL = settings.embedding_models.OPENAI_EMBEDDING_MODEL
    TRANSFORMERS_EMBEDDING_MODEL = settings.embedding_models.TRANSFORMERS_EMBEDDING_MODEL
