"""Prompt template for floorplan image analysis."""


def floorplan_analysis_prompt() -> str:
    """Return the system prompt for analysing a floorplan image.

    Use with `call_gemini_with_image(prompt, image)` where `prompt` is this
    function's return value and `image` is the floorplan image.
    """
    return """\
You are an expert interior-design assistant. Analyse the attached floorplan image and extract structured room data.

Return ONLY valid JSON (no markdown fences, no commentary) matching this schema:

{
  "rooms": [
    {
      "name": "string — e.g. living_room, bedroom, kitchen, bathroom, hallway, studio",
      "width_m": "number — room width in metres (east-west dimension)",
      "length_m": "number — room length in metres (north-south dimension)",
      "height_m": "number — ceiling height, default 2.7 if unknown",
      "x_offset_m": "number — X position of room's south-west corner within the apartment (0 = apartment west edge)",
      "z_offset_m": "number — Z position of room's south-west corner within the apartment (0 = apartment south edge)",
      "doors": [
        { "wall": "north|south|east|west", "position_m": "number — distance from left edge of that wall", "width_m": "number" }
      ],
      "windows": [
        { "wall": "north|south|east|west", "position_m": "number", "width_m": "number" }
      ],
      "shape": "rectangular|l_shaped|irregular",
      "area_sqm": "number — width_m * length_m for rectangular rooms"
    }
  ]
}

## Coordinate System
- The apartment's south-west corner (bottom-left of image) is origin (0, 0).
- X axis: west → east (left → right in the image).
- Z axis: south → north (bottom → top in the image).
- North = top of image.
- x_offset_m and z_offset_m define where each room's south-west corner sits within the apartment.

## Guidelines
- Use metric units throughout.
- If the image contains a scale bar, use it; otherwise estimate from standard door widths (≈0.9 m).
- Mark walls using compass directions (north = top of image).
- Include ALL rooms visible in the floorplan.
- Calculate area_sqm as width_m * length_m for rectangular rooms.
- CRITICAL: x_offset_m and z_offset_m must be accurate — they define where furniture gets placed in the 3D model."""


def parse_floorplan_prompt() -> str:
    """Simplified prompt when the floorplan is described in text rather than an image."""
    return """\
Convert the following room description into structured JSON matching this schema:

{
  "rooms": [
    {
      "name": "string",
      "width_m": "number",
      "length_m": "number",
      "height_m": "number (default 2.7)",
      "doors": [{ "wall": "string", "position_m": "number", "width_m": "number" }],
      "windows": [{ "wall": "string", "position_m": "number", "width_m": "number" }],
      "shape": "rectangular|l_shaped|irregular",
      "area_sqm": "number"
    }
  ]
}

Return ONLY valid JSON."""
