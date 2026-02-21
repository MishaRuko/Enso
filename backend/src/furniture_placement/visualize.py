"""Visualize a FloorPlanGrid as a PNG image for debugging.

Renders a color-coded grid where each room gets a unique color,
passages are light gray, and outdoor cells are white.
"""

import colorsys
from pathlib import Path

import numpy as np

from .grid_types import FloorPlanGrid


# Generate N distinct colors
def _distinct_colors(n: int) -> list[tuple[int, int, int]]:
    colors = []
    for i in range(n):
        h = i / max(n, 1)
        r, g, b = colorsys.hsv_to_rgb(h, 0.5, 0.85)
        colors.append((int(r * 255), int(g * 255), int(b * 255)))
    return colors


def grid_to_image_array(grid: FloorPlanGrid, scale: int = 40) -> np.ndarray:
    """Render the grid as an RGB numpy array.

    Args:
        grid: The floor plan grid.
        scale: Pixels per cell.

    Returns:
        RGB array of shape (height * scale, width * scale, 3).
    """
    h, w = grid.height, grid.width
    img = np.full((h * scale, w * scale, 3), 255, dtype=np.uint8)

    room_names = grid.room_names
    colors = _distinct_colors(len(room_names))
    room_color_map = dict(zip(room_names, colors))

    # Fill room cells
    for room_name, cells in grid.room_cells.items():
        color = room_color_map[room_name]
        for (i, j) in cells:
            y0, x0 = i * scale, j * scale
            img[y0:y0 + scale, x0:x0 + scale] = color

    # Fill passage cells
    for (i, j) in grid.passage_cells:
        y0, x0 = i * scale, j * scale
        img[y0:y0 + scale, x0:x0 + scale] = (220, 220, 220)

    # Draw grid lines
    for i in range(h + 1):
        y = i * scale
        if y < img.shape[0]:
            img[y, :] = (180, 180, 180)
    for j in range(w + 1):
        x = j * scale
        if x < img.shape[1]:
            img[:, x] = (180, 180, 180)

    # Mark entrance
    if grid.entrance:
        ei, ej = grid.entrance
        y0, x0 = ei * scale, ej * scale
        # Draw a red border on the entrance cell
        img[y0:y0 + 3, x0:x0 + scale] = (255, 0, 0)
        img[y0 + scale - 3:y0 + scale, x0:x0 + scale] = (255, 0, 0)
        img[y0:y0 + scale, x0:x0 + 3] = (255, 0, 0)
        img[y0:y0 + scale, x0 + scale - 3:x0 + scale] = (255, 0, 0)

    return img


def save_grid_image(grid: FloorPlanGrid, output_path: str, scale: int = 40) -> str:
    """Save a grid visualization as a PNG image.

    Args:
        grid: The floor plan grid.
        output_path: Where to save the PNG.
        scale: Pixels per cell.

    Returns:
        The output path.
    """
    try:
        from PIL import Image
    except ImportError:
        # Fallback: save as raw PPM (no dependency needed)
        img_array = grid_to_image_array(grid, scale)
        h, w, _ = img_array.shape
        path = Path(output_path).with_suffix(".ppm")
        with open(path, "wb") as f:
            f.write(f"P6\n{w} {h}\n255\n".encode())
            f.write(img_array.tobytes())
        return str(path)

    img_array = grid_to_image_array(grid, scale)
    img = Image.fromarray(img_array)

    # Add room labels
    try:
        from PIL import ImageDraw, ImageFont
        draw = ImageDraw.Draw(img)
        try:
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", max(12, scale // 3))
        except (OSError, IOError):
            font = ImageFont.load_default()

        room_names = grid.room_names
        colors = _distinct_colors(len(room_names))
        for room_name, cells in grid.room_cells.items():
            if not cells:
                continue
            # Find centroid of room cells
            avg_i = sum(c[0] for c in cells) / len(cells)
            avg_j = sum(c[1] for c in cells) / len(cells)
            x = int((avg_j + 0.5) * scale)
            y = int((avg_i + 0.5) * scale)
            draw.text((x, y), room_name, fill=(0, 0, 0), font=font, anchor="mm")
    except ImportError:
        pass

    img.save(output_path)
    return output_path


def print_grid_ascii(grid: FloorPlanGrid) -> str:
    """Render the grid as ASCII art. Useful for logging."""
    # Assign single-char labels to rooms
    room_names = grid.room_names
    labels = {}
    for idx, name in enumerate(room_names):
        labels[name] = chr(ord("A") + idx) if idx < 26 else str(idx)

    lines = []
    # Header
    header = "  " + "".join(f"{j % 10}" for j in range(grid.width))
    lines.append(header)

    for i in range(grid.height):
        row = f"{i % 10} "
        for j in range(grid.width):
            cell = (i, j)
            found = False
            for name, cells in grid.room_cells.items():
                if cell in cells:
                    row += labels[name]
                    found = True
                    break
            if not found:
                if cell in grid.passage_cells:
                    row += "."
                else:
                    row += " "
        lines.append(row)

    # Legend
    lines.append("")
    lines.append("Legend:")
    for name, label in labels.items():
        area = grid.room_area_sqm(name)
        lines.append(f"  {label} = {name} ({area:.0f} m²)")
    lines.append(f"  . = passage")
    if grid.entrance:
        lines.append(f"  entrance = {grid.entrance}")

    return "\n".join(lines)
