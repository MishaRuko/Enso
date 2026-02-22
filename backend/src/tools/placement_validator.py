"""Spatial validation for furniture placements within a room."""

from ..models.schemas import FurnitureDimensions, FurniturePlacement, RoomData

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
