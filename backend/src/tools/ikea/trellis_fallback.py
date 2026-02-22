"""Generate 3D models via Trellis for items that have no IKEA GLB.

- Checks local JSON cache first (survives across runs).
- Then checks DO Spaces (remote persistent cache).
- Only calls fal.ai Trellis as a last resort.
- Deduplicates by item code (same IKEA product → one call).
- Runs up to max_concurrent Trellis calls in parallel.
"""

import asyncio
import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

MAX_TRELLIS_CALLS = 10
MAX_CONCURRENT = 5

# Local cache file: item_code → glb_url
_CACHE_PATH = Path(__file__).parent.parent.parent.parent / "output" / "glb_url_cache.json"


def _load_local_cache() -> dict[str, str]:
    if _CACHE_PATH.exists():
        try:
            return json.loads(_CACHE_PATH.read_text())
        except Exception:
            return {}
    return {}


def _save_local_cache(cache: dict[str, str]) -> None:
    _CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    _CACHE_PATH.write_text(json.dumps(cache, indent=2))


async def _generate_single(
    item_code: str,
    image_url: str,
    name: str,
    semaphore: asyncio.Semaphore,
    local_cache: dict[str, str],
    dry_run: bool = False,
) -> str | None:
    """Generate a GLB for one unique item code. Returns URL or None."""
    if not image_url:
        logger.info("  SKIP: %s (no image URL)", name)
        return None

    # 1. Check local file cache (fastest)
    if item_code in local_cache:
        logger.info("  LOCAL CACHE HIT: %s → %s", item_code, local_cache[item_code][:60])
        return local_cache[item_code]

    # 2. Check DO Spaces cache (remote persistent)
    try:
        from .storage import download_and_upload_model, model_exists
    except ImportError:
        from tools.ikea.storage import download_and_upload_model, model_exists

    for fmt in ("glb", "glb_draco"):
        existing = model_exists(item_code, fmt)
        if existing:
            logger.info("  DO SPACES CACHE HIT: %s (%s)", item_code, fmt)
            local_cache[item_code] = existing
            return existing

    if dry_run:
        logger.info("  DRY RUN: would generate %s from %s", name, image_url[:80])
        return None

    try:
        from ..fal_client import generate_3d_model, upload_to_fal
    except ImportError:
        from tools.fal_client import generate_3d_model, upload_to_fal

    # 3. Generate via Trellis (rate-limited by semaphore)
    async with semaphore:
        logger.info("  Generating Trellis for %s (%s)", name, item_code)

        # fal.ai can't download IKEA images directly (blocked by IKEA CDN).
        # Re-upload the image to fal.ai storage first.
        if "ikea.com" in image_url:
            import httpx
            logger.info("  Re-uploading IKEA image to fal.ai storage...")
            async with httpx.AsyncClient() as http:
                resp = await http.get(image_url, follow_redirects=True)
                resp.raise_for_status()
                content_type = resp.headers.get("content-type", "image/jpeg")
                image_url = await upload_to_fal(resp.content, content_type)

        trellis_url = await generate_3d_model(image_url)

    # 4. Upload to DO Spaces (outside semaphore — different service)
    try:
        spaces_url = await download_and_upload_model(item_code, trellis_url, "glb")
    except Exception as e:
        logger.warning("  DO Spaces upload failed for %s: %s (using fal.ai URL)", name, e)
        spaces_url = None

    final_url = spaces_url or trellis_url
    local_cache[item_code] = final_url
    return final_url


async def generate_missing_models(
    placements: list[dict],
    max_calls: int = MAX_TRELLIS_CALLS,
    max_concurrent: int = MAX_CONCURRENT,
    dry_run: bool = False,
) -> int:
    """Generate 3D models for placement dicts that have image_url but no glb_url.

    Runs up to max_concurrent Trellis jobs in parallel. Modifies placements
    in place (sets glb_url). Deduplicates by item code so identical products
    (e.g. 4 dining chairs) only trigger one Trellis call.

    Cache priority: local JSON file → DO Spaces → Trellis generation.
    """
    # Load local cache from previous runs
    local_cache = _load_local_cache()
    logger.info("Local GLB cache: %d entries loaded from %s", len(local_cache), _CACHE_PATH)

    # Pre-fill from local cache before filtering "missing"
    for p in placements:
        if p.get("glb_url"):
            continue
        code = p.get("ikea_item_code") or p.get("item_id") or p["name"].replace(" ", "_")
        if code in local_cache:
            p["glb_url"] = local_cache[code]

    missing = [p for p in placements if not p.get("glb_url") and p.get("image_url")]
    if not missing:
        logger.info("All items have GLB URLs — no Trellis generation needed")
        return sum(1 for p in placements if p.get("glb_url"))

    # Group by item code to deduplicate
    by_code: dict[str, list[dict]] = {}
    for p in missing:
        code = p.get("ikea_item_code") or p.get("item_id") or p["name"].replace(" ", "_")
        by_code.setdefault(code, []).append(p)

    # Only process up to max_calls unique items
    codes_to_process = list(by_code.keys())[:max_calls]

    mode = "DRY RUN" if dry_run else "GENERATING"
    logger.info(
        "%s 3D models: %d items still missing GLB (%d unique, processing %d, %d concurrent)",
        mode, len(missing), len(by_code), len(codes_to_process), max_concurrent,
    )

    semaphore = asyncio.Semaphore(max_concurrent)

    async def _process_one(code: str) -> tuple[str, str | None]:
        items = by_code[code]
        try:
            url = await _generate_single(
                item_code=code,
                image_url=items[0].get("image_url", ""),
                name=items[0].get("name", code),
                semaphore=semaphore,
                local_cache=local_cache,
                dry_run=dry_run,
            )
            return code, url
        except Exception as e:
            logger.warning("  FAIL generating %s: %s", items[0].get("name", code), e)
            return code, None

    # Run all in parallel (semaphore limits concurrency)
    results = await asyncio.gather(*[_process_one(code) for code in codes_to_process])

    # Apply results back to placements
    for code, url in results:
        if url:
            for item in by_code[code]:
                item["glb_url"] = url

    # Save updated local cache
    _save_local_cache(local_cache)
    logger.info("Local GLB cache: %d entries saved to %s", len(local_cache), _CACHE_PATH)

    total_with_glb = sum(1 for p in placements if p.get("glb_url"))
    successful = sum(1 for _, url in results if url)
    logger.info(
        "After Trellis: %d/%d items have GLB URLs (%d newly generated, dry_run=%s)",
        total_with_glb, len(placements), successful, dry_run,
    )
    return total_with_glb
