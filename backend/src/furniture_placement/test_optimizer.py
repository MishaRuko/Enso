"""Test the furniture placement optimizer with synthetic data.

Usage:
    cd backend/src
    python -m furniture_placement.test_optimizer

Requires gurobipy with a valid license.
"""

import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from furniture_placement.grid_types import RoomPolygon
from furniture_placement.rasterize import build_grid_from_polygons
from furniture_placement.optimizer import (
    FurnitureConstraints,
    FurniturePlacementModel,
    FurnitureSpec,
)
from furniture_placement.coord_convert import convert_all_placements
from furniture_placement.visualize import print_grid_ascii

logging.basicConfig(level=logging.INFO, format="%(name)s %(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


def main():
    # Build a simple 2-room apartment
    rooms = [
        RoomPolygon(
            name="Living Room",
            vertices_m=[(0, 0), (5, 0), (5, 4), (0, 4)],
            area_sqm=20.0,
        ),
        RoomPolygon(
            name="Bedroom",
            vertices_m=[(5, 0), (9, 0), (9, 4), (5, 4)],
            area_sqm=16.0,
        ),
    ]
    grid = build_grid_from_polygons(rooms, envelope_width_m=9, envelope_height_m=4)

    print("Room grid:")
    print(print_grid_ascii(grid))
    print()

    # Furniture specs (dimensions in grid cells — 1 cell = 1m)
    furniture = {
        "Living Room": [
            FurnitureSpec(name="sofa", length=2, width=1),
            FurnitureSpec(name="coffee_table", length=1, width=1),
            FurnitureSpec(name="tv_stand", length=2, width=1),
        ],
        "Bedroom": [
            FurnitureSpec(name="bed", length=2, width=2),
            FurnitureSpec(name="nightstand", length=1, width=1),
            FurnitureSpec(name="wardrobe", length=2, width=1),
        ],
    }

    constraints = {
        "Living Room": FurnitureConstraints(
            boundary_items=["sofa", "tv_stand"],
            facing_constraints=[["sofa", "tv_stand"]],
        ),
        "Bedroom": FurnitureConstraints(
            boundary_items=["bed", "wardrobe"],
        ),
    }

    # Run optimizer
    logger.info("Creating model...")
    model = FurniturePlacementModel(
        grid=grid,
        furniture=furniture,
        constraints=constraints,
        time_limit=60,
    )

    logger.info("Optimizing...")
    placements = model.optimize()

    if not placements:
        logger.error("No solution found!")
        return

    print(f"\nPlaced {len(placements)} items:")
    for p in placements:
        print(f"  {p.name} in {p.room_name}: grid({p.grid_i}, {p.grid_j}), size={p.size_i}x{p.size_j}")

    # Convert to 3D
    coords_3d = convert_all_placements(placements, grid)
    print("\n3D coordinates:")
    for c in coords_3d:
        pos = c["position"]
        print(f"  {c['name']}: x={pos['x']:.1f}, z={pos['z']:.1f}, rot={c['rotation_y_degrees']:.0f}°")


if __name__ == "__main__":
    main()
