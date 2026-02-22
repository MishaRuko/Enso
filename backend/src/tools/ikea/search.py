"""IKEA product search — adapter between our pipeline and the IKEA package.

Translates FurnitureItemSpec (from our furniture agents) into FurnitureQuery
(for the IKEA pipeline), runs the pipeline, and maps results back.
"""

import logging
import re

try:
    from ...furniture_placement.furniture_agents import FurnitureItemSpec
except ImportError:
    from furniture_placement.furniture_agents import FurnitureItemSpec
from .models import FurnitureQuery
from .pipeline import run_pipeline

logger = logging.getLogger(__name__)


def _dims_to_string(spec: FurnitureItemSpec) -> str:
    """Convert metric dimensions to the string format the IKEA pipeline expects."""
    l_cm = round(spec.length_m * 100)
    w_cm = round(spec.width_m * 100)
    h_cm = round(spec.height_m * 100)
    return f"{l_cm}x{w_cm}x{h_cm} cm"


def _parse_dimensions_string(dims_str: str | None) -> dict | None:
    """Parse IKEA dimension strings like '80x28x202 cm' or '80x28 cm' into cm dict.

    IKEA formats vary: "Width: 80 cm, Depth: 28 cm, Height: 202 cm" or "80x28x202 cm"
    """
    if not dims_str:
        return None

    # Try "NxNxN cm" format
    m = re.search(r"(\d+)\s*x\s*(\d+)\s*x\s*(\d+)", dims_str)
    if m:
        return {
            "width": float(m.group(1)),
            "length": float(m.group(2)),
            "height": float(m.group(3)),
        }

    # Try extracting labelled dimensions
    width = re.search(r"[Ww]idth:?\s*(\d+(?:\.\d+)?)", dims_str)
    depth = re.search(r"[Dd]epth:?\s*(\d+(?:\.\d+)?)", dims_str)
    height = re.search(r"[Hh]eight:?\s*(\d+(?:\.\d+)?)", dims_str)
    length = re.search(r"[Ll]ength:?\s*(\d+(?:\.\d+)?)", dims_str)

    result = {}
    if width:
        result["width"] = float(width.group(1))
    if depth:
        result["length"] = float(depth.group(1))
    elif length:
        result["length"] = float(length.group(1))
    if height:
        result["height"] = float(height.group(1))

    return result if result else None


def _specs_to_queries(
    specs: dict[str, list[FurnitureItemSpec]],
) -> tuple[list[FurnitureQuery], list[dict]]:
    """Convert our FurnitureItemSpec list to FurnitureQuery objects for the pipeline.

    Returns:
        (queries, metadata) — queries for the pipeline, metadata for mapping results back.
    """
    queries = []
    metadata = []
    for room_name, items in specs.items():
        for item in items:
            queries.append(FurnitureQuery(
                description=item.search_query or f"{item.category} {item.name}",
                category=item.category,
                dimensions=_dims_to_string(item),
            ))
            metadata.append({
                "room_name": room_name,
                "item_name": item.name,
            })
    return queries, metadata


def _result_from_pipeline_item(item, meta: dict) -> dict:
    """Convert a PipelineResult item + metadata to our output dict."""
    glb_url = ""
    for mf in item.model_files:
        if "glb" in mf.format:
            glb_url = mf.url
            break

    dims_cm = _parse_dimensions_string(item.dimensions)

    return {
        "name": meta.get("item_name", ""),
        "room_name": meta.get("room_name", ""),
        "found": True,
        "ikea_item_code": item.item_code,
        "ikea_name": item.name or "",
        "price": item.price,
        "currency": item.currency or "GBP",
        "dimensions_cm": dims_cm,
        "glb_url": glb_url,
        "buy_url": item.buy_url or "",
        "image_url": item.image_url or "",
    }


async def search_ikea_products(
    specs: dict[str, list[FurnitureItemSpec]],
) -> list[dict]:
    """Run furniture specs through the IKEA pipeline (direct function call).

    Deduplicates by category so e.g. "chair1", "chair2", "chair3" only trigger
    one IKEA API search. The result is reused for all items of the same category.

    Args:
        specs: Our furniture specs (room_name -> list of FurnitureItemSpec).

    Returns:
        List of result dicts, one per item, with fields:
        - name, room_name, found, ikea_item_code, ikea_name,
        - price, currency, dimensions_cm, glb_url, buy_url, image_url, source
    """
    queries, metadata = _specs_to_queries(specs)

    # Deduplicate: group items by category so identical products search once
    unique_queries: list[FurnitureQuery] = []
    category_to_idx: dict[str, int] = {}  # category -> index in unique_queries
    item_to_unique: list[int] = []  # per-item index into unique_queries

    for i, q in enumerate(queries):
        cat = q.category.lower().strip()
        if cat in category_to_idx:
            item_to_unique.append(category_to_idx[cat])
        else:
            category_to_idx[cat] = len(unique_queries)
            item_to_unique.append(len(unique_queries))
            unique_queries.append(q)

    logger.info(
        "IKEA search: %d items → %d unique categories",
        len(queries), len(unique_queries),
    )

    pipeline_results = await run_pipeline(unique_queries)

    # Map results back — reuse the same pipeline result for duplicate categories
    results = []
    for i, meta in enumerate(metadata):
        unique_idx = item_to_unique[i]
        pr = pipeline_results[unique_idx]

        if not pr.item:
            logger.warning(
                "No IKEA result for %s/%s",
                meta.get("room_name", "?"),
                meta.get("item_name", "?"),
            )
            results.append({
                "name": meta.get("item_name", ""),
                "room_name": meta.get("room_name", ""),
                "ikea_item_code": None,
                "found": False,
            })
            continue

        result = _result_from_pipeline_item(pr.item, meta)
        result["source"] = pr.source
        results.append(result)

    found = sum(1 for r in results if r.get("found"))
    with_glb = sum(1 for r in results if r.get("glb_url"))
    logger.info(
        "IKEA search: %d/%d found, %d with GLB models",
        found, len(results), with_glb,
    )

    return results


def ikea_results_to_spec_updates(results: list[dict]) -> list[dict]:
    """Convert IKEA search results to the format expected by update_specs_from_search_results().

    Only includes results that have actual dimensions to update.
    """
    updates = []
    for r in results:
        if not r.get("found") or not r.get("dimensions_cm"):
            continue
        updates.append({
            "name": r["name"],
            "room_name": r["room_name"],
            "dimensions_cm": r["dimensions_cm"],
        })
    return updates
