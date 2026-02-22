"""Spatial validation for furniture placements within a room."""

import logging

from ..models.schemas import (
    FurnitureDimensions,
    FurniturePlacement,
    Position3D,
    RoomData,
)

logger = logging.getLogger(__name__)

# Clearance constants (metres)
DOOR_CLEARANCE_M = 0.9
WINDOW_CLEARANCE_M = 0.3
WALKWAY_MIN_M = 0.6


def _item_bounds(
    p: FurniturePlacement,
    dims: FurnitureDimensions | None,
) -> tuple[float, float, float, float]:
    """Return (x_min, z_min, x_max, z_max) for a placement.

    Uses dimensions (converted from cm to m) if available, otherwise assumes
    a default 0.5m x 0.5m footprint.
    """
    if dims:
        half_w = (dims.width_cm / 100) / 2
        half_d = (dims.depth_cm / 100) / 2
    else:
        half_w = 0.25
        half_d = 0.25

    # rotation_y_degrees: 0/180 keep width on X, 90/270 swap
    rot = p.rotation_y_degrees % 360
    if 45 < rot < 135 or 225 < rot < 315:
        half_w, half_d = half_d, half_w

    return (
        p.position.x - half_w,
        p.position.z - half_d,
        p.position.x + half_w,
        p.position.z + half_d,
    )


def _boxes_overlap(
    a: tuple[float, float, float, float],
    b: tuple[float, float, float, float],
    gap: float = 0.0,
) -> bool:
    """Check if two axis-aligned bounding boxes (with optional gap) overlap."""
    return not (
        a[2] + gap <= b[0]
        or b[2] + gap <= a[0]
        or a[3] + gap <= b[1]
        or b[3] + gap <= a[1]
    )


def validate_placements(
    room: RoomData,
    placements: list[FurniturePlacement],
    furniture_dims: dict[str, FurnitureDimensions | None],
) -> list[str]:
    """Validate a set of placements against the room and each other.

    Args:
        room: The room geometry.
        placements: Proposed furniture placements.
        furniture_dims: Map of item_id -> FurnitureDimensions (may be None).

    Returns:
        A list of human-readable error strings. Empty means valid.
    """
    errors: list[str] = []
    bounds_list: list[tuple[str, tuple[float, float, float, float]]] = []

    # Apartment-absolute room bounds
    x_min = room.x_offset_m
    x_max = room.x_offset_m + room.width_m
    z_min = room.z_offset_m
    z_max = room.z_offset_m + room.length_m

    for p in placements:
        dims = furniture_dims.get(p.item_id)
        bbox = _item_bounds(p, dims)
        bounds_list.append((p.item_id, bbox))

        # --- 1. Room bounds check (apartment-absolute) ---
        if bbox[0] < x_min - 0.01 or bbox[1] < z_min - 0.01:
            errors.append(
                f"{p.name} (id={p.item_id}) extends outside room (before origin)."
            )
        if bbox[2] > x_max + 0.01:
            errors.append(
                f"{p.name} (id={p.item_id}) extends past room width ({x_max}m)."
            )
        if bbox[3] > z_max + 0.01:
            errors.append(
                f"{p.name} (id={p.item_id}) extends past room length ({z_max}m)."
            )

    # --- 2. Overlap / walkway check ---
    for i in range(len(bounds_list)):
        for j in range(i + 1, len(bounds_list)):
            id_a, box_a = bounds_list[i]
            id_b, box_b = bounds_list[j]
            if _boxes_overlap(box_a, box_b):
                name_a = next(p.name for p in placements if p.item_id == id_a)
                name_b = next(p.name for p in placements if p.item_id == id_b)
                errors.append(f"{name_a} and {name_b} overlap.")
            elif _boxes_overlap(box_a, box_b, gap=WALKWAY_MIN_M):
                name_a = next(p.name for p in placements if p.item_id == id_a)
                name_b = next(p.name for p in placements if p.item_id == id_b)
                errors.append(
                    f"{name_a} and {name_b} are too close (< {WALKWAY_MIN_M}m walkway)."
                )

    # --- 3. Door clearance ---
    for door in room.doors:
        door_zone = _door_zone(door, room)
        for item_id, bbox in bounds_list:
            if _boxes_overlap(bbox, door_zone):
                name = next(p.name for p in placements if p.item_id == item_id)
                errors.append(
                    f"{name} blocks a door on the {door.wall} wall."
                )

    # --- 4. Window clearance ---
    for win in room.windows:
        win_zone = _window_zone(win, room)
        for item_id, bbox in bounds_list:
            if _boxes_overlap(bbox, win_zone):
                name = next(p.name for p in placements if p.item_id == item_id)
                errors.append(
                    f"{name} blocks a window on the {win.wall} wall."
                )

    return errors


def _door_zone(
    door, room: RoomData
) -> tuple[float, float, float, float]:
    """Return the rectangular keep-clear zone in front of a door (apartment-absolute)."""
    wall = door.wall.lower()
    x0 = room.x_offset_m
    z0 = room.z_offset_m
    pos = door.position_m
    w = door.width_m

    if wall == "south":
        return (x0 + pos, z0, x0 + pos + w, z0 + DOOR_CLEARANCE_M)
    elif wall == "north":
        return (x0 + pos, z0 + room.length_m - DOOR_CLEARANCE_M, x0 + pos + w, z0 + room.length_m)
    elif wall == "west":
        return (x0, z0 + pos, x0 + DOOR_CLEARANCE_M, z0 + pos + w)
    elif wall == "east":
        return (x0 + room.width_m - DOOR_CLEARANCE_M, z0 + pos, x0 + room.width_m, z0 + pos + w)
    return (0, 0, 0, 0)


def _window_zone(
    window, room: RoomData
) -> tuple[float, float, float, float]:
    """Return the rectangular keep-clear zone in front of a window (apartment-absolute)."""
    wall = window.wall.lower()
    x0 = room.x_offset_m
    z0 = room.z_offset_m
    pos = window.position_m
    w = window.width_m

    if wall == "south":
        return (x0 + pos, z0, x0 + pos + w, z0 + WINDOW_CLEARANCE_M)
    elif wall == "north":
        return (x0 + pos, z0 + room.length_m - WINDOW_CLEARANCE_M, x0 + pos + w, z0 + room.length_m)
    elif wall == "west":
        return (x0, z0 + pos, x0 + WINDOW_CLEARANCE_M, z0 + pos + w)
    elif wall == "east":
        return (x0 + room.width_m - WINDOW_CLEARANCE_M, z0 + pos, x0 + room.width_m, z0 + pos + w)
    return (0, 0, 0, 0)


def auto_fix_placements(
    room: RoomData,
    placements: list[FurniturePlacement],
    dims_map: dict[str, FurnitureDimensions | None],
    max_iters: int = 10,
) -> list[FurniturePlacement]:
    """Programmatically fix overlaps and out-of-bounds placements.

    Iteratively resolves AABB collisions by pushing overlapping pairs apart
    along their shortest separation axis, then clamping to room bounds.
    """
    x_min = room.x_offset_m
    x_max = room.x_offset_m + room.width_m
    z_min = room.z_offset_m
    z_max = room.z_offset_m + room.length_m

    # Work with mutable position copies
    pos = {p.item_id: [p.position.x, p.position.z] for p in placements}

    def _half_extents(item_id: str, rot: float) -> tuple[float, float]:
        dims = dims_map.get(item_id)
        hw = (dims.width_cm / 200) if dims else 0.25
        hd = (dims.depth_cm / 200) if dims else 0.25
        r = rot % 360
        if 45 < r < 135 or 225 < r < 315:
            hw, hd = hd, hw
        return hw, hd

    rots = {p.item_id: p.rotation_y_degrees for p in placements}
    ids = [p.item_id for p in placements]

    for it in range(max_iters):
        moved = False

        # 1. Resolve overlaps — push apart along shortest axis
        for i in range(len(ids)):
            for j in range(i + 1, len(ids)):
                a, b = ids[i], ids[j]
                hw_a, hd_a = _half_extents(a, rots[a])
                hw_b, hd_b = _half_extents(b, rots[b])

                dx = abs(pos[a][0] - pos[b][0])
                dz = abs(pos[a][1] - pos[b][1])
                min_dx = hw_a + hw_b + 0.05
                min_dz = hd_a + hd_b + 0.05

                overlap_x = min_dx - dx
                overlap_z = min_dz - dz

                if overlap_x > 0 and overlap_z > 0:
                    # Push apart along the axis with smaller overlap
                    if overlap_x <= overlap_z:
                        shift = overlap_x / 2 + 0.02
                        if pos[a][0] <= pos[b][0]:
                            pos[a][0] -= shift
                            pos[b][0] += shift
                        else:
                            pos[a][0] += shift
                            pos[b][0] -= shift
                    else:
                        shift = overlap_z / 2 + 0.02
                        if pos[a][1] <= pos[b][1]:
                            pos[a][1] -= shift
                            pos[b][1] += shift
                        else:
                            pos[a][1] += shift
                            pos[b][1] -= shift
                    moved = True

        # 2. Clamp to room bounds
        for pid in ids:
            hw, hd = _half_extents(pid, rots[pid])
            old = pos[pid].copy()
            pos[pid][0] = max(x_min + hw, min(x_max - hw, pos[pid][0]))
            pos[pid][1] = max(z_min + hd, min(z_max - hd, pos[pid][1]))
            if pos[pid] != old:
                moved = True

        if not moved:
            break

    fixed_count = 0
    result = []
    for p in placements:
        new_x, new_z = pos[p.item_id]
        if abs(new_x - p.position.x) > 0.01 or abs(new_z - p.position.z) > 0.01:
            fixed_count += 1
        result.append(FurniturePlacement(
            item_id=p.item_id,
            name=p.name,
            position=Position3D(x=round(new_x, 3), y=p.position.y, z=round(new_z, 3)),
            rotation_y_degrees=p.rotation_y_degrees,
            reasoning=p.reasoning,
        ))

    if fixed_count:
        logger.info("Auto-fixed %d/%d placements (%d iterations)", fixed_count, len(placements), it + 1)
    return result


def per_item_errors(
    room: RoomData,
    placements: list[FurniturePlacement],
    dims_map: dict[str, FurnitureDimensions | None],
) -> dict[str, list[str]]:
    """Return a mapping of item_id → list of error strings for that item.

    Items with no errors are omitted from the result.
    """
    errors: dict[str, list[str]] = {}
    bounds_list = []

    x_min = room.x_offset_m
    x_max = room.x_offset_m + room.width_m
    z_min = room.z_offset_m
    z_max = room.z_offset_m + room.length_m

    for p in placements:
        dims = dims_map.get(p.item_id)
        bbox = _item_bounds(p, dims)
        bounds_list.append((p.item_id, p.name, bbox))

        if bbox[0] < x_min - 0.01 or bbox[1] < z_min - 0.01:
            errors.setdefault(p.item_id, []).append("extends outside room (before origin)")
        if bbox[2] > x_max + 0.01:
            errors.setdefault(p.item_id, []).append(f"extends past room width ({x_max}m)")
        if bbox[3] > z_max + 0.01:
            errors.setdefault(p.item_id, []).append(f"extends past room length ({z_max}m)")

    for i in range(len(bounds_list)):
        for j in range(i + 1, len(bounds_list)):
            id_a, name_a, box_a = bounds_list[i]
            id_b, name_b, box_b = bounds_list[j]
            if _boxes_overlap(box_a, box_b):
                errors.setdefault(id_a, []).append(f"overlaps with {name_b}")
                errors.setdefault(id_b, []).append(f"overlaps with {name_a}")

    for door in room.doors:
        dz = _door_zone(door, room)
        for item_id, name, bbox in bounds_list:
            if _boxes_overlap(bbox, dz):
                errors.setdefault(item_id, []).append(f"blocks door on {door.wall} wall")

    for win in room.windows:
        wz = _window_zone(win, room)
        for item_id, name, bbox in bounds_list:
            if _boxes_overlap(bbox, wz):
                errors.setdefault(item_id, []).append(f"blocks window on {win.wall} wall")

    return errors
