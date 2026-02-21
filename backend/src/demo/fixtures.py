"""Pre-built demo scenarios with real IKEA product names and prices.

Three complete scenarios for live demos and fallback when APIs fail:
- Living Room: modern minimalist
- Bedroom: scandinavian
- Home Office: industrial
"""

from ..models.schemas import (
    DoorWindow,
    FurnitureDimensions,
    FurnitureItem,
    FurniturePlacement,
    PlacementResult,
    Position3D,
    RoomData,
    UserPreferences,
)


# =============================================================================
# LIVING ROOM — Modern Minimalist, EUR 3000, 5.2 x 4.0 m
# =============================================================================

LIVING_ROOM_PREFERENCES = UserPreferences(
    style="modern minimalist",
    budget_min=1500,
    budget_max=3000,
    currency="EUR",
    colors=["white", "grey", "natural oak"],
    room_type="living_room",
    lifestyle=["entertaining", "wfh"],
    must_haves=["sofa", "coffee table", "TV stand"],
    dealbreakers=["heavy patterns", "dark wood"],
    existing_furniture=[],
)

LIVING_ROOM_DATA = RoomData(
    name="Living Room",
    width_m=5.2,
    length_m=4.0,
    height_m=2.7,
    doors=[
        DoorWindow(wall="south", position_m=1.0, width_m=0.9),
        DoorWindow(wall="east", position_m=2.5, width_m=0.9),
    ],
    windows=[
        DoorWindow(wall="north", position_m=1.5, width_m=1.4),
        DoorWindow(wall="west", position_m=1.0, width_m=1.2),
    ],
    shape="rectangular",
    area_sqm=20.8,
)

LIVING_ROOM_FURNITURE: list[FurnitureItem] = [
    FurnitureItem(
        id="demo-lr-001",
        retailer="IKEA",
        name="KIVIK 3-seat sofa",
        price=599.0,
        currency="EUR",
        dimensions=FurnitureDimensions(width_cm=228, depth_cm=95, height_cm=83),
        image_url="https://www.ikea.com/fr/fr/images/products/kivik-canape-3-places-orrsta-gris-clair__0479965_pe619105_s5.jpg",
        product_url="https://www.ikea.com/fr/fr/p/kivik-canape-3-places-orrsta-gris-clair-s29932726/",
        category="sofa",
        selected=True,
    ),
    FurnitureItem(
        id="demo-lr-002",
        retailer="IKEA",
        name="STOCKHOLM coffee table",
        price=249.0,
        currency="EUR",
        dimensions=FurnitureDimensions(width_cm=180, depth_cm=59, height_cm=40),
        image_url="https://www.ikea.com/fr/fr/images/products/stockholm-table-basse-plaque-noyer__0178008_pe330564_s5.jpg",
        product_url="https://www.ikea.com/fr/fr/p/stockholm-table-basse-plaque-noyer-40239719/",
        category="coffee table",
        selected=True,
    ),
    FurnitureItem(
        id="demo-lr-003",
        retailer="IKEA",
        name="BESTA TV bench",
        price=199.0,
        currency="EUR",
        dimensions=FurnitureDimensions(width_cm=180, depth_cm=42, height_cm=38),
        image_url="https://www.ikea.com/fr/fr/images/products/besta-banc-tv-blanc__0783848_pe761763_s5.jpg",
        product_url="https://www.ikea.com/fr/fr/p/besta-banc-tv-blanc-50299885/",
        category="TV stand",
        selected=True,
    ),
    FurnitureItem(
        id="demo-lr-004",
        retailer="IKEA",
        name="KALLAX shelving unit 4x2",
        price=79.0,
        currency="EUR",
        dimensions=FurnitureDimensions(width_cm=147, depth_cm=39, height_cm=77),
        image_url="https://www.ikea.com/fr/fr/images/products/kallax-etagere-blanc__0644757_pe702939_s5.jpg",
        product_url="https://www.ikea.com/fr/fr/p/kallax-etagere-blanc-70301537/",
        category="shelving",
        selected=True,
    ),
    FurnitureItem(
        id="demo-lr-005",
        retailer="IKEA",
        name="SKADIS pegboard",
        price=19.0,
        currency="EUR",
        dimensions=FurnitureDimensions(width_cm=76, depth_cm=12, height_cm=56),
        image_url="https://www.ikea.com/fr/fr/images/products/skadis-panneau-perfore-blanc__0586665_pe672458_s5.jpg",
        product_url="https://www.ikea.com/fr/fr/p/skadis-panneau-perfore-blanc-10321618/",
        category="wall storage",
        selected=True,
    ),
    FurnitureItem(
        id="demo-lr-006",
        retailer="IKEA",
        name="TERTIAL work lamp",
        price=12.0,
        currency="EUR",
        dimensions=FurnitureDimensions(width_cm=17, depth_cm=17, height_cm=44),
        image_url="https://www.ikea.com/fr/fr/images/products/tertial-lampe-de-bureau-gris-fonce__0809807_pe771046_s5.jpg",
        product_url="https://www.ikea.com/fr/fr/p/tertial-lampe-de-bureau-gris-fonce-50507830/",
        category="lighting",
        selected=True,
    ),
]

LIVING_ROOM_PLACEMENT = PlacementResult(
    placements=[
        FurniturePlacement(
            item_id="demo-lr-001",
            name="KIVIK 3-seat sofa",
            position=Position3D(x=2.6, y=0, z=3.2),
            rotation_y_degrees=0,
            reasoning="Centered against south wall, facing north window for natural light",
        ),
        FurniturePlacement(
            item_id="demo-lr-002",
            name="STOCKHOLM coffee table",
            position=Position3D(x=2.6, y=0, z=2.2),
            rotation_y_degrees=0,
            reasoning="Centered in front of sofa, accessible from all sides",
        ),
        FurniturePlacement(
            item_id="demo-lr-003",
            name="BESTA TV bench",
            position=Position3D(x=2.6, y=0, z=0.2),
            rotation_y_degrees=0,
            reasoning="Against north wall, facing sofa for TV viewing",
        ),
        FurniturePlacement(
            item_id="demo-lr-004",
            name="KALLAX shelving unit 4x2",
            position=Position3D(x=4.9, y=0, z=1.5),
            rotation_y_degrees=90,
            reasoning="Along east wall between door and corner, storage unit",
        ),
        FurniturePlacement(
            item_id="demo-lr-005",
            name="SKADIS pegboard",
            position=Position3D(x=0.1, y=1.2, z=2.5),
            rotation_y_degrees=90,
            reasoning="Mounted on west wall above eye level near window",
        ),
        FurniturePlacement(
            item_id="demo-lr-006",
            name="TERTIAL work lamp",
            position=Position3D(x=4.8, y=0.77, z=0.5),
            rotation_y_degrees=0,
            reasoning="On corner shelf near east wall for reading light",
        ),
    ]
)


# =============================================================================
# BEDROOM — Scandinavian, EUR 1500, 4.0 x 3.5 m
# =============================================================================

BEDROOM_PREFERENCES = UserPreferences(
    style="scandinavian",
    budget_min=800,
    budget_max=1500,
    currency="EUR",
    colors=["white", "light birch", "soft blue"],
    room_type="bedroom",
    lifestyle=["relaxation"],
    must_haves=["bed frame", "wardrobe", "bedside table"],
    dealbreakers=["dark colours", "plastic"],
    existing_furniture=[],
)

BEDROOM_DATA = RoomData(
    name="Bedroom",
    width_m=4.0,
    length_m=3.5,
    height_m=2.7,
    doors=[
        DoorWindow(wall="south", position_m=0.5, width_m=0.8),
    ],
    windows=[
        DoorWindow(wall="north", position_m=1.5, width_m=1.2),
    ],
    shape="rectangular",
    area_sqm=14.0,
)

BEDROOM_FURNITURE: list[FurnitureItem] = [
    FurnitureItem(
        id="demo-br-001",
        retailer="IKEA",
        name="MALM bed frame 160x200",
        price=249.0,
        currency="EUR",
        dimensions=FurnitureDimensions(width_cm=176, depth_cm=209, height_cm=100),
        image_url="https://www.ikea.com/fr/fr/images/products/malm-cadre-de-lit-haut-teinte-blanc-leirsund__0638608_pe698416_s5.jpg",
        product_url="https://www.ikea.com/fr/fr/p/malm-cadre-de-lit-haut-teinte-blanc-leirsund-s89011564/",
        category="bed frame",
        selected=True,
    ),
    FurnitureItem(
        id="demo-br-002",
        retailer="IKEA",
        name="PAX wardrobe 150x60x201",
        price=435.0,
        currency="EUR",
        dimensions=FurnitureDimensions(width_cm=150, depth_cm=60, height_cm=201),
        image_url="https://www.ikea.com/fr/fr/images/products/pax-armoire-blanc__0579581_pe669816_s5.jpg",
        product_url="https://www.ikea.com/fr/fr/p/pax-armoire-blanc-s19028023/",
        category="wardrobe",
        selected=True,
    ),
    FurnitureItem(
        id="demo-br-003",
        retailer="IKEA",
        name="HEMNES bedside table",
        price=59.0,
        currency="EUR",
        dimensions=FurnitureDimensions(width_cm=46, depth_cm=35, height_cm=70),
        image_url="https://www.ikea.com/fr/fr/images/products/hemnes-table-de-chevet-teinte-blanc__0530853_pe647199_s5.jpg",
        product_url="https://www.ikea.com/fr/fr/p/hemnes-table-de-chevet-teinte-blanc-40200547/",
        category="bedside table",
        selected=True,
    ),
    FurnitureItem(
        id="demo-br-004",
        retailer="IKEA",
        name="HEMNES bedside table",
        price=59.0,
        currency="EUR",
        dimensions=FurnitureDimensions(width_cm=46, depth_cm=35, height_cm=70),
        image_url="https://www.ikea.com/fr/fr/images/products/hemnes-table-de-chevet-teinte-blanc__0530853_pe647199_s5.jpg",
        product_url="https://www.ikea.com/fr/fr/p/hemnes-table-de-chevet-teinte-blanc-40200547/",
        category="bedside table",
        selected=True,
    ),
    FurnitureItem(
        id="demo-br-005",
        retailer="IKEA",
        name="SKURUP floor/reading lamp",
        price=39.0,
        currency="EUR",
        dimensions=FurnitureDimensions(width_cm=28, depth_cm=28, height_cm=155),
        image_url="https://www.ikea.com/fr/fr/images/products/skurup-lampadaire-liseuse-noir__0637348_pe698321_s5.jpg",
        product_url="https://www.ikea.com/fr/fr/p/skurup-lampadaire-liseuse-noir-20471270/",
        category="lighting",
        selected=True,
    ),
]

BEDROOM_PLACEMENT = PlacementResult(
    placements=[
        FurniturePlacement(
            item_id="demo-br-001",
            name="MALM bed frame 160x200",
            position=Position3D(x=2.0, y=0, z=1.75),
            rotation_y_degrees=0,
            reasoning="Centered in room, headboard against north wall",
        ),
        FurniturePlacement(
            item_id="demo-br-002",
            name="PAX wardrobe 150x60x201",
            position=Position3D(x=3.2, y=0, z=3.2),
            rotation_y_degrees=180,
            reasoning="Against south wall opposite bed, away from door swing",
        ),
        FurniturePlacement(
            item_id="demo-br-003",
            name="HEMNES bedside table (left)",
            position=Position3D(x=0.9, y=0, z=0.8),
            rotation_y_degrees=0,
            reasoning="Left side of bed, near headboard",
        ),
        FurniturePlacement(
            item_id="demo-br-004",
            name="HEMNES bedside table (right)",
            position=Position3D(x=3.1, y=0, z=0.8),
            rotation_y_degrees=0,
            reasoning="Right side of bed, symmetric with left",
        ),
        FurniturePlacement(
            item_id="demo-br-005",
            name="SKURUP floor/reading lamp",
            position=Position3D(x=0.5, y=0, z=0.4),
            rotation_y_degrees=0,
            reasoning="Corner near left bedside table for reading",
        ),
    ]
)


# =============================================================================
# HOME OFFICE — Industrial, EUR 2000, 3.0 x 2.5 m
# =============================================================================

OFFICE_PREFERENCES = UserPreferences(
    style="industrial",
    budget_min=1000,
    budget_max=2000,
    currency="EUR",
    colors=["black", "walnut", "steel grey"],
    room_type="office",
    lifestyle=["wfh"],
    must_haves=["desk", "office chair", "shelving"],
    dealbreakers=["flimsy furniture"],
    existing_furniture=[],
)

OFFICE_DATA = RoomData(
    name="Home Office",
    width_m=3.0,
    length_m=2.5,
    height_m=2.7,
    doors=[
        DoorWindow(wall="south", position_m=1.0, width_m=0.8),
    ],
    windows=[
        DoorWindow(wall="north", position_m=0.8, width_m=1.0),
    ],
    shape="rectangular",
    area_sqm=7.5,
)

OFFICE_FURNITURE: list[FurnitureItem] = [
    FurnitureItem(
        id="demo-of-001",
        retailer="IKEA",
        name="BEKANT desk 160x80",
        price=349.0,
        currency="EUR",
        dimensions=FurnitureDimensions(width_cm=160, depth_cm=80, height_cm=65),
        image_url="https://www.ikea.com/fr/fr/images/products/bekant-bureau-plaque-chene-blanc-noir__0723167_pe733936_s5.jpg",
        product_url="https://www.ikea.com/fr/fr/p/bekant-bureau-plaque-chene-blanc-noir-s19282665/",
        category="desk",
        selected=True,
    ),
    FurnitureItem(
        id="demo-of-002",
        retailer="IKEA",
        name="MARKUS office chair",
        price=229.0,
        currency="EUR",
        dimensions=FurnitureDimensions(width_cm=62, depth_cm=60, height_cm=140),
        image_url="https://www.ikea.com/fr/fr/images/products/markus-chaise-de-bureau-glose-noir__0724718_pe734597_s5.jpg",
        product_url="https://www.ikea.com/fr/fr/p/markus-chaise-de-bureau-glose-noir-40103100/",
        category="office chair",
        selected=True,
    ),
    FurnitureItem(
        id="demo-of-003",
        retailer="IKEA",
        name="FJALLBO shelving unit",
        price=129.0,
        currency="EUR",
        dimensions=FurnitureDimensions(width_cm=100, depth_cm=36, height_cm=136),
        image_url="https://www.ikea.com/fr/fr/images/products/fjaellbo-etagere-noir__0476185_pe616397_s5.jpg",
        product_url="https://www.ikea.com/fr/fr/p/fjaellbo-etagere-noir-70339291/",
        category="shelving",
        selected=True,
    ),
    FurnitureItem(
        id="demo-of-004",
        retailer="IKEA",
        name="ALEX drawer unit",
        price=99.0,
        currency="EUR",
        dimensions=FurnitureDimensions(width_cm=36, depth_cm=58, height_cm=70),
        image_url="https://www.ikea.com/fr/fr/images/products/alex-caisson-a-tiroirs-blanc__0604180_pe681027_s5.jpg",
        product_url="https://www.ikea.com/fr/fr/p/alex-caisson-a-tiroirs-blanc-10192824/",
        category="storage",
        selected=True,
    ),
]

OFFICE_PLACEMENT = PlacementResult(
    placements=[
        FurniturePlacement(
            item_id="demo-of-001",
            name="BEKANT desk 160x80",
            position=Position3D(x=1.5, y=0, z=0.4),
            rotation_y_degrees=0,
            reasoning="Against north wall facing window for natural light",
        ),
        FurniturePlacement(
            item_id="demo-of-002",
            name="MARKUS office chair",
            position=Position3D(x=1.5, y=0, z=1.2),
            rotation_y_degrees=0,
            reasoning="In front of desk with room to roll back",
        ),
        FurniturePlacement(
            item_id="demo-of-003",
            name="FJALLBO shelving unit",
            position=Position3D(x=2.7, y=0, z=1.3),
            rotation_y_degrees=90,
            reasoning="Against east wall, accessible from desk",
        ),
        FurniturePlacement(
            item_id="demo-of-004",
            name="ALEX drawer unit",
            position=Position3D(x=0.2, y=0, z=0.4),
            rotation_y_degrees=0,
            reasoning="Under/beside desk on left side, within arm reach",
        ),
    ]
)


# =============================================================================
# Scenario registry
# =============================================================================

SCENARIOS = {
    "living_room": {
        "preferences": LIVING_ROOM_PREFERENCES,
        "room_data": LIVING_ROOM_DATA,
        "furniture": LIVING_ROOM_FURNITURE,
        "placement": LIVING_ROOM_PLACEMENT,
    },
    "bedroom": {
        "preferences": BEDROOM_PREFERENCES,
        "room_data": BEDROOM_DATA,
        "furniture": BEDROOM_FURNITURE,
        "placement": BEDROOM_PLACEMENT,
    },
    "office": {
        "preferences": OFFICE_PREFERENCES,
        "room_data": OFFICE_DATA,
        "furniture": OFFICE_FURNITURE,
        "placement": OFFICE_PLACEMENT,
    },
}


def get_fallback_furniture(room_type: str) -> list[FurnitureItem]:
    """Return demo furniture for a given room type. Falls back to living room."""
    key = room_type.lower().replace(" ", "_")
    if key in SCENARIOS:
        return SCENARIOS[key]["furniture"]
    # Try partial match
    for k in SCENARIOS:
        if k in key or key in k:
            return SCENARIOS[k]["furniture"]
    return SCENARIOS["living_room"]["furniture"]


def get_fallback_placement(room_type: str) -> PlacementResult:
    """Return demo placement for a given room type. Falls back to living room."""
    key = room_type.lower().replace(" ", "_")
    if key in SCENARIOS:
        return SCENARIOS[key]["placement"]
    for k in SCENARIOS:
        if k in key or key in k:
            return SCENARIOS[k]["placement"]
    return SCENARIOS["living_room"]["placement"]
