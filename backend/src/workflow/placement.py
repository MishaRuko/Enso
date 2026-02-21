"""Furniture placement workflow — Gemini spatial reasoning + validation loop."""

import json
import logging
import re
import time

from .. import db
from ..config import GEMINI_MODEL
from ..models.schemas import (
    FurnitureDimensions,
    FurnitureItem,
    FurniturePlacement,
    PlacementResult,
    Position3D,
    RoomData,
)
from ..prompts.placement import placement_prompt
from ..tools.llm import call_gemini_with_images
from ..tools.placement_renderer import render_placement_data_url
from ..tools.placement_validator import validate_placements
from ..tools.scene_renderer import render_scene_3d_views
from .floorplan import _to_data_url, pick_primary_room

logger = logging.getLogger(__name__)


def _trace_event(step: str, message: str, **kwargs) -> dict:
    evt = {"step": step, "message": message, "timestamp": time.time()}
    evt.update(kwargs)
    return evt

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


def _clamp_placements(
    placements: list[FurniturePlacement],
    room: RoomData,
    dims_map: dict[str, FurnitureDimensions | None],
) -> list[FurniturePlacement]:
    """Clamp placement positions so items stay within room bounds (apartment-absolute)."""
    x_min = room.x_offset_m
    x_max = room.x_offset_m + room.width_m
    z_min = room.z_offset_m
    z_max = room.z_offset_m + room.length_m

    clamped = []
    for p in placements:
        dims = dims_map.get(p.item_id)
        half_w = (dims.width_cm / 200) if dims else 0.25
        half_d = (dims.depth_cm / 200) if dims else 0.25

        # Swap for rotated items
        rot = p.rotation_y_degrees % 360
        if 45 < rot < 135 or 225 < rot < 315:
            half_w, half_d = half_d, half_w

        x = max(x_min + half_w, min(x_max - half_w, p.position.x))
        z = max(z_min + half_d, min(z_max - half_d, p.position.z))
        y = p.position.y

        clamped.append(FurniturePlacement(
            item_id=p.item_id,
            name=p.name,
            position=Position3D(x=round(x, 3), y=round(y, 3), z=round(z, 3)),
            rotation_y_degrees=p.rotation_y_degrees,
            reasoning=p.reasoning,
        ))
    return clamped


async def place_furniture(session_id: str, job_id: str) -> PlacementResult:
    """Run the placement pipeline: prompt Gemini, validate, re-prompt if needed.

    Args:
        session_id: Design session ID.
        job_id: Job ID for progress tracking.

    Returns:
        PlacementResult with validated furniture placements.
    """
    trace: list[dict] = []

    try:
        trace.append(_trace_event("started", "Placement pipeline started"))
        db.update_job(job_id, {"status": "running", "trace": trace})

        session = db.get_session(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")

        room_data_raw = session.get("room_data")
        if room_data_raw and isinstance(room_data_raw, dict):
            room = RoomData(**pick_primary_room(room_data_raw))
            all_rooms = [RoomData(**r) for r in room_data_raw.get("rooms", [])]
        else:
            raise ValueError(f"Session {session_id} has no room_data")

        furniture_rows = db.list_furniture(session_id, selected_only=True)
        if not furniture_rows:
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
        room_glb_url = session.get("room_glb_url")
        floorplan_url = session.get("floorplan_url")
        original_floorplan_url = floorplan_url
        if floorplan_url:
            floorplan_url = await _to_data_url(floorplan_url)

        db.update_session(session_id, {"status": "placing"})

        prompt = placement_prompt(room, furniture, all_rooms=all_rooms)
        errors: list[str] = []
        result: PlacementResult | None = None

        # Pre-render room context images for initial placement
        room_diagram_url = render_placement_data_url(room, [], furniture)
        # Also render 3D top-down if GLB available
        room_3d_topdown_url = None
        if room_glb_url:
            try:
                scene_views = await render_scene_3d_views(
                    room_glb_url, [], furniture, all_rooms,
                )
                if scene_views:
                    room_3d_topdown_url = scene_views[0]  # Top-down view
            except Exception as e:
                logger.warning("Failed to render 3D top-down for initial placement: %s", e)

        for attempt in range(1, MAX_ATTEMPTS + 1):
            t0 = time.time()
            trace.append(_trace_event(
                f"gemini_attempt_{attempt}", f"Calling Gemini (attempt {attempt})",
            ))
            db.update_job(job_id, {"trace": trace})

            if errors:
                error_feedback = (
                    "\n\n## Validation Errors from Previous Attempt\n"
                    "Fix these issues in your new placement:\n"
                    + "\n".join(f"- {e}" for e in errors)
                )
                full_prompt = prompt + error_feedback
            else:
                full_prompt = prompt

            # Send floorplan + room images as reference
            input_images: list[str] = []
            if floorplan_url:
                input_images.append(floorplan_url)
            if room_3d_topdown_url:
                input_images.append(room_3d_topdown_url)
            input_images.append(room_diagram_url)

            raw = await call_gemini_with_images(full_prompt, input_images)

            duration_ms = (time.time() - t0) * 1000
            trace.append(_trace_event(
                f"gemini_response_{attempt}",
                f"Gemini response ({len(raw)} chars)",
                duration_ms=round(duration_ms),
                input_prompt=full_prompt[:4000],
                input_image=original_floorplan_url,
                image_url=room_diagram_url,
                input_images=input_images,
                output_text=raw[:4000],
                model=GEMINI_MODEL,
            ))
            db.update_job(job_id, {"trace": trace})

            logger.info("Attempt %d: got Gemini response (%d chars)", attempt, len(raw))
            json_str = _extract_json(raw)
            try:
                data = json.loads(json_str)
            except json.JSONDecodeError:
                logger.warning("Attempt %d: failed to parse JSON:\n%s", attempt, json_str[:500])
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

            errors = validate_placements(room, result.placements, dims_map)
            if not errors:
                logger.info("Placement validated on attempt %d with %d items", attempt, len(result.placements))
                break

            logger.info("Attempt %d: %d validation errors, retrying", attempt, len(errors))

        if result is None:
            raise ValueError("Gemini returned no parseable placement after all attempts")

        if errors:
            logger.warning(
                "Accepting placement with %d remaining validation warnings after %d attempts",
                len(errors), MAX_ATTEMPTS,
            )

        # --- Verification: render 3D scene views and ask Gemini to review ---
        t0 = time.time()
        trace.append(_trace_event("verification", "Rendering 3D scene views for verification"))
        db.update_job(job_id, {"trace": trace})

        try:
            # Render actual 3D views of the room GLB with furniture boxes
            if room_glb_url:
                scene_urls = await render_scene_3d_views(
                    room_glb_url, result.placements, furniture, all_rooms,
                )
            else:
                scene_urls = []


            furniture_info = []
            for f in furniture:
                entry = {"item_id": f.id, "name": f.name, "category": f.category}
                if f.dimensions:
                    entry["dimensions_cm"] = {
                        "width": f.dimensions.width_cm,
                        "depth": f.dimensions.depth_cm,
                        "height": f.dimensions.height_cm,
                    }
                furniture_info.append(entry)

            verify_prompt = (
                "You are an expert interior designer reviewing a furniture layout.\n\n"
                "You are given 3D renders of the actual room model with colored furniture boxes:\n"
                "1. TOP-DOWN view — bird's eye showing furniture positions in the room\n"
                "2. SOUTH-WEST isometric view — 3D perspective\n"
                "3. SOUTH-EAST isometric view — 3D perspective\n"
                "4. NORTH-EAST isometric view — 3D perspective\n\n"
                "Colored boxes represent furniture items placed in the room.\n\n"
                f"## Room\n{room.name}, {room.width_m}m wide x {room.length_m}m long, "
                f"height {room.height_m}m\n\n"
                "## Coordinate System\n"
                "- Origin (0,0,0) is south-west corner at floor level.\n"
                "- X axis: west → east (width). Z axis: south → north (length). Y = 0 (floor).\n"
                "- All values in METRES.\n\n"
                f"## Furniture Items\n```json\n{json.dumps(furniture_info, indent=2)}\n```\n\n"
                "## Current Placement\n"
                f"```json\n{json.dumps(result.model_dump(), indent=2)}\n```\n\n"
                "## Your Task\n"
                "Review all views and fix any issues:\n"
                "- Furniture overlapping or too close (< 0.6m clearance)\n"
                f"- Items placed outside the room (0,0) to ({room.width_m},{room.length_m})\n"
                "- Poor functional grouping (chairs far from tables, bed blocking door)\n"
                "- Wasted space or items crammed in one area\n"
                "- Items that should be against walls floating in the middle\n\n"
                "If the layout is already good, return it unchanged.\n"
                "You MUST include ALL items from the furniture list — do not drop any.\n\n"
                "Return ONLY valid JSON (no markdown fences):\n"
                '{"placements": [{"item_id": "...", "name": "...", '
                '"position": {"x": ..., "y": 0, "z": ...}, '
                '"rotation_y_degrees": ..., "reasoning": "..."}]}'
            )

            verify_raw = await call_gemini_with_images(verify_prompt, scene_urls)
            duration_ms = (time.time() - t0) * 1000

            trace.append(_trace_event(
                "verification_response",
                f"Gemini verification complete ({len(scene_urls)} 3D views)",
                duration_ms=round(duration_ms),
                input_prompt=verify_prompt[:4000],
                output_text=verify_raw[:4000],
                model=GEMINI_MODEL,
                image_url=scene_urls[0] if scene_urls else None,
                input_images=scene_urls,
            ))
            db.update_job(job_id, {"trace": trace})

            verify_json = _extract_json(verify_raw)
            verify_data = json.loads(verify_json)
            verified = PlacementResult.model_validate(verify_data)

            if len(verified.placements) >= len(result.placements) * 0.5:
                result = verified
                logger.info("Verification adjusted placement to %d items", len(result.placements))
            else:
                logger.warning("Verification returned too few items (%d), keeping original", len(verified.placements))

        except Exception as verify_err:
            logger.warning("Verification failed, keeping original placement: %s", verify_err)
            trace.append(_trace_event(
                "verification_error", f"Verification failed: {verify_err}",
                duration_ms=round((time.time() - t0) * 1000),
            ))
            db.update_job(job_id, {"trace": trace})

        # Clamp all placements so items stay within room bounds
        result = PlacementResult(placements=_clamp_placements(result.placements, room, dims_map))

        db.update_session(session_id, {
            "placements": result.model_dump(),
            "status": "placement_ready",
        })

        trace.append(_trace_event(
            "completed", f"Placed {len(result.placements)} items",
            data={"items_placed": len(result.placements)},
        ))
        db.update_job(job_id, {"status": "completed", "trace": trace})

        logger.info("Placement complete: session=%s items=%d", session_id, len(result.placements))
        return result

    except Exception as e:
        logger.error("Placement pipeline failed: %s", e, exc_info=True)
        trace.append(_trace_event("error", f"Placement failed: {e}", error=str(e)))
        try:
            db.update_job(job_id, {"status": "failed", "trace": trace})
            db.update_session(session_id, {"status": "placement_failed"})
        except Exception:
            pass
        raise
