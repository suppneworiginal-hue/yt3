"""Configuration constants for the Story Generator app."""

import os
from pathlib import Path

# Get project root (where app.py is located)
PROJECT_ROOT = Path(__file__).parent.parent

# Prompt file names (exact filenames, relative to project root)
STORY_CORE_PROMPT_FILENAME = "story_core_prompt.txt"
STORY_PROMPT_FILENAME = "prompt_story.txt"

# Full paths to prompt files (resolved relative to project root)
STORY_CORE_PROMPT_PATH = PROJECT_ROOT / STORY_CORE_PROMPT_FILENAME
STORY_PROMPT_PATH = PROJECT_ROOT / STORY_PROMPT_FILENAME

# Cache directory
CACHE_DIR = "data/cache"

# Subtitle language preferences (in order)
DEFAULT_LANGS = ["en", "uk", "ru"]

# Maximum subtitle characters (safety cap)
MAX_SUBTITLE_CHARS = 200000

# Cookies file for authenticated access
COOKIES_FILE = "youtube_cookies.txt"

# LLM configuration
LLM_MODEL = "gpt-5.2-chat-latest"  # Configurable model name
LLM_TEMPERATURE = 1.0  # Fixed temperature

# LLM Backend configuration
LLM_BACKEND_DEFAULT = "openai"

# GenAI App Builder configuration
GENAI_APP_URL = os.getenv("GENAI_APP_URL", "").strip()
GENAI_APP_TOKEN = os.getenv("GENAI_APP_TOKEN", "").strip()
GENAI_APP_AUTH_MODE = os.getenv("GENAI_APP_AUTH_MODE", "bearer").strip().lower()


def ensure_cache_dir():
    """Ensure CACHE_DIR exists at runtime."""
    cache_path = Path(CACHE_DIR)
    cache_path.mkdir(parents=True, exist_ok=True)
    return cache_path

