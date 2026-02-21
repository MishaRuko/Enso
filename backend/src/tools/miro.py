"""Miro board creation for design briefs."""

import json
import logging
import re

import httpx

from ..config import MIRO_API_TOKEN, OPENROUTER_API_KEY, PEXELS_API_KEY

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

_PHRASES_MODEL = "anthropic/claude-haiku-4-5"


def _llm_search_phrases(brief: dict) -> list[str]:
    """Ask Claude to generate 6 Pexels search phrases tailored to the brief."""
    if not OPENROUTER_API_KEY:
        logger.warning("OPENROUTER_API_KEY not set — falling back to keyword queries")
        return []

    brief_summary = {k: v for k, v in brief.items() if v}
    prompt = (
        "Generate 6 specific Pexels image search phrases for an interior design mood board.\n"
        f"Brief: {json.dumps(brief_summary)}\n\n"
        "Return ONLY a JSON array of 6 short search phrases (2-4 words each) that work well "
        "on Pexels. Mix: room shots with the style, key furniture pieces, colour palette, "
        "and atmosphere/vibe. Example: [\"modern living room\", \"minimalist sofa\", "
        "\"warm neutral tones\", \"scandinavian bedroom\", \"cosy reading nook\", "
        "\"natural light interior\"]"
    )

    try:
        resp = httpx.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": _PHRASES_MODEL,
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 200,
            },
            timeout=15.0,
        )
        resp.raise_for_status()
        content = resp.json()["choices"][0]["message"]["content"]
        match = re.search(r"\[.*?\]", content, re.DOTALL)
        if match:
            phrases = json.loads(match.group())
            logger.info("LLM generated %d search phrases", len(phrases))
            return [str(p) for p in phrases[:6]]
        logger.warning("LLM response had no JSON array: %s", content[:200])
    except Exception as exc:
        logger.warning("LLM phrase generation failed: %s", exc)

    return []


def _vision_queries(brief: dict) -> list[str]:
    """
    Fallback: build image search queries from brief fields without LLM.
    Combines style prefix with rooms, must-haves and vibe words.
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


def _resolve_image_urls(query: str, count: int = 2) -> list[str]:
    """Search Pexels for a query and return up to `count` landscape image URLs."""
    if not PEXELS_API_KEY:
        logger.warning("PEXELS_API_KEY not set — skipping vision images")
        return []
    try:
        resp = httpx.get(
            "https://api.pexels.com/v1/search",
            headers={"Authorization": PEXELS_API_KEY},
            params={"query": query, "per_page": count, "orientation": "landscape"},
            timeout=8.0,
        )
        resp.raise_for_status()
        photos = resp.json().get("photos", [])
        urls = [p["src"]["large"] for p in photos[:count]]
        if not urls:
            logger.warning("No Pexels results for: %s", query)
        return urls
    except Exception as exc:
        logger.warning("Pexels fetch failed for '%s': %s", query, exc)
    return []


def _add_vision_images(client: httpx.Client, headers: dict, board_id: str, brief: dict) -> None:
    """
    Generate search phrases via Claude, fetch 2 Pexels photos each, and place
    them in a 4-column grid above the sticky notes.
    Falls back to keyword-based queries if the LLM call fails.
    """
    queries = _llm_search_phrases(brief) or _vision_queries(brief)
    if not queries:
        return

    images_endpoint = f"{_MIRO_API_BASE}/boards/{board_id}/images"
    placed = 0

    # 4-column grid — up to 12 images (6 queries × 2) fit in 3 rows
    # Rows at y = -700, -440, -180  →  280 px clear before sticky notes at y = 100
    _COLS = 4
    _COL_XS = [-450, -150, 150, 450]
    _ROW_Y_START = -700
    _ROW_Y_STEP = 260

    for query in queries:
        urls = _resolve_image_urls(query, count=2)
        for img_url in urls:
            col = placed % _COLS
            row = placed // _COLS
            x = _COL_XS[col]
            y = _ROW_Y_START + row * _ROW_Y_STEP

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
                logger.info("Added vision image %d for query: %s", placed, query)
            except Exception:
                logger.warning("Miro image upload failed for: %s", query)

    logger.info("Vision images added: %d total", placed)


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
