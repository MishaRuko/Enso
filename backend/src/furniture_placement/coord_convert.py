"""Convert grid-based placement results to 3D coordinates for the frontend.

Grid system (optimizer):
- Origin (0, 0) = Northwest corner
- i-axis = rows, southward (down)
- j-axis = columns, eastward (right)
- Units: grid cells

Frontend 3D system (React Three Fiber):
- Origin (0, 0, 0) = Southwest corner, floor level
- X axis = east (room width)
- Z axis = north (room length)
- Y axis = up (height)
- Units: metres
"""

import logging

from .grid_types import FloorPlanGrid
from .optimizer import PlacedFurniture

logger = logging.getLogger(__name__)

# Default wall margin in metres. Furniture centers are pushed inward by this
# amount when they fall within margin distance of a room boundary. This
# prevents clipping with wall meshes whose thickness extends inward.
DEFAULT_WALL_MARGIN_M = 0.25


def _clamp_to_room_interior(
    x: float,
    z: float,
    half_w: float,
    half_d: float,
    room_cells: set[tuple[int, int]],
    grid: FloorPlanGrid,
    margin: float,
) -> tuple[float, float]:
    """Push furniture center inward so its edges don't overlap wall meshes.

    Computes the room bounding box in 3D from the room cells, then ensures
    the furniture footprint (center ± half-size) stays `margin` metres inside.
    """
    if not room_cells or margin <= 0:
        return x, z

    cell = grid.cell_size
    grid_h = grid.height

    # Room bounding box in 3D coords
    min_j = min(c[1] for c in room_cells)
    max_j = max(c[1] for c in room_cells)
    min_i = min(c[0] for c in room_cells)
    max_i = max(c[0] for c in room_cells)

    room_x_min = min_j * cell
    room_x_max = (max_j + 1) * cell
    room_z_min = (grid_h * cell) - (max_i + 1) * cell
    room_z_max = (grid_h * cell) - min_i * cell

    # Clamp: furniture edge + margin must be inside room bounds
    x_lo = room_x_min + half_w + margin
    x_hi = room_x_max - half_w - margin
    z_lo = room_z_min + half_d + margin
    z_hi = room_z_max - half_d - margin

    # Only clamp if the room is wide enough; otherwise center the furniture
    if x_lo > x_hi:
        x = (room_x_min + room_x_max) / 2
    else:
        x = max(x_lo, min(x, x_hi))

    if z_lo > z_hi:
        z = (room_z_min + room_z_max) / 2
    else:
        z = max(z_lo, min(z, z_hi))

    return x, z


def grid_to_3d(
    placement: PlacedFurniture,
    grid: FloorPlanGrid,
    wall_margin: float = DEFAULT_WALL_MARGIN_M,
) -> dict:
    """Convert a single grid placement to 3D coordinates.

    Returns a dict matching the frontend's PlacementResult format:
    {
        "name": str,
        "room_name": str,
        "position": {"x": float, "y": float, "z": float},
        "rotation_y_degrees": float,
        "size_m": {"width": float, "depth": float, "height": float},
    }
    """
    cell = grid.cell_size
    grid_h = grid.height  # total rows (north-south extent)

    # Grid center of the furniture piece (in grid coords)
    center_i = placement.grid_i + placement.size_i / 2
    center_j = placement.grid_j + placement.size_j / 2

    # Convert to metres
    center_i_m = center_i * cell
    center_j_m = center_j * cell

    # Grid → 3D coordinate transform:
    # j (east) → X (east):  x = center_j_m
    # i (south) → Z (north): z = (grid_h * cell) - center_i_m  (flip north/south)
    x = center_j_m
    z = (grid_h * cell) - center_i_m
    y = 0.0  # floor level

    # Orientation: (sigma, mu) → rotation_y_degrees
    # (0, 0) = East  → 90°
    # (0, 1) = West  → 270°
    # (1, 0) = South → 180°
    # (1, 1) = North → 0°
    orientation_map = {
        (0, 0): 90.0,   # East
        (0, 1): 270.0,  # West
        (1, 0): 180.0,  # South
        (1, 1): 0.0,    # North
    }
    rotation = orientation_map.get((placement.sigma, placement.mu), 0.0)

    # Size in metres (j-axis = width, i-axis = depth in 3D)
    width_m = placement.size_j * cell
    depth_m = placement.size_i * cell
    height_m = placement.height if hasattr(placement, "height") else 0.0

    # Push furniture inward from walls to prevent clipping
    half_w = width_m / 2
    half_d = depth_m / 2
    room_cells = grid.room_cells.get(placement.room_name, set())
    x, z = _clamp_to_room_interior(x, z, half_w, half_d, room_cells, grid, wall_margin)

    return {
        "name": placement.name,
        "room_name": placement.room_name,
        "position": {"x": x, "y": y, "z": z},
        "rotation_y_degrees": rotation,
        "size_m": {"width": width_m, "depth": depth_m, "height": height_m},
    }


def convert_all_placements(
    placements: list[PlacedFurniture],
    grid: FloorPlanGrid,
    wall_margin: float = DEFAULT_WALL_MARGIN_M,
) -> list[dict]:
    """Convert all placements to 3D coordinates."""
    return [grid_to_3d(p, grid, wall_margin) for p in placements]
