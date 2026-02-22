import asyncio
import os
import logging
from pathlib import Path

from .floorplan_analyzer import FloorPlanAnalyzer
from .visualize import save_grid_image, print_grid_ascii

async def main():
    logging.basicConfig(level=logging.INFO)
    # Setup paths
    base_dir = Path(__file__).resolve().parent.parent.parent
    example_model_dir = base_dir / "example_model"
    output_dir = base_dir / "output"
    
    # Ensure output dir exists
    output_dir.mkdir(exist_ok=True)
    
    # Use example GLB model
    glb_path = example_model_dir / "example_model.glb"
    if not glb_path.exists():
        # Fallback to jpg if glb doesn't exist (though it should)
        print(f"GLB not found at {glb_path}, checking for floorplan.jpg")
        glb_path = example_model_dir / "floorplan.jpg"
        
    if not glb_path.exists():
        print(f"Error: No input file found at {glb_path}")
        return

    print(f"Testing FloorPlanAnalyzer on {glb_path}...")
    
    # Initialize analyzer
    analyzer = FloorPlanAnalyzer(target_width_m=12.0, cell_size_m=0.5)
    
    # Expected rooms
    required_rooms = ["Living Room", "Kitchen", "Bedroom", "Bathroom"]
    
    try:
        # Run segmentation with debug output
        print("Running segmentation (Blender -> Gemini)...")
        grid = await analyzer.segment_floorplan(
            str(glb_path), 
            required_rooms,
            debug_output_dir=str(output_dir)
        )
        
        print(f"Segmentation complete!")
        print(f"Grid dimensions: {grid.width}x{grid.height} cells ({grid.width_m:.1f}x{grid.height_m:.1f} m)")
        print(f"Rooms found: {grid.room_names}")
        
        # Verify files were created
        expected_files = ["nano_banana_output.png", "floorplan_depth.png", "glb_binary_input.png"]
        for f in expected_files:
            if (output_dir / f).exists():
                print(f"Verified: {f} was saved successfully.")
            else:
                print(f"Warning: {f} was NOT found!")
        
        # Save grid visualization
        vis_path = output_dir / "segmented_floorplan.png"
        print(f"\nSaving grid visualization to {vis_path}...")
        save_grid_image(grid, str(vis_path), scale=20)
        
    except Exception as e:
        print(f"Analysis failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
