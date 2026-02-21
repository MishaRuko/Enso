"""Floorplan processing pipeline — text removal + colored render + Trellis v2 room GLB + Gemini analysis."""

import base64
import json
import logging
import re

import httpx

from .. import db
from ..models.schemas import FloorplanAnalysis
from ..prompts.floorplan_analysis import floorplan_analysis_prompt
from ..tools.fal_client import generate_room_model, upload_data_url_to_fal
from ..tools.llm import call_gemini_with_image
from ..tools.nanobananana import generate_colored_render, remove_text_from_image

logger = logging.getLogger(__name__)


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
    1. Download floorplan
    2. Clean text with Nano Banana
    3. Analyse with Gemini (room dimensions for placement)
    4. Generate colored architectural render with Nano Banana
    5. Upload render to fal.ai storage
    6. Generate room 3D GLB with Trellis v2
    7. Save room_data + room_glb_url to session

    Args:
        session_id: The design session ID.

    Returns:
        Parsed FloorplanAnalysis with room data.

    Raises:
        ValueError: If the session or floorplan URL is missing.
    """
    session = db.get_session(session_id)
    if not session:
        raise ValueError(f"Session {session_id} not found")

    floorplan_url = session.get("floorplan_url")
    if not floorplan_url:
        raise ValueError(f"Session {session_id} has no floorplan_url")

    job = db.create_job(session_id, phase="floorplan_analysis")
    job_id = job["id"]

    try:
        db.update_job(job_id, {"status": "running", "trace": ["started"]})
        db.update_session(session_id, {"status": "analyzing_floorplan"})

        # --- Step 0: Convert localhost URL to base64 data URL ---
        image_for_llm = await _to_data_url(floorplan_url)

        # --- Step 1: Clean text/labels with Nano Banana ---
        logger.info("Session %s: cleaning floorplan text via Nano Banana", session_id)
        db.update_job(job_id, {"trace": ["started", "text_removal"]})
        cleaned_image = await remove_text_from_image(image_for_llm)

        # --- Step 2: Analyse with Gemini vision (for room dimensions needed by placement) ---
        logger.info("Session %s: analysing floorplan with Gemini", session_id)
        db.update_job(job_id, {"trace": ["started", "text_removal", "gemini_analysis"]})
        prompt = floorplan_analysis_prompt()
        raw_response = await call_gemini_with_image(prompt, cleaned_image)

        # --- Step 3: Parse JSON response ---
        logger.info("Session %s: parsing Gemini response", session_id)
        json_str = _extract_json(raw_response)
        data = json.loads(json_str)
        analysis = FloorplanAnalysis.model_validate(data)

        room_data = analysis.model_dump()
        trace = ["started", "text_removal", "gemini_analysis", "parsed"]

        # --- Step 4: Generate colored architectural render ---
        logger.info("Session %s: generating colored 3D render via Nano Banana", session_id)
        db.update_job(job_id, {"trace": [*trace, "colored_render"]})
        colored_render = await generate_colored_render(cleaned_image)

        # --- Step 5: Upload render to fal.ai storage ---
        logger.info("Session %s: uploading render to fal.ai storage", session_id)
        db.update_job(job_id, {"trace": [*trace, "colored_render", "fal_upload"]})
        fal_image_url = await upload_data_url_to_fal(colored_render)

        # --- Step 6: Generate room 3D GLB with Trellis v2 ---
        logger.info("Session %s: generating room 3D model with Trellis v2", session_id)
        db.update_job(job_id, {"trace": [*trace, "colored_render", "fal_upload", "trellis_room"]})
        room_glb_url = await generate_room_model(fal_image_url)

        # --- Step 7: Save everything ---
        db.update_session(session_id, {
            "room_data": room_data,
            "room_glb_url": room_glb_url,
            "status": "floorplan_ready",
        })
        db.update_job(job_id, {
            "status": "completed",
            "trace": [*trace, "colored_render", "fal_upload", "trellis_room", "completed"],
        })

        logger.info(
            "Session %s: floorplan pipeline complete — %d rooms found, GLB at %s",
            session_id,
            len(analysis.rooms),
            room_glb_url,
        )
        return analysis

    except Exception:
        logger.exception("Session %s: floorplan pipeline failed", session_id)
        db.update_job(job_id, {"status": "failed"})
        db.update_session(session_id, {"status": "floorplan_failed"})
        raise
