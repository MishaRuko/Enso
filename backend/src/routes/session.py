"""Session management endpoints."""

import logging

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ..db import new_voice_intake_session, get_voice_intake_session

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/session", tags=["session"])


class NewSessionResponse(BaseModel):
    session_id: str


@router.post("/new")
async def new_session() -> dict:
    """Create a new voice-intake session."""
    session = new_voice_intake_session()
    return {"session_id": session["session_id"]}


@router.get("/{session_id}")
async def get_session(session_id: str) -> dict:
    """Get full session state for debugging."""
    session = get_voice_intake_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return session
