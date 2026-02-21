"""fal.ai wrapper — generate 3D GLB models from images + FAL storage upload."""

import base64
import logging
import os

import fal_client

from ..config import FAL_KEY, HUNYUAN_MODEL, TRELLIS_MODEL

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

    Uses Trellis v2 with remesh enabled for cleaner room geometry.
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
        "remesh": True,
    }

    logger.info("fal.ai: generating room 3D model with Trellis v2 for %s", image_url)

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
    """Generate a 3D GLB model from an image URL (for furniture objects).

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
        # Hunyuan3D v2
        arguments = {
            "input_image_url": image_url,
            "num_inference_steps": 30,
            "guidance_scale": 7.5,
            "octree_resolution": 256,
            "textured_mesh": True,
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
