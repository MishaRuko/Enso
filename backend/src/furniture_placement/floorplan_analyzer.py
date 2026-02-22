import base64
import logging
import os
import shutil
import subprocess
import tempfile
import json
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import cv2
import numpy as np
import requests

from ..tools.nanobananana import generate_segmented_rooms
from .grid_types import FloorPlanGrid

logger = logging.getLogger(__name__)


class FloorPlanAnalyzer:
    """
    Analyzes floor plan images to extract room layouts and convert them into
    grid representations for furniture placement.
    """

    def __init__(self, target_width_m: float = 12.0, cell_size_m: float = 0.5):
        """
        Args:
            target_width_m: Assumed real-world width of the floor plan in meters.
                            Used to scale pixels to grid cells.
            cell_size_m: Size of each grid cell in meters (default 0.5m).
        """
        self.target_width_m = target_width_m
        self.cell_size_m = cell_size_m

    def _find_blender(self) -> str:
        """Find Blender executable."""
        if shutil.which("blender"):
            return "blender"
        
        # Check macOS paths
        mac_paths = [
            "/Applications/Blender.app/Contents/MacOS/Blender",
            "/Applications/Blender.app/Contents/MacOS/blender",
        ]
        for path in mac_paths:
            if os.path.exists(path):
                return path
                
        raise FileNotFoundError("Blender not found. Please install Blender or add it to PATH.")

    def _run_blender_script(self, glb_path: str, script_args: List[str]) -> bool:
        """Run the flythrough.py script in Blender."""
        blender = self._find_blender()
        
        # Locate flythrough.py relative to this file
        current_dir = Path(__file__).parent
        script_path = current_dir.parent / "glb-flythrough" / "flythrough.py"
        
        if not script_path.exists():
             raise FileNotFoundError(f"flythrough.py not found at {script_path}")

        cmd = [
            blender,
            "--background",
            "--python", str(script_path),
            "--",
            glb_path,
        ] + script_args

        logger.info(f"Running Blender: {' '.join(cmd)}")
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        # Print output for debugging
        print(f"Blender return code: {result.returncode}")
        print(f"Blender stdout:\n{result.stdout}")
        print(f"Blender stderr:\n{result.stderr}")
        
        if result.returncode != 0:
            logger.error(f"Blender failed: {result.stderr}")
            return False
            
        return True

    def _generate_binary_from_glb(self, glb_path: str, output_dir: Path) -> Tuple[bytes, dict]:
        """
        Generate a binary floorplan from a GLB file using Blender.
        Returns the binary image bytes and the bounds info dict.
        """
        # Paths for Blender output
        depth_path = output_dir / "floorplan_depth.png"
        
        # Run Blender to generate depth map
        # Using 1024 resolution to match reference pipeline
        success = self._run_blender_script(
            glb_path,
            ["--floorplan", "--depth", "-o", str(depth_path),
             "--resolution", "1024", "1024",
             "--clip-height", "75.0"]
        )
        
        if not success or not depth_path.exists():
            raise RuntimeError("Failed to generate depth floorplan with Blender")
            
        # Load info file
        info_path = output_dir / "floorplan_depth_info.json"
        with open(info_path, 'r') as f:
            bounds_info = json.load(f)
            
        # Load depth image
        depth_img = cv2.imread(str(depth_path), cv2.IMREAD_GRAYSCALE)
        if depth_img is None:
            raise RuntimeError(f"Failed to load depth image: {depth_path}")
            
        # Threshold logic (from pipeline.py)
        # Separate house from background
        # Background typically has very high depth values (far from camera)
        unique_vals, counts = np.unique(depth_img, return_counts=True)
        # logger.info(f"Unique depth values: {list(zip(unique_vals, counts))}")
        
        sorted_vals = sorted(unique_vals)
        
        # Find gap between background (high values) and house
        max_gap = 0
        gap_threshold = float(sorted_vals[-1])
        
        for i in range(len(sorted_vals) - 1):
            gap = float(sorted_vals[i + 1]) - float(sorted_vals[i])
            if gap > max_gap:
                max_gap = gap
                gap_threshold = (float(sorted_vals[i]) + float(sorted_vals[i + 1])) / 2
        
        logger.info(f"House/background threshold: {gap_threshold:.1f} (gap of {max_gap})")
                
        house_mask = depth_img < gap_threshold
        
        if not np.any(house_mask):
            logger.warning("No house pixels detected, using full image")
            binary_img = np.ones_like(depth_img) * 255
        else:
            house_depths = depth_img[house_mask]
            house_min = int(np.min(house_depths))
            house_max = int(np.max(house_depths))
            house_range = house_max - house_min
            
            logger.info(f"House depth range: {house_min}-{house_max} (range: {house_range})")
            
            # Wall threshold (walls are highest = lowest depth value)
            if house_range <= 2:
                # Very flat model - use the minimum value as walls
                wall_threshold = house_min + 0.5
                logger.info(f"Flat model detected, using wall threshold: {wall_threshold}")
            else:
                # 75% height threshold (25% from top/darkest)
                wall_threshold = house_min + 0.25 * house_range
                logger.info(f"Using 75% height threshold: {wall_threshold:.1f}")
                
            binary_img = np.ones_like(depth_img) * 255 # White background
            binary_img[depth_img <= wall_threshold] = 0 # Black walls
            binary_img[~house_mask] = 255 # Background
            
        # Clean up
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
        inverted = 255 - binary_img
        inverted = cv2.morphologyEx(inverted, cv2.MORPH_CLOSE, kernel, iterations=1)
        inverted = cv2.morphologyEx(inverted, cv2.MORPH_OPEN, kernel, iterations=1)
        binary_img = 255 - inverted
        
        # Invert as requested by user (White Walls, Black Background)
        binary_img = 255 - binary_img
        
        # Save the binary image for debugging
        binary_output_path = output_dir / "glb_binary_input.png"
        cv2.imwrite(str(binary_output_path), binary_img)
        logger.info(f"Saved binary floorplan input to {binary_output_path}")
        
        # Encode to bytes
        success, encoded_img = cv2.imencode('.png', binary_img)
        return encoded_img.tobytes(), bounds_info

    async def segment_floorplan(self, image_path: str, required_rooms: List[str], debug_output_dir: Optional[str] = None) -> FloorPlanGrid:
        """
        Segment a floor plan image into rooms and assign room names.

        Args:
            image_path: Path to the floor plan image OR .glb file.
            required_rooms: List of room names expected (e.g., ["Living Room", "Bedroom"]).
            debug_output_dir: Optional directory to save intermediate images.

        Returns:
            FloorPlanGrid populated with room cells.
        """
        original_bytes = None
        
        # Check if input is GLB
        if image_path.lower().endswith(('.glb', '.gltf')):
            logger.info(f"Processing GLB file: {image_path}")
            
            # Use temporary directory for Blender output if debug dir not provided
            if debug_output_dir:
                work_dir = Path(debug_output_dir)
                work_dir.mkdir(parents=True, exist_ok=True)
                cleanup = False
            else:
                temp_dir = tempfile.TemporaryDirectory()
                work_dir = Path(temp_dir.name)
                cleanup = True
                
            try:
                original_bytes, _ = self._generate_binary_from_glb(image_path, work_dir)
                
                # If using temp dir, we might want to save the binary for debugging if requested?
                # But logic above handles saving to debug_output_dir inside _generate_binary_from_glb
                # implicitly by using work_dir.
                
            finally:
                if cleanup:
                    temp_dir.cleanup()
        else:
            # 1. Read original image directly
            with open(image_path, "rb") as f:
                original_bytes = f.read()

        # Convert to base64 for API
        original_b64 = f"data:image/png;base64,{base64.b64encode(original_bytes).decode('utf-8')}"

        # 2. Call Nano Banana to segment rooms (color fill)
        logger.info("Sending image to Nano Banana for room segmentation...")
        segmented_url = await generate_segmented_rooms(original_b64)

        # 3. Download segmented image
        if segmented_url.startswith("data:image"):
            # Handle base64 data URL
            header, encoded = segmented_url.split(",", 1)
            segmented_bytes = base64.b64decode(encoded)
        else:
            # Handle regular URL
            resp = requests.get(segmented_url)
            resp.raise_for_status()
            segmented_bytes = resp.content

        # Save raw Nano Banana output if debug dir is provided
        if debug_output_dir:
            out_dir = Path(debug_output_dir)
            out_dir.mkdir(parents=True, exist_ok=True)
            
            nano_output_path = out_dir / "nano_banana_output.png"
            with open(nano_output_path, "wb") as f:
                f.write(segmented_bytes)
            logger.info(f"Saved Nano Banana output to {nano_output_path}")

        # 4. Process image to find rooms on FULL-RESOLUTION image
        segmented_img = self._load_image_cv2(segmented_bytes)
        img_h, img_w = segmented_img.shape[:2]

        # Calculate grid dimensions
        grid_width = int(self.target_width_m / self.cell_size_m)
        scale_factor = grid_width / img_w
        grid_height = int(img_h * scale_factor)

        # 5. Extract room regions on full-res image using connected components
        label_map, n_regions = self._extract_regions(segmented_img)

        # 6. Downsample label map to grid cells (majority vote per cell)
        grid_labels = self._downsample_to_grid(
            label_map, img_h, img_w, grid_height, grid_width
        )

        # Collect cells per region label
        region_cells: dict[int, set[tuple[int, int]]] = defaultdict(set)
        for i in range(grid_height):
            for j in range(grid_width):
                lbl = grid_labels[i, j]
                if lbl > 0:
                    region_cells[lbl].add((i, j))

        # Filter tiny regions (< 1 m²)
        min_cells = max(1, int(1.0 / (self.cell_size_m ** 2)))
        region_cells = {k: v for k, v in region_cells.items() if len(v) >= min_cells}

        # 7. Assign room names based on area
        room_mapping = self._assign_rooms(region_cells, required_rooms)

        # Debug: save binary mask
        if debug_output_dir:
            binary_mask = np.zeros((grid_height, grid_width), dtype=np.uint8)
            for cells in region_cells.values():
                for ci, cj in cells:
                    binary_mask[ci, cj] = 255
            binary_path = out_dir / "floorplan_binary_mask.png"
            cv2.imwrite(str(binary_path), binary_mask)

        # 8. Build Grid
        grid = FloorPlanGrid(
            width=grid_width,
            height=grid_height,
            cell_size=self.cell_size_m,
        )

        for label_id, cells in region_cells.items():
            room_name = room_mapping.get(label_id)
            if room_name:
                grid.room_cells[room_name] = cells

        logger.info(
            "Grid %dx%d, %d rooms: %s",
            grid.width, grid.height, grid.num_rooms,
            {n: f"{grid.room_area_sqm(n):.1f}m²" for n in grid.room_names},
        )
        return grid

    def _load_image_cv2(self, image_bytes: bytes) -> np.ndarray:
        nparr = np.frombuffer(image_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        return cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

    def _extract_regions(self, img: np.ndarray) -> tuple[np.ndarray, int]:
        """Extract room regions using connected component analysis on full-res image.

        Works by:
        1. Masking out walls (black) and background (white/near-white)
        2. Quantizing remaining colors (round to nearest 64)
        3. Running connected components PER quantized color
        4. Each connected blob = one room (handles same-color separate rooms)

        Returns:
            (label_map, n_regions) where label_map[y, x] is the region ID (0 = wall/bg).
        """
        height, width = img.shape[:2]
        r, g, b = img[:, :, 0].astype(np.int16), img[:, :, 1].astype(np.int16), img[:, :, 2].astype(np.int16)

        # Mask: black walls, white background, near-gray
        is_dark = (r < 50) & (g < 50) & (b < 50)
        is_bright = (r > 220) & (g > 220) & (b > 220)
        chroma = np.abs(r - g) + np.abs(g - b) + np.abs(b - r)
        is_gray = chroma < 40
        colored_mask = ~is_dark & ~is_bright & ~is_gray

        # Quantize colors to reduce noise (round to nearest 64)
        quantized = (img // 64).astype(np.uint8)

        # Build label map
        label_map = np.zeros((height, width), dtype=np.int32)
        next_label = 1

        # Get unique quantized colors among colored pixels
        colored_pixels = quantized[colored_mask]
        if len(colored_pixels) == 0:
            logger.warning("No colored pixels found in segmented image")
            return label_map, 0

        unique_qcolors = np.unique(colored_pixels.reshape(-1, 3), axis=0)
        logger.info("Found %d unique quantized colors", len(unique_qcolors))

        for qc in unique_qcolors:
            # Binary mask of pixels with this quantized color
            match = (
                (quantized[:, :, 0] == qc[0])
                & (quantized[:, :, 1] == qc[1])
                & (quantized[:, :, 2] == qc[2])
                & colored_mask
            )
            n_labels, cc_labels = cv2.connectedComponents(match.astype(np.uint8), connectivity=4)
            for cc_id in range(1, n_labels):
                region_mask = cc_labels == cc_id
                pixel_count = np.count_nonzero(region_mask)
                # Skip tiny noise blobs (< 0.3% of image area)
                if pixel_count < height * width * 0.003:
                    continue
                label_map[region_mask] = next_label
                next_label += 1

        logger.info("Extracted %d room regions from colored image", next_label - 1)
        return label_map, next_label - 1

    @staticmethod
    def _downsample_to_grid(
        label_map: np.ndarray,
        img_h: int, img_w: int,
        grid_h: int, grid_w: int,
    ) -> np.ndarray:
        """Downsample a full-res label map to grid cells using majority vote.

        Each grid cell (i, j) covers a rectangular patch in the image.
        The most common non-zero label in that patch wins.
        """
        grid_labels = np.zeros((grid_h, grid_w), dtype=np.int32)
        cell_h = img_h / grid_h
        cell_w = img_w / grid_w

        for i in range(grid_h):
            y0 = int(i * cell_h)
            y1 = int((i + 1) * cell_h)
            for j in range(grid_w):
                x0 = int(j * cell_w)
                x1 = int((j + 1) * cell_w)
                patch = label_map[y0:y1, x0:x1].ravel()
                nonzero = patch[patch > 0]
                if len(nonzero) == 0:
                    continue
                # Majority vote
                counts = np.bincount(nonzero)
                grid_labels[i, j] = counts.argmax()

        return grid_labels

    def _assign_rooms(
        self,
        region_cells: dict[int, set[tuple[int, int]]],
        required_rooms: list[str],
    ) -> dict[int, str]:
        """Assign room names to region labels based on area heuristics.

        Strategy: sort regions by area (descending), sort required room names
        by expected size (living/kitchen > bedroom > bathroom), match 1:1.
        Extra regions get auto-names based on area.
        """
        cell_area = self.cell_size_m ** 2

        # Sort regions largest first
        sorted_labels = sorted(region_cells.keys(), key=lambda k: len(region_cells[k]), reverse=True)

        # Sort required rooms: largest expected first
        def room_size_priority(name: str) -> int:
            n = name.lower()
            if "living" in n or "lounge" in n:
                return 100
            if "kitchen" in n or "dining" in n:
                return 90
            if "master" in n:
                return 80
            if "bed" in n:
                return 70
            if "bath" in n or "toilet" in n or "wc" in n:
                return 30
            if "hall" in n or "corridor" in n or "entry" in n:
                return 20
            if "storage" in n or "closet" in n or "laundry" in n:
                return 10
            return 50

        sorted_rooms = sorted(required_rooms, key=room_size_priority, reverse=True)

        mapping: dict[int, str] = {}
        used_names: set[str] = set()

        for idx, label_id in enumerate(sorted_labels):
            area = len(region_cells[label_id]) * cell_area

            if idx < len(sorted_rooms):
                name = sorted_rooms[idx]
            else:
                # Auto-name by area
                if area > 15:
                    name = f"Living Area {idx + 1}"
                elif area > 8:
                    name = f"Bedroom {idx + 1}"
                elif area > 3:
                    name = f"Bathroom {idx + 1}"
                else:
                    name = f"Storage {idx + 1}"

            # Ensure unique names
            base = name
            suffix = 2
            while name in used_names:
                name = f"{base} {suffix}"
                suffix += 1

            mapping[label_id] = name
            used_names.add(name)

        return mapping
