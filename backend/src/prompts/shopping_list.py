"""Prompt template for generating a furniture shopping list."""

from ..models.schemas import RoomData, UserPreferences


def shopping_list_prompt(room: RoomData, preferences: UserPreferences) -> str:
    """Build the prompt for generating a furniture shopping list.

    Use with `call_claude(messages=[{"role": "user", "content": prompt}])`.
    """
    return f"""\
You are an expert interior designer. Given a room and client preferences, create a furniture shopping list.

## Room
- Name: {room.name}
- Dimensions: {room.width_m}m x {room.length_m}m (area {room.area_sqm} sqm)
- Height: {room.height_m}m
- Doors: {len(room.doors)} | Windows: {len(room.windows)}

## Client Preferences
- Style: {preferences.style or "modern"}
- Budget: {preferences.budget_min}–{preferences.budget_max} {preferences.currency}
- Colours: {", ".join(preferences.colors) if preferences.colors else "neutral"}
- Room type: {preferences.room_type or room.name}
- Lifestyle: {", ".join(preferences.lifestyle) if preferences.lifestyle else "general"}
- Must-haves: {", ".join(preferences.must_haves) if preferences.must_haves else "none"}
- Dealbreakers: {", ".join(preferences.dealbreakers) if preferences.dealbreakers else "none"}
- Existing furniture to keep: {", ".join(preferences.existing_furniture) if preferences.existing_furniture else "none"}

## Instructions
1. List ONLY furniture that fits in the room (check dimensions).
2. Allocate budget proportionally — big items first.
3. Include a search query for each item that would work well on IKEA or similar retailers.
4. Set priority: "essential" for must-have items, "nice_to_have" for accent/decor.

Return ONLY valid JSON (no markdown fences) as an array:
[
  {{
    "item": "string — e.g. sofa, coffee table, bookshelf",
    "query": "string — search query for IKEA/retailer, e.g. '3-seat sofa grey fabric'",
    "max_width_cm": number,
    "budget_min": number,
    "budget_max": number,
    "priority": "essential" | "nice_to_have"
  }}
]"""
