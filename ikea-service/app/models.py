from __future__ import annotations

from pydantic import BaseModel


class ProductImage(BaseModel):
    url: str
    alt: str | None = None
    type: str | None = None  # MAIN_PRODUCT_IMAGE, CONTEXT_PRODUCT_IMAGE, etc.


class Variant(BaseModel):
    item_code: str
    name: str | None = None
    description: str | None = None
    color: str | None = None
    dimensions: str | None = None
    price: float | None = None
    currency: str | None = None
    image_url: str | None = None
    buy_url: str | None = None


class ModelFile(BaseModel):
    format: str  # "glb" or "usdz"
    url: str  # DigitalOcean Spaces URL (after upload) or IKEA CDN URL
    source_url: str  # Original IKEA CDN URL


class FurnitureItem(BaseModel):
    item_code: str
    name: str | None = None
    type_name: str | None = None
    description: str | None = None
    dimensions: str | None = None
    price: float | None = None
    currency: str | None = None
    image_url: str | None = None
    images: list[ProductImage] = []
    buy_url: str | None = None
    category: str | None = None
    color: str | None = None
    rating: float | None = None
    rating_count: int | None = None
    variants: list[Variant] = []
    model_files: list[ModelFile] = []


class SearchResponse(BaseModel):
    query: str
    items: list[FurnitureItem]


class StockInfo(BaseModel):
    item_code: str
    available: dict


class FurnitureQuery(BaseModel):
    description: str  # e.g. "white bookcase 80cm wide"
    category: str | None = None  # e.g. "bookcase", "sofa"
    dimensions: str | None = None  # e.g. "80x28x202 cm"


class FurnitureRequest(BaseModel):
    items: list[FurnitureQuery]


class PipelineResult(BaseModel):
    query: FurnitureQuery
    source: str  # "cache" or "ikea_api"
    item: FurnitureItem | None = None


class PipelineResponse(BaseModel):
    results: list[PipelineResult]
