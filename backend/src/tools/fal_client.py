"""fal.ai wrapper — generate 3D GLB models from images + FAL storage upload."""

import base64
import logging
import os

import fal_client

try:
    from ..config import FAL_KEY, HUNYUAN_MODEL, TRELLIS_MODEL, TRELLIS_MULTI_MODEL
except ImportError:
    from config import FAL_KEY, HUNYUAN_MODEL, TRELLIS_MODEL, TRELLIS_MULTI_MODEL

logger = logging.getLogger(__name__)

# fal_client reads FAL_KEY from the environment automatically
os.environ.setdefault("FAL_KEY", FAL_KEY)

_MODEL_MAP = {
    "trellis-2": TRELLIS_MODEL,
    "hunyuan": HUNYUAN_MODEL,
}


async def upload_to_fal(image_bytes: bytes, content_type: str = "image/png") -> str:
    """Upload image bytes to fal.ai storage and return a public URL.

    This is needed because Trellis v2 requires a publicly-accessible URL.
    """
    url = await fal_client.upload_async(image_bytes, content_type)
    logger.info("fal.ai: uploaded to storage → %s", url)
    return url


async def upload_data_url_to_fal(data_url: str) -> str:
    """Upload a base64 data-URL (data:image/...;base64,...) to fal.ai storage.

    If the input is already a regular URL, returns it unchanged.
    """
    if not data_url.startswith("data:"):
        return data_url

    # Parse data URL: data:image/png;base64,<data>
    header, b64_data = data_url.split(",", 1)
    content_type = header.split(";")[0].replace("data:", "")
    image_bytes = base64.b64decode(b64_data)
    return await upload_to_fal(image_bytes, content_type)


async def generate_room_model(image_url: str) -> str:
    """Generate a 3D GLB model of a room from a rendered floorplan image.

    Uses TRELLIS v2 which produces reliably textured/colored GLB models.
    This is specifically for room structure (walls/floor/ceiling), not furniture.

    Args:
        image_url: Public URL of the colored floorplan render.

    Returns:
        Public URL of the generated room GLB file.
    """
    arguments = {
        "image_url": image_url,
        "resolution": 1024,
        "texture_size": 2048,
    }

    logger.info("fal.ai: generating room 3D model with TRELLIS v2 for %s", image_url)

    result = await fal_client.subscribe_async(
        TRELLIS_MODEL,
        arguments=arguments,
    )

    glb_url = result["model_glb"]["url"]
    logger.info("fal.ai: room GLB ready at %s", glb_url)
    return glb_url


async def generate_3d_model(
    image_url: str,
    model: str = "trellis-2",
) -> str:
    """Generate a 3D GLB model from a single image URL (for furniture objects).

    Args:
        image_url: Publicly-accessible URL of the source image.
        model: One of "trellis-2" or "hunyuan".

    Returns:
        Public URL of the generated GLB file.
    """
    fal_model_id = _MODEL_MAP.get(model, TRELLIS_MODEL)

    if fal_model_id == TRELLIS_MODEL:
        arguments = {
            "image_url": image_url,
            "resolution": 1024,
            "texture_size": 2048,
        }
    else:
        # Hunyuan 3D v3.1 Rapid
        arguments = {
            "input_image_url": image_url,
            "enable_pbr": True,
        }

    logger.info("fal.ai: generating 3D model with %s for %s", fal_model_id, image_url)

    result = await fal_client.subscribe_async(
        fal_model_id,
        arguments=arguments,
    )

    # TRELLIS returns model_glb, Hunyuan returns model_mesh
    if "model_glb" in result:
        glb_url = result["model_glb"]["url"]
    elif "model_mesh" in result:
        glb_url = result["model_mesh"]["url"]
    else:
        raise ValueError(f"Unexpected fal.ai response keys: {list(result.keys())}")

    logger.info("fal.ai: GLB ready at %s", glb_url)
    return glb_url


async def generate_3d_model_multi_view(image_urls: list[str]) -> str:
    """Generate a 3D GLB model from multiple product images using Trellis v2 multi-view.

    Uses fal-ai/trellis-2/multi which accepts multiple viewpoints of the same
    object to produce a higher-quality 3D reconstruction.

    Args:
        image_urls: List of publicly-accessible image URLs (different views of
            the same product). At least 1, ideally 2-4 images.

    Returns:
        Public URL of the generated GLB file.
    """
    if not image_urls:
        raise ValueError("At least one image URL is required")

    # Single image — fall back to standard endpoint
    if len(image_urls) == 1:
        return await generate_3d_model(image_urls[0])

    arguments = {
        "image_urls": image_urls,
        "resolution": 1024,
        "texture_size": 2048,
    }

    logger.info(
        "fal.ai: generating multi-view 3D model with %s from %d images",
        TRELLIS_MULTI_MODEL, len(image_urls),
    )

    result = await fal_client.subscribe_async(
        TRELLIS_MULTI_MODEL,
        arguments=arguments,
    )

    glb_url = result["model_glb"]["url"]
    logger.info("fal.ai: multi-view GLB ready at %s", glb_url)
    return glb_url
