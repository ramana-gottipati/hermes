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
