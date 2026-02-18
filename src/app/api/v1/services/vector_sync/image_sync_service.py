"""
ImageSyncService — Modernized GerMed Image Embedding Synchronization.

🎓 MIGRATION NOTES (Gervet → GerMed):
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
1. Manual `requests` replaced with `httpx` (async).
2. CLIP Model handled via `ImageEmbeddingModel` singleton.
3. Redis client is now `redis.asyncio` (async).
4. All sync processes are now `async` methods.
5. Integrated with Pydantic `settings`.
"""

import os
import math
import json
import logging
import hashlib
import time
import numpy as np
import pandas as pd
import httpx
import torch
import xmltodict
from PIL import Image
from io import BytesIO
from typing import List, Dict, Any, Optional, Tuple
from lxml import etree
from redis.commands.search.field import VectorField, TextField, TagField
from redis.exceptions import ResponseError
from fastapi.concurrency import run_in_threadpool

from src.app.config.settings import settings
from src.app.utils.embedding_model import ImageEmbeddingModel

logger = logging.getLogger(__name__)

class ImageSyncService:
    XML_URL = "https://www.gervetusa.com/up_data/lc-prodoucts.xml?s3"
    IMAGE_EMBEDDING_FIELD = "image_vector"
    EMBEDDING_DIMENSION = 512
    BATCH_SIZE = 32
    MAX_RETRIES = 3
    INDEX_NAME = "idx_images"

    def __init__(self, redis_conn):
        self.redis = redis_conn
        embedding_data = ImageEmbeddingModel.get_instance()
        self.model = embedding_data["model"]
        self.processor = embedding_data["processor"]
        self.device = embedding_data["device"]

    async def run_sync(self):
        """Main entry point for image embedding synchronization."""
        logger.info("🚀 [ImageSync] Starting Image Embedding Sync...")
        start_time = time.time()

        try:
            # 1. Fetch and Parse XML
            raw_products = await self._fetch_and_parse_xml()
            df = self._process_product_data(raw_products)
            product_metadata = df.to_dict(orient='index')

            # 2. Identify changes using content hash
            existing_info = await self._get_existing_hashes()
            
            to_update = []
            seen_keys = set()

            for index, item in product_metadata.items():
                key = f"product:image:{item['primary_key']}"
                seen_keys.add(key)

                new_hash = self._calculate_content_hash(item)
                item['content_hash'] = new_hash

                if key not in existing_info or existing_info[key] != new_hash:
                    if item.get('image_url'):
                        to_update.append((index, item, key))

            logger.info(f"📊 [ImageSync] Found {len(product_metadata)} products total, {len(to_update)} need updates.")

            if not to_update:
                logger.info("✅ [ImageSync] No changes detected. Sync complete.")
            else:
                # 3. Ensure Search Index Exists
                await self._ensure_index()

                # 4. Process Updates in Batches
                for i in range(0, len(to_update), self.BATCH_SIZE):
                    batch = to_update[i:i + self.BATCH_SIZE]
                    await self._process_batch(batch)
                    logger.info(f"💾 [ImageSync] Progress: {min(i + self.BATCH_SIZE, len(to_update))}/{len(to_update)}")

            # 5. Cleanup stale keys
            stale_keys = set(existing_info.keys()) - seen_keys
            if stale_keys:
                logger.info(f"🧹 [ImageSync] Removing {len(stale_keys)} stale image records.")
                for k in list(stale_keys):
                    await self.redis.delete(k)

            duration = time.time() - start_time
            logger.info(f"🏁 [ImageSync] Synchronization completed in {duration:.2f} seconds.")

        except Exception as e:
            logger.error(f"❌ [ImageSync] Synchronization failed: {e}", exc_info=True)

    async def _fetch_and_parse_xml(self) -> List[Dict[str, Any]]:
        """Fetches and parses XML product data asynchronously."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(self.XML_URL)
            response.raise_for_status()
            
            # Use run_in_threadpool for CPU-bound XML parsing
            return await run_in_threadpool(self._parse_xml_sync, response.content)

    def _parse_xml_sync(self, xml_content: bytes) -> List[Dict[str, Any]]:
        """Synchronous XML parsing logic."""
        parser = etree.XMLParser(recover=True)
        xml_tree = etree.fromstring(xml_content, parser=parser)
        data_dict = xmltodict.parse(etree.tostring(xml_tree))
        products = data_dict['products']['product']
        return [products] if isinstance(products, dict) else products

    def _process_product_data(self, products: List[Dict[str, Any]]) -> pd.DataFrame:
        """Processes raw XML products into structured data."""
        rows = []
        for product in products:
            prod_images, prod_videos, sub_list, cat_list, spec_list = [], [], [], [], []

            # 1. Images
            image_data = product.get("images", {})
            image_list = image_data.get("image", []) if image_data else []
            if isinstance(image_list, dict): image_list = [image_list]
            for img in image_list:
                prod_images.append({
                    "thumbnail": img.get("thumbnail", ""),
                    "medium": img.get("medium", ""),
                    "large": img.get("large", ""),
                })

            # 2. Sub products
            subs = (product.get("sub_products") or {}).get("sub_product", [])
            if isinstance(subs, dict): subs = [subs]
            for sp in subs:
                sub_list.append({
                    "sku": sp.get("sku", ""),
                    "name": sp.get("name", ""),
                    "url": sp.get("url", ""),
                })

            # 3. Categories
            cats = (product.get("categories") or {}).get("category", [])
            if isinstance(cats, dict): cats = [cats]
            for cat in cats:
                cat_list.append(cat.get("name", ""))

            row = {
                "primary_key": product.get("id", ""),
                "product_name": product.get("name", ""),
                "sku": product.get("sku", ""),
                "product_url": product.get("url", ""),
                "image_url": prod_images, # list of dicts
                "short_description": product.get("short_description", ""),
                "full_description": product.get("full_description", ""),
                "sub_products": sub_list,
                "categories": cat_list,
                "pdf_url": product.get("pdf_link", ""),
                "item_keywords": product.get("name", "")
            }
            rows.append(row)
        
        return pd.DataFrame(rows)

    async def _get_existing_hashes(self) -> Dict[str, str]:
        """Retrieves existing content hashes from Redis."""
        keys = await self.redis.keys("product:image:*")
        hashes = {}
        if keys:
            for k in keys:
                h = await self.redis.hget(k, "content_hash")
                if h:
                    hashes[k] = h
        return hashes

    def _calculate_content_hash(self, item: Dict[str, Any]) -> str:
        """Calculates MD5 hash for change detection."""
        hash_payload = {
            "id": str(item.get("primary_key", "")),
            "name": str(item.get("product_name", "")),
            "image": str(item.get("image_url", "")),
            "url": str(item.get("product_url", ""))
        }
        encoded = json.dumps(hash_payload, sort_keys=True).encode('utf-8')
        return hashlib.md5(encoded).hexdigest()

    async def _ensure_index(self):
        """Creates the search index if it doesn't exist."""
        try:
            await self.redis.ft(self.INDEX_NAME).info()
        except ResponseError:
            logger.info(f"🏗️ [ImageSync] Creating Index: {self.INDEX_NAME}")
            try:
                await self.redis.ft(self.INDEX_NAME).create_index([
                    VectorField(self.IMAGE_EMBEDDING_FIELD, "FLAT", {
                        "TYPE": "FLOAT32",
                        "DIM": self.EMBEDDING_DIMENSION,
                        "DISTANCE_METRIC": "COSINE"
                    }),
                    TextField("primary_key"),
                    TextField("product_name"),
                    TextField("product_url"),
                    TextField("image_url"),
                    TextField("pdf_url"),
                    TextField("short_description"),
                    TextField("full_description"),
                    TextField("sub_products"),
                    TextField("categories"),
                    TextField("sku"),
                    TagField("content_hash")
                ])
            except Exception as e:
                logger.error(f"Failed to create index: {e}")
                raise

    async def _process_batch(self, batch: List[Tuple[int, Dict[str, Any], str]]):
        """Downloads images and generates embeddings for a batch."""
        valid_items = []
        batch_images = []

        async with httpx.AsyncClient(timeout=10.0) as client:
            for index, item, key in batch:
                images = item.get('image_url', [])
                clean_url = self._extract_clean_url(images)
                
                if clean_url:
                    try:
                        resp = await client.get(clean_url)
                        if resp.status_code == 200:
                            img = Image.open(BytesIO(resp.content))
                            if img.mode != 'RGB':
                                img = img.convert('RGB')
                            batch_images.append(img)
                            item['_clean_image_url'] = clean_url
                            valid_items.append((item, key))
                    except Exception as e:
                        logger.warning(f"Failed to download {clean_url}: {e}")

        if batch_images:
            # Generate Embeddings (CPU bound)
            embeddings = await run_in_threadpool(self._get_embeddings_sync, batch_images)
            
            # Store in Redis
            pipe = self.redis.pipeline()
            for idx, (item, key) in enumerate(valid_items):
                mapping = self._prepare_redis_mapping(item, embeddings[idx])
                pipe.hset(key, mapping=mapping)
            await pipe.execute()

    def _extract_clean_url(self, val: Any) -> Optional[str]:
        """Extracts a single valid URL from various possible structures."""
        if not val: return None
        if isinstance(val, str) and val.startswith('http'): return val
        if isinstance(val, list) and len(val) > 0:
            return self._extract_clean_url(val[0])
        if isinstance(val, dict):
            return val.get('large') or val.get('medium') or val.get('thumbnail')
        return None

    def _get_embeddings_sync(self, images: List[Image.Image]) -> np.ndarray:
        """Synchronous CLIP inference."""
        with torch.no_grad():
            inputs = self.processor(images=images, return_tensors="pt", padding=True)
            inputs = {k: v.to(self.device) for k, v in inputs.items()}
            outputs = self.model.get_image_features(**inputs)
            
            # Handle cases where output might be a dict-like object (BaseModelOutputWithPooling)
            if hasattr(outputs, "image_embeds"):
                features = outputs.image_embeds
            elif hasattr(outputs, "pooler_output"):
                features = outputs.pooler_output
            elif isinstance(outputs, dict):
                features = outputs.get("image_embeds") or outputs.get("pooler_output") or outputs
            else:
                features = outputs

            features = features.cpu().numpy()
            
            # L2 Normalization
            norms = np.linalg.norm(features, axis=1, keepdims=True)
            normalized_features = features / (norms + 1e-12)
            return normalized_features.astype(np.float32)

    def _prepare_redis_mapping(self, item: Dict[str, Any], vector: np.ndarray) -> Dict[str, Any]:
        """Prepares a dictionary for Redis HSET."""
        mapping = {
            "primary_key": str(item.get("primary_key", "")),
            "product_name": str(item.get("product_name", "")),
            "product_url": str(item.get("product_url", "")),
            "image_url": str(item.get("_clean_image_url", "")),
            "pdf_url": str(item.get("pdf_url", "")),
            "short_description": str(item.get("short_description", "")),
            "full_description": str(item.get("full_description", "")),
            "sub_products": json.dumps(item.get("sub_products", [])),
            "categories": json.dumps(item.get("categories", [])),
            "sku": str(item.get("sku", "")),
            "content_hash": str(item.get("content_hash", "")),
            self.IMAGE_EMBEDDING_FIELD: vector.tobytes()
        }
        return mapping
