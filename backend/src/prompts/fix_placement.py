"""Fix prompt for furniture placement — takes verification feedback, outputs corrected placements."""

import json

from ..models.schemas import FurnitureItem, RoomData


def fix_placement_prompt(
    room: RoomData,
    furniture: list[FurnitureItem],
    placements_json: dict,
    verification_json: dict,
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

    # Extract and highlight visual issues
    issues = verification_json.get("visual_issues", [])
    issues_text = ""
    if issues:
        lines = []
        for iss in issues:
            sev = iss.get("severity", "minor").upper()
            desc = iss.get("description", "")
            items = ", ".join(iss.get("affected_items", []))
            fix = iss.get("suggested_fix", "")
            lines.append(f"- **[{sev}]** {desc}\n  Items: {items}\n  Suggested fix: {fix}")
        issues_text = (
            "\n\n## Visual Issues (HIGH PRIORITY)\n"
            "The vision model identified these problems from the rendered views:\n\n"
            + "\n".join(lines)
        )

    # Extract failed questions
    failed = [a for a in verification_json.get("answers", []) if a.get("answer") != "yes"]
    failed_text = ""
    if failed:
        lines = [f"- {a['question']} → {a['answer']} ({a.get('reasoning', '')})" for a in failed]
        failed_text = (
            "\n\n## Failed Validation Questions\n"
            + "\n".join(lines)
        )

    score = verification_json.get("overall_score", 0)
    summary = verification_json.get("summary", "")

    return f"""\
You are an expert interior designer fixing a furniture layout based on visual verification feedback.

## Attached Images (in order)
1. **Top-Down 3D View** — overhead view of room with colored furniture boxes
2. **South-West 3D View** — perspective view from the south-west corner
3. **South-East 3D View** — perspective view from the south-east corner
4. **North-East 3D View** — perspective view from the north-east corner
5. **2D Placement Diagram** — labeled top-down floor plan with furniture names, doors, and windows
Use the 2D diagram to identify which colored box is which furniture item.

## Room — APARTMENT-ABSOLUTE coordinates
{room.name}, {room.width_m}m wide (X) x {room.length_m}m long (Z), height {room.height_m}m
Room spans from ({x_min}, 0, {z_min}) to ({x_max}, {room.height_m}, {z_max}) in apartment coordinates.
X: west→east. Z: south→north. Y=0 floor.

## Furniture
```json
{json.dumps(furniture_info, indent=2)}
```

## Current Placement (score: {score:.2f})
```json
{json.dumps(placements_json, indent=2)}
```

## Verification Summary
{summary}{issues_text}{failed_text}

## Your Task
Fix the placement to address the issues above. Priority:
1. Fix all CRITICAL issues first
2. Then MAJOR issues
3. Then MINOR issues
4. Apply the suggested coordinate fixes where possible

## Rules
- Keep items within room bounds: x in [{x_min}, {x_max}], z in [{z_min}, {z_max}]
- Maintain 60cm walkway clearance between items
- Keep wall furniture against walls (x near {x_min} or {x_max}, z near {z_min} or {z_max})
- You MUST include ALL items — do not drop any
- Only move items that have issues — keep good placements unchanged
- y=0 for all floor items

## Output
Return ONLY valid JSON (no markdown fences):
{{"placements": [{{"item_id": "...", "name": "...", "position": {{"x": ..., "y": 0, "z": ...}}, "rotation_y_degrees": ..., "reasoning": "..."}}]}}"""
