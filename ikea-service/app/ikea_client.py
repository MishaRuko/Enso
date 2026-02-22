from __future__ import annotations

from typing import Any

import httpx
import ikea_api

from app.models import FurnitureItem, ModelFile, ProductImage, StockInfo, Variant

CONSTANTS = ikea_api.Constants(country="gb", language="en")


def _parse_product(product: dict[str, Any]) -> FurnitureItem:
    """Parse a product dict from the IKEA search API into a FurnitureItem."""
    price_obj = product.get("salesPrice", {})
    price_val = price_obj.get("numeral") if price_obj else None
    currency = price_obj.get("currencyCode") if price_obj else None

    images = [
        ProductImage(
            url=img.get("url", ""),
            alt=img.get("altText"),
            type=img.get("type"),
        )
        for img in product.get("allProductImage", [])
    ]

    category_path = product.get("categoryPath", [])
    category = category_path[-1].get("name") if category_path else None

    colors = product.get("colors", [])
    color = colors[0].get("name") if colors else product.get("validDesignText")

    variants = []
    gpr = product.get("gprDescription", {})
    for v in gpr.get("variants", []):
        v_price = v.get("salesPrice", {})
        variants.append(
            Variant(
                item_code=v.get("id", ""),
                name=v.get("name"),
                description=f"{v.get('name', '')} {v.get('typeName', '')}".strip() or None,
                color=v.get("validDesignText"),
                dimensions=v.get("itemMeasureReferenceText"),
                price=v_price.get("numeral") if v_price else None,
                currency=v_price.get("currencyCode") if v_price else None,
                image_url=v.get("mainImageUrl"),
                buy_url=v.get("pipUrl"),
            )
        )

    return FurnitureItem(
        item_code=product.get("id", product.get("itemNo", "")),
        name=product.get("name"),
        type_name=product.get("typeName"),
        description=f"{product.get('name', '')} {product.get('typeName', '')}, {product.get('itemMeasureReferenceText', '')}".strip(", "),
        dimensions=product.get("itemMeasureReferenceText"),
        price=price_val,
        currency=currency,
        image_url=product.get("mainImageUrl"),
        images=images,
        buy_url=product.get("pipUrl"),
        category=category,
        color=color,
        rating=product.get("ratingValue"),
        rating_count=product.get("ratingCount"),
        variants=variants,
    )


def _extract_products(raw: dict[str, Any]) -> list[dict[str, Any]]:
    """Extract product dicts from raw search API response."""
    return [
        item.get("product", {})
        for item in raw.get("searchResultPage", {})
        .get("products", {})
        .get("main", {})
        .get("items", [])
        if item.get("product")
    ]


async def search_products(query: str, limit: int = 24) -> list[FurnitureItem]:
    search = ikea_api.Search(CONSTANTS)
    endpoint = search.search(query, limit=limit)
    raw = await ikea_api.run_async(endpoint)
    return [_parse_product(p) for p in _extract_products(raw)]


async def get_product_details(item_code: str) -> FurnitureItem | None:
    """Look up a single product by item code using the search API."""
    search = ikea_api.Search(CONSTANTS)
    endpoint = search.search(item_code, limit=5)
    raw = await ikea_api.run_async(endpoint)

    for product in _extract_products(raw):
        if product.get("id") == item_code or product.get("itemNo") == item_code:
            return _parse_product(product)

    # If exact match not found, return first result
    products = _extract_products(raw)
    if products:
        return _parse_product(products[0])
    return None


async def get_3d_models(item_code: str) -> list[ModelFile]:
    """Fetch 3D model URLs for an item via the Rotera endpoint.

    Calls the IKEA Rotera API directly with httpx because the ikea_api
    library's executor doesn't handle gzip-encoded responses properly.
    """
    url = f"{CONSTANTS.base_url}/global/assets/rotera/resources/{item_code}.json"
    async with httpx.AsyncClient() as client:
        resp = await client.get(url, headers={"Accept-Encoding": "gzip"})
        resp.raise_for_status()
        raw = resp.json()

    models: list[ModelFile] = []
    for model in raw.get("models", []):
        model_url = model.get("url", "")
        fmt = model.get("format", "")
        if model_url and fmt:
            models.append(ModelFile(format=fmt, url=model_url, source_url=model_url))
    return models


async def get_stock(item_code: str) -> StockInfo:
    stock = ikea_api.Stock(CONSTANTS)
    endpoint = stock.get_stock(item_code)
    raw = await ikea_api.run_async(endpoint)
    return StockInfo(item_code=item_code, available=raw)
