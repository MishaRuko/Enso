"""Nano Banana — Gemini image generation via OpenRouter.

Single call: floorplan → isometric empty-room render (text removal + render in one shot).
"""

import logging

from openai import AsyncOpenAI

from ..config import OPENROUTER_API_KEY

logger = logging.getLogger(__name__)

_MODEL = "google/gemini-3-pro-image-preview"


def _extract_image_from_response(resp) -> str | None:
    """Extract a generated image data-URL from an OpenRouter multimodal response."""
    message = resp.choices[0].message

    # OpenRouter non-standard images field
    images = getattr(message, "images", None)
    if images and len(images) > 0:
        try:
            return images[0]["image_url"]["url"]
        except (KeyError, TypeError, IndexError):
            pass

    # Inline data URL in content string
    content = message.content or ""
    if content.startswith("data:image"):
        return content

    # Content array with image parts
    raw = resp.model_dump()
    choices = raw.get("choices", [])
    if choices:
        msg_content = choices[0].get("message", {}).get("content")
        if isinstance(msg_content, list):
            for part in msg_content:
                if not isinstance(part, dict):
                    continue
                img_url = part.get("image_url", {})
                if isinstance(img_url, dict) and img_url.get("url", "").startswith("data:image"):
                    return img_url["url"]
                text = part.get("text", "")
                if text.startswith("data:image"):
                    return text

    return None


async def _call_gemini_image(prompt: str, image_url: str) -> str | None:
    """Send an image + prompt to Gemini image model, return generated image data-URL."""
    client = AsyncOpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=OPENROUTER_API_KEY,
    )

    resp = await client.chat.completions.create(
        model=_MODEL,
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": image_url}},
                ],
            }
        ],
        extra_body={"modalities": ["image", "text"]},
        extra_headers={
            "HTTP-Referer": "https://homedesigner.ai",
            "X-Title": "HomeDesigner",
        },
    )

    return _extract_image_from_response(resp)


def build_render_prompt(preferences: dict | None = None) -> str:
    """Build the isometric render prompt, incorporating user preferences if available."""
    style = ""
    if preferences:
        parts = []
        if preferences.get("style"):
            parts.append(f"{preferences['style']} style")
        if preferences.get("colors"):
            colors = preferences["colors"]
            if isinstance(colors, list):
                parts.append(f"color palette: {', '.join(colors)}")
        style = f" Design style: {', '.join(parts)}." if parts else ""

    return (
        "Analyze this floor plan and generate a professional isometric architectural "
        "maquette photographed in a studio. Show the bare structural shell of each room "
        "as if the building was just constructed and nobody has moved in yet — pristine, "
        "vacant, and completely unlived-in. "
        "Walls with realistic height and thickness, bare floors with natural material "
        "textures (hardwood, polished concrete, or tile), door openings, and window frames. "
        f"Warm natural studio lighting with soft shadows to emphasize depth.{style} "
        "Maintain the EXACT room layout, proportions, and wall positions from the "
        "original floor plan. Isometric bird's eye perspective, clean white background "
        "beneath the model.\n\n"
        "CRITICAL CONSTRAINTS — you MUST follow these EXACTLY:\n"
        "- Remove ALL text, labels, annotations, dimensions, and numbers.\n"
        "- Every room MUST be COMPLETELY VACANT — show ONLY the architectural shell.\n"
        "- NO furniture, NO kitchen islands, NO cabinets, NO countertops, NO appliances.\n"
        "- NO bathroom fixtures, NO sinks, NO toilets, NO bathtubs, NO showers.\n"
        "- NO decor, NO rugs, NO plants, NO shelving, NO lighting fixtures, NO objects.\n"
        "- The ONLY elements permitted are: walls, floors, doors, and windows.\n\n"
        "Generate the rendered image only."
    )


async def generate_colored_render(
    image_url: str,
    preferences: dict | None = None,
) -> str:
    """Generate a colored isometric render from a floorplan image.

    Single call that handles text removal + colored render in one shot.
    Incorporates user style/color preferences when available.

    Args:
        image_url: URL or base64 data-URL of the floorplan.
        preferences: Optional user preferences dict with style/colors.

    Returns:
        Base64 data-URL of the rendered image, or the original URL on failure.
    """
    prompt = build_render_prompt(preferences)

    try:
        result = await _call_gemini_image(prompt, image_url)
        if result:
            logger.info("Nano Banana: isometric render succeeded")
            return result

        logger.warning("Nano Banana: no image in response, falling back to original")
        return image_url

    except Exception:
        logger.exception("Nano Banana render failed, using original image")
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
