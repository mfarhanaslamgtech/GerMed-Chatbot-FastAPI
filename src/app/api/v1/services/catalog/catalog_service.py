"""
CatalogService — Async PDF Catalog Scraper & Product XML Sync.

🎓 MIGRATION NOTES (Gervet → GerMed):
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
1. `requests.get()` → `httpx.AsyncClient()`  (non-blocking HTTP)
2. All methods are now `async` for FastAPI compatibility
3. `print()` replaced with `logging` (proper structured logging)
4. Used as a background task in FastAPI's lifespan (replaces APScheduler)
5. Redis sync calls remain (redis-py is sync), wrapped where needed

Pipeline:
  1. Scrape GerVetUSA /catalogs page for PDF links → store in Redis hash
  2. Fetch XML product feed → parse SKUs → store in Redis hash
  3. Both caches are used by TextSearchService and VisualSearchService
"""
import json
import re
import logging
import httpx
from urllib.parse import urljoin
from typing import Optional

logger = logging.getLogger(__name__)


class CatalogService:
    CATALOG_REDIS_KEY = "gervet:catalogs"
    PRODUCT_SKU_REDIS_KEY = "gervet:sku_to_product"
    BASE_URL = "https://www.gervetusa.com/catalogs"
    PRODUCT_XML_URL = "https://www.gervetusa.com/up_data/lc-prodoucts.xml?s3"

    def __init__(self, redis_conn):
        self.redis_conn = redis_conn

    async def fetch_catalogs_and_products(self):
        """
        Main entry point — scrapes catalogs and syncs products from XML.
        Runs as a background task during app lifespan.
        """
        await self._sync_pdf_catalogs()
        await self._sync_products_from_xml()

    # ═══════════════════════════════════════════════════════════
    # PDF CATALOG SCRAPING
    # ═══════════════════════════════════════════════════════════

    async def _sync_pdf_catalogs(self):
        """
        Scrapes the GerVetUSA catalogs page and stores PDF links in Redis.
        Handles pagination automatically.
        
        🎓 MIGRATION: BeautifulSoup is CPU-bound but fast enough for
        a few pages. No need for run_in_threadpool here.
        """
        from bs4 import BeautifulSoup

        logger.info(f"🚀 [CatalogService] Starting catalog fetch from {self.BASE_URL}")

        visited_pages = set()
        pages_to_visit = {self.BASE_URL}
        stats = {"found": 0, "pages": 0}

        async with httpx.AsyncClient(timeout=60.0, follow_redirects=True) as client:
            while pages_to_visit:
                current_url = pages_to_visit.pop()
                if current_url in visited_pages:
                    continue
                visited_pages.add(current_url)
                stats["pages"] += 1

                try:
                    response = await client.get(current_url)
                    if response.status_code != 200:
                        continue

                    soup = BeautifulSoup(response.content, "html.parser")

                    # 1. Extract PDF links
                    for link in soup.find_all("a", href=True):
                        href = link["href"]
                        if href.lower().endswith(".pdf"):
                            file_url = urljoin(current_url, href)
                            file_name_short = href.split("/")[-1]

                            clean_name = (
                                file_name_short.lower()
                                .replace(".pdf", "")
                                .replace("-", " ")
                                .replace("_", " ")
                            )

                            await self.redis_conn.hset(
                                self.CATALOG_REDIS_KEY, clean_name, file_url
                            )
                            stats["found"] += 1
                            logger.debug(f"   ✅ Cached PDF: {clean_name}")

                    # 2. Dynamic pagination
                    for link in soup.find_all("a", href=True):
                        next_href = link["href"]
                        if "catalogs" in next_href and (
                            "page=" in next_href or "p=" in next_href
                        ):
                            full_next_url = urljoin(self.BASE_URL, next_href)
                            if full_next_url not in visited_pages:
                                pages_to_visit.add(full_next_url)

                except Exception as e:
                    logger.error(f"Error scraping {current_url}: {e}")

        logger.info(
            f"🏁 [CatalogService] PDF sync completed. "
            f"Found {stats['found']} files across {stats['pages']} pages."
        )

    # ═══════════════════════════════════════════════════════════
    # PRODUCT XML SYNC
    # ═══════════════════════════════════════════════════════════

    async def _sync_products_from_xml(self):
        """
        Fetches all products from XML feed and stores SKU → Product mapping in Redis.
        
        🎓 MIGRATION: xmltodict + lxml parsing is CPU-bound but runs fast enough
        for a single XML document. No threadpool needed.
        """
        logger.info(f"🚀 [CatalogService] Syncing products from XML: {self.PRODUCT_XML_URL}")

        try:
            import xmltodict
            from lxml import etree

            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(self.PRODUCT_XML_URL)

            if response.status_code != 200:
                logger.error(
                    f"[CatalogService] Failed to fetch XML: {response.status_code}"
                )
                return

            # Clean and parse XML
            parser = etree.XMLParser(recover=True)
            xml_tree = etree.fromstring(response.content, parser=parser)
            data_dict = xmltodict.parse(etree.tostring(xml_tree))

            products = data_dict.get("products", {}).get("product", [])
            if isinstance(products, dict):
                products = [products]

            sku_map = {}
            for product in products:
                p_info = {
                    "item_name": product.get("name", ""),
                    "product_name": product.get("name", ""),
                    "sku": product.get("sku", ""),
                    "product_url": product.get("url", ""),
                    "pdf_link": product.get("pdf_link", ""),
                    "short_description": product.get("short_description", ""),
                    "full_description": product.get("full_description", ""),
                }

                # Handle images
                images = (product.get("images") or {}).get("image", [])
                if isinstance(images, dict):
                    images = [images]
                if images:
                    p_info["product_image"] = (
                        images[0].get("large") or images[0].get("medium") or ""
                    )
                    p_info["image_url"] = p_info["product_image"]

                # Handle sub-products
                subs = (product.get("sub_products") or {}).get("sub_product", [])
                if isinstance(subs, dict):
                    subs = [subs]
                p_info["sub_products"] = subs

                # Store primary SKU
                if p_info["sku"]:
                    standard_sku = p_info["sku"].strip().upper()
                    sku_map[standard_sku] = json.dumps(p_info)

                # Store sub-product SKUs pointing to parent product
                for sp in subs:
                    sp_sku = sp.get("sku")
                    if sp_sku:
                        standard_sp_sku = sp_sku.strip().upper()
                        if standard_sp_sku not in sku_map:
                            sku_map[standard_sp_sku] = json.dumps(p_info)

            # Batch write to Redis
            if sku_map:
                await self.redis_conn.hset(self.PRODUCT_SKU_REDIS_KEY, mapping=sku_map)
                logger.info(
                    f"✅ [CatalogService] Synced {len(sku_map)} SKUs to Redis."
                )

        except ImportError as e:
            logger.warning(
                f"[CatalogService] XML parsing libraries not available: {e}. "
                "Install xmltodict and lxml to enable product sync."
            )
        except Exception as e:
            logger.error(f"[CatalogService] Product sync failed: {e}")
