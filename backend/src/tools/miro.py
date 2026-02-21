"""Miro board creation for design briefs."""

import logging

import httpx

from ..config import MIRO_API_TOKEN

logger = logging.getLogger(__name__)

_DEMO_BOARD_URL = "https://miro.com/app/board/demo/"
_MIRO_API_BASE = "https://api.miro.com/v2"


def create_board_from_brief(brief: dict) -> str:
    """Create a real Miro board from a design brief and return its URL."""
    if not MIRO_API_TOKEN:
        logger.warning("MIRO_API_TOKEN not set, returning demo board URL")
        return _DEMO_BOARD_URL

    headers = {
        "Authorization": f"Bearer {MIRO_API_TOKEN}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }

    with httpx.Client(timeout=30.0) as client:
        resp = client.post(
            f"{_MIRO_API_BASE}/boards",
            headers=headers,
            json={
                "name": "Interior Design Brief — HomeDesigner",
                "description": "AI-generated design brief from voice consultation",
            },
        )
        resp.raise_for_status()
        board = resp.json()
        board_id = board["id"]
        board_url = board["viewLink"]
        logger.info("Created Miro board: %s", board_url)

        _add_sticky_notes(client, headers, board_id, brief)

    return board_url


def _add_sticky_notes(client: httpx.Client, headers: dict, board_id: str, brief: dict) -> None:
    base_url = f"{_MIRO_API_BASE}/boards/{board_id}/sticky_notes"

    budget_val = brief.get("budget")
    currency = brief.get("currency", "EUR")
    budget_str = f"{currency} {int(budget_val):,}" if budget_val else "TBD"

    # Grid layout: 3 columns x 3 rows, 280px spacing
    sections = [
        ("BUDGET",      budget_str,                         "light_yellow", -280, -200),
        ("ROOMS",       _join(brief.get("rooms_priority")), "light_green",     0, -200),
        ("STYLE",       _join(brief.get("style")),          "light_blue",    280, -200),
        ("MUST HAVES",  _join(brief.get("must_haves")),     "light_pink",   -280,   80),
        ("AVOID",       _join(brief.get("avoid")),          "red",              0,   80),
        ("VIBE",        _join(brief.get("vibe_words")),     "cyan",           280,   80),
        ("CONSTRAINTS", _join(brief.get("constraints")),    "gray",          -140,  360),
        ("NOTES",       brief.get("notes") or "—",          "white",          140,  360),
    ]

    for label, value, color, x, y in sections:
        try:
            client.post(
                base_url,
                headers=headers,
                json={
                    "data": {"content": f"{label}\n{value}", "shape": "square"},
                    "style": {"fillColor": color},
                    "geometry": {"width": 220},
                    "position": {"x": x, "y": y, "origin": "center"},
                },
            )
        except Exception:
            logger.warning("Failed to add sticky note: %s", label)


def _join(items: list | None) -> str:
    if not items:
        return "—"
    return ", ".join(str(i) for i in items)
