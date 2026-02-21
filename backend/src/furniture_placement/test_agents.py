"""Test the furniture spec and constraint agents with synthetic grid data.

Usage:
    cd backend/src
    python -m furniture_placement.test_agents

    # With a real grid from the analyzer (needs grid_data.json from test_analyzer):
    python -m furniture_placement.test_agents --from-grid output/grid_data.json

Requires OPENROUTER_API_KEY in backend/.env.
"""

import argparse
import asyncio
import json
import logging
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
from openai import AsyncOpenAI

from furniture_placement.grid_types import RoomPolygon
from furniture_placement.rasterize import build_grid_from_polygons
from furniture_placement.furniture_agents import (
    FurnitureItemSpec,
    generate_furniture_specs,
    generate_furniture_constraints,
    specs_to_optimizer_format,
    constraints_to_optimizer_format,
    specs_to_search_queries,
    _generate_specs_impl,
    _generate_constraints_impl,
)

logging.basicConfig(level=logging.INFO, format="%(name)s %(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

# Load env
load_dotenv(Path(__file__).parent.parent.parent / ".env")


def _build_synthetic_grid():
    """Build a synthetic 3-room apartment for testing."""
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
        RoomPolygon(
            name="Kitchen",
            vertices_m=[(0, 4), (4, 4), (4, 7), (0, 7)],
            area_sqm=12.0,
        ),
    ]
    return build_grid_from_polygons(rooms, envelope_width_m=9, envelope_height_m=7)


def _load_grid_from_json(path: str):
    """Reconstruct a FloorPlanGrid from grid_data.json."""
    from furniture_placement.grid_types import FloorPlanGrid, DoorInfo, WindowInfo

    with open(path) as f:
        data = json.load(f)

    grid = FloorPlanGrid(
        width=data["width"],
        height=data["height"],
        cell_size=data["cell_size"],
    )
    for room_name, cells in data.get("room_cells", {}).items():
        grid.room_cells[room_name] = {tuple(c) for c in cells}
    grid.passage_cells = {tuple(c) for c in data.get("passage_cells", [])}
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


async def main():
    parser = argparse.ArgumentParser(description="Test furniture agents")
    parser.add_argument("--from-grid", help="Path to grid_data.json from test_analyzer")
    parser.add_argument("--style", default="modern scandinavian", help="Style preference")
    parser.add_argument("--budget-max", type=float, default=5000, help="Max budget in EUR")
    args = parser.parse_args()

    # Build or load grid
    if args.from_grid:
        logger.info("Loading grid from %s", args.from_grid)
        grid = _load_grid_from_json(args.from_grid)
    else:
        logger.info("Building synthetic 3-room grid")
        grid = _build_synthetic_grid()

    logger.info("Grid: %dx%d, %d rooms: %s", grid.width, grid.height, grid.num_rooms, grid.room_names)

    # User preferences
    preferences = {
        "style": args.style,
        "budget_max": args.budget_max,
        "currency": "EUR",
        "colors": ["warm neutrals", "wood tones"],
        "lifestyle": ["work from home", "couple"],
    }

    # Set up OpenRouter client (standalone, no relative imports)
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        logger.error("OPENROUTER_API_KEY not set")
        return

    client = AsyncOpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=api_key,
        timeout=120.0,
    )
    model = "anthropic/claude-sonnet-4.6"

    async def llm_call(system: str, user: str, temperature: float) -> str:
        messages = [{"role": "user", "content": user}]
        if system:
            messages.insert(0, {"role": "system", "content": system})
        resp = await client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature,
            extra_headers={
                "HTTP-Referer": "https://homedesigner.ai",
                "X-Title": "HomeDesigner",
            },
        )
        return resp.choices[0].message.content or ""

    # --- Agent 7: Furniture Specs ---
    logger.info("=" * 60)
    logger.info("AGENT 7: Generating furniture specifications...")
    logger.info("=" * 60)

    specs = await _generate_specs_impl(grid, preferences, llm_call)

    print("\n=== Furniture Specifications ===")
    total_items = 0
    for room_name, items in specs.items():
        print(f"\n{room_name} ({grid.room_area_sqm(room_name):.1f} m²):")
        for item in items:
            footprint = item.length_m * item.width_m
            print(f"  {item.name} ({item.category}): {item.length_m:.2f}×{item.width_m:.2f}m "
                  f"[{footprint:.2f}m²] — {item.priority}")
            if item.search_query:
                print(f"    search: \"{item.search_query}\"")
            total_items += 1
        if items:
            total_footprint = sum(i.length_m * i.width_m for i in items)
            room_area = grid.room_area_sqm(room_name)
            pct = (total_footprint / room_area * 100) if room_area > 0 else 0
            print(f"  → Total footprint: {total_footprint:.1f} m² ({pct:.0f}% of room)")

    print(f"\nTotal: {total_items} furniture items")

    # --- Agent 8: Constraints ---
    logger.info("\n" + "=" * 60)
    logger.info("AGENT 8: Generating placement constraints...")
    logger.info("=" * 60)

    constraints = await _generate_constraints_impl(grid, specs, preferences, llm_call)

    print("\n=== Placement Constraints ===")
    for room_name, c in constraints.items():
        print(f"\n{room_name}:")
        if c.boundary_items:
            print(f"  boundary: {c.boundary_items}")
        if c.distance_constraints:
            print(f"  distance:")
            for d in c.distance_constraints:
                print(f"    [{d[0]}, {d[1]}, {d[2]:.2f}, {d[3]:.2f}]")
        if c.alignment_constraints:
            print(f"  align: {c.alignment_constraints}")
        if c.facing_constraints:
            print(f"  facing: {c.facing_constraints}")

    # --- Conversion to optimizer format ---
    cell_size = grid.cell_size
    opt_furniture = specs_to_optimizer_format(specs, cell_size)
    opt_constraints = constraints_to_optimizer_format(constraints, cell_size)

    print("\n=== Optimizer Format (grid cells) ===")
    for room_name, items in opt_furniture.items():
        if items:
            print(f"\n{room_name}:")
            for item in items:
                print(f"  {item.name}: {item.length}×{item.width} cells")

    # --- Search queries ---
    search_queries = specs_to_search_queries(specs, preferences)
    print(f"\n=== Search Queries ({len(search_queries)} items) ===")
    for sq in search_queries:
        dims = sq["dimensions_cm"]
        print(f"  [{sq['room_name']}] {sq['name']}: \"{sq['search_query']}\" "
              f"({dims['length']}×{dims['width']}×{dims['height']}cm)")

    # Save output
    output_dir = Path(__file__).parent.parent.parent / "output"
    output_dir.mkdir(exist_ok=True)

    output_data = {
        "furniture_specs": {
            room: [
                {
                    "name": i.name,
                    "category": i.category,
                    "length_m": i.length_m,
                    "width_m": i.width_m,
                    "height_m": i.height_m,
                    "search_query": i.search_query,
                    "priority": i.priority,
                }
                for i in items
            ]
            for room, items in specs.items()
        },
        "constraints": {
            room: {
                "boundary": c.boundary_items,
                "distance": [list(d) for d in c.distance_constraints],
                "align": c.alignment_constraints,
                "facing": c.facing_constraints,
            }
            for room, c in constraints.items()
        },
        "search_queries": search_queries,
    }
    out_path = output_dir / "furniture_agents_output.json"
    with open(out_path, "w") as f:
        json.dump(output_data, f, indent=2)
    logger.info("Saved output to %s", out_path)


if __name__ == "__main__":
    asyncio.run(main())
