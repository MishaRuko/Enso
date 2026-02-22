
## Floor Plan Analysis (FloorPlanAnalyzer)

The `FloorPlanAnalyzer` converts raw inputs (images or 3D GLB models) into the `FloorPlanGrid` structure required by the optimizer.

It uses a multi-stage pipeline involving Blender (for 3D models) and Generative AI (Gemini via Nano Banana) to robustly identify rooms.

### Workflow

1.  **Input Processing**:
    *   **Images (`.jpg`, `.png`)**: Used directly.
    *   **3D Models (`.glb`)**: Processed via Blender (`flythrough.py`). The model is clipped at 75% height to remove ceilings, and a top-down depth map is rendered. This map is thresholded to create a clean binary floorplan (White Walls, Black Background).

2.  **AI Segmentation**:
    *   The binary or raw image is sent to **Gemini 1.5 Pro** (via `nanobananana.py`).
    *   Prompt: *"Fill the empty spaces of individual/distinct rooms with different bright solid colours."*
    *   Result: A "colored-in" version of the floor plan where each room has a unique color.

3.  **Region Extraction**:
    *   Colors are clustered using Euclidean distance to merge noisy pixels into coherent regions.
    *   Regions are mapped to required room names (e.g., Living Room, Kitchen) based on size heuristics.

4.  **Grid Generation**:
    *   The segmented map is rasterized into a `FloorPlanGrid` with the specified cell size.

### Usage

```python
from furniture_placement.floorplan_analyzer import FloorPlanAnalyzer

# Initialize
analyzer = FloorPlanAnalyzer(
    target_width_m=12.0,  # Assumed width of the building
    cell_size_m=0.5       # Grid resolution
)

# Define expected rooms (helps with mapping)
required_rooms = ["Living Room", "Kitchen", "Bedroom", "Bathroom"]

# Run analysis (async)
# Supports .jpg, .png, or .glb paths
grid = await analyzer.segment_floorplan(
    "path/to/model.glb", 
    required_rooms,
    debug_output_dir="backend/output"  # Optional: saves intermediate debug images
)

# The resulting 'grid' is ready for the optimization pipeline
```

### Debugging

If `debug_output_dir` is provided, the analyzer saves:
*   `floorplan_depth.png`: Raw depth render from Blender (for GLB inputs).
*   `glb_binary_input.png`: The inverted binary mask sent to Gemini (White Walls, Black Rooms).
*   `nano_banana_output.png`: The raw colored segmentation returned by Gemini.

**Troubleshooting:**
*   **Blender Errors**: Ensure Blender 4.x or later is installed. The script automatically handles `BLENDER_EEVEE` vs `BLENDER_EEVEE_NEXT` engine names.
*   **Flat/Blank Binary**: Check `clip-height`. If the model is flat, the auto-thresholding might fail. The logs will show "Flat model detected".
*   **Messy Segmentation**: Check `nano_banana_output.png`. If colors are mixed, the color clustering threshold in `_extract_regions` might need adjustment.
