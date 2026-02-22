"""Furniture placement workflow — zone-based parallel Gemini placement + verification loop."""

import asyncio
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
    FurnitureZone,
    PlacementResult,
    Position3D,
    RoomData,
    ZoneDecomposition,
)
from ..models.verification import PlacementVerificationResult
from ..prompts.fix_placement import fix_placement_prompt
from ..prompts.placement import placement_prompt
from ..prompts.verify_placement import verify_placement_prompt
from ..prompts.zone_decomposition import zone_decomposition_prompt
from ..prompts.zone_placement import zone_placement_prompt
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
QUALITY_THRESHOLD = 0.75
MAX_VERIFY_ITERATIONS = 3


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


# ---------------------------------------------------------------------------
# Phase 1: Zone Decomposition
# ---------------------------------------------------------------------------

async def _decompose_zones(
    room: RoomData,
    furniture: list[FurnitureItem],
    all_rooms: list[RoomData] | None,
    input_images: list[str],
    trace: list[dict],
    job_id: str,
) -> ZoneDecomposition | None:
    """Ask Gemini to divide the room into functional zones. Returns None on failure."""
    t0 = time.time()
    trace.append(_trace_event("zone_decomposition", "Decomposing room into zones"))
    db.update_job(job_id, {"trace": trace})

    prompt = zone_decomposition_prompt(room, furniture, all_rooms)
    raw = await call_gemini_with_images(prompt, input_images)
    duration_ms = (time.time() - t0) * 1000

    trace.append(_trace_event(
        "zone_decomposition_result",
        f"Zone decomposition response ({len(raw)} chars)",
        duration_ms=round(duration_ms),
        input_prompt=prompt[:4000],
        output_text=raw[:4000],
        input_images=input_images,
        model=GEMINI_MODEL,
    ))
    db.update_job(job_id, {"trace": trace})

    try:
        json_str = _extract_json(raw)
        data = json.loads(json_str)
        decomposition = ZoneDecomposition.model_validate(data)

        # Validate: every furniture item must be assigned to exactly one zone
        furniture_ids = {f.id for f in furniture}
        assigned_ids: set[str] = set()
        for zone in decomposition.zones:
            for fid in zone.furniture_ids:
                if fid in assigned_ids:
                    logger.warning("Zone decomposition: item %s assigned to multiple zones", fid)
                assigned_ids.add(fid)

        unassigned = furniture_ids - assigned_ids
        if unassigned:
            logger.warning("Zone decomposition: %d items unassigned: %s", len(unassigned), unassigned)
            # Add unassigned items to the largest zone
            if decomposition.zones:
                largest = max(decomposition.zones, key=lambda z: len(z.furniture_ids))
                largest.furniture_ids.extend(unassigned)
                logger.info("Added unassigned items to zone '%s'", largest.name)

        logger.info(
            "Zone decomposition: %d zones, %s",
            len(decomposition.zones),
            [(z.name, len(z.furniture_ids)) for z in decomposition.zones],
        )
        return decomposition

    except Exception as e:
        logger.warning("Zone decomposition failed: %s", e)
        trace.append(_trace_event(
            "zone_decomposition_error",
            f"Zone decomposition failed: {e}, falling back to single-call placement",
        ))
        db.update_job(job_id, {"trace": trace})
        return None


# ---------------------------------------------------------------------------
# Phase 2: Per-Zone Parallel Placement
# ---------------------------------------------------------------------------

async def _place_zone(
    zone: FurnitureZone,
    room: RoomData,
    furniture: list[FurnitureItem],
    other_zones: list[FurnitureZone],
    input_images: list[str],
    zone_index: int,
    trace: list[dict],
    job_id: str,
) -> list[FurniturePlacement]:
    """Place furniture in a single zone. Returns list of placements."""
    furniture_map = {f.id: f for f in furniture}
    zone_furniture = [furniture_map[fid] for fid in zone.furniture_ids if fid in furniture_map]

    if not zone_furniture:
        logger.warning("Zone '%s' has no matching furniture items", zone.name)
        return []

    t0 = time.time()
    prompt = zone_placement_prompt(zone, room, zone_furniture, other_zones)
    raw = await call_gemini_with_images(prompt, input_images)
    duration_ms = (time.time() - t0) * 1000

    # Thread-safe trace append — we'll add to trace after gather
    logger.info(
        "Zone '%s' placement: %d chars in %.1fs",
        zone.name, len(raw), duration_ms / 1000,
    )

    try:
        json_str = _extract_json(raw)
        data = json.loads(json_str)
        result = PlacementResult.model_validate(data)
        return result.placements
    except Exception as e:
        logger.warning("Zone '%s' placement parse failed: %s", zone.name, e)
        return []


async def _zone_placement_pipeline(
    room: RoomData,
    furniture: list[FurnitureItem],
    all_rooms: list[RoomData] | None,
    input_images: list[str],
    trace: list[dict],
    job_id: str,
) -> list[FurniturePlacement] | None:
    """Run zone decomposition + parallel per-zone placement. Returns None on failure."""

    # Phase 1: Decompose
    decomposition = await _decompose_zones(
        room, furniture, all_rooms, input_images, trace, job_id,
    )
    if decomposition is None or len(decomposition.zones) == 0:
        return None

    # Phase 2: Parallel per-zone placement
    t0 = time.time()
    trace.append(_trace_event(
        "zone_placement_start",
        f"Placing furniture in {len(decomposition.zones)} zones in parallel",
    ))
    db.update_job(job_id, {"trace": trace})

    tasks = []
    for i, zone in enumerate(decomposition.zones):
        other_zones = [z for z in decomposition.zones if z.name != zone.name]
        tasks.append(
            _place_zone(zone, room, furniture, other_zones, input_images, i, trace, job_id)
        )

    zone_results = await asyncio.gather(*tasks, return_exceptions=True)
    duration_ms = (time.time() - t0) * 1000

    # Phase 3: Merge results
    all_placements: list[FurniturePlacement] = []
    placed_ids: set[str] = set()

    for i, (zone, result) in enumerate(zip(decomposition.zones, zone_results)):
        if isinstance(result, Exception):
            logger.warning("Zone '%s' failed: %s", zone.name, result)
            trace.append(_trace_event(
                f"zone_placement_error_{i}",
                f"Zone '{zone.name}' failed: {result}",
            ))
            continue

        for p in result:
            if p.item_id not in placed_ids:
                all_placements.append(p)
                placed_ids.add(p.item_id)

        trace.append(_trace_event(
            f"zone_placement_result_{i}",
            f"Zone '{zone.name}': placed {len(result)} items",
            data={
                "zone": zone.name,
                "items": [p.name for p in result] if not isinstance(result, Exception) else [],
                "polygon": zone.polygon,
            },
        ))

    trace.append(_trace_event(
        "zone_placement_merged",
        f"Merged {len(all_placements)} placements from {len(decomposition.zones)} zones",
        duration_ms=round(duration_ms),
        data={"total_items": len(all_placements), "zones": len(decomposition.zones)},
    ))
    db.update_job(job_id, {"trace": trace})

    # Check if we got enough items
    if len(all_placements) < len(furniture) * 0.5:
        logger.warning(
            "Zone pipeline placed only %d/%d items, falling back",
            len(all_placements), len(furniture),
        )
        return None

    logger.info(
        "Zone pipeline: %d/%d items placed across %d zones",
        len(all_placements), len(furniture), len(decomposition.zones),
    )
    return all_placements


# ---------------------------------------------------------------------------
# Legacy single-call placement (fallback)
# ---------------------------------------------------------------------------

async def _single_call_placement(
    room: RoomData,
    furniture: list[FurnitureItem],
    all_rooms: list[RoomData] | None,
    input_images: list[str],
    dims_map: dict[str, FurnitureDimensions | None],
    original_floorplan_url: str | None,
    room_diagram_url: str,
    trace: list[dict],
    job_id: str,
) -> PlacementResult:
    """Original single-call placement as fallback."""
    prompt = placement_prompt(room, furniture, all_rooms=all_rooms)
    errors: list[str] = []
    result: PlacementResult | None = None

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

    return result


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

async def place_furniture(session_id: str, job_id: str) -> PlacementResult:
    """Run the placement pipeline: zone decomposition → parallel placement → verify/fix.

    Falls back to single-call placement if zone decomposition fails.
    """
    trace: list[dict] = []

    try:
        trace.append(_trace_event("started", "Placement pipeline started (zone-based)"))
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

        # Pre-render room context images
        room_diagram_url = render_placement_data_url(room, [], furniture)
        room_3d_views: list[str] = []
        if room_glb_url:
            try:
                room_3d_views = await render_scene_3d_views(
                    room_glb_url, [], furniture, all_rooms,
                )
            except Exception as e:
                logger.warning("Failed to render 3D views for initial placement: %s", e)

        # Build image list: floorplan + 3D views + 2D diagram
        input_images: list[str] = []
        if floorplan_url:
            input_images.append(floorplan_url)
        input_images.extend(room_3d_views)
        input_images.append(room_diagram_url)

        # === Phase 1+2: Zone-based parallel placement ===
        zone_placements = await _zone_placement_pipeline(
            room, furniture, all_rooms, input_images, trace, job_id,
        )

        if zone_placements is not None:
            result = PlacementResult(placements=zone_placements)
            logger.info("Using zone-based placement: %d items", len(result.placements))
        else:
            # Fallback to single-call placement
            logger.info("Falling back to single-call placement")
            trace.append(_trace_event("fallback", "Zone pipeline failed, using single-call placement"))
            db.update_job(job_id, {"trace": trace})
            result = await _single_call_placement(
                room, furniture, all_rooms, input_images, dims_map,
                original_floorplan_url, room_diagram_url, trace, job_id,
            )

        # === Phase 4: Verify → Fix loop ===
        for iteration in range(MAX_VERIFY_ITERATIONS):
            t0 = time.time()
            trace.append(_trace_event(
                f"verify_{iteration}",
                f"Verify iteration {iteration}: rendering 3D views",
            ))
            db.update_job(job_id, {"trace": trace})

            try:
                # 1. Render views for verification
                verify_images: list[str] = []
                if room_glb_url:
                    scene_urls = await render_scene_3d_views(
                        room_glb_url, result.placements, furniture, all_rooms,
                    )
                    verify_images.extend(scene_urls)
                # Always include labeled 2D diagram so Gemini can match names
                diagram_url = render_placement_data_url(room, result.placements, furniture)
                verify_images.append(diagram_url)

                # 2. Ask Gemini to VERIFY (structured result, not new placement)
                v_prompt = verify_placement_prompt(room, furniture, result.model_dump())
                verify_raw = await call_gemini_with_images(v_prompt, verify_images)
                duration_ms = (time.time() - t0) * 1000

                verify_json_str = _extract_json(verify_raw)
                verify_data = json.loads(verify_json_str)

                try:
                    verification = PlacementVerificationResult.model_validate(verify_data)
                except Exception:
                    verification = PlacementVerificationResult(
                        answers=[], visual_issues=[], overall_score=0.0,
                        summary=verify_data.get("summary", "Parse error"),
                    )

                score = verification.overall_score
                n_issues = len(verification.visual_issues)

                trace.append(_trace_event(
                    f"verify_result_{iteration}",
                    f"Score: {score:.2f}, {n_issues} issues",
                    duration_ms=round(duration_ms),
                    input_prompt=v_prompt[:4000],
                    output_text=verify_raw[:4000],
                    model=GEMINI_MODEL,
                    image_url=verify_images[0] if verify_images else None,
                    input_images=verify_images,
                    data={
                        "score": score,
                        "issues": n_issues,
                        "iteration": iteration,
                        "summary": verification.summary[:200],
                    },
                ))
                db.update_job(job_id, {"trace": trace})

                logger.info(
                    "Verify iteration %d: score=%.2f issues=%d",
                    iteration, score, n_issues,
                )

                # 3. Check quality threshold
                if score >= QUALITY_THRESHOLD:
                    logger.info("Quality met at iteration %d (%.2f >= %.2f)",
                                iteration, score, QUALITY_THRESHOLD)
                    break

                # 4. Fix — send verification feedback to Gemini
                if iteration < MAX_VERIFY_ITERATIONS - 1:
                    t1 = time.time()
                    trace.append(_trace_event(
                        f"fix_{iteration}",
                        f"Fixing placement (score {score:.2f} < {QUALITY_THRESHOLD})",
                    ))
                    db.update_job(job_id, {"trace": trace})

                    f_prompt = fix_placement_prompt(
                        room, furniture, result.model_dump(), verification.model_dump(),
                    )
                    fix_raw = await call_gemini_with_images(f_prompt, verify_images)
                    fix_duration = (time.time() - t1) * 1000

                    trace.append(_trace_event(
                        f"fix_result_{iteration}",
                        "Fix complete",
                        duration_ms=round(fix_duration),
                        input_prompt=f_prompt[:4000],
                        output_text=fix_raw[:4000],
                        model=GEMINI_MODEL,
                    ))
                    db.update_job(job_id, {"trace": trace})

                    fix_json_str = _extract_json(fix_raw)
                    fix_data = json.loads(fix_json_str)
                    fixed = PlacementResult.model_validate(fix_data)

                    if len(fixed.placements) >= len(result.placements) * 0.5:
                        result = fixed
                        logger.info("Fix applied: %d items", len(result.placements))
                    else:
                        logger.warning(
                            "Fix returned too few items (%d), keeping current",
                            len(fixed.placements),
                        )
                        break

            except Exception as verify_err:
                logger.warning("Verify/fix iteration %d failed: %s", iteration, verify_err)
                trace.append(_trace_event(
                    f"verify_error_{iteration}",
                    f"Verify/fix failed: {verify_err}",
                    duration_ms=round((time.time() - t0) * 1000),
                ))
                db.update_job(job_id, {"trace": trace})
                break

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
