"""
Standalone Migration/Sync Script for GerMed Embeddings (Gemedusa).

Usage:
    python scripts/sync_embeddings.py
"""

import sys
import os
import asyncio
import logging
from pathlib import Path

# Add project root to path
project_root = str(Path(__file__).parent.parent)
sys.path.append(project_root)

from src.app.core.redis_connector import RedisConnection
from src.app.api.v1.services.vector_sync.sync_manager import SyncManager

async def main():
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    logger = logging.getLogger("StandaloneSync")

    logger.info("🎬 Starting Standalone Embedding Sync (Gemedusa Migration)...")
    
    try:
        # Get Redis connections (uses settings internally)
        text_redis = RedisConnection.get_textbot_client()
        image_redis = RedisConnection.get_imagebot_client()
        
        # Verify connections
        await text_redis.ping()
        await image_redis.ping()
        logger.info("✅ Redis connections (Text & Image) verified.")

        # Initialize and run sync
        sync_manager = SyncManager(text_redis, image_redis)
        await sync_manager.run_sync_task()
        
        logger.info("✅ Standalone Sync Completed.")
    except Exception as e:
        logger.error(f"❌ Standalone Sync Failed: {e}")
    finally:
        await RedisConnection.close_all()

if __name__ == "__main__":
    asyncio.run(main())
