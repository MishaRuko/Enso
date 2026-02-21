"""HomeDesigner — AI Interior Design Agent API."""

import logging

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

import asyncio

from fastapi import FastAPI, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from . import db
from .models.schemas import UserPreferences
from .workflow.floorplan import process_floorplan
from .workflow.pipeline import run_full_pipeline

app = FastAPI(title="HomeDesigner", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


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


@app.post("/api/sessions/{session_id}/preferences")
async def save_preferences(session_id: str, prefs: UserPreferences):
    session = db.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    updated = db.update_session(session_id, {"preferences": prefs.model_dump(), "status": "consulting"})
    return updated


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

    # Fire-and-forget floorplan analysis
    asyncio.create_task(process_floorplan(session_id))

    return {"floorplan_url": updated["floorplan_url"]}


@app.post("/api/sessions/{session_id}/search")
async def start_search(session_id: str):
    session = db.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    db.update_session(session_id, {"status": "searching"})
    job = db.create_job(session_id, phase="furniture_search")
    return {"job_id": job["id"]}


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


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8100)
