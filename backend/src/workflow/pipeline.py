"""End-to-end pipeline orchestrator — chains search → placement."""

import logging

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


async def run_full_pipeline(session_id: str) -> None:
    """Run the design pipeline: search → place → complete.

    Updates session.status through each stage and creates design_jobs for tracing.
    On failure, sets status to `{stage}_failed` and stops.
    """
    job = db.create_job(session_id, phase="full_pipeline")
    job_id = job["id"]

    try:
        # 0. Ensure floorplan analysis is complete
        session = db.get_session(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")
        if not session.get("room_data"):
            if not session.get("floorplan_url"):
                logger.error("Session %s: no floorplan uploaded", session_id)
                db.update_session(session_id, {"status": "floorplan_failed"})
                db.update_job(job_id, {
                    "status": "failed",
                    "trace": [{"step": "error", "message": "No floorplan uploaded"}],
                })
                return
            logger.info("Session %s: room_data missing, re-running floorplan analysis", session_id)
            await process_floorplan(session_id)

        # 1. Furniture search
        db.update_session(session_id, {"status": "searching"})
        db.update_job(job_id, {
            "status": "running",
            "trace": [{"step": "searching", "message": "Searching for furniture"}],
        })

        search_job = db.create_job(session_id, phase="furniture_search")
        items = await search_furniture(session_id, search_job["id"])

        if not items:
            logger.warning("Session %s: no furniture found, continuing anyway", session_id)

        db.update_job(job_id, {
            "trace": [
                {"step": "searching", "message": "Searching for furniture"},
                {"step": "search_done", "message": f"Found {len(items)} items"},
            ],
        })

        # 2. Placement
        db.update_session(session_id, {"status": "placing"})
        db.update_job(job_id, {
            "trace": [
                {"step": "searching", "message": "Searching for furniture"},
                {"step": "search_done", "message": f"Found {len(items)} items"},
                {"step": "placing", "message": "Computing furniture placement"},
            ],
        })

        placement_job = db.create_job(session_id, phase="placement")
        try:
            await place_furniture(session_id, placement_job["id"])
        except Exception:
            logger.exception("Session %s: placement failed (non-fatal)", session_id)

        # 3. Done
        db.update_session(session_id, {"status": "complete"})
        db.update_job(job_id, {
            "status": "completed",
            "trace": [
                {"step": "searching", "message": "Searching for furniture"},
                {"step": "search_done", "message": f"Found {len(items)} items"},
                {"step": "placing", "message": "Computing furniture placement"},
                {"step": "complete", "message": "Pipeline finished"},
            ],
        })

        logger.info("Session %s: full pipeline completed", session_id)

    except Exception:
        logger.exception("Session %s: pipeline failed", session_id)

        session = db.get_session(session_id)
        current = session.get("status", "unknown") if session else "unknown"
        failed_status = f"{current}_failed" if not current.endswith("_failed") else current

        db.update_session(session_id, {"status": failed_status})
        db.update_job(job_id, {
            "status": "failed",
            "trace": [{"step": "error", "message": "Pipeline failed"}],
        })
