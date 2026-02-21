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

from .grid_types import FloorPlanGrid
from .optimizer import PlacedFurniture


def grid_to_3d(
    placement: PlacedFurniture,
    grid: FloorPlanGrid,
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

    return {
        "name": placement.name,
        "room_name": placement.room_name,
        "position": {"x": x, "y": y, "z": z},
        "rotation_y_degrees": rotation,
        "size_m": {"width": width_m, "depth": depth_m},
    }


def convert_all_placements(
    placements: list[PlacedFurniture],
    grid: FloorPlanGrid,
) -> list[dict]:
    """Convert all placements to 3D coordinates."""
    return [grid_to_3d(p, grid) for p in placements]
