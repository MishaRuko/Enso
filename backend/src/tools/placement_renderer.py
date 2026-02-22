"""Render a top-down 2D diagram of furniture placements for verification.

Generates a PNG image using Pillow showing the room outline, doors/windows,
and each placed furniture item as a labeled rectangle at its position.
"""

import base64
import io
import math

from PIL import Image, ImageDraw, ImageFont

from ..models.schemas import FurnitureItem, FurniturePlacement, RoomData

_PAD = 40
_PX_PER_M = 80

_COLORS = [
    "#db504a", "#7c8c6e", "#4a90d9", "#d4a037",
    "#8e44ad", "#27ae60", "#e67e22", "#2c3e50",
    "#e74c3c", "#1abc9c", "#f39c12", "#9b59b6",
]


def _hex_to_rgb(h: str) -> tuple[int, int, int]:
    h = h.lstrip("#")
    return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))


def _hex_to_rgba(h: str, alpha: int) -> tuple[int, int, int, int]:
    r, g, b = _hex_to_rgb(h)
    return (r, g, b, alpha)


def render_placement_png(
    room: RoomData,
    placements: list[FurniturePlacement],
    furniture: list[FurnitureItem],
) -> bytes:
    """Generate a PNG top-down diagram and return raw bytes."""
    dims_map = {f.id: f.dimensions for f in furniture}
    names_map = {f.id: f.name for f in furniture}

    rw = room.width_m * _PX_PER_M
    rl = room.length_m * _PX_PER_M
    w = int(rw + 2 * _PAD)
    h = int(rl + 2 * _PAD)

    img = Image.new("RGBA", (w, h), (255, 255, 255, 255))
    draw = ImageDraw.Draw(img)

    # Room outline
    draw.rectangle([_PAD, _PAD, _PAD + rw, _PAD + rl], fill="#f5f0eb", outline="#2e2e38", width=2)

    # Axis labels and tick marks (apartment-absolute coordinates)
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 11)
        font_sm = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 8)
    except OSError:
        font = ImageFont.load_default()
        font_sm = font

    x_off = room.x_offset_m if hasattr(room, "x_offset_m") else 0
    z_off = room.z_offset_m if hasattr(room, "z_offset_m") else 0

    draw.text((_PAD + rw / 2, _PAD - 22), f"X ({x_off:.1f}–{x_off + room.width_m:.1f}m)", fill="#666", anchor="mm", font=font)
    draw.text((_PAD - 22, _PAD + rl / 2), f"Z ({z_off:.1f}–{z_off + room.length_m:.1f}m)", fill="#666", anchor="mm", font=font)

    # X-axis tick marks every 1m (apartment-absolute values)
    x_start = math.ceil(x_off)
    x_end_val = math.floor(x_off + room.width_m)
    for xm in range(x_start, x_end_val + 1):
        px = _PAD + (xm - x_off) * _PX_PER_M
        draw.line([(px, _PAD), (px, _PAD + 6)], fill="#999", width=1)
        draw.text((px, _PAD - 8), f"{xm}", fill="#999", anchor="mm", font=font_sm)

    # Z-axis tick marks every 1m (apartment-absolute values)
    z_start = math.ceil(z_off)
    z_end_val = math.floor(z_off + room.length_m)
    for zm in range(z_start, z_end_val + 1):
        py = _PAD + (zm - z_off) * _PX_PER_M
        draw.line([(_PAD, py), (_PAD + 6, py)], fill="#999", width=1)
        draw.text((_PAD - 8, py), f"{zm}", fill="#999", anchor="rm", font=font_sm)

    # Doors
    for door in room.doors:
        wall = door.wall.lower()
        pos = door.position_m * _PX_PER_M
        dw = door.width_m * _PX_PER_M
        brown = _hex_to_rgba("#8B4513", 180)
        if wall == "south":
            draw.rectangle([_PAD + pos, _PAD, _PAD + pos + dw, _PAD + 4], fill=brown)
        elif wall == "north":
            draw.rectangle([_PAD + pos, _PAD + rl - 4, _PAD + pos + dw, _PAD + rl], fill=brown)
        elif wall == "west":
            draw.rectangle([_PAD, _PAD + pos, _PAD + 4, _PAD + pos + dw], fill=brown)
        elif wall == "east":
            draw.rectangle([_PAD + rw - 4, _PAD + pos, _PAD + rw, _PAD + pos + dw], fill=brown)

    # Windows
    for win in room.windows:
        wall = win.wall.lower()
        pos = win.position_m * _PX_PER_M
        ww = win.width_m * _PX_PER_M
        blue = _hex_to_rgba("#87CEEB", 180)
        if wall == "south":
            draw.rectangle([_PAD + pos, _PAD, _PAD + pos + ww, _PAD + 3], fill=blue)
        elif wall == "north":
            draw.rectangle([_PAD + pos, _PAD + rl - 3, _PAD + pos + ww, _PAD + rl], fill=blue)
        elif wall == "west":
            draw.rectangle([_PAD, _PAD + pos, _PAD + 3, _PAD + pos + ww], fill=blue)
        elif wall == "east":
            draw.rectangle([_PAD + rw - 3, _PAD + pos, _PAD + rw, _PAD + pos + ww], fill=blue)

    # Furniture (convert absolute coords to room-relative for rendering)
    for i, p in enumerate(placements):
        dims = dims_map.get(p.item_id)
        name = names_map.get(p.item_id, p.name)
        color = _COLORS[i % len(_COLORS)]

        if dims:
            fw = dims.width_cm / 100 * _PX_PER_M
            fd = dims.depth_cm / 100 * _PX_PER_M
        else:
            fw = 0.5 * _PX_PER_M
            fd = 0.5 * _PX_PER_M

        rot = p.rotation_y_degrees % 360
        if 45 < rot < 135 or 225 < rot < 315:
            fw, fd = fd, fw

        cx = _PAD + (p.position.x - x_off) * _PX_PER_M
        cy = _PAD + (p.position.z - z_off) * _PX_PER_M
        x0 = cx - fw / 2
        y0 = cy - fd / 2

        fill = _hex_to_rgba(color, 77)
        draw.rectangle([x0, y0, x0 + fw, y0 + fd], fill=fill, outline=color, width=2)

        label = name[:20]
        draw.text((cx, cy), label, fill="#2e2e38", anchor="mm", font=font_sm)

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def _render_front_elevation(
    room: RoomData,
    placements: list[FurniturePlacement],
    furniture: list[FurnitureItem],
) -> bytes:
    """Render front elevation (X-Y plane, looking from south). Shows widths and heights."""
    dims_map = {f.id: f.dimensions for f in furniture}
    names_map = {f.id: f.name for f in furniture}

    rw = room.width_m * _PX_PER_M
    rh = room.height_m * _PX_PER_M
    w = int(rw + 2 * _PAD)
    h = int(rh + 2 * _PAD)

    img = Image.new("RGBA", (w, h), (255, 255, 255, 255))
    draw = ImageDraw.Draw(img)

    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 11)
        font_sm = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 8)
    except OSError:
        font = ImageFont.load_default()
        font_sm = font

    # Room outline (front wall)
    draw.rectangle([_PAD, _PAD, _PAD + rw, _PAD + rh], fill="#f5f0eb", outline="#2e2e38", width=2)
    draw.text((_PAD + rw / 2, _PAD - 18), f"FRONT VIEW — X: {room.width_m}m", fill="#666", anchor="mm", font=font)
    draw.text((_PAD - 18, _PAD + rh / 2), f"Y: {room.height_m}m", fill="#666", anchor="mm", font=font)

    # Floor line
    draw.line([_PAD, _PAD + rh, _PAD + rw, _PAD + rh], fill="#2e2e38", width=3)

    x_off = room.x_offset_m if hasattr(room, "x_offset_m") else 0
    for i, p in enumerate(placements):
        dims = dims_map.get(p.item_id)
        name = names_map.get(p.item_id, p.name)
        color = _COLORS[i % len(_COLORS)]

        if dims:
            fw = dims.width_cm / 100 * _PX_PER_M
            fh = dims.height_cm / 100 * _PX_PER_M
        else:
            fw = 0.5 * _PX_PER_M
            fh = 0.5 * _PX_PER_M

        rot = p.rotation_y_degrees % 360
        if 45 < rot < 135 or 225 < rot < 315:
            fw = (dims.depth_cm / 100 * _PX_PER_M) if dims else fw

        cx = _PAD + (p.position.x - x_off) * _PX_PER_M
        y_bottom = _PAD + rh
        y_top = y_bottom - fh
        x0 = cx - fw / 2

        fill = _hex_to_rgba(color, 77)
        draw.rectangle([x0, y_top, x0 + fw, y_bottom], fill=fill, outline=color, width=2)
        draw.text((cx, y_top + fh / 2), name[:15], fill="#2e2e38", anchor="mm", font=font_sm)

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def _render_side_elevation(
    room: RoomData,
    placements: list[FurniturePlacement],
    furniture: list[FurnitureItem],
) -> bytes:
    """Render side elevation (Z-Y plane, looking from west). Shows depths and heights."""
    dims_map = {f.id: f.dimensions for f in furniture}
    names_map = {f.id: f.name for f in furniture}

    rl = room.length_m * _PX_PER_M
    rh = room.height_m * _PX_PER_M
    w = int(rl + 2 * _PAD)
    h = int(rh + 2 * _PAD)

    img = Image.new("RGBA", (w, h), (255, 255, 255, 255))
    draw = ImageDraw.Draw(img)

    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 11)
        font_sm = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 8)
    except OSError:
        font = ImageFont.load_default()
        font_sm = font

    draw.rectangle([_PAD, _PAD, _PAD + rl, _PAD + rh], fill="#f5f0eb", outline="#2e2e38", width=2)
    draw.text((_PAD + rl / 2, _PAD - 18), f"SIDE VIEW — Z: {room.length_m}m", fill="#666", anchor="mm", font=font)
    draw.text((_PAD - 18, _PAD + rh / 2), f"Y: {room.height_m}m", fill="#666", anchor="mm", font=font)

    draw.line([_PAD, _PAD + rh, _PAD + rl, _PAD + rh], fill="#2e2e38", width=3)

    z_off = room.z_offset_m if hasattr(room, "z_offset_m") else 0
    for i, p in enumerate(placements):
        dims = dims_map.get(p.item_id)
        name = names_map.get(p.item_id, p.name)
        color = _COLORS[i % len(_COLORS)]

        if dims:
            fd = dims.depth_cm / 100 * _PX_PER_M
            fh = dims.height_cm / 100 * _PX_PER_M
        else:
            fd = 0.5 * _PX_PER_M
            fh = 0.5 * _PX_PER_M

        rot = p.rotation_y_degrees % 360
        if 45 < rot < 135 or 225 < rot < 315:
            fd = (dims.width_cm / 100 * _PX_PER_M) if dims else fd

        cz = _PAD + (p.position.z - z_off) * _PX_PER_M
        y_bottom = _PAD + rh
        y_top = y_bottom - fh
        z0 = cz - fd / 2

        fill = _hex_to_rgba(color, 77)
        draw.rectangle([z0, y_top, z0 + fd, y_bottom], fill=fill, outline=color, width=2)
        draw.text((cz, y_top + fh / 2), name[:15], fill="#2e2e38", anchor="mm", font=font_sm)

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def render_placement_views(
    room: RoomData,
    placements: list[FurniturePlacement],
    furniture: list[FurnitureItem],
) -> list[str]:
    """Render 3 views (top-down, front, side) and return as PNG data-URL list."""
    views = [
        render_placement_png(room, placements, furniture),
        _render_front_elevation(room, placements, furniture),
        _render_side_elevation(room, placements, furniture),
    ]
    return [f"data:image/png;base64,{base64.b64encode(v).decode()}" for v in views]


def render_placement_data_url(
    room: RoomData,
    placements: list[FurniturePlacement],
    furniture: list[FurnitureItem],
) -> str:
    """Render placement diagram and return as PNG data-URL."""
    png_bytes = render_placement_png(room, placements, furniture)
    b64 = base64.b64encode(png_bytes).decode()
    return f"data:image/png;base64,{b64}"
