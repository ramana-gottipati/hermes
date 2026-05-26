from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

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
