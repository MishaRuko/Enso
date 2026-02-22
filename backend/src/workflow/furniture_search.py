"""Furniture search workflow — generates shopping list via Claude, then searches IKEA."""

import asyncio
import json
import logging
import time
import uuid

from ..agents.scraper import search_ikea
from ..config import CLAUDE_MODEL
from ..db import delete_session_furniture, get_session, update_job, update_session, upsert_furniture
from ..models.schemas import FurnitureItem, RoomData, ShoppingListItem, UserPreferences
from ..prompts.shopping_list import shopping_list_prompt
from ..tools.llm import call_claude
from ..workflow.floorplan import pick_primary_room

logger = logging.getLogger(__name__)


def _trace_event(step: str, message: str, **kwargs) -> dict:
    evt = {"step": step, "message": message, "timestamp": time.time()}
    evt.update(kwargs)
    return evt


async def _generate_shopping_list(
    room: RoomData,
    preferences: UserPreferences,
) -> tuple[list[ShoppingListItem], str, str]:
    """Ask Claude to generate a shopping list. Returns (items, prompt, raw_response)."""
    prompt = shopping_list_prompt(room, preferences)
    logger.info("Generating shopping list for room=%s style=%s", room.name, preferences.style)

    raw = await call_claude(
        messages=[{"role": "user", "content": prompt}],
        temperature=0.4,
    )

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
        return [], prompt, raw

    if not isinstance(items_raw, list):
        logger.error("Shopping list is not a list: %s", type(items_raw))
        return [], prompt, raw

    items: list[ShoppingListItem] = []
    for entry in items_raw:
        try:
            items.append(ShoppingListItem(**entry))
        except Exception as e:
            logger.warning("Skipping invalid shopping list entry: %s — %s", entry, e)

    logger.info("Generated %d shopping list items", len(items))
    return items, prompt, raw


async def _search_for_item(
    item: ShoppingListItem,
    session_id: str,
    country: str = "fr",
    room_width_cm: float = 0,
    room_length_cm: float = 0,
) -> dict:
    """Search IKEA for a single shopping list item, requiring GLB models.

    Returns a dict with items, query metadata, and timing for tracing.
    """
    t0 = time.time()
    results = await search_ikea(item.query, country=country, limit=1, require_glb=True)

    saved: list[FurnitureItem] = []
    skipped: list[str] = []
    for furniture in results:
        # Skip items too large for the room (with 30% margin)
        if furniture.dimensions and room_width_cm > 0:
            max_dim = max(furniture.dimensions.width_cm, furniture.dimensions.depth_cm)
            room_max = max(room_width_cm, room_length_cm)
            if max_dim > room_max * 0.8:
                logger.info(
                    "Skipping oversized %s (%dcm > room %dcm)", furniture.name, max_dim, room_max
                )
                skipped.append(f"{furniture.name} (oversized {max_dim:.0f}cm)")
                continue
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

    return {
        "items": saved,
        "query": item.query,
        "item_name": item.item,
        "candidates_found": len(results),
        "glb_found": any(f.glb_url for f in saved),
        "skipped": skipped,
        "duration_ms": round((time.time() - t0) * 1000),
    }


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
    trace: list[dict] = []

    try:
        trace.append(_trace_event("started", "Furniture search started"))
        update_job(job_id, {"status": "running", "trace": trace})

        # Clear stale furniture from previous runs
        delete_session_furniture(session_id)

        session = get_session(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")

        room_data_raw = session.get("room_data")
        if room_data_raw and isinstance(room_data_raw, dict):
            room = RoomData(**pick_primary_room(room_data_raw))
        else:
            room = RoomData(
                name="Living Room",
                width_m=4.0,
                length_m=5.0,
                height_m=2.7,
                area_sqm=20.0,
            )

        prefs_raw = session.get("preferences", {})
        preferences = UserPreferences(**(prefs_raw or {}))

        trace.append(
            _trace_event(
                "session_loaded",
                f"Room: {room.name} ({room.width_m}x{room.length_m}m)",
                data={
                    "room": room.name,
                    "width_m": room.width_m,
                    "length_m": room.length_m,
                    "area_sqm": room.area_sqm,
                    "style": preferences.style,
                },
            )
        )
        update_job(job_id, {"trace": trace})

        # Generate shopping list via Claude
        t0 = time.time()
        trace.append(_trace_event("shopping_list", "Generating shopping list via Claude"))
        update_job(job_id, {"trace": trace})

        shopping_list, prompt_used, raw_response = await _generate_shopping_list(room, preferences)
        duration_ms = (time.time() - t0) * 1000

        trace.append(
            _trace_event(
                "shopping_list",
                f"Claude returned {len(shopping_list)} items",
                duration_ms=round(duration_ms),
                input_prompt=prompt_used,
                output_text=raw_response[:4000],
                model=CLAUDE_MODEL,
                data={
                    "items": [
                        {"name": it.item, "query": it.query, "priority": it.priority}
                        for it in shopping_list
                    ],
                },
            )
        )
        update_job(job_id, {"trace": trace})

        if not shopping_list:
            trace.append(_trace_event("no_items", "Claude returned empty shopping list"))
            update_job(job_id, {"status": "completed", "trace": trace})
            return []

        update_session(
            session_id,
            {
                "furniture_list": [item.model_dump() for item in shopping_list],
            },
        )

        # Search IKEA in parallel
        queries = [item.query for item in shopping_list]
        t0 = time.time()
        trace.append(
            _trace_event(
                "searching_ikea",
                f"Searching IKEA for {len(shopping_list)} items",
                data={"queries": queries},
            )
        )
        update_job(job_id, {"trace": trace})

        room_w_cm = room.width_m * 100
        room_l_cm = room.length_m * 100
        tasks = [
            _search_for_item(item, session_id, room_width_cm=room_w_cm, room_length_cm=room_l_cm)
            for item in shopping_list
        ]
        results_nested = await asyncio.gather(*tasks, return_exceptions=True)

        all_items: list[FurnitureItem] = []
        errors_count = 0
        for i, result in enumerate(results_nested):
            if isinstance(result, dict):
                all_items.extend(result["items"])
                trace.append(
                    _trace_event(
                        f"search_item_{i}",
                        f"IKEA: '{result['item_name']}' → {len(result['items'])} found",
                        duration_ms=result["duration_ms"],
                        data={
                            "query": result["query"],
                            "glb_found": result["glb_found"],
                            "candidates": result["candidates_found"],
                            "skipped": result["skipped"],
                            "result_name": (result["items"][0].name if result["items"] else None),
                            "result_price": (result["items"][0].price if result["items"] else None),
                            "result_glb_url": (
                                result["items"][0].glb_url if result["items"] else None
                            ),
                        },
                    )
                )
            elif isinstance(result, Exception):
                errors_count += 1
                logger.warning("Search task failed: %s", result)
                trace.append(
                    _trace_event(
                        f"search_item_{i}",
                        f"IKEA search failed: {result}",
                        error=str(result),
                    )
                )

        duration_ms = (time.time() - t0) * 1000
        trace.append(
            _trace_event(
                "search_done",
                f"Found {len(all_items)} items ({errors_count} search errors)",
                duration_ms=round(duration_ms),
                data={
                    "total_found": len(all_items),
                    "errors": errors_count,
                    "items_with_glb": sum(1 for it in all_items if it.glb_url),
                },
            )
        )

        update_session(
            session_id,
            {
                "status": "furniture_found",
                "furniture_list": [item.model_dump() for item in all_items],
            },
        )

        trace.append(_trace_event("completed", "Furniture search complete"))
        update_job(job_id, {"status": "completed", "trace": trace})

        logger.info("Furniture search complete: session=%s items=%d", session_id, len(all_items))
        return all_items

    except Exception as e:
        logger.error("Furniture search pipeline failed: %s", e, exc_info=True)
        trace.append(_trace_event("error", f"Search failed: {e}", error=str(e)))
        try:
            update_job(job_id, {"status": "failed", "trace": trace})
            update_session(session_id, {"status": "searching_failed"})
        except Exception:
            pass
        return []
