"""Furniture search workflow — generates shopping list via Claude, then searches IKEA."""

import asyncio
import json
import logging
import uuid

from ..agents.scraper import search_ikea
from ..db import get_session, update_job, update_session, upsert_furniture
from ..models.schemas import FurnitureItem, RoomData, ShoppingListItem, UserPreferences
from ..prompts.shopping_list import shopping_list_prompt
from ..tools.llm import call_claude

logger = logging.getLogger(__name__)


async def _generate_shopping_list(
    room: RoomData,
    preferences: UserPreferences,
) -> list[ShoppingListItem]:
    """Ask Claude to generate a shopping list from room data + preferences."""
    prompt = shopping_list_prompt(room, preferences)
    logger.info("Generating shopping list for room=%s style=%s", room.name, preferences.style)

    raw = await call_claude(
        messages=[{"role": "user", "content": prompt}],
        temperature=0.4,
    )

    # Strip markdown fences if Claude wraps it
    text = raw.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1] if "\n" in text else text[3:]
        if text.endswith("```"):
            text = text[:-3]
        text = text.strip()

    try:
        items_raw = json.loads(text)
    except json.JSONDecodeError:
        logger.error("Failed to parse shopping list JSON:\n%s", text[:500])
        return []

    if not isinstance(items_raw, list):
        logger.error("Shopping list is not a list: %s", type(items_raw))
        return []

    items: list[ShoppingListItem] = []
    for entry in items_raw:
        try:
            items.append(ShoppingListItem(**entry))
        except Exception as e:
            logger.warning("Skipping invalid shopping list entry: %s — %s", entry, e)

    logger.info("Generated %d shopping list items", len(items))
    return items


async def _search_for_item(
    item: ShoppingListItem,
    session_id: str,
    country: str = "fr",
) -> list[FurnitureItem]:
    """Search IKEA for a single shopping list item and save results to DB."""
    results = await search_ikea(item.query, country=country, limit=5)

    saved: list[FurnitureItem] = []
    for furniture in results:
        row = {
            "id": furniture.id or uuid.uuid4().hex[:16],
            "session_id": session_id,
            "retailer": furniture.retailer,
            "name": furniture.name,
            "price": furniture.price,
            "currency": furniture.currency,
            "image_url": furniture.image_url,
            "product_url": furniture.product_url,
            "glb_url": furniture.glb_url,
            "category": item.item,
            "selected": False,
        }
        if furniture.dimensions:
            row["dimensions"] = furniture.dimensions.model_dump()
        try:
            upsert_furniture(row)
            saved.append(furniture)
        except Exception as e:
            logger.warning("Failed to save furniture %s: %s", furniture.name, e)

    return saved


async def search_furniture(session_id: str, job_id: str) -> list[FurnitureItem]:
    """Run the full furniture search pipeline for a session.

    1. Load session data (room + preferences)
    2. Generate a shopping list via Claude
    3. Search IKEA in parallel for each item
    4. Save results to DB and update job status

    Args:
        session_id: The design session ID.
        job_id: The job ID for status tracking.

    Returns:
        All found FurnitureItem results.
    """
    try:
        update_job(job_id, {"status": "running", "trace": [{"step": "started"}]})

        # 1. Load session
        session = get_session(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")

        # Parse room data — use first room if available, else build default
        room_data_raw = session.get("room_data")
        if room_data_raw and isinstance(room_data_raw, dict):
            rooms = room_data_raw.get("rooms", [])
            if rooms:
                room = RoomData(**rooms[0])
            else:
                room = RoomData(**room_data_raw)
        else:
            room = RoomData(
                name="Living Room",
                width_m=4.0,
                length_m=5.0,
                height_m=2.7,
                area_sqm=20.0,
            )

        # Parse preferences
        prefs_raw = session.get("preferences", {})
        preferences = UserPreferences(**(prefs_raw or {}))

        update_job(job_id, {"trace": [{"step": "generating_shopping_list"}]})

        # 2. Generate shopping list
        shopping_list = await _generate_shopping_list(room, preferences)
        if not shopping_list:
            update_job(job_id, {
                "status": "completed",
                "trace": [{"step": "no_items", "message": "Claude returned empty shopping list"}],
            })
            return []

        # Save shopping list to session
        update_session(session_id, {
            "furniture_list": [item.model_dump() for item in shopping_list],
        })

        update_job(job_id, {
            "trace": [{"step": "searching_ikea", "items": len(shopping_list)}],
        })

        # 3. Search IKEA in parallel for all items
        tasks = [_search_for_item(item, session_id) for item in shopping_list]
        results_nested = await asyncio.gather(*tasks, return_exceptions=True)

        # Flatten results, skip errors
        all_items: list[FurnitureItem] = []
        for result in results_nested:
            if isinstance(result, list):
                all_items.extend(result)
            elif isinstance(result, Exception):
                logger.warning("Search task failed: %s", result)

        # 4. Update job as completed
        update_job(job_id, {
            "status": "completed",
            "trace": [
                {"step": "done", "total_items": len(all_items)},
            ],
        })

        # Update session with found furniture and status
        update_session(session_id, {
            "status": "furniture_found",
            "furniture_list": [item.model_dump() for item in all_items],
        })

        logger.info(
            "Furniture search complete: session=%s items=%d", session_id, len(all_items)
        )
        return all_items

    except Exception as e:
        logger.error("Furniture search pipeline failed: %s", e, exc_info=True)
        try:
            update_job(job_id, {
                "status": "failed",
                "trace": [{"step": "error", "message": str(e)}],
            })
            update_session(session_id, {"status": "searching_failed"})
        except Exception:
            pass
        return []
