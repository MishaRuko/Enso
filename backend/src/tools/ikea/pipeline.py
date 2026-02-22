from __future__ import annotations

import asyncio
import logging

from .ikea_client import get_3d_models, search_products
from .models import FurnitureItem, FurnitureQuery, ModelFile, PipelineResult
from .storage import download_and_upload_model, model_exists
from .vector_db import embed, search_similar, upsert_item

logger = logging.getLogger(__name__)

# Minimum cosine similarity between query and IKEA result to accept it.
# Lower than the cache threshold (0.85) since we're comparing a short query
# against a product name+type string — different text styles.
RELEVANCE_THRESHOLD = 0.35

# Max concurrent IKEA API calls (avoid rate-limiting)
MAX_CONCURRENT_SEARCHES = 5


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = sum(x * x for x in a) ** 0.5
    norm_b = sum(x * x for x in b) ** 0.5
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def _best_match(
    query: FurnitureQuery,
    candidates: list[FurnitureItem],
) -> FurnitureItem | None:
    """Pick the most relevant IKEA result for a query using embedding similarity.

    Returns None if no candidate exceeds RELEVANCE_THRESHOLD.
    """
    query_text = query.description
    if query.category:
        query_text += f" {query.category}"
    query_vec = embed(query_text)

    best_item = None
    best_score = -1.0

    for item in candidates:
        item_text = f"{item.name or ''} {item.type_name or ''} {item.category or ''}".strip()
        if not item_text:
            continue
        item_vec = embed(item_text)
        score = _cosine_similarity(query_vec, item_vec)

        if score > best_score:
            best_score = score
            best_item = item

    if best_score < RELEVANCE_THRESHOLD:
        logger.info(
            "No relevant IKEA result for '%s' (best score %.2f < %.2f)",
            query.description, best_score, RELEVANCE_THRESHOLD,
        )
        return None

    logger.info(
        "Best IKEA match for '%s': %s %s (score %.2f)",
        query.description, best_item.name, best_item.type_name, best_score,
    )
    return best_item


async def _fetch_and_upload_models(item: FurnitureItem) -> list[ModelFile]:
    """Fetch 3D models for an item, upload GLB to DO Spaces.

    Falls back to generating a 3D model via fal.ai Trellis if IKEA has no GLB
    and the item has a product image.
    """
    # Check if we already have a model in DO Spaces (try both formats)
    for fmt in ("glb", "glb_draco"):
        existing_url = model_exists(item.item_code, fmt)
        if existing_url:
            logger.info("DO Spaces cache hit for %s (%s)", item.item_code, fmt)
            return [ModelFile(format=fmt, url=existing_url, source_url="do_spaces_cache")]

    # Try IKEA's 3D model API
    try:
        models = await get_3d_models(item.item_code)
    except Exception as e:
        logger.warning("Could not fetch 3D models for %s: %s", item.item_code, e)
        models = []

    uploaded: list[ModelFile] = []
    for model in models:
        if "glb" not in model.format:
            continue

        existing_url = model_exists(item.item_code, model.format)
        if existing_url:
            uploaded.append(
                ModelFile(format=model.format, url=existing_url, source_url=model.source_url)
            )
            continue

        try:
            spaces_url = await download_and_upload_model(
                item.item_code, model.source_url, model.format
            )
            if spaces_url:
                uploaded.append(
                    ModelFile(format=model.format, url=spaces_url, source_url=model.source_url)
                )
            else:
                uploaded.append(model)
        except Exception as e:
            logger.warning("Failed to upload model for %s: %s", item.item_code, e)
            uploaded.append(model)

    # NOTE: Trellis fallback (generating 3D models from product images) is NOT
    # done here — it's handled by the caller (e.g. generate_missing_models in
    # test_e2e.py) which deduplicates by item code and enforces a call limit.
    if not uploaded and (item.image_url or item.images):
        logger.info(
            "No IKEA GLB for %s (%s) — Trellis generation deferred to caller",
            item.item_code, item.name,
        )

    return uploaded


async def process_query(
    query: FurnitureQuery,
    semaphore: asyncio.Semaphore | None = None,
) -> PipelineResult:
    """Process a single furniture query through the pipeline."""
    # 1. Check vector DB cache (no semaphore needed, it's local/fast)
    cached = search_similar(query.description, query.category, query.dimensions)
    if cached is not None:
        logger.info("Cache hit for '%s': %s", query.description, cached.name)
        return PipelineResult(query=query, source="cache", item=cached)

    # 2. Search IKEA API (rate-limited)
    search_text = query.description
    if query.category:
        search_text += f" {query.category}"

    try:
        if semaphore:
            async with semaphore:
                results = await search_products(search_text, limit=5)
        else:
            results = await search_products(search_text, limit=5)
    except Exception as e:
        logger.error("IKEA search failed for '%s': %s", search_text, e)
        return PipelineResult(query=query, source="ikea_api", item=None)

    if not results:
        return PipelineResult(query=query, source="ikea_api", item=None)

    # 3. Pick best match by semantic similarity (reject irrelevant results)
    item = _best_match(query, results)
    if item is None:
        return PipelineResult(query=query, source="ikea_api", item=None)

    # 4. Fetch and upload 3D models (also rate-limited)
    if semaphore:
        async with semaphore:
            item.model_files = await _fetch_and_upload_models(item)
    else:
        item.model_files = await _fetch_and_upload_models(item)

    # 5. Cache in vector DB (only cache relevant matches)
    # Qdrant upsert is idempotent (keyed by item_code hash), so concurrent
    # upserts of the same item are safe — last write wins with identical data.
    try:
        upsert_item(item, description=query.description)
    except Exception as e:
        logger.warning("Failed to cache item %s in Qdrant: %s", item.item_code, e)

    return PipelineResult(query=query, source="ikea_api", item=item)


async def run_pipeline(queries: list[FurnitureQuery]) -> list[PipelineResult]:
    """Process furniture queries through the full pipeline, in parallel.

    Uses a semaphore to limit concurrent IKEA API calls and avoid rate-limiting.
    Qdrant upserts are safe for concurrent access (idempotent by item_code hash).
    """
    semaphore = asyncio.Semaphore(MAX_CONCURRENT_SEARCHES)

    tasks = [process_query(query, semaphore) for query in queries]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    # Convert exceptions to empty results
    final: list[PipelineResult] = []
    for i, result in enumerate(results):
        if isinstance(result, Exception):
            logger.error("Query %d failed: %s", i, result)
            final.append(PipelineResult(query=queries[i], source="error", item=None))
        else:
            final.append(result)

    return final
