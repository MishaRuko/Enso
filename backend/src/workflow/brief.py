"""Pipeline workflow helpers — interface for consuming design briefs."""

import logging

from ..db import get_voice_intake_session
from ..models.schemas import DesignBrief

logger = logging.getLogger(__name__)


async def get_brief_for_session(session_id: str) -> DesignBrief | None:
    """
    Get the design brief for a session.
    Used by downstream stages (furniture search, floorplan, placement, etc.)
    to consume the intake-collected preferences.

    Args:
        session_id: The voice consultation session ID

    Returns:
        DesignBrief if session exists, None otherwise
    """
    session = get_voice_intake_session(session_id)
    if not session:
        logger.warning(f"Session {session_id} not found")
        return None

    brief_dict = session.get("brief", {})
    try:
        brief = DesignBrief(**brief_dict)
        return brief
    except Exception as e:
        logger.error(f"Failed to parse brief for session {session_id}: {e}")
        return None


def get_session_status(session_id: str) -> str | None:
    """Get the current session status (collecting, confirmed, finalized)."""
    session = get_voice_intake_session(session_id)
    if not session:
        return None
    return session.get("status")


def get_miro_board_url(session_id: str) -> str | None:
    """Get the Miro board URL for a session (if finalized)."""
    session = get_voice_intake_session(session_id)
    if not session:
        return None
    miro = session.get("miro", {})
    return miro.get("board_url")
