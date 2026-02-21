"""3D model sourcing workflow — find or generate GLB models for furniture items.

Priority chain:
  1. IKEA GLB (free, instant) — extract from product page if retailer is IKEA
  2. Sketchfab search + download (free downloadable models)
  3. fal.ai TRELLIS 2 (AI-generated from product image, costs ~$0.05)
"""

import asyncio
import logging

from ..db import create_model, list_furniture, update_furniture
from ..models.schemas import FurnitureItem
from ..tools.fal_client import generate_3d_model
from ..tools.ikea_glb import extract_ikea_glb
from ..tools.sketchfab import get_download_url, search_sketchfab

logger = logging.getLogger(__name__)


async def source_3d_model(item: FurnitureItem) -> str | None:
    """Try to obtain a GLB model URL for a single furniture item.

    Attempts sources in priority order:
      1. IKEA GLB extraction (if product_url is IKEA)
      2. Sketchfab free downloadable search
      3. fal.ai TRELLIS 2 generation from product image

    Returns:
        GLB URL string or None if all sources fail.
    """
    item_label = f"{item.name} ({item.id})"

    # --- 1. IKEA GLB ---
    if item.product_url and "ikea" in item.product_url.lower():
        logger.info("[%s] Trying IKEA GLB extraction...", item_label)
        glb_url = await extract_ikea_glb(item.product_url)
        if glb_url:
            logger.info("[%s] Got IKEA GLB: %s", item_label, glb_url)
            return glb_url

    # --- 2. Sketchfab ---
    search_query = f"{item.name} furniture"
    if item.retailer:
        search_query = f"{item.retailer} {item.name}"

    logger.info("[%s] Searching Sketchfab for '%s'...", item_label, search_query)
    results = await search_sketchfab(search_query, max_results=3)

    for result in results:
        if not result.get("is_downloadable"):
            continue
        download_url = await get_download_url(result["uid"])
        if download_url:
            logger.info("[%s] Got Sketchfab GLB: %s", item_label, download_url)
            return download_url

    # --- 3. fal.ai TRELLIS 2 ---
    if item.image_url:
        logger.info("[%s] Generating 3D model via TRELLIS 2...", item_label)
        try:
            glb_url = await generate_3d_model(item.image_url, model="trellis-2")
            logger.info("[%s] Got TRELLIS GLB: %s", item_label, glb_url)
            return glb_url
        except Exception:
            logger.exception("[%s] TRELLIS 2 generation failed", item_label)

    logger.warning("[%s] No 3D model found from any source", item_label)
    return None


async def _source_single(item_dict: dict) -> tuple[str, str | None, str]:
    """Source a model for one item and return (item_id, glb_url, source_name)."""
    item = FurnitureItem(**item_dict)

    # Skip if already has a GLB
    if item.glb_url:
        return item.id, item.glb_url, "existing"

    glb_url = await source_3d_model(item)

    # Determine which source succeeded
    source = "none"
    if glb_url:
        if "ikea" in glb_url.lower():
            source = "ikea"
        elif "sketchfab" in glb_url.lower():
            source = "sketchfab"
        else:
            source = "trellis"

    return item.id, glb_url, source


async def source_all_models(session_id: str) -> dict:
    """Source 3D models for all furniture items in a session.

    Runs all sourcing tasks in parallel using asyncio.gather().
    Updates the furniture_items and models_3d tables.

    Returns:
        Summary dict with counts: {total, success, failed, skipped}.
    """
    items = list_furniture(session_id, selected_only=True)
    if not items:
        items = list_furniture(session_id)

    if not items:
        logger.info("No furniture items for session %s", session_id)
        return {"total": 0, "success": 0, "failed": 0, "skipped": 0}

    logger.info("Sourcing 3D models for %d items in session %s", len(items), session_id)

    # Run all sourcing tasks concurrently
    tasks = [_source_single(item) for item in items]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    summary = {"total": len(items), "success": 0, "failed": 0, "skipped": 0}

    for result in results:
        if isinstance(result, Exception):
            logger.exception("Model sourcing task failed: %s", result)
            summary["failed"] += 1
            continue

        item_id, glb_url, source = result

        if source == "existing":
            summary["skipped"] += 1
            continue

        if glb_url:
            # Update furniture item with GLB URL
            update_furniture(item_id, {"glb_url": glb_url})

            # Create record in models_3d table
            create_model(
                furniture_item_id=item_id,
                source=source,
                glb_url=glb_url,
                generation_cost=0.05 if source == "trellis" else 0,
            )
            summary["success"] += 1
        else:
            summary["failed"] += 1

    logger.info(
        "Session %s model sourcing complete: %d/%d success, %d failed, %d skipped",
        session_id,
        summary["success"],
        summary["total"],
        summary["failed"],
        summary["skipped"],
    )
    return summary
