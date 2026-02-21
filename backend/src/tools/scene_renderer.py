"""Software 3D renderer — renders Trellis room GLB + furniture boxes from multiple angles.

Uses trimesh for GLB loading only, Pillow for rasterization. No OpenGL/display needed.
"""

import base64
import io
import logging

import httpx
import numpy as np
from PIL import Image, ImageDraw, ImageFont

logger = logging.getLogger(__name__)

_FURN_COLORS = [
    (219, 80, 74, 200), (124, 140, 110, 200), (74, 144, 217, 200),
    (212, 160, 55, 200), (142, 68, 173, 200), (39, 174, 96, 200),
    (230, 126, 34, 200), (44, 62, 80, 200), (231, 76, 60, 200),
    (26, 188, 156, 200), (243, 156, 18, 200), (155, 89, 182, 200),
]

_BG = (250, 249, 247, 255)


def _box_mesh(center, size, color):
    """Create box vertices (8), faces (12 tris), and per-face colors."""
    cx, cy, cz = center
    hx, hy, hz = size[0] / 2, size[1] / 2, size[2] / 2

    v = np.array([
        [cx - hx, cy - hy, cz - hz], [cx + hx, cy - hy, cz - hz],
        [cx + hx, cy + hy, cz - hz], [cx - hx, cy + hy, cz - hz],
        [cx - hx, cy - hy, cz + hz], [cx + hx, cy - hy, cz + hz],
        [cx + hx, cy + hy, cz + hz], [cx - hx, cy + hy, cz + hz],
    ], dtype=np.float32)

    f = np.array([
        [0, 2, 1], [0, 3, 2],  # back
        [4, 5, 6], [4, 6, 7],  # front
        [0, 1, 5], [0, 5, 4],  # bottom
        [2, 3, 7], [2, 7, 6],  # top
        [0, 4, 7], [0, 7, 3],  # left
        [1, 2, 6], [1, 6, 5],  # right
    ], dtype=np.int32)

    # Slightly vary shade per face for depth cue
    c = np.array(color[:3], dtype=float)
    shades = [0.7, 0.7, 0.55, 1.0, 0.85, 0.85, 0.85, 0.85, 0.8, 0.8, 0.9, 0.9]
    colors = np.array([
        [int(c[0] * s), int(c[1] * s), int(c[2] * s), color[3]] for s in shades
    ], dtype=np.uint8)

    return v, f, colors


def _topdown(verts):
    """Top-down projection: X→right, Z→up, Y→depth (higher Y = closer to camera)."""
    return verts[:, 0].copy(), verts[:, 2].copy(), verts[:, 1].copy()


def _isometric(verts, azimuth_deg=45, elevation_deg=35):
    """Isometric projection with rotation around Y axis and tilt."""
    az = np.radians(azimuth_deg)
    el = np.radians(elevation_deg)
    cos_a, sin_a = np.cos(az), np.sin(az)
    cos_e, sin_e = np.cos(el), np.sin(el)

    # Rotate around Y
    x_rot = verts[:, 0] * cos_a + verts[:, 2] * sin_a
    z_rot = -verts[:, 0] * sin_a + verts[:, 2] * cos_a

    # Tilt
    x_screen = x_rot
    y_screen = verts[:, 1] * cos_e - z_rot * sin_e
    depth = verts[:, 1] * sin_e + z_rot * cos_e

    return x_screen, y_screen, depth


def _render_view(all_verts, all_faces, all_colors, project_fn, resolution, label=""):
    """Render using painter's algorithm with Pillow."""
    x, y, depth = project_fn(all_verts)

    # Scale to fit canvas
    margin = 30
    uw = resolution[0] - 2 * margin
    uh = resolution[1] - 2 * margin
    x_min, x_max = x.min(), x.max()
    y_min, y_max = y.min(), y.max()
    x_range = max(x_max - x_min, 0.01)
    y_range = max(y_max - y_min, 0.01)
    scale = min(uw / x_range, uh / y_range)

    sx = (x - x_min) * scale + margin + (uw - x_range * scale) / 2
    sy = resolution[1] - ((y - y_min) * scale + margin + (uh - y_range * scale) / 2)

    # Sort faces by depth (far first = painter's algorithm)
    face_depths = depth[all_faces].mean(axis=1)
    order = np.argsort(face_depths)

    img = Image.new("RGBA", resolution, _BG)
    draw = ImageDraw.Draw(img)

    for fi in order:
        f = all_faces[fi]
        pts = [(float(sx[f[j]]), float(sy[f[j]])) for j in range(3)]

        # Skip tiny triangles
        dx = max(abs(pts[0][0] - pts[1][0]), abs(pts[0][0] - pts[2][0]))
        dy = max(abs(pts[0][1] - pts[1][1]), abs(pts[0][1] - pts[2][1]))
        if dx < 1.5 and dy < 1.5:
            continue

        c = all_colors[fi]
        fill = (int(c[0]), int(c[1]), int(c[2]), int(c[3]) if len(c) > 3 else 255)
        draw.polygon(pts, fill=fill)

    # Label
    if label:
        try:
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 14)
        except OSError:
            font = ImageFont.load_default()
        draw.text((margin, 8), label, fill=(46, 46, 56, 200), font=font)

    return img


def _img_to_data_url(img: Image.Image) -> str:
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return f"data:image/png;base64,{base64.b64encode(buf.getvalue()).decode()}"


async def render_scene_3d_views(
    room_glb_url: str,
    placements: list,
    furniture: list,
    all_rooms: list | None = None,
    target_width: float = 6.8,
    target_length: float = 8.0,
    resolution: tuple[int, int] = (800, 600),
) -> list[str]:
    """Download room GLB, scale to apartment footprint, add furniture boxes, render.

    Args:
        room_glb_url: URL of the Trellis-generated room GLB.
        placements: List of FurniturePlacement objects.
        furniture: List of FurnitureItem objects.
        all_rooms: All rooms in the apartment (used to compute footprint).
        target_width: Apartment width in metres (X axis).
        target_length: Apartment length in metres (Z axis).
        resolution: Image resolution (width, height).

    Returns list of PNG data-URL strings.
    """
    import trimesh

    # Compute actual apartment footprint from all rooms
    if all_rooms:
        target_width = max((r.x_offset_m + r.width_m) for r in all_rooms)
        target_length = max((r.z_offset_m + r.length_m) for r in all_rooms)

    # Download GLB
    async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
        resp = await client.get(room_glb_url)
        resp.raise_for_status()

    # Load and concatenate meshes
    scene = trimesh.load(io.BytesIO(resp.content), file_type="glb")
    if isinstance(scene, trimesh.Scene):
        mesh = scene.dump(concatenate=True)
    else:
        mesh = scene

    all_verts = mesh.vertices.astype(np.float32)
    all_faces = mesh.faces.astype(np.int32)

    # Extract face colors
    if hasattr(mesh.visual, "face_colors") and mesh.visual.face_colors is not None:
        all_colors = np.array(mesh.visual.face_colors, dtype=np.uint8)
    else:
        all_colors = np.full((len(all_faces), 4), [210, 200, 190, 255], dtype=np.uint8)

    # Scale GLB to match apartment footprint (same logic as frontend RoomGLBModel)
    bbox_min = all_verts.min(axis=0)
    bbox_max = all_verts.max(axis=0)
    size = bbox_max - bbox_min
    if size[0] > 0.01 and size[2] > 0.01:
        sx = target_width / size[0]
        sz = target_length / size[2]
        sy = max(sx, sz)
        all_verts[:, 0] = (all_verts[:, 0] - bbox_min[0]) * sx
        all_verts[:, 1] = (all_verts[:, 1] - bbox_min[1]) * sy
        all_verts[:, 2] = (all_verts[:, 2] - bbox_min[2]) * sz
        logger.info(
            "Scaled GLB from %.2fx%.2f to %.1fx%.1fm",
            size[0], size[2], target_width, target_length,
        )

    # Subsample faces if too many (keep rendering under ~5s)
    max_faces = 40000
    if len(all_faces) > max_faces:
        indices = np.random.default_rng(42).choice(len(all_faces), max_faces, replace=False)
        indices.sort()
        all_faces = all_faces[indices]
        all_colors = all_colors[indices]
        logger.info("Subsampled to %d faces for rendering", max_faces)

    # Build dims lookup
    dims_map = {f.id: f.dimensions for f in furniture}

    # Add furniture boxes
    for i, p in enumerate(placements):
        dims = dims_map.get(p.item_id)
        if dims:
            w, d, h = dims.width_cm / 100, dims.depth_cm / 100, dims.height_cm / 100
        else:
            w = d = h = 0.5

        color = _FURN_COLORS[i % len(_FURN_COLORS)]
        center = (p.position.x, p.position.y + h / 2, p.position.z)

        bv, bf, bc = _box_mesh(center, (w, h, d), color)
        offset = len(all_verts)
        all_verts = np.vstack([all_verts, bv])
        all_faces = np.vstack([all_faces, bf + offset])
        all_colors = np.vstack([all_colors, bc])

    # Render views
    views = [
        (lambda v: _topdown(v), "Top-Down View"),
        (lambda v: _isometric(v, azimuth_deg=-45, elevation_deg=35), "View from South-West"),
        (lambda v: _isometric(v, azimuth_deg=45, elevation_deg=35), "View from South-East"),
        (lambda v: _isometric(v, azimuth_deg=135, elevation_deg=35), "View from North-East"),
    ]

    data_urls: list[str] = []
    for proj_fn, label in views:
        try:
            img = _render_view(all_verts, all_faces, all_colors, proj_fn, resolution, label)
            data_urls.append(_img_to_data_url(img))
        except Exception as e:
            logger.warning("Failed to render %s: %s", label, e)

    return data_urls
