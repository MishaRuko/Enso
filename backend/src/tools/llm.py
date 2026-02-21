"""OpenRouter LLM client — unified access to Claude and Gemini models."""

import logging

from openai import AsyncOpenAI

from ..config import CLAUDE_MODEL, GEMINI_MODEL, OPENROUTER_API_KEY

logger = logging.getLogger(__name__)

_client = AsyncOpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=OPENROUTER_API_KEY,
    timeout=120.0,
)

_EXTRA_HEADERS = {
    "HTTP-Referer": "https://homedesigner.ai",
    "X-Title": "HomeDesigner",
}


async def call_claude(
    messages: list[dict],
    system: str | None = None,
    temperature: float = 0.7,
) -> str:
    """Call Claude Sonnet via OpenRouter. Returns the text content."""
    full_messages = list(messages)
    if system:
        full_messages.insert(0, {"role": "system", "content": system})

    resp = await _client.chat.completions.create(
        model=CLAUDE_MODEL,
        messages=full_messages,
        temperature=temperature,
        extra_headers=_EXTRA_HEADERS,
    )
    return resp.choices[0].message.content or ""


async def call_gemini(
    messages: list[dict],
    temperature: float = 0.3,
) -> str:
    """Call Gemini 2.5 Pro via OpenRouter. Returns the text content."""
    resp = await _client.chat.completions.create(
        model=GEMINI_MODEL,
        messages=messages,
        temperature=temperature,
        extra_headers=_EXTRA_HEADERS,
    )
    return resp.choices[0].message.content or ""


def _image_content_part(image_url_or_base64: str) -> dict:
    """Build an image_url content part from a URL or base64 string."""
    if image_url_or_base64.startswith("data:"):
        url = image_url_or_base64
    elif image_url_or_base64.startswith("http"):
        url = image_url_or_base64
    else:
        # Treat as raw base64 — guess JPEG
        url = f"data:image/jpeg;base64,{image_url_or_base64}"

    return {"type": "image_url", "image_url": {"url": url}}


async def call_gemini_with_image(
    prompt: str,
    image_url_or_base64: str,
    temperature: float = 0.3,
) -> str:
    """Call Gemini with a single image + text prompt. Returns the text content."""
    messages = [
        {
            "role": "user",
            "content": [
                {"type": "text", "text": prompt},
                _image_content_part(image_url_or_base64),
            ],
        }
    ]
    resp = await _client.chat.completions.create(
        model=GEMINI_MODEL,
        messages=messages,
        temperature=temperature,
        extra_headers=_EXTRA_HEADERS,
    )
    return resp.choices[0].message.content or ""


async def call_claude_with_image(
    prompt: str,
    image_url_or_base64: str,
    system: str | None = None,
    temperature: float = 0.7,
) -> str:
    """Call Claude with a single image + text prompt. Returns the text content."""
    messages = [
        {
            "role": "user",
            "content": [
                {"type": "text", "text": prompt},
                _image_content_part(image_url_or_base64),
            ],
        }
    ]
    if system:
        messages.insert(0, {"role": "system", "content": system})

    resp = await _client.chat.completions.create(
        model=CLAUDE_MODEL,
        messages=messages,
        temperature=temperature,
        extra_headers=_EXTRA_HEADERS,
    )
    return resp.choices[0].message.content or ""
