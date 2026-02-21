#!/usr/bin/env python3
"""
Creates (or updates) the Enso ElevenLabs conversational agent via the Management API.

Usage:
    cd /Users/charlenechen/Enso
    uv run python backend/scripts/setup_elevenlabs_agent.py

On success it prints the Agent ID — paste that into
frontend/designer-next/.env.local as NEXT_PUBLIC_ELEVENLABS_AGENT_ID.
"""

import json
import sys
from pathlib import Path

import requests

# Bootstrap config so we can read the API key
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
from config import ELEVENLABS_API_KEY  # noqa: E402
from prompts.consultation_agent import CLIENT_TOOLS, SYSTEM_PROMPT  # noqa: E402

BASE = "https://api.elevenlabs.io/v1"
HEADERS = {"xi-api-key": ELEVENLABS_API_KEY, "Content-Type": "application/json"}
AGENT_NAME = "Enso — Design Consultation"


def die(msg: str) -> None:
    print(f"ERROR: {msg}", file=sys.stderr)
    sys.exit(1)


def create_tool(tool: dict) -> str:
    """POST /v1/convai/tools — returns the new tool_id."""
    payload = {
        "name": tool["name"],
        "description": tool["description"],
        "type": "client",
        "expects_response": True,
        "parameters": tool["parameters"],
    }
    r = requests.post(f"{BASE}/convai/tools", headers=HEADERS, json=payload, timeout=30)
    if not r.ok:
        die(f"Failed to create tool '{tool['name']}': {r.status_code} {r.text}")
    tool_id = r.json().get("tool_id") or r.json().get("id")
    if not tool_id:
        die(f"No tool_id in response for '{tool['name']}': {r.text}")
    print(f"  ✓  {tool['name']} → {tool_id}")
    return tool_id


def create_agent(tool_ids: list[str]) -> str:
    """POST /v1/convai/agents/create — returns the agent_id."""
    payload = {
        "name": AGENT_NAME,
        "conversation_config": {
            "agent": {
                "prompt": {
                    "prompt": SYSTEM_PROMPT.strip(),
                    "llm": "gemini-2.0-flash",
                    "temperature": 0.7,
                    "tool_ids": tool_ids,
                },
                "first_message": (
                    "Hi! I'm Aria, your Enso interior design consultant. "
                    "I'm here to help you design the perfect room. "
                    "To get started — what room are we working on today?"
                ),
                "language": "en",
            },
            "tts": {
                "model_id": "eleven_turbo_v2_5",
                "voice_id": "pMsXgVXv3BLzUgSXRplE",  # Aria
            },
            "conversation": {
                "max_duration_seconds": 600,
            },
        },
    }
    r = requests.post(
        f"{BASE}/convai/agents/create", headers=HEADERS, json=payload, timeout=30
    )
    if not r.ok:
        die(f"Failed to create agent: {r.status_code} {r.text}")
    data = r.json()
    agent_id = data.get("agent_id") or data.get("id")
    if not agent_id:
        die(f"No agent_id in response: {r.text}")
    return agent_id


def main() -> None:
    if not ELEVENLABS_API_KEY:
        die("ELEVENLABS_API_KEY is not set in backend/src/.env")

    print(f"\nUsing API key: {ELEVENLABS_API_KEY[:8]}…\n")

    print("Creating client tools:")
    tool_ids = [create_tool(t) for t in CLIENT_TOOLS]

    print("\nCreating agent…")
    agent_id = create_agent(tool_ids)

    print(f"\n{'─' * 60}")
    print(f"✅  Agent created: {AGENT_NAME}")
    print(f"    Agent ID: {agent_id}")
    print(f"{'─' * 60}")
    print("\nAdd this to frontend/designer-next/.env.local:")
    print(f"\n    NEXT_PUBLIC_ELEVENLABS_AGENT_ID={agent_id}\n")


if __name__ == "__main__":
    main()
