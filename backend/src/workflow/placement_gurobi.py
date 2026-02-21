"""Gurobi-based furniture placement pipeline.

Replaces the one-shot Gemini placement with:
1. Floor plan → grid (vision LLM)
2. Furniture spec agent (Claude)
3. Furniture constraint agent (Claude)
4. Gurobi integer programming optimizer
5. Grid → 3D coordinate conversion
"""

import logging

from .. import db
from ..furniture_placement.coord_convert import convert_all_placements
from ..furniture_placement.floorplan_analyzer import analyze_floorplan_from_url
from ..furniture_placement.furniture_agents import (
    FurnitureItemSpec,
    constraints_to_optimizer_format,
    generate_furniture_constraints,
    generate_furniture_specs,
    specs_to_optimizer_format,
    specs_to_search_queries,
    update_specs_from_search_results,
)
from ..furniture_placement.grid_types import FloorPlanGrid
from ..furniture_placement.optimizer import FurniturePlacementModel
from .floorplan import _to_data_url

logger = logging.getLogger(__name__)


async def _get_or_create_grid(
    session_id: str,
    session: dict,
    job_id: str | None = None,
) -> FloorPlanGrid:
    """Load cached grid from session or create from floorplan image.

    The grid is cached in session['grid_data'] to avoid re-running the
    vision LLM on every placement request.
    """
    # Try cached grid first
    grid_data = session.get("grid_data")
    if grid_data and isinstance(grid_data, dict) and "room_cells" in grid_data:
        logger.info("Using cached grid (%dx%d)", grid_data["width"], grid_data["height"])
        return FloorPlanGrid.from_dict(grid_data)

    # Generate grid from floorplan image
    floorplan_url = session.get("floorplan_url")
    if not floorplan_url:
        raise ValueError(f"Session {session_id} has no floorplan_url")

    if job_id:
        db.update_job(job_id, {"trace": [{"step": "grid_analysis"}]})

    logger.info("Generating grid from floorplan for session %s", session_id)
    image_url = await _to_data_url(floorplan_url)

    # Estimate total area from existing room data if available
    total_area = None
    room_data = session.get("room_data")
    if room_data and isinstance(room_data, dict):
        rooms = room_data.get("rooms", [])
        if rooms:
            total_area = sum(r.get("area_sqm", 0) for r in rooms)
            if total_area > 0:
                logger.info("Using total area hint from room_data: %.1f m²", total_area)
            else:
                total_area = None

    grid = await analyze_floorplan_from_url(
        image_url,
        total_area_sqm=total_area,
        cell_size=1.0,
    )

    # Cache grid in session
    db.update_session(session_id, {"grid_data": grid.to_dict()})
    logger.info("Grid cached: %dx%d, %d rooms", grid.width, grid.height, grid.num_rooms)

    return grid


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
        3. Optionally update specs from existing furniture search results
        4. Run Agent 8 (constraints)
        5. Run Gurobi optimizer
        6. Convert to 3D coordinates
        7. Save placements to session

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
        grid = await _get_or_create_grid(session_id, session, job_id)

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

        # --- Step 2b: Update specs from existing search results ---
        existing_furniture = db.list_furniture(session_id)
        if existing_furniture:
            search_results = _furniture_items_to_search_results(existing_furniture)
            if search_results:
                logger.info("Updating specs from %d existing furniture items", len(search_results))
                update_specs_from_search_results(specs, search_results)

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

        # --- Step 5: Convert to 3D ---
        coords_3d = convert_all_placements(placements, grid)

        # Build placements in the API format
        api_placements = []
        for coord in coords_3d:
            api_placements.append({
                "item_id": coord["name"],  # use furniture name as ID
                "name": coord["name"],
                "position": coord["position"],
                "rotation_y_degrees": coord["rotation_y_degrees"],
                "reasoning": f"Gurobi-optimized placement in {coord['room_name']}",
                "room_name": coord["room_name"],
                "size_m": coord.get("size_m", {}),
            })

        result = {"placements": api_placements}

        # Generate search queries for the IKEA pipeline
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

        db.update_job(job_id, {
            "status": "completed",
            "trace": [
                {"step": "started"},
                {"step": "grid_ready"},
                {"step": "furniture_specs"},
                {"step": "constraints_ready"},
                {"step": "optimized", "items_placed": len(placements)},
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
