"""Configuration and environment variables."""

import os
from pathlib import Path

from dotenv import load_dotenv

# Load .env from backend directory
load_dotenv(Path(__file__).parent.parent / ".env")

# --- API Keys ---
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
FAL_KEY = os.getenv("FAL_KEY", "")
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY", "")

# --- OpenRouter Models ---
CLAUDE_MODEL = "anthropic/claude-opus-4.6"
GEMINI_MODEL = "google/gemini-3.1-pro-preview"
GEMINI_IMAGE_MODEL = "google/gemini-3-pro-image-preview"

# --- fal.ai Models ---
TRELLIS_MODEL = "fal-ai/trellis-2"
TRELLIS_MULTI_MODEL = "fal-ai/trellis-2/multi"
HUNYUAN_MODEL = "fal-ai/hunyuan3d/v2"
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
