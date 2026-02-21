from __future__ import annotations

import logging

from app.ikea_client import get_3d_models, search_products
from app.models import FurnitureQuery, FurnitureItem, ModelFile, PipelineResult
from app.storage import download_and_upload_model, model_exists
from app.vector_db import search_similar, upsert_item

logger = logging.getLogger(__name__)


async def _fetch_and_upload_models(item: FurnitureItem) -> list[ModelFile]:
    """Fetch 3D models for an item, upload GLB to DO Spaces."""
    try:
        models = await get_3d_models(item.item_code)
    except Exception as e:
        logger.warning("Could not fetch 3D models for %s: %s", item.item_code, e)
        return []

    uploaded: list[ModelFile] = []
    for model in models:
        if "glb" not in model.format:
            continue

        # Check if already uploaded
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
                # DO Spaces not configured, use IKEA CDN URL directly
                uploaded.append(model)
        except Exception as e:
            logger.warning("Failed to upload model for %s: %s", item.item_code, e)
            # Fall back to IKEA CDN URL
            uploaded.append(model)

    return uploaded


async def process_query(query: FurnitureQuery) -> PipelineResult:
    """Process a single furniture query through the pipeline."""
    # 1. Check vector DB cache
    cached = search_similar(query.description, query.category, query.dimensions)
    if cached is not None:
        return PipelineResult(query=query, source="cache", item=cached)

    # 2. Search IKEA API
    search_text = query.description
    if query.category:
        search_text += f" {query.category}"

    try:
        results = await search_products(search_text, limit=5)
    except Exception as e:
        logger.error("IKEA search failed for '%s': %s", search_text, e)
        return PipelineResult(query=query, source="ikea_api", item=None)

    if not results:
        return PipelineResult(query=query, source="ikea_api", item=None)

    # Pick best match (first result from IKEA search)
    item = results[0]

    # 3. Fetch and upload 3D models
    item.model_files = await _fetch_and_upload_models(item)

    # 4. Cache in vector DB
    try:
        upsert_item(item, description=query.description)
    except Exception as e:
        logger.warning("Failed to cache item %s in Qdrant: %s", item.item_code, e)

    return PipelineResult(query=query, source="ikea_api", item=item)


async def run_pipeline(queries: list[FurnitureQuery]) -> list[PipelineResult]:
    """Process a list of furniture queries through the full pipeline."""
    results: list[PipelineResult] = []
    for query in queries:
        result = await process_query(query)
        results.append(result)
    return results
