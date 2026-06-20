from pathlib import Path

from dotenv import load_dotenv
from pydantic_settings import BaseSettings, SettingsConfigDict

# Anchor .env to the project root (parent of src/) so it loads regardless of cwd.
# We use python-dotenv directly with override=True because pydantic-settings'
# built-in env_file loader gets shadowed when something earlier in the import
# chain seeds os.environ with empty strings for these keys.
ENV_PATH = Path(__file__).resolve().parents[2] / ".env"
load_dotenv(ENV_PATH, override=True)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(extra="ignore")

    anthropic_api_key: str = ""
    default_model: str = "claude-sonnet-4-6"
    fast_model: str = "claude-haiku-4-5"

    # Optional: Gemini for cheap classifier tasks (much cheaper than Haiku).
    # If GEMINI_API_KEY is set, intent + news classifiers + Pat's free-text
    # router go to Gemini; else falls back to Anthropic Haiku. Get a key at
    # https://aistudio.google.com/apikey
    # Default = 2.5-flash-lite: gemini-2.0-flash's free tier is quota-0 (limit:0)
    # as of 2026-06, and 2.5-flash-lite also captures chip params better.
    gemini_api_key: str = ""
    gemini_classifier_model: str = "gemini-2.5-flash-lite"

    host: str = "0.0.0.0"
    port: int = 8000
    log_level: str = "INFO"

    telegram_bot_token: str = ""
    telegram_allowed_user_ids: str = ""

    trading_live: bool = False
    broker_api_key: str = ""
    broker_api_secret: str = ""

    database_url: str = "sqlite:///./data/hermes.db"


settings = Settings()
