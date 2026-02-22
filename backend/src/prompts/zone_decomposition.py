"""Zone decomposition prompt — divide room into functional zones with polygon boundaries."""

import json

from ..models.schemas import FurnitureItem, RoomData


def zone_decomposition_prompt(
    room: RoomData,
    furniture: list[FurnitureItem],
    all_rooms: list[RoomData] | None = None,
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

    # Build other-rooms info so Gemini knows what areas are NOT usable floor
    other_rooms_text = ""
    if all_rooms:
        others = []
        for r in all_rooms:
            if r.name == room.name:
                continue
            rx0 = r.x_offset_m
            rz0 = r.z_offset_m
            rx1 = rx0 + r.width_m
            rz1 = rz0 + r.length_m
            others.append(
                f"- **{r.name}**: ({rx0:.2f}, {rz0:.2f}) to ({rx1:.2f}, {rz1:.2f})"
            )
        if others:
            other_rooms_text = (
                "\n\n## Other Rooms (NOT usable floor space)\n"
                "These areas within the bounding rectangle are occupied by walls, "
                "bathroom, hallway, etc. Your zone polygons must NOT overlap these:\n"
                + "\n".join(others)
            )

    return f"""\
You are an expert interior designer and spatial planner. Your task is to divide a room into
functional zones and assign furniture to each zone.

## Attached Images (in order)
1. **Original floorplan** — the architectural floor plan
2. **Top-Down 3D View** — overhead parallel projection of the empty room
3. **South-West 3D View** — perspective view from the south-west corner
4. **South-East 3D View** — perspective view from the south-east corner
5. **North-East 3D View** — perspective view from the north-east corner
6. **2D Room Diagram** — labeled top-down floor plan with doors and windows

IMPORTANT: Use the images to identify the ACTUAL usable floor area. The room shape is
"{room.shape}" — the bounding box is larger than the real floor space. Look at the walls
in the 3D renders and floorplan to determine where furniture can actually go.

## Room — APARTMENT-ABSOLUTE coordinates
{room.name}, {room.width_m}m wide (X) x {room.length_m}m long (Z), height {room.height_m}m
Bounding box: ({x_min}, {z_min}) to ({x_max}, {z_max})
Shape: {room.shape}
X axis: west → east. Z axis: south → north.
Doors: {json.dumps([d.model_dump() for d in room.doors])}
Windows: {json.dumps([w.model_dump() for w in room.windows])}{other_rooms_text}

## Furniture to Assign
```json
{json.dumps(furniture_info, indent=2)}
```

## Instructions
1. Study the images to identify the PHYSICAL floor boundary (not the bounding box).
2. Divide the usable floor into 2-5 functional zones based on furniture categories:
   - sleeping_area: bed, nightstands
   - living_area: sofa, coffee table, TV stand, armchair
   - dining_area: dining table, chairs
   - work_area: desk, office chair, shelves
   - storage_area: wardrobe, bookshelf, dresser
3. Each zone gets a polygon of [x, z] vertices (apartment-absolute metres) that defines
   its usable floor area. The polygon must be INSIDE the physical walls.
4. Assign each furniture item to exactly ONE zone by its item_id.
5. Maximum 5 items per zone. If a category has more, split into sub-zones.
6. Leave 60cm gaps between zone polygons for walkways.
7. Ensure zone polygons do NOT overlap each other or other rooms.

## Output
Return ONLY valid JSON (no markdown fences):
{{
  "zones": [
    {{
      "name": "living_area",
      "polygon": [[x1, z1], [x2, z2], [x3, z3], [x4, z4]],
      "furniture_ids": ["id1", "id2", "id3"],
      "description": "South-west corner near window, sofa facing TV"
    }}
  ]
}}"""
