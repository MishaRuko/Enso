"""Nano Banana text removal — uses Gemini Flash Image via OpenRouter to remove
text/labels/watermarks from floorplan images before analysis."""

import base64
import logging

from openai import AsyncOpenAI

from ..config import OPENROUTER_API_KEY

logger = logging.getLogger(__name__)

_REMOVAL_PROMPT = (
    "Remove ALL text, labels, annotations, watermarks, dimensions, numbers, "
    "and written characters from this architectural floorplan image. "
    "Keep the walls, doors, windows, and room outlines perfectly intact. "
    "Fill in where text was removed with clean white or the surrounding background colour. "
    "Return the cleaned image only."
)

# OpenRouter image generation model
_NANO_BANANA_MODEL = "google/gemini-3-pro-image-preview"


async def remove_text_from_image(image_url: str) -> str:
    """Remove text/labels from a floorplan image using Nano Banana (Gemini Flash Image).

    Args:
        image_url: Public URL of the floorplan image.

    Returns:
        Base64 data-URL of the cleaned image (data:image/png;base64,...),
        or the original URL if text removal fails.
    """
    try:
        client = AsyncOpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=OPENROUTER_API_KEY,
        )

        resp = await client.chat.completions.create(
            model=_NANO_BANANA_MODEL,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": _REMOVAL_PROMPT},
                        {
                            "type": "image_url",
                            "image_url": {"url": image_url},
                        },
                    ],
                }
            ],
            extra_body={"modalities": ["image", "text"]},
            extra_headers={
                "HTTP-Referer": "https://homedesigner.ai",
                "X-Title": "HomeDesigner",
            },
        )

        # Extract generated image from OpenRouter response
        message = resp.choices[0].message

        # Method 1: OpenRouter may include images in a non-standard field
        images = getattr(message, "images", None)
        if images and len(images) > 0:
            try:
                data_url = images[0]["image_url"]["url"]
                logger.info("Nano Banana: text removal succeeded (images field)")
                return data_url
            except (KeyError, TypeError, IndexError):
                pass

        # Method 2: Content may contain inline base64 data URL
        content = message.content or ""
        if content.startswith("data:image"):
            logger.info("Nano Banana: text removal succeeded (inline data URL)")
            return content

        # Method 3: Content blocks may contain image parts (multimodal response)
        raw = resp.model_dump()
        choices = raw.get("choices", [])
        if choices:
            msg = choices[0].get("message", {})
            # Check for content array with image parts
            msg_content = msg.get("content")
            if isinstance(msg_content, list):
                for part in msg_content:
                    if isinstance(part, dict):
                        # OpenRouter image_url part
                        img_url = part.get("image_url", {})
                        if isinstance(img_url, dict) and img_url.get("url", "").startswith("data:image"):
                            logger.info("Nano Banana: text removal succeeded (content array)")
                            return img_url["url"]
                        # Inline base64 in text part
                        text = part.get("text", "")
                        if text.startswith("data:image"):
                            logger.info("Nano Banana: text removal succeeded (text part)")
                            return text

        logger.warning("Nano Banana: no image in response, falling back to original")
        return image_url

    except Exception:
        logger.exception("Nano Banana text removal failed, using original image")
        return image_url


async def remove_text_from_bytes(image_bytes: bytes, content_type: str = "image/png") -> str:
    """Remove text from raw image bytes. Returns a base64 data-URL of the cleaned image."""
    b64 = base64.b64encode(image_bytes).decode()
    data_url = f"data:{content_type};base64,{b64}"
    return await remove_text_from_image(data_url)


# ---------------------------------------------------------------------------
# Colored architectural render — generates a 3D top-down view for Trellis input
# ---------------------------------------------------------------------------

_RENDER_PROMPT = (
    "Transform this floor plan into a colorful architectural top-down 3D render. "
    "Show the room layout as a bird's eye view with visible walls, floors with "
    "realistic materials and textures (wood, tile, carpet), and warm lighting. "
    "Keep the rooms EMPTY — no furniture, no decor, no objects. "
    "Maintain the exact room layout and proportions from the original floor plan. "
    "Clean architectural visualization with shadows and depth. "
    "Return the rendered image only."
)


async def generate_colored_render(image_url: str) -> str:
    """Generate a colored architectural top-down render from a floorplan image.

    This produces a visually rich 3D-looking render that serves as better input
    for Trellis v2 room model generation (vs. a flat 2D floorplan).

    Args:
        image_url: Public URL or base64 data-URL of the cleaned floorplan.

    Returns:
        Base64 data-URL of the rendered image (data:image/png;base64,...),
        or the original URL if rendering fails.
    """
    try:
        client = AsyncOpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=OPENROUTER_API_KEY,
        )

        resp = await client.chat.completions.create(
            model=_NANO_BANANA_MODEL,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": _RENDER_PROMPT},
                        {
                            "type": "image_url",
                            "image_url": {"url": image_url},
                        },
                    ],
                }
            ],
            extra_body={"modalities": ["image", "text"]},
            extra_headers={
                "HTTP-Referer": "https://homedesigner.ai",
                "X-Title": "HomeDesigner",
            },
        )

        message = resp.choices[0].message

        images = getattr(message, "images", None)
        if images and len(images) > 0:
            try:
                data_url = images[0]["image_url"]["url"]
                logger.info("Nano Banana: colored render succeeded (images field)")
                return data_url
            except (KeyError, TypeError, IndexError):
                pass

        content = message.content or ""
        if content.startswith("data:image"):
            logger.info("Nano Banana: colored render succeeded (inline data URL)")
            return content

        raw = resp.model_dump()
        choices = raw.get("choices", [])
        if choices:
            msg = choices[0].get("message", {})
            msg_content = msg.get("content")
            if isinstance(msg_content, list):
                for part in msg_content:
                    if isinstance(part, dict):
                        img_url = part.get("image_url", {})
                        if isinstance(img_url, dict) and img_url.get("url", "").startswith("data:image"):
                            logger.info("Nano Banana: colored render succeeded (content array)")
                            return img_url["url"]
                        text = part.get("text", "")
                        if text.startswith("data:image"):
                            logger.info("Nano Banana: colored render succeeded (text part)")
                            return text

        logger.warning("Nano Banana: no image in render response, falling back to original")
        return image_url

    except Exception:
        logger.exception("Nano Banana colored render failed, using original image")
        return image_url


# ---------------------------------------------------------------------------
# Room Segmentation — fills distinct rooms with solid colors for analysis
# ---------------------------------------------------------------------------

_SEGMENTATION_PROMPT = (
    "This is a floor plan. Your task is to fill the empty spaces of individual/distinct rooms with different bright solid colours. "
    "CRITICAL RULES:"
    "1. DO NOT add, remove, or modify any walls, doors, or structural lines. The black structural elements must remain PIXEL-PERFECT identical."
    "2. ONLY color the empty white spaces inside the rooms."
    "3. Do not hallucinate new dividers, partitions, or furniture."
    "4. Keep the coloured regions solid and uniform inside, with no artifacts."
    "This is a strict coloring task, not a design task. Preserve the original structure exactly."
)


async def generate_segmented_rooms(image_url: str) -> str:
    """Generate a segmented floor plan where each room is filled with a unique solid color.

    This aids in programmatically detecting rooms and their shapes by analyzing the unique colors.

    Args:
        image_url: Public URL or base64 data-URL of the floorplan.

    Returns:
        Base64 data-URL of the segmented image (data:image/png;base64,...),
        or the original URL if generation fails.
    """
    try:
        client = AsyncOpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=OPENROUTER_API_KEY,
        )

        resp = await client.chat.completions.create(
            model=_NANO_BANANA_MODEL,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": _SEGMENTATION_PROMPT},
                        {
                            "type": "image_url",
                            "image_url": {"url": image_url},
                        },
                    ],
                }
            ],
            extra_body={"modalities": ["image", "text"]},
            extra_headers={
                "HTTP-Referer": "https://homedesigner.ai",
                "X-Title": "HomeDesigner",
            },
        )

        message = resp.choices[0].message

        # Method 1: OpenRouter may include images in a non-standard field
        images = getattr(message, "images", None)
        if images and len(images) > 0:
            try:
                data_url = images[0]["image_url"]["url"]
                logger.info("Nano Banana: segmentation succeeded (images field)")
                return data_url
            except (KeyError, TypeError, IndexError):
                pass

        # Method 2: Content may contain inline base64 data URL
        content = message.content or ""
        if content.startswith("data:image"):
            logger.info("Nano Banana: segmentation succeeded (inline data URL)")
            return content

        # Method 3: Content blocks may contain image parts (multimodal response)
        raw = resp.model_dump()
        choices = raw.get("choices", [])
        if choices:
            msg = choices[0].get("message", {})
            msg_content = msg.get("content")
            if isinstance(msg_content, list):
                for part in msg_content:
                    if isinstance(part, dict):
                        img_url = part.get("image_url", {})
                        if isinstance(img_url, dict) and img_url.get("url", "").startswith("data:image"):
                            logger.info("Nano Banana: segmentation succeeded (content array)")
                            return img_url["url"]
                        text = part.get("text", "")
                        if text.startswith("data:image"):
                            logger.info("Nano Banana: segmentation succeeded (text part)")
                            return text

        logger.warning("Nano Banana: no image in segmentation response, falling back to original")
        return image_url

    except Exception:
        logger.exception("Nano Banana segmentation failed, using original image")
        return image_url
