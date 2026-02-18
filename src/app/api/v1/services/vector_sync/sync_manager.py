"""
SyncManager — Orchestrates Text and Image embedding synchronization for GerMed.

This service integrates both Text and Image synchronization logic into a 
single manager that can be triggered by FastAPI lifespan or background tasks.
"""

import logging
import asyncio
from src.app.api.v1.services.vector_sync.text_sync_service import TextSyncService
from src.app.api.v1.services.vector_sync.image_sync_service import ImageSyncService

logger = logging.getLogger(__name__)

class SyncManager:
    def __init__(self, text_redis, image_redis):
        """
        Initialize with separate Redis connections for Text (DB 0) and Images (DB 2).
        """
        self.text_sync = TextSyncService(text_redis)
        self.image_sync = ImageSyncService(image_redis)

    async def run_sync_task(self):
        """
        Runs both synchronization tasks. 
        Can be run-and-forgotten in the background.
        """
        logger.info("🎬 [SyncManager] Starting full embedding synchronization...")
        try:
            # We run them sequentially to avoid overloading CPU during embedding generation
            # as both use heavy ML models (CLIP and SentenceTransformer).
            await self.text_sync.run_sync()
            await self.image_sync.run_sync()
            logger.info("✅ [SyncManager] Full synchronization completed successfully.")
        except Exception as e:
            logger.error(f"❌ [SyncManager] Synchronization failed: {e}")
