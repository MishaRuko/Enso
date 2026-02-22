"""
Demo script showing the full IKEA Furniture API pipeline.

Usage:
    # Start the server first:
    #   uvicorn app.main:app --port 8000
    #
    # Then run this script:
    #   python demo.py
    #
    # Or pass a custom search query:
    #   python demo.py "standing desk"
"""

import sys
import httpx

BASE_URL = "http://localhost:8000"


def print_header(title: str):
    print(f"\n{'=' * 60}")
    print(f"  {title}")
    print(f"{'=' * 60}\n")


def demo_search(query: str, limit: int = 3):
    print_header(f'1. SEARCH: "{query}" (limit={limit})')

    resp = httpx.get(f"{BASE_URL}/search", params={"query": query, "limit": limit})
    resp.raise_for_status()
    data = resp.json()

    print(f"Found {len(data['items'])} results:\n")

    for i, item in enumerate(data["items"], 1):
        print(f"  [{i}] {item['name']} {item['type_name'] or ''}")
        print(f"      Item code:  {item['item_code']}")
        print(f"      Price:      {item['currency']} {item['price']}")
        print(f"      Dimensions: {item['dimensions'] or 'N/A'}")
        print(f"      Color:      {item['color'] or 'N/A'}")
        print(f"      Category:   {item['category'] or 'N/A'}")
        print(f"      Rating:     {item['rating']}/5 ({item['rating_count']} reviews)")
        print(f"      Images:     {len(item['images'])} available")
        print(f"      Variants:   {len(item['variants'])} color/size options")
        print(f"      Buy URL:    {item['buy_url']}")
        print()

    return data["items"]


def demo_product(item_code: str):
    print_header(f"2. PRODUCT DETAIL: {item_code}")

    resp = httpx.get(f"{BASE_URL}/product/{item_code}")
    resp.raise_for_status()
    item = resp.json()

    print(f"  Name:        {item['name']} {item['type_name'] or ''}")
    print(f"  Description: {item['description']}")
    print(f"  Price:       {item['currency']} {item['price']}")
    print(f"  Dimensions:  {item['dimensions'] or 'N/A'}")
    print(f"  Color:       {item['color'] or 'N/A'}")
    print(f"  Category:    {item['category'] or 'N/A'}")
    print(f"  Rating:      {item['rating']}/5 ({item['rating_count']} reviews)")
    print(f"  Buy URL:     {item['buy_url']}")

    print(f"\n  Images ({len(item['images'])}):")
    for img in item["images"]:
        print(f"    [{img['type']}] {img['url']}")

    if item["variants"]:
        print(f"\n  Variants ({len(item['variants'])}):")
        for v in item["variants"]:
            print(f"    - {v['color'] or 'N/A':25s}  {item['currency']} {v['price']}  {v['dimensions'] or ''}")
            print(f"      {v['buy_url']}")

    return item


def demo_3d_model(item_code: str):
    print_header(f"3. 3D MODELS: {item_code}")

    resp = httpx.get(f"{BASE_URL}/model/{item_code}")
    if resp.status_code != 200:
        print(f"  No 3D models available (code: {resp.status_code})")
        return None

    models = resp.json()
    if not models:
        print("  No 3D models found for this item.")
        return models

    print(f"  Found {len(models)} model(s):\n")
    for m in models:
        print(f"    [{m['format']}] {m['url']}")
    return models


def demo_stock(item_code: str):
    print_header(f"4. STOCK CHECK: {item_code}")

    resp = httpx.get(f"{BASE_URL}/stock/{item_code}")
    if resp.status_code != 200:
        print(f"  Stock check unavailable for this item (code: {resp.status_code})")
        print(f"  This can happen with combination/bundle items (e.g. codes starting with 's').")
        return None
    data = resp.json()

    stores = data["available"].get("availabilities", [])
    in_stock = [s for s in stores if s.get("buyingOption", {}).get("cashCarry", {}).get("availability", {}).get("quantity", 0) > 0]
    print(f"  {len(in_stock)}/{len(stores)} stores have stock\n")

    for store in stores[:10]:
        cash_carry = store.get("buyingOption", {}).get("cashCarry", {})
        avail = cash_carry.get("availability", {})
        qty = avail.get("quantity", "?")
        prob = avail.get("probability", {}).get("thisDay", {}).get("messageType", "UNKNOWN")

        class_unit = store.get("classUnitKey", {})
        store_code = class_unit.get("classUnitCode", "")

        print(f"  Store {store_code}: {qty} in stock [{prob}]")

    if len(stores) > 10:
        print(f"  ... and {len(stores) - 10} more stores")

    return data


def demo_pipeline():
    print_header("5. PIPELINE (search + 3D models + cache)")

    queries = [
        {"description": "white bookcase 80cm", "category": "bookcase"},
        {"description": "small wooden desk", "category": "desk"},
        {"description": "floor lamp", "category": "lighting"},
    ]

    print("  Sending furniture list:")
    for q in queries:
        print(f"    - {q['description']} ({q.get('category', '')})")

    resp = httpx.post(
        f"{BASE_URL}/pipeline",
        json={"items": queries},
        timeout=60,
    )
    resp.raise_for_status()
    data = resp.json()

    print(f"\n  Results ({len(data['results'])}):\n")
    for r in data["results"]:
        item = r["item"]
        if item is None:
            print(f"  [{r['source']:9s}] \"{r['query']['description']}\" -> No match found")
            continue

        models_count = len(item.get("model_files", []))
        model_info = f" | 3D: {models_count} model(s)" if models_count else ""
        print(f"  [{r['source']:9s}] {item['name']} {item['type_name'] or ''}")
        print(f"             {item['currency']} {item['price']} | {item['dimensions'] or 'N/A'} | {item['color'] or 'N/A'}{model_info}")
        print(f"             {item['buy_url']}")
        for m in item.get("model_files", []):
            print(f"             3D [{m['format']}]: {m['url'][:80]}...")
        print()

    # Run again to show caching
    print("  --- Running same queries again (should hit cache) ---\n")
    resp2 = httpx.post(f"{BASE_URL}/pipeline", json={"items": queries}, timeout=60)
    resp2.raise_for_status()
    data2 = resp2.json()

    for r in data2["results"]:
        item = r["item"]
        name = f"{item['name']} {item['type_name'] or ''}" if item else "No match"
        print(f"  [{r['source']:9s}] {name}")

    return data


def main():
    query = sys.argv[1] if len(sys.argv) > 1 else "bookcase"

    # Check server is running
    try:
        httpx.get(f"{BASE_URL}/health").raise_for_status()
    except httpx.ConnectError:
        print(f"Error: Server not running at {BASE_URL}")
        print("Start it with: uvicorn app.main:app --port 8000")
        sys.exit(1)

    # 1. Search
    items = demo_search(query)
    if not items:
        print("No results found.")
        return

    # 2. Product detail
    first_code = items[0]["item_code"]
    demo_product(first_code)

    # 3. 3D models
    demo_3d_model(first_code)

    # 4. Stock
    demo_stock(first_code)

    # 5. Full pipeline
    demo_pipeline()

    print_header("DONE")
    print(f"  API docs:  {BASE_URL}/docs")
    print(f"  Endpoints: /search, /product/{{code}}, /model/{{code}}, /stock/{{code}}, /pipeline")
    print()


if __name__ == "__main__":
    main()
