"""LLM agents for furniture specification and constraint generation.

Agent 7 (FurnitureSpecAgent): Room data + user preferences → furniture list per room
Agent 8 (FurnitureConstraintAgent): Furniture list + room data → placement constraints

Adapted from Co-Layout paper (Agents 7 & 8). Uses Claude via OpenRouter for
reasoning about furniture selection and spatial constraint generation.
"""

import json
import logging
import math
import re
from dataclasses import dataclass, field
from typing import Awaitable, Callable

from .grid_types import FloorPlanGrid
from .optimizer import FurnitureConstraints, FurnitureSpec

logger = logging.getLogger(__name__)

# Type for text LLM callable: (system_prompt, user_prompt, temperature) -> response text
TextLLMCallable = Callable[[str, str, float], Awaitable[str]]


# ---------------------------------------------------------------------------
# Data types
# ---------------------------------------------------------------------------

@dataclass
class FurnitureItemSpec:
    """A furniture item with metric dimensions and search metadata.

    This is the intermediate representation between the LLM agent output
    and the optimizer's FurnitureSpec (which uses grid cells).
    """
    name: str           # unique per room, e.g. "nightstand1", "chair2"
    category: str       # generic category, e.g. "sofa", "bed", "desk"
    length_m: float     # longer dimension in metres
    width_m: float      # shorter dimension in metres
    height_m: float = 0.8
    search_query: str = ""   # IKEA-style search query
    room_name: str = ""
    priority: str = "essential"  # "essential" or "nice_to_have"


# ---------------------------------------------------------------------------
# Room info extraction for prompts
# ---------------------------------------------------------------------------

def _room_info_for_prompt(grid: FloorPlanGrid) -> str:
    """Extract room information from FloorPlanGrid as formatted text for LLM."""
    lines = []
    for room_name in grid.room_names:
        area = grid.room_area_sqm(room_name)
        cells = grid.room_cells[room_name]
        if not cells:
            continue

        # Bounding box in metres
        min_i = min(c[0] for c in cells) * grid.cell_size
        max_i = (max(c[0] for c in cells) + 1) * grid.cell_size
        min_j = min(c[1] for c in cells) * grid.cell_size
        max_j = (max(c[1] for c in cells) + 1) * grid.cell_size
        bbox_w = max_j - min_j
        bbox_h = max_i - min_i

        # Doors and windows for this room
        room_doors = [d for d in grid.doors if d.room_name == room_name]
        room_windows = [w for w in grid.windows if w.room_name == room_name]

        lines.append(f"### {room_name}")
        lines.append(f"- Area: {area:.1f} m²")
        lines.append(f"- Bounding box: {bbox_w:.1f}m (east-west) × {bbox_h:.1f}m (north-south)")
        if room_doors:
            door_strs = [f"{d.wall} wall ({d.width_m:.1f}m wide)" for d in room_doors]
            lines.append(f"- Doors: {', '.join(door_strs)}")
        if room_windows:
            win_strs = [f"{w.wall} wall ({w.width_m:.1f}m wide)" for w in room_windows]
            lines.append(f"- Windows: {', '.join(win_strs)}")
        lines.append("")

    return "\n".join(lines)


def _extract_json(text: str) -> str:
    """Strip markdown fences or prose to isolate JSON."""
    m = re.search(r"```(?:json)?\s*(\{[\s\S]*\})\s*```", text)
    if m:
        return m.group(1)
    m = re.search(r"(\{[\s\S]*\})", text)
    if m:
        return m.group(1)
    return text


# ---------------------------------------------------------------------------
# Agent 7: Furniture Specification
# ---------------------------------------------------------------------------

_FURNITURE_SPEC_SYSTEM = """\
You are a professional interior furniture designer. Your task is to select \
and size furniture for rooms based on the room geometry and client preferences.

You ONLY determine what furniture to place and its dimensions. You do NOT \
decide positions or spatial relationships — that is handled separately."""

_FURNITURE_SPEC_PROMPT = """\
Analyze the rooms below and create a furniture list for each.

## Rooms
{room_info}

## Client Preferences
{preferences_info}

## Rules

1. **Furnish every room with the key pieces** a professional interior \
designer would select. Be selective — pick the most impactful items, not \
every possible piece. Examples:
   - **Living room** (max 6): sofa, coffee table, TV unit, armchair, \
side table, floor lamp
   - **Bedroom** (max 5): bed, wardrobe, bedside table, desk, desk chair
   - **Kitchen** (max 4): dining table, chairs (count each separately), storage cabinet
   - **Hallway/entry** (max 3): console table, shoe rack, coat stand
   - **Study/office** (max 5): desk, office chair, bookshelf, floor lamp
   These are guidelines — adapt to the room's actual size and shape. \
Prioritise essential functional furniture over decorative items.

2. **Total furniture footprint** must be ≤ 70% of the room's floor area.

3. All furniture is approximated as **rectangular**. Report the length (longer \
side) and width (shorter side) in metres.

4. Do NOT include wall-hung shelves, rugs, or small table-top items.

5. **Identical pieces** must have unique numbered names: "chair1", "chair2", etc. \
NOT a single "chairs" entry.

6. **Skip rooms that don't need furniture**: bathrooms, WC, utility rooms, \
laundry rooms. Include them in the output with an empty list.

7. The `search_query` should be a concise retail search string (e.g., \
"3-seat sofa grey fabric scandinavian") including style cues from user preferences.

8. Set `priority` to "essential" for must-have items and "nice_to_have" for \
accent/decorative pieces.

## Output Format

Return ONLY valid JSON (no markdown fences, no commentary):
{{
  "RoomName1": [
    {{
      "name": "sofa",
      "category": "sofa",
      "length_m": 2.2,
      "width_m": 0.9,
      "height_m": 0.8,
      "search_query": "3-seat sofa grey fabric modern",
      "priority": "essential"
    }}
  ],
  "RoomName2": [],
  ...
}}

Include ALL rooms from the input (even if empty)."""


def _format_preferences(preferences: dict | None) -> str:
    """Format user preferences for the prompt."""
    if not preferences:
        return "No specific preferences provided. Use modern, neutral defaults."

    parts = []
    if preferences.get("style"):
        parts.append(f"- Style: {preferences['style']}")
    if preferences.get("budget_min") or preferences.get("budget_max"):
        currency = preferences.get("currency", "EUR")
        parts.append(f"- Budget: {preferences.get('budget_min', 0)}–{preferences.get('budget_max', 10000)} {currency}")
    if preferences.get("colors"):
        colors = preferences["colors"]
        if isinstance(colors, list):
            colors = ", ".join(colors)
        parts.append(f"- Colours: {colors}")
    if preferences.get("lifestyle"):
        lifestyle = preferences["lifestyle"]
        if isinstance(lifestyle, list):
            lifestyle = ", ".join(lifestyle)
        parts.append(f"- Lifestyle: {lifestyle}")
    if preferences.get("must_haves"):
        must = preferences["must_haves"]
        if isinstance(must, list):
            must = ", ".join(must)
        parts.append(f"- Must-haves: {must}")
    if preferences.get("dealbreakers"):
        deal = preferences["dealbreakers"]
        if isinstance(deal, list):
            deal = ", ".join(deal)
        parts.append(f"- Dealbreakers: {deal}")
    if preferences.get("existing_furniture"):
        existing = preferences["existing_furniture"]
        if isinstance(existing, list):
            existing = ", ".join(existing)
        parts.append(f"- Existing furniture to keep: {existing}")

    return "\n".join(parts) if parts else "No specific preferences provided."


_MAX_ITEMS_PER_ROOM: dict[str, int] = {
    "Living Room": 6,
    "Kitchen": 4,
    "Master Bedroom": 5,
    "Bedroom": 5,
    "Hallway": 3,
    "Study": 5,
    "Office": 5,
}
_DEFAULT_MAX_ITEMS = 5


def _cap_items_per_room(
    specs: dict[str, list[FurnitureItemSpec]],
) -> dict[str, list[FurnitureItemSpec]]:
    """Trim items per room to a hard cap. Keeps essentials first, then nice_to_have."""
    for room_name, items in specs.items():
        # Find the matching cap key (prefix match)
        cap = _DEFAULT_MAX_ITEMS
        for key, limit in _MAX_ITEMS_PER_ROOM.items():
            if room_name.startswith(key) or room_name.lower().startswith(key.lower()):
                cap = limit
                break

        if len(items) <= cap:
            continue

        # Sort: essential first, then nice_to_have, preserving original order within each group
        essential = [i for i in items if i.priority == "essential"]
        nice = [i for i in items if i.priority != "essential"]
        ordered = essential + nice

        dropped = ordered[cap:]
        specs[room_name] = ordered[:cap]
        logger.info(
            "Capped %s: %d → %d items (dropped: %s)",
            room_name, len(items), cap,
            ", ".join(d.name for d in dropped),
        )
    return specs


async def _generate_specs_impl(
    grid: FloorPlanGrid,
    preferences: dict | None,
    llm_call: TextLLMCallable,
) -> dict[str, list[FurnitureItemSpec]]:
    """Core implementation: call LLM, parse response."""
    room_info = _room_info_for_prompt(grid)
    pref_info = _format_preferences(preferences)
    prompt = _FURNITURE_SPEC_PROMPT.format(
        room_info=room_info,
        preferences_info=pref_info,
    )

    raw = await llm_call(_FURNITURE_SPEC_SYSTEM, prompt, 0.4)
    logger.info("Furniture spec agent response (%d chars)", len(raw))
    logger.debug("Raw: %s", raw[:2000])

    text = _extract_json(raw)
    data = json.loads(text)

    result: dict[str, list[FurnitureItemSpec]] = {}
    for room_name, items in data.items():
        specs = []
        for item in items:
            length = float(item["length_m"])
            width = float(item["width_m"])
            # Ensure length >= width
            if width > length:
                length, width = width, length
            specs.append(FurnitureItemSpec(
                name=item["name"],
                category=item.get("category", item["name"]),
                length_m=length,
                width_m=width,
                height_m=float(item.get("height_m", 0.8)),
                search_query=item.get("search_query", ""),
                room_name=room_name,
                priority=item.get("priority", "essential"),
            ))
        result[room_name] = specs

    # Enforce per-room item cap
    result = _cap_items_per_room(result)

    # Log summary
    total = sum(len(v) for v in result.values())
    logger.info("Furniture spec: %d items across %d rooms", total, len(result))
    for rn, items in result.items():
        if items:
            names = [f"{i.name} ({i.length_m}×{i.width_m}m)" for i in items]
            logger.info("  %s: %s", rn, ", ".join(names))

    return result


async def generate_furniture_specs(
    grid: FloorPlanGrid,
    preferences: dict | None = None,
) -> dict[str, list[FurnitureItemSpec]]:
    """Generate furniture specifications for each room using Claude.

    Args:
        grid: FloorPlanGrid from floor plan analysis.
        preferences: User preferences dict (style, budget, lifestyle, etc.).

    Returns:
        Dict mapping room_name -> list of FurnitureItemSpec.
    """
    from ..tools.llm import call_claude

    async def _call(system: str, user: str, temperature: float) -> str:
        return await call_claude(
            messages=[{"role": "user", "content": user}],
            system=system,
            temperature=temperature,
        )

    return await _generate_specs_impl(grid, preferences, _call)


# ---------------------------------------------------------------------------
# Agent 8: Furniture Constraint Generation
# ---------------------------------------------------------------------------

_CONSTRAINT_SYSTEM = """\
You are an expert interior designer planning furniture placement. Your task is \
to determine spatial constraints for furniture that has already been selected. \
You do NOT select furniture — only define how pieces relate to each other spatially."""

_CONSTRAINT_PROMPT = """\
Given the rooms and their furniture below, define placement constraints.

## Rooms
{room_info}

## Furniture per Room
{furniture_info}

## Constraint Types

### 1. boundary
List furniture that **must be placed against a wall**: beds, sofas, wardrobes, \
TV stands, bookshelves, desks (usually), dressers.

### 2. distance
Center-to-center distance targets between furniture pairs.
Format: `[name1, name2, d_along, d_perpendicular]`
- `d_along`: distance in name1's **facing direction** (positive = in front, negative = behind)
- `d_perpendicular`: distance **perpendicular** to name1's facing (positive = right, negative = left)
- **Critical**: these are center-to-center distances, so you MUST account for the furniture dimensions.

**Example — nightstands beside a bed (bed: 2.0×1.5m, nightstand: 0.5×0.5m):**
- Nightstand center is beside the bed center, offset perpendicular
- d_perpendicular = bed_width/2 + nightstand_width/2 + gap = 1.5/2 + 0.5/2 + 0 = 1.0
- d_along = -(bed_length/2 - nightstand_length/2) = -(2.0/2 - 0.5/2) = -0.75 (behind bed center)
- Result: `["nightstand1", "bed", -0.75, 1.0]` (right side)
- Result: `["nightstand2", "bed", -0.75, -1.0]` (left side)

**Example — coffee table in front of sofa (sofa: 2.2×0.9m, table: 1.2×0.6m):**
- d_along = sofa_width/2 + table_width/2 + gap = 0.9/2 + 0.6/2 + 0.4 = 1.15
- d_perpendicular = 0 (centered)
- Result: `["coffee_table", "sofa", 1.15, 0]`

### 3. align
Pairs that should share the same **orientation axis**: `[name1, name2]`
Use for: bed + nightstands, dining table + chairs on same side.

### 4. facing
name1 should **face toward** name2: `[name1, name2]`
Use for: sofa → TV, chair → desk, dining chairs → table.

## Guidelines
- Be comprehensive enough to achieve a good layout, but avoid contradictory constraints.
- Every room with furniture should have at least boundary constraints.
- Use distance constraints for tightly coupled pairs (nightstands+bed, coffee table+sofa).
- Use facing for functional relationships (seating→focal point).
- Distance values are in **metres**.

## Output Format

Return ONLY valid JSON (no markdown fences, no commentary):
{{
  "RoomName1": {{
    "boundary": ["item1", "item2"],
    "distance": [["item1", "item2", 1.0, 0.5]],
    "align": [["item1", "item2"]],
    "facing": [["item1", "item2"]]
  }},
  ...
}}

Include ALL rooms that have furniture."""


def _furniture_info_for_prompt(
    furniture: dict[str, list[FurnitureItemSpec]],
) -> str:
    """Format furniture specs as text for the constraint prompt."""
    lines = []
    for room_name, items in furniture.items():
        if not items:
            continue
        lines.append(f"### {room_name}")
        for item in items:
            lines.append(
                f"- **{item.name}** ({item.category}): "
                f"{item.length_m:.2f}m × {item.width_m:.2f}m × {item.height_m:.2f}m"
            )
        lines.append("")
    return "\n".join(lines)


async def _generate_constraints_impl(
    grid: FloorPlanGrid,
    furniture: dict[str, list[FurnitureItemSpec]],
    preferences: dict | None,
    llm_call: TextLLMCallable,
) -> dict[str, FurnitureConstraints]:
    """Core implementation: call LLM, parse constraints."""
    room_info = _room_info_for_prompt(grid)
    furn_info = _furniture_info_for_prompt(furniture)
    prompt = _CONSTRAINT_PROMPT.format(
        room_info=room_info,
        furniture_info=furn_info,
    )

    raw = await llm_call(_CONSTRAINT_SYSTEM, prompt, 0.3)
    logger.info("Constraint agent response (%d chars)", len(raw))
    logger.debug("Raw: %s", raw[:2000])

    text = _extract_json(raw)
    data = json.loads(text)

    result: dict[str, FurnitureConstraints] = {}
    for room_name, constraints in data.items():
        # Validate that referenced items exist
        room_items = {i.name for i in furniture.get(room_name, [])}

        boundary = [b for b in constraints.get("boundary", []) if b in room_items]
        distance = [
            (d[0], d[1], float(d[2]), float(d[3]))
            for d in constraints.get("distance", [])
            if d[0] in room_items and d[1] in room_items
        ]
        align = [
            a for a in constraints.get("align", [])
            if a[0] in room_items and a[1] in room_items
        ]
        facing = [
            f for f in constraints.get("facing", [])
            if f[0] in room_items and f[1] in room_items
        ]

        result[room_name] = FurnitureConstraints(
            boundary_items=boundary,
            distance_constraints=distance,
            alignment_constraints=align,
            facing_constraints=facing,
        )

    # Log summary
    for rn, c in result.items():
        logger.info(
            "  %s: %d boundary, %d distance, %d align, %d facing",
            rn, len(c.boundary_items), len(c.distance_constraints),
            len(c.alignment_constraints), len(c.facing_constraints),
        )

    return result


async def generate_furniture_constraints(
    grid: FloorPlanGrid,
    furniture: dict[str, list[FurnitureItemSpec]],
    preferences: dict | None = None,
) -> dict[str, FurnitureConstraints]:
    """Generate placement constraints for furniture using Claude.

    Args:
        grid: FloorPlanGrid from floor plan analysis.
        furniture: Dict from generate_furniture_specs().
        preferences: Optional user preferences for context.

    Returns:
        Dict mapping room_name -> FurnitureConstraints.
    """
    from ..tools.llm import call_claude

    async def _call(system: str, user: str, temperature: float) -> str:
        return await call_claude(
            messages=[{"role": "user", "content": user}],
            system=system,
            temperature=temperature,
        )

    return await _generate_constraints_impl(grid, furniture, preferences, _call)


# ---------------------------------------------------------------------------
# Conversion utilities
# ---------------------------------------------------------------------------

def specs_to_optimizer_format(
    specs: dict[str, list[FurnitureItemSpec]],
    cell_size: float = 1.0,
) -> dict[str, list[FurnitureSpec]]:
    """Convert metric FurnitureItemSpec to grid-cell FurnitureSpec for optimizer.

    Dimensions are divided by cell_size and rounded UP (ceil) so the grid
    allocation always covers the full furniture dimensions.
    """
    result: dict[str, list[FurnitureSpec]] = {}
    for room_name, items in specs.items():
        opt_specs = []
        for item in items:
            length_cells = max(1, math.ceil(item.length_m / cell_size))
            width_cells = max(1, math.ceil(item.width_m / cell_size))
            # Ensure length >= width in grid cells too
            if width_cells > length_cells:
                length_cells, width_cells = width_cells, length_cells
            opt_specs.append(FurnitureSpec(
                name=item.name,
                length=length_cells,
                width=width_cells,
                height=item.height_m,
            ))
        result[room_name] = opt_specs
    return result


def constraints_to_optimizer_format(
    constraints: dict[str, FurnitureConstraints],
    cell_size: float = 1.0,
) -> dict[str, FurnitureConstraints]:
    """Scale distance constraints from metres to grid cells."""
    result: dict[str, FurnitureConstraints] = {}
    for room_name, c in constraints.items():
        scaled_distances = [
            (name1, name2, d1 / cell_size, d2 / cell_size)
            for name1, name2, d1, d2 in c.distance_constraints
        ]
        result[room_name] = FurnitureConstraints(
            boundary_items=c.boundary_items,
            distance_constraints=scaled_distances,
            alignment_constraints=c.alignment_constraints,
            facing_constraints=c.facing_constraints,
        )
    return result


def specs_to_search_queries(
    specs: dict[str, list[FurnitureItemSpec]],
    preferences: dict | None = None,
) -> list[dict]:
    """Convert furniture specs to search queries for the IKEA pipeline.

    Returns a list of dicts compatible with Charlene's search interface:
    {category, description, dimensions_cm, quantity, room_name, search_query, priority}
    """
    queries = []
    for room_name, items in specs.items():
        for item in items:
            queries.append({
                "category": item.category,
                "name": item.name,
                "search_query": item.search_query,
                "dimensions_cm": {
                    "length": round(item.length_m * 100),
                    "width": round(item.width_m * 100),
                    "height": round(item.height_m * 100),
                },
                "room_name": room_name,
                "priority": item.priority,
            })
    return queries


def update_specs_from_search_results(
    specs: dict[str, list[FurnitureItemSpec]],
    search_results: list[dict],
) -> dict[str, list[FurnitureItemSpec]]:
    """Update furniture specs with actual dimensions from IKEA search results.

    If a search result provides actual product dimensions, update the spec
    to use those instead of the LLM's estimate. This gives the optimizer
    accurate dimensions for placement.

    Args:
        specs: Original specs from generate_furniture_specs().
        search_results: List of dicts with at least {name, room_name, dimensions_cm}.

    Returns:
        Updated specs dict (modified in place and returned).
    """
    # Index search results by (room_name, item_name)
    lookup = {}
    for sr in search_results:
        key = (sr.get("room_name", ""), sr.get("name", ""))
        if key[0] and key[1]:
            lookup[key] = sr

    for room_name, items in specs.items():
        for item in items:
            sr = lookup.get((room_name, item.name))
            if not sr:
                continue
            dims = sr.get("dimensions_cm") or sr.get("actual_dimensions")
            if not dims:
                continue

            # Convert cm to metres
            new_length = dims.get("length", dims.get("depth", 0)) / 100
            new_width = dims.get("width", 0) / 100
            new_height = dims.get("height", 0) / 100

            if new_length > 0 and new_width > 0:
                if new_width > new_length:
                    new_length, new_width = new_width, new_length
                logger.info(
                    "Updated %s/%s: %.2f×%.2f → %.2f×%.2f m (from search)",
                    room_name, item.name,
                    item.length_m, item.width_m,
                    new_length, new_width,
                )
                item.length_m = new_length
                item.width_m = new_width
                if new_height > 0:
                    item.height_m = new_height

    return specs
