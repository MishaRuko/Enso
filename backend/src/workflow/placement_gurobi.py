"""Gurobi-based furniture placement — runs Misha's pipeline step by step.

Breaks the monolithic run_pipeline() into individual calls so we can update
the job trace and session status at each stage, giving the frontend granular
progress (colored image, furniture list, placement result).
"""

import asyncio
import json
import logging
import tempfile
import time
from pathlib import Path

import httpx

from .. import db

logger = logging.getLogger(__name__)

# Nano Banana prompt (matches pipeline.py)
_NANO_BANANA_PROMPT = (
    "This is a floor plan. Fill each individual/distinct room with a different "
    "bright solid colour. Keep the walls black. Keep the coloured bits just solid "
    "inside, no black artefacts. Do not add, remove, or modify any walls or "
    "structural lines."
)


async def _download_floorplan(url: str, dest: Path) -> Path:
    """Download floorplan image from URL to a local file."""
    async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
        resp = await client.get(url)
        resp.raise_for_status()
    dest.write_bytes(resp.content)
    logger.info("Downloaded floorplan (%d bytes) → %s", len(resp.content), dest)
    return dest


async def _generate_room_glb(floorplan_path: str, session_id: str) -> str:
    """Upload floorplan to fal.ai, run Trellis 2 to get a room GLB. Returns GLB URL."""
    from ..tools.fal_client import generate_room_model, upload_to_fal

    image_bytes = Path(floorplan_path).read_bytes()
    content_type = "image/png" if floorplan_path.endswith(".png") else "image/jpeg"
    fal_image_url = await upload_to_fal(image_bytes, content_type)
    logger.info("Uploaded floorplan to fal: %s", fal_image_url)

    glb_url = await generate_room_model(fal_image_url)
    logger.info("Trellis room GLB: %s", glb_url)
    return glb_url


def _render_glb_to_binary(glb_path: str, output_path: str, resolution: int = 1024) -> str:
    """Render a GLB to a top-down binary floorplan image using trimesh + OpenCV.

    Replicates Misha's Blender pipeline: load GLB → orthographic top-down
    depth render → threshold to get black walls on white background.

    Uses vectorized numpy + OpenCV fillPoly for fast rasterization.
    """
    import cv2
    import numpy as np
    import trimesh

    scene = trimesh.load(glb_path)

    if isinstance(scene, trimesh.Scene):
        meshes = list(scene.dump())
        if not meshes:
            raise ValueError("GLB contains no geometry")
        mesh = trimesh.util.concatenate(meshes)
    else:
        mesh = scene

    bounds = mesh.bounds
    extent = bounds[1] - bounds[0]

    # Clip at 75% height (remove ceiling), matching Misha's --clip-height 75.0
    clip_y = bounds[0][1] + 0.75 * extent[1]

    verts = mesh.vertices
    faces = mesh.faces

    # Filter faces: keep those with at least one vertex below clip height
    face_verts_y = verts[faces, 1]  # (N_faces, 3) — Y coord per vertex
    face_mask = np.any(face_verts_y <= clip_y, axis=1)
    kept_faces = faces[face_mask]

    # Grid covering the XZ extent
    x_min, x_max = bounds[0][0], bounds[1][0]
    z_min, z_max = bounds[0][2], bounds[1][2]
    x_range = x_max - x_min
    z_range = z_max - z_min
    if x_range < 1e-6 or z_range < 1e-6:
        raise ValueError("GLB has zero extent in XZ plane")

    aspect = z_range / x_range
    w = resolution
    h = max(1, int(resolution * aspect))

    # Project all vertices to pixel coords (XZ plane → image)
    px_all = ((verts[:, 0] - x_min) / x_range * (w - 1)).astype(np.int32)
    py_all = ((verts[:, 2] - z_min) / z_range * (h - 1)).astype(np.int32)
    px_all = np.clip(px_all, 0, w - 1)
    py_all = np.clip(py_all, 0, h - 1)

    # Per-face minimum Y (height) as the "depth" value for that triangle
    face_min_y = np.min(verts[kept_faces, 1], axis=1)

    # Rasterize with OpenCV fillPoly: paint each triangle with its depth index
    # Sort faces by depth (tallest = lowest Y first) so shorter structures overwrite
    depth_order = np.argsort(face_min_y)

    # Quantize depths into 256 levels for an 8-bit depth buffer
    if len(face_min_y) == 0:
        cv2.imwrite(output_path, np.ones((h, w), dtype=np.uint8) * 255)
        return output_path

    y_min, y_max = face_min_y.min(), face_min_y.max()
    y_range = y_max - y_min if (y_max - y_min) > 1e-6 else 1.0
    depth_vals = ((face_min_y - y_min) / y_range * 254).astype(np.uint8) + 1  # 1..255

    # Paint depth map: background = 0, geometry = 1..255
    depth_map = np.zeros((h, w), dtype=np.uint8)
    for idx in depth_order:
        f = kept_faces[idx]
        pts = np.array([[px_all[f[0]], py_all[f[0]]],
                         [px_all[f[1]], py_all[f[1]]],
                         [px_all[f[2]], py_all[f[2]]]], dtype=np.int32)
        cv2.fillPoly(depth_map, [pts], int(depth_vals[idx]))

    # Threshold: walls are the tallest structures (lowest Y = lowest depth_val)
    has_geometry = depth_map > 0
    if not np.any(has_geometry):
        binary = np.ones((h, w), dtype=np.uint8) * 255
    else:
        # Wall threshold at 25% of the depth range (shortest structures)
        wall_thresh = int(0.25 * 254) + 1
        binary = np.ones((h, w), dtype=np.uint8) * 255  # white background
        binary[(depth_map > 0) & (depth_map <= wall_thresh)] = 0  # black walls

    # Morphological cleanup
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
    inverted = 255 - binary
    inverted = cv2.morphologyEx(inverted, cv2.MORPH_CLOSE, kernel, iterations=2)
    inverted = cv2.morphologyEx(inverted, cv2.MORPH_OPEN, kernel, iterations=1)
    binary = 255 - inverted

    cv2.imwrite(output_path, binary)
    logger.info("Binary floorplan rendered: %s (%dx%d)", output_path, w, h)
    return output_path


async def _download_glb(url: str, dest: Path) -> Path:
    """Download a GLB file from URL."""
    async with httpx.AsyncClient(timeout=60, follow_redirects=True) as client:
        resp = await client.get(url)
        resp.raise_for_status()
    dest.write_bytes(resp.content)
    logger.info("Downloaded GLB (%d bytes) → %s", len(resp.content), dest)
    return dest


def _trace(*events: dict) -> list[dict]:
    return list(events)


async def place_furniture_gurobi(session_id: str, job_id: str) -> dict:
    """Run Misha's full Gurobi pipeline step by step.

    Matches Misha's CLI exactly:
    0. Upload floorplan → Trellis 2 → room GLB (3D model)
    1. Render GLB to binary floorplan (top-down depth → threshold)
    2. Nano Banana coloring on the clean binary image
    3. Build grid from colored image
    4. Claude furniture specs
    5. IKEA product search → save furniture items
    6. Claude constraints
    7. Gurobi optimizer
    8. 3D coordinate conversion + Trellis models
    9. Save results back to session
    """
    try:
        db.update_job(job_id, {"status": "running", "trace": [{"step": "started"}]})

        session = db.get_session(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")

        floorplan_url = session.get("floorplan_url")
        if not floorplan_url:
            raise ValueError(f"Session {session_id} has no floorplan_url")

        prefs = session.get("preferences") or {}
        style = prefs.get("style", "modern scandinavian")
        budget = prefs.get("budget_max", 5000)

        with tempfile.TemporaryDirectory(prefix="enso_gurobi_") as tmpdir:
            tmp = Path(tmpdir)

            # --- Step 0: Download floorplan ---
            db.update_session(session_id, {"status": "analyzing_floorplan"})
            db.update_job(job_id, {"trace": _trace(
                {"step": "started"},
                {"step": "downloading_floorplan", "message": "Downloading floorplan"},
            )})

            ext = floorplan_url.rsplit(".", 1)[-1].split("?")[0] if "." in floorplan_url else "png"
            floorplan_path = tmp / f"floorplan.{ext}"
            await _download_floorplan(floorplan_url, floorplan_path)

            # --- Step 1: Generate room GLB via Trellis 2 ---
            db.update_job(job_id, {"trace": _trace(
                {"step": "started"},
                {"step": "downloading_floorplan", "duration_ms": 1},
                {"step": "trellis_room", "message": "Generating 3D room model (Trellis 2)",
                 "input_image": floorplan_url, "model": "fal-ai/trellis-2"},
            )})

            t0 = time.time()
            room_glb_url = await _generate_room_glb(str(floorplan_path), session_id)
            trellis_room_ms = round((time.time() - t0) * 1000)

            # Save room GLB URL to session
            db.update_session(session_id, {"room_glb_url": room_glb_url})

            # --- Step 1b: Render GLB → binary floorplan ---
            db.update_job(job_id, {"trace": _trace(
                {"step": "started", "duration_ms": 1},
                {"step": "downloading_floorplan", "duration_ms": 1},
                {"step": "trellis_room", "message": "Room GLB generated", "duration_ms": trellis_room_ms,
                 "input_image": floorplan_url, "model": "fal-ai/trellis-2"},
                {"step": "render_binary", "message": "Rendering GLB to binary floorplan"},
            )})

            t0 = time.time()
            glb_local = tmp / "room.glb"
            await _download_glb(room_glb_url, glb_local)
            binary_path = str(tmp / "binary_floorplan.png")
            await asyncio.to_thread(_render_glb_to_binary, str(glb_local), binary_path)
            render_ms = round((time.time() - t0) * 1000)

            # Upload binary image for trace display
            binary_bytes = Path(binary_path).read_bytes()
            binary_url = db.upload_to_storage(
                "floorplans", f"{session_id}/binary.png", binary_bytes, "image/png",
            )

            # --- Step 2: Nano Banana coloring on the CLEAN binary image ---
            db.update_job(job_id, {"trace": _trace(
                {"step": "started", "duration_ms": 1},
                {"step": "trellis_room", "duration_ms": trellis_room_ms,
                 "input_image": floorplan_url, "model": "fal-ai/trellis-2"},
                {"step": "render_binary", "message": "Binary floorplan ready", "duration_ms": render_ms,
                 "image_url": binary_url},
                {"step": "nano_banana", "message": "Coloring rooms with Nano Banana",
                 "input_image": binary_url,
                 "input_prompt": _NANO_BANANA_PROMPT,
                 "model": "google/gemini-3-pro-image-preview"},
            )})

            from ..furniture_placement.furniture_agents import (
                _CONSTRAINT_PROMPT,
                _CONSTRAINT_SYSTEM,
                _FURNITURE_SPEC_PROMPT,
                _FURNITURE_SPEC_SYSTEM,
                _format_preferences,
                _furniture_info_for_prompt,
                _generate_constraints_impl,
                _generate_specs_impl,
                _room_info_for_prompt,
                constraints_to_optimizer_format,
                specs_to_optimizer_format,
                specs_to_search_queries,
                update_specs_from_search_results,
            )
            from ..furniture_placement.pipeline import (
                _color_rooms_with_nano_banana,
                _make_llm_caller,
                build_grid_from_colored_image,
            )

            t0 = time.time()
            colored_path = str(tmp / "colored.png")
            await _color_rooms_with_nano_banana(binary_path, colored_path)
            nano_ms = round((time.time() - t0) * 1000)

            # Upload colored image so the frontend can show it
            colored_bytes = Path(colored_path).read_bytes()
            colored_url = db.upload_to_storage(
                "floorplans", f"{session_id}/colored.png", colored_bytes, "image/png",
            )

            db.update_job(job_id, {"trace": _trace(
                {"step": "started", "duration_ms": 1},
                {"step": "trellis_room", "duration_ms": trellis_room_ms, "model": "fal-ai/trellis-2"},
                {"step": "render_binary", "duration_ms": render_ms, "image_url": binary_url},
                {"step": "nano_banana", "message": "Rooms colored", "duration_ms": nano_ms,
                 "input_image": binary_url, "image_url": colored_url,
                 "input_prompt": _NANO_BANANA_PROMPT,
                 "model": "google/gemini-3-pro-image-preview"},
                {"step": "grid_building", "message": "Building placement grid"},
            )})

            # --- Step 3: Build grid (CPU-bound, run in thread) ---
            t0 = time.time()
            grid = await asyncio.to_thread(build_grid_from_colored_image, colored_path, 12.0, 0.25)
            grid_ms = round((time.time() - t0) * 1000)

            room_summary = ", ".join(
                f"{n} ({grid.room_area_sqm(n):.0f}m²)" for n in grid.room_names
            )

            # Build the spec prompt so we can include it in the trace
            room_info = _room_info_for_prompt(grid)
            preferences = {
                "style": style,
                "budget_max": budget,
                "currency": "EUR",
                "colors": ["warm neutrals", "wood tones"],
                "lifestyle": ["work from home", "couple"],
            }
            pref_info = _format_preferences(preferences)
            spec_prompt = _FURNITURE_SPEC_PROMPT.format(
                room_info=room_info, preferences_info=pref_info,
            )

            db.update_job(job_id, {"trace": _trace(
                {"step": "started", "duration_ms": 1},
                {"step": "nano_banana", "duration_ms": nano_ms, "image_url": colored_url,
                 "input_image": binary_url, "model": "google/gemini-3-pro-image-preview"},
                {"step": "grid_ready", "message": f"{grid.width}×{grid.height} grid, {grid.num_rooms} rooms: {room_summary}", "duration_ms": grid_ms},
                {"step": "furniture_specs", "message": "Generating furniture list (Claude)",
                 "input_prompt": spec_prompt,
                 "model": "anthropic/claude-sonnet-4-6"},
            )})

            # --- Step 4: Furniture specs (Claude) ---
            db.update_session(session_id, {"status": "searching"})

            # Wrap llm_call to capture raw response text
            llm_traces: dict[str, str] = {}
            raw_llm_call = _make_llm_caller()

            async def tracing_llm_call(system: str, user: str, temperature: float) -> str:
                result = await raw_llm_call(system, user, temperature)
                llm_traces[system[:40]] = result
                return result

            t0 = time.time()
            specs = await _generate_specs_impl(grid, preferences, tracing_llm_call)
            specs_ms = round((time.time() - t0) * 1000)
            total_items = sum(len(v) for v in specs.values())

            # Get the raw LLM output for the spec agent
            spec_output = llm_traces.get(_FURNITURE_SPEC_SYSTEM[:40], "")
            specs_summary = json.dumps(
                {room: [i.name for i in items] for room, items in specs.items()},
                indent=2,
            )

            db.update_job(job_id, {"trace": _trace(
                {"step": "started", "duration_ms": 1},
                {"step": "nano_banana", "duration_ms": nano_ms, "image_url": colored_url,
                 "input_image": binary_url, "model": "google/gemini-3-pro-image-preview"},
                {"step": "grid_ready", "duration_ms": grid_ms},
                {"step": "furniture_specs", "message": f"{total_items} furniture items specified",
                 "duration_ms": specs_ms, "model": "anthropic/claude-sonnet-4-6",
                 "input_prompt": spec_prompt,
                 "output_text": spec_output[:3000]},
                {"step": "searching_ikea", "message": "Searching IKEA catalog"},
            )})

            # --- Step 5: IKEA search ---
            from ..tools.ikea.search import ikea_results_to_spec_updates, search_ikea_products

            t0 = time.time()
            ikea_results = await search_ikea_products(specs)
            ikea_ms = round((time.time() - t0) * 1000)
            found = sum(1 for r in ikea_results if r.get("found"))
            with_glb = sum(1 for r in ikea_results if r.get("glb_url"))

            spec_updates = ikea_results_to_spec_updates(ikea_results)
            if spec_updates:
                update_specs_from_search_results(specs, spec_updates)

            ikea_lookup: dict[tuple[str, str], dict] = {}
            for r in ikea_results:
                if r.get("found"):
                    ikea_lookup[(r["room_name"], r["name"])] = r

            search_queries = specs_to_search_queries(specs, preferences)

            # Save furniture items to DB so the sidebar shows them during processing
            for r in ikea_results:
                if not r.get("found"):
                    continue
                try:
                    db.upsert_furniture({
                        "id": r.get("ikea_item_code") or f"{r['room_name']}_{r['name']}",
                        "session_id": session_id,
                        "retailer": "ikea",
                        "name": r.get("ikea_name") or r["name"],
                        "price": r.get("price") or 0,
                        "currency": r.get("currency") or "EUR",
                        "image_url": r.get("image_url", ""),
                        "product_url": r.get("buy_url", ""),
                        "glb_url": r.get("glb_url", ""),
                        "category": r.get("room_name", ""),
                        "dimensions": {
                            "width_cm": (r.get("width_cm") or 0),
                            "depth_cm": (r.get("depth_cm") or 0),
                            "height_cm": (r.get("height_cm") or 0),
                        },
                        "selected": True,
                    })
                except Exception:
                    logger.debug("Failed to upsert IKEA item %s", r.get("name"))

            # IKEA summary for trace output
            ikea_summary = "\n".join(
                f"{'✓' if r.get('found') else '✗'} [{r['room_name']}] {r['name']}"
                + (f" → {r.get('ikea_name', '')} €{r.get('price', 0):.0f}" if r.get("found") else "")
                + (" [GLB]" if r.get("glb_url") else "")
                for r in ikea_results
            )

            # Build constraint prompt for trace
            furn_info = _furniture_info_for_prompt(specs)
            constraint_prompt = _CONSTRAINT_PROMPT.format(
                room_info=room_info, furniture_info=furn_info,
            )

            db.update_job(job_id, {"trace": _trace(
                {"step": "started", "duration_ms": 1},
                {"step": "nano_banana", "duration_ms": nano_ms, "image_url": colored_url,
                 "input_image": binary_url, "model": "google/gemini-3-pro-image-preview"},
                {"step": "grid_ready", "duration_ms": grid_ms},
                {"step": "furniture_specs", "duration_ms": specs_ms, "model": "anthropic/claude-sonnet-4-6",
                 "input_prompt": spec_prompt, "output_text": spec_output[:3000]},
                {"step": "searching_ikea", "message": f"{found}/{len(ikea_results)} found, {with_glb} with 3D models",
                 "duration_ms": ikea_ms,
                 "input_prompt": specs_summary,
                 "output_text": ikea_summary},
                {"step": "constraints", "message": "Generating placement constraints (Claude)",
                 "input_prompt": constraint_prompt,
                 "model": "anthropic/claude-sonnet-4-6"},
            )})

            # --- Step 6: Constraints (Claude) ---
            db.update_session(session_id, {"status": "placing"})

            llm_traces.clear()
            t0 = time.time()
            constraints = await _generate_constraints_impl(grid, specs, preferences, tracing_llm_call)
            constraints_ms = round((time.time() - t0) * 1000)

            constraint_output = llm_traces.get(_CONSTRAINT_SYSTEM[:40], "")

            db.update_job(job_id, {"trace": _trace(
                {"step": "started", "duration_ms": 1},
                {"step": "nano_banana", "duration_ms": nano_ms, "image_url": colored_url,
                 "input_image": binary_url, "model": "google/gemini-3-pro-image-preview"},
                {"step": "grid_ready", "duration_ms": grid_ms},
                {"step": "furniture_specs", "duration_ms": specs_ms, "model": "anthropic/claude-sonnet-4-6",
                 "input_prompt": spec_prompt, "output_text": spec_output[:3000]},
                {"step": "searching_ikea", "duration_ms": ikea_ms,
                 "output_text": ikea_summary},
                {"step": "constraints", "message": "Constraints ready", "duration_ms": constraints_ms,
                 "model": "anthropic/claude-sonnet-4-6",
                 "input_prompt": constraint_prompt,
                 "output_text": constraint_output[:3000]},
                {"step": "optimizing", "message": "Running Gurobi optimizer"},
            )})

            # --- Step 7: Gurobi optimizer ---
            from ..furniture_placement.coord_convert import convert_all_placements
            from ..furniture_placement.optimizer import FurniturePlacementModel

            opt_furniture = specs_to_optimizer_format(specs, 0.25)
            opt_constraints = constraints_to_optimizer_format(constraints, 0.25)

            t0 = time.time()
            model = FurniturePlacementModel(
                grid=grid,
                furniture=opt_furniture,
                constraints=opt_constraints,
                time_limit=180,
            )
            placements = await asyncio.to_thread(model.optimize)

            if not placements:
                logger.info("No solution, retrying without distance constraints...")
                for room_name in opt_constraints:
                    opt_constraints[room_name].distance_constraints = []
                model = FurniturePlacementModel(
                    grid=grid,
                    furniture=opt_furniture,
                    constraints=opt_constraints,
                    time_limit=180,
                )
                placements = await asyncio.to_thread(model.optimize)
            gurobi_ms = round((time.time() - t0) * 1000)

            if not placements:
                raise ValueError("Gurobi found no feasible solution")

            # Placement summary for trace
            placement_summary = "\n".join(
                f"  {p.room_name}/{p.name}: grid({p.grid_i},{p.grid_j}) "
                f"size={p.size_i}x{p.size_j}"
                for p in placements
            )

            db.update_job(job_id, {"trace": _trace(
                {"step": "started", "duration_ms": 1},
                {"step": "nano_banana", "duration_ms": nano_ms, "image_url": colored_url,
                 "input_image": binary_url, "model": "google/gemini-3-pro-image-preview"},
                {"step": "grid_ready", "duration_ms": grid_ms},
                {"step": "furniture_specs", "duration_ms": specs_ms, "model": "anthropic/claude-sonnet-4-6",
                 "input_prompt": spec_prompt, "output_text": spec_output[:3000]},
                {"step": "searching_ikea", "duration_ms": ikea_ms,
                 "output_text": ikea_summary},
                {"step": "constraints", "duration_ms": constraints_ms, "model": "anthropic/claude-sonnet-4-6",
                 "input_prompt": constraint_prompt, "output_text": constraint_output[:3000]},
                {"step": "optimizing", "message": f"{len(placements)} items placed",
                 "duration_ms": gurobi_ms, "model": "Gurobi IP",
                 "output_text": placement_summary},
                {"step": "trellis_3d", "message": "Generating 3D models (Trellis)"},
            )})

            # --- Step 8: Convert to 3D + Trellis models ---
            coords_3d = convert_all_placements(placements, grid)

            api_placements = []
            for coord in coords_3d:
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

            # Generate Trellis 3D models for items missing GLBs
            from ..tools.ikea.trellis_fallback import generate_missing_models

            t0 = time.time()
            total_with_glb = await generate_missing_models(
                api_placements, max_calls=10, dry_run=False,
            )
            trellis_ms = round((time.time() - t0) * 1000)

        # --- Step 9: Save to session DB ---
        placement_result = {"placements": api_placements}

        # Update furniture items with final placement data
        for p in api_placements:
            try:
                db.upsert_furniture({
                    "id": p.get("item_id") or p["name"],
                    "session_id": session_id,
                    "retailer": "ikea" if p.get("buy_url") else "generated",
                    "name": p.get("ikea_name") or p["name"],
                    "price": p.get("price") or 0,
                    "currency": p.get("currency") or "EUR",
                    "image_url": p.get("image_url", ""),
                    "product_url": p.get("buy_url", ""),
                    "glb_url": p.get("glb_url", ""),
                    "category": p.get("room_name", ""),
                    "dimensions": {
                        "width_cm": (p.get("size_m", {}).get("width", 0)) * 100,
                        "depth_cm": (p.get("size_m", {}).get("depth", p.get("size_m", {}).get("length", 0))) * 100,
                        "height_cm": (p.get("size_m", {}).get("height", 0)) * 100,
                    },
                    "selected": True,
                })
            except Exception:
                logger.debug("Failed to upsert furniture item %s", p.get("item_id", p["name"]))

        grid_data = grid.to_dict()
        furniture_specs = {
            room: [
                {
                    "name": i.name, "category": i.category,
                    "length_m": i.length_m, "width_m": i.width_m,
                    "height_m": i.height_m, "search_query": i.search_query,
                    "priority": i.priority,
                }
                for i in items
            ]
            for room, items in specs.items()
        }

        db.update_session(session_id, {
            "placements": placement_result,
            "grid_data": grid_data,
            "furniture_specs": furniture_specs,
            "search_queries": search_queries,
            "status": "placement_ready",
        })

        db.update_job(job_id, {
            "status": "completed",
            "trace": _trace(
                {"step": "started", "duration_ms": 1},
                {"step": "nano_banana", "message": "Rooms colored", "duration_ms": nano_ms,
                 "image_url": colored_url, "input_image": floorplan_url,
                 "input_prompt": _NANO_BANANA_PROMPT,
                 "model": "google/gemini-3-pro-image-preview"},
                {"step": "grid_ready", "message": f"{grid.width}×{grid.height}, {grid.num_rooms} rooms",
                 "duration_ms": grid_ms},
                {"step": "furniture_specs", "message": f"{total_items} items",
                 "duration_ms": specs_ms, "model": "anthropic/claude-sonnet-4-6",
                 "input_prompt": spec_prompt, "output_text": spec_output[:3000]},
                {"step": "searching_ikea", "message": f"{found} found, {with_glb} GLBs",
                 "duration_ms": ikea_ms, "output_text": ikea_summary},
                {"step": "constraints", "message": "Constraints ready",
                 "duration_ms": constraints_ms, "model": "anthropic/claude-sonnet-4-6",
                 "input_prompt": constraint_prompt, "output_text": constraint_output[:3000]},
                {"step": "optimizing", "message": f"{len(api_placements)} items placed",
                 "duration_ms": gurobi_ms, "model": "Gurobi IP",
                 "output_text": placement_summary},
                {"step": "trellis_3d", "message": f"{total_with_glb}/{len(api_placements)} with 3D",
                 "duration_ms": trellis_ms, "model": "fal-ai/trellis-2"},
                {"step": "completed"},
            ),
        })

        logger.info(
            "Gurobi pipeline complete: session=%s, %d items placed",
            session_id, len(api_placements),
        )

        return {
            "placements": placement_result,
            "search_queries": search_queries,
            "items_placed": len(api_placements),
        }

    except Exception as e:
        logger.error("Gurobi placement failed: %s", e, exc_info=True)
        try:
            db.update_job(job_id, {
                "status": "failed",
                "trace": [{"step": "error", "message": str(e)}],
            })
            db.update_session(session_id, {"status": "placing_failed"})
        except Exception:
            pass
        raise
