"""Furniture placement workflow — Gemini spatial reasoning + validation loop."""

import json
import logging
import re

from .. import db
from ..models.schemas import (
    FurnitureDimensions,
    FurnitureItem,
    PlacementResult,
    RoomData,
)
from ..prompts.placement import placement_prompt
from ..tools.llm import call_gemini, call_gemini_with_image
from ..tools.placement_validator import validate_placements
from .floorplan import _to_data_url

logger = logging.getLogger(__name__)

MAX_ATTEMPTS = 1


def _extract_json(text: str) -> str:
    """Strip markdown fences or surrounding prose to isolate JSON."""
    m = re.search(r"```(?:json)?\s*(\{[\s\S]*\})\s*```", text)
    if m:
        return m.group(1)
    m = re.search(r"(\{[\s\S]*\})", text)
    if m:
        return m.group(1)
    return text


def _build_dims_map(
    furniture: list[FurnitureItem],
) -> dict[str, FurnitureDimensions | None]:
    """Build a lookup from item_id to its dimensions."""
    return {f.id: f.dimensions for f in furniture}


async def place_furniture(session_id: str, job_id: str) -> PlacementResult:
    """Run the placement pipeline: prompt Gemini, validate, re-prompt if needed.

    Args:
        session_id: Design session ID.
        job_id: Job ID for progress tracking.

    Returns:
        PlacementResult with validated furniture placements.
    """
    try:
        db.update_job(job_id, {"status": "running", "trace": [{"step": "started"}]})

        # 1. Load session data
        session = db.get_session(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")

        # Parse room — use first room from floorplan analysis
        room_data_raw = session.get("room_data")
        if room_data_raw and isinstance(room_data_raw, dict):
            rooms = room_data_raw.get("rooms", [])
            if rooms:
                room = RoomData(**rooms[0])
            else:
                room = RoomData(**room_data_raw)
        else:
            raise ValueError(f"Session {session_id} has no room_data")

        # Load selected furniture from DB (cap at 15 to keep prompt manageable)
        furniture_rows = db.list_furniture(session_id, selected_only=True)
        if not furniture_rows:
            # Fall back to all furniture if none selected
            furniture_rows = db.list_furniture(session_id)
        if not furniture_rows:
            raise ValueError(f"Session {session_id} has no furniture items")
        if len(furniture_rows) > 15:
            logger.info("Capping furniture from %d to 15 for placement", len(furniture_rows))
            furniture_rows = furniture_rows[:15]

        furniture: list[FurnitureItem] = []
        for row in furniture_rows:
            dims = None
            if row.get("dimensions") and isinstance(row["dimensions"], dict):
                dims = FurnitureDimensions(**row["dimensions"])
            furniture.append(
                FurnitureItem(
                    id=row["id"],
                    retailer=row.get("retailer", ""),
                    name=row["name"],
                    price=row.get("price", 0),
                    currency=row.get("currency", "EUR"),
                    dimensions=dims,
                    image_url=row.get("image_url", ""),
                    product_url=row.get("product_url", ""),
                    glb_url=row.get("glb_url", ""),
                    category=row.get("category", ""),
                    selected=row.get("selected", False),
                )
            )

        dims_map = _build_dims_map(furniture)
        floorplan_url = session.get("floorplan_url")
        if floorplan_url:
            floorplan_url = await _to_data_url(floorplan_url)

        db.update_session(session_id, {"status": "placing"})

        # 2. Iterative placement with validation
        prompt = placement_prompt(room, furniture)
        errors: list[str] = []
        result: PlacementResult | None = None

        for attempt in range(1, MAX_ATTEMPTS + 1):
            db.update_job(
                job_id,
                {"trace": [{"step": f"gemini_attempt_{attempt}"}]},
            )

            # Build the full prompt — include previous errors for retry
            if errors:
                error_feedback = (
                    "\n\n## Validation Errors from Previous Attempt\n"
                    "Fix these issues in your new placement:\n"
                    + "\n".join(f"- {e}" for e in errors)
                )
                full_prompt = prompt + error_feedback
            else:
                full_prompt = prompt

            # Call Gemini (with or without floorplan image)
            if floorplan_url:
                raw = await call_gemini_with_image(full_prompt, floorplan_url)
            else:
                raw = await call_gemini(
                    [{"role": "user", "content": full_prompt}],
                    temperature=0.3,
                )

            # Parse response
            logger.info("Attempt %d: got Gemini response (%d chars)", attempt, len(raw))
            json_str = _extract_json(raw)
            logger.info("Attempt %d: extracted JSON (%d chars)", attempt, len(json_str) if json_str else 0)
            try:
                data = json.loads(json_str)
            except json.JSONDecodeError:
                logger.warning(
                    "Attempt %d: failed to parse JSON:\n%s", attempt, json_str[:500]
                )
                errors = [
                    "Your response was not valid JSON. Return ONLY a JSON object with a 'placements' array."
                ]
                continue

            try:
                result = PlacementResult.model_validate(data)
            except Exception as e:
                logger.warning("Attempt %d: invalid placement schema: %s", attempt, e)
                errors = [f"Invalid response schema: {e}. Follow the exact output format."]
                continue

            # Validate spatial constraints
            errors = validate_placements(room, result.placements, dims_map)
            if not errors:
                logger.info(
                    "Placement validated on attempt %d with %d items",
                    attempt,
                    len(result.placements),
                )
                break

            logger.info(
                "Attempt %d: %d validation errors, retrying", attempt, len(errors)
            )

        # Use best result even if some errors remain after max attempts
        if result is None:
            raise ValueError("Gemini returned no parseable placement after all attempts")

        if errors:
            logger.warning(
                "Accepting placement with %d remaining validation warnings after %d attempts",
                len(errors),
                MAX_ATTEMPTS,
            )

        # 3. Save placements to session
        db.update_session(
            session_id,
            {
                "placements": result.model_dump(),
                "status": "placement_ready",
            },
        )
        db.update_job(
            job_id,
            {
                "status": "completed",
                "trace": [
                    {"step": "completed", "items_placed": len(result.placements)},
                ],
            },
        )

        logger.info(
            "Placement complete: session=%s items=%d",
            session_id,
            len(result.placements),
        )
        return result

    except Exception as e:
        logger.error("Placement pipeline failed: %s", e, exc_info=True)
        try:
            db.update_job(
                job_id,
                {
                    "status": "failed",
                    "trace": [{"step": "error", "message": str(e)}],
                },
            )
            db.update_session(session_id, {"status": "placement_failed"})
        except Exception:
            pass
        raise
