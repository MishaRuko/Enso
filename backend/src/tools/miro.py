"""Miro board creation for design briefs."""

import logging
import os

from ..config import MIRO_API_TOKEN

logger = logging.getLogger(__name__)

# Placeholder Miro URLs for demo (replace with real Miro API calls when token available)
_DEMO_BOARD_ID = "miro-board-demo-12345"
_DEMO_BOARD_URL = f"https://miro.com/app/board/{_DEMO_BOARD_ID}/"


def create_board_from_brief(brief: dict) -> str:
    """
    Create a Miro board from a design brief.

    For now, returns a plausible URL if MIRO_API_TOKEN is missing.
    If token exists, would create a real board with frames/cards summarizing the brief.

    Args:
        brief: The canonical brief JSON

    Returns:
        Miro board URL
    """
    if not MIRO_API_TOKEN:
        logger.warning("MIRO_API_TOKEN not set, returning demo board URL")
        return _DEMO_BOARD_URL

    # TODO: Implement real Miro API calls when token available
    # Steps:
    # 1. Create a board via REST API
    # 2. Add frames/cards with budget, rooms, style, must_haves, etc.
    # 3. Return the board URL

    logger.info("Would create real Miro board for brief")
    return _DEMO_BOARD_URL
