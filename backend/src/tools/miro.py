"""Miro board creation for design briefs."""

import logging

import httpx

from ..config import MIRO_API_TOKEN, PEXELS_API_KEY

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

    with httpx.Client(timeout=60.0) as client:
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

        _add_vision_images(client, headers, board_id, brief)
        _add_sticky_notes(client, headers, board_id, brief)

    return board_url


# ---------------------------------------------------------------------------
# Vision board images
# ---------------------------------------------------------------------------

def _vision_queries(brief: dict) -> list[str]:
    """
    Build image search queries from brief fields.
    Combines style prefix with rooms, must-haves and vibe words to get
    specific, on-brand results — e.g. "modern minimalist living room".
    """
    styles = brief.get("style", [])
    rooms = brief.get("rooms_priority", [])
    must_haves = brief.get("must_haves", [])
    vibe_words = brief.get("vibe_words", [])

    style = " ".join(styles[:2]) if styles else ""
    queries: list[str] = []

    for room in rooms[:2]:
        queries.append(f"{style} {room}".strip())
    for item in must_haves[:2]:
        queries.append(f"{style} {item}".strip())
    for vibe in vibe_words[:1]:
        queries.append(f"{vibe} interior design")
    if style:
        queries.append(f"{style} interior design")

    return queries[:6]


def _resolve_image_url(query: str) -> str | None:
    """Search Pexels for a query and return a direct landscape image URL."""
    if not PEXELS_API_KEY:
        logger.warning("PEXELS_API_KEY not set — skipping vision images")
        return None
    try:
        resp = httpx.get(
            "https://api.pexels.com/v1/search",
            headers={"Authorization": PEXELS_API_KEY},
            params={"query": query, "per_page": 1, "orientation": "landscape"},
            timeout=8.0,
        )
        resp.raise_for_status()
        photos = resp.json().get("photos", [])
        if photos:
            return photos[0]["src"]["large"]
        logger.warning("No Pexels results for: %s", query)
    except Exception as exc:
        logger.warning("Pexels fetch failed for '%s': %s", query, exc)
    return None


def _add_vision_images(client: httpx.Client, headers: dict, board_id: str, brief: dict) -> None:
    """Fetch images for each vision query and place them above the sticky notes."""
    queries = _vision_queries(brief)
    if not queries:
        return

    images_endpoint = f"{_MIRO_API_BASE}/boards/{board_id}/images"
    placed = 0

    for i, query in enumerate(queries):
        img_url = _resolve_image_url(query)
        if not img_url:
            continue

        col = placed % 3
        row = placed // 3
        x = (col - 1) * 310    # columns at x = -310, 0, +310
        y = -700 + row * 260   # rows at y = -700, -440

        try:
            client.post(
                images_endpoint,
                headers=headers,
                json={
                    "data": {"imageUrl": img_url},
                    "geometry": {"width": 280},
                    "position": {"x": x, "y": y, "origin": "center"},
                },
            )
            placed += 1
            logger.info("Added vision image %d/%d: %s", placed, len(queries), query)
        except Exception:
            logger.warning("Miro image upload failed for: %s", query)

    logger.info("Vision images added: %d", placed)


# ---------------------------------------------------------------------------
# Sticky notes
# ---------------------------------------------------------------------------

def _add_sticky_notes(client: httpx.Client, headers: dict, board_id: str, brief: dict) -> None:
    base_url = f"{_MIRO_API_BASE}/boards/{board_id}/sticky_notes"

    budget_val = brief.get("budget")
    currency = brief.get("currency", "EUR")
    budget_str = f"{currency} {int(budget_val):,}" if budget_val else "TBD"

    # Shifted down by 300px to sit below the vision image rows
    sections = [
        ("BUDGET",      budget_str,                         "light_yellow", -280,  100),
        ("ROOMS",       _join(brief.get("rooms_priority")), "light_green",     0,  100),
        ("STYLE",       _join(brief.get("style")),          "light_blue",    280,  100),
        ("MUST HAVES",  _join(brief.get("must_haves")),     "light_pink",   -280,  380),
        ("AVOID",       _join(brief.get("avoid")),          "red",              0,  380),
        ("VIBE",        _join(brief.get("vibe_words")),     "cyan",           280,  380),
        ("CONSTRAINTS", _join(brief.get("constraints")),    "gray",          -140,  660),
        ("NOTES",       brief.get("notes") or "—",          "white",          140,  660),
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
