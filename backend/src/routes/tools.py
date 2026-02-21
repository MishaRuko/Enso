"""Tool endpoints for voice-intake knowledge base operations."""

import logging

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ..agents.voice_intake import run_voice_intake_turn
from ..db import get_voice_intake_session, save_voice_intake_session
from ..tools.miro import create_board_from_brief

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/tool", tags=["tools"])


class KBGetRequest(BaseModel):
    session_id: str


class KBUpsertRequest(BaseModel):
    session_id: str
    brief_patch: dict


class NextQuestionRequest(BaseModel):
    session_id: str
    transcript: str


class FinalizeRequest(BaseModel):
    session_id: str


@router.post("/kb_get")
async def kb_get(req: KBGetRequest):
    """Get current brief status for a session."""
    session = get_voice_intake_session(req.session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    return {
        "status": session["status"],
        "brief": session["brief"],
        "missing_fields": session["missing_fields"],
        "miro_board_url": session["miro"]["board_url"],
    }


@router.post("/kb_upsert")
async def kb_upsert(req: KBUpsertRequest):
    """Manually update brief fields (for testing or direct input)."""
    session = get_voice_intake_session(req.session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    # Merge patch into brief
    for k, v in (req.brief_patch or {}).items():
        if k in session["brief"]:
            session["brief"][k] = v

    save_voice_intake_session(session)
    return {"brief": session["brief"]}


@router.post("/next_question")
async def next_question(req: NextQuestionRequest):
    """Process one turn of voice intake conversation."""
    session = get_voice_intake_session(req.session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    # Run the intake turn
    try:
        result = await run_voice_intake_turn(
            transcript=req.transcript,
            brief_current=session["brief"],
            history=session["history"],
        )
    except Exception as e:
        logger.exception("Voice intake turn failed")
        raise HTTPException(status_code=500, detail="Failed to process turn") from e

    # Merge patch into brief
    for k, v in result.brief_patch.items():
        session["brief"][k] = v

    # Append to history
    session["history"].append({"role": "user", "content": req.transcript})
    session["history"].append({"role": "assistant", "content": result.assistant_text})

    # Update missing fields
    session["missing_fields"] = result.missing_fields

    # Update done status
    if result.done:
        session["status"] = "confirmed"

    save_voice_intake_session(session)

    return {
        "assistant_text": result.assistant_text,
        "brief": session["brief"],
        "missing_fields": result.missing_fields,
        "done": result.done,
    }


@router.post("/finalize")
async def finalize(req: FinalizeRequest):
    """Finalize session and create Miro board."""
    session = get_voice_intake_session(req.session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    # Create Miro board from brief — degrade gracefully if it fails
    try:
        board_url = create_board_from_brief(session["brief"])
    except Exception:
        logger.exception("Miro board creation failed, using demo fallback")
        board_url = "https://miro.com/app/board/demo/"

    session["miro"]["board_url"] = board_url
    session["status"] = "finalized"
    save_voice_intake_session(session)
    logger.info(f"Session {req.session_id} finalized with board: {board_url}")

    return {"miro_board_url": board_url}
