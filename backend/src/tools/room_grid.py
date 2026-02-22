"""ASCII grid generator for Visualization-of-Thought (VoT) prompting."""

import math

from ..models.schemas import RoomData


def generate_room_grid(
    room: RoomData,
    all_rooms: list[RoomData] | None = None,
    cell_size: float = 0.5,
) -> str:
    """Generate an ASCII grid of the room using apartment-absolute coordinates.

    Each cell represents `cell_size` metres. Marks walls, doors, windows,
    and exclusion zones from other rooms that overlap the bounding box.

    Legend: [W]=wall  [D]=door  [~]=window  [X]=other room  [  ]=empty floor
    """
    x_min = room.x_offset_m
    z_min = room.z_offset_m
    x_max = x_min + room.width_m
    z_max = z_min + room.length_m

    cols = math.ceil(room.width_m / cell_size) + 1
    rows = math.ceil(room.length_m / cell_size) + 1

    # Build grid (row 0 = highest z, row -1 = lowest z)
    grid: list[list[str]] = [["  "] * cols for _ in range(rows)]

    # Helper: convert absolute coords to grid indices
    def to_col(x: float) -> int:
        return max(0, min(cols - 1, round((x - x_min) / cell_size)))

    def to_row(z: float) -> int:
        # rows are top-to-bottom, z increases upward
        return max(0, min(rows - 1, rows - 1 - round((z - z_min) / cell_size)))

    # Mark walls on all four edges
    for c in range(cols):
        grid[0][c] = "W "       # north wall (top row)
        grid[rows - 1][c] = "W "  # south wall (bottom row)
    for r in range(rows):
        grid[r][0] = "W "         # west wall (left col)
        grid[r][cols - 1] = "W "  # east wall (right col)

    # Mark doors and windows on their respective walls
    for door in room.doors:
        _mark_opening(grid, door, "D ", x_min, z_min, cell_size, cols, rows, room)
    for win in room.windows:
        _mark_opening(grid, win, "~ ", x_min, z_min, cell_size, cols, rows, room)

    # Mark exclusion zones from other rooms
    if all_rooms:
        for r in all_rooms:
            if r.name == room.name:
                continue
            rx0 = r.x_offset_m
            rz0 = r.z_offset_m
            rx1 = rx0 + r.width_m
            rz1 = rz0 + r.length_m
            # Check overlap with target room
            if rx0 < x_max and rx1 > x_min and rz0 < z_max and rz1 > z_min:
                c0 = to_col(max(rx0, x_min))
                c1 = to_col(min(rx1, x_max))
                r0 = to_row(min(rz1, z_max))
                r1 = to_row(max(rz0, z_min))
                for rr in range(r0, r1 + 1):
                    for cc in range(c0, c1 + 1):
                        if 0 <= rr < rows and 0 <= cc < cols:
                            grid[rr][cc] = "X "

    # Build the output string with coordinate labels
    lines: list[str] = []

    # Header row: X-axis labels (every 1m, i.e. every 2 cells at 0.5m)
    header = "Z\\X  "
    for c in range(cols):
        x_val = x_min + c * cell_size
        if c == 0 or (x_val - x_min) % 1.0 < 0.01:
            header += f"{x_val:<5.1f}"
        else:
            header += "     "
    lines.append(header)

    # Grid rows (top = max z, bottom = min z)
    for r in range(rows):
        z_val = z_max - r * cell_size
        label = f"{z_val:4.1f} "
        row_str = label + " ".join(f"[{grid[r][c]}]" for c in range(cols))
        lines.append(row_str)

    # Footer: axis direction indicator
    lines.append("      X →  (east)")
    lines.append("Legend: [W ]=wall  [D ]=door  [~ ]=window  [X ]=exclusion  [  ]=floor")

    return "\n".join(lines)


def _mark_opening(
    grid: list[list[str]],
    opening,
    symbol: str,
    x_min: float,
    z_min: float,
    cell_size: float,
    cols: int,
    rows: int,
    room: RoomData,
) -> None:
    """Mark a door/window opening on the appropriate wall edge."""
    wall = opening.wall.lower()
    pos = opening.position_m
    width = opening.width_m
    half = width / 2

    if wall == "south":
        row = rows - 1
        for c in range(_col(x_min + pos - half, x_min, cell_size, cols),
                       _col(x_min + pos + half, x_min, cell_size, cols) + 1):
            if 0 <= c < cols:
                grid[row][c] = symbol
    elif wall == "north":
        row = 0
        for c in range(_col(x_min + pos - half, x_min, cell_size, cols),
                       _col(x_min + pos + half, x_min, cell_size, cols) + 1):
            if 0 <= c < cols:
                grid[row][c] = symbol
    elif wall == "west":
        col = 0
        for r in range(_row_from_z(z_min + pos + half, z_min, cell_size, rows),
                       _row_from_z(z_min + pos - half, z_min, cell_size, rows) + 1):
            if 0 <= r < rows:
                grid[r][col] = symbol
    elif wall == "east":
        col = cols - 1
        for r in range(_row_from_z(z_min + pos + half, z_min, cell_size, rows),
                       _row_from_z(z_min + pos - half, z_min, cell_size, rows) + 1):
            if 0 <= r < rows:
                grid[r][col] = symbol


def _col(x: float, x_min: float, cell_size: float, cols: int) -> int:
    return max(0, min(cols - 1, round((x - x_min) / cell_size)))


def _row_from_z(z: float, z_min: float, cell_size: float, rows: int) -> int:
    return max(0, min(rows - 1, rows - 1 - round((z - z_min) / cell_size)))
