"""Voice realtime endpoints."""

import logging

from fastapi import APIRouter

from ..tools.elevenlabs_realtime import create_realtime_session_token

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/voice", tags=["voice"])


@router.post("/session_token")
async def session_token(session_id: str) -> dict:
    """Get ElevenLabs realtime session config for frontend."""
    return create_realtime_session_token(session_id)
