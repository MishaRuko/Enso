"""Data types for the grid-based furniture placement system.

Coordinate system:
- Origin (0, 0) is the top-left (Northwest) corner of the building envelope.
- i-axis: rows, increasing southward (down).
- j-axis: columns, increasing eastward (right).
- Each cell is CELL_SIZE × CELL_SIZE metres (default 1m).
- A room is a set of (i, j) cells.
- Furniture is a rectangular block of cells within a room.
"""

from dataclasses import dataclass, field

# Grid resolution in metres per cell
CELL_SIZE = 1


@dataclass
class DoorInfo:
    """A door opening in the floor plan."""
    wall: str  # "north", "south", "east", "west"
    room_name: str  # which room this door belongs to
    position_along_wall_m: float  # distance from the wall's start to the door center
    width_m: float = 1.0


@dataclass
class WindowInfo:
    """A window in the floor plan."""
    wall: str
    room_name: str
    position_along_wall_m: float
    width_m: float = 1.0


@dataclass
class RoomPolygon:
    """A room extracted from the floor plan, defined by a polygon.

    The vertices are in metres, relative to the building envelope's NW corner.
    """
    name: str
    vertices_m: list[tuple[float, float]]  # [(x, y), ...] in metres, x=east, y=south
    area_sqm: float = 0.0
    doors: list[DoorInfo] = field(default_factory=list)
    windows: list[WindowInfo] = field(default_factory=list)
    is_open: bool = False  # open rooms (e.g. living+dining) don't need door access


@dataclass
class FloorPlanGrid:
    """The rasterized grid representation of a floor plan.

    This is the primary data structure consumed by the Gurobi optimizer.
    """
    width: int  # grid columns (j-axis, east-west)
    height: int  # grid rows (i-axis, north-south)
    cell_size: float  # metres per cell

    # room_name -> set of (i, j) cells
    room_cells: dict[str, set[tuple[int, int]]] = field(default_factory=dict)

    # set of (i, j) cells that are corridor/passage
    passage_cells: set[tuple[int, int]] = field(default_factory=set)

    # set of (i, j) cells that are outside the building (outdoor/invalid)
    outdoor_cells: set[tuple[int, int]] = field(default_factory=set)

    # entrance cell (i, j)
    entrance: tuple[int, int] | None = None

    # door and window info preserved for constraint generation
    doors: list[DoorInfo] = field(default_factory=list)
    windows: list[WindowInfo] = field(default_factory=list)

    # original room polygons (for reference/debugging)
    room_polygons: list[RoomPolygon] = field(default_factory=list)

    @property
    def width_m(self) -> float:
        return self.width * self.cell_size

    @property
    def height_m(self) -> float:
        return self.height * self.cell_size

    @property
    def room_names(self) -> list[str]:
        return list(self.room_cells.keys())

    @property
    def num_rooms(self) -> int:
        return len(self.room_cells)

    def room_area_sqm(self, room_name: str) -> float:
        return len(self.room_cells.get(room_name, set())) * self.cell_size ** 2

    def all_valid_cells(self) -> set[tuple[int, int]]:
        """All cells that are inside the building (rooms + passages)."""
        cells = set(self.passage_cells)
        for room_set in self.room_cells.values():
            cells |= room_set
        return cells

    def to_dict(self) -> dict:
        """Serialize to JSON-safe dict for storage."""
        return {
            "width": self.width,
            "height": self.height,
            "cell_size": self.cell_size,
            "room_cells": {
                name: [list(c) for c in sorted(cells)]
                for name, cells in self.room_cells.items()
            },
            "passage_cells": [list(c) for c in sorted(self.passage_cells)],
            "outdoor_cells": [list(c) for c in sorted(self.outdoor_cells)],
            "entrance": list(self.entrance) if self.entrance else None,
            "doors": [
                {
                    "wall": d.wall,
                    "room_name": d.room_name,
                    "position_along_wall_m": d.position_along_wall_m,
                    "width_m": d.width_m,
                }
                for d in self.doors
            ],
            "windows": [
                {
                    "wall": w.wall,
                    "room_name": w.room_name,
                    "position_along_wall_m": w.position_along_wall_m,
                    "width_m": w.width_m,
                }
                for w in self.windows
            ],
        }

    @classmethod
    def from_dict(cls, data: dict) -> "FloorPlanGrid":
        """Deserialize from dict."""
        grid = cls(
            width=data["width"],
            height=data["height"],
            cell_size=data["cell_size"],
        )
        for name, cells in data.get("room_cells", {}).items():
            grid.room_cells[name] = {tuple(c) for c in cells}
        grid.passage_cells = {tuple(c) for c in data.get("passage_cells", [])}
        grid.outdoor_cells = {tuple(c) for c in data.get("outdoor_cells", [])}
        if data.get("entrance"):
            grid.entrance = tuple(data["entrance"])
        for d in data.get("doors", []):
            grid.doors.append(DoorInfo(
                wall=d["wall"],
                room_name=d["room_name"],
                position_along_wall_m=d["position_along_wall_m"],
                width_m=d.get("width_m", 1.0),
            ))
        for w in data.get("windows", []):
            grid.windows.append(WindowInfo(
                wall=w["wall"],
                room_name=w["room_name"],
                position_along_wall_m=w["position_along_wall_m"],
                width_m=w.get("width_m", 1.0),
            ))
        return grid
