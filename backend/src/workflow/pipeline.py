"""End-to-end pipeline orchestrator — chains search → placement."""

import logging
import time

from .. import db
from .floorplan import process_floorplan
from .furniture_search import search_furniture
from .placement import place_furniture

logger = logging.getLogger(__name__)

PIPELINE_STAGES = [
    "searching",
    "placing",
    "complete",
]


def _trace_event(step: str, message: str, **kwargs) -> dict:
    evt = {"step": step, "message": message, "timestamp": time.time()}
    evt.update(kwargs)
    return evt


async def run_full_pipeline(session_id: str) -> None:
    """Run the design pipeline: search → place → complete.

    Updates session.status through each stage and creates design_jobs for tracing.
    On failure, sets status to `{stage}_failed` and stops.
    """
    job = db.create_job(session_id, phase="full_pipeline")
    job_id = job["id"]
    trace: list[dict] = []

    try:
        # 0. Ensure floorplan analysis is complete
        session = db.get_session(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")
        if not session.get("room_data"):
            if not session.get("floorplan_url"):
                logger.error("Session %s: no floorplan uploaded", session_id)
                trace.append(_trace_event("error", "No floorplan uploaded"))
                db.update_session(session_id, {"status": "floorplan_failed"})
                db.update_job(job_id, {"status": "failed", "trace": trace})
                return
            logger.info("Session %s: room_data missing, re-running floorplan analysis", session_id)
            trace.append(_trace_event("started", "Re-running floorplan analysis"))
            db.update_job(job_id, {"status": "running", "trace": trace})
            await process_floorplan(session_id)

        # 1. Furniture search
        trace.append(_trace_event("searching", "Searching for furniture"))
        db.update_session(session_id, {"status": "searching"})
        db.update_job(job_id, {"status": "running", "trace": trace})

        t0 = time.time()
        search_job = db.create_job(session_id, phase="furniture_search")
        items = await search_furniture(session_id, search_job["id"])
        duration_ms = (time.time() - t0) * 1000

        if not items:
            logger.warning("Session %s: no furniture found, continuing anyway", session_id)

        trace.append(_trace_event(
            "search_done", f"Found {len(items)} items", duration_ms=round(duration_ms),
        ))
        db.update_job(job_id, {"trace": trace})

        # 2. Placement
        trace.append(_trace_event("placing", "Computing furniture placement"))
        db.update_session(session_id, {"status": "placing"})
        db.update_job(job_id, {"trace": trace})

        t0 = time.time()
        placement_job = db.create_job(session_id, phase="placement")
        try:
            await place_furniture(session_id, placement_job["id"])
        except Exception:
            logger.exception("Session %s: placement failed (non-fatal)", session_id)
        duration_ms = (time.time() - t0) * 1000

        trace.append(_trace_event(
            "placing", "Placement complete", duration_ms=round(duration_ms),
        ))

        # 3. Done — only mark complete if placement actually saved results
        session_check = db.get_session(session_id)
        has_placements = bool(
            session_check
            and session_check.get("placements")
            and session_check["placements"].get("placements")
        )
        if has_placements:
            trace.append(_trace_event("complete", "Pipeline finished"))
            db.update_session(session_id, {"status": "complete"})
        else:
            trace.append(_trace_event("complete", "Pipeline finished (no placements)"))
            logger.warning("Session %s: pipeline done but no placements saved", session_id)
            db.update_session(session_id, {"status": "placement_ready"})
        db.update_job(job_id, {"status": "completed", "trace": trace})

        logger.info("Session %s: full pipeline completed", session_id)

    except Exception as exc:
        logger.exception("Session %s: pipeline failed", session_id)

        session = db.get_session(session_id)
        current = session.get("status", "unknown") if session else "unknown"
        failed_status = f"{current}_failed" if not current.endswith("_failed") else current

        trace.append(_trace_event("error", f"Pipeline failed: {exc}", error=str(exc)))
        db.update_session(session_id, {"status": failed_status})
        db.update_job(job_id, {"status": "failed", "trace": trace})
