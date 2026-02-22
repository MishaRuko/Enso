"""Quick smoke-test for Miro vision board generation.

Run from backend/ directory:
  uv run --project .. python test_miro.py
"""

import logging
import sys
import os

# backend/ is the package root — src is the package
sys.path.insert(0, os.path.dirname(__file__))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    stream=sys.stdout,
)

from src.tools.miro_mcp import generate_vision_board_with_miro_ai  # noqa: E402

BRIEF = {
    "style": "warm bohemian",
    "room_type": "living room",
    "budget_min": 500,
    "budget_max": 2000,
    "currency": "EUR",
    "colors": ["terracotta", "warm cream", "forest green"],
    "lifestyle": ["relaxing", "entertaining friends"],
    "must_haves": ["large sofa", "lots of plants", "cozy lighting"],
    "dealbreakers": ["cold grey tones", "minimalist"],
    "existing_furniture": ["vintage wooden coffee table"],
}

if __name__ == "__main__":
    print("\n=== Testing Miro board generation ===\n")
    result = generate_vision_board_with_miro_ai(BRIEF)
    print("\n=== RESULT ===")
    print(f"URL:            {result.url}")
    print(f"Pass 2 applied: {result.pass2_applied}")
    if result.layout_plan:
        imgs = result.layout_plan.get("images", [])
        stickies = result.layout_plan.get("stickies", [])
        print(f"Images:         {len(imgs)}")
        print(f"Stickies:       {len(stickies)}")
