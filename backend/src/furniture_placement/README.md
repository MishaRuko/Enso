# Furniture Placement Pipeline

Grid-based furniture placement for interior design. Takes a floor plan image, converts it to a discrete grid, uses Gurobi integer programming to optimally place furniture, and outputs 3D coordinates for the frontend.

## Overview

```
Floor plan image
    │
    ▼
┌─────────────────────┐
│  floorplan_analyzer  │  Vision LLM (Gemini) extracts room polygons
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│     rasterize        │  Polygons → grid cells (1m or 0.5m resolution)
└──────────┬──────────┘
           │
           ▼
     FloorPlanGrid         Room cells, passage cells, doors, windows, entrance
           │
           ├──── + UserPreferences (from voice consultation)
           │
           ▼
┌─────────────────────┐
│  furniture_agents    │  Claude: room data + prefs → furniture list (Agent 7)
│  (Spec Agent)        │  → search queries for IKEA pipeline
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  furniture_agents    │  Claude: furniture + rooms → constraints (Agent 8)
│  (Constraint Agent)  │  boundary, distance, alignment, facing
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│     optimizer        │  Gurobi integer programming — guaranteed valid placement
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│   coord_convert      │  Grid positions → 3D metres for React Three Fiber
└─────────────────────┘
```

## Modules

| File | Purpose |
|------|---------|
| `grid_types.py` | Data structures: `FloorPlanGrid`, `RoomPolygon`, `DoorInfo`, `WindowInfo` |
| `rasterize.py` | Polygon → grid cell conversion (scanline point-in-polygon) |
| `floorplan_analyzer.py` | Vision LLM prompt, response parsing, grid construction |
| `optimizer.py` | Gurobi furniture placement with fixed room boundaries |
| `coord_convert.py` | Grid coordinates → 3D metres for the frontend |
| `furniture_agents.py` | LLM agents: furniture spec (Agent 7) + constraints (Agent 8) |
| `visualize.py` | ASCII and PNG grid visualization for debugging |
| `test_analyzer.py` | Test: floor plan → grid (needs OpenRouter key) |
| `test_optimizer.py` | Test: grid → furniture placement (needs Gurobi license) |
| `test_agents.py` | Test: furniture agents (needs OpenRouter key) |

## Quick Start

### 1. Floor plan → grid

```bash
cd backend/src

# Analyze the example floor plan (needs OPENROUTER_API_KEY in backend/.env)
python -m furniture_placement.test_analyzer

# With known total area (for floor plans without dimension labels)
python -m furniture_placement.test_analyzer --total-area 75

# Finer grid (0.5m cells — better accuracy, 4x more cells)
python -m furniture_placement.test_analyzer --cell-size 0.5
```

### 2. Furniture placement (needs Gurobi)

```bash
# Install Gurobi: https://www.gurobi.com/academia/academic-program-and-licenses/
pip install gurobipy

# Test with synthetic data
python -m furniture_placement.test_optimizer
```

### 3. Furniture agents (needs OpenRouter key)

```bash
# Generate furniture specs + constraints using Claude
python -m furniture_placement.test_agents

# Using a real grid from the analyzer
python -m furniture_placement.test_agents --from-grid output/grid_data.json

# Custom style preferences
python -m furniture_placement.test_agents --style "minimalist japanese"
```

### 4. From Python (full pipeline)

```python
from furniture_placement.floorplan_analyzer import analyze_floorplan
from furniture_placement.furniture_agents import (
    generate_furniture_specs,
    generate_furniture_constraints,
    specs_to_optimizer_format,
    constraints_to_optimizer_format,
    specs_to_search_queries,
)
from furniture_placement.optimizer import FurniturePlacementModel
from furniture_placement.coord_convert import convert_all_placements

# Step 1: Floor plan → grid
grid = await analyze_floorplan("plan.jpg", total_area_sqm=85.0, cell_size=1.0)

# Step 2: LLM agents generate furniture + constraints
preferences = {"style": "modern scandinavian", "budget_max": 5000}
specs = await generate_furniture_specs(grid, preferences)
constraints = await generate_furniture_constraints(grid, specs, preferences)

# Step 2b: (optional) Send search queries to IKEA pipeline
search_queries = specs_to_search_queries(specs, preferences)

# Step 3: Convert to optimizer format (metres → grid cells)
opt_furniture = specs_to_optimizer_format(specs, grid.cell_size)
opt_constraints = constraints_to_optimizer_format(constraints, grid.cell_size)

# Step 4: Optimize placement
model = FurniturePlacementModel(grid, opt_furniture, opt_constraints)
placements = model.optimize()

# Step 5: Convert to 3D coordinates
coords_3d = convert_all_placements(placements, grid)
# [{"name": "sofa", "position": {"x": 2.5, "y": 0, "z": 3.5}, "rotation_y_degrees": 90, ...}]
```

## Grid Coordinate System

```
    j →  (East)
  ┌───┬───┬───┬───┐
i │0,0│0,1│0,2│0,3│  ← North wall
↓ ├───┼───┼───┼───┤
  │1,0│1,1│1,2│1,3│
  ├───┼───┼───┼───┤
  │2,0│2,1│2,2│2,3│  ← South wall
  └───┴───┴───┴───┘
```

- Origin `(0, 0)` = Northwest corner
- `i` = rows (southward), `j` = columns (eastward)
- Each cell = `cell_size × cell_size` metres (default 1m)

The frontend uses a different system (SW origin, X=east, Z=north). `coord_convert.py` handles the transform.

## Optimizer Details

The optimizer uses Gurobi mixed-integer programming. Furniture pieces are rectangles of grid cells. The solver guarantees:

- **No overlaps** — each cell is occupied by at most one item
- **Room containment** — all furniture cells are inside their room
- **Wall adjacency** — items like beds/sofas are against walls
- **Facing** — e.g., sofa faces the TV
- **Alignment** — paired items share the same orientation axis
- **Distance** — soft targets for center-to-center distances
- **Balance** — furniture weighted center near room center

### Constraint types

| Type | Example | Effect |
|------|---------|--------|
| `boundary_items` | `["sofa", "wardrobe"]` | Must touch a wall |
| `facing_constraints` | `[["sofa", "tv"]]` | Sofa faces toward TV |
| `alignment_constraints` | `[["bed", "nightstand"]]` | Same rotation axis |
| `distance_constraints` | `[["nightstand", "bed", 0, 0.5]]` | Target center offset |

## Furniture Agents

Two Claude-powered agents (adapted from Co-Layout paper) generate furniture specs and constraints:

### Agent 7: Furniture Spec
- **Input**: `FloorPlanGrid` + user preferences (style, budget, lifestyle)
- **Output**: `dict[room_name, list[FurnitureItemSpec]]` — per-room furniture with:
  - Metric dimensions (length, width, height in metres)
  - IKEA search queries for each item
  - Priority (essential / nice_to_have)
- **Rules**: Scales count with room area, caps footprint at 80%, numbers identical items

### Agent 8: Furniture Constraints
- **Input**: `FloorPlanGrid` + furniture specs from Agent 7
- **Output**: `dict[room_name, FurnitureConstraints]` with 4 types:
  - `boundary` — items against walls (beds, sofas, wardrobes)
  - `distance` — center-to-center offset targets `[name1, name2, d_along, d_perp]`
  - `align` — same orientation axis `[name1, name2]`
  - `facing` — name1 faces toward name2 `[name1, name2]`

### Search Interface

`specs_to_search_queries()` produces IKEA-compatible search dicts:
```python
{"category": "sofa", "name": "sofa", "search_query": "3-seat sofa grey modern",
 "dimensions_cm": {"length": 220, "width": 90, "height": 80},
 "room_name": "Living Room", "priority": "essential"}
```

If actual product dimensions come back from the IKEA search, call
`update_specs_from_search_results()` to patch the specs before optimization.

## Configuration

| Parameter | Default | Description |
|-----------|---------|-------------|
| `cell_size` | `1.0` | Grid metres/cell. `0.5` = finer. |
| `total_area_sqm` | `None` | Scale hint for unlabeled floor plans. |
| `time_limit` | `300` | Gurobi solver timeout (seconds). |
| `mip_gap` | `0.02` | Optimality gap (2% = good enough). |
| `threads` | `4` | Solver threads. |

## Dependencies

- `openai` — OpenRouter API client (floor plan analysis)
- `numpy` — Grid operations
- `gurobipy` — Gurobi optimizer ([free academic license](https://www.gurobi.com/academia/))
- `Pillow` — PNG visualization (optional)
- `python-dotenv` — Env loading (test scripts)
