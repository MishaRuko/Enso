"""Miro board creation for design briefs."""

import json
import logging
import re
from typing import Any

import httpx

from ..config import MIRO_API_TOKEN, MIRO_TEMPLATE_BOARD_ID, OPENROUTER_API_KEY, PEXELS_API_KEY

logger = logging.getLogger(__name__)

_DEMO_BOARD_URL = "https://miro.com/app/board/demo/"
_MIRO_API_BASE = "https://api.miro.com/v2"
_LAYOUT_MODEL = "anthropic/claude-haiku-4-5"

# ---------------------------------------------------------------------------
# Fallback slot template — used when no MIRO_TEMPLATE_BOARD_ID is set.
# (x, y, width_px) — board-centre coordinates.
# ---------------------------------------------------------------------------
_IMG_SLOTS = [
    (-360, -760, 560),   # 0  HERO
    ( 130, -790, 400),   # 1  medium
    ( 490, -775, 300),   # 2  small
    (-420, -410, 300),   # 3  small
    ( -30, -411, 460),   # 4  medium-large
    ( 390, -400, 360),   # 5  medium
    (-355, -120, 370),   # 6  medium
    ( -10, -118, 300),   # 7  small
    ( 345, -115, 390),   # 8  medium
    (-375,  168, 300),   # 9  small
    (   0,  168, 430),   # 10 medium
    ( 375,  168, 300),   # 11 small
]

_STICKY_COLS: dict[str, tuple[str, int, int]] = {
    "BUDGET":      ("light_yellow",  1020, -790),
    "ROOMS":       ("light_green",   1020, -410),
    "MUST HAVES":  ("light_pink",    1020, -120),
    "CONSTRAINTS": ("gray",          1020,  168),
    "STYLE":       ("light_blue",   -1110, -790),
    "VIBE":        ("cyan",         -1110, -410),
    "AVOID":       ("red",          -1110, -120),
    "NOTES":       ("white",        -1110,  168),
}

# Board layout constants (used by async helpers)
COLUMN_WIDTH = 400
ROW_HEIGHT = 500
PADDING = 60
TITLE_Y = -200
TIMEOUT = 30.0


# ---------------------------------------------------------------------------
# Async helper API (used by pipeline mood board generation)
# ---------------------------------------------------------------------------

def _headers() -> dict[str, str]:
    return {
        "Authorization": f"Bearer {MIRO_API_TOKEN}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }


async def _miro_post(path: str, body: dict) -> dict:
    """POST to Miro API and return JSON response."""
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        resp = await client.post(f"{_MIRO_API_BASE}{path}", json=body, headers=_headers())
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


# ---------------------------------------------------------------------------
# Synchronous brief-based board creation (from design consultation)
# ---------------------------------------------------------------------------

def create_board_from_brief(brief: dict) -> str:
    """Create a Miro board from a design brief and return its URL."""
    if not MIRO_API_TOKEN:
        logger.warning("MIRO_API_TOKEN not set, returning demo board URL")
        return _DEMO_BOARD_URL

    miro_headers = {
        "Authorization": f"Bearer {MIRO_API_TOKEN}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }

    with httpx.Client(timeout=60.0) as client:
        if MIRO_TEMPLATE_BOARD_ID:
            board_id, board_url = _copy_template_board(client, miro_headers)
            if board_id:
                logger.info("Using template board copy: %s", board_url)
                _populate_template_board(client, miro_headers, board_id, brief)
                return board_url
            logger.warning("Template board copy failed — falling back to generated layout")

        # Fallback: create a blank board and generate layout programmatically
        resp = client.post(
            f"{_MIRO_API_BASE}/boards",
            headers=miro_headers,
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

        _add_vision_images(client, miro_headers, board_id, brief)
        _add_sticky_notes(client, miro_headers, board_id, brief)

    return board_url


# ---------------------------------------------------------------------------
# Template path — copy board, detect diamonds, populate
# ---------------------------------------------------------------------------

def _copy_template_board(
    client: httpx.Client,
    headers: dict,
) -> tuple[str, str] | tuple[None, None]:
    """Copy the template board and return (new_board_id, view_url)."""
    resp = client.put(
        f"{_MIRO_API_BASE}/boards/{MIRO_TEMPLATE_BOARD_ID}/copy",
        headers=headers,
        json={},
    )
    if not resp.is_success:
        logger.warning("Board copy failed %s: %s", resp.status_code, resp.text[:200])
        return None, None
    board = resp.json()
    return board["id"], board["viewLink"]


def _get_all_items(
    client: httpx.Client,
    headers: dict,
    board_id: str,
    item_type: str,
) -> list[dict]:
    """Fetch every item of a given type via cursor-based pagination."""
    items: list[dict] = []
    cursor: str | None = None
    while True:
        params: dict = {"type": item_type, "limit": 50}
        if cursor:
            params["cursor"] = cursor
        resp = client.get(
            f"{_MIRO_API_BASE}/boards/{board_id}/items",
            headers=headers,
            params=params,
        )
        resp.raise_for_status()
        data = resp.json()
        items.extend(data.get("data", []))
        cursor = data.get("cursor")
        if not cursor:
            break
    return items


def _find_diamond_placeholders(
    client: httpx.Client,
    headers: dict,
    board_id: str,
) -> list[dict]:
    """
    Find all rhombus shapes on the board — these are the image placeholders.
    Returns them sorted top-left → bottom-right (row-major, 100 px row tolerance).
    """
    shapes = _get_all_items(client, headers, board_id, "shape")
    diamonds = [
        s for s in shapes
        if s.get("style", {}).get("shapeType") == "rhombus"
    ]
    logger.info("Found %d diamond placeholders", len(diamonds))

    def _sort_key(d: dict) -> tuple[int, float]:
        x = d["position"]["x"]
        y = d["position"]["y"]
        return (round(y / 100) * 100, x)   # group rows within 100 px, then left→right

    return sorted(diamonds, key=_sort_key)


def _populate_template_board(
    client: httpx.Client,
    headers: dict,
    board_id: str,
    brief: dict,
) -> None:
    """
    Populate a copied template board:
      1. Detect diamond placeholders → get their centre positions.
      2. Fetch Pexels images (de-duplicated, brief-aware).
      3. Place each image centred on its diamond using a two-step upload+PATCH
         so both width AND height can be set (Miro's POST only accepts one dim).
      4. Update sticky note text content from the brief.
    """
    diamonds = _find_diamond_placeholders(client, headers, board_id)

    if not diamonds:
        logger.warning("No diamond placeholders found — using fallback slot layout")
        _add_vision_images(client, headers, board_id, brief)
        _add_sticky_notes(client, headers, board_id, brief)
        return

    plan   = _llm_layout_plan(brief) or _fallback_plan(brief)
    images = _fetch_unique_images(plan.get("groups", []), n=len(diamonds))
    logger.info("Placing %d images on %d diamond slots", len(images), len(diamonds))

    auth_token = headers["Authorization"]
    placed = 0

    for i, (img_url, orig_w, orig_h) in enumerate(images):
        if i >= len(diamonds):
            break
        diamond   = diamonds[i]
        cx        = diamond["position"]["x"]
        cy        = diamond["position"]["y"]
        target_w  = round(diamond.get("geometry", {}).get("width",  350))
        target_h  = round(target_w * orig_h / orig_w)

        logger.info(
            "Slot %d: diamond @ (%.0f, %.0f) %dpx -> %s",
            i, cx, cy, target_w, img_url.split("/")[-1][:30],
        )
        ok = _place_image_at(client, board_id, auth_token, img_url, cx, cy, target_w, target_h)
        if ok:
            placed += 1

    logger.info("Template images placed: %d / %d", placed, len(images))
    _update_template_sticky_notes(client, headers, board_id, brief)


def _place_image_at(
    client: httpx.Client,
    board_id: str,
    auth_token: str,
    img_url: str,
    cx: float,
    cy: float,
    target_w: int,
    target_h: int,
) -> bool:
    """
    Two-step image placement that enforces exact width × height:

    Step 1 — binary multipart POST with position only (no geometry).
              Miro's POST accepts only one dimension; omitting both means Miro
              stores the image at its natural size without cropping.

    Step 2 — PATCH the created item with both width and height so the widget
              is sized deterministically. The image fills the widget at the
              correct aspect ratio (no cropping, no letterboxing).
    """
    try:
        dl = httpx.get(img_url, timeout=25.0, follow_redirects=True)
        dl.raise_for_status()
    except Exception as exc:
        logger.warning("Download failed for %s: %s", img_url[:60], exc)
        return False

    content_type = dl.headers.get("content-type", "image/jpeg").split(";")[0]

    # Step 1: upload binary, set position only
    data_payload = json.dumps({"position": {"x": cx, "y": cy}})
    try:
        r = client.post(
            f"{_MIRO_API_BASE}/boards/{board_id}/images",
            headers={"Authorization": auth_token, "Accept": "application/json"},
            files={"resource": ("photo.jpg", dl.content, content_type)},
            data={"data": data_payload},
        )
        if not r.is_success:
            logger.warning("Image POST %s: %s", r.status_code, r.text[:150])
            return False
        item_id = r.json()["id"]
    except Exception as exc:
        logger.warning("Image POST exception: %s", exc)
        return False

    # Step 2: PATCH to enforce position + exact widget dimensions.
    # Miro sometimes ignores position from the multipart POST, so we set it here.
    patch_headers = {
        "Authorization": auth_token,
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    try:
        p = client.patch(
            f"{_MIRO_API_BASE}/boards/{board_id}/images/{item_id}",
            headers=patch_headers,
            json={
                "geometry": {"width": target_w, "height": target_h},
                "position": {"x": cx, "y": cy, "origin": "center"},
            },
        )
        if not p.is_success:
            logger.warning("Image PATCH %s: %s", p.status_code, p.text[:150])
            # Image was still placed (step 1 succeeded); treat as partial success
    except Exception as exc:
        logger.warning("Image PATCH exception: %s", exc)

    return True


def _update_template_sticky_notes(
    client: httpx.Client,
    headers: dict,
    board_id: str,
    brief: dict,
) -> None:
    """
    Find sticky notes on the template copy and update their text content from
    the brief. Matches by the first word of the note's existing content
    (e.g. "STYLE", "BUDGET"). Position and colour are left unchanged.
    """
    budget_val = brief.get("budget")
    currency   = brief.get("currency", "EUR")
    budget_str = f"{currency} {int(budget_val):,}" if budget_val else "TBD"

    content_map = {
        "BUDGET":      budget_str,
        "ROOMS":       _join(brief.get("rooms_priority")),
        "MUST HAVES":  _join(brief.get("must_haves")),
        "CONSTRAINTS": _join(brief.get("constraints")),
        "STYLE":       _join(brief.get("style")),
        "VIBE":        _join(brief.get("vibe_words")),
        "AVOID":       _join(brief.get("avoid")),
        "NOTES":       brief.get("notes") or "—",
    }

    sticky_notes = _get_all_items(client, headers, board_id, "sticky_note")
    updated = 0
    patch_headers = {**headers, "Content-Type": "application/json"}

    for note in sticky_notes:
        raw     = note.get("data", {}).get("content", "")
        # Strip HTML tags that Miro may wrap content in
        plain   = re.sub(r"<[^>]+>", "", raw).strip()
        label   = plain.split("\n")[0].strip().upper()
        if label not in content_map:
            continue
        new_content = f"{label}\n{content_map[label]}"
        try:
            p = client.patch(
                f"{_MIRO_API_BASE}/boards/{board_id}/sticky_notes/{note['id']}",
                headers=patch_headers,
                json={"data": {"content": new_content}},
            )
            if p.is_success:
                updated += 1
            else:
                logger.warning("Sticky PATCH %s: %s", p.status_code, p.text[:100])
        except Exception as exc:
            logger.warning("Sticky PATCH exception for %s: %s", label, exc)

    logger.info("Sticky notes updated: %d / %d", updated, len(sticky_notes))


# ---------------------------------------------------------------------------
# Layout planning (Claude produces themed groups)
# ---------------------------------------------------------------------------

def _llm_layout_plan(brief: dict) -> dict | None:
    """
    Ask Claude Haiku for a semantic layout plan: 4-5 themed image groups
    with size hints (hero | medium | small) and Pexels queries.
    """
    if not OPENROUTER_API_KEY:
        return None

    brief_summary = {k: v for k, v in brief.items() if v}
    prompt = (
        "You are planning a Pinterest-style interior design vision board.\n"
        f"Design brief: {json.dumps(brief_summary)}\n\n"
        "Return a JSON layout plan with 4-5 themed image groups. "
        "Return ONLY valid JSON (no prose, no markdown):\n"
        "{\n"
        '  "groups": [\n'
        '    {"theme": "living_room", "size": "hero",   '
        '"queries": ["modern minimalist living room interior", "open plan lounge interior design"]},\n'
        '    {"theme": "bedroom",     "size": "medium", '
        '"queries": ["scandinavian bedroom interior design", "calm airy bedroom room"]},\n'
        '    {"theme": "workspace",   "size": "medium", '
        '"queries": ["home office interior design room", "minimalist desk room interior"]},\n'
        '    {"theme": "atmosphere",  "size": "small",  '
        '"queries": ["warm neutral interior room", "natural light minimalist interior design"]}\n'
        "  ]\n"
        "}\n\n"
        "Rules:\n"
        "- Exactly ONE group with size='hero'\n"
        "- 2-3 groups with size='medium'\n"
        "- 1-2 groups with size='small'\n"
        "- Every query MUST include 'interior' or 'room' (forces full-room shots)\n"
        "- Exactly 2 queries per group\n"
        "- Tailor themes closely to the brief content\n"
    )

    try:
        resp = httpx.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": _LAYOUT_MODEL,
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 600,
            },
            timeout=20.0,
        )
        resp.raise_for_status()
        content = resp.json()["choices"][0]["message"]["content"]
        match = re.search(r"\{.*\}", content, re.DOTALL)
        if match:
            plan = json.loads(match.group())
            if "groups" in plan and plan["groups"]:
                logger.info("Layout plan: %d groups", len(plan["groups"]))
                return plan
        logger.warning("LLM layout plan missing groups: %s", content[:200])
    except Exception as exc:
        logger.warning("Layout plan generation failed: %s", exc)

    return None


def _fallback_plan(brief: dict) -> dict:
    """Keyword-based layout plan used when the LLM call fails."""
    styles     = brief.get("style", [])
    rooms      = brief.get("rooms_priority", [])
    must_haves = brief.get("must_haves", [])
    vibe_words = brief.get("vibe_words", [])

    style        = " ".join(styles[:2]) if styles else "modern"
    vibe         = " ".join(vibe_words[:2]) if vibe_words else style
    primary_room = rooms[0] if rooms else "living room"
    second_room  = rooms[1] if len(rooms) > 1 else "bedroom"
    item         = must_haves[0] if must_haves else "sofa"

    return {
        "groups": [
            {
                "theme": primary_room.replace(" ", "_"),
                "size": "hero",
                "queries": [
                    f"{style} {primary_room} interior",
                    f"{primary_room} interior design room",
                ],
            },
            {
                "theme": second_room.replace(" ", "_"),
                "size": "medium",
                "queries": [
                    f"{style} {second_room} interior",
                    f"{second_room} room design interior",
                ],
            },
            {
                "theme": "furniture",
                "size": "medium",
                "queries": [
                    f"{style} {item} living room interior",
                    f"{style} furniture interior design room",
                ],
            },
            {
                "theme": "atmosphere",
                "size": "small",
                "queries": [
                    f"{vibe} interior design room",
                    f"{style} natural light interior room",
                ],
            },
        ]
    }


# ---------------------------------------------------------------------------
# Fetch unique images from Pexels
# ---------------------------------------------------------------------------

def _fetch_unique_images(
    groups: list[dict],
    n: int | None = None,
) -> list[tuple[str, int, int]]:
    """
    Fetch 2 images per query.  Returns (url, orig_w, orig_h) tuples.
    URL uses only ?w=940 (no h= constraint) — proportional resize, no crop.
    Deduped by photo ID. Ordered hero → medium → small.
    Capped at n (defaults to len(_IMG_SLOTS)).
    """
    cap = n if n is not None else len(_IMG_SLOTS)

    if not PEXELS_API_KEY:
        logger.warning("PEXELS_API_KEY not set — skipping vision images")
        return []

    size_order = {"hero": 0, "medium": 1, "small": 2}
    sorted_groups = sorted(groups, key=lambda g: size_order.get(g.get("size", "medium"), 1))

    seen_ids: set[str] = set()
    results: list[tuple[str, int, int]] = []

    for group in sorted_groups:
        for query in group.get("queries", []):
            try:
                resp = httpx.get(
                    "https://api.pexels.com/v1/search",
                    headers={"Authorization": PEXELS_API_KEY},
                    params={"query": query, "per_page": 2, "orientation": "landscape"},
                    timeout=8.0,
                )
                resp.raise_for_status()
                for photo in resp.json().get("photos", []):
                    pid = str(photo["id"])
                    if pid not in seen_ids:
                        seen_ids.add(pid)
                        url = (
                            f"https://images.pexels.com/photos/{photo['id']}/"
                            f"pexels-photo-{photo['id']}.jpeg"
                            "?auto=compress&cs=tinysrgb&w=940"
                        )
                        results.append((url, photo["width"], photo["height"]))
            except Exception as exc:
                logger.warning("Pexels fetch failed for '%s': %s", query, exc)

    logger.info("Fetched %d unique images across %d groups", len(results), len(sorted_groups))
    return results[:cap]


# ---------------------------------------------------------------------------
# Fallback path — programmatic slot layout
# ---------------------------------------------------------------------------

def _upload_image_binary(
    client: httpx.Client,
    board_id: str,
    auth_token: str,
    img_url: str,
    width: int,
    x: int,
    y: int,
    orig_w: int,
    orig_h: int,
) -> bool:
    """Binary multipart upload with height-only geometry (avoids square default)."""
    try:
        dl = httpx.get(img_url, timeout=25.0, follow_redirects=True)
        dl.raise_for_status()
    except Exception as exc:
        logger.warning("Download failed for %s: %s", img_url[:60], exc)
        return False

    content_type = dl.headers.get("content-type", "image/jpeg").split(";")[0]
    target_height = round(width * orig_h / orig_w)
    data_payload = json.dumps({
        "position": {"x": x, "y": y},
        "geometry": {"height": target_height},
    })

    try:
        r = client.post(
            f"{_MIRO_API_BASE}/boards/{board_id}/images",
            headers={"Authorization": auth_token, "Accept": "application/json"},
            files={"resource": ("photo.jpg", dl.content, content_type)},
            data={"data": data_payload},
        )
        if r.is_success:
            return True
        logger.warning("Miro upload %s: %s", r.status_code, r.text[:150])
    except Exception as exc:
        logger.warning("Miro multipart upload exception: %s", exc)

    return False


def _add_vision_images(client: httpx.Client, headers: dict, board_id: str, brief: dict) -> None:
    plan   = _llm_layout_plan(brief) or _fallback_plan(brief)
    images = _fetch_unique_images(plan.get("groups", []))

    if not images:
        logger.warning("No images fetched — skipping vision board imagery")
        return

    auth_token = headers["Authorization"]
    placed = 0

    for img_url, orig_w, orig_h in images:
        if placed >= len(_IMG_SLOTS):
            break
        x, y, width = _IMG_SLOTS[placed]
        ok = _upload_image_binary(client, board_id, auth_token, img_url, width, x, y, orig_w, orig_h)
        if ok:
            placed += 1
            logger.info("Image %2d -> slot %2d  (%dpx at %d, %d)", placed, placed - 1, width, x, y)

    logger.info("Vision images placed: %d / %d", placed, len(images))


def _add_sticky_notes(client: httpx.Client, headers: dict, board_id: str, brief: dict) -> None:
    base_url = f"{_MIRO_API_BASE}/boards/{board_id}/sticky_notes"

    budget_val = brief.get("budget")
    currency   = brief.get("currency", "EUR")
    budget_str = f"{currency} {int(budget_val):,}" if budget_val else "TBD"

    content_map = {
        "BUDGET":      budget_str,
        "ROOMS":       _join(brief.get("rooms_priority")),
        "MUST HAVES":  _join(brief.get("must_haves")),
        "CONSTRAINTS": _join(brief.get("constraints")),
        "STYLE":       _join(brief.get("style")),
        "VIBE":        _join(brief.get("vibe_words")),
        "AVOID":       _join(brief.get("avoid")),
        "NOTES":       brief.get("notes") or "—",
    }

    for label, (color, x, y) in _STICKY_COLS.items():
        value = content_map.get(label, "—")
        try:
            client.post(
                base_url,
                headers=headers,
                json={
                    "data":     {"content": f"{label}\n{value}", "shape": "square"},
                    "style":    {"fillColor": color},
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
