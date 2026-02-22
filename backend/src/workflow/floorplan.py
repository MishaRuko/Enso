"""Floorplan processing pipeline — Gemini analysis + isometric render + Trellis v2 room GLB."""

import asyncio
import base64
import json
import logging
import re
import time

import httpx

from .. import db
from ..config import GEMINI_MODEL
from ..furniture_placement.grid_types import FloorPlanGrid
from ..models.schemas import FloorplanAnalysis
from ..prompts.floorplan_analysis import floorplan_analysis_prompt
from ..tools.fal_client import generate_room_model, upload_data_url_to_fal
from ..tools.llm import call_gemini_with_image
from ..tools.nanobananana import build_render_prompt, generate_colored_render

logger = logging.getLogger(__name__)


def pick_primary_room(room_data_raw: dict) -> dict:
    """Pick the largest room by area from room_data. Used by all pipeline stages."""
    rooms = room_data_raw.get("rooms", [])
    if not rooms:
        return room_data_raw
    return max(rooms, key=lambda r: r.get("area_sqm", 0))


def _trace_event(step: str, message: str, **kwargs) -> dict:
    """Build a structured trace event dict."""
    evt = {"step": step, "message": message, "timestamp": time.time()}
    evt.update(kwargs)
    return evt


async def _to_data_url(image_url: str) -> str:
    """Convert a URL to a base64 data URL. Needed for localhost URLs that external APIs can't reach."""
    if image_url.startswith("data:"):
        return image_url
    async with httpx.AsyncClient() as client:
        resp = await client.get(image_url)
        resp.raise_for_status()
        content_type = resp.headers.get("content-type", "image/png")
        b64 = base64.b64encode(resp.content).decode()
        return f"data:{content_type};base64,{b64}"


def _extract_json(text: str) -> str:
    """Strip markdown fences or surrounding prose to isolate JSON."""
    m = re.search(r"```(?:json)?\s*(\{[\s\S]*\})\s*```", text)
    if m:
        return m.group(1)
    m = re.search(r"(\{[\s\S]*\})", text)
    if m:
        return m.group(1)
    return text


def room_data_to_grid(analysis: FloorplanAnalysis, cell_size: float = 0.5) -> FloorPlanGrid:
    """Convert Gemini room analysis into a FloorPlanGrid for Gurobi.

    Each room is a rectangle defined by (x_offset, z_offset, width, length).
    We rasterize these into grid cells at the given resolution.
    """
    if not analysis.rooms:
        raise ValueError("No rooms in analysis")

    # Compute bounding box of all rooms
    max_x = max(r.x_offset_m + r.width_m for r in analysis.rooms)
    max_z = max(r.z_offset_m + r.length_m for r in analysis.rooms)

    grid_w = max(1, int(max_x / cell_size) + 1)
    grid_h = max(1, int(max_z / cell_size) + 1)

    grid = FloorPlanGrid(width=grid_w, height=grid_h, cell_size=cell_size)

    for room in analysis.rooms:
        cells: set[tuple[int, int]] = set()
        j_start = int(room.x_offset_m / cell_size)
        j_end = int((room.x_offset_m + room.width_m) / cell_size)
        i_start = int(room.z_offset_m / cell_size)
        i_end = int((room.z_offset_m + room.length_m) / cell_size)

        for i in range(i_start, min(i_end, grid_h)):
            for j in range(j_start, min(j_end, grid_w)):
                cells.add((i, j))

        if cells:
            grid.room_cells[room.name] = cells

    logger.info(
        "Built grid %dx%d (%.1fm x %.1fm), %d rooms: %s",
        grid_w, grid_h, max_x, max_z, grid.num_rooms,
        {n: f"{grid.room_area_sqm(n):.1f}m²" for n in grid.room_names},
    )
    return grid


async def process_floorplan(session_id: str) -> FloorplanAnalysis:
    """Full floorplan pipeline:
    1. Gemini analyses original floorplan (text labels help identification)
    2. Single Nano Banana call: floorplan → isometric render (removes text + renders)
    3. Upload render to fal.ai storage
    4. Trellis v2 generates room 3D GLB
    5. Save room_data + room_glb_url to session
    """
    session = db.get_session(session_id)
    if not session:
        raise ValueError(f"Session {session_id} not found")

    floorplan_url = session.get("floorplan_url")
    if not floorplan_url:
        raise ValueError(f"Session {session_id} has no floorplan_url")

    job = db.create_job(session_id, phase="floorplan_analysis")
    job_id = job["id"]
    trace: list[dict] = []

    try:
        trace.append(_trace_event("started", "Floorplan analysis started"))
        db.update_job(job_id, {"status": "running", "trace": trace})
        db.update_session(session_id, {"status": "analyzing_floorplan"})

        image_data_url = await _to_data_url(floorplan_url)

        # --- Steps 1+2 in parallel: Gemini analysis + isometric render ---
        preferences = session.get("preferences") or {}
        prompt = floorplan_analysis_prompt()
        render_prompt = build_render_prompt(preferences)

        logger.info(
            "Session %s: running Gemini analysis + isometric render in parallel", session_id
        )
        trace.append(_trace_event("gemini_analysis", "Analysing floorplan with Gemini"))
        trace.append(_trace_event("isometric_render", "Generating isometric render"))
        db.update_job(job_id, {"trace": trace})

        t0 = time.time()

        async def _gemini_analysis():
            return await call_gemini_with_image(prompt, image_data_url)

        async def _isometric_render():
            return await generate_colored_render(image_data_url, preferences)

        raw_response, colored_render = await asyncio.gather(
            _gemini_analysis(),
            _isometric_render(),
        )
        parallel_ms = (time.time() - t0) * 1000

        # Parse Gemini result
        json_str = _extract_json(raw_response)
        data = json.loads(json_str)
        analysis = FloorplanAnalysis.model_validate(data)
        room_data = analysis.model_dump()
        rooms_found = len(analysis.rooms)

        trace.append(
            _trace_event(
                "parsed",
                f"Gemini found {rooms_found} room(s)",
                duration_ms=round(parallel_ms),
                input_prompt=prompt,
                input_image=floorplan_url,
                output_text=raw_response[:4000],
                model=GEMINI_MODEL,
                data={
                    "rooms": [
                        {
                            "name": r.name,
                            "width_m": r.width_m,
                            "length_m": r.length_m,
                            "area_sqm": r.area_sqm,
                        }
                        for r in analysis.rooms
                    ],
                },
            )
        )
        trace.append(
            _trace_event(
                "isometric_render",
                "Isometric render complete",
                duration_ms=round(parallel_ms),
                input_prompt=render_prompt,
                input_image=floorplan_url,
                output_image=colored_render,
                model="google/gemini-3-pro-image-preview",
            )
        )
        db.update_job(job_id, {"trace": trace})

        # --- Steps 3+4+4b in parallel: fal upload → Trellis GLB + Misha grid analyzer ---
        logger.info("Session %s: uploading render + running grid analyzer in parallel", session_id)
        trace.append(_trace_event("fal_upload", "Uploading render to fal.ai"))
        trace.append(_trace_event("grid_analysis", "Building placement grid"))
        db.update_job(job_id, {"trace": trace})

        t0 = time.time()

        async def _upload_and_trellis():
            fal_url = await upload_data_url_to_fal(colored_render)
            glb_url = await generate_room_model(fal_url)
            return fal_url, glb_url

        async def _grid_analysis():
            """Run Misha's FloorPlanAnalyzer on the floorplan image."""
            import tempfile

            from ..furniture_placement.floorplan_analyzer import FloorPlanAnalyzer

            room_names = [r.name for r in analysis.rooms]
            analyzer = FloorPlanAnalyzer(
                target_width_m=max(r.x_offset_m + r.width_m for r in analysis.rooms),
                cell_size_m=0.5,
            )
            # Download floorplan to temp file (analyzer needs a file path)
            async with httpx.AsyncClient() as client:
                resp = await client.get(floorplan_url)
                resp.raise_for_status()
            with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
                f.write(resp.content)
                tmp_path = f.name
            try:
                grid = await analyzer.segment_floorplan(tmp_path, room_names)
                return grid.to_dict()
            finally:
                import os
                os.unlink(tmp_path)

        # Run Trellis + grid analyzer in parallel
        trellis_task = asyncio.create_task(_upload_and_trellis())
        grid_task = asyncio.create_task(_grid_analysis())

        # Wait for Trellis (required)
        fal_image_url, room_glb_url = await trellis_task
        duration_ms = (time.time() - t0) * 1000

        trace.append(
            _trace_event(
                "fal_upload", "Uploaded to fal.ai",
                duration_ms=round(duration_ms),
                image_url=fal_image_url,
                output_image=fal_image_url,
            )
        )
        trace.append(
            _trace_event(
                "room_3d", "Room GLB generated",
                duration_ms=round(duration_ms),
                image_url=fal_image_url,
                glb_url=room_glb_url,
                model="fal-ai/trellis-2",
            )
        )

        # Collect grid result (non-blocking, fall back to rectangle grid if it fails)
        grid_data = None
        try:
            grid_data = await asyncio.wait_for(grid_task, timeout=60)
            logger.info("Session %s: Misha grid analyzer succeeded", session_id)
            trace.append(_trace_event("grid_analysis", "Grid built (CV pipeline)", duration_ms=round((time.time() - t0) * 1000)))
        except Exception:
            logger.warning("Session %s: Misha grid analyzer failed, falling back to rectangle grid", session_id, exc_info=True)
            grid_task.cancel()
            try:
                grid = room_data_to_grid(analysis)
                grid_data = grid.to_dict()
                trace.append(_trace_event("grid_analysis", "Grid built (rectangle fallback)", duration_ms=round((time.time() - t0) * 1000)))
            except Exception:
                logger.warning("Session %s: rectangle grid also failed", session_id)

        # --- Step 5: Save everything ---
        updates = {
            "room_data": room_data,
            "room_glb_url": room_glb_url,
            "status": "floorplan_ready",
        }
        if grid_data:
            updates["grid_data"] = grid_data
        db.update_session(session_id, updates)

        trace.append(_trace_event("completed", "Floorplan pipeline complete"))
        db.update_job(job_id, {"status": "completed", "trace": trace})

        logger.info(
            "Session %s: floorplan pipeline complete — %d rooms found, GLB at %s",
            session_id,
            rooms_found,
            room_glb_url,
        )
        return analysis

    except Exception as exc:
        logger.exception("Session %s: floorplan pipeline failed", session_id)
        trace.append(_trace_event("error", f"Pipeline failed: {exc}", error=str(exc)))
        db.update_job(job_id, {"status": "failed", "trace": trace})
        db.update_session(session_id, {"status": "floorplan_failed"})
        raise
