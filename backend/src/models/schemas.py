"""Pydantic models for the HomeDesigner pipeline."""

from pydantic import BaseModel

# --- User Preferences (from voice consultation) ---


class UserPreferences(BaseModel):
    style: str = ""  # modern, minimalist, scandinavian, industrial, etc.
    budget_min: float = 0
    budget_max: float = 10000
    currency: str = "EUR"
    colors: list[str] = []
    room_type: str = ""  # living_room, bedroom, office, etc.
    lifestyle: list[str] = []  # kids, pets, wfh, entertaining
    must_haves: list[str] = []
    dealbreakers: list[str] = []
    existing_furniture: list[str] = []


# --- Floorplan / Room Data ---


class DoorWindow(BaseModel):
    wall: str  # north, south, east, west
    position_m: float
    width_m: float


class RoomData(BaseModel):
    name: str
    width_m: float
    length_m: float
    height_m: float = 2.7
    doors: list[DoorWindow] = []
    windows: list[DoorWindow] = []
    shape: str = "rectangular"
    area_sqm: float = 0


class FloorplanAnalysis(BaseModel):
    rooms: list[RoomData]


# --- Furniture ---


class FurnitureDimensions(BaseModel):
    width_cm: float
    depth_cm: float
    height_cm: float


class FurnitureItem(BaseModel):
    id: str
    retailer: str
    name: str
    price: float
    currency: str = "EUR"
    dimensions: FurnitureDimensions | None = None
    image_url: str = ""
    product_url: str = ""
    glb_url: str = ""
    category: str = ""
    selected: bool = False


class ShoppingListItem(BaseModel):
    item: str
    query: str
    max_width_cm: float = 0
    budget_min: float = 0
    budget_max: float = 0
    priority: str = "essential"  # essential, nice_to_have


# --- Placement ---


class Position3D(BaseModel):
    x: float
    y: float
    z: float


class FurniturePlacement(BaseModel):
    item_id: str
    name: str
    position: Position3D
    rotation_y_degrees: float = 0
    reasoning: str = ""


class PlacementResult(BaseModel):
    placements: list[FurniturePlacement]


# --- Pipeline ---


class PipelineStatus(BaseModel):
    session_id: str
    phase: str
    status: str  # pending, running, completed, failed
    progress: float = 0  # 0-1
    message: str = ""
