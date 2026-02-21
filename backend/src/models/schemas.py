"""Pydantic models for the HomeDesigner pipeline."""

from pydantic import BaseModel, Field

# --- Canonical Design Brief (unified schema for voice intake, DB, Miro, pipeline) ---


class DesignBrief(BaseModel):
    """
    Canonical design brief JSON collected during voice consultation.
    Used internally by voice intake agent, stored in DB, and sent to Miro.
    Single source of truth for design preferences across the pipeline.
    """

    budget: float | None = Field(
        default=None, description="Total budget as a number (EUR or specified currency)"
    )
    currency: str = Field(default="EUR", description="Currency code (ISO 4217)")
    style: list[str] = Field(
        default_factory=list,
        description="Design styles (e.g., modern, minimalist, scandinavian)",
    )
    avoid: list[str] = Field(
        default_factory=list, description="Things to avoid (e.g., bright colors, leather)"
    )
    rooms_priority: list[str] = Field(
        default_factory=list, description="Rooms to design (e.g., living room, bedroom)"
    )
    must_haves: list[str] = Field(
        default_factory=list, description="Essential items/features (e.g., large sofa)"
    )
    existing_items: list[str] = Field(
        default_factory=list,
        description="Furniture they already own and want to keep",
    )
    constraints: list[str] = Field(
        default_factory=list,
        description="Physical constraints (e.g., small space, low ceiling)",
    )
    vibe_words: list[str] = Field(
        default_factory=list,
        description="Mood/atmosphere words (e.g., cozy, bright, luxurious)",
    )
    reference_images: list[str] = Field(
        default_factory=list, description="URLs or descriptions of reference images"
    )
    notes: str = Field(default="", description="Additional notes or comments")

    class Config:
        json_schema_extra = {
            "example": {
                "budget": 5000,
                "currency": "EUR",
                "style": ["modern", "minimalist"],
                "avoid": ["dark colors", "leather"],
                "rooms_priority": ["living room", "home office"],
                "must_haves": ["large sofa", "standing desk"],
                "existing_items": ["white bookshelf"],
                "constraints": ["small space"],
                "vibe_words": ["cozy", "bright"],
                "reference_images": [],
                "notes": "Plant lover, work from home",
            }
        }


class DesignSession(BaseModel):
    """Session state for a design consultation."""

    session_id: str
    status: str = Field(
        default="collecting",
        description="Session phase: collecting, confirmed, finalized",
    )
    brief: DesignBrief = Field(default_factory=DesignBrief)
    history: list[dict] = Field(
        default_factory=list, description="Conversation history [{role, content}, ...]"
    )
    missing_fields: list[str] = Field(
        default_factory=list, description="Required fields still missing"
    )
    miro: dict = Field(
        default_factory=lambda: {"board_id": None, "board_url": None},
        description="Miro board metadata",
    )


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
