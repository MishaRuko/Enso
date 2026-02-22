"""Full pipeline: GLB model → floor plan grid → furniture placement.

Usage:
    cd backend/src
    python -m furniture_placement.pipeline

    # With a specific GLB model:
    python -m furniture_placement.pipeline --glb path/to/model.glb

    # Skip Nano Banana (reuse existing colored image):
    python -m furniture_placement.pipeline --reuse-colored output/nano_banana_output.png

    # Custom settings:
    python -m furniture_placement.pipeline --width 10.0 --cell-size 0.5

Requires:
    - OPENROUTER_API_KEY in backend/.env (for Nano Banana + Claude agents)
    - Gurobi license (academic free)
    - Blender 4.x (for GLB → binary floorplan)
"""

import argparse
import asyncio
import json
import logging
import os
import sys
from pathlib import Path

import colorsys

import cv2
import numpy as np
import trimesh

# Fix imports: add parent to path so we can import tools/ and furniture_placement/
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
from openai import AsyncOpenAI

from furniture_placement.grid_types import FloorPlanGrid
from furniture_placement.optimizer import FurniturePlacementModel
from furniture_placement.coord_convert import convert_all_placements
from furniture_placement.visualize import save_grid_image, print_grid_ascii
from furniture_placement.furniture_agents import (
    FurnitureItemSpec,
    specs_to_optimizer_format,
    constraints_to_optimizer_format,
    specs_to_search_queries,
    update_specs_from_search_results,
    _generate_specs_impl,
    _generate_constraints_impl,
)
from tools.ikea.search import search_ikea_products, ikea_results_to_spec_updates
from tools.ikea.trellis_fallback import generate_missing_models

logging.basicConfig(level=logging.INFO, format="%(name)s %(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

# Load env from backend/.env
load_dotenv(Path(__file__).parent.parent.parent / ".env")

OUTPUT_DIR = Path(__file__).parent.parent.parent / "output"
EXAMPLE_DIR = Path(__file__).parent.parent.parent / "example_model"


# ---------------------------------------------------------------------------
# Step 1: GLB → Binary floor plan (Blender) → Nano Banana coloring → Grid
# ---------------------------------------------------------------------------

def _load_binary_image(path: str) -> bytes:
    """Load an image file as PNG bytes."""
    with open(path, "rb") as f:
        return f.read()


async def _color_rooms_with_nano_banana(binary_image_path: str, output_path: str) -> str:
    """Call Nano Banana to color each room a different solid color.

    Args:
        binary_image_path: Path to binary floor plan (black walls, white rooms).
        output_path: Where to save the colored output PNG.

    Returns:
        Path to the saved colored image.
    """
    import base64
    from openai import AsyncOpenAI

    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        raise RuntimeError("OPENROUTER_API_KEY not set")

    with open(binary_image_path, "rb") as f:
        img_bytes = f.read()
    b64 = base64.b64encode(img_bytes).decode()
    data_url = f"data:image/png;base64,{b64}"

    prompt = (
        "This is a floor plan. Fill each individual/distinct room with a different "
        "bright solid colour. Keep the walls black. Keep the coloured bits just solid "
        "inside, no black artefacts. Do not add, remove, or modify any walls or "
        "structural lines."
    )

    client = AsyncOpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=api_key,
        timeout=120.0,
    )

    logger.info("Calling Nano Banana to color rooms...")
    resp = await client.chat.completions.create(
        model="google/gemini-3-pro-image-preview",
        messages=[{
            "role": "user",
            "content": [
                {"type": "text", "text": prompt},
                {"type": "image_url", "image_url": {"url": data_url}},
            ],
        }],
        extra_body={"modalities": ["image", "text"]},
        extra_headers={
            "HTTP-Referer": "https://homedesigner.ai",
            "X-Title": "HomeDesigner",
        },
    )

    # Extract image from response (same extraction logic as nanobananana.py)
    result_url = None
    message = resp.choices[0].message

    images = getattr(message, "images", None)
    if images and len(images) > 0:
        try:
            result_url = images[0]["image_url"]["url"]
        except (KeyError, TypeError, IndexError):
            pass

    if not result_url:
        content = message.content or ""
        if content.startswith("data:image"):
            result_url = content

    if not result_url:
        raw = resp.model_dump()
        choices = raw.get("choices", [])
        if choices:
            msg = choices[0].get("message", {})
            msg_content = msg.get("content")
            if isinstance(msg_content, list):
                for part in msg_content:
                    if isinstance(part, dict):
                        img_url = part.get("image_url", {})
                        if isinstance(img_url, dict) and img_url.get("url", "").startswith("data:image"):
                            result_url = img_url["url"]
                            break
                        text = part.get("text", "")
                        if text.startswith("data:image"):
                            result_url = text
                            break

    if not result_url:
        raise RuntimeError("Nano Banana did not return an image")

    # Decode and save
    header, b64_data = result_url.split(",", 1)
    img_data = base64.b64decode(b64_data)
    with open(output_path, "wb") as f:
        f.write(img_data)
    logger.info("Colored room image saved: %s (%d bytes)", output_path, len(img_data))
    return output_path


def _extract_regions_from_image(img: np.ndarray) -> tuple[np.ndarray, int]:
    """Extract room regions using connected component analysis.

    Same logic as FloorPlanAnalyzer._extract_regions but standalone.
    """
    height, width = img.shape[:2]
    r = img[:, :, 0].astype(np.int16)
    g = img[:, :, 1].astype(np.int16)
    b = img[:, :, 2].astype(np.int16)

    is_dark = (r < 50) & (g < 50) & (b < 50)
    is_bright = (r > 220) & (g > 220) & (b > 220)
    chroma = np.abs(r - g) + np.abs(g - b) + np.abs(b - r)
    is_gray = chroma < 40
    colored_mask = ~is_dark & ~is_bright & ~is_gray

    quantized = (img // 64).astype(np.uint8)

    label_map = np.zeros((height, width), dtype=np.int32)
    next_label = 1

    colored_pixels = quantized[colored_mask]
    if len(colored_pixels) == 0:
        return label_map, 0

    unique_qcolors = np.unique(colored_pixels.reshape(-1, 3), axis=0)
    logger.info("Found %d unique quantized colors", len(unique_qcolors))

    for qc in unique_qcolors:
        match = (
            (quantized[:, :, 0] == qc[0])
            & (quantized[:, :, 1] == qc[1])
            & (quantized[:, :, 2] == qc[2])
            & colored_mask
        )
        n_labels, cc_labels = cv2.connectedComponents(match.astype(np.uint8), connectivity=4)
        for cc_id in range(1, n_labels):
            region_mask = cc_labels == cc_id
            pixel_count = np.count_nonzero(region_mask)
            if pixel_count < height * width * 0.003:
                continue
            label_map[region_mask] = next_label
            next_label += 1

    logger.info("Extracted %d room regions", next_label - 1)
    return label_map, next_label - 1


def _downsample_to_grid(label_map, img_h, img_w, grid_h, grid_w):
    """Downsample label map to grid via majority vote."""
    grid_labels = np.zeros((grid_h, grid_w), dtype=np.int32)
    cell_h = img_h / grid_h
    cell_w = img_w / grid_w
    for i in range(grid_h):
        y0 = int(i * cell_h)
        y1 = int((i + 1) * cell_h)
        for j in range(grid_w):
            x0 = int(j * cell_w)
            x1 = int((j + 1) * cell_w)
            patch = label_map[y0:y1, x0:x1].ravel()
            nonzero = patch[patch > 0]
            if len(nonzero) == 0:
                continue
            counts = np.bincount(nonzero)
            grid_labels[i, j] = counts.argmax()
    return grid_labels


def _guess_room_names(region_cells: dict[int, set], cell_size: float) -> dict[int, str]:
    """Assign room type names by area heuristics."""
    cell_area = cell_size ** 2
    sorted_labels = sorted(region_cells.keys(), key=lambda k: len(region_cells[k]), reverse=True)

    names: dict[int, str] = {}
    used: set[str] = set()
    bedroom_count = 0
    bathroom_count = 0
    hallway_count = 0

    for idx, label_id in enumerate(sorted_labels):
        area = len(region_cells[label_id]) * cell_area

        if idx == 0 and area > 12:
            name = "Living Room"
        elif idx <= 1 and area > 10:
            name = "Kitchen"
        elif area > 12:
            bedroom_count += 1
            name = "Master Bedroom" if bedroom_count == 1 else f"Bedroom {bedroom_count}"
        elif area > 8:
            bedroom_count += 1
            name = "Bedroom" if bedroom_count == 1 else f"Bedroom {bedroom_count}"
        elif area > 5:
            # 5-8 m² is too small for a real bedroom — hallway or utility
            hallway_count += 1
            name = "Hallway" if hallway_count == 1 else f"Hallway {hallway_count}"
        elif area > 3:
            bathroom_count += 1
            name = "Bathroom" if bathroom_count == 1 else f"Bathroom {bathroom_count}"
        elif area > 1.5:
            name = "WC"
        else:
            name = f"Storage {idx + 1}"

        base = name
        suffix = 2
        while name in used:
            name = f"{base} {suffix}"
            suffix += 1
        names[label_id] = name
        used.add(name)

    return names


def build_grid_from_colored_image(
    colored_image_path: str,
    target_width_m: float = 12.0,
    cell_size: float = 0.25,
) -> FloorPlanGrid:
    """Build a FloorPlanGrid from an already-colored floor plan image."""
    img = cv2.imread(colored_image_path)
    if img is None:
        raise FileNotFoundError(f"Cannot load image: {colored_image_path}")
    img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    img_h, img_w = img.shape[:2]

    grid_w = int(target_width_m / cell_size)
    scale = grid_w / img_w
    grid_h = int(img_h * scale)

    label_map, n_regions = _extract_regions_from_image(img)
    grid_labels = _downsample_to_grid(label_map, img_h, img_w, grid_h, grid_w)

    from collections import defaultdict
    region_cells: dict[int, set[tuple[int, int]]] = defaultdict(set)
    for i in range(grid_h):
        for j in range(grid_w):
            lbl = grid_labels[i, j]
            if lbl > 0:
                region_cells[lbl].add((i, j))

    min_cells = max(1, int(1.0 / (cell_size ** 2)))
    region_cells = {k: v for k, v in region_cells.items() if len(v) >= min_cells}

    room_names = _guess_room_names(region_cells, cell_size)

    grid = FloorPlanGrid(width=grid_w, height=grid_h, cell_size=cell_size)
    for label_id, cells in region_cells.items():
        name = room_names.get(label_id)
        if name:
            grid.room_cells[name] = cells

    return grid


# ---------------------------------------------------------------------------
# Step 2 & 3: LLM agents (furniture specs + constraints)
# ---------------------------------------------------------------------------

def _make_llm_caller():
    """Create an OpenRouter LLM caller for the furniture agents."""
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        raise RuntimeError("OPENROUTER_API_KEY not set in backend/.env")

    client = AsyncOpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=api_key,
        timeout=120.0,
    )
    model = "anthropic/claude-sonnet-4-6"

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

    return llm_call


# ---------------------------------------------------------------------------
# GLB scene export
# ---------------------------------------------------------------------------

def _room_colors(n: int) -> list[tuple[int, int, int, int]]:
    """Generate N distinct RGBA colors for rooms."""
    colors = []
    for i in range(n):
        h = i / max(n, 1)
        r, g, b = colorsys.hsv_to_rgb(h, 0.25, 0.92)
        colors.append((int(r * 255), int(g * 255), int(b * 255), 255))
    return colors


def _furniture_color(category: str) -> tuple[int, int, int, int]:
    """Pick a color based on furniture category."""
    cat = category.lower()
    if "bed" in cat:
        return (180, 140, 100, 255)  # warm wood
    if "sofa" in cat or "armchair" in cat or "chair" in cat:
        return (120, 140, 170, 255)  # blue-grey fabric
    if "table" in cat or "desk" in cat:
        return (160, 130, 90, 255)   # oak
    if "wardrobe" in cat or "cabinet" in cat or "shelf" in cat or "bookshelf" in cat:
        return (200, 180, 150, 255)  # light wood
    if "lamp" in cat:
        return (240, 220, 180, 255)  # cream
    if "plant" in cat:
        return (80, 160, 80, 255)    # green
    if "mirror" in cat:
        return (200, 220, 240, 255)  # light blue
    return (180, 180, 180, 255)      # neutral grey


def _compute_model_transform(
    model_scene: trimesh.Scene,
    target_width_m: float,
) -> np.ndarray:
    """Compute 4x4 transform to align a GLB model with the furniture grid coordinates.

    The Blender floorplan renderer uses an orthographic camera with:
        ortho_scale = max(model_x, model_y_blender) * 1.1
    The 1024x1024 image covers ortho_scale metres in both directions.
    The grid assumes the image width = target_width_m.

    The furniture coordinate system has Z increasing northward, but the model's
    Z increases southward (image top→bottom = model +Z). We flip Z only.
    The negative-Z scale produces a mirror transform (det < 0), so callers
    must reverse face winding on each mesh after applying this transform.
    """
    bounds = model_scene.bounds
    extent = bounds[1] - bounds[0]
    center = (bounds[0] + bounds[1]) / 2

    blender_x = extent[0]
    blender_y = extent[2]  # trimesh Z → Blender Y
    ortho_scale = max(blender_x, blender_y) * 1.1

    scale = target_width_m / ortho_scale

    T = np.eye(4)
    T[0, 0] = scale         # scale X (no flip)
    T[1, 1] = scale          # scale Y (height)
    T[2, 2] = -scale         # scale + flip Z
    T[0, 3] = target_width_m / 2 - center[0] * scale
    T[1, 3] = -bounds[0][1] * scale  # floor at Y=0
    T[2, 3] = target_width_m / 2 + center[2] * scale
    return T


def _download_glb(url: str, cache_dir: Path) -> str | None:
    """Download a GLB file to a local cache directory. Returns local path or None."""
    import hashlib
    import httpx

    url_hash = hashlib.md5(url.encode()).hexdigest()[:12]
    local_path = cache_dir / f"{url_hash}.glb"
    if local_path.exists():
        return str(local_path)

    try:
        with httpx.Client(timeout=30, follow_redirects=True) as client:
            resp = client.get(url)
            resp.raise_for_status()
            local_path.write_bytes(resp.content)
            return str(local_path)
    except Exception as e:
        logger.warning("Failed to download GLB %s: %s", url[:80], e)
        return None


def _load_and_fit_furniture_glb(
    glb_path: str,
    target_w: float,
    target_d: float,
    target_h: float,
) -> trimesh.Trimesh | None:
    """Load a furniture GLB, scale it to fit the target bounding box, and return as a single mesh."""
    try:
        loaded = trimesh.load(glb_path)
    except Exception as e:
        logger.warning("Failed to load GLB %s: %s", glb_path, e)
        return None

    # Combine all geometries into one mesh
    if isinstance(loaded, trimesh.Scene):
        meshes = list(loaded.dump())
        if not meshes:
            return None
        mesh = trimesh.util.concatenate(meshes)
    else:
        mesh = loaded

    if not hasattr(mesh, 'bounds') or mesh.bounds is None:
        return None

    # Compute scale to fit target dimensions
    extent = mesh.bounds[1] - mesh.bounds[0]
    if any(e <= 0 for e in extent):
        return None

    # Scale uniformly to fit within target box (preserve proportions)
    sx = target_w / extent[0] if extent[0] > 0 else 1
    sy = target_h / extent[1] if extent[1] > 0 else 1
    sz = target_d / extent[2] if extent[2] > 0 else 1
    scale = min(sx, sy, sz)

    # Center at origin, scale, then shift so bottom is at Y=0
    center = (mesh.bounds[0] + mesh.bounds[1]) / 2
    mesh.apply_translation(-center)
    mesh.apply_scale(scale)

    # Shift bottom to Y=0
    new_min_y = mesh.bounds[0][1]
    mesh.apply_translation([0, -new_min_y, 0])

    return mesh


def export_scene_glb(
    grid: FloorPlanGrid,
    api_placements: list[dict],
    specs: dict,
    output_path: str,
    model_path: str | None = None,
    target_width_m: float = 12.0,
) -> str:
    """Export placement result as GLB: apartment model + actual furniture GLBs.

    Downloads real 3D models from glb_url when available, falls back to
    colored placeholder boxes when no GLB is available.
    """
    scene = trimesh.Scene()

    # GLB download cache
    cache_dir = OUTPUT_DIR / "glb_cache"
    cache_dir.mkdir(parents=True, exist_ok=True)

    # --- Load real apartment model ---
    if model_path and os.path.exists(model_path):
        logger.info("Loading apartment model: %s", model_path)
        model_scene = trimesh.load(model_path)
        T = _compute_model_transform(model_scene, target_width_m)

        if isinstance(model_scene, trimesh.Scene):
            for name, geom in model_scene.geometry.items():
                geom_copy = geom.copy()
                geom_copy.apply_transform(T)
                if hasattr(geom_copy, 'faces') and geom_copy.faces is not None:
                    geom_copy.faces = geom_copy.faces[:, ::-1]
                scene.add_geometry(geom_copy, node_name=f"apartment_{name}")
        else:
            model_mesh = model_scene.copy()
            model_mesh.apply_transform(T)
            if hasattr(model_mesh, 'faces') and model_mesh.faces is not None:
                model_mesh.faces = model_mesh.faces[:, ::-1]
            scene.add_geometry(model_mesh, node_name="apartment")

        logger.info("Apartment model added (scale=%.2f)", T[0, 0])
    else:
        logger.warning("No apartment model provided, furniture-only export")

    # --- Furniture: real models or placeholder boxes ---
    spec_lookup: dict[tuple[str, str], dict] = {}
    for room_name, items in (specs or {}).items():
        for item in items:
            if isinstance(item, dict):
                spec_lookup[(room_name, item["name"])] = item
            else:
                spec_lookup[(room_name, item.name)] = {
                    "name": item.name, "category": item.category,
                    "height_m": item.height_m,
                    "length_m": item.length_m, "width_m": item.width_m,
                }

    real_count = 0
    box_count = 0

    for p in api_placements:
        pos = p["position"]
        size = p.get("size_m", {})
        w = size.get("width", 0.5)
        d = size.get("depth", 0.5)

        spec = spec_lookup.get((p["room_name"], p["name"]), {})
        h = spec.get("height_m", 0.8)
        category = spec.get("category", p["name"])

        if spec.get("length_m") and spec.get("width_m"):
            actual_l = spec["length_m"]
            actual_w = spec["width_m"]
            if d >= w:
                d, w = actual_l, actual_w
            else:
                w, d = actual_l, actual_w

        rot_deg = p.get("rotation_y_degrees", 0)
        rot_rad = np.radians(rot_deg)
        node_name = f"furn_{p['room_name']}_{p['name']}"

        # Try loading real GLB model
        glb_url = p.get("glb_url", "")
        furniture_mesh = None
        if glb_url:
            local_path = _download_glb(glb_url, cache_dir)
            if local_path:
                furniture_mesh = _load_and_fit_furniture_glb(local_path, w, d, h)

        if furniture_mesh is not None:
            # Place real model
            rot_matrix = trimesh.transformations.rotation_matrix(rot_rad, [0, 1, 0])
            furniture_mesh.apply_transform(rot_matrix)
            # Re-align bottom to Y=0 after rotation (rotation can shift bounds)
            min_y_after_rot = furniture_mesh.bounds[0][1]
            furniture_mesh.apply_translation([pos["x"], -min_y_after_rot, pos["z"]])
            scene.add_geometry(furniture_mesh, node_name=node_name)
            real_count += 1
        else:
            # Fallback: colored placeholder box
            color = _furniture_color(category)
            box = trimesh.creation.box(extents=[w, h, d])
            rot_matrix = trimesh.transformations.rotation_matrix(rot_rad, [0, 1, 0])
            box.apply_transform(rot_matrix)
            box.apply_translation([pos["x"], h / 2, pos["z"]])
            box.visual.face_colors = color
            scene.add_geometry(box, node_name=node_name)
            box_count += 1

    scene.export(output_path)
    logger.info(
        "Exported GLB: %s (%d real models, %d placeholder boxes)",
        output_path, real_count, box_count,
    )
    return output_path


# ---------------------------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------------------------

async def run_pipeline(
    colored_image_path: str,
    target_width_m: float = 12.0,
    cell_size: float = 0.25,
    style: str = "modern scandinavian",
    budget_max: float = 5000,
    time_limit: int = 180,
    output_dir: Path | None = None,
    model_path: str | None = None,
) -> dict:
    """Run the full pipeline: colored image → grid → furniture → optimize → 3D.

    Args:
        colored_image_path: Path to the Nano Banana colored floor plan.
        target_width_m: Assumed real-world width of the building.
        cell_size: Grid cell size in metres.
        style: Furniture style preference.
        budget_max: Max budget in EUR.
        time_limit: Gurobi time limit in seconds.
        output_dir: Where to save outputs.

    Returns:
        Dict with placements, grid_data, search_queries.
    """
    if output_dir is None:
        output_dir = OUTPUT_DIR
    output_dir.mkdir(parents=True, exist_ok=True)

    # ---- Step 1: Build grid from colored image ----
    print("\n" + "=" * 60)
    print("STEP 1: Building grid from colored floor plan")
    print("=" * 60)

    grid = build_grid_from_colored_image(colored_image_path, target_width_m, cell_size)

    print(f"Grid: {grid.width}x{grid.height} cells ({grid.width_m:.1f}x{grid.height_m:.1f} m)")
    print(f"Rooms ({grid.num_rooms}):")
    for name in grid.room_names:
        area = grid.room_area_sqm(name)
        print(f"  {name}: {area:.1f} m² ({len(grid.room_cells[name])} cells)")

    total_area = sum(grid.room_area_sqm(n) for n in grid.room_names)
    print(f"Total room area: {total_area:.1f} m²")

    # Save grid visualization
    vis_path = output_dir / "pipeline_grid.png"
    save_grid_image(grid, str(vis_path), scale=20)
    print(f"Grid visualization: {vis_path}")

    # Save grid data
    grid_json_path = output_dir / "grid_data.json"
    with open(grid_json_path, "w") as f:
        json.dump(grid.to_dict(), f, indent=2)
    print(f"Grid data: {grid_json_path}")

    # ASCII preview
    ascii_grid = print_grid_ascii(grid)
    print(f"\n{ascii_grid}")

    # ---- Step 2: Furniture spec agent ----
    print("\n" + "=" * 60)
    print("STEP 2: Generating furniture specifications (Claude)")
    print("=" * 60)

    preferences = {
        "style": style,
        "budget_max": budget_max,
        "currency": "EUR",
        "colors": ["warm neutrals", "wood tones"],
        "lifestyle": ["work from home", "couple"],
    }

    llm_call = _make_llm_caller()
    specs = await _generate_specs_impl(grid, preferences, llm_call)

    total_items = sum(len(v) for v in specs.values())
    print(f"\nFurniture specs: {total_items} items")
    for room_name, items in specs.items():
        if not items:
            print(f"  {room_name}: (empty)")
            continue
        print(f"  {room_name} ({grid.room_area_sqm(room_name):.1f} m²):")
        footprint_total = 0
        for item in items:
            fp = item.length_m * item.width_m
            footprint_total += fp
            print(f"    {item.name}: {item.length_m:.2f}x{item.width_m:.2f}m [{item.priority}]")
        room_area = grid.room_area_sqm(room_name)
        pct = (footprint_total / room_area * 100) if room_area > 0 else 0
        print(f"    → Footprint: {footprint_total:.1f} m² ({pct:.0f}% of room)")

    # ---- Step 2b: IKEA product search ----
    print("\n" + "=" * 60)
    print("STEP 2b: IKEA product search")
    print("=" * 60)

    ikea_results = await search_ikea_products(specs)

    found = sum(1 for r in ikea_results if r.get("found"))
    with_glb = sum(1 for r in ikea_results if r.get("glb_url"))
    print(f"IKEA search: {found}/{len(ikea_results)} found, {with_glb} with GLB models")
    for r in ikea_results:
        status = "FOUND" if r.get("found") else "NOT FOUND"
        glb = " [GLB]" if r.get("glb_url") else ""
        ikea_name = r.get("ikea_name", "")
        price_str = ""
        if r.get("price"):
            price_str = f" {r['currency']}{r['price']:.0f}"
        print(f"  [{r['room_name']}] {r['name']}: {status} {ikea_name}{price_str}{glb}")

    # Update specs with real IKEA dimensions (if available)
    spec_updates = ikea_results_to_spec_updates(ikea_results)
    if spec_updates:
        update_specs_from_search_results(specs, spec_updates)
        print(f"Updated {len(spec_updates)} items with actual IKEA dimensions")

    # Build lookup for enriching placements later
    ikea_lookup: dict[tuple[str, str], dict] = {}
    for r in ikea_results:
        if r.get("found"):
            ikea_lookup[(r["room_name"], r["name"])] = r

    search_queries = specs_to_search_queries(specs, preferences)

    # ---- Step 3: Constraint agent ----
    print("\n" + "=" * 60)
    print("STEP 3: Generating placement constraints (Claude)")
    print("=" * 60)

    constraints = await _generate_constraints_impl(grid, specs, preferences, llm_call)

    for room_name, c in constraints.items():
        print(f"  {room_name}:")
        if c.boundary_items:
            print(f"    boundary: {c.boundary_items}")
        if c.distance_constraints:
            print(f"    distance: {len(c.distance_constraints)} rules")
        if c.alignment_constraints:
            print(f"    align: {len(c.alignment_constraints)} pairs")
        if c.facing_constraints:
            print(f"    facing: {len(c.facing_constraints)} pairs")

    # ---- Step 4: Gurobi optimizer ----
    print("\n" + "=" * 60)
    print("STEP 4: Running Gurobi optimizer")
    print("=" * 60)

    opt_furniture = specs_to_optimizer_format(specs, cell_size)
    opt_constraints = constraints_to_optimizer_format(constraints, cell_size)

    model = FurniturePlacementModel(
        grid=grid,
        furniture=opt_furniture,
        constraints=opt_constraints,
        time_limit=time_limit,
    )
    placements = model.optimize()

    if not placements:
        print("No solution found, retrying without distance constraints...")
        for room_name in opt_constraints:
            opt_constraints[room_name].distance_constraints = []
        model = FurniturePlacementModel(
            grid=grid,
            furniture=opt_furniture,
            constraints=opt_constraints,
            time_limit=time_limit,
        )
        placements = model.optimize()

    if not placements:
        print("ERROR: Gurobi found no feasible solution")
        return {"error": "no_solution"}

    print(f"\nPlaced {len(placements)} items:")
    for p in placements:
        print(f"  {p.room_name}/{p.name}: grid({p.grid_i},{p.grid_j}) "
              f"size={p.size_i}x{p.size_j} orient=({p.sigma},{p.mu})")

    # ---- Step 5: Convert to 3D coordinates ----
    print("\n" + "=" * 60)
    print("STEP 5: Converting to 3D coordinates")
    print("=" * 60)

    coords_3d = convert_all_placements(placements, grid)

    api_placements = []
    for coord in coords_3d:
        # Enrich with IKEA data if available
        ikea_data = ikea_lookup.get((coord["room_name"], coord["name"]), {})

        api_placements.append({
            "item_id": ikea_data.get("ikea_item_code") or coord["name"],
            "name": coord["name"],
            "position": coord["position"],
            "rotation_y_degrees": coord["rotation_y_degrees"],
            "room_name": coord["room_name"],
            "size_m": coord.get("size_m", {}),
            "glb_url": ikea_data.get("glb_url", ""),
            "image_url": ikea_data.get("image_url", ""),
            "buy_url": ikea_data.get("buy_url", ""),
            "ikea_item_code": ikea_data.get("ikea_item_code", ""),
            "ikea_name": ikea_data.get("ikea_name", ""),
            "price": ikea_data.get("price"),
            "currency": ikea_data.get("currency", ""),
            "reasoning": f"Gurobi-optimized placement in {coord['room_name']}",
        })

    for ap in api_placements:
        pos = ap["position"]
        size = ap["size_m"]
        glb_tag = " [GLB]" if ap.get("glb_url") else ""
        ikea_tag = f" ({ap['ikea_name']})" if ap.get("ikea_name") else ""
        print(f"  {ap['room_name']}/{ap['name']}{ikea_tag}: "
              f"pos=({pos['x']:.2f}, {pos['y']:.2f}, {pos['z']:.2f}) "
              f"rot={ap['rotation_y_degrees']:.0f}° "
              f"size={size.get('width',0):.2f}x{size.get('depth',0):.2f}m{glb_tag}")

    # ---- Step 5b: Trellis 3D model generation ----
    print("\n" + "=" * 60)
    print("STEP 5b: Trellis 3D model generation")
    print("=" * 60)

    items_with_glb_before = sum(1 for p in api_placements if p.get("glb_url"))
    print(f"Items with IKEA GLB: {items_with_glb_before}/{len(api_placements)}")

    total_with_glb = await generate_missing_models(
        api_placements, max_calls=10, dry_run=False,
    )
    print(f"After Trellis: {total_with_glb}/{len(api_placements)} have GLBs")

    # ---- Step 5c: Export GLB scene with placeholder furniture ----
    print("\n" + "=" * 60)
    print("STEP 5c: Exporting GLB scene")
    print("=" * 60)

    glb_path = output_dir / "pipeline_furnished.glb"
    export_scene_glb(
        grid, api_placements, specs, str(glb_path),
        model_path=model_path, target_width_m=target_width_m,
    )
    print(f"GLB scene: {glb_path}")

    # ---- Step 6: Save results ----
    print("\n" + "=" * 60)
    print("STEP 6: Saving results")
    print("=" * 60)

    result = {
        "grid_data": grid.to_dict(),
        "placements": api_placements,
        "search_queries": search_queries,
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
    }

    result_path = output_dir / "pipeline_result.json"
    with open(result_path, "w") as f:
        json.dump(result, f, indent=2)
    print(f"Full result: {result_path}")

    placements_path = output_dir / "placements.json"
    with open(placements_path, "w") as f:
        json.dump(api_placements, f, indent=2)
    print(f"Placements: {placements_path}")

    print(f"\nDone! {len(placements)} items placed across {grid.num_rooms} rooms.")
    return result


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Full pipeline: colored floor plan → placed furniture"
    )
    parser.add_argument(
        "--colored-image",
        default=str(OUTPUT_DIR / "nano_banana_output.png"),
        help="Path to the Nano Banana colored floor plan image",
    )
    parser.add_argument(
        "--binary-image",
        default=str(OUTPUT_DIR / "glb_binary_input.png"),
        help="Path to binary floor plan (used to generate colored image via Nano Banana)",
    )
    parser.add_argument("--width", type=float, default=12.0, help="Building width in metres")
    parser.add_argument("--cell-size", type=float, default=0.25, help="Grid cell size in metres")
    parser.add_argument("--style", default="modern scandinavian", help="Furniture style")
    parser.add_argument("--budget-max", type=float, default=5000, help="Max budget EUR")
    parser.add_argument("--time-limit", type=int, default=180, help="Gurobi time limit (s)")
    parser.add_argument("--output-dir", default=str(OUTPUT_DIR), help="Output directory")
    parser.add_argument(
        "--model",
        default=str(EXAMPLE_DIR / "example_model.glb"),
        help="Path to the apartment GLB model (furniture is placed into this)",
    )
    args = parser.parse_args()

    colored_path = args.colored_image

    # If colored image doesn't exist, generate it from binary via Nano Banana
    if not os.path.exists(colored_path):
        binary_path = args.binary_image
        if not os.path.exists(binary_path):
            print(f"ERROR: Neither colored image ({colored_path}) nor binary image ({binary_path}) found.")
            sys.exit(1)
        print(f"Colored image not found, generating via Nano Banana from {binary_path}...")
        colored_path = asyncio.run(
            _color_rooms_with_nano_banana(binary_path, colored_path)
        )
        print(f"Colored image saved: {colored_path}")

    result = asyncio.run(run_pipeline(
        colored_image_path=colored_path,
        target_width_m=args.width,
        cell_size=args.cell_size,
        style=args.style,
        budget_max=args.budget_max,
        time_limit=args.time_limit,
        output_dir=Path(args.output_dir),
        model_path=args.model,
    ))

    if result.get("error"):
        sys.exit(1)


if __name__ == "__main__":
    main()
