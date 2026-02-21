"""Sketchfab Data API v3 — search and download free GLB models."""

import logging

import httpx

from ..config import SKETCHFAB_API_TOKEN

logger = logging.getLogger(__name__)

_BASE = "https://api.sketchfab.com/v3"
_SEARCH_URL = f"{_BASE}/search"
_MODEL_URL = f"{_BASE}/models"


def _auth_headers() -> dict[str, str]:
    if SKETCHFAB_API_TOKEN:
        return {"Authorization": f"Token {SKETCHFAB_API_TOKEN}"}
    return {}


async def search_sketchfab(
    query: str,
    *,
    downloadable: bool = True,
    max_results: int = 5,
) -> list[dict]:
    """Search Sketchfab for 3D models matching a query.

    Args:
        query: Search text (e.g. "IKEA KALLAX shelf").
        downloadable: Only return models that can be downloaded.
        max_results: Maximum number of results to return.

    Returns:
        List of dicts with keys: uid, name, thumbnail_url, vertex_count, is_downloadable.
    """
    params: dict = {
        "type": "models",
        "q": query,
        "downloadable": str(downloadable).lower(),
        "sort_by": "-relevance",
        "count": min(max_results, 24),
    }

    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(
                _SEARCH_URL,
                params=params,
                headers=_auth_headers(),
            )
            resp.raise_for_status()
            data = resp.json()
    except httpx.HTTPError as exc:
        logger.warning("Sketchfab search failed for '%s': %s", query, exc)
        return []

    results = []
    for model in data.get("results", [])[:max_results]:
        thumbnail = ""
        thumbnails = model.get("thumbnails", {}).get("images", [])
        if thumbnails:
            # Pick a medium-sized thumbnail
            for t in thumbnails:
                if t.get("width", 0) >= 200:
                    thumbnail = t.get("url", "")
                    break
            if not thumbnail:
                thumbnail = thumbnails[0].get("url", "")

        results.append({
            "uid": model.get("uid", ""),
            "name": model.get("name", ""),
            "thumbnail_url": thumbnail,
            "vertex_count": model.get("vertexCount", 0),
            "is_downloadable": model.get("isDownloadable", False),
        })

    logger.info("Sketchfab: found %d results for '%s'", len(results), query)
    return results


async def get_download_url(model_uid: str) -> str | None:
    """Get the GLB download URL for a Sketchfab model.

    Requires a valid SKETCHFAB_API_TOKEN with download permissions.

    Args:
        model_uid: The model's unique identifier.

    Returns:
        Temporary download URL for the glTF archive, or None on failure.
    """
    if not SKETCHFAB_API_TOKEN:
        logger.warning("SKETCHFAB_API_TOKEN not set — cannot download models")
        return None

    url = f"{_MODEL_URL}/{model_uid}/download"

    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(url, headers=_auth_headers())
            resp.raise_for_status()
            data = resp.json()
    except httpx.HTTPError as exc:
        logger.warning("Sketchfab download failed for %s: %s", model_uid, exc)
        return None

    # Prefer GLB format, fall back to glTF
    if "glb" in data:
        return data["glb"]["url"]
    if "gltf" in data:
        return data["gltf"]["url"]

    logger.warning("Sketchfab: no GLB/glTF download for model %s", model_uid)
    return None
