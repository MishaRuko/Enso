"""Miro REST API v2 integration — mood board generation."""

import logging
from typing import Any

import httpx

from ..config import MIRO_API_TOKEN

logger = logging.getLogger(__name__)

BASE_URL = "https://api.miro.com/v2"
TIMEOUT = 30.0

# Board layout constants
COLUMN_WIDTH = 400
ROW_HEIGHT = 500
PADDING = 60
TITLE_Y = -200


def _headers() -> dict[str, str]:
    return {
        "Authorization": f"Bearer {MIRO_API_TOKEN}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }


async def _miro_post(path: str, body: dict) -> dict:
    """POST to Miro API and return JSON response."""
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        resp = await client.post(f"{BASE_URL}{path}", json=body, headers=_headers())
        resp.raise_for_status()
        return resp.json()


async def create_board(name: str, description: str = "") -> dict:
    """Create a new Miro board and return the full response (includes id, viewLink)."""
    body: dict[str, Any] = {"name": name, "description": description}
    return await _miro_post("/boards", body)


async def add_sticky_note(
    board_id: str,
    content: str,
    *,
    x: float = 0,
    y: float = 0,
    color: str = "light_yellow",
    width: int = 300,
) -> dict:
    """Add a sticky note to a board."""
    body = {
        "data": {"content": content, "shape": "square"},
        "style": {"fillColor": color},
        "position": {"x": x, "y": y, "origin": "center"},
        "geometry": {"width": width},
    }
    return await _miro_post(f"/boards/{board_id}/sticky_notes", body)


async def add_text(
    board_id: str,
    content: str,
    *,
    x: float = 0,
    y: float = 0,
    font_size: str = "36",
    width: int = 600,
) -> dict:
    """Add a text item to a board."""
    body = {
        "data": {"content": content},
        "style": {"fontSize": font_size},
        "position": {"x": x, "y": y, "origin": "center"},
        "geometry": {"width": width},
    }
    return await _miro_post(f"/boards/{board_id}/texts", body)


async def add_image(
    board_id: str,
    image_url: str,
    *,
    x: float = 0,
    y: float = 0,
    width: int = 300,
    title: str = "",
) -> dict:
    """Add an image to a board from a URL."""
    body: dict[str, Any] = {
        "data": {"url": image_url},
        "position": {"x": x, "y": y, "origin": "center"},
        "geometry": {"width": width},
    }
    if title:
        body["data"]["title"] = title
    return await _miro_post(f"/boards/{board_id}/images", body)


async def create_mood_board(
    session_id: str,
    preferences: dict,
    furniture_items: list[dict],
) -> str:
    """Create a Miro mood board for a design session.

    Returns the viewLink URL to the created board.
    """
    if not MIRO_API_TOKEN:
        raise ValueError("MIRO_API_TOKEN is not configured")

    style = preferences.get("style", "modern")
    room_type = preferences.get("room_type", "room")
    budget_min = preferences.get("budget_min", 0)
    budget_max = preferences.get("budget_max", 0)
    colors = preferences.get("colors", [])
    currency = preferences.get("currency", "EUR")

    board_name = f"HomeDesigner - {style.title()} {room_type.replace('_', ' ').title()}"
    board_desc = f"Mood board for session {session_id}"

    # 1. Create the board
    board = await create_board(board_name, board_desc)
    board_id = board["id"]
    view_link = board.get("viewLink", "")

    logger.info("Created Miro board %s: %s", board_id, view_link)

    # 2. Add title text
    await add_text(
        board_id,
        f"<b>{board_name}</b>",
        x=0,
        y=TITLE_Y,
        font_size="48",
        width=800,
    )

    # 3. Add preference sticky notes in a row
    pref_notes = []
    if style:
        pref_notes.append(f"Style: {style}")
    if room_type:
        pref_notes.append(f"Room: {room_type.replace('_', ' ')}")
    if budget_max > 0:
        pref_notes.append(f"Budget: {currency} {budget_min:.0f} - {budget_max:.0f}")
    if colors:
        pref_notes.append(f"Colors: {', '.join(colors)}")

    lifestyle = preferences.get("lifestyle", [])
    if lifestyle:
        pref_notes.append(f"Lifestyle: {', '.join(lifestyle)}")

    must_haves = preferences.get("must_haves", [])
    if must_haves:
        pref_notes.append(f"Must-haves: {', '.join(must_haves)}")

    pref_colors = ["light_yellow", "light_green", "light_blue", "light_pink", "yellow", "green"]

    for i, note_text in enumerate(pref_notes):
        col = i % 4
        row = i // 4
        await add_sticky_note(
            board_id,
            note_text,
            x=(col - 1.5) * (COLUMN_WIDTH + PADDING),
            y=TITLE_Y + 250 + row * 350,
            color=pref_colors[i % len(pref_colors)],
            width=280,
        )

    # 4. Add furniture items as images with price labels
    furniture_start_y = TITLE_Y + 250 + 400
    items_per_row = 3
    center_offset = (items_per_row - 1) / 2

    for i, item in enumerate(furniture_items[:12]):  # max 12 items
        col = i % items_per_row
        row = i // items_per_row
        x = (col - center_offset) * (COLUMN_WIDTH + PADDING)
        y = furniture_start_y + row * ROW_HEIGHT

        image_url = item.get("image_url", "")
        name = item.get("name", "Item")
        price = item.get("price", 0)
        item_currency = item.get("currency", currency)

        if image_url:
            try:
                await add_image(
                    board_id,
                    image_url,
                    x=x,
                    y=y,
                    width=320,
                    title=name,
                )
            except Exception:
                logger.warning("Failed to add image for %s, adding as sticky note", name)
                await add_sticky_note(
                    board_id,
                    f"<b>{name}</b>",
                    x=x,
                    y=y,
                    color="light_blue",
                )
        else:
            await add_sticky_note(
                board_id,
                f"<b>{name}</b>",
                x=x,
                y=y,
                color="light_blue",
            )

        # Price label below the image
        await add_sticky_note(
            board_id,
            f"<b>{name}</b><br>{item_currency} {price:.0f}",
            x=x,
            y=y + 220,
            color="light_green",
            width=280,
        )

    logger.info("Mood board populated with %d items", min(len(furniture_items), 12))

    return view_link
