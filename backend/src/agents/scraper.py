"""IKEA product scraper — searches IKEA's public search API via httpx."""

import logging
import uuid

import httpx

from ..models.schemas import FurnitureDimensions, FurnitureItem

logger = logging.getLogger(__name__)

# IKEA public search endpoint (no auth required)
_IKEA_SEARCH_URL = "https://sik.search.blue.cdtapps.com/{country}/{lang}/search-result-page"

# Default timeout for IKEA API calls
_TIMEOUT = httpx.Timeout(15.0, connect=10.0)


def _parse_dimensions(product: dict) -> FurnitureDimensions | None:
    """Try to extract dimensions from IKEA product data."""
    try:
        width = product.get("itemWidth", 0)
        height = product.get("itemHeight", 0)
        depth = product.get("itemDepth", 0)
        if width or height or depth:
            return FurnitureDimensions(width_cm=width, depth_cm=depth, height_cm=height)
    except Exception:
        pass
    return None


def _parse_product(product: dict, country: str, lang: str) -> FurnitureItem | None:
    """Parse a single IKEA search result into a FurnitureItem."""
    try:
        # Extract price
        price_numeral = product.get("priceNumeral")
        if price_numeral is None:
            # Some items don't have price data
            sales_price = product.get("salesPrice", {})
            price_numeral = sales_price.get("numeral", 0) if isinstance(sales_price, dict) else 0

        price = float(price_numeral) if price_numeral else 0

        # Currency mapping
        currency_map = {"fr": "EUR", "de": "EUR", "us": "USD", "gb": "GBP", "se": "SEK"}
        currency = product.get("currencyCode", currency_map.get(country, "EUR"))

        # Product URL
        pip_url = product.get("pipUrl", "")
        if pip_url and not pip_url.startswith("http"):
            pip_url = f"https://www.ikea.com{pip_url}"

        # Image URL — prefer contextual, fall back to main
        image_url = (
            product.get("contextualImageUrl")
            or product.get("mainImageUrl")
            or product.get("imageUrl", "")
        )

        name = product.get("name", "Unknown")
        type_name = product.get("typeName", "")
        display_name = f"{name} {type_name}".strip() if type_name else name

        item_id = product.get("id", uuid.uuid4().hex[:16])

        return FurnitureItem(
            id=str(item_id),
            retailer="ikea",
            name=display_name,
            price=price,
            currency=currency,
            dimensions=_parse_dimensions(product),
            image_url=image_url,
            product_url=pip_url,
            glb_url="",
            category=type_name,
        )
    except Exception as e:
        logger.warning("Failed to parse IKEA product: %s", e)
        return None


async def search_ikea(
    query: str,
    *,
    country: str = "fr",
    lang: str = "fr",
    limit: int = 5,
) -> list[FurnitureItem]:
    """Search IKEA's public search API and return parsed FurnitureItem list.

    Args:
        query: Search query string (e.g. "3-seat sofa grey fabric").
        country: IKEA country code (default "fr" for France).
        lang: Language code (default "fr").
        limit: Maximum number of results to return.

    Returns:
        List of FurnitureItem parsed from search results.
    """
    url = _IKEA_SEARCH_URL.format(country=country, lang=lang)
    params = {
        "q": query,
        "size": min(limit, 24),
        "types": "PRODUCT",
    }
    headers = {
        "Accept": "application/json",
        "User-Agent": "HomeDesigner/1.0",
    }

    # Simplify query: IKEA API rejects long/complex queries with 400
    words = query.split()
    if len(words) > 3:
        query = " ".join(words[:3])
        params["q"] = query

    logger.info("Searching IKEA: query=%r country=%s limit=%d", query, country, limit)

    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            resp = await client.get(url, params=params, headers=headers)
            resp.raise_for_status()
            data = resp.json()
    except httpx.HTTPStatusError as e:
        logger.error("IKEA API HTTP error %d: %s", e.response.status_code, e)
        return []
    except Exception as e:
        logger.error("IKEA API request failed: %s", e)
        return []

    # Navigate response structure: searchResultPage -> products -> main -> items
    try:
        items_data = (
            data.get("searchResultPage", {})
            .get("products", {})
            .get("main", {})
            .get("items", [])
        )
    except (AttributeError, TypeError):
        logger.warning("Unexpected IKEA response structure")
        items_data = []

    results: list[FurnitureItem] = []
    for item_wrapper in items_data[:limit]:
        product = item_wrapper.get("product", item_wrapper)
        parsed = _parse_product(product, country, lang)
        if parsed:
            results.append(parsed)

    logger.info("IKEA search for %r returned %d results", query, len(results))
    return results
