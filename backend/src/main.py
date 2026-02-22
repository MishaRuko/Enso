"""HomeDesigner — AI Interior Design Agent API."""

import logging

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

import asyncio
import re as _re
from urllib.parse import urlparse

import httpx
from fastapi import FastAPI, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from pydantic import BaseModel

from . import db
from .models.schemas import PlacementResult, UserPreferences
from .routes import session, tools, voice, voice_intake
from .tools.miro_mcp import generate_vision_board_with_miro_ai
from .workflow.floorplan import process_floorplan
from .workflow.pipeline import run_full_pipeline

app = FastAPI(title="HomeDesigner", version="0.1.0")

# CORS: Allow all origins for hackathon sprint.
# - Frontend dev on any port (localhost:3000, 3001, etc.)
# - ElevenLabs realtime WebSocket tool calls to backend endpoints
# - Production deployments should restrict to specific origin.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(session.router)
app.include_router(tools.router)
app.include_router(voice.router)
app.include_router(voice_intake.router)


# ---------------------------------------------------------------------------
# Helpers — Miro
# ---------------------------------------------------------------------------


def _extract_board_id(url: str) -> str:
    match = _re.search(r'/board/([^/?]+)', url)
    return match.group(1) if match else ""


def _preferences_to_brief(prefs: dict) -> dict:
    style = prefs.get("style", "")
    lifestyle = prefs.get("lifestyle", [])
    colors = prefs.get("colors", [])
    notes_parts = []
    if lifestyle:
        notes_parts.append("Lifestyle: " + ", ".join(lifestyle))
    return {
        "budget": prefs.get("budget_max"),
        "budget_min": prefs.get("budget_min"),
        "currency": prefs.get("currency", "EUR"),
        "style": (
            [style] if isinstance(style, str) and style
            else style if isinstance(style, list) else []
        ),
        "avoid": prefs.get("dealbreakers", []),
        "rooms_priority": [prefs["room_type"]] if prefs.get("room_type") else [],
        "must_haves": prefs.get("must_haves", []),
        "existing_items": prefs.get("existing_furniture", []),
        "constraints": lifestyle,
        "vibe_words": colors,
        "reference_images": [],
        "notes": "; ".join(notes_parts),
    }


# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------

class CreateSessionRequest(BaseModel):
    client_name: str | None = None
    client_email: str | None = None


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------

@app.get("/health")
async def health():
    return {"status": "ok", "service": "homedesigner"}


_GLB_ALLOWED_HOSTS = (".ikea.com", ".fal.ai", ".fal.run", ".sketchfab.com", ".poly.pizza")


@app.get("/api/proxy-glb")
async def proxy_glb(url: str):
    """Proxy external GLB files to avoid CORS issues (e.g. IKEA CDN)."""
    if not url.startswith("https://"):
        raise HTTPException(400, "Only HTTPS URLs allowed")
    hostname = urlparse(url).hostname or ""
    if hostname != "localhost" and not any(
        hostname.endswith(d) for d in _GLB_ALLOWED_HOSTS
    ):
        raise HTTPException(403, {"error": "Domain not allowed"})
    try:
        async with httpx.AsyncClient(follow_redirects=True, timeout=30) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            return Response(
                content=resp.content,
                media_type=resp.headers.get("content-type", "model/gltf-binary"),
                headers={"Cache-Control": "public, max-age=86400"},
            )
    except httpx.HTTPError as e:
        raise HTTPException(502, f"Failed to fetch GLB: {e}")


@app.get("/api/status")
async def status():
    return {"status": "ready"}


# ---------------------------------------------------------------------------
# Sessions
# ---------------------------------------------------------------------------

@app.post("/api/sessions")
async def create_session(body: CreateSessionRequest | None = None):
    body = body or CreateSessionRequest()
    session = db.create_session(client_name=body.client_name, client_email=body.client_email)
    return {"session_id": session["id"]}


@app.get("/api/sessions")
async def list_sessions():
    return db.list_sessions()


@app.get("/api/sessions/{session_id}")
async def get_session(session_id: str):
    session = db.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    # Merge GLB URLs from furniture_items table into furniture_list
    # and append any placed items missing from furniture_list
    furniture_list = session.get("furniture_list") or []
    db_items = db.list_furniture(session_id)

    if db_items:
        db_map = {item["id"]: item for item in db_items}
        fl_ids = {item["id"] for item in furniture_list}

        # Update existing items with GLB URLs from DB
        for item in furniture_list:
            db_item = db_map.get(item["id"])
            if db_item and db_item.get("glb_url") and not item.get("glb_url"):
                item["glb_url"] = db_item["glb_url"]

        # Append placed items that are in DB but missing from furniture_list
        placements = (session.get("placements") or {}).get("placements", [])
        placed_ids = {p["item_id"] for p in placements}
        for pid in placed_ids - fl_ids:
            if pid in db_map:
                furniture_list.append(db_map[pid])

        session["furniture_list"] = furniture_list

    return session


class PatchSessionRequest(BaseModel):
    preferences: dict | None = None
    status: str | None = None


@app.patch("/api/sessions/{session_id}")
async def patch_session(session_id: str, body: PatchSessionRequest):
    session = db.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    updates: dict = {}
    if body.preferences is not None:
        updates["preferences"] = body.preferences
    if body.status is not None:
        updates["status"] = body.status
    if updates:
        session = db.update_session(session_id, updates)
    return session


@app.post("/api/sessions/{session_id}/miro")
async def create_miro_board(session_id: str):
    session = db.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    preferences = session.get("preferences") or {}
    brief = _preferences_to_brief(preferences)
    logging.getLogger("miro_task").info("Generating Miro board for %s with brief: %s", session_id, brief)

    async def _run_miro():
        try:
            result = await asyncio.to_thread(generate_vision_board_with_miro_ai, brief)
            db.update_session(session_id, {"miro_board_url": result.url})
            logging.getLogger("miro_task").info("Board ready for %s: %s", session_id, result.url)
        except Exception:
            logging.getLogger("miro_task").exception("Miro board creation failed for %s", session_id)

    asyncio.create_task(_run_miro())
    return {"status": "pending", "miro_board_url": None, "board_id": None}


_pref_log = logging.getLogger("preferences")

_EXTRACT_SYSTEM = """You are an interior design preference extractor.
Given a consultation transcript between a user and an AI designer, extract the user's
design preferences and return ONLY a valid JSON object with these exact keys:

{
  "style": "design style as a single string, e.g. Scandinavian minimalist",
  "room_type": "e.g. living room, bedroom, home office",
  "budget_min": 0,
  "budget_max": 0,
  "currency": "EUR",
  "colors": ["list of colors/palettes mentioned"],
  "lifestyle": ["lifestyle tags, e.g. works from home, has pets, entertains often"],
  "must_haves": ["essential items or features"],
  "dealbreakers": ["things to avoid"],
  "existing_furniture": ["items the user already owns"]
}

Rules:
- Use empty string for style/room_type if not mentioned.
- Use 0 for budget_min/budget_max if not mentioned; infer from context if a range is described.
- All list fields default to [] if not mentioned.
- Extract inferred information — e.g. if the user says "cozy Scandinavian vibe" that's a style.
- Return ONLY the JSON object, no explanation."""


class TranscriptRequest(BaseModel):
    transcript: list[str]


@app.post("/api/sessions/{session_id}/extract-preferences")
async def extract_preferences_from_transcript(session_id: str, body: TranscriptRequest):
    """Extract UserPreferences from the ElevenLabs conversation transcript using Claude,
    save them to the session, and kick off Miro board generation."""
    from .agents.voice_intake import _extract_json  # noqa: PLC0415
    from .tools.llm import call_claude  # noqa: PLC0415

    session = db.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    transcript_text = "\n".join(body.transcript)
    _pref_log.info("Extracting preferences for %s from %d transcript lines", session_id, len(body.transcript))

    try:
        raw = await call_claude(
            messages=[{"role": "user", "content": f"Transcript:\n{transcript_text}"}],
            system=_EXTRACT_SYSTEM,
            temperature=0.1,
        )
        extracted = _extract_json(raw)
    except Exception:
        _pref_log.exception("Preference extraction failed for %s, using empty prefs", session_id)
        extracted = {}

    # Parse through Pydantic so we get type coercion and defaults
    try:
        prefs = UserPreferences(**extracted)
    except Exception:
        _pref_log.warning("Pydantic parse failed for extracted prefs %s, using defaults", extracted)
        prefs = UserPreferences()

    dumped = prefs.model_dump()
    _pref_log.info("Extracted preferences for %s: %s", session_id, dumped)
    db.update_session(session_id, {"preferences": dumped, "status": "consulting"})

    # Kick off Miro board generation with the freshly extracted preferences
    brief = _preferences_to_brief(dumped)
    logging.getLogger("miro_task").info("Generating Miro board for %s with brief: %s", session_id, brief)

    async def _run_miro():
        try:
            result = await asyncio.to_thread(generate_vision_board_with_miro_ai, brief)
            db.update_session(session_id, {"miro_board_url": result.url})
            logging.getLogger("miro_task").info("Board ready for %s: %s", session_id, result.url)
        except Exception:
            logging.getLogger("miro_task").exception("Miro board creation failed for %s", session_id)

    asyncio.create_task(_run_miro())
    return {"preferences": dumped, "status": "pending"}


@app.post("/api/sessions/{session_id}/preferences")
async def save_preferences(session_id: str, prefs: UserPreferences):
    session = db.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    dumped = prefs.model_dump()
    _pref_log.info("Saving preferences for %s: %s", session_id, dumped)
    updated = db.update_session(session_id, {"preferences": dumped, "status": "consulting"})
    return updated


class MiroItemRequest(BaseModel):
    board_id: str
    label: str
    value: str
    color: str = "light_yellow"


@app.post("/api/sessions/{session_id}/miro/item")
async def add_miro_item(session_id: str, body: MiroItemRequest):
    from .tools.miro import add_sticky_note

    session = db.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    positions = {
        "style": (-1100, -790, "light_blue"),
        "budget_min": (1020, -790, "light_yellow"),
        "budget_max": (1020, -790, "light_yellow"),
        "colors": (-1100, -410, "cyan"),
        "room_type": (1020, -410, "light_green"),
        "must_haves": (1020, -120, "light_pink"),
        "dealbreakers": (-1100, -120, "red"),
        "lifestyle": (1020, 168, "gray"),
        "existing_furniture": (-1100, 168, "white"),
        "currency": (1020, -600, "light_yellow"),
    }
    x, y, default_color = positions.get(body.label, (0, 500, body.color))
    result = await add_sticky_note(
        body.board_id,
        f"{body.label.upper().replace('_', ' ')}\n{body.value}",
        x=x, y=y, color=default_color, width=220,
    )
    return {"ok": True, "item_id": result.get("id", "")}


_ALLOWED_IMAGE_TYPES = {"image/png", "image/jpeg", "image/webp"}
_MAX_UPLOAD_BYTES = 10 * 1024 * 1024


@app.post("/api/sessions/{session_id}/floorplan")
async def upload_floorplan(session_id: str, file: UploadFile):
    session = db.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    if file.content_type not in _ALLOWED_IMAGE_TYPES:
        raise HTTPException(status_code=400, detail="Only PNG, JPEG, and WebP images are accepted")

    contents = await file.read()

    if len(contents) > _MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="File too large (max 10 MB)")

    ext = (file.filename or "plan.png").rsplit(".", 1)[-1]
    storage_path = f"{session_id}/floorplan.{ext}"
    content_type = file.content_type or "image/png"

    public_url = db.upload_to_storage("floorplans", storage_path, contents, content_type)
    updated = db.update_session(session_id, {"floorplan_url": public_url, "status": "analyzing_floorplan"})

    async def _run_floorplan():
        try:
            await process_floorplan(session_id)
        except Exception:
            logging.getLogger("floorplan_task").exception("Floorplan task failed for %s", session_id)
            db.update_session(session_id, {"status": "floorplan_failed"})

    task = asyncio.create_task(_run_floorplan())
    _background_tasks.add(task)
    task.add_done_callback(_background_tasks.discard)

    return {"floorplan_url": updated["floorplan_url"]}


@app.post("/api/sessions/{session_id}/search")
async def start_search(session_id: str):
    from .workflow.furniture_search import search_furniture

    session = db.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    db.update_session(session_id, {"status": "searching"})
    job = db.create_job(session_id, phase="furniture_search")

    async def _run():
        _logger = logging.getLogger("search_task")
        try:
            _logger.info("Starting furniture search for %s", session_id)
            await search_furniture(session_id, job["id"])
            _logger.info("Furniture search complete for %s", session_id)
        except Exception:
            _logger.exception("Furniture search failed for %s", session_id)
            db.update_session(session_id, {"status": "search_failed"})

    task = asyncio.create_task(_run())
    _background_tasks.add(task)
    task.add_done_callback(_background_tasks.discard)
    return {"job_id": job["id"]}


@app.patch("/api/sessions/{session_id}/placements")
async def update_placements(session_id: str, body: PlacementResult):
    session = db.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    db.update_session(session_id, {"placements": body.model_dump()})
    return {"status": "ok"}


@app.post("/api/sessions/{session_id}/place")
async def start_placement(session_id: str):
    session = db.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    db.update_session(session_id, {"status": "placing"})
    job = db.create_job(session_id, phase="placement")

    has_grid = session.get("grid_data") and isinstance(session.get("grid_data"), dict)

    async def _run():
        _logger = logging.getLogger("placement_task")
        try:
            if has_grid:
                from .workflow.placement_gurobi import place_furniture_gurobi
                _logger.info("Starting Gurobi placement for %s", session_id)
                await place_furniture_gurobi(session_id, job["id"])
            else:
                from .workflow.placement import place_furniture
                _logger.info("No grid_data — falling back to Gemini placement for %s", session_id)
                await place_furniture(session_id, job["id"])
            db.update_session(session_id, {"status": "complete"})
            _logger.info("Placement complete for %s", session_id)
        except Exception:
            _logger.exception("Placement failed for %s", session_id)
            db.update_session(session_id, {"status": "placement_failed"})

    task = asyncio.create_task(_run())
    _background_tasks.add(task)
    task.add_done_callback(_background_tasks.discard)
    return {"job_id": job["id"]}


@app.get("/api/sessions/{session_id}/grid")
async def get_grid(session_id: str):
    """Get the FloorPlanGrid for a session."""
    session = db.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    grid_data = session.get("grid_data")
    if not grid_data:
        raise HTTPException(status_code=404, detail="No grid data — upload a floorplan first")
    return grid_data


@app.post("/api/sessions/{session_id}/pipeline")
async def start_pipeline(session_id: str):
    session = db.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    async def _run_pipeline():
        try:
            await run_full_pipeline(session_id)
        except Exception:
            logging.getLogger("pipeline_task").exception("Pipeline task failed for %s", session_id)
            sess = db.get_session(session_id)
            current = sess.get("status", "unknown") if sess else "unknown"
            if not current.endswith("_failed"):
                db.update_session(session_id, {"status": "pipeline_failed"})

    task = asyncio.create_task(_run_pipeline())
    _background_tasks.add(task)
    task.add_done_callback(_background_tasks.discard)
    return {"status": "started"}


@app.post("/api/sessions/{session_id}/source-models")
async def source_placed_models(session_id: str):
    """Re-source GLB models for placed furniture items using parallel sourcing."""
    from .workflow.model_sourcing import source_all_models

    session = db.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    summary = await source_all_models(session_id)
    return {
        "sourced": summary["success"],
        "total_placed": summary["total"],
        "failed": summary["failed"],
        "skipped": summary["skipped"],
    }


# ---------------------------------------------------------------------------
# Jobs
# ---------------------------------------------------------------------------

@app.get("/api/jobs/{job_id}")
async def get_job(job_id: str):
    job = db.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


# ---------------------------------------------------------------------------
# Tracing
# ---------------------------------------------------------------------------

@app.get("/api/sessions/{session_id}/jobs")
async def list_session_jobs(session_id: str):
    session = db.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return db.list_jobs(session_id)


# In-memory cancel signals for running pipelines
_background_tasks: set[asyncio.Task] = set()
_cancel_events: dict[str, asyncio.Event] = {}


def register_cancel_event(session_id: str) -> asyncio.Event:
    event = asyncio.Event()
    _cancel_events[session_id] = event
    return event


def cleanup_cancel_event(session_id: str) -> None:
    _cancel_events.pop(session_id, None)


def is_cancelled(session_id: str) -> bool:
    event = _cancel_events.get(session_id)
    return event.is_set() if event else False


@app.post("/api/sessions/{session_id}/checkout")
async def checkout(session_id: str):
    from .workflow.checkout import create_checkout

    session = db.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    try:
        url = await create_checkout(session_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logging.getLogger("checkout").exception("Checkout failed for %s", session_id)
        raise HTTPException(status_code=502, detail="Stripe checkout failed")
    return {"payment_link": url}


@app.post("/api/sessions/{session_id}/cancel")
async def cancel_session(session_id: str):
    session = db.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    event = _cancel_events.get(session_id)
    if event:
        event.set()
        return {"status": "ok", "message": f"Cancellation requested for {session_id}"}

    processing = [
        "analyzing_floorplan", "searching", "sourcing", "placing", "placing_furniture",
    ]
    if session.get("status") in processing:
        db.update_session(session_id, {"status": f"{session['status']}_failed"})
        return {"status": "ok", "message": f"Session {session_id} marked as failed"}

    return {"status": "not_found", "message": "No running pipeline to cancel"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8100)
