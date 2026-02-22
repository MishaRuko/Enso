"""Rasterize room polygons onto a grid.

Converts room polygons (in metres) to sets of grid cells using a scanline
point-in-polygon approach.
"""

import numpy as np

from .grid_types import CELL_SIZE, FloorPlanGrid, RoomPolygon


def point_in_polygon(px: float, py: float, vertices: list[tuple[float, float]]) -> bool:
    """Ray-casting algorithm to test if a point is inside a polygon."""
    n = len(vertices)
    inside = False
    j = n - 1
    for i in range(n):
        xi, yi = vertices[i]
        xj, yj = vertices[j]
        if ((yi > py) != (yj > py)) and (px < (xj - xi) * (py - yi) / (yj - yi) + xi):
            inside = not inside
        j = i
    return inside


def rasterize_polygon(
    vertices_m: list[tuple[float, float]],
    grid_width: int,
    grid_height: int,
    cell_size: float = CELL_SIZE,
) -> set[tuple[int, int]]:
    """Convert a polygon (in metres) to a set of grid cells.

    Tests each cell center against the polygon. A cell (i, j) has its center
    at ((j + 0.5) * cell_size, (i + 0.5) * cell_size) in the metre coordinate
    system where x=east and y=south.

    Args:
        vertices_m: Polygon vertices as (x_east, y_south) in metres.
        grid_width: Number of columns (j-axis).
        grid_height: Number of rows (i-axis).
        cell_size: Metres per cell.

    Returns:
        Set of (i, j) grid cells whose centers fall inside the polygon.
    """
    cells = set()
    for i in range(grid_height):
        cy = (i + 0.5) * cell_size  # y = southward
        for j in range(grid_width):
            cx = (j + 0.5) * cell_size  # x = eastward
            if point_in_polygon(cx, cy, vertices_m):
                cells.add((i, j))
    return cells


def build_grid_from_polygons(
    rooms: list[RoomPolygon],
    envelope_width_m: float,
    envelope_height_m: float,
    cell_size: float = CELL_SIZE,
    entrance_ij: tuple[int, int] | None = None,
) -> FloorPlanGrid:
    """Build a FloorPlanGrid from a list of room polygons.

    Args:
        rooms: Room polygons with vertices in metres.
        envelope_width_m: Building width in metres (east-west, j-axis).
        envelope_height_m: Building height in metres (north-south, i-axis).
        cell_size: Grid cell size in metres.
        entrance_ij: Optional entrance cell. If None, auto-detected from doors.

    Returns:
        A fully populated FloorPlanGrid.
    """
    grid_w = int(np.ceil(envelope_width_m / cell_size))
    grid_h = int(np.ceil(envelope_height_m / cell_size))

    grid = FloorPlanGrid(
        width=grid_w,
        height=grid_h,
        cell_size=cell_size,
        room_polygons=rooms,
    )

    # Rasterize each room
    all_room_cells: set[tuple[int, int]] = set()
    for room in rooms:
        cells = rasterize_polygon(room.vertices_m, grid_w, grid_h, cell_size)
        grid.room_cells[room.name] = cells
        all_room_cells |= cells

        # Collect doors and windows
        for d in room.doors:
            grid.doors.append(d)
        for w in room.windows:
            grid.windows.append(w)

    # Everything inside the envelope that isn't a room is passage
    all_cells = {(i, j) for i in range(grid_h) for j in range(grid_w)}
    grid.passage_cells = all_cells - all_room_cells

    # Resolve overlaps: if a cell is claimed by multiple rooms, assign to the one
    # whose polygon center is closest (simple heuristic)
    _resolve_overlaps(grid, rooms)

    # Set entrance
    if entrance_ij:
        grid.entrance = entrance_ij
    else:
        grid.entrance = _find_entrance(grid)

    return grid


def _resolve_overlaps(grid: FloorPlanGrid, rooms: list[RoomPolygon]) -> None:
    """If any cell is in multiple rooms, assign it to the nearest room center."""
    room_names = list(grid.room_cells.keys())
    if len(room_names) < 2:
        return

    # Find cells that appear in more than one room
    from collections import Counter
    cell_counts: Counter[tuple[int, int]] = Counter()
    for cells in grid.room_cells.values():
        for c in cells:
            cell_counts[c] += 1

    overlapping = {c for c, count in cell_counts.items() if count > 1}
    if not overlapping:
        return

    # Compute room centers
    room_centers: dict[str, tuple[float, float]] = {}
    for room in rooms:
        xs = [v[0] for v in room.vertices_m]
        ys = [v[1] for v in room.vertices_m]
        room_centers[room.name] = (sum(xs) / len(xs), sum(ys) / len(ys))

    for cell in overlapping:
        ci = (cell[0] + 0.5) * grid.cell_size
        cj = (cell[1] + 0.5) * grid.cell_size
        best_room = min(
            (name for name in room_names if cell in grid.room_cells[name]),
            key=lambda name: (room_centers[name][0] - cj) ** 2 + (room_centers[name][1] - ci) ** 2,
        )
        for name in room_names:
            if name != best_room:
                grid.room_cells[name].discard(cell)


def _find_entrance(grid: FloorPlanGrid) -> tuple[int, int]:
    """Auto-detect entrance from door positions, or default to a boundary passage cell."""
    # If there are doors, pick the one closest to the building boundary
    if grid.doors:
        for door in grid.doors:
            if door.wall == "south":
                # Bottom edge
                j = int(door.position_along_wall_m / grid.cell_size)
                return (grid.height - 1, min(j, grid.width - 1))
            elif door.wall == "north":
                j = int(door.position_along_wall_m / grid.cell_size)
                return (0, min(j, grid.width - 1))
            elif door.wall == "west":
                i = int(door.position_along_wall_m / grid.cell_size)
                return (min(i, grid.height - 1), 0)
            elif door.wall == "east":
                i = int(door.position_along_wall_m / grid.cell_size)
                return (min(i, grid.height - 1), grid.width - 1)

    # Default: first passage cell on the south edge
    for j in range(grid.width):
        if (grid.height - 1, j) in grid.passage_cells:
            return (grid.height - 1, j)

    # Last resort: (0, 0)
    return (0, 0)
