from __future__ import annotations

import os

from qdrant_client import QdrantClient
from qdrant_client.models import Distance, PointStruct, VectorParams
from sentence_transformers import SentenceTransformer

from .models import FurnitureItem

COLLECTION = "ikea_furniture"
VECTOR_DIM = 384  # all-MiniLM-L6-v2 output dimension
SIMILARITY_THRESHOLD = 0.85

_qdrant: QdrantClient | None = None
_embedder: SentenceTransformer | None = None


def _get_qdrant() -> QdrantClient:
    global _qdrant
    if _qdrant is None:
        url = os.environ.get("QDRANT_URL", "")
        api_key = os.environ.get("QDRANT_API_KEY", "")
        if url:
            _qdrant = QdrantClient(url=url, api_key=api_key or None)
        else:
            # In-memory mode for local dev without a Qdrant server
            _qdrant = QdrantClient(":memory:")
        _ensure_collection(_qdrant)
    return _qdrant


def _get_embedder() -> SentenceTransformer:
    global _embedder
    if _embedder is None:
        _embedder = SentenceTransformer("all-MiniLM-L6-v2")
    return _embedder


def _ensure_collection(client: QdrantClient):
    collections = [c.name for c in client.get_collections().collections]
    if COLLECTION not in collections:
        client.create_collection(
            collection_name=COLLECTION,
            vectors_config=VectorParams(size=VECTOR_DIM, distance=Distance.COSINE),
        )


def _build_search_text(
    description: str,
    category: str | None = None,
    dimensions: str | None = None,
) -> str:
    parts = [description]
    if category:
        parts.append(category)
    if dimensions:
        parts.append(dimensions)
    return " ".join(parts)


def embed(text: str) -> list[float]:
    return _get_embedder().encode(text).tolist()


def search_similar(
    description: str,
    category: str | None = None,
    dimensions: str | None = None,
    threshold: float = SIMILARITY_THRESHOLD,
) -> FurnitureItem | None:
    """Search Qdrant for a cached furniture item similar to the query."""
    text = _build_search_text(description, category, dimensions)
    vector = embed(text)

    results = _get_qdrant().query_points(
        collection_name=COLLECTION,
        query=vector,
        limit=1,
        with_payload=True,
    )

    if results.points and results.points[0].score >= threshold:
        payload = results.points[0].payload
        return FurnitureItem(**payload)
    return None


def upsert_item(item: FurnitureItem, description: str | None = None):
    """Store a furniture item in Qdrant with its embedding."""
    text = _build_search_text(
        description or item.description or f"{item.name} {item.type_name}",
        item.category,
        item.dimensions,
    )
    vector = embed(text)

    point = PointStruct(
        id=abs(hash(item.item_code)) % (2**63),
        vector=vector,
        payload=item.model_dump(),
    )

    _get_qdrant().upsert(collection_name=COLLECTION, points=[point])
