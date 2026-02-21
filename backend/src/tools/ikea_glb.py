"""Extract GLB model URLs from IKEA product pages.

IKEA embeds 3D models (GLB format) via <model-viewer> elements and
fetches them at runtime. We parse the product page HTML to find these
URLs directly.
"""

import logging
import re

import httpx

logger = logging.getLogger(__name__)

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

# Patterns that IKEA uses for embedded GLB model URLs
_GLB_PATTERNS = [
    # model-viewer src attribute
    re.compile(r'<model-viewer[^>]+src=["\']([^"\']+\.glb[^"\']*)["\']', re.IGNORECASE),
    # Direct GLB URL references in page scripts / JSON-LD
    re.compile(r'(https?://[^\s"\'<>]+\.glb(?:\?[^\s"\'<>]*)?)', re.IGNORECASE),
    # USDZ fallback (can be converted or used directly)
    re.compile(r'(https?://[^\s"\'<>]+\.usdz(?:\?[^\s"\'<>]*)?)', re.IGNORECASE),
]


def _is_ikea_url(url: str) -> bool:
    return "ikea.com" in url or "ikea." in url


async def extract_ikea_glb(product_url: str) -> str | None:
    """Fetch an IKEA product page and extract the embedded GLB model URL.

    Args:
        product_url: Full URL to an IKEA product page.

    Returns:
        The GLB model URL if found, else None.
    """
    if not _is_ikea_url(product_url):
        logger.debug("Not an IKEA URL, skipping: %s", product_url)
        return None

    try:
        async with httpx.AsyncClient(follow_redirects=True, timeout=15) as client:
            resp = await client.get(product_url, headers=_HEADERS)
            resp.raise_for_status()
            html = resp.text
    except httpx.HTTPError as exc:
        logger.warning("Failed to fetch IKEA page %s: %s", product_url, exc)
        return None

    # Try each pattern in priority order (GLB first, then USDZ)
    for pattern in _GLB_PATTERNS:
        matches = pattern.findall(html)
        for match in matches:
            # Filter out tiny icons / thumbnails — real models are on IKEA CDNs
            if ".glb" in match.lower() and _looks_like_model_url(match):
                logger.info("Found IKEA GLB model: %s", match)
                return match

    logger.info("No GLB model found on IKEA page: %s", product_url)
    return None


def _looks_like_model_url(url: str) -> bool:
    """Heuristic: real 3D model URLs are on known IKEA asset domains."""
    known_domains = [
        "ikea.com",
        "ikea-static",
        "ikeaimg.com",
        "cloudfront.net",
        "amazonaws.com",
    ]
    return any(domain in url for domain in known_domains)
