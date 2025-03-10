import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Telegram Bot Token
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
if not TELEGRAM_BOT_TOKEN:
    raise ValueError("TELEGRAM_BOT_TOKEN environment variable not set")

# OpenAI API Key
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Gemini API Key (for fallback)
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# AI Provider selection - defaults to "openai" if not set
AI_PROVIDER = os.getenv("AI_PROVIDER", "openai").lower()

# Check if we have at least one valid API key
if not OPENAI_API_KEY and not GEMINI_API_KEY:
    raise ValueError("Either OPENAI_API_KEY or GEMINI_API_KEY environment variable must be set")

# Database URL
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./bot_database.db")