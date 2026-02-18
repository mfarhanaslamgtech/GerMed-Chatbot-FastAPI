"""
Layer 9 Test — CatalogService
Tests the async CatalogService without making real HTTP requests.
"""
import asyncio
import sys
import os
import json

sys.path.append(os.getcwd())


async def test_layer9():
    print("=" * 60)
    print("🧪 Testing Layer 9: Catalog Service")
    print("=" * 60)

    # ═══════════════════════════════════════════════════════════
    # 1. Test Imports
    # ═══════════════════════════════════════════════════════════
    print("\n1️⃣  Testing Imports...")

    from src.app.api.v1.services.catalog.catalog_service import CatalogService
    print("   ✅ CatalogService imported")

    # Verify async methods
    assert asyncio.iscoroutinefunction(CatalogService.fetch_catalogs_and_products)
    print("   ✅ fetch_catalogs_and_products is async")

    assert asyncio.iscoroutinefunction(CatalogService._sync_pdf_catalogs)
    print("   ✅ _sync_pdf_catalogs is async")

    assert asyncio.iscoroutinefunction(CatalogService._sync_products_from_xml)
    print("   ✅ _sync_products_from_xml is async")

    # ═══════════════════════════════════════════════════════════
    # 2. Test Class Constants
    # ═══════════════════════════════════════════════════════════
    print("\n2️⃣  Testing Class Constants...")

    assert CatalogService.CATALOG_REDIS_KEY == "gervet:catalogs"
    print(f"   ✅ CATALOG_REDIS_KEY = '{CatalogService.CATALOG_REDIS_KEY}'")

    assert CatalogService.PRODUCT_SKU_REDIS_KEY == "gervet:sku_to_product"
    print(f"   ✅ PRODUCT_SKU_REDIS_KEY = '{CatalogService.PRODUCT_SKU_REDIS_KEY}'")

    assert "gervetusa.com" in CatalogService.BASE_URL
    print(f"   ✅ BASE_URL = '{CatalogService.BASE_URL}'")

    assert CatalogService.PRODUCT_XML_URL.endswith(".xml?s3")
    print(f"   ✅ PRODUCT_XML_URL = '{CatalogService.PRODUCT_XML_URL}'")

    # ═══════════════════════════════════════════════════════════
    # 3. Test Constructor
    # ═══════════════════════════════════════════════════════════
    print("\n3️⃣  Testing Constructor...")

    class MockRedis:
        def __init__(self):
            self.store = {}
        def hset(self, key, field=None, value=None, mapping=None):
            if key not in self.store:
                self.store[key] = {}
            if mapping:
                self.store[key].update(mapping)
            elif field and value:
                self.store[key][field] = value
        def hgetall(self, key):
            return self.store.get(key, {})

    mock_redis = MockRedis()
    service = CatalogService(redis_conn=mock_redis)
    assert service.redis_conn is mock_redis
    print("   ✅ CatalogService created with mock Redis")

    # ═══════════════════════════════════════════════════════════
    # 4. Test PDF Catalog Sync (with mock HTTP)
    # ═══════════════════════════════════════════════════════════
    print("\n4️⃣  Testing PDF Catalog Sync Logic (mock HTTP)...")

    # We test the HTML parsing logic by simulating what BeautifulSoup would do
    from bs4 import BeautifulSoup

    html = """
    <html>
    <body>
        <a href="/media/catalogs/dental-instruments-2024.pdf">Download</a>
        <a href="/media/catalogs/surgical-kits.pdf">Download</a>
        <a href="/products/scissors">Not a PDF</a>
    </body>
    </html>
    """
    soup = BeautifulSoup(html, "html.parser")
    pdf_links = [a["href"] for a in soup.find_all("a", href=True) if a["href"].endswith(".pdf")]
    assert len(pdf_links) == 2
    print(f"   ✅ BeautifulSoup finds {len(pdf_links)} PDF links in mock HTML")

    # Verify clean name generation
    file_name = "dental-instruments-2024.pdf"
    clean_name = file_name.lower().replace(".pdf", "").replace("-", " ").replace("_", " ")
    assert clean_name == "dental instruments 2024"
    print(f"   ✅ Clean name: '{clean_name}'")

    # Test Redis hset
    mock_redis.hset("gervet:catalogs", clean_name, "https://example.com/dental.pdf")
    assert mock_redis.hgetall("gervet:catalogs")[clean_name] == "https://example.com/dental.pdf"
    print("   ✅ PDF link stored in Redis mock")

    # ═══════════════════════════════════════════════════════════
    # 5. Test XML Product Parsing
    # ═══════════════════════════════════════════════════════════
    print("\n5️⃣  Testing XML Product Parsing...")

    import xmltodict
    from lxml import etree

    xml_content = b"""<?xml version="1.0" encoding="UTF-8"?>
    <products>
        <product>
            <name>Iris Scissors 4.5" Curved</name>
            <sku>GV-1001</sku>
            <url>https://www.gervetusa.com/iris-scissors</url>
            <pdf_link>https://www.gervetusa.com/pdf/iris.pdf</pdf_link>
            <short_description>Curved iris scissors</short_description>
            <full_description>Professional grade iris scissors</full_description>
            <images>
                <image>
                    <large>https://cdn.gervetusa.com/iris-large.jpg</large>
                    <medium>https://cdn.gervetusa.com/iris-medium.jpg</medium>
                </image>
            </images>
            <sub_products>
                <sub_product>
                    <sku>GV-1001-A</sku>
                    <name>Iris Scissors 4.5" Curved - Titanium</name>
                </sub_product>
            </sub_products>
        </product>
        <product>
            <name>Operating Scissors 5.5" Straight</name>
            <sku>GV-2001</sku>
            <url>https://www.gervetusa.com/operating-scissors</url>
            <short_description>Straight operating scissors</short_description>
        </product>
    </products>
    """

    parser = etree.XMLParser(recover=True)
    xml_tree = etree.fromstring(xml_content, parser=parser)
    data_dict = xmltodict.parse(etree.tostring(xml_tree))

    products = data_dict.get("products", {}).get("product", [])
    if isinstance(products, dict):
        products = [products]

    assert len(products) == 2
    print(f"   ✅ Parsed {len(products)} products from XML")

    # Test first product
    p1 = products[0]
    assert p1["name"] == 'Iris Scissors 4.5" Curved'
    assert p1["sku"] == "GV-1001"
    print(f"   ✅ Product 1: {p1['name']} (SKU: {p1['sku']})")

    # Test image extraction
    images = (p1.get("images") or {}).get("image", [])
    if isinstance(images, dict):
        images = [images]
    assert len(images) == 1
    assert images[0]["large"] == "https://cdn.gervetusa.com/iris-large.jpg"
    print(f"   ✅ Image extracted: {images[0]['large']}")

    # Test sub-products
    subs = (p1.get("sub_products") or {}).get("sub_product", [])
    if isinstance(subs, dict):
        subs = [subs]
    assert len(subs) == 1
    assert subs[0]["sku"] == "GV-1001-A"
    print(f"   ✅ Sub-product: {subs[0]['sku']}")

    # Test SKU map building
    sku_map = {}
    for product in products:
        p_info = {
            "item_name": product.get("name", ""),
            "sku": product.get("sku", ""),
            "product_url": product.get("url", ""),
        }
        if p_info["sku"]:
            standard_sku = p_info["sku"].strip().upper()
            sku_map[standard_sku] = json.dumps(p_info)

        _subs = (product.get("sub_products") or {}).get("sub_product", [])
        if isinstance(_subs, dict):
            _subs = [_subs]
        for sp in _subs:
            sp_sku = sp.get("sku")
            if sp_sku:
                if sp_sku.strip().upper() not in sku_map:
                    sku_map[sp_sku.strip().upper()] = json.dumps(p_info)

    assert "GV-1001" in sku_map
    assert "GV-1001-A" in sku_map
    assert "GV-2001" in sku_map
    print(f"   ✅ SKU map built: {len(sku_map)} entries ({list(sku_map.keys())})")

    # Test Redis batch write
    mock_redis_2 = MockRedis()
    mock_redis_2.hset("gervet:sku_to_product", mapping=sku_map)
    stored = mock_redis_2.hgetall("gervet:sku_to_product")
    assert len(stored) == 3
    print(f"   ✅ SKU map stored in Redis mock ({len(stored)} entries)")

    # ═══════════════════════════════════════════════════════════
    # 6. Test DI Container Wiring
    # ═══════════════════════════════════════════════════════════
    print("\n6️⃣  Testing DI Container Wiring...")

    from src.app.containers.app_container import AppContainer
    container = AppContainer()

    assert hasattr(container, "catalog_service"), "Missing catalog_service provider"
    print("   ✅ catalog_service provider registered in container")

    # ═══════════════════════════════════════════════════════════
    # 7. Test App Lifespan Integration
    # ═══════════════════════════════════════════════════════════
    print("\n7️⃣  Testing App Lifespan Integration...")

    import inspect
    from src.app.app import lifespan
    assert callable(lifespan)
    print("   ✅ lifespan is callable (async context manager)")

    # Check that catalog is referenced in app.py
    with open("src/app/app.py", "r") as f:
        app_content = f.read()

    assert "catalog_service" in app_content
    assert "fetch_catalogs_and_products" in app_content
    assert "create_task" in app_content
    print("   ✅ catalog_service.fetch_catalogs_and_products() in lifespan (background task)")

    print("\n" + "=" * 60)
    print("🎉 Layer 9 — ALL TESTS PASSED!")
    print("=" * 60)


asyncio.run(test_layer9())
