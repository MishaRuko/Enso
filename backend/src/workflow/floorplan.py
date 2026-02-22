"""Floorplan processing pipeline — Gemini analysis + isometric render + Trellis v2 room GLB."""

import base64
import json
import logging
import re
import time

import httpx

from .. import db
from ..config import GEMINI_MODEL
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

        # --- Step 1: Gemini analyses the ORIGINAL floorplan ---
        logger.info("Session %s: analysing floorplan with Gemini", session_id)
        t0 = time.time()
        trace.append(_trace_event("gemini_analysis", "Analysing floorplan with Gemini"))
        db.update_job(job_id, {"trace": trace})

        prompt = floorplan_analysis_prompt()
        raw_response = await call_gemini_with_image(prompt, image_data_url)

        json_str = _extract_json(raw_response)
        data = json.loads(json_str)
        analysis = FloorplanAnalysis.model_validate(data)
        room_data = analysis.model_dump()
        rooms_found = len(analysis.rooms)
        duration_ms = (time.time() - t0) * 1000

        trace.append(_trace_event(
            "parsed", f"Gemini found {rooms_found} room(s)",
            duration_ms=round(duration_ms),
            input_prompt=prompt,
            input_image=floorplan_url,
            output_text=raw_response[:4000],
            model=GEMINI_MODEL,
        ))
        db.update_job(job_id, {"trace": trace})

        # --- Step 2: Single Nano Banana call → isometric render ---
        preferences = session.get("preferences") or {}
        logger.info("Session %s: generating isometric render via Nano Banana", session_id)
        t0 = time.time()
        trace.append(_trace_event("isometric_render", "Generating isometric render"))
        db.update_job(job_id, {"trace": trace})

        render_prompt = build_render_prompt(preferences)
        colored_render = await generate_colored_render(image_data_url, preferences)
        duration_ms = (time.time() - t0) * 1000

        trace.append(_trace_event(
            "isometric_render", "Isometric render complete",
            duration_ms=round(duration_ms),
            input_prompt=render_prompt,
            input_image=floorplan_url,
            model="google/gemini-3-pro-image-preview",
        ))
        db.update_job(job_id, {"trace": trace})

        # --- Step 3: Upload render to fal.ai storage ---
        logger.info("Session %s: uploading render to fal.ai storage", session_id)
        t0 = time.time()
        trace.append(_trace_event("fal_upload", "Uploading render to fal.ai"))
        db.update_job(job_id, {"trace": trace})

        fal_image_url = await upload_data_url_to_fal(colored_render)
        duration_ms = (time.time() - t0) * 1000

        trace.append(_trace_event(
            "fal_upload", "Uploaded to fal.ai", duration_ms=round(duration_ms),
            image_url=fal_image_url,
            output_image=fal_image_url,
        ))
        db.update_job(job_id, {"trace": trace})

        # --- Step 4: Generate room 3D GLB with Trellis v2 ---
        logger.info("Session %s: generating room 3D model with Trellis v2", session_id)
        t0 = time.time()
        trace.append(_trace_event("room_3d", "Generating room 3D model with TRELLIS v2"))
        db.update_job(job_id, {"trace": trace})

        room_glb_url = await generate_room_model(fal_image_url)
        duration_ms = (time.time() - t0) * 1000

        trace.append(_trace_event(
            "room_3d", "Room GLB generated",
            duration_ms=round(duration_ms),
            input_image=fal_image_url,
            model="fal-ai/trellis-2",
        ))

        # --- Step 5: Save everything ---
        db.update_session(session_id, {
            "room_data": room_data,
            "room_glb_url": room_glb_url,
            "status": "floorplan_ready",
        })

        trace.append(_trace_event("completed", "Floorplan pipeline complete"))
        db.update_job(job_id, {"status": "completed", "trace": trace})

        logger.info(
            "Session %s: floorplan pipeline complete — %d rooms found, GLB at %s",
            session_id, rooms_found, room_glb_url,
        )
        return analysis

    except Exception as exc:
        logger.exception("Session %s: floorplan pipeline failed", session_id)
        trace.append(_trace_event("error", f"Pipeline failed: {exc}", error=str(exc)))
        db.update_job(job_id, {"status": "failed", "trace": trace})
        db.update_session(session_id, {"status": "floorplan_failed"})
        raise
