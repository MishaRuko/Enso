"""Prompt template for furniture placement in a 3D room."""

import json

from ..models.schemas import FurnitureItem, RoomData


def placement_prompt(
    room: RoomData,
    furniture: list[FurnitureItem],
    all_rooms: list[RoomData] | None = None,
) -> str:
    """Build the prompt for AI-driven furniture placement.

    Use with `call_gemini_with_image(prompt, room_image)` when a room render is
    available, or `call_gemini([{"role": "user", "content": prompt}])` without.
    """
    furniture_list = []
    for f in furniture:
        entry = {
            "item_id": f.id,
            "name": f.name,
            "category": f.category,
        }
        if f.dimensions:
            entry["dimensions_cm"] = {
                "width": f.dimensions.width_cm,
                "depth": f.dimensions.depth_cm,
                "height": f.dimensions.height_cm,
            }
        furniture_list.append(entry)

    room_json = {
        "name": room.name,
        "width_m": room.width_m,
        "length_m": room.length_m,
        "height_m": room.height_m,
        "x_offset_m": room.x_offset_m,
        "z_offset_m": room.z_offset_m,
        "doors": [d.model_dump() for d in room.doors],
        "windows": [w.model_dump() for w in room.windows],
        "shape": room.shape,
    }

    # Absolute bounds for this room within the apartment
    x_min = room.x_offset_m
    x_max = room.x_offset_m + room.width_m
    z_min = room.z_offset_m
    z_max = room.z_offset_m + room.length_m

    # Build exclusion zones from other rooms that overlap the target room's rectangle
    exclusion_text = ""
    if all_rooms:
        exclusions = []
        for r in all_rooms:
            if r.name == room.name:
                continue
            rx0 = r.x_offset_m
            rz0 = r.z_offset_m
            rx1 = rx0 + r.width_m
            rz1 = rz0 + r.length_m
            # Check if this room overlaps the target room's bounding rectangle
            if rx0 < x_max and rx1 > x_min and rz0 < z_max and rz1 > z_min:
                exclusions.append(
                    f"- **{r.name}**: ({rx0:.1f}, {rz0:.1f}) to ({rx1:.1f}, {rz1:.1f})"
                )
        if exclusions:
            exclusion_text = (
                "\n\n## EXCLUSION ZONES — DO NOT place furniture here!\n"
                "These areas are other rooms (walls/bathroom/hallway) inside the bounding "
                "rectangle. They are NOT usable floor space:\n"
                + "\n".join(exclusions)
                + "\n\nKeep ALL furniture at least 0.3m away from these zones."
            )

    return f"""\
You are an expert interior designer and spatial planner. Place the furniture items in the room according to best design practices.

## Room
```json
{json.dumps(room_json, indent=2)}
```

## Furniture to Place
```json
{json.dumps(furniture_list, indent=2)}
```

## Coordinate System — APARTMENT-ABSOLUTE
- Origin (0, 0, 0) is at the **apartment's** south-west corner, at floor level.
- X axis: west → east. Z axis: south → north. Y axis: floor → ceiling (y = 0 for floor items).
- The "{room.name}" room spans from ({x_min}, 0, {z_min}) to ({x_max}, {room.height_m}, {z_max}).
- The room shape is "{room.shape}" so not all of the bounding rectangle is usable.
- All furniture positions MUST be within these bounds and outside exclusion zones.
- All position values are in METRES.{exclusion_text}

## Placement Rules
1. Keep at least 60 cm (0.6 m) walkway clearance between furniture.
2. Do NOT place furniture blocking doors or windows.
3. Face seating toward focal points (TV, fireplace, window views).
4. Group conversational seating within 2.5 m of each other.
5. Keep bedside tables within arm's reach of the bed.
6. Desks should face or be perpendicular to windows for natural light.
7. Allow 75 cm clearance for chairs to be pulled out from tables/desks.
8. Wardrobes and storage against walls, not blocking pathways.

## Output
Return ONLY valid JSON (no markdown fences):
{{
  "placements": [
    {{
      "item_id": "string — matches the furniture item ID",
      "name": "string — furniture name for reference",
      "position": {{ "x": number, "y": number, "z": number }},
      "rotation_y_degrees": number,
      "reasoning": "string — brief explanation of why this position was chosen"
    }}
  ]
}}"""
