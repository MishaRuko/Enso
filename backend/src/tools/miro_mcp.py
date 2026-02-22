"""
Miro vision-board generation — 2-pass AI-driven layout.

Pass 1 (Plan):
  Claude searches Pexels and calls submit_layout_plan with a strict JSON plan
  (image slots: x/y/width/rotation, sticky positions, summary text).
  The plan is stored for audit and applied deterministically via REST.

Pass 2 (Refine):
  Claude reviews the placed items (slot_id → miro_item_id map) and calls
  move_item / move_sticky to nudge positions for collage feel, better
  whitespace, and readable sticky notes.
  If Pass 2 raises, the Pass 1 board is returned unchanged.

Tiers:
  1. 2-pass REST agent  (MIRO_MCP_ENABLED=true + valid API keys)
  2. Deterministic REST fallback (miro.create_board_from_brief)
"""

import json
import logging
import re
from dataclasses import dataclass

import httpx

from ..config import (MIRO_API_TOKEN, MIRO_MCP_ENABLED, OPENROUTER_API_KEY,
                      PEXELS_API_KEY)
from .miro import create_board_from_brief

logger = logging.getLogger(__name__)

_MIRO_API_BASE = "https://api.miro.com/v2"
_AGENT_MODEL   = "anthropic/claude-sonnet-4-6"
_MAX_TURNS     = 25  # hard cap per pass

# ─────────────────────────────────────────────────────────────────────────────
# Hardcoded grid — positions injected at placement time, not decided by the AI
# ─────────────────────────────────────────────────────────────────────────────

# Image slots: (x, y) = board centre coordinates; width in px; rotation in °
# Arranged in a 3-column grid. At 3:2 aspect ratio, each image height ≈ width * 0.67.
# hero (440px) → h≈293  medium (300px) → h≈200  small (180px) → h≈120
# Column centres: left=-560, centre=0, right=+560
# Row centres:    top=-320, middle=0, bottom=+340
_GRID_SLOTS: dict[str, dict] = {
    "hero":     {"x":    0, "y":    0, "width": 440, "rotation": 0},   # centre, middle
    "medium_1": {"x":  560, "y": -220, "width": 300, "rotation": 0},   # right, upper
    "medium_2": {"x":  560, "y":  220, "width": 300, "rotation": 0},   # right, lower
    "medium_3": {"x": -560, "y": -220, "width": 300, "rotation": 0},   # left, upper
    "medium_4": {"x": -560, "y":  220, "width": 300, "rotation": 0},   # left, lower
    "small_1":  {"x":  190, "y": -360, "width": 200, "rotation": 0},   # centre-right, top
    "small_2":  {"x":  850, "y":    0, "width": 170, "rotation": 0},   # far right, middle
    "small_3":  {"x": -190, "y":  360, "width": 200, "rotation": 0},   # centre-left, bottom
    "small_4":  {"x": -850, "y":    0, "width": 170, "rotation": 0},   # far left, middle
}

# Sticky slots: fixed position and colour per brief field label
_STICKY_SLOTS: dict[str, dict] = {
    "STYLE":       {"x": -1100, "y": -600, "color": "light_blue"},
    "VIBE":        {"x": -1100, "y": -280, "color": "cyan"},
    "AVOID":       {"x": -1100, "y":   40, "color": "red"},
    "NOTES":       {"x": -1100, "y":  360, "color": "white"},
    "BUDGET":      {"x":  1100, "y": -600, "color": "light_yellow"},
    "ROOMS":       {"x":  1100, "y": -280, "color": "light_green"},
    "MUST HAVES":  {"x":  1100, "y":   40, "color": "light_pink"},
    "CONSTRAINTS": {"x":  1100, "y":  360, "color": "gray"},
}



# ─────────────────────────────────────────────────────────────────────────────
# Result type
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class BoardResult:
    url: str
    layout_plan: dict | None = None
    pass2_applied: bool = False


# ─────────────────────────────────────────────────────────────────────────────
# Public entry point
# ─────────────────────────────────────────────────────────────────────────────

def generate_vision_board_with_miro_ai(brief: dict) -> BoardResult:
    """
    Create a Miro vision board using a 2-pass AI agent loop.
    Always returns a BoardResult with a valid URL.
    """
    if not MIRO_API_TOKEN or not OPENROUTER_API_KEY or not MIRO_MCP_ENABLED:
        logger.warning("2-pass agent disabled or missing keys — deterministic fallback")
        return BoardResult(url=create_board_from_brief(brief))

    try:
        return _two_pass_agent(brief)
    except Exception as exc:
        logger.warning("2-pass agent failed (%s) — deterministic fallback", exc)
        return BoardResult(url=create_board_from_brief(brief))


# ─────────────────────────────────────────────────────────────────────────────
# Pass 1 tool schemas — search + plan submission
# ─────────────────────────────────────────────────────────────────────────────

_PASS1_TOOLS: list[dict] = [
    {
        "type": "function",
        "function": {
            "name": "search_pexels",
            "description": (
                "Search Pexels for landscape interior design photos. "
                "Returns [{id, url, width, height}, ...]. "
                "Always include 'interior' or 'room' in every query for full-room shots."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query":    {"type": "string"},
                    "per_page": {"type": "integer", "default": 4, "maximum": 5},
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "submit_layout_plan",
            "description": (
                "Submit the complete Pass 1 layout plan. "
                "Call this ONCE — only after searching for all photos and selecting candidates. "
                "This ends Pass 1. Do NOT call it more than once. "
                "Positions, sizes, and rotations are handled by the system — do NOT provide them."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "board_name": {
                        "type": "string",
                        "description": "Descriptive board name",
                    },
                    "images": {
                        "type": "array",
                        "description": (
                            "Exactly 9 image slots, one per fixed slot_id. "
                            "Allowed slot_ids: hero, medium_1, medium_2, medium_3, medium_4, "
                            "small_1, small_2, small_3, small_4. No duplicate photo_id allowed."
                        ),
                        "items": {
                            "type": "object",
                            "properties": {
                                "slot_id":  {
                                    "type": "string",
                                    "description": "One of: hero, medium_1, medium_2, medium_3, medium_4, small_1, small_2, small_3, small_4",
                                    "enum": ["hero", "medium_1", "medium_2", "medium_3", "medium_4",
                                             "small_1", "small_2", "small_3", "small_4"],
                                },
                                "photo_id": {"type": "integer", "description": "Pexels photo id (dedup key)"},
                                "url":      {"type": "string",  "description": "Pexels ?w=940 image URL"},
                                "orig_w":   {"type": "integer", "description": "Original pixel width from search result"},
                                "orig_h":   {"type": "integer", "description": "Original pixel height from search result"},
                            },
                            "required": ["slot_id", "photo_id", "url", "orig_w", "orig_h"],
                        },
                    },
                    "stickies": {
                        "type": "array",
                        "description": (
                            "Exactly 8 sticky notes, one per brief category. "
                            "Allowed labels: STYLE, VIBE, AVOID, NOTES, BUDGET, ROOMS, MUST HAVES, CONSTRAINTS. "
                            "Positions and colors are handled by the system."
                        ),
                        "items": {
                            "type": "object",
                            "properties": {
                                "label":   {
                                    "type": "string",
                                    "description": "One of: STYLE, VIBE, AVOID, NOTES, BUDGET, ROOMS, MUST HAVES, CONSTRAINTS",
                                    "enum": ["STYLE", "VIBE", "AVOID", "NOTES", "BUDGET", "ROOMS", "MUST HAVES", "CONSTRAINTS"],
                                },
                                "value":   {"type": "string", "description": "Body text from brief"},
                            },
                            "required": ["label", "value"],
                        },
                    },
                },
                "required": ["board_name", "images", "stickies"],
            },
        },
    },
]


# ─────────────────────────────────────────────────────────────────────────────
# Pass 2 tool schemas — positional refinement
# ─────────────────────────────────────────────────────────────────────────────

_PASS2_TOOLS: list[dict] = [
    {
        "type": "function",
        "function": {
            "name": "move_item",
            "description": (
                "Nudge a placed image to a new centre position, or resize it. "
                "Use the miro_item_id from the Pass 1 placements map. "
                "Maximum nudge: ±150 px from current position."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "board_id":     {"type": "string"},
                    "miro_item_id": {"type": "string"},
                    "x":            {"type": "number",  "description": "New centre x"},
                    "y":            {"type": "number",  "description": "New centre y"},
                    "width":        {"type": "integer", "description": "New display width (optional)"},
                },
                "required": ["board_id", "miro_item_id", "x", "y"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "move_sticky",
            "description": (
                "Move a sticky note to a new centre position. "
                "Stickies must stay in their side columns (x < −900 or x > +900). "
                "Use the miro_item_id from the Pass 1 placements map."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "board_id":     {"type": "string"},
                    "miro_item_id": {"type": "string"},
                    "x":            {"type": "number"},
                    "y":            {"type": "number"},
                },
                "required": ["board_id", "miro_item_id", "x", "y"],
            },
        },
    },
]


# ─────────────────────────────────────────────────────────────────────────────
# REST tool implementations
# ─────────────────────────────────────────────────────────────────────────────

def _auth() -> str:
    return f"Bearer {MIRO_API_TOKEN}"


def _tool_search_pexels(query: str, per_page: int = 4) -> list[dict]:
    if not PEXELS_API_KEY:
        return []
    r = httpx.get(
        "https://api.pexels.com/v1/search",
        headers={"Authorization": PEXELS_API_KEY},
        params={"query": query, "per_page": min(per_page, 5), "orientation": "landscape"},
        timeout=10.0,
    )
    r.raise_for_status()
    return [
        {
            "id":     p["id"],
            "url":    (
                f"https://images.pexels.com/photos/{p['id']}/"
                f"pexels-photo-{p['id']}.jpeg?auto=compress&cs=tinysrgb&w=940"
            ),
            "width":  p["width"],
            "height": p["height"],
        }
        for p in r.json().get("photos", [])
    ]


def _tool_create_board(name: str) -> dict:
    r = httpx.post(
        f"{_MIRO_API_BASE}/boards",
        headers={"Authorization": _auth(), "Content-Type": "application/json", "Accept": "application/json"},
        json={"name": name, "description": "AI-generated interior design vision board"},
        timeout=30.0,
    )
    r.raise_for_status()
    d = r.json()
    logger.info("Created board: %s", d["viewLink"])
    return {"board_id": d["id"], "board_url": d["viewLink"]}


def _tool_place_image(
    board_id: str,
    url: str,
    orig_w: int,
    orig_h: int,
    x: float,
    y: float,
    width: int,
    rotation: float = 0.0,
) -> dict:
    """Two-step POST+PATCH: sets both width and height to prevent Miro cropping."""
    try:
        dl = httpx.get(url, timeout=25.0, follow_redirects=True)
        dl.raise_for_status()
    except Exception as exc:
        return {"ok": False, "error": f"Download failed: {exc}"}

    content_type = dl.headers.get("content-type", "image/jpeg").split(";")[0]
    target_h = round(width * orig_h / orig_w)

    position: dict = {"x": x, "y": y}
    if rotation:
        position["rotation"] = rotation

    # Step 1: POST binary (position only — Miro only allows one geometry dimension here)
    r = httpx.post(
        f"{_MIRO_API_BASE}/boards/{board_id}/images",
        headers={"Authorization": _auth(), "Accept": "application/json"},
        files={"resource": ("photo.jpg", dl.content, content_type)},
        data={"data": json.dumps({"position": position})},
        timeout=60.0,
    )
    if not r.is_success:
        return {"ok": False, "error": r.text[:200]}
    item_id = r.json()["id"]

    # Step 2: PATCH position + width. Miro sometimes ignores position from the
    # multipart POST; PATCHing it explicitly guarantees the correct placement.
    p = httpx.patch(
        f"{_MIRO_API_BASE}/boards/{board_id}/images/{item_id}",
        headers={"Authorization": _auth(), "Content-Type": "application/json", "Accept": "application/json"},
        json={
            "geometry": {"width": width},
            "position": {"x": x, "y": y, "origin": "center"},
        },
        timeout=15.0,
    )
    if not p.is_success:
        logger.warning("Image PATCH %s: %s", p.status_code, p.text[:100])

    return {"ok": True, "item_id": item_id, "width": width, "height": target_h}


def _tool_sticky_note(
    board_id: str, label: str, value: str, x: float, y: float, color: str,
) -> dict:
    r = httpx.post(
        f"{_MIRO_API_BASE}/boards/{board_id}/sticky_notes",
        headers={"Authorization": _auth(), "Content-Type": "application/json", "Accept": "application/json"},
        json={
            "data":     {"content": f"{label}\n{value}", "shape": "square"},
            "style":    {"fillColor": color},
            "geometry": {"width": 220},
            "position": {"x": x, "y": y, "origin": "center"},
        },
        timeout=15.0,
    )
    if r.is_success:
        return {"ok": True, "item_id": r.json()["id"]}
    return {"ok": False, "status": r.status_code, "error": r.text[:100]}


def _tool_text_block(board_id: str, content: str, x: float, y: float, width: int = 520) -> dict:
    r = httpx.post(
        f"{_MIRO_API_BASE}/boards/{board_id}/texts",
        headers={"Authorization": _auth(), "Content-Type": "application/json", "Accept": "application/json"},
        json={
            "data":     {"content": content},
            "style":    {"fontSize": "14", "textAlign": "left", "color": "#1a1a1a"},
            "geometry": {"width": width},
            "position": {"x": x, "y": y, "origin": "center"},
        },
        timeout=15.0,
    )
    if r.is_success:
        return {"ok": True, "item_id": r.json()["id"]}
    return {"ok": False, "status": r.status_code}


def _tool_move_item(
    board_id: str, item_id: str, x: float, y: float, width: int | None = None,
) -> dict:
    payload: dict = {"position": {"x": x, "y": y, "origin": "center"}}
    if width is not None:
        payload["geometry"] = {"width": width}
    r = httpx.patch(
        f"{_MIRO_API_BASE}/boards/{board_id}/images/{item_id}",
        headers={"Authorization": _auth(), "Content-Type": "application/json", "Accept": "application/json"},
        json=payload,
        timeout=15.0,
    )
    return {"ok": r.is_success, "status": r.status_code}


def _tool_move_sticky(board_id: str, item_id: str, x: float, y: float) -> dict:
    r = httpx.patch(
        f"{_MIRO_API_BASE}/boards/{board_id}/sticky_notes/{item_id}",
        headers={"Authorization": _auth(), "Content-Type": "application/json", "Accept": "application/json"},
        json={"position": {"x": x, "y": y, "origin": "center"}},
        timeout=15.0,
    )
    return {"ok": r.is_success, "status": r.status_code}


# ─────────────────────────────────────────────────────────────────────────────
# Shared LLM call
# ─────────────────────────────────────────────────────────────────────────────

def _llm(system: str, messages: list[dict], tools: list[dict]) -> dict:
    resp = httpx.post(
        "https://openrouter.ai/api/v1/chat/completions",
        headers={"Authorization": f"Bearer {OPENROUTER_API_KEY}", "Content-Type": "application/json"},
        json={
            "model":       _AGENT_MODEL,
            "messages":    [{"role": "system", "content": system}] + messages,
            "tools":       tools,
            "tool_choice": "auto",
            "max_tokens":  4096,
        },
        timeout=90.0,
    )
    resp.raise_for_status()
    return resp.json()["choices"][0]


# ─────────────────────────────────────────────────────────────────────────────
# System prompts
# ─────────────────────────────────────────────────────────────────────────────

_PASS1_SYSTEM = """\
You are an expert interior design AI curating photos for a Miro vision board.

The board layout (positions, sizes, rotations) is handled entirely by the system.
Your only job is to select the right photos and write the text content.

WORKFLOW — follow every step exactly:

1. SEARCH — call search_pexels 5–7 times with varied, brief-tailored queries.
   Always include "interior" or "room" for full-room shots. Themes to cover:
   primary room aesthetic, secondary room type, furniture/objects, atmosphere,
   textures/materials, colour palette, lifestyle/mood.
   Collect 15–20 candidate photos total.

2. SELECT — choose exactly 9 photos (no duplicate photo_id) and assign each to
   one of the 9 fixed slot IDs. Pick the most impactful photo for each slot:
   • hero     — your single best full-room shot; anchors the board
   • medium_1 — second strongest room or furniture photo
   • medium_2 — third strongest; complements hero
   • medium_3 — fourth; different angle or texture focus
   • medium_4 — fifth; colour palette or material emphasis
   • small_1  — accent detail, close-up, or lifestyle shot
   • small_2  — texture or material detail
   • small_3  — another detail or complementary mood shot
   • small_4  — final accent; may repeat a theme with a different photo

3. STICKIES — write the text value for each of the 8 sticky note labels.
   Use only these exact labels (system handles position and colour):
   STYLE, VIBE, AVOID, NOTES, BUDGET, ROOMS, MUST HAVES, CONSTRAINTS
   Draw values directly from the brief. If a field has no value, write "—".

4. SUBMIT — call submit_layout_plan ONCE with the complete plan.
   After the call, output nothing else.

RULES:
• Never duplicate a photo_id across image slots.
• Use all 9 slot IDs exactly as listed above — no custom slot names.
• Do NOT provide x, y, width, rotation, or color — those are set by the system.
• Do NOT call submit_layout_plan more than once.
"""

_PASS2_SYSTEM = """\
You are a layout refinement AI for a Miro vision board.

A board has been created from a layout plan. Your job is to make small
positional tweaks using move_item and move_sticky.

REFINEMENT GOALS (in priority order):
1. COLLAGE FEEL — introduce or tighten corner overlaps (10–30 px) where gaps
   are too large. Images should feel organically arranged, not grid-like.
2. WHITESPACE — target 20–30 % empty canvas. Nudge images inward if too
   spread out; apart if too cramped.
3. NO EXCESSIVE OVERLAP — no two images should overlap by more than
   30 % of the smaller image's area.
4. STICKY READABILITY — stickies must stay in their side columns
   (x < −900 or x > +900). Align y values with nearby image rows.
   Never overlap the image cluster.
5. SUBTLETY — maximum nudge: ±150 px per item. Do not relocate items to
   entirely new canvas areas.

You will receive:
• The Pass 1 layout plan JSON (slot positions and sizes).
• A placement map: {slot_id: miro_item_id} for images and stickies.
• The board_id.

Call move_item for images and move_sticky for sticky notes.
When satisfied (or if no improvements are needed), output exactly:
  REFINED: ok
"""


# ─────────────────────────────────────────────────────────────────────────────
# Pass 1 — plan generation
# ─────────────────────────────────────────────────────────────────────────────

def _pass1_generate_plan(brief: dict) -> dict | None:
    """
    Run Claude to search photos and call submit_layout_plan.
    Returns the raw plan dict (the args of submit_layout_plan) or None.
    """
    messages: list[dict] = [
        {
            "role": "user",
            "content": (
                "Create a Miro vision board layout plan for this interior design brief:\n\n"
                f"{json.dumps(brief, indent=2)}\n\n"
                "Follow the workflow in your system instructions exactly. "
                "Call submit_layout_plan once with the complete plan."
            ),
        }
    ]

    layout_plan: dict | None = None

    for turn in range(_MAX_TURNS):
        logger.info("Pass 1 — turn %d/%d", turn + 1, _MAX_TURNS)
        choice  = _llm(_PASS1_SYSTEM, messages, _PASS1_TOOLS)
        msg     = choice["message"]
        finish  = choice["finish_reason"]
        content = msg.get("content") or ""

        assistant_msg: dict = {"role": "assistant", "content": content}
        if msg.get("tool_calls"):
            assistant_msg["tool_calls"] = msg["tool_calls"]
        messages.append(assistant_msg)

        if finish in ("stop", "end_turn") or not msg.get("tool_calls"):
            logger.info("Pass 1 finished (finish_reason=%s) after %d turns", finish, turn + 1)
            break

        tool_results: list[dict] = []
        for tc in msg["tool_calls"]:
            fn_name = tc["function"]["name"]
            fn_args = json.loads(tc["function"]["arguments"])
            logger.info("Pass1 → %s(%s)", fn_name, str(fn_args)[:140])

            if fn_name == "search_pexels":
                result = _tool_search_pexels(fn_args["query"], fn_args.get("per_page", 4))
                result_str = json.dumps(result)

            elif fn_name == "submit_layout_plan":
                layout_plan = fn_args
                result_str  = json.dumps({
                    "ok": True,
                    "images":   len(fn_args.get("images", [])),
                    "stickies": len(fn_args.get("stickies", [])),
                })
                logger.info(
                    "Pass 1 plan received: %d images, %d stickies",
                    len(fn_args.get("images", [])),
                    len(fn_args.get("stickies", [])),
                )
            else:
                result_str = json.dumps({"error": f"Tool '{fn_name}' not available in Pass 1"})

            logger.info("Pass1 ← %s", result_str[:160])
            tool_results.append({
                "role":         "tool",
                "tool_call_id": tc["id"],
                "content":      result_str,
            })

        messages.extend(tool_results)

        if layout_plan is not None:
            break  # plan received — no need for another LLM turn

    else:
        logger.warning("Pass 1 hit max turns (%d)", _MAX_TURNS)

    return layout_plan


# ─────────────────────────────────────────────────────────────────────────────
# Plan execution — deterministic REST placement
# ─────────────────────────────────────────────────────────────────────────────

def _apply_layout_plan(
    plan: dict,
) -> tuple[str, str, dict[str, str], dict[str, str]]:
    """
    Execute a layout plan via REST calls.

    Returns:
        (board_id, board_url, image_placements, sticky_placements)
        where *_placements map slot_id → miro_item_id.
    """
    board     = _tool_create_board(plan["board_name"])
    board_id  = board["board_id"]
    board_url = board["board_url"]

    image_placements: dict[str, str] = {}
    used_photo_ids:   set[int]       = set()

    for img in plan.get("images", []):
        pid = int(img["photo_id"])
        if pid in used_photo_ids:
            logger.warning("Dedup: skipping repeated photo_id %d", pid)
            continue
        used_photo_ids.add(pid)

        slot = _GRID_SLOTS.get(img["slot_id"], {"x": 0, "y": 0, "width": 400, "rotation": 0})
        result = _tool_place_image(
            board_id,
            img["url"],
            int(img["orig_w"]),
            int(img["orig_h"]),
            float(slot["x"]),
            float(slot["y"]),
            int(slot["width"]),
            float(slot.get("rotation", 0)),
        )
        if result.get("ok"):
            image_placements[img["slot_id"]] = result["item_id"]
            logger.info("Placed %s → %s", img["slot_id"], result["item_id"])
        else:
            logger.warning("Failed to place %s: %s", img["slot_id"], result.get("error"))

    sticky_placements: dict[str, str] = {}

    for s in plan.get("stickies", []):
        pos = _STICKY_SLOTS.get(s["label"].upper(), {"x": 0, "y": 500, "color": "light_yellow"})
        result = _tool_sticky_note(
            board_id, s["label"], s["value"],
            float(pos["x"]), float(pos["y"]), pos["color"],
        )
        if result.get("ok"):
            sticky_placements[s["label"]] = result["item_id"]

    logger.info(
        "Plan applied: %d images, %d stickies on %s",
        len(image_placements), len(sticky_placements), board_url,
    )
    return board_id, board_url, image_placements, sticky_placements


# ─────────────────────────────────────────────────────────────────────────────
# Pass 2 — refinement
# ─────────────────────────────────────────────────────────────────────────────

def _pass2_refine(
    board_id: str,
    layout_plan: dict,
    image_placements: dict[str, str],
    sticky_placements: dict[str, str],
) -> bool:
    """
    Run Claude to nudge positions. Returns True if any moves were applied.
    """
    context_msg = (
        "The Miro board has been populated from this layout plan. "
        "Please review and refine positions.\n\n"
        "LAYOUT PLAN:\n"
        f"{json.dumps(layout_plan, indent=2)}\n\n"
        "IMAGE PLACEMENTS (slot_id → miro_item_id):\n"
        f"{json.dumps(image_placements, indent=2)}\n\n"
        "STICKY PLACEMENTS (slot_id → miro_item_id):\n"
        f"{json.dumps(sticky_placements, indent=2)}\n\n"
        f"board_id: {board_id}\n\n"
        "Use move_item and move_sticky to nudge positions. "
        "When done, output: REFINED: ok"
    )
    messages: list[dict] = [{"role": "user", "content": context_msg}]

    moved = False

    for turn in range(_MAX_TURNS):
        logger.info("Pass 2 — turn %d/%d", turn + 1, _MAX_TURNS)
        choice  = _llm(_PASS2_SYSTEM, messages, _PASS2_TOOLS)
        msg     = choice["message"]
        finish  = choice["finish_reason"]
        content = msg.get("content") or ""

        assistant_msg: dict = {"role": "assistant", "content": content}
        if msg.get("tool_calls"):
            assistant_msg["tool_calls"] = msg["tool_calls"]
        messages.append(assistant_msg)

        # Completion signal or no more tool calls
        if finish in ("stop", "end_turn") or not msg.get("tool_calls"):
            if "REFINED:" in content:
                logger.info("Pass 2 agent signalled completion")
            else:
                logger.info("Pass 2 finished (finish_reason=%s)", finish)
            break

        tool_results: list[dict] = []
        for tc in msg["tool_calls"]:
            fn_name = tc["function"]["name"]
            fn_args = json.loads(tc["function"]["arguments"])
            logger.info("Pass2 → %s(%s)", fn_name, str(fn_args)[:120])

            if fn_name == "move_item":
                result = _tool_move_item(
                    fn_args["board_id"],
                    fn_args["miro_item_id"],
                    float(fn_args["x"]),
                    float(fn_args["y"]),
                    int(fn_args["width"]) if "width" in fn_args else None,
                )
                if result.get("ok"):
                    moved = True

            elif fn_name == "move_sticky":
                result = _tool_move_sticky(
                    fn_args["board_id"],
                    fn_args["miro_item_id"],
                    float(fn_args["x"]),
                    float(fn_args["y"]),
                )
                if result.get("ok"):
                    moved = True

            else:
                result = {"error": f"Tool '{fn_name}' not available in Pass 2"}

            result_str = json.dumps(result)
            logger.info("Pass2 ← %s", result_str[:120])
            tool_results.append({
                "role":         "tool",
                "tool_call_id": tc["id"],
                "content":      result_str,
            })

        messages.extend(tool_results)

    else:
        logger.warning("Pass 2 hit max turns (%d)", _MAX_TURNS)

    return moved


# ─────────────────────────────────────────────────────────────────────────────
# 2-pass orchestrator
# ─────────────────────────────────────────────────────────────────────────────

def _two_pass_agent(brief: dict) -> BoardResult:
    # ── Pass 1: generate layout plan ─────────────────────────────────────────
    logger.info("Starting Pass 1: layout plan generation")
    layout_plan = _pass1_generate_plan(brief)

    if not layout_plan or not layout_plan.get("images"):
        logger.warning("Pass 1 returned no valid plan — deterministic fallback")
        return BoardResult(url=create_board_from_brief(brief))

    # ── Apply plan via REST ───────────────────────────────────────────────────
    logger.info(
        "Applying layout plan: %d images, %d stickies",
        len(layout_plan.get("images", [])),
        len(layout_plan.get("stickies", [])),
    )
    board_id, board_url, image_placements, sticky_placements = _apply_layout_plan(layout_plan)

    if not board_id:
        logger.warning("Board creation failed — deterministic fallback")
        return BoardResult(url=create_board_from_brief(brief))

    logger.info("Pass 1 complete: %s | %d images placed", board_url, len(image_placements))

    # ── Pass 2: refinement ────────────────────────────────────────────────────
    pass2_applied = False
    try:
        logger.info("Starting Pass 2: layout refinement")
        pass2_applied = _pass2_refine(
            board_id, layout_plan, image_placements, sticky_placements,
        )
        logger.info("Pass 2 complete (moves applied: %s)", pass2_applied)
    except Exception as exc:
        logger.warning("Pass 2 failed (%s) — keeping Pass 1 result", exc)

    return BoardResult(url=board_url, layout_plan=layout_plan, pass2_applied=pass2_applied)
