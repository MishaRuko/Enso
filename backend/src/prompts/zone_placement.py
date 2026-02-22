"""Per-zone placement prompt — place furniture within a specific zone polygon."""

import json

from ..models.schemas import FurnitureItem, FurnitureZone, RoomData


def zone_placement_prompt(
    zone: FurnitureZone,
    room: RoomData,
    zone_furniture: list[FurnitureItem],
    other_zones: list[FurnitureZone],
) -> str:
    furniture_info = []
    for f in zone_furniture:
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

    # Format zone polygon as readable coords
    poly_str = ", ".join(f"({x:.2f}, {z:.2f})" for x, z in zone.polygon)

    # Compute zone bounding box for quick reference
    xs = [p[0] for p in zone.polygon]
    zs = [p[1] for p in zone.polygon]
    zone_x_min, zone_x_max = min(xs), max(xs)
    zone_z_min, zone_z_max = min(zs), max(zs)

    # Build exclusion text from other zones
    exclusion_lines = []
    for oz in other_zones:
        oz_poly = ", ".join(f"({x:.2f}, {z:.2f})" for x, z in oz.polygon)
        exclusion_lines.append(f"- **{oz.name}**: [{oz_poly}]")
    exclusion_text = ""
    if exclusion_lines:
        exclusion_text = (
            "\n\n## Other Zones (EXCLUSION — do NOT place items here)\n"
            + "\n".join(exclusion_lines)
        )

    return f"""\
You are an expert interior designer placing furniture in a specific zone of a room.

## Attached Images (in order)
1. **Original floorplan** — the architectural floor plan
2. **Top-Down 3D View** — overhead parallel projection of the empty room
3. **South-West 3D View** — perspective view from the south-west corner
4. **South-East 3D View** — perspective view from the south-east corner
5. **North-East 3D View** — perspective view from the north-east corner
6. **2D Room Diagram** — labeled top-down floor plan with doors and windows

## Room Context
{room.name}, {room.width_m}m wide (X) x {room.length_m}m long (Z), height {room.height_m}m
Room bounds: ({x_min}, {z_min}) to ({x_max}, {z_max})
Doors: {json.dumps([d.model_dump() for d in room.doors])}
Windows: {json.dumps([w.model_dump() for w in room.windows])}

## YOUR ZONE: {zone.name}
Description: {zone.description}
Polygon boundary (apartment-absolute metres): [{poly_str}]
Zone bounding box: x in [{zone_x_min:.2f}, {zone_x_max:.2f}], z in [{zone_z_min:.2f}, {zone_z_max:.2f}]

CRITICAL: ALL furniture positions MUST be INSIDE this polygon. Do NOT place items outside it.
The polygon vertices define the usable floor area for this zone.{exclusion_text}

## Furniture to Place ({len(zone_furniture)} items)
```json
{json.dumps(furniture_info, indent=2)}
```

## Coordinate System
- X axis: west → east. Z axis: south → north. Y = 0 for floor items.
- All values in METRES (apartment-absolute coordinates).

## Placement Rules
1. ALL positions must be inside the zone polygon above.
2. Keep at least 60cm (0.6m) clearance between furniture items.
3. Do NOT block doors or windows.
4. Wall furniture (wardrobe, shelves, TV stand) should be against the nearest wall.
5. Seating should face focal points (TV, windows).
6. Allow 75cm clearance for chairs to be pulled out.
7. Desks perpendicular to or facing windows for natural light.

## Output
Return ONLY valid JSON (no markdown fences):
{{"placements": [{{"item_id": "...", "name": "...", "position": {{"x": ..., "y": 0, "z": ...}}, "rotation_y_degrees": ..., "reasoning": "..."}}]}}"""
