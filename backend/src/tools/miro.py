"""Miro board creation for design briefs."""

import json
import logging
import re

import httpx

from ..config import MIRO_API_TOKEN, OPENROUTER_API_KEY, PEXELS_API_KEY

logger = logging.getLogger(__name__)

_DEMO_BOARD_URL = "https://miro.com/app/board/demo/"
_MIRO_API_BASE = "https://api.miro.com/v2"
_LAYOUT_MODEL = "anthropic/claude-haiku-4-5"

# ---------------------------------------------------------------------------
# Vision board slot template — Pinterest-style irregular composition
# (x, y, width_px) — board-centre coordinates.
#
# Sizes:  hero = 640 px  |  medium = 460-520 px  |  small = 360 px
#
# Row centres (computed for aspect ratio 1.44:1, ~40 px vertical gap):
#   Row 1  y ≈ −780   Row 2  y ≈ −330   Row 3  y ≈ +55   Row 4  y ≈ +432
# Horizontal gaps ≈ 40-50 px between columns (≈ 3 % of board width).
#
# Board footprint: x ≈ −780 … +760, y ≈ −1000 … +600
# Sticky columns sit outside at x ≈ −1110 and +1020 (never overlap images).
# ---------------------------------------------------------------------------
_IMG_SLOTS = [
    # ── ROW 1 — hero anchor ─────────────────────────────────────────────────
    (-460, -780, 640),   # 0  HERO — largest, top-left
    ( 130, -770, 460),   # 1  medium  (40 px x-gap from hero)
    ( 580, -785, 360),   # 2  small accent, top-right

    # ── ROW 2 ────────────────────────────────────────────────────────────────
    (-580, -330, 360),   # 3  small, far-left
    (-100, -337, 520),   # 4  medium-large (40 px gap from slot 3)
    ( 430, -325, 460),   # 5  medium right (40 px gap from slot 4)

    # ── ROW 3 ────────────────────────────────────────────────────────────────
    (-530,   55, 460),   # 6  medium left
    ( -70,   50, 360),   # 7  small centre (50 px gap from slot 6)
    ( 400,   51, 480),   # 8  medium right (50 px gap from slot 7)

    # ── ROW 4 — bottom zone ──────────────────────────────────────────────────
    (-550,  432, 360),   # 9  small bottom-left
    ( -80,  432, 500),   # 10 medium bottom-centre (40 px gap from slot 9)
    ( 390,  432, 360),   # 11 small bottom-right  (40 px gap from slot 10)
]

# ---------------------------------------------------------------------------
# Sticky note columns — flanking the image canvas, never overlapping images.
# y values aligned to the four image row centres so notes feel visually tied.
# Left  (x ≈ −1110) : aesthetic info — style, vibe, avoid, notes
# Right (x ≈ +1020) : practical info — budget, rooms, must-haves, constraints
# ---------------------------------------------------------------------------
_STICKY_COLS: dict[str, tuple[str, int, int]] = {
    "BUDGET":      ("light_yellow",  1020, -800),
    "ROOMS":       ("light_green",   1020, -340),
    "MUST HAVES":  ("light_pink",    1020,   50),
    "CONSTRAINTS": ("gray",          1020,  430),
    "STYLE":       ("light_blue",   -1110, -800),
    "VIBE":        ("cyan",         -1110, -340),
    "AVOID":       ("red",          -1110,   50),
    "NOTES":       ("white",        -1110,  430),
}


# ---------------------------------------------------------------------------
# Public API — signature unchanged
# ---------------------------------------------------------------------------

def create_board_from_brief(brief: dict) -> str:
    """Create a real Miro board from a design brief and return its URL."""
    if not MIRO_API_TOKEN:
        logger.warning("MIRO_API_TOKEN not set, returning demo board URL")
        return _DEMO_BOARD_URL

    miro_headers = {
        "Authorization": f"Bearer {MIRO_API_TOKEN}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }

    with httpx.Client(timeout=60.0) as client:
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
# Step 1 — Layout planning (Claude produces themed groups)
# ---------------------------------------------------------------------------

def _llm_layout_plan(brief: dict) -> dict | None:
    """
    Ask Claude Haiku for a semantic layout plan: 4-5 themed image groups
    with size hints (hero | medium | small) and Pexels queries.
    Pixel placement is handled by _IMG_SLOTS; Claude only decides themes.
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
# Step 2 — Fetch unique images, hero-first, deduplicated
# ---------------------------------------------------------------------------

def _fetch_unique_images(groups: list[dict]) -> list[str]:
    """
    Fetch 2 images per query using the Pexels large2x URL (~1880 px wide,
    proportional crop — good quality without the multi-MB original files).
    Deduplicate by photo ID. Return URLs ordered hero → medium → small.
    Capped at len(_IMG_SLOTS).
    """
    if not PEXELS_API_KEY:
        logger.warning("PEXELS_API_KEY not set — skipping vision images")
        return []

    size_order = {"hero": 0, "medium": 1, "small": 2}
    sorted_groups = sorted(groups, key=lambda g: size_order.get(g.get("size", "medium"), 1))

    seen_ids: set[str] = set()
    urls: list[str] = []

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
                        # large: ~940 px wide, proportional resize (no forced crop).
                        # large2x has h=650&w=940 which forces a 1.44:1 crop via Imgix.
                        urls.append(photo["src"]["large"])
            except Exception as exc:
                logger.warning("Pexels fetch failed for '%s': %s", query, exc)

    logger.info("Fetched %d unique images across %d groups", len(urls), len(sorted_groups))
    return urls[: len(_IMG_SLOTS)]


# ---------------------------------------------------------------------------
# Step 3 — Upload images to Miro via multipart (binary upload)
# ---------------------------------------------------------------------------

def _jpeg_dims(data: bytes) -> tuple[int, int] | None:
    """
    Parse a JPEG stream to return (width, height) without an image library.
    Walks SOF markers (0xC0–0xCF, excluding 0xC4/0xC8) to find frame dimensions.
    Returns None if parsing fails.
    """
    i = 2  # skip SOI (FF D8)
    while i + 3 < len(data):
        if data[i] != 0xFF:
            break
        marker = data[i + 1]
        # SOF markers that carry image dimensions
        if marker in (0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7,
                      0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF):
            if i + 8 < len(data):
                h = (data[i + 5] << 8) | data[i + 6]
                w = (data[i + 7] << 8) | data[i + 8]
                if w > 0 and h > 0:
                    return w, h
        if i + 3 >= len(data):
            break
        seg_len = (data[i + 2] << 8) | data[i + 3]
        i += 2 + seg_len
    return None


def _upload_image_binary(
    client: httpx.Client,
    board_id: str,
    auth_token: str,
    img_url: str,
    width: int,
    x: int,
    y: int,
) -> bool:
    """
    Download image bytes from Pexels then POST them directly to Miro as a
    multipart/form-data upload.

    Why not data.url?  When Miro fetches by URL its servers must reach the
    Pexels CDN at upload time; timeouts or CDN blocks leave the widget in a
    broken 'click to reload' state.  Uploading the bytes ourselves guarantees
    the image is stored in Miro immediately and always renders.

    Both width AND height are specified in geometry (computed from the image's
    actual aspect ratio) so Miro never crops the image to fit a default frame.
    """
    try:
        dl = httpx.get(img_url, timeout=25.0, follow_redirects=True)
        dl.raise_for_status()
    except Exception as exc:
        logger.warning("Download failed for %s: %s", img_url[:60], exc)
        return False

    content_type = dl.headers.get("content-type", "image/jpeg").split(";")[0]

    # Miro's binary-upload API accepts only ONE of width or height.
    # Prefer passing height (derived from the image's actual pixel dims) so that
    # Miro infers width proportionally — avoids any "square default" when only
    # width is given.  Fall back to width if JPEG parsing fails.
    dims = _jpeg_dims(dl.content)
    if dims:
        img_w, img_h = dims
        geom: dict = {"height": round(width * img_h / img_w)}
    else:
        geom = {"width": width}

    data_payload = json.dumps({
        "position": {"x": x, "y": y},
        "geometry": geom,
    })

    try:
        r = client.post(
            f"{_MIRO_API_BASE}/boards/{board_id}/images",
            # No Content-Type header — httpx sets multipart boundary automatically
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
    """
    1. Claude generates a themed layout plan (groups + size hints).
    2. Fetch unique Pexels images (large2x, hero-first, deduplicated).
    3. Download each and upload as binary to Miro — guarantees rendering.
    4. Place into the pre-designed Pinterest-style slot template.
    """
    plan   = _llm_layout_plan(brief) or _fallback_plan(brief)
    images = _fetch_unique_images(plan.get("groups", []))

    if not images:
        logger.warning("No images fetched — skipping vision board imagery")
        return

    auth_token = headers["Authorization"]
    placed = 0

    for img_url in images:
        if placed >= len(_IMG_SLOTS):
            break
        x, y, width = _IMG_SLOTS[placed]
        ok = _upload_image_binary(client, board_id, auth_token, img_url, width, x, y)
        if ok:
            placed += 1
            logger.info(
                "Image %2d → slot %2d  (%dpx at %d, %d)",
                placed, placed - 1, width, x, y,
            )

    logger.info("Vision images placed: %d / %d", placed, len(images))


# ---------------------------------------------------------------------------
# Sticky notes — two flanking columns, vertically aligned to image rows
# ---------------------------------------------------------------------------

def _add_sticky_notes(client: httpx.Client, headers: dict, board_id: str, brief: dict) -> None:
    """
    8 sticky notes in two columns flanking the image collage.
    Left  (x ≈ −1110): STYLE, VIBE, AVOID, NOTES          (aesthetic)
    Right (x ≈ +1020): BUDGET, ROOMS, MUST HAVES, CONSTRAINTS  (practical)
    y values align with the four image rows — notes feel tied to the imagery.
    """
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
