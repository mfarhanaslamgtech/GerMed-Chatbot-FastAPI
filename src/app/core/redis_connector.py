import logging
import redis.asyncio as redis
from typing import Optional
from src.app.config.settings import settings

class RedisConnection:
    """ 
    Unified Asynchronous Redis Client Manager.
    
    🎓 PRO TIP:
    Creating a Redis client object is synchronous. 
    Connecting/Pinging is asynchronous. 
    By separating them, we make Dependency Injection much cleaner.
    """

    _clients = {}

    @classmethod
    def get_client(cls, host: str, port: int, password: Optional[str], db: int, label: str) -> redis.Redis:
        """Returns a singleton Redis client instance for a given config."""
        key = f"{host}:{port}:{db}"
        if key not in cls._clients:
            try:
                # client creation is sync
                client = redis.Redis(
                    host=host,
                    port=port,
                    password=password if password else None,
                    db=db,
                    decode_responses=True,
                    socket_timeout=5,
                )
                cls._clients[key] = client
                logging.info(f"🔌 Redis client created for [{label}] ({host}:{port}/{db})")
            except Exception as e:
                logging.error(f"❌ Failed to create Redis client [{label}]: {e}")
                raise
        return cls._clients[key]

    @classmethod
    def get_textbot_client(cls):
        return cls.get_client(
            host=settings.redis.TEXT_REDIS_HOST,
            port=settings.redis.TEXT_REDIS_PORT,
            password=settings.redis.TEXT_REDIS_PASSWORD,
            db=settings.redis.TEXT_REDIS_DB,
            label="TextBot"
        )

    @classmethod
    def get_imagebot_client(cls):
        return cls.get_client(
            host=settings.redis.IMAGE_REDIS_HOST,
            port=settings.redis.IMAGE_REDIS_PORT,
            password=settings.redis.IMAGE_REDIS_PASSWORD,
            db=settings.redis.IMAGE_REDIS_DB,
            label="ImageBot"
        )

    @classmethod
    def get_rate_limit_client(cls):
        return cls.get_client(
            host=settings.redis.RATE_LIMIT_REDIS_HOST,
            port=settings.redis.RATE_LIMIT_REDIS_PORT,
            password=settings.redis.RATE_LIMIT_REDIS_PASSWORD,
            db=settings.redis.RATE_LIMIT_REDIS_DB,
            label="RateLimit"
        )

    @classmethod
    def get_token_manager_client(cls):
        return cls.get_client(
            host=settings.redis.TOKEN_REDIS_HOST,
            port=settings.redis.TOKEN_REDIS_PORT,
            password=settings.redis.TOKEN_REDIS_PASSWORD,
            db=settings.redis.TOKEN_REDIS_DB,
            label="TokenManager"
        )

    @classmethod
    async def ping_all(cls):
        """Asynchronously verify all connections. Call this at Startup."""
        for key, client in cls._clients.items():
            try:
                await client.ping()
                logging.info(f"✅ Redis connection verified: {key}")
            except Exception as e:
                logging.error(f"❌ Redis verification failed for {key}: {e}")
                raise

    @classmethod
    async def close_all(cls):
        """Closes all active redis connections."""
        for key, client in cls._clients.items():
            await client.close()
            logging.info(f"🛑 Closed Redis connection: {key}")
        cls._clients.clear()