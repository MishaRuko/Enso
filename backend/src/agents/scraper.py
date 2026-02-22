"""IKEA product scraper — searches IKEA's public search API via httpx."""

import asyncio
import logging
import re
import uuid

import httpx

from ..models.schemas import FurnitureDimensions, FurnitureItem
from ..tools.ikea_glb import extract_ikea_glb

logger = logging.getLogger(__name__)

# IKEA public search endpoint (no auth required)
_IKEA_SEARCH_URL = "https://sik.search.blue.cdtapps.com/{country}/{lang}/search-result-page"

# Default timeout for IKEA API calls
_TIMEOUT = httpx.Timeout(15.0, connect=10.0)


def _parse_dimensions(product: dict) -> FurnitureDimensions | None:
    """Try to extract dimensions from IKEA product data."""
    try:
        # Try explicit fields first
        width = product.get("itemWidth", 0)
        height = product.get("itemHeight", 0)
        depth = product.get("itemDepth", 0)
        if width or height or depth:
            return FurnitureDimensions(width_cm=width, depth_cm=depth, height_cm=height)

        # Parse itemMeasureReferenceText like "60x47x83 cm" or "50 cm"
        measure = product.get("itemMeasureReferenceText", "")
        if measure and "cm" in measure:
            nums = [float(n) for n in re.findall(r"[\d.]+", measure.split("cm")[0])]
            if len(nums) >= 3:
                return FurnitureDimensions(width_cm=nums[0], depth_cm=nums[1], height_cm=nums[2])
            if len(nums) == 2:
                return FurnitureDimensions(width_cm=nums[0], depth_cm=nums[1], height_cm=nums[1])
            if len(nums) == 1:
                return FurnitureDimensions(width_cm=nums[0], depth_cm=nums[0], height_cm=nums[0])
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
    limit: int = 1,
    require_glb: bool = True,
) -> list[FurnitureItem]:
    """Search IKEA's public search API and return parsed FurnitureItem list.

    When require_glb is True, fetches extra results and filters to only items
    with a 3D model (GLB) available on their product page. Tries each result
    until `limit` items with GLB are found.

    Args:
        query: Search query string (e.g. "3-seat sofa grey fabric").
        country: IKEA country code (default "fr" for France).
        lang: Language code (default "fr").
        limit: Number of results to return (with GLB if require_glb).
        require_glb: If True, only return items that have a GLB model.

    Returns:
        List of FurnitureItem parsed from search results.
    """
    # Fetch more candidates when filtering for GLB
    fetch_size = min(limit * 4, 24) if require_glb else min(limit, 24)

    url = _IKEA_SEARCH_URL.format(country=country, lang=lang)
    params = {
        "q": query,
        "size": fetch_size,
        "types": "PRODUCT",
    }
    headers = {
        "Accept": "application/json",
        "User-Agent": "HomeDesigner/1.0",
    }

    words = query.split()
    if len(words) > 3:
        query = " ".join(words[:3])
        params["q"] = query

    logger.info("Searching IKEA: query=%r country=%s fetch=%d need=%d glb=%s", query, country, fetch_size, limit, require_glb)

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

    candidates: list[FurnitureItem] = []
    for item_wrapper in items_data:
        product = item_wrapper.get("product", item_wrapper)
        parsed = _parse_product(product, country, lang)
        if parsed:
            candidates.append(parsed)

    if not require_glb:
        results = candidates[:limit]
        logger.info("IKEA search for %r returned %d results (no GLB filter)", query, len(results))
        return results

    # Try GLB extraction for all candidates in parallel, then take first `limit` with GLB
    sem = asyncio.Semaphore(5)

    async def _extract_with_sem(item: FurnitureItem) -> FurnitureItem:
        if not item.product_url:
            return item
        async with sem:
            glb_url = await extract_ikea_glb(item.product_url)
            if glb_url:
                item.glb_url = glb_url
                logger.info("GLB found for %s: %s", item.name, glb_url)
            else:
                logger.info("No GLB for %s, skipping", item.name)
            return item

    candidates = list(await asyncio.gather(*[_extract_with_sem(c) for c in candidates]))
    results: list[FurnitureItem] = [c for c in candidates if c.glb_url][:limit]

    logger.info("IKEA search for %r: %d/%d candidates have GLB", query, len(results), len(candidates))
    return results
