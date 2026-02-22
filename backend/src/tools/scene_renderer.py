"""3D scene renderer — headless Three.js via Playwright for textured GLB rendering.

Renders room + furniture GLBs with full PBR textures and semi-transparent
bounding boxes. Uses Playwright (headless Chromium) with the same Three.js
pipeline as the frontend for pixel-accurate results.
"""

import asyncio
import base64
import io
import logging
import os

import httpx
from PIL import Image, ImageDraw, ImageFont

logger = logging.getLogger(__name__)

_FURN_COLORS_HEX = [
    "#db504a", "#7c8c6e", "#4a90d9", "#d4a037",
    "#8e44ad", "#27ae60", "#e67e22", "#2c3e50",
    "#e74c3c", "#1abc9c", "#f39c12", "#9b59b6",
]

# ---------------------------------------------------------------------------
# HTML template — self-contained Three.js scene with GLTFLoader + DRACOLoader
# ---------------------------------------------------------------------------
_HTML_TEMPLATE = """\
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>body{margin:0;overflow:hidden;background:#e0e4ea}</style>
<script type="importmap">
{
  "imports": {
    "three": "https://cdn.jsdelivr.net/npm/three@0.169.0/build/three.module.js",
    "three/addons/": "https://cdn.jsdelivr.net/npm/three@0.169.0/examples/jsm/"
  }
}
</script>
</head>
<body>
<script type="module">
import * as THREE from 'three';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { DRACOLoader } from 'three/addons/loaders/DRACOLoader.js';

window.initScene = async function(config) {
  const W = config.width || 800;
  const H = config.height || 600;

  const renderer = new THREE.WebGLRenderer({
    antialias: true,
    preserveDrawingBuffer: true,
    alpha: false,
  });
  renderer.setSize(W, H);
  renderer.setPixelRatio(1);
  renderer.outputColorSpace = THREE.SRGBColorSpace;
  renderer.toneMapping = THREE.ACESFilmicToneMapping;
  renderer.toneMappingExposure = 1.2;
  renderer.shadowMap.enabled = true;
  renderer.shadowMap.type = THREE.PCFSoftShadowMap;
  document.body.appendChild(renderer.domElement);

  const scene = new THREE.Scene();
  scene.background = new THREE.Color(0xe0e4ea);

  // Lighting — warm interior
  scene.add(new THREE.AmbientLight(0xfaf9f7, 0.7));

  const key = new THREE.DirectionalLight(0xfffaf0, 1.0);
  key.position.set(5, 15, 5);
  key.castShadow = true;
  key.shadow.mapSize.set(1024, 1024);
  scene.add(key);

  const fill = new THREE.DirectionalLight(0xffffff, 0.4);
  fill.position.set(-3, 12, -2);
  scene.add(fill);

  const top = new THREE.DirectionalLight(0xffffff, 0.5);
  top.position.set(3, 20, 4);
  scene.add(top);

  scene.add(new THREE.HemisphereLight(0xfef3c7, 0x1e1b4b, 0.3));

  // Loader
  const loader = new GLTFLoader();
  const draco = new DRACOLoader();
  draco.setDecoderPath('https://www.gstatic.com/draco/versioned/decoders/1.5.7/');
  loader.setDRACOLoader(draco);

  const tw = config.targetWidth;
  const tl = config.targetLength;

  // --- Load room GLB ---
  try {
    const roomGltf = await loader.loadAsync('/assets/room.glb');
    const rm = roomGltf.scene;
    rm.traverse(c => { if (c.isMesh) { c.receiveShadow = true; c.castShadow = true; } });

    const box = new THREE.Box3().setFromObject(rm);
    const sz = new THREE.Vector3();
    box.getSize(sz);
    if (sz.x > 0.01 && sz.z > 0.01) {
      const sX = tw / sz.x;
      const sZ = tl / sz.z;
      const sY = Math.max(sX, sZ);
      rm.scale.set(sX, sY, sZ);
      const sb = new THREE.Box3().setFromObject(rm);
      rm.position.x -= sb.min.x;
      rm.position.y -= sb.min.y;
      rm.position.z -= sb.min.z;
    }
    scene.add(rm);
  } catch (e) {
    console.error('Room GLB failed:', e);
  }

  // --- Load furniture ---
  for (const item of config.furniture) {
    const group = new THREE.Group();
    let loaded = false;

    if (item.glbPath) {
      try {
        const gltf = await loader.loadAsync(item.glbPath);
        const model = gltf.scene;
        model.traverse(c => {
          if (c.isMesh) { c.castShadow = true; c.receiveShadow = true; }
        });

        const fb = new THREE.Box3().setFromObject(model);
        const fs = new THREE.Vector3();
        fb.getSize(fs);
        const maxDim = Math.max(fs.x, fs.y, fs.z);

        if (maxDim > 0.001 && !item.isIkea && item.dims) {
          const maxExp = Math.max(item.dims.w, item.dims.d, item.dims.h);
          model.scale.setScalar(maxExp / maxDim);
        }

        const sb = new THREE.Box3().setFromObject(model);
        const ctr = new THREE.Vector3();
        sb.getCenter(ctr);
        model.position.y -= sb.min.y;
        model.position.x -= ctr.x;
        model.position.z -= ctr.z;

        // Measure actual bounding box AFTER scaling & centering
        const actualBox = new THREE.Box3().setFromObject(model);
        const actualSize = new THREE.Vector3();
        actualBox.getSize(actualSize);
        item._actualW = actualSize.x;
        item._actualH = actualSize.y;
        item._actualD = actualSize.z;

        group.add(model);
        loaded = true;
      } catch (e) {
        console.warn('Furniture GLB failed:', item.name, e);
      }
    }

    if (!loaded && item.dims) {
      const geo = new THREE.BoxGeometry(item.dims.w, item.dims.h, item.dims.d);
      const mat = new THREE.MeshStandardMaterial({
        color: item.colorHex,
        roughness: 0.7,
        metalness: 0.1,
      });
      const mesh = new THREE.Mesh(geo, mat);
      mesh.position.y = item.dims.h / 2;
      mesh.castShadow = true;
      group.add(mesh);
    }

    group.position.set(item.position.x, item.position.y, item.position.z);
    group.rotation.y = item.rotationY * Math.PI / 180;
    scene.add(group);

    // Semi-transparent bounding box overlay — use actual GLB size when available
    const bbW = item._actualW || (item.dims ? item.dims.w : 0.8);
    const bbH = item._actualH || (item.dims ? item.dims.h : 0.8);
    const bbD = item._actualD || (item.dims ? item.dims.d : 0.8);
    {
      const bbGroup = new THREE.Group();
      const bbGeo = new THREE.BoxGeometry(bbW, bbH, bbD);

      const bbMat = new THREE.MeshBasicMaterial({
        color: item.colorHex,
        transparent: true,
        opacity: 0.1,
        depthWrite: false,
        side: THREE.DoubleSide,
      });
      bbGroup.add(new THREE.Mesh(bbGeo, bbMat));

      const edges = new THREE.EdgesGeometry(bbGeo);
      const lineMat = new THREE.LineBasicMaterial({ color: item.colorHex });
      bbGroup.add(new THREE.LineSegments(edges, lineMat));

      bbGroup.position.set(
        item.position.x,
        item.position.y + bbH / 2,
        item.position.z
      );
      bbGroup.rotation.y = item.rotationY * Math.PI / 180;
      scene.add(bbGroup);
    }
  }

  // Ground plane (subtle shadow catcher)
  const ground = new THREE.Mesh(
    new THREE.PlaneGeometry(tw * 2, tl * 2),
    new THREE.ShadowMaterial({ opacity: 0.15 })
  );
  ground.rotation.x = -Math.PI / 2;
  ground.position.set(tw / 2, -0.01, tl / 2);
  ground.receiveShadow = true;
  scene.add(ground);

  // --- Coordinate grid on floor ---
  const gridGroup = new THREE.Group();
  const gridMat = new THREE.LineBasicMaterial({ color: 0x666666, transparent: true, opacity: 0.4 });
  const majorMat = new THREE.LineBasicMaterial({ color: 0x333333, transparent: true, opacity: 0.7 });

  const maxX = Math.ceil(tw);
  const maxZ = Math.ceil(tl);

  for (let x = 0; x <= maxX; x++) {
    const pts = [new THREE.Vector3(x, 0.015, 0), new THREE.Vector3(x, 0.015, maxZ)];
    gridGroup.add(new THREE.Line(new THREE.BufferGeometry().setFromPoints(pts), x % 2 === 0 ? majorMat : gridMat));
  }
  for (let z = 0; z <= maxZ; z++) {
    const pts = [new THREE.Vector3(0, 0.015, z), new THREE.Vector3(maxX, 0.015, z)];
    gridGroup.add(new THREE.Line(new THREE.BufferGeometry().setFromPoints(pts), z % 2 === 0 ? majorMat : gridMat));
  }
  scene.add(gridGroup);

  // Coordinate labels as sprites
  function makeCoordLabel(text, wx, wz) {
    const canvas = document.createElement('canvas');
    canvas.width = 128; canvas.height = 64;
    const ctx = canvas.getContext('2d');
    ctx.fillStyle = 'rgba(255,255,255,0.85)';
    ctx.roundRect(4, 4, 120, 56, 8);
    ctx.fill();
    ctx.fillStyle = '#222';
    ctx.font = 'bold 32px monospace';
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    ctx.fillText(text, 64, 32);
    const tex = new THREE.CanvasTexture(canvas);
    const mat = new THREE.SpriteMaterial({ map: tex });
    const sprite = new THREE.Sprite(mat);
    sprite.position.set(wx, 0.05, wz);
    sprite.scale.set(0.6, 0.3, 1);
    scene.add(sprite);
  }

  for (let x = 0; x <= maxX; x++) {
    makeCoordLabel(x + 'm', x, -0.35);
  }
  for (let z = 0; z <= maxZ; z++) {
    makeCoordLabel(z + 'm', -0.4, z);
  }

  // Axis arrows
  const xArrow = new THREE.ArrowHelper(
    new THREE.Vector3(1,0,0), new THREE.Vector3(0, 0.03, -0.7),
    Math.min(2, tw), 0xcc3333, 0.15, 0.1
  );
  scene.add(xArrow);
  makeCoordLabel('X(east)', 1.2, -0.7);

  const zArrow = new THREE.ArrowHelper(
    new THREE.Vector3(0,0,1), new THREE.Vector3(-0.7, 0.03, 0),
    Math.min(2, tl), 0x3333cc, 0.15, 0.1
  );
  scene.add(zArrow);
  makeCoordLabel('Z(north)', -0.7, 1.2);

  window._scene = scene;
  window._renderer = renderer;
  window._tw = tw;
  window._tl = tl;
  window._THREE = THREE;

  return true;
};

window.captureView = function(azimuthDeg, elevationDeg, isParallel) {
  const scene = window._scene;
  const r = window._renderer;
  const tw = window._tw;
  const tl = window._tl;
  const THREE = window._THREE;

  const cx = tw / 2;
  const cz = tl / 2;
  const cy = 1.4;
  const radius = Math.max(tw, tl) * 1.6;

  let camera;
  if (isParallel) {
    const aspect = r.domElement.width / r.domElement.height;
    const frust = Math.max(tw, tl) * 1.15;
    camera = new THREE.OrthographicCamera(
      -frust * aspect / 2, frust * aspect / 2,
      frust / 2, -frust / 2, 0.1, 100
    );
    camera.position.set(cx, 25, cz);
    camera.lookAt(cx, 0, cz);
  } else {
    camera = new THREE.PerspectiveCamera(
      45, r.domElement.width / r.domElement.height, 0.1, 100
    );
    const az = azimuthDeg * Math.PI / 180;
    const el = elevationDeg * Math.PI / 180;
    camera.position.set(
      cx + radius * Math.cos(el) * Math.sin(az),
      cy + radius * Math.sin(el),
      cz + radius * Math.cos(el) * Math.cos(az)
    );
    camera.lookAt(cx, cy * 0.3, cz);
  }

  r.render(scene, camera);
  return r.domElement.toDataURL('image/jpeg', 0.8);
};

window._ready = true;
</script>
</body>
</html>
"""


def _get_font(size: int = 16):
    try:
        return ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", size)
    except OSError:
        try:
            return ImageFont.truetype("/System/Library/Fonts/Menlo.ttc", size)
        except OSError:
            return ImageFont.load_default()


def _add_label(img: Image.Image, label: str) -> Image.Image:
    """Overlay a label on the top-left of an image."""
    draw = ImageDraw.Draw(img)
    font = _get_font(16)
    tw = len(label) * 9 + 16
    draw.rectangle([(8, 6), (8 + tw, 26)], fill=(250, 249, 247))
    draw.text((12, 8), label, fill=(46, 46, 56), font=font)
    return img


def _add_coordinate_grid(
    img: Image.Image,
    target_width: float,
    target_length: float,
) -> Image.Image:
    """Overlay a coordinate grid on the top-down orthographic view.

    Maps apartment-absolute coordinates to pixel positions based on the
    orthographic camera parameters used in captureView (parallel=true).
    """
    W, H = img.size
    aspect = W / H
    frust = max(target_width, target_length) * 1.15
    cx = target_width / 2
    cz = target_length / 2

    # World-to-pixel mapping for orthographic top-down view
    # Camera at (cx, 25, cz) looking straight down with default up=(0,1,0).
    # Three.js resolves the degenerate lookAt so that:
    #   camera right = +X (screen-right = world east)
    #   camera up ≈ (0, 0, -1) (screen-up = world south, i.e. Z+ goes DOWN)
    # So: px = (wx - cx) / (frust*aspect/2) * W/2 + W/2
    #     py = (wz - cz) / (frust/2) * H/2 + H/2  (Z+ toward image bottom)
    def world_to_px(wx: float, wz: float) -> tuple[int, int]:
        px = (wx - cx) / (frust * aspect / 2) * (W / 2) + W / 2
        py = (wz - cz) / (frust / 2) * (H / 2) + H / 2
        return int(px), int(py)

    draw = ImageDraw.Draw(img, "RGBA")
    font = _get_font(13)
    font_small = _get_font(11)

    max_x = int(target_width) + 1
    max_z = int(target_length) + 1

    # Draw grid lines
    grid_color = (100, 100, 100, 80)
    major_color = (60, 60, 60, 120)

    for x in range(max_x + 1):
        p1 = world_to_px(x, 0)
        p2 = world_to_px(x, max_z)
        color = major_color if x % 2 == 0 else grid_color
        draw.line([p1, p2], fill=color, width=1)

    for z in range(max_z + 1):
        p1 = world_to_px(0, z)
        p2 = world_to_px(max_x, z)
        color = major_color if z % 2 == 0 else grid_color
        draw.line([p1, p2], fill=color, width=1)

    # Draw coordinate labels
    label_bg = (255, 255, 255, 200)
    label_fg = (30, 30, 30)

    # X axis labels along the south wall (z=0, top of image)
    for x in range(max_x + 1):
        px, py_top = world_to_px(x, 0)
        text = f"{x}m"
        draw.rectangle([(px - 14, py_top - 18), (px + 14, py_top - 2)], fill=label_bg)
        draw.text((px - 10, py_top - 17), text, fill=label_fg, font=font_small)

    # Z axis labels along the west wall (x=0, left of image), top-to-bottom = south-to-north
    for z in range(max_z + 1):
        px_left, py = world_to_px(0, z)
        text = f"{z}m"
        draw.rectangle([(px_left - 30, py - 8), (px_left - 2, py + 8)], fill=label_bg)
        draw.text((px_left - 28, py - 7), text, fill=label_fg, font=font_small)

    # Axis indicators
    origin = world_to_px(0, 0)
    x_end = world_to_px(1.5, 0)
    z_end = world_to_px(0, 1.5)
    draw.line([origin, x_end], fill=(200, 50, 50, 200), width=2)
    draw.text((x_end[0] + 2, x_end[1] - 6), "X(E)", fill=(200, 50, 50), font=font_small)
    draw.line([origin, z_end], fill=(50, 50, 200, 200), width=2)
    draw.text((z_end[0] + 2, z_end[1] - 6), "Z(N)", fill=(50, 50, 200), font=font_small)

    return img


def _data_url_to_image(data_url: str) -> Image.Image:
    """Convert a data URL to a PIL Image."""
    b64 = data_url.split(",", 1)[1]
    return Image.open(io.BytesIO(base64.b64decode(b64)))


def _img_to_data_url(img: Image.Image) -> str:
    buf = io.BytesIO()
    img = img.convert("RGB")
    img.save(buf, format="JPEG", quality=85)
    return f"data:image/jpeg;base64,{base64.b64encode(buf.getvalue()).decode()}"


def _is_ikea_url(url: str) -> bool:
    return "ikea.com" in url or "ikea-static" in url


async def render_scene_3d_views(
    room_glb_url: str,
    placements: list,
    furniture: list,
    all_rooms: list | None = None,
    target_width: float = 6.8,
    target_length: float = 8.0,
    resolution: tuple[int, int] = (400, 300),
) -> list[str]:
    """Render room GLB + textured furniture with transparent bounding boxes.

    Uses headless Chromium via Playwright with Three.js — same rendering
    pipeline as the frontend, preserving full PBR textures.

    Returns list of PNG data-URL strings (4 views).
    """
    from playwright.async_api import async_playwright

    if all_rooms:
        target_width = max((r.x_offset_m + r.width_m) for r in all_rooms)
        target_length = max((r.z_offset_m + r.length_m) for r in all_rooms)

    dims_map = {f.id: f.dimensions for f in furniture}

    # --- Download all GLBs concurrently ---
    assets: dict[str, bytes] = {}

    async def _dl(client: httpx.AsyncClient, key: str, url: str) -> None:
        try:
            r = await client.get(url, headers={
                "User-Agent": "Mozilla/5.0 (compatible; HomeDesigner/1.0)"
            })
            r.raise_for_status()
            assets[key] = r.content
            logger.info("Downloaded %s (%d KB)", key, len(r.content) // 1024)
        except Exception as e:
            logger.warning("GLB download failed %s: %s", key, e)

    async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
        tasks = [_dl(client, "room.glb", room_glb_url)]
        for i, f in enumerate(furniture):
            glb_url = getattr(f, "glb_url", "")
            if glb_url:
                tasks.append(_dl(client, f"furn_{f.id}.glb", glb_url))
        await asyncio.gather(*tasks)

    if "room.glb" not in assets:
        logger.error("Room GLB download failed, cannot render")
        return []

    # --- Build scene config for Three.js ---
    furn_config = []
    for i, p in enumerate(placements):
        dims = dims_map.get(p.item_id)
        glb_url = ""
        for f in furniture:
            if f.id == p.item_id:
                glb_url = getattr(f, "glb_url", "")
                break

        glb_key = f"furn_{p.item_id}.glb"
        has_glb = glb_key in assets

        d = None
        if dims:
            d = {
                "w": dims.width_cm / 100,
                "d": dims.depth_cm / 100,
                "h": dims.height_cm / 100,
            }

        furn_config.append({
            "glbPath": f"/assets/{glb_key}" if has_glb else None,
            "name": getattr(p, "name", ""),
            "position": {"x": p.position.x, "y": p.position.y, "z": p.position.z},
            "rotationY": p.rotation_y_degrees,
            "dims": d or {"w": 0.8, "d": 0.8, "h": 0.8},
            "colorHex": _FURN_COLORS_HEX[i % len(_FURN_COLORS_HEX)],
            "isIkea": _is_ikea_url(glb_url) if glb_url else False,
        })

    scene_config = {
        "width": resolution[0],
        "height": resolution[1],
        "targetWidth": target_width,
        "targetLength": target_length,
        "furniture": furn_config,
    }

    # --- Render via Playwright ---
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        page = await browser.new_page(viewport={
            "width": resolution[0], "height": resolution[1],
        })

        # Single catch-all route — intercepts navigation + asset requests,
        # passes CDN requests (Three.js, Draco) through to the network.
        async def _route_handler(route):
            url = route.request.url
            if "render.local" in url and url.endswith("index.html"):
                await route.fulfill(body=_HTML_TEMPLATE, content_type="text/html")
            elif "render.local" in url and "/assets/" in url:
                key = url.split("/assets/")[1]
                if key in assets:
                    await route.fulfill(
                        body=assets[key],
                        content_type="model/gltf-binary",
                    )
                else:
                    await route.abort("blockedbyclient")
            else:
                await route.continue_()

        await page.route("**/*", _route_handler)
        await page.goto("http://render.local/index.html")

        # Wait for Three.js modules to load
        await page.wait_for_function("window._ready === true", timeout=15000)

        # Initialize scene (loads all GLBs — async JS function)
        import json
        logger.info("Initializing Three.js scene with %d furniture items", len(furn_config))
        config_json = json.dumps(scene_config)
        await page.evaluate(f"window.initScene({config_json}).then(() => {{ window._sceneReady = true; }})")
        await page.wait_for_function("window._sceneReady === true", timeout=60000)
        # Give GPU a moment to finish rendering
        await page.wait_for_timeout(500)

        # Capture 4 views
        views = [
            {"az": 0, "el": 89, "label": "Top-Down View", "parallel": True},
            {"az": -45, "el": 35, "label": "View from South-West", "parallel": False},
            {"az": 45, "el": 35, "label": "View from South-East", "parallel": False},
            {"az": 135, "el": 35, "label": "View from North-East", "parallel": False},
        ]

        data_urls: list[str] = []
        for v in views:
            try:
                raw_url = await page.evaluate(
                    f"window.captureView({v['az']}, {v['el']}, {'true' if v['parallel'] else 'false'})"
                )
                img = _data_url_to_image(raw_url)
                # Add coordinate grid overlay to top-down view
                if v.get("parallel"):
                    img = _add_coordinate_grid(img, target_width, target_length)
                img = _add_label(img, v["label"])
                data_urls.append(_img_to_data_url(img))
            except Exception as e:
                logger.warning("Capture failed %s: %s", v["label"], e)

        await browser.close()

    logger.info("Rendered %d Playwright views at %dx%d", len(data_urls), *resolution)
    return data_urls
