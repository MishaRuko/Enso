"""ElevenLabs realtime session configuration for frontend."""

import logging
import os

from ..config import BACKEND_PUBLIC_URL, ELEVENLABS_AGENT_ID, ELEVENLABS_API_KEY

logger = logging.getLogger(__name__)


def create_realtime_session_token(session_id: str) -> dict:
    """
    Mint a token or return session config for frontend to connect to ElevenLabs realtime safely.

    Does NOT expose ELEVENLABS_API_KEY to the frontend.
    Instead provides:
    - agent_id: The agent to connect to
    - backend_tool_endpoints: URL where tool calls will be routed
    - token: (if supported) API token specific to this session

    Args:
        session_id: The design session ID for context

    Returns:
        Config dict for frontend ElevenLabs client
    """

    config = {
        "agent_id": ELEVENLABS_AGENT_ID or "placeholder-agent-id",
        "backend_url": BACKEND_PUBLIC_URL,
        "tool_endpoint_base": f"{BACKEND_PUBLIC_URL}/tool",
        "session_id": session_id,
    }

    if ELEVENLABS_API_KEY:
        # TODO: If ElevenLabs supports token minting, get a limited-scope token here
        # For now, just document the approach
        # endpoint = "https://api.elevenlabs.io/v1/session/token"
        # response = requests.post(endpoint, headers={"xi-api-key": ELEVENLABS_API_KEY})
        # config["token"] = response.json()["token"]
        pass
    else:
        logger.warning("ELEVENLABS_API_KEY not set, realtime may not work")

    return config
