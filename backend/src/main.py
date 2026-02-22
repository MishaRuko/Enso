"""HomeDesigner — AI Interior Design Agent API."""

import logging

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

import asyncio
import re as _re

import httpx
from fastapi import FastAPI, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from pydantic import BaseModel

import re as _re

from . import db
<<<<<<< Updated upstream
from .models.schemas import PlacementResult, UserPreferences
from .routes import session, tools, voice, voice_intake
=======
from .models.schemas import UserPreferences
>>>>>>> Stashed changes
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
    return {
        "budget": prefs.get("budget_max"),
        "currency": prefs.get("currency", "EUR"),
        "style": (
            [style] if isinstance(style, str) and style
            else style if isinstance(style, list) else []
        ),
        "avoid": prefs.get("dealbreakers", []),
        "rooms_priority": [prefs["room_type"]] if prefs.get("room_type") else [],
        "must_haves": prefs.get("must_haves", []),
        "existing_items": prefs.get("existing_furniture", []),
        "constraints": [],
        "vibe_words": prefs.get("colors", []),
        "reference_images": [],
        "notes": "",
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


@app.get("/api/proxy-glb")
async def proxy_glb(url: str):
    """Proxy external GLB files to avoid CORS issues (e.g. IKEA CDN)."""
    if not url.startswith("https://"):
        raise HTTPException(400, "Only HTTPS URLs allowed")
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


def _extract_board_id(url: str) -> str:
    match = _re.search(r'/board/([^/?]+)', url)
    return match.group(1) if match else ""


def _preferences_to_brief(prefs: dict) -> dict:
    style = prefs.get("style", "")
    return {
        "budget": prefs.get("budget_max"),
        "currency": prefs.get("currency", "EUR"),
        "style": ([style] if isinstance(style, str) and style else style if isinstance(style, list) else []),
        "avoid": prefs.get("dealbreakers", []),
        "rooms_priority": [prefs["room_type"]] if prefs.get("room_type") else [],
        "must_haves": prefs.get("must_haves", []),
        "existing_items": prefs.get("existing_furniture", []),
        "constraints": [],
        "vibe_words": prefs.get("colors", []),
        "reference_images": [],
        "notes": "",
    }


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
    existing_url = session.get("miro_board_url")
    if existing_url:
        return {"miro_board_url": existing_url, "board_id": _extract_board_id(existing_url), "status": "ready"}
    preferences = session.get("preferences") or {}
    brief = _preferences_to_brief(preferences)

    async def _run_miro():
        try:
            result = await asyncio.to_thread(generate_vision_board_with_miro_ai, brief)
            db.update_session(session_id, {"miro_board_url": result.url})
            logging.getLogger("miro_task").info("Board ready for %s: %s", session_id, result.url)
        except Exception:
            logging.getLogger("miro_task").exception("Miro board creation failed for %s", session_id)

    asyncio.create_task(_run_miro())
    return {"status": "pending", "miro_board_url": None, "board_id": None}


@app.post("/api/sessions/{session_id}/preferences")
async def save_preferences(session_id: str, prefs: UserPreferences):
    session = db.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    updated = db.update_session(session_id, {"preferences": prefs.model_dump(), "status": "consulting"})
    return updated


@app.post("/api/sessions/{session_id}/miro")
async def create_miro_board(session_id: str):
    session = db.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    existing_url = session.get("miro_board_url")
    if existing_url:
        return {"miro_board_url": existing_url, "board_id": _extract_board_id(existing_url)}
    preferences = session.get("preferences") or {}
    brief = _preferences_to_brief(preferences)
    result = await asyncio.to_thread(generate_vision_board_with_miro_ai, brief)
    db.update_session(session_id, {"miro_board_url": result.url})
    return {"miro_board_url": result.url, "board_id": _extract_board_id(result.url)}


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


@app.post("/api/sessions/{session_id}/floorplan")
async def upload_floorplan(session_id: str, file: UploadFile):
    session = db.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    contents = await file.read()
    ext = (file.filename or "plan.png").rsplit(".", 1)[-1]
    storage_path = f"{session_id}/floorplan.{ext}"
    content_type = file.content_type or "image/png"

    public_url = db.upload_to_storage("floorplans", storage_path, contents, content_type)
    updated = db.update_session(session_id, {"floorplan_url": public_url, "status": "analyzing_floorplan"})

    # Fire-and-forget floorplan analysis with error logging
    async def _run_floorplan():
        try:
            await process_floorplan(session_id)
        except Exception:
            logging.getLogger("floorplan_task").exception("Floorplan task failed for %s", session_id)

    asyncio.create_task(_run_floorplan())

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

    task = asyncio.create_task(_run())
    task.add_done_callback(lambda t: t.result() if not t.cancelled() and not t.exception() else None)
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
    from .workflow.placement import place_furniture
    session = db.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    db.update_session(session_id, {"status": "placing"})
    job = db.create_job(session_id, phase="placement")

    async def _run():
        logger = logging.getLogger("placement_task")
        try:
            logger.info("Starting placement for %s", session_id)
            await place_furniture(session_id, job["id"])
            db.update_session(session_id, {"status": "complete"})
            logger.info("Placement complete for %s", session_id)
        except Exception:
            logger.exception("Placement failed for %s", session_id)
            db.update_session(session_id, {"status": "placing_failed"})

    task = asyncio.create_task(_run())
    task.add_done_callback(lambda t: t.result() if not t.cancelled() and not t.exception() else None)
    return {"job_id": job["id"]}


@app.post("/api/sessions/{session_id}/pipeline")
async def start_pipeline(session_id: str):
    session = db.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    asyncio.create_task(run_full_pipeline(session_id))
    return {"status": "started"}


@app.post("/api/sessions/{session_id}/source-models")
async def source_placed_models(session_id: str):
    """Re-source GLB models for placed furniture items: IKEA extraction then TRELLIS."""
    from .tools.fal_client import generate_3d_model, upload_to_fal
    from .tools.ikea_glb import extract_ikea_glb

    logger = logging.getLogger("source_models")

    session = db.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    placements = (session.get("placements") or {}).get("placements", [])
    if not placements:
        return {"sourced": 0, "message": "No placements found"}

    placed_ids = {p["item_id"] for p in placements}

    # Get furniture items from DB
    all_items = db.list_furniture(session_id)
    placed_items = [i for i in all_items if i["id"] in placed_ids and not i.get("glb_url")]

    sourced = 0
    for item in placed_items:
        product_url = item.get("product_url", "")
        glb_url = None

        # Try IKEA GLB extraction first
        if product_url and "ikea" in product_url.lower():
            glb_url = await extract_ikea_glb(product_url)
            if glb_url:
                logger.info("IKEA GLB for %s: %s", item.get("name", "?"), glb_url)

        # Fall back to TRELLIS if no IKEA GLB and has image
        if not glb_url and item.get("image_url"):
            logger.info("Trying TRELLIS for %s...", item.get("name", "?"))
            try:
                import httpx
                async with httpx.AsyncClient(timeout=httpx.Timeout(15.0)) as http:
                    img_resp = await http.get(item["image_url"])
                    img_resp.raise_for_status()
                    fal_url = await upload_to_fal(img_resp.content, img_resp.headers.get("content-type", "image/jpeg"))
                glb_url = await generate_3d_model(fal_url, model="trellis-2")
                logger.info("TRELLIS GLB for %s: %s", item.get("name", "?"), glb_url)
            except Exception:
                logger.exception("TRELLIS failed for %s", item.get("name", "?"))

        if glb_url:
            try:
                db.update_furniture(item["id"], {"glb_url": glb_url})
            except Exception:
                pass
            sourced += 1

    return {"sourced": sourced, "total_placed": len(placed_ids)}


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
