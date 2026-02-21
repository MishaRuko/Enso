"""Analyze a floor plan image using a vision LLM to extract room polygons.

Uses Gemini via OpenRouter to look at a floor plan and produce structured
room data (polygons, doors, windows) that can be rasterized onto a grid.
"""

import base64
import json
import logging
import re
from pathlib import Path

from .grid_types import CELL_SIZE, DoorInfo, RoomPolygon, WindowInfo
from .rasterize import build_grid_from_polygons, FloorPlanGrid

logger = logging.getLogger(__name__)

_PROMPT_BASE = """\
You are an expert architectural analyst. Analyze this floor plan image and extract precise room geometry.

## Your Task

1. **Determine the building envelope** — the overall bounding box of the entire floor plan in metres.
{scale_guidance}

2. **For each room**, extract a polygon that traces its interior walls. Express vertices as (x, y) coordinates in metres where:
   - Origin (0, 0) is the **top-left** (Northwest) corner of the building envelope
   - x increases **eastward** (to the right)
   - y increases **southward** (downward)
   - Vertices should trace the room boundary clockwise

3. **For each door**, note which room it belongs to, which wall it's on, and its approximate position along that wall.

4. **For each window**, same as doors.

5. **Identify the main entrance** to the building.

## Important Notes
- Include ALL rooms, including hallways/passages, bathrooms, storage rooms, verandahs, etc.
- Rooms are NOT always simple rectangles — they can be L-shaped, T-shaped, or irregular polygons. Trace the actual wall lines.
- Corridors/passages that connect rooms should be included as rooms too.
- Wall thickness is typically 0.15-0.2m; trace the INTERIOR face of walls.
- Doors appear as arcs or gaps in walls. Windows appear as parallel lines or distinctive wall markings.
- **IGNORE all furniture, fixtures, and appliances** shown in the floor plan (beds, sofas, counters, sinks, wardrobes, kitchen islands, etc.). Trace the full room boundary as if the room were completely empty. Built-in counters and wardrobes are NOT walls — the room extends through them to the actual walls.
- Adjacent rooms should share a wall boundary. Rooms that are next to each other in the floor plan must have touching polygons (sharing an edge), with only the wall thickness between them.
- The sum of all room areas (including passages and corridors) plus wall area should approximately equal the total building envelope area.

## Output Format

Return ONLY valid JSON (no markdown fences, no explanation):
{{
  "envelope_width_m": <number>,
  "envelope_height_m": <number>,
  "rooms": [
    {{
      "name": "<room name>",
      "vertices_m": [[x1, y1], [x2, y2], ...],
      "area_sqm": <number from label or estimated>,
      "is_open": <true if this room flows openly into another without a door>,
      "doors": [
        {{
          "wall": "north|south|east|west",
          "position_along_wall_m": <distance from wall start to door center>,
          "width_m": <door width, typically 0.8-1.0>
        }}
      ],
      "windows": [
        {{
          "wall": "north|south|east|west",
          "position_along_wall_m": <distance from wall start to window center>,
          "width_m": <window width>
        }}
      ]
    }}
  ],
  "entrance": {{
    "wall": "north|south|east|west",
    "position_along_wall_m": <number>
  }}
}}"""

_SCALE_FROM_LABELS = """\
   Use any area labels, dimension lines, or scale bars visible in the image to calibrate. For example, if a room is labeled "A: 20.5 m²" and appears roughly 5m × 4m, use that to determine the metre-per-pixel scale. Cross-check with multiple rooms if possible."""

_SCALE_FROM_TOTAL_AREA = """\
   The total property area is approximately {total_area_sqm} m². Use this to calibrate: estimate the building's width-to-height ratio from the image, then derive dimensions such that width × height ≈ {total_area_sqm}. If there are also area labels or dimension lines in the image, use those to cross-check."""

_SCALE_FROM_BOTH = """\
   The total property area is approximately {total_area_sqm} m². Also look for any area labels, dimension lines, or scale bars in the image. Use all available information to calibrate the metre scale. The total envelope area should be close to {total_area_sqm} m²."""


def _build_prompt(total_area_sqm: float | None = None) -> str:
    if total_area_sqm is not None:
        # Check if image might also have labels — we can't know for sure, so use "both"
        guidance = _SCALE_FROM_BOTH.format(total_area_sqm=total_area_sqm)
    else:
        guidance = _SCALE_FROM_LABELS
    return _PROMPT_BASE.format(scale_guidance=guidance)


def _extract_json(text: str) -> str:
    """Strip markdown fences or prose to isolate JSON."""
    m = re.search(r"```(?:json)?\s*(\{[\s\S]*\})\s*```", text)
    if m:
        return m.group(1)
    m = re.search(r"(\{[\s\S]*\})", text)
    if m:
        return m.group(1)
    return text


def _image_to_base64_url(image_path: str) -> str:
    """Convert a local image file to a data URL."""
    path = Path(image_path)
    data = path.read_bytes()
    b64 = base64.b64encode(data).decode()
    suffix = path.suffix.lower()
    mime = {"jpg": "image/jpeg", "jpeg": "image/jpeg", "png": "image/png"}.get(
        suffix.lstrip("."), "image/jpeg"
    )
    return f"data:{mime};base64,{b64}"


def parse_llm_response(raw_json: str) -> tuple[float, float, list[RoomPolygon], tuple[int, int] | None]:
    """Parse the LLM's JSON response into our data types.

    Returns:
        (envelope_width_m, envelope_height_m, rooms, entrance_ij)
    """
    text = _extract_json(raw_json)
    data = json.loads(text)

    envelope_w = float(data["envelope_width_m"])
    envelope_h = float(data["envelope_height_m"])

    rooms: list[RoomPolygon] = []
    for r in data["rooms"]:
        verts = [(float(v[0]), float(v[1])) for v in r["vertices_m"]]
        doors = [
            DoorInfo(
                wall=d["wall"],
                room_name=r["name"],
                position_along_wall_m=float(d["position_along_wall_m"]),
                width_m=float(d.get("width_m", 0.9)),
            )
            for d in r.get("doors", [])
        ]
        windows = [
            WindowInfo(
                wall=w["wall"],
                room_name=r["name"],
                position_along_wall_m=float(w["position_along_wall_m"]),
                width_m=float(w.get("width_m", 1.0)),
            )
            for w in r.get("windows", [])
        ]
        rooms.append(
            RoomPolygon(
                name=r["name"],
                vertices_m=verts,
                area_sqm=float(r.get("area_sqm", 0)),
                doors=doors,
                windows=windows,
                is_open=r.get("is_open", False),
            )
        )

    # Parse entrance
    entrance_ij = None
    if "entrance" in data and data["entrance"]:
        ent = data["entrance"]
        wall = ent.get("wall", "south")
        pos = float(ent.get("position_along_wall_m", 0))
        grid_h = int(envelope_h)
        grid_w = int(envelope_w)
        if wall == "south":
            entrance_ij = (grid_h - 1, min(int(pos), grid_w - 1))
        elif wall == "north":
            entrance_ij = (0, min(int(pos), grid_w - 1))
        elif wall == "west":
            entrance_ij = (min(int(pos), grid_h - 1), 0)
        elif wall == "east":
            entrance_ij = (min(int(pos), grid_h - 1), grid_w - 1)

    return envelope_w, envelope_h, rooms, entrance_ij


from typing import Callable, Awaitable

# Type for the vision LLM callable: (prompt, image_url, temperature) -> response text
VisionLLMCallable = Callable[[str, str, float], Awaitable[str]]


async def _call_and_parse(
    image_url: str,
    total_area_sqm: float | None,
    llm_call: VisionLLMCallable,
    cell_size: float = CELL_SIZE,
) -> FloorPlanGrid:
    """Shared implementation: call LLM, parse response, build grid.

    Args:
        image_url: Base64 data URL or public URL of the floor plan.
        total_area_sqm: Optional total area hint for scale calibration.
        llm_call: Async callable (prompt, image_url, temperature) -> str.
        cell_size: Grid cell size in metres (default 1.0). Use 0.5 for higher detail.
    """
    prompt = _build_prompt(total_area_sqm)

    raw = await llm_call(prompt, image_url, 0.2)
    logger.info("Got LLM response (%d chars)", len(raw))
    logger.debug("Raw response: %s", raw[:2000])

    envelope_w, envelope_h, rooms, entrance_ij = parse_llm_response(raw)
    logger.info(
        "Parsed: envelope=%.1fm x %.1fm, %d rooms, entrance=%s",
        envelope_w, envelope_h, len(rooms), entrance_ij,
    )

    for room in rooms:
        logger.info(
            "  Room '%s': %d vertices, area=%.1f m², %d doors, %d windows",
            room.name, len(room.vertices_m), room.area_sqm,
            len(room.doors), len(room.windows),
        )

    grid = build_grid_from_polygons(
        rooms=rooms,
        envelope_width_m=envelope_w,
        envelope_height_m=envelope_h,
        cell_size=cell_size,
        entrance_ij=entrance_ij,
    )

    total_room_cells = sum(len(c) for c in grid.room_cells.values())
    logger.info(
        "Grid: %dx%d (%d cells, %.1fm/cell), %d room cells, %d passage cells",
        grid.width, grid.height, grid.width * grid.height, cell_size,
        total_room_cells, len(grid.passage_cells),
    )

    return grid


async def analyze_floorplan(
    image_path: str,
    total_area_sqm: float | None = None,
    cell_size: float = CELL_SIZE,
) -> FloorPlanGrid:
    """Analyze a floor plan image and return a rasterized grid.

    Args:
        image_path: Path to the floor plan image file.
        total_area_sqm: Optional total property area in m². Helps the LLM
            determine the correct scale when the floor plan has no dimension
            labels or area annotations.
        cell_size: Grid resolution in metres per cell. Default 1.0m. Use 0.5
            for finer detail (4x more cells, better accuracy for small rooms).

    Returns:
        A FloorPlanGrid ready for furniture optimization.
    """
    from ..tools.llm import call_gemini_with_image

    logger.info("Analyzing floor plan: %s (total_area=%s, cell_size=%s)", image_path, total_area_sqm, cell_size)
    image_url = _image_to_base64_url(image_path)
    return await _call_and_parse(image_url, total_area_sqm, call_gemini_with_image, cell_size)


async def analyze_floorplan_from_url(
    image_url: str,
    total_area_sqm: float | None = None,
    cell_size: float = CELL_SIZE,
) -> FloorPlanGrid:
    """Analyze a floor plan from a URL (or base64 data URL).

    Args:
        image_url: Public URL or base64 data URL of the floor plan image.
        total_area_sqm: Optional total property area for scale calibration.
        cell_size: Grid resolution in metres per cell. Default 1.0m.

    Returns:
        A FloorPlanGrid ready for furniture optimization.
    """
    from ..tools.llm import call_gemini_with_image

    logger.info("Analyzing floor plan from URL (total_area=%s, cell_size=%s)", total_area_sqm, cell_size)
    return await _call_and_parse(image_url, total_area_sqm, call_gemini_with_image, cell_size)
