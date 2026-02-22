"""Gurobi-based furniture placement pipeline.

Steps:
1. Load FloorPlanGrid (must already exist in session)
2. Furniture spec agent (Claude)
3. IKEA product search (direct pipeline call)
4. Furniture constraint agent (Claude)
5. Gurobi integer programming optimizer
6. Grid → 3D coordinate conversion
"""

import logging

from .. import db
from ..furniture_placement.coord_convert import convert_all_placements
from ..furniture_placement.furniture_agents import (
    constraints_to_optimizer_format,
    generate_furniture_constraints,
    generate_furniture_specs,
    specs_to_optimizer_format,
    specs_to_search_queries,
    update_specs_from_search_results,
)
from ..furniture_placement.grid_types import FloorPlanGrid
from ..furniture_placement.optimizer import FurniturePlacementModel
from ..tools.ikea.search import (
    ikea_results_to_spec_updates,
    search_ikea_products,
)

logger = logging.getLogger(__name__)


def _get_grid(session_id: str, session: dict) -> FloorPlanGrid:
    """Load FloorPlanGrid from session.

    The grid must already exist in session['grid_data'].
    Grid creation is handled externally (e.g. from room segmentation).
    """
    grid_data = session.get("grid_data")
    if not grid_data or not isinstance(grid_data, dict) or "room_cells" not in grid_data:
        raise ValueError(
            f"Session {session_id} has no grid_data. "
            "Upload a floorplan and run room segmentation first."
        )

    logger.info("Using grid (%dx%d)", grid_data["width"], grid_data["height"])
    return FloorPlanGrid.from_dict(grid_data)


def _get_preferences(session: dict) -> dict | None:
    """Extract user preferences from session."""
    prefs = session.get("preferences")
    if prefs and isinstance(prefs, dict):
        return prefs
    return None


def _furniture_items_to_search_results(items: list[dict]) -> list[dict]:
    """Convert DB furniture items to search result format for spec updating."""
    results = []
    for item in items:
        dims = item.get("dimensions")
        if not dims or not isinstance(dims, dict):
            continue
        results.append({
            "name": item.get("name", ""),
            "room_name": item.get("room_name", item.get("category", "")),
            "dimensions_cm": {
                "length": dims.get("depth_cm", dims.get("length", 0)),
                "width": dims.get("width_cm", dims.get("width", 0)),
                "height": dims.get("height_cm", dims.get("height", 0)),
            },
        })
    return results


async def place_furniture_gurobi(session_id: str, job_id: str) -> dict:
    """Run the full Gurobi placement pipeline.

    Steps:
        1. Load or generate FloorPlanGrid
        2. Run Agent 7 (furniture specs)
        2b. Search IKEA for real products + GLB models (via ikea-service)
        3. Run Agent 8 (constraints — using actual IKEA dimensions)
        4. Run Gurobi optimizer
        5. Convert to 3D + merge IKEA product data (GLB URLs, prices)
        6. Save placements to session

    Args:
        session_id: Design session ID.
        job_id: Job ID for progress tracking.

    Returns:
        Dict with placements and search_queries.
    """
    try:
        db.update_job(job_id, {"status": "running", "trace": [{"step": "started"}]})

        session = db.get_session(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")

        # --- Step 1: Get FloorPlanGrid ---
        db.update_session(session_id, {"status": "analyzing_grid"})
        grid = _get_grid(session_id, session)

        db.update_job(job_id, {"trace": [
            {"step": "started"},
            {"step": "grid_ready", "rooms": grid.room_names, "size": f"{grid.width}x{grid.height}"},
        ]})

        # --- Step 2: Furniture Spec Agent ---
        db.update_session(session_id, {"status": "generating_furniture"})
        preferences = _get_preferences(session)

        logger.info("Running furniture spec agent...")
        specs = await generate_furniture_specs(grid, preferences)

        total_items = sum(len(v) for v in specs.values())
        db.update_job(job_id, {"trace": [
            {"step": "started"},
            {"step": "grid_ready"},
            {"step": "furniture_specs", "total_items": total_items},
        ]})

        # --- Step 2b: IKEA product search ---
        ikea_results = []
        try:
            db.update_session(session_id, {"status": "searching_ikea"})
            logger.info("Searching IKEA for %d items...", total_items)
            ikea_results = await search_ikea_products(specs)

            # Update our specs with actual IKEA dimensions
            spec_updates = ikea_results_to_spec_updates(ikea_results)
            if spec_updates:
                logger.info("Updating %d specs with actual IKEA dimensions", len(spec_updates))
                update_specs_from_search_results(specs, spec_updates)

            found = sum(1 for r in ikea_results if r.get("found"))
            db.update_job(job_id, {"trace": [
                {"step": "started"},
                {"step": "grid_ready"},
                {"step": "furniture_specs"},
                {"step": "ikea_search", "found": found, "total": len(ikea_results)},
            ]})
        except Exception as e:
            logger.warning("IKEA search failed (continuing without): %s", e)
            # Non-fatal — we can still optimize with estimated dimensions

        # --- Step 3: Constraint Agent ---
        db.update_session(session_id, {"status": "generating_constraints"})
        logger.info("Running constraint agent...")
        constraints = await generate_furniture_constraints(grid, specs, preferences)

        db.update_job(job_id, {"trace": [
            {"step": "started"},
            {"step": "grid_ready"},
            {"step": "furniture_specs"},
            {"step": "constraints_ready"},
        ]})

        # --- Step 4: Optimize ---
        db.update_session(session_id, {"status": "optimizing"})
        logger.info("Running Gurobi optimizer...")

        opt_furniture = specs_to_optimizer_format(specs, grid.cell_size)
        opt_constraints = constraints_to_optimizer_format(constraints, grid.cell_size)

        model = FurniturePlacementModel(
            grid=grid,
            furniture=opt_furniture,
            constraints=opt_constraints,
            time_limit=120,
        )
        placements = model.optimize()

        if not placements:
            logger.warning("Optimizer found no solution, trying without distance constraints")
            # Retry with relaxed constraints (drop distance, keep boundary + facing)
            for room_name in opt_constraints:
                opt_constraints[room_name].distance_constraints = []
            model = FurniturePlacementModel(
                grid=grid,
                furniture=opt_furniture,
                constraints=opt_constraints,
                time_limit=120,
            )
            placements = model.optimize()

        if not placements:
            raise ValueError("Gurobi optimizer found no feasible solution")

        # --- Step 5: Convert to 3D and merge IKEA data ---
        coords_3d = convert_all_placements(placements, grid)

        # Index IKEA results by (room_name, item_name) for fast lookup
        ikea_lookup = {}
        for r in ikea_results:
            if r.get("found"):
                ikea_lookup[(r["room_name"], r["name"])] = r

        # Build placements in the API format, merging IKEA product data
        api_placements = []
        for coord in coords_3d:
            key = (coord["room_name"], coord["name"])
            ikea = ikea_lookup.get(key, {})

            api_placements.append({
                "item_id": ikea.get("ikea_item_code") or coord["name"],
                "name": coord["name"],
                "ikea_name": ikea.get("ikea_name", ""),
                "position": coord["position"],
                "rotation_y_degrees": coord["rotation_y_degrees"],
                "reasoning": f"Gurobi-optimized placement in {coord['room_name']}",
                "room_name": coord["room_name"],
                "size_m": coord.get("size_m", {}),
                "glb_url": ikea.get("glb_url", ""),
                "image_url": ikea.get("image_url", ""),
                "buy_url": ikea.get("buy_url", ""),
                "price": ikea.get("price"),
                "currency": ikea.get("currency", ""),
            })

        # --- Step 5b: Generate 3D models for items without IKEA GLBs ---
        try:
            from ..tools.ikea.trellis_fallback import generate_missing_models
            await generate_missing_models(api_placements, max_calls=3)
        except Exception as e:
            logger.warning("Trellis fallback failed (continuing without): %s", e)

        result = {"placements": api_placements}

        # Save furniture items to DB so the sidebar shows them
        for p in api_placements:
            try:
                db.upsert_furniture({
                    "id": p["item_id"],
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
                        "depth_cm": (p.get("size_m", {}).get("length", 0)) * 100,
                        "height_cm": (p.get("size_m", {}).get("height", 0)) * 100,
                    },
                    "selected": True,
                })
            except Exception:
                logger.debug("Failed to upsert furniture item %s", p["item_id"])

        # Generate search queries (for reference / re-search)
        search_queries = specs_to_search_queries(specs, preferences)

        # --- Step 6: Save ---
        db.update_session(session_id, {
            "placements": result,
            "furniture_specs": {
                room: [
                    {
                        "name": item.name,
                        "category": item.category,
                        "length_m": item.length_m,
                        "width_m": item.width_m,
                        "height_m": item.height_m,
                        "search_query": item.search_query,
                        "priority": item.priority,
                    }
                    for item in items
                ]
                for room, items in specs.items()
            },
            "search_queries": search_queries,
            "status": "placement_ready",
        })

        items_with_glb = sum(1 for p in api_placements if p.get("glb_url"))
        db.update_job(job_id, {
            "status": "completed",
            "trace": [
                {"step": "started"},
                {"step": "grid_ready"},
                {"step": "furniture_specs"},
                {"step": "ikea_search"},
                {"step": "constraints_ready"},
                {"step": "optimized", "items_placed": len(placements), "with_glb": items_with_glb},
                {"step": "completed"},
            ],
        })

        logger.info(
            "Placement complete: session=%s, %d items placed across %d rooms",
            session_id, len(placements), grid.num_rooms,
        )

        return {
            "placements": result,
            "search_queries": search_queries,
            "rooms": grid.room_names,
            "items_placed": len(placements),
        }

    except Exception as e:
        logger.error("Gurobi placement failed: %s", e, exc_info=True)
        try:
            db.update_job(job_id, {
                "status": "failed",
                "trace": [{"step": "error", "message": str(e)}],
            })
            db.update_session(session_id, {"status": "placement_failed"})
        except Exception:
            pass
        raise
