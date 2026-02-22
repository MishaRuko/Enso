"""Combined verify+fix prompt — single LLM call evaluates placement and fixes if needed."""

import json

from ..models.schemas import FurnitureItem, RoomData


def verify_and_fix_prompt(
    room: RoomData,
    furniture: list[FurnitureItem],
    placements_json: dict,
) -> str:
    furniture_info = []
    for f in furniture:
        entry = {"item_id": f.id, "name": f.name, "category": f.category}
        if f.dimensions:
            entry["dimensions_cm"] = {
                "width": f.dimensions.width_cm,
                "depth": f.dimensions.depth_cm,
                "height": f.dimensions.height_cm,
            }
            entry["dimensions_m"] = {
                "width": round(f.dimensions.width_cm / 100, 3),
                "depth": round(f.dimensions.depth_cm / 100, 3),
                "height": round(f.dimensions.height_cm / 100, 3),
            }
            entry["footprint_m"] = (
                f"{entry['dimensions_m']['width']}m x {entry['dimensions_m']['depth']}m"
            )
        furniture_info.append(entry)

    x_min = room.x_offset_m
    x_max = room.x_offset_m + room.width_m
    z_min = room.z_offset_m
    z_max = room.z_offset_m + room.length_m

    return f"""\
You are an expert interior designer evaluating AND fixing a furniture layout from rendered 3D views.

## Attached Images (in order)
The images are provided in this exact order:
1. **Top-Down 3D View** — overhead parallel projection of the room with colored furniture boxes
2. **South-West 3D View** — perspective view from the south-west corner (35 deg elevation)
3. **South-East 3D View** — perspective view from the south-east corner (35 deg elevation)
4. **North-East 3D View** — perspective view from the north-east corner (35 deg elevation)
5. **2D Placement Diagram** — labeled top-down floor plan with furniture names, doors, and windows

Use the 2D diagram to identify which colored box is which furniture item.

## Room — APARTMENT-ABSOLUTE coordinates
{room.name}, {room.width_m}m wide (X) x {room.length_m}m long (Z), height {room.height_m}m
Room spans from ({x_min}, 0, {z_min}) to ({x_max}, {room.height_m}, {z_max}) in apartment coordinates.
X: west->east. Z: south->north. Y=0 floor.

## Furniture
```json
{json.dumps(furniture_info, indent=2)}
```

## Current Placement
```json
{json.dumps(placements_json, indent=2)}
```

## STEP 1: Evaluate the layout
Answer each question with yes/no/unclear and a confidence score (0-1):

1. Are all furniture items inside the room boundaries (x in [{x_min}, {x_max}], z in [{z_min}, {z_max}])?
2. Is there at least 60cm walkway clearance between all furniture pairs?
3. Are items that should be against walls (wardrobe, shelves, TV stand) actually against walls?
4. Is seating (sofa, chairs) grouped logically near tables or focal points?
5. Are doors and windows kept unblocked with clearance?
6. Is the overall layout balanced — not all furniture crammed in one area?
7. Do chairs have enough space (75cm) to be pulled out from tables?

Also identify visual issues from the rendered views:
- Furniture overlapping or too close to each other
- Items floating in the middle that should be against walls
- Poor functional grouping (chairs far from tables)
- Wasted space or cramped areas
- Items placed in clearly wrong locations

For each issue, specify description, severity (critical/major/minor), affected_items, and suggested_fix.

Compute overall_score as: (number of "yes" answers) / (total questions), weighted by confidence.

## STEP 2: Fix if needed
- If overall_score < 0.75: produce corrected placements fixing all issues. Priority: CRITICAL > MAJOR > MINOR.
- If overall_score >= 0.75: return the original placements unchanged.

Fix rules:
- Keep items within room bounds: x in [{x_min}, {x_max}], z in [{z_min}, {z_max}]
- Maintain 60cm walkway clearance between items
- Keep wall furniture against walls (x near {x_min} or {x_max}, z near {z_min} or {z_max})
- You MUST include ALL items — do not drop any
- Only move items that have issues — keep good placements unchanged
- y=0 for all floor items

## Output
Return ONLY valid JSON matching this exact schema:
{{
  "evaluation": {{
    "answers": [
      {{"question": "...", "answer": "yes|no|unclear", "confidence": 0.9, "reasoning": "..."}}
    ],
    "visual_issues": [
      {{
        "description": "...",
        "severity": "critical|major|minor",
        "affected_items": ["item name"],
        "suggested_fix": "move item to x=..., z=..."
      }}
    ],
    "overall_score": 0.85,
    "summary": "Brief summary of findings"
  }},
  "placements": [
    {{"item_id": "...", "name": "...", "position": {{"x": ..., "y": 0, "z": ...}}, "rotation_y_degrees": ..., "reasoning": "..."}}
  ]
}}"""
