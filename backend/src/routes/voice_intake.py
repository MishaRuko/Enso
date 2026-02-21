"""Voice intake fallback endpoints for simple (non-realtime) WebSocket testing."""

import logging

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ..agents.voice_intake import run_voice_intake_turn
from ..db import get_voice_intake_session, save_voice_intake_session
from ..tools.miro import create_board_from_brief

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/voice_intake", tags=["voice_intake"])


class TurnRequest(BaseModel):
    session_id: str
    user_text: str


class FinalizeRequest(BaseModel):
    session_id: str


@router.post("/turn")
async def turn(req: TurnRequest) -> dict:
    """
    Simple non-realtime fallback for one voice intake turn.
    Same output as /tool/next_question.
    """
    session = get_voice_intake_session(req.session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    # Run the intake turn
    try:
        result = await run_voice_intake_turn(
            transcript=req.user_text,
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
    session["history"].append({"role": "user", "content": req.user_text})
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
async def finalize(req: FinalizeRequest) -> dict:
    """Finalize session and create Miro board."""
    session = get_voice_intake_session(req.session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    # Create Miro board from brief
    try:
        board_url = create_board_from_brief(session["brief"])
        session["miro"]["board_url"] = board_url
        session["status"] = "finalized"
        save_voice_intake_session(session)
        logger.info(f"Session {req.session_id} finalized with board: {board_url}")
    except Exception as e:
        logger.exception("Failed to finalize session")
        raise HTTPException(status_code=500, detail="Failed to create Miro board") from e

    return {"miro_board_url": board_url}
