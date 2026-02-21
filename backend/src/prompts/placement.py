"""Prompt template for furniture placement in a 3D room."""

import json

from ..models.schemas import FurnitureItem, RoomData


def placement_prompt(room: RoomData, furniture: list[FurnitureItem]) -> str:
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
        "doors": [d.model_dump() for d in room.doors],
        "windows": [w.model_dump() for w in room.windows],
        "shape": room.shape,
    }

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

## Coordinate System
- Origin (0, 0, 0) is at the south-west corner of the room, at floor level.
- X axis: west → east (room width).
- Z axis: south → north (room length).
- Y axis: floor → ceiling (height). Place items on the floor: y = 0.
- All position values are in METRES.

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
