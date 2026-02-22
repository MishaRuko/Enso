"""Voice intake conversation agent — processes user utterances and builds design brief."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from typing import Any

from ..prompts.voice_intake import build_voice_intake_messages
from ..tools.llm import call_claude

logger = logging.getLogger(__name__)


# Canonical brief keys (internal_json == miro_json for now)
BRIEF_KEYS = {
    "budget",
    "currency",
    "style",
    "avoid",
    "rooms_priority",
    "must_haves",
    "existing_items",
    "constraints",
    "vibe_words",
    "reference_images",
    "notes",
}

REQUIRED_FIELDS = ["rooms_priority", "budget", "style", "must_haves"]


@dataclass
class VoiceIntakeResult:
    assistant_text: str
    brief_patch: dict[str, Any]
    missing_fields: list[str]
    done: bool


def _coerce_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    # allow comma-separated strings
    if isinstance(value, str):
        parts = [p.strip() for p in value.split(",")]
        return [p for p in parts if p]
    return [value]


def _coerce_number(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        # strip currency symbols and commas
        cleaned = (
            value.replace("€", "")
            .replace("$", "")
            .replace("£", "")
            .replace(",", "")
            .strip()
        )
        try:
            return float(cleaned)
        except ValueError:
            return None
    return None


def _filter_patch(patch: dict[str, Any]) -> dict[str, Any]:
    """Keep only known brief keys and normalize basic types."""
    safe: dict[str, Any] = {}
    for k, v in (patch or {}).items():
        if k not in BRIEF_KEYS:
            continue

        if k in {"style", "avoid", "rooms_priority", "must_haves", "constraints", "vibe_words"}:
            safe[k] = _coerce_list(v)
        elif k == "existing_items":
            safe[k] = v if isinstance(v, list) else []
        elif k == "reference_images":
            safe[k] = v if isinstance(v, list) else []
        elif k == "budget":
            safe[k] = _coerce_number(v)
        elif k == "currency":
            safe[k] = str(v).upper().strip() if v is not None else "EUR"
        elif k == "notes":
            safe[k] = str(v) if v is not None else ""
        else:
            safe[k] = v
    return safe


def _merge_brief(current: dict[str, Any], patch: dict[str, Any]) -> dict[str, Any]:
    merged = dict(current or {})
    for k, v in patch.items():
        merged[k] = v
    # ensure all keys exist
    for k in BRIEF_KEYS:
        merged.setdefault(k, [] if k in {"style","avoid","rooms_priority","must_haves","constraints","vibe_words","existing_items","reference_images"} else None)
    merged.setdefault("currency", "EUR")
    merged.setdefault("notes", "")
    return merged


def _missing_fields(brief: dict[str, Any]) -> list[str]:
    missing: list[str] = []
    for f in REQUIRED_FIELDS:
        val = brief.get(f)
        if f == "budget":
            if val is None:
                missing.append(f)
        elif isinstance(val, list):
            if len(val) == 0:
                missing.append(f)
        else:
            if not val:
                missing.append(f)
    return missing


def _extract_json(text: str) -> dict[str, Any]:
    """
    Claude sometimes wraps JSON with text. Try strict parse first, then substring.
    """
    text = text.strip()
    try:
        return json.loads(text)
    except Exception:
        pass

    # try to find outermost {...}
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        candidate = text[start : end + 1]
        try:
            return json.loads(candidate)
        except Exception:
            pass

    raise ValueError("Could not parse JSON from LLM response.")


async def run_voice_intake_turn(
    *,
    transcript: str,
    brief_current: dict[str, Any] | None = None,
    history: list[dict[str, str]] | None = None,
) -> VoiceIntakeResult:
    """
    One turn of the intake agent.
    - transcript: user utterance (already transcribed)
    - brief_current: current canonical brief JSON
    - history: list of {role, content} (short; last N is fine)

    Returns assistant text + patch + missing fields + done.
    """

    brief_current = brief_current or {}
    history = history or []

    messages = build_voice_intake_messages(
        transcript=transcript,
        brief_current=brief_current,
        history=history[-12:],  # keep it short
        required_fields=REQUIRED_FIELDS,
    )

    # Call Claude via OpenRouter wrapper
    try:
        llm_text = await call_claude(
            messages=messages,
            temperature=0.2,
        )
    except Exception as e:
        logger.error("Claude API call failed", exc_info=e)
        # Fallback response if API fails
        return VoiceIntakeResult(
            assistant_text="I'm having trouble hearing you. Could you try again?",
            brief_patch={},
            missing_fields=_missing_fields(brief_current),
            done=False,
        )

    try:
        parsed = _extract_json(llm_text)
    except Exception as e:
        logger.error(f"Failed to parse Claude response as JSON: {llm_text}", exc_info=e)
        # Fallback response if JSON parsing fails
        parsed = {
            "assistant_text": "I couldn't quite understand that. Could you rephrase?",
            "brief_patch": {},
            "done": False,
        }

    assistant_text = str(parsed.get("assistant_text", "")).strip()
    brief_patch_raw = parsed.get("brief_patch", {}) or {}
    done = bool(parsed.get("done", False))

    brief_patch = _filter_patch(brief_patch_raw)
    brief_merged = _merge_brief(brief_current, brief_patch)

    missing = _missing_fields(brief_merged)

    # If user confirmed but still missing required fields, override done
    if done and missing:
        done = False
        # Safety: ensure assistant asks for next missing item
        if not assistant_text:
            assistant_text = f"Quick follow-up: what is your {missing[0]}?"

    # If assistant_text empty, provide a fallback
    if not assistant_text:
        if missing:
            assistant_text = f"Got it. Next, what’s your {missing[0]}?"
        else:
            assistant_text = "Thanks. Want me to recap the design brief and you confirm?"
    # Log turn completion for debugging
    logger.info(
        f"Intake turn complete: brief_patch={len(brief_patch)} keys, "
        f"missing_fields={missing}, done={done}"
    )
    return VoiceIntakeResult(
        assistant_text=assistant_text,
        brief_patch=brief_patch,
        missing_fields=missing,
        done=done,
    )
