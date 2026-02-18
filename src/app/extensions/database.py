import logging
from pymongo import AsyncMongoClient
from src.app.config.settings import settings

class Database:
    """
    Manages MongoDB connection using NEW Native Async PyMongo (v4.12+).
    
    🎓 PRO TIP:
    PyMongo now has its own 'Async' engine, making 'motor' secondary
    for projects that want to stay on the official driver's newest features.
    """
    
    def __init__(self):
        """Initialize Native Async MongoDB connection."""
        try:
            # Native AsyncMongoClient from pymongo 4.12+
            self._client = AsyncMongoClient(
                settings.mongodb.MONGO_URI,
                maxPoolSize=settings.mongodb.MONGODB_MAX_POOL_SIZE,
                connectTimeoutMS=settings.mongodb.MONGODB_CONNECT_TIMEOUT,
                serverSelectionTimeoutMS=settings.mongodb.MONGODB_SERVER_SELECTION_TIMEOUT,
            )
            self._db = self._client[settings.mongodb.MONGODB_DATABASE]
            logging.info(f"✅ Native Async PyMongo initialized (DB: {settings.mongodb.MONGODB_DATABASE})")
        except Exception as e:
            logging.error(f"❌ Failed to initialize Native Async MongoDB: {str(e)}")
            raise

    def get_collection(self, collection_name: str):
        """Get a native async collection by name."""
        if self._db is None:
            raise RuntimeError("Database not initialized")
        return self._db[collection_name]

    async def close(self):
        """Close the async connection pool."""
        if self._client:
            # Note: client.close() in native async is often just .close() 
            # but usually handled by the async lifecycle.
            await self._client.close()
            logging.info("🛑 Native Async MongoDB connection closed.")

    @property
    def client(self) -> AsyncMongoClient:
        """Get the Async MongoDB client instance."""
        return self._client
    
    @property
    def db(self):
        """Get the Async MongoDB database instance."""
        return self._db

# 🧪 Direct Check Mode 
if __name__ == "__main__":
    import asyncio
    
    async def main():
        logging.basicConfig(level=logging.INFO)
        print("🔍 Checking Database Config...")
        try:
            db = Database()
            # Try a ping
            await db.client.admin.command('ping')
            print("✅ Database.py: Connection Successful!")
        except Exception as e:
            print(f"❌ Database.py: Connection Failed -> {e}")
        finally:
            if 'db' in locals():
                await db.close()

    asyncio.run(main())
