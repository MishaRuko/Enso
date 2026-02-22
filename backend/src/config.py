"""Configuration and environment variables."""

import os
from pathlib import Path

from dotenv import load_dotenv

<<<<<<< Updated upstream
# Load .env from backend directory (one level up from src/)
load_dotenv(Path(__file__).parent.parent / ".env")
=======
_env_path = Path(__file__).parent.parent / ".env"
if not _env_path.exists():
    _env_path = Path(__file__).parent / ".env"
load_dotenv(_env_path)
>>>>>>> Stashed changes

# --- API Keys ---
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
FAL_KEY = os.getenv("FAL_KEY", "")
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY", "")
MIRO_API_TOKEN = os.getenv("MIRO_API_TOKEN", "")
MIRO_TEMPLATE_BOARD_ID = os.getenv("MIRO_TEMPLATE_BOARD_ID", "")
MIRO_MCP_ENABLED = os.getenv("MIRO_MCP_ENABLED", "true").lower() == "true"
MIRO_MCP_PACKAGE = os.getenv("MIRO_MCP_PACKAGE", "@evalstate/mcp-miro")
PEXELS_API_KEY = os.getenv("PEXELS_API_KEY", "")
STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY", "")
SKETCHFAB_API_TOKEN = os.getenv("SKETCHFAB_API_TOKEN", "")

# --- OpenRouter Models ---
CLAUDE_MODEL = "anthropic/claude-opus-4.6"
GEMINI_MODEL = "google/gemini-3.1-pro-preview"
GEMINI_IMAGE_MODEL = "google/gemini-3-pro-image-preview"

# --- fal.ai Models ---
TRELLIS_MODEL = "fal-ai/trellis-2"
TRELLIS_MULTI_MODEL = "fal-ai/trellis-2/multi"
HUNYUAN_MODEL = "fal-ai/hunyuan-3d/v3.1/rapid/image-to-3d"
TRIPOSR_MODEL = "fal-ai/triposr"

# --- Paths ---
DATA_DIR = Path(__file__).parent.parent / "data"
OUTPUT_DIR = Path(__file__).parent.parent / "output"
DATA_DIR.mkdir(exist_ok=True)
OUTPUT_DIR.mkdir(exist_ok=True)

# --- Supabase ---
DATABASE_URL = os.getenv("DATABASE_URL", "")
SUPABASE_URL = os.getenv("NEXT_PUBLIC_SUPABASE_URL", "http://127.0.0.1:54421")
SUPABASE_ANON_KEY = os.getenv("NEXT_PUBLIC_SUPABASE_ANON_KEY", "")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")

# --- Backend ---
BACKEND_PUBLIC_URL = os.getenv("BACKEND_PUBLIC_URL", "http://localhost:8100")

# --- ElevenLabs ---
ELEVENLABS_AGENT_ID = os.getenv("ELEVENLABS_AGENT_ID", "")
ELEVENLABS_VOICE_ID = os.getenv("ELEVENLABS_VOICE_ID", "")

# --- Feature Flags ---
ENABLE_VOICE_AGENT = os.getenv("ENABLE_VOICE_AGENT", "true").lower() == "true"
ENABLE_MIRO = os.getenv("ENABLE_MIRO", "true").lower() == "true"
