"""
TextSyncService — Modernized GerMed Text Embedding Synchronization.

🎓 MIGRATION NOTES (Gervet → GerMed):
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
1. Manual `requests` replaced with `httpx` (async).
2. SentenceTransformer handled via `TextEmbeddingModel` singleton.
3. Redis client is now `redis.asyncio` (async).
4. All sync processes are now `async`.
5. Integrated with Pydantic `settings`.
"""

import math
import json
import logging
import hashlib
import time
import numpy as np
import pandas as pd
import httpx
import xmltodict
from typing import List, Dict, Any, Tuple
from lxml import etree
from redis.commands.search.field import VectorField, TextField, TagField
from redis.exceptions import ResponseError
from fastapi.concurrency import run_in_threadpool

from src.app.config.settings import settings
from src.app.utils.embedding_model import TextEmbeddingModel

logger = logging.getLogger(__name__)

class TextSyncService:
    XML_URL = "https://www.gervetusa.com/up_data/lc-prodoucts.xml?s3"
    ITEM_KEYWORD_EMBEDDING_FIELD = "item_keyword_vector"
    CATEGORY_NAME_EMBEDDING_FIELD = "category_name_vector"
    TEXT_EMBEDDING_DIMENSION = 768
    INDEX_NAME = "idx"  # Matches what TextSearchService expects

    def __init__(self, redis_conn):
        self.redis = redis_conn
        self.model = TextEmbeddingModel.get_instance()

    async def run_sync(self):
        """Main entry point for text embedding synchronization."""
        logger.info("🚀 [TextSync] Starting Product Text Sync...")
        start_time = time.time()

        try:
            # 1. Fetch and Parse XML
            raw_products = await self._fetch_and_parse_xml()
            df = self._process_product_data(raw_products)
            product_metadata = df.to_dict(orient='index')

            # 2. Identify updates
            existing_info = await self._get_existing_hashes()
            
            to_update = []
            seen_keys = set()

            for index, item in product_metadata.items():
                key = f"product:text:{item['primary_key']}"
                seen_keys.add(key)

                new_hash = self._calculate_content_hash(item)
                item['content_hash'] = new_hash

                if key not in existing_info or existing_info[key] != new_hash:
                    to_update.append((index, item, key))

            logger.info(f"📊 [TextSync] {len(product_metadata)} total, {len(to_update)} to update.")

            if not to_update:
                logger.info("✅ [TextSync] Everything up to date.")
            else:
                # 3. Ensure Index
                await self._ensure_index(len(product_metadata) + 500)

                # 4. Generate Vectors (CPU bound)
                item_keywords_list = [str(item['item_keywords']) for _, item, _ in to_update]
                category_names_list = [str(item['category_names']) for _, item, _ in to_update]
                
                logger.info(f"🧠 [TextSync] Generating embeddings for {len(to_update)} items...")
                item_vectors = await run_in_threadpool(self.model.encode, item_keywords_list)
                category_vectors = await run_in_threadpool(self.model.encode, category_names_list)

                # 5. Batch Store in Redis
                pipe = self.redis.pipeline()
                for i, (index, item, key) in enumerate(to_update):
                    item_data = item.copy()
                    item_data[self.ITEM_KEYWORD_EMBEDDING_FIELD] = item_vectors[i].astype(np.float32).tobytes()
                    item_data[self.CATEGORY_NAME_EMBEDDING_FIELD] = category_vectors[i].astype(np.float32).tobytes()
                    
                    # Sanitize
                    sanitized_item = {
                        k: self._sanitize_value(v) if k not in [self.ITEM_KEYWORD_EMBEDDING_FIELD, self.CATEGORY_NAME_EMBEDDING_FIELD] else v
                        for k, v in item_data.items()
                    }
                    
                    pipe.hset(key, mapping=sanitized_item)
                    
                    if i % 100 == 0 and i > 0:
                        await pipe.execute()
                await pipe.execute()

            # 6. Cleanup
            stale_keys = set(existing_info.keys()) - seen_keys
            if stale_keys:
                logger.info(f"🧹 [TextSync] Removing {len(stale_keys)} stale records.")
                for k in stale_keys:
                    await self.redis.delete(k)

            duration = time.time() - start_time
            logger.info(f"🏁 [TextSync] Completed in {duration:.2f}s.")

        except Exception as e:
            logger.error(f"❌ [TextSync] Failed: {e}", exc_info=True)

    async def _fetch_and_parse_xml(self) -> List[Dict[str, Any]]:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(self.XML_URL)
            response.raise_for_status()
            return await run_in_threadpool(self._parse_xml_sync, response.content)

    def _parse_xml_sync(self, content: bytes) -> List[Dict[str, Any]]:
        parser = etree.XMLParser(recover=True)
        xml_tree = etree.fromstring(content, parser=parser)
        data_dict = xmltodict.parse(etree.tostring(xml_tree))
        products = data_dict['products']['product']
        return [products] if isinstance(products, dict) else products

    def _process_product_data(self, products: List[Dict[str, Any]]) -> pd.DataFrame:
        rows = []
        for product in products:
            prod_images, sub_list, cat_names, cat_urls = [], [], [], []

            # Images
            images = (product.get("images") or {}).get("image", [])
            if isinstance(images, dict): images = [images]
            for img in images:
                prod_images.append(img.get("large") or img.get("medium") or "")

            # Categories
            categories = (product.get("categories") or {}).get("category", [])
            if isinstance(categories, dict): categories = [categories]
            for cat in categories:
                cat_names.append(cat.get("name", ""))
                cat_urls.append(cat.get("url", ""))

            # Sub products
            subs = (product.get("sub_products") or {}).get("sub_product", [])
            if isinstance(subs, dict): subs = [subs]
            for sp in subs:
                sub_list.append({"name": sp.get("name"), "sku": sp.get("sku")})

            # Videos
            prod_videos = []
            videos = (product.get("videos") or {}).get("video", [])
            if isinstance(videos, dict): videos = [videos]
            for v in videos:
                prod_videos.append({
                    "video_url": v.get("video_url", ""),
                    "video_source": v.get("video_source", ""),
                })

            row = {
                "primary_key": product.get("id", ""),
                "product_name": product.get("name", ""),
                "item_keywords": product.get("name", ""),
                "product_url": product.get("url", ""),
                "product_image": prod_images[0] if prod_images else "",
                "pdf_link": product.get("pdf_link", ""),
                "video_url": prod_videos,
                "short_description": product.get("short_description", ""),
                "full_description": product.get("full_description", ""),
                "sub_products": sub_list,
                "categories": cat_urls,
                "category_names": cat_names,
                "sku": product.get("sku") or product.get("id", "")
            }
            rows.append(row)
        return pd.DataFrame(rows)

    async def _get_existing_hashes(self) -> Dict[str, str]:
        keys = await self.redis.keys("product:text:*")
        hashes = {}
        if keys:
            for k in keys:
                h = await self.redis.hget(k, "content_hash")
                if h: hashes[k] = h
        return hashes

    def _calculate_content_hash(self, item: Dict[str, Any]) -> str:
        relevant = {
            "keywords": item.get("item_keywords", ""),
            "cats": item.get("category_names", []),
            "name": item.get("product_name", ""),
            "sku": item.get("sku", ""),
            "desc": item.get("short_description", ""),
            "videos": item.get("video_url", [])
        }
        return hashlib.md5(json.dumps(relevant, sort_keys=True).encode()).hexdigest()

    async def _ensure_index(self, n_vectors: int):
        try:
            await self.redis.ft(self.INDEX_NAME).info()
        except ResponseError:
            logger.info(f"🏗️ [TextSync] Creating Index: {self.INDEX_NAME}")
            await self.redis.ft(self.INDEX_NAME).create_index([
                VectorField(self.ITEM_KEYWORD_EMBEDDING_FIELD, "FLAT", {
                    "TYPE": "FLOAT32", "DIM": self.TEXT_EMBEDDING_DIMENSION, "DISTANCE_METRIC": "COSINE"
                }),
                VectorField(self.CATEGORY_NAME_EMBEDDING_FIELD, "FLAT", {
                    "TYPE": "FLOAT32", "DIM": self.TEXT_EMBEDDING_DIMENSION, "DISTANCE_METRIC": "COSINE"
                }),
                TextField("product_name"),
                TagField("product_url"),
                TagField("product_image"),
                TagField("pdf_link"),
                TagField("sub_products"),
                TagField("categories"),
                TagField("sku"),
                TextField("short_description"),
                TextField("full_description"),
                TextField("video_url"),
                TagField("content_hash"),
            ])

    def _sanitize_value(self, v: Any) -> str:
        if v is None: return ""
        if isinstance(v, float) and math.isnan(v): return ""
        if isinstance(v, (list, dict)): return json.dumps(v, ensure_ascii=False)
        return str(v)
