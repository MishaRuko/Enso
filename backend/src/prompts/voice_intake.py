"""Prompt builders for voice intake conversation."""

from ..models.schemas import UserPreferences


def build_voice_intake_messages(
    transcript: str,
    brief_current: dict,
    history: list[dict],
    required_fields: list[str],
) -> list[dict]:
    """Build messages for Claude to handle one turn of voice intake conversation.

    Args:
        transcript: The user's utterance (transcribed speech)
        brief_current: Current canonical brief JSON with all fields
        history: Conversation history [{"role": "user|assistant", "content": "..."}]
        required_fields: List of required brief fields for completion

    Returns:
        List of messages ready for Claude API
    """

    system_prompt = f"""You are a friendly interior design consultation assistant.
Your role is to conduct a natural conversation to gather the user's design preferences and build a brief.

You are collecting the following information for the design brief:
- rooms_priority: List of rooms to design (e.g., ["living room", "bedroom"])
- budget: Total budget as a number (e.g., 5000)
- style: Design styles they like (e.g., ["modern", "minimalist"])
- must_haves: Essential items/features (e.g., ["large sofa", "home office desk"])
- avoid: Things to avoid (e.g., ["dark colors", "leather"])
- constraints: Physical constraints (e.g., ["small space", "low ceiling"])
- vibe_words: Mood/atmosphere words (e.g., ["cozy", "bright", "luxurious"])
- existing_items: Furniture they already have to keep
- notes: Any additional notes

Current brief state:
{_format_brief_json(brief_current)}

Required for completion: {', '.join(required_fields)}

Guidelines:
1. Ask ONE question at a time to keep conversation flowing naturally
2. If the user provides info, extract it and update the brief_patch in your response
3. Be conversational - don't sound like a form
4. If the user says something like "I'm done" or "that's it", check if all required fields are filled
5. Always respond in STRICT JSON format (no markdown, no text before/after JSON):
{{"assistant_text": "Your conversational response...", "brief_patch": {{}}, "done": false}}

JSON schema for response:
- assistant_text (string): Your conversational response to the user
- brief_patch (object): Any new/updated fields from the brief to merge (keys only from canonical brief)
- done (boolean): True only if all required fields are filled AND user confirms

Start with welcoming them and asking about the first missing required field.
Keep responses short and natural (1-2 sentences for assistant_text)."""

    messages = []

    # Add brief context as a system message
    messages.append({"role": "system", "content": system_prompt})

    # Add conversation history
    for msg in history:
        messages.append({"role": msg["role"], "content": msg["content"]})

    # Add current user input
    messages.append({"role": "user", "content": transcript})

    return messages


def _format_brief_json(brief: dict) -> str:
    """Format the brief JSON for display in the prompt."""
    if not brief:
        return "{}"

    lines = ["{"]
    for key in [
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
    ]:
        value = brief.get(key)
        if value is None:
            lines.append(f'  "{key}": null,')
        elif isinstance(value, str):
            lines.append(f'  "{key}": "{value}",')
        elif isinstance(value, (int, float)):
            lines.append(f'  "{key}": {value},')
        else:
            # Lists, dicts, etc.
            lines.append(f'  "{key}": {value},')
    lines.append("}")

    return "\n".join(lines)
