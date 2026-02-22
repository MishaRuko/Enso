"""Gurobi-based furniture placement optimizer with fixed room boundaries.

Adapted from Co-Layout (coopt_model.py). Rooms are fixed from floor plan
analysis; only furniture positions are optimized.

Requires: gurobipy (with a valid license — academic licenses are free).
"""

import logging
from dataclasses import dataclass, field

import numpy as np
from gurobipy import GRB, LinExpr, Model, QuadExpr, quicksum

from .grid_types import FloorPlanGrid

logger = logging.getLogger(__name__)

# Directions (matching Co-Layout convention)
EAST, WEST, SOUTH, NORTH = 0, 1, 2, 3

# Door width in cells (for accessibility constraints)
DOOR_SIZE_CELLS = 1

# Default optimization weights (furniture-only, no room objectives needed)
DEFAULT_WEIGHTS = {
    "balance": 1.0,    # furniture centered in room
    "distance": 0.6,   # inter-furniture distance targets
}

# Default Gurobi parameters
DEFAULT_TIME_LIMIT = 30   # seconds (solutions are near-optimal within 30s)
DEFAULT_MIP_GAP = 0.10    # accept 10% gap (visually indistinguishable)
DEFAULT_THREADS = 4


@dataclass
class FurnitureSpec:
    """A piece of furniture to place."""
    name: str
    length: float  # in grid cells (already divided by cell_size)
    width: float   # in grid cells
    height: float = 0  # not used by optimizer, kept for output


@dataclass
class FurnitureConstraints:
    """Placement constraints for furniture in a room."""
    boundary_items: list[str] = field(default_factory=list)  # must be against wall
    distance_constraints: list[tuple[str, str, float, float]] = field(default_factory=list)
    alignment_constraints: list[list[str]] = field(default_factory=list)
    facing_constraints: list[list[str]] = field(default_factory=list)


@dataclass
class PlacedFurniture:
    """Result of optimization for one furniture piece."""
    room_name: str
    name: str
    grid_i: int        # top-left row
    grid_j: int        # top-left column
    sigma: int         # orientation variable 1
    mu: int            # orientation variable 2
    size_i: int        # rows occupied (depends on orientation)
    size_j: int        # columns occupied
    height: float = 0  # height in metres (passed through from FurnitureSpec)


# ---------------------------------------------------------------------------
# Grid variable wrappers (from Co-Layout grid_model.py)
# ---------------------------------------------------------------------------

class _RoomGridFixed:
    """Room grid that returns fixed 0/1 values (rooms are not optimized)."""

    def __init__(self, room_num: int, valid_coords: list, room_cells_by_idx: dict):
        self._valid = set(valid_coords)
        self._lookup: dict[tuple[int, int, int], int] = {}
        for k in range(room_num):
            cells = room_cells_by_idx.get(k, set())
            for (i, j) in valid_coords:
                self._lookup[(k, i, j)] = 1 if (i, j) in cells else 0

    def __getitem__(self, key):
        if isinstance(key, tuple) and len(key) == 3:
            k, i, j = key
            if k is None or i is None or j is None:
                return 0
            return self._lookup.get((k, i, j), 0)
        raise IndexError("Index must be (k, i, j)")


class _PassageGridFixed:
    """Passage grid that returns fixed 0/1 values."""

    def __init__(self, valid_coords: list, passage_cells: set):
        self._valid = set(valid_coords)
        self._passage = passage_cells

    def __getitem__(self, key):
        if isinstance(key, tuple) and len(key) == 2:
            i, j = key
            if i is None or j is None:
                return 0
            if (i, j) not in self._valid:
                return 0
            return 1 if (i, j) in self._passage else 0
        raise IndexError("Index must be (i, j)")


class _FurnitureGrid:
    """Gurobi variable grid for furniture placement."""

    def __init__(self, model, furniture_indices, valid_coords):
        self._valid = set(valid_coords)
        self.vars = model.addVars(
            furniture_indices, valid_coords, vtype=GRB.BINARY, name="furniture"
        )

    def __getitem__(self, key):
        if isinstance(key, tuple) and len(key) == 4:
            k, l, i, j = key
            if k is None or l is None or i is None or j is None:
                return 0
            if (i, j) not in self._valid:
                return 0
            return self.vars[k, l, i, j]
        raise IndexError("Index must be (k, l, i, j)")


# ---------------------------------------------------------------------------
# Main optimizer
# ---------------------------------------------------------------------------

class FurniturePlacementModel:
    """Optimize furniture placement within fixed room boundaries.

    Args:
        grid: FloorPlanGrid with room cells already assigned.
        furniture: Dict mapping room_name -> list of FurnitureSpec.
        constraints: Dict mapping room_name -> FurnitureConstraints.
        weights: Objective function weights.
        time_limit: Gurobi time limit in seconds.
        mip_gap: Gurobi MIP optimality gap.
        threads: Number of solver threads.
    """

    def __init__(
        self,
        grid: FloorPlanGrid,
        furniture: dict[str, list[FurnitureSpec]],
        constraints: dict[str, FurnitureConstraints],
        weights: dict[str, float] | None = None,
        time_limit: int = DEFAULT_TIME_LIMIT,
        mip_gap: float = DEFAULT_MIP_GAP,
        threads: int = DEFAULT_THREADS,
    ):
        self.grid = grid
        self.weights = weights or DEFAULT_WEIGHTS
        self.width = grid.height   # i-axis (rows, north-south)
        self.length = grid.width   # j-axis (columns, east-west)

        # Room data
        self.room_name_list = grid.room_names
        self.room_num = grid.num_rooms
        room_cells_by_idx = {
            k: grid.room_cells[name]
            for k, name in enumerate(self.room_name_list)
        }

        # Valid coordinates (all cells inside the building)
        self.valid_coordinates = sorted(grid.all_valid_cells())
        self.valid_coordinates_set = set(self.valid_coordinates)
        self.BigM = self.width * self.length

        # Furniture data
        self.furnitures_raw = furniture
        self._prepare_furniture(furniture)

        # Constraints
        self.furniture_constraints = {}
        for room_name in self.room_name_list:
            if room_name in constraints:
                c = constraints[room_name]
                self.furniture_constraints[room_name] = {
                    "boundary_items": c.boundary_items,
                    "distance_constraints": c.distance_constraints,
                    "alignment_constraints": c.alignment_constraints,
                    "facing_constraints": c.facing_constraints,
                }
            else:
                self.furniture_constraints[room_name] = {
                    "boundary_items": [],
                    "distance_constraints": [],
                    "alignment_constraints": [],
                    "facing_constraints": [],
                }

        # Create Gurobi model
        self.model = Model("FurniturePlacement")
        self.model.Params.MIPGap = mip_gap
        self.model.Params.TimeLimit = time_limit
        self.model.setParam("Threads", threads)
        self.model.setParam("OutputFlag", 1)

        # Fixed grids (rooms are constants, not variables)
        self.x = _RoomGridFixed(self.room_num, self.valid_coordinates, room_cells_by_idx)
        self.passage = _PassageGridFixed(self.valid_coordinates, grid.passage_cells)

        # Furniture variables
        self._create_variables()

        # Constraints
        self.objective_function = QuadExpr()
        self._add_constraints()
        self._add_objective()

    def _prepare_furniture(self, furniture: dict[str, list[FurnitureSpec]]):
        """Pre-process furniture data into indexed lists."""
        self.furniture_num_list = []
        self.furniture_name_list = []
        self.furniture_parallel_size = []
        self.furniture_vertical_size = []
        self.furniture_area_list = []
        self.furniture_height_list = []  # metres, passed through to PlacedFurniture

        for room_name in self.room_name_list:
            items = furniture.get(room_name, [])
            self.furniture_num_list.append(len(items))
            names = [f.name for f in items]
            self.furniture_name_list.append(names)

            p_list, v_list, area_list, h_list = [], [], [], []
            for f in items:
                # parallel = width (short side), vertical = length (long side)
                p_list.append(int(f.width))
                v_list.append(int(f.length))
                area_list.append(int(f.length) * int(f.width))
                h_list.append(f.height)
            self.furniture_parallel_size.append(p_list)
            self.furniture_vertical_size.append(v_list)
            self.furniture_area_list.append(area_list)
            self.furniture_height_list.append(h_list)

        self.furniture_indices = [
            (k, l)
            for k in range(self.room_num)
            for l in range(self.furniture_num_list[k])
        ]

    def _create_variables(self):
        """Create Gurobi variables for furniture placement."""
        self.furniture_grid = _FurnitureGrid(
            self.model, self.furniture_indices, self.valid_coordinates
        )
        self.f_rect_min_i = self.model.addVars(
            self.furniture_indices, vtype=GRB.INTEGER,
            lb=0, ub=self.width - 1, name="f_rect_min_i",
        )
        self.f_rect_min_j = self.model.addVars(
            self.furniture_indices, vtype=GRB.INTEGER,
            lb=0, ub=self.length - 1, name="f_rect_min_j",
        )
        self.sigma = self.model.addVars(
            self.furniture_indices, vtype=GRB.BINARY, name="sigma"
        )
        self.mu = self.model.addVars(
            self.furniture_indices, vtype=GRB.BINARY, name="mu"
        )

        # Result arrays
        self.furniture_array = []
        self.furniture_sigma_array = []
        self.furniture_mu_array = []
        self.f_rect_min_i_array = []
        self.f_rect_min_j_array = []
        for k in range(self.room_num):
            n = self.furniture_num_list[k]
            self.furniture_array.append(np.zeros((n, self.width, self.length)))
            self.furniture_sigma_array.append(np.zeros(n))
            self.furniture_mu_array.append(np.zeros(n))
            self.f_rect_min_i_array.append(np.zeros(n))
            self.f_rect_min_j_array.append(np.zeros(n))

    def _add_orientation_case_vars(self, sigma_var, mu_var, prefix):
        """Create 4 binary vars encoding orientation cases."""
        z = self.model.addVars(4, vtype=GRB.BINARY, name=prefix)
        self.model.addConstr(quicksum(z) == 1, name=f"{prefix}_sum")
        # z[0] = sigma * mu (North)
        self.model.addConstr(z[0] <= sigma_var)
        self.model.addConstr(z[0] <= mu_var)
        self.model.addConstr(z[0] >= sigma_var + mu_var - 1)
        # z[1] = sigma * (1 - mu) (South)
        self.model.addConstr(z[1] <= sigma_var)
        self.model.addConstr(z[1] <= 1 - mu_var)
        self.model.addConstr(z[1] >= sigma_var - mu_var)
        # z[2] = (1 - sigma) * mu (West)
        self.model.addConstr(z[2] <= 1 - sigma_var)
        self.model.addConstr(z[2] <= mu_var)
        self.model.addConstr(z[2] >= mu_var - sigma_var)
        # z[3] = (1 - sigma) * (1 - mu) (East)
        self.model.addConstr(z[3] <= 1 - sigma_var)
        self.model.addConstr(z[3] <= 1 - mu_var)
        self.model.addConstr(z[3] >= 1 - sigma_var - mu_var)
        return z

    def _add_constraints(self):
        """Add all furniture constraints."""
        self._add_containment_constraints()
        self._add_door_clearance_constraints()
        self._add_basic_constraints()
        self._add_boundary_constraints()
        self._add_relation_constraints()

    def _add_containment_constraints(self):
        """Each furniture cell must be inside its room."""
        for k in range(self.room_num):
            for (i, j) in self.valid_coordinates:
                room_val = self.x[k, i, j]
                if room_val == 0:
                    # Cell not in this room — no furniture from this room here
                    for l in range(self.furniture_num_list[k]):
                        self.model.addConstr(self.furniture_grid[k, l, i, j] == 0)
                # If room_val == 1, furniture CAN be here (no constraint needed)

    def _add_door_clearance_constraints(self):
        """Keep furniture out of cells near doors so doorways stay accessible."""
        if not self.grid.doors:
            return

        cell = self.grid.cell_size
        blocked: set[tuple[int, int]] = set()

        for door in self.grid.doors:
            wall = door.wall.lower()
            pos_cells = int(door.position_along_wall_m / cell)
            width_cells = max(1, int(round(door.width_m / cell)))
            room_cells = self.grid.room_cells.get(door.room_name, set())

            # For each column (or row) spanned by the door width, find the
            # first DOOR_SIZE_CELLS room cells moving inward from the wall.
            for offset in range(width_cells + 1):
                if wall == "north":
                    j = min(pos_cells + offset, self.grid.width - 1)
                    # Scan southward (increasing i) to find room cells near the north wall
                    count = 0
                    for ci in range(self.grid.height):
                        if (ci, j) in room_cells:
                            blocked.add((ci, j))
                            count += 1
                            if count >= DOOR_SIZE_CELLS:
                                break
                elif wall == "south":
                    j = min(pos_cells + offset, self.grid.width - 1)
                    # Scan northward (decreasing i) to find room cells near the south wall
                    count = 0
                    for ci in range(self.grid.height - 1, -1, -1):
                        if (ci, j) in room_cells:
                            blocked.add((ci, j))
                            count += 1
                            if count >= DOOR_SIZE_CELLS:
                                break
                elif wall == "west":
                    i = min(pos_cells + offset, self.grid.height - 1)
                    # Scan eastward (increasing j)
                    count = 0
                    for cj in range(self.grid.width):
                        if (i, cj) in room_cells:
                            blocked.add((i, cj))
                            count += 1
                            if count >= DOOR_SIZE_CELLS:
                                break
                elif wall == "east":
                    i = min(pos_cells + offset, self.grid.height - 1)
                    # Scan westward (decreasing j)
                    count = 0
                    for cj in range(self.grid.width - 1, -1, -1):
                        if (i, cj) in room_cells:
                            blocked.add((i, cj))
                            count += 1
                            if count >= DOOR_SIZE_CELLS:
                                break

        if blocked:
            logger.info("Door clearance: blocking %d cells near %d doors",
                        len(blocked), len(self.grid.doors))
            for k in range(self.room_num):
                for l in range(self.furniture_num_list[k]):
                    for (i, j) in blocked:
                        if (i, j) in self.valid_coordinates_set:
                            self.model.addConstr(
                                self.furniture_grid[k, l, i, j] == 0,
                                name=f"door_clear_{k}_{l}_{i}_{j}",
                            )

    def _add_basic_constraints(self):
        """Furniture area, shape (rectangle), and orientation constraints."""
        for k in range(self.room_num):
            for l in range(self.furniture_num_list[k]):
                fg = self.furniture_grid
                # Area: total cells = length * width
                self.model.addConstr(
                    quicksum(fg[k, l, i, j] for (i, j) in self.valid_coordinates)
                    == self.furniture_area_list[k][l]
                )

                # Rectangular shape via bounding box
                for (i, j) in self.valid_coordinates:
                    self.model.addConstr(
                        self.f_rect_min_i[k, l] <= i + self.BigM * (1 - fg[k, l, i, j])
                    )
                    self.model.addConstr(
                        self.f_rect_min_i[k, l]
                        + self.furniture_parallel_size[k][l] * self.sigma[k, l]
                        + self.furniture_vertical_size[k][l] * (1 - self.sigma[k, l])
                        - 1 >= i * fg[k, l, i, j]
                    )
                    self.model.addConstr(
                        self.f_rect_min_j[k, l] <= j + self.BigM * (1 - fg[k, l, i, j])
                    )
                    self.model.addConstr(
                        self.f_rect_min_j[k, l]
                        + self.furniture_parallel_size[k][l] * (1 - self.sigma[k, l])
                        + self.furniture_vertical_size[k][l] * self.sigma[k, l]
                        - 1 >= j * fg[k, l, i, j]
                    )

                # No two furniture in same room share a cell
                # (handled implicitly via area + rectangle, but add overlap prevention across rooms)
        # Cross-furniture non-overlap: at most one furniture per cell
        for (i, j) in self.valid_coordinates:
            total = quicksum(
                self.furniture_grid[k, l, i, j]
                for k in range(self.room_num)
                for l in range(self.furniture_num_list[k])
            )
            if isinstance(total, (int, float)):
                continue  # no furniture variables for this cell
            self.model.addConstr(total <= 1)

    def _add_boundary_constraints(self):
        """Furniture items that must be placed against a wall."""
        for room_name in self.room_name_list:
            k = self.room_name_list.index(room_name)
            boundary_items = self.furniture_constraints[room_name]["boundary_items"]
            for item_name in boundary_items:
                if item_name not in self.furniture_name_list[k]:
                    continue
                l = self.furniture_name_list[k].index(item_name)
                fg = self.furniture_grid

                # Require furniture_vertical_size cells that are both furniture AND
                # adjacent to a non-room cell (wall boundary)
                fb = self.model.addVars(
                    self.valid_coordinates, vtype=GRB.BINARY,
                    name=f"fb_{k}_{l}",
                )
                self.model.addConstr(
                    quicksum(fb[i, j] for (i, j) in self.valid_coordinates)
                    == self.furniture_vertical_size[k][l]
                )
                for (i, j) in self.valid_coordinates:
                    # Neighbor not in room = wall. Since self.x returns fixed
                    # constants (0 or 1), pre-compute which neighbors are walls
                    # to avoid QuadExpr (keeps the model linear).
                    wall_n = 1 - self.x[k, i - 1, j]  # 0 or 1
                    wall_s = 1 - self.x[k, i + 1, j]
                    wall_w = 1 - self.x[k, i, j - 1]
                    wall_e = 1 - self.x[k, i, j + 1]

                    # When sigma=1: long side along j, check i-direction walls
                    # When sigma=0: long side along i, check j-direction walls
                    neighbors = LinExpr()
                    neighbors += (wall_n + wall_s) * self.sigma[k, l]
                    neighbors += (wall_w + wall_e) * (1 - self.sigma[k, l])
                    self.model.addConstr(neighbors >= fb[i, j])
                    self.model.addConstr(fb[i, j] <= fg[k, l, i, j])

    def _add_relation_constraints(self):
        """Distance, alignment, and facing constraints between furniture pairs."""
        for room_name in self.room_name_list:
            k = self.room_name_list.index(room_name)
            fc = self.furniture_constraints[room_name]
            fn = self.furniture_name_list[k]

            # Alignment: same sigma (same rotation axis)
            for pair in fc["alignment_constraints"]:
                l1 = fn.index(pair[0]) if pair[0] in fn else None
                l2 = fn.index(pair[1]) if pair[1] in fn else None
                if l1 is not None and l2 is not None:
                    self.model.addConstr(self.sigma[k, l1] == self.sigma[k, l2])

            # Facing: l1 faces toward l2
            for pair in fc["facing_constraints"]:
                l1 = fn.index(pair[0]) if pair[0] in fn else None
                l2 = fn.index(pair[1]) if pair[1] in fn else None
                if l1 is not None and l2 is not None:
                    z = self._add_orientation_case_vars(
                        self.sigma[k, l1], self.mu[k, l1],
                        f"face_{k}_{l1}_{l2}",
                    )
                    M = self.BigM
                    self.model.addConstr(
                        self.f_rect_min_i[k, l1] - 1 >= self.f_rect_min_i[k, l2] - M * (1 - z[0])
                    )
                    self.model.addConstr(
                        self.f_rect_min_i[k, l1] + 1 <= self.f_rect_min_i[k, l2] + M * (1 - z[1])
                    )
                    self.model.addConstr(
                        self.f_rect_min_j[k, l1] - 1 >= self.f_rect_min_j[k, l2] - M * (1 - z[2])
                    )
                    self.model.addConstr(
                        self.f_rect_min_j[k, l1] + 1 <= self.f_rect_min_j[k, l2] + M * (1 - z[3])
                    )

            # Distance: soft penalty for deviations from target distances
            for pair in fc["distance_constraints"]:
                name1, name2, d1, d2 = pair
                l1 = fn.index(name1) if name1 in fn else None
                l2 = fn.index(name2) if name2 in fn else None
                if l1 is None or l2 is None:
                    continue

                de1 = self.model.addVar(vtype=GRB.CONTINUOUS, name=f"de1_{k}_{l1}_{l2}")
                de2 = self.model.addVar(vtype=GRB.CONTINUOUS, name=f"de2_{k}_{l1}_{l2}")
                M = self.BigM

                z = self._add_orientation_case_vars(
                    self.sigma[k, l2], self.mu[k, l2],
                    f"dist_{k}_{l1}_{l2}",
                )

                ps, vs = self.furniture_parallel_size, self.furniture_vertical_size
                sig1 = self.sigma[k, l1]

                # Center-to-center distance linearized across 4 orientation cases
                # (Ported directly from Co-Layout coopt_model.py)
                for case_idx, (axis_l2_i, axis_l2_j, half_l2_i, half_l2_j) in enumerate([
                    # z[0]: sigma2=1, mu2=1 (North)
                    (1, 0, ps[k][l2] / 2, vs[k][l2] / 2),
                    # z[1]: sigma2=1, mu2=0 (South)
                    (1, 0, ps[k][l2] / 2, vs[k][l2] / 2),
                    # z[2]: sigma2=0, mu2=1 (West)
                    (0, 1, vs[k][l2] / 2, ps[k][l2] / 2),
                    # z[3]: sigma2=0, mu2=0 (East)
                    (0, 1, vs[k][l2] / 2, ps[k][l2] / 2),
                ]):
                    half_l1_i = ((1 - sig1) * vs[k][l1] + sig1 * ps[k][l1]) / 2
                    half_l1_j = (sig1 * vs[k][l1] + (1 - sig1) * ps[k][l1]) / 2

                    ci1 = self.f_rect_min_i[k, l1] + half_l1_i
                    cj1 = self.f_rect_min_j[k, l1] + half_l1_j
                    ci2 = self.f_rect_min_i[k, l2] + half_l2_i
                    cj2 = self.f_rect_min_j[k, l2] + half_l2_j

                    self.model.addConstr(de1 >= (ci2 - ci1) - d1 - M * (1 - z[case_idx]))
                    self.model.addConstr(de1 >= (ci1 - ci2) + d1 - M * (1 - z[case_idx]))
                    self.model.addConstr(de2 >= (cj2 - cj1) - d2 - M * (1 - z[case_idx]))
                    self.model.addConstr(de2 >= (cj1 - cj2) + d2 - M * (1 - z[case_idx]))

                self.objective_function += self.weights.get("distance", 0.6) * (de1 + de2)

    def _add_objective(self):
        """Furniture balance: weighted center of furniture close to room center."""
        for k in range(self.room_num):
            if self.furniture_num_list[k] == 0:
                continue

            # Room center (average of room cells)
            room_cells = self.grid.room_cells[self.room_name_list[k]]
            if not room_cells:
                continue
            center_i = sum(c[0] for c in room_cells) / len(room_cells)
            center_j = sum(c[1] for c in room_cells) / len(room_cells)

            # Furniture area-weighted center
            total_area = sum(self.furniture_area_list[k])
            if total_area == 0:
                continue

            furn_ci = LinExpr()
            furn_cj = LinExpr()
            for l in range(self.furniture_num_list[k]):
                area = self.furniture_area_list[k][l]
                ps = self.furniture_parallel_size[k][l]
                vs = self.furniture_vertical_size[k][l]
                half_i = ((1 - self.sigma[k, l]) * vs + self.sigma[k, l] * ps) / 2
                half_j = (self.sigma[k, l] * vs + (1 - self.sigma[k, l]) * ps) / 2
                furn_ci += (self.f_rect_min_i[k, l] + half_i) * area
                furn_cj += (self.f_rect_min_j[k, l] + half_j) * area
            furn_ci /= total_area
            furn_cj /= total_area

            err_i = self.model.addVar(lb=0, vtype=GRB.CONTINUOUS, name=f"bal_i_{k}")
            err_j = self.model.addVar(lb=0, vtype=GRB.CONTINUOUS, name=f"bal_j_{k}")
            self.model.addConstr(err_i >= furn_ci - center_i)
            self.model.addConstr(err_i >= center_i - furn_ci)
            self.model.addConstr(err_j >= furn_cj - center_j)
            self.model.addConstr(err_j >= center_j - furn_cj)
            self.objective_function += self.weights.get("balance", 1.0) * (err_i + err_j)

    def optimize(self) -> list[PlacedFurniture]:
        """Run the optimizer and return placed furniture."""
        logger.info(
            "Starting optimization: %d rooms, %d total furniture items",
            self.room_num, len(self.furniture_indices),
        )

        # Two-stage: first find feasible, then optimize
        self.model.setParam("MIPFocus", 1)
        self.model.setObjective(0)
        self.model.optimize()

        if self.model.status == GRB.OPTIMAL and self.model.SolCount > 0:
            self.model.update()
            self.model.setParam("MIPFocus", 1)
            self.model.setObjective(self.objective_function, GRB.MINIMIZE)
            self.model.optimize()
        elif self.model.status == GRB.INFEASIBLE:
            logger.error("Model is infeasible — computing IIS")
            self.model.computeIIS()
            self.model.write("/tmp/enso_infeasible.ilp")
            return []

        if self.model.SolCount == 0:
            logger.error("No feasible solution found (status=%d)", self.model.status)
            return []

        return self._extract_solution()

    def _extract_solution(self) -> list[PlacedFurniture]:
        """Read solution values and build result list."""
        results = []
        for k in range(self.room_num):
            room_name = self.room_name_list[k]
            for l in range(self.furniture_num_list[k]):
                gi = int(round(self.f_rect_min_i[k, l].X))
                gj = int(round(self.f_rect_min_j[k, l].X))
                sig = int(round(self.sigma[k, l].X))
                mu_val = int(round(self.mu[k, l].X))

                ps = self.furniture_parallel_size[k][l]
                vs = self.furniture_vertical_size[k][l]
                size_i = ps if sig else vs
                size_j = vs if sig else ps

                results.append(PlacedFurniture(
                    room_name=room_name,
                    name=self.furniture_name_list[k][l],
                    grid_i=gi,
                    grid_j=gj,
                    sigma=sig,
                    mu=mu_val,
                    size_i=size_i,
                    size_j=size_j,
                    height=self.furniture_height_list[k][l],
                ))
                logger.info(
                    "  Placed %s in %s at (%d, %d), size=%dx%d, sigma=%d, mu=%d",
                    self.furniture_name_list[k][l], room_name,
                    gi, gj, size_i, size_j, sig, mu_val,
                )

        return results
