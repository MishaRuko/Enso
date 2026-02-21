"""Test the floor plan analyzer against the example floor plan.

Usage:
    cd backend/src
    python -m furniture_placement.test_analyzer [--total-area 75.3] [--cell-size 0.5]
"""

import argparse
import asyncio
import json
import logging
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from openai import AsyncOpenAI

# Ensure backend/src is on the path
sys.path.insert(0, str(Path(__file__).parent.parent))

from furniture_placement.floorplan_analyzer import (
    _build_prompt,
    _call_and_parse,
    _image_to_base64_url,
    parse_llm_response,
)
from furniture_placement.rasterize import build_grid_from_polygons
from furniture_placement.visualize import print_grid_ascii, save_grid_image

logging.basicConfig(level=logging.INFO, format="%(name)s %(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

# Load env from backend/.env
load_dotenv(Path(__file__).parent.parent.parent / ".env")

EXAMPLE_FLOORPLAN = str(
    Path(__file__).parent.parent.parent / "example_model" / "floorplan.jpg"
)

EXAMPLE_EXPECTED_AREAS = {
    "Kitchen Store": 2.5,
    "Kitchen Verandah": 4.4,
    "Kitchen": 11.5,
    "Bathroom": 3.6,
    "Bedroom #2": 12.2,
    "Passage": 1.6,
    "Living Room": 20.5,
    "Bedroom #1": 11.4,
    "Entry Verandah": 7.6,
}

# Set up OpenRouter client for the test
_client = AsyncOpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.getenv("OPENROUTER_API_KEY", ""),
    timeout=120.0,
)
GEMINI_MODEL = "google/gemini-3.1-pro-preview"


async def _call_gemini_with_image(prompt: str, image_url: str, temperature: float) -> str:
    """Call Gemini via OpenRouter with an image."""
    messages = [
        {
            "role": "user",
            "content": [
                {"type": "text", "text": prompt},
                {"type": "image_url", "image_url": {"url": image_url}},
            ],
        }
    ]
    resp = await _client.chat.completions.create(
        model=GEMINI_MODEL,
        messages=messages,
        temperature=temperature,
        extra_headers={"HTTP-Referer": "https://homedesigner.ai", "X-Title": "HomeDesigner"},
    )
    return resp.choices[0].message.content or ""


def _print_results(grid):
    """Print summary and validation."""
    ascii_art = print_grid_ascii(grid)
    print("\n" + ascii_art + "\n")

    output_dir = Path(__file__).parent.parent.parent / "output"
    output_dir.mkdir(exist_ok=True)
    png_path = str(output_dir / "grid_visualization.png")
    try:
        save_grid_image(grid, png_path)
        logger.info("Saved grid visualization to %s", png_path)
    except Exception as e:
        logger.warning("Could not save PNG (missing Pillow?): %s", e)

    # Save raw grid data for reuse
    grid_data = {
        "width": grid.width,
        "height": grid.height,
        "cell_size": grid.cell_size,
        "rooms": {
            name: sorted(list(cells))
            for name, cells in grid.room_cells.items()
        },
        "passage": sorted(list(grid.passage_cells)),
        "entrance": grid.entrance,
    }
    json_path = str(output_dir / "grid_data.json")
    with open(json_path, "w") as f:
        json.dump(grid_data, f, indent=2)
    logger.info("Saved grid data to %s", json_path)

    print("=" * 50)
    print(f"Grid: {grid.width} x {grid.height} cells ({grid.width_m:.0f}m x {grid.height_m:.0f}m)")
    print(f"Rooms: {grid.num_rooms}")
    for name in grid.room_names:
        area = grid.room_area_sqm(name)
        print(f"  {name}: {len(grid.room_cells[name])} cells, {area:.1f} m²")
    print(f"Passage cells: {len(grid.passage_cells)}")
    print(f"Entrance: {grid.entrance}")
    print(f"Doors: {len(grid.doors)}")
    print(f"Windows: {len(grid.windows)}")

    # Area validation
    print("\nArea validation (vs. labeled areas):")
    for name, expected in EXAMPLE_EXPECTED_AREAS.items():
        actual = grid.room_area_sqm(name)
        if actual > 0:
            diff_pct = abs(actual - expected) / expected * 100
            status = "OK" if diff_pct < 30 else "WARN"
            print(f"  {status} {name}: expected={expected:.1f}, actual={actual:.1f} ({diff_pct:.0f}% diff)")
        else:
            matches = [n for n in grid.room_names if name.lower() in n.lower() or n.lower() in name.lower()]
            if matches:
                actual = grid.room_area_sqm(matches[0])
                diff_pct = abs(actual - expected) / expected * 100
                status = "OK" if diff_pct < 30 else "WARN"
                print(f"  {status} {name} (as '{matches[0]}'): expected={expected:.1f}, actual={actual:.1f} ({diff_pct:.0f}% diff)")
            else:
                print(f"  MISS {name}: not found in grid (expected {expected:.1f} m²)")


async def main():
    parser = argparse.ArgumentParser(description="Test floor plan analyzer")
    parser.add_argument("--image", default=EXAMPLE_FLOORPLAN, help="Floor plan image path")
    parser.add_argument("--total-area", type=float, default=None, help="Total property area in m²")
    parser.add_argument("--cell-size", type=float, default=1.0, help="Grid cell size in metres (default 1.0, use 0.5 for finer detail)")
    args = parser.parse_args()

    image_path = args.image
    if not Path(image_path).exists():
        logger.error("Floor plan not found at %s", image_path)
        return

    if not os.getenv("OPENROUTER_API_KEY"):
        logger.error("OPENROUTER_API_KEY not set. Copy backend/.env.example to backend/.env and fill it in.")
        return

    logger.info("Analyzing: %s (total_area=%s, cell_size=%s)", image_path, args.total_area, args.cell_size)

    image_url = _image_to_base64_url(image_path)
    grid = await _call_and_parse(image_url, args.total_area, _call_gemini_with_image, args.cell_size)
    _print_results(grid)


if __name__ == "__main__":
    asyncio.run(main())
