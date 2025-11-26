from collections.abc import Iterable
from functools import lru_cache
from json import JSONDecodeError, loads
from typing import Any, Literal, Optional

from pydantic import Field, HttpUrl, validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_DEFAULT_ALLOWED_UPDATES: tuple[str, ...] = ("message", "callback_query")


def _normalize_allowed_updates(raw: object) -> tuple[str, ...]:
    if raw is None or raw == "":
        return _DEFAULT_ALLOWED_UPDATES

    if isinstance(raw, str):
        candidates = [item.strip() for item in raw.split(",")]
    elif isinstance(raw, Iterable) and not isinstance(raw, dict):
        candidates = [str(item).strip() for item in raw]
    else:
        raise ValueError(
            "Invalid value for TELEGRAM_ALLOWED_UPDATES; provide comma-separated text "
            "or a sequence."
        )

    cleaned = tuple(item for item in candidates if item)
    return cleaned or _DEFAULT_ALLOWED_UPDATES


def _safe_json_loads(value: str) -> Any:
    if value is None:
        return value

    stripped = value.strip()
    if not stripped:
        return value

    try:
        return loads(value)
    except JSONDecodeError:
        return value


class Settings(BaseSettings):
    """Runtime configuration loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=False,
        enable_decoding=False,
    )

    environment: Literal["development", "staging", "production"] = Field(
        default="development", alias="APP_ENV"
    )
    log_level: str = Field(default="INFO", alias="APP_LOG_LEVEL")
    telegram_bot_token: str = Field(..., alias="TELEGRAM_BOT_TOKEN")
    telegram_webhook_url: Optional[HttpUrl] = Field(
        default=None, alias="TELEGRAM_WEBHOOK_URL"
    )
    telegram_webhook_path: str = Field(default="/telegram/webhook")

    telegram_allowed_updates: tuple[str, ...] = Field(
        default=_DEFAULT_ALLOWED_UPDATES,
        alias="TELEGRAM_ALLOWED_UPDATES",
    )

    google_api_key: str = Field(..., alias="GOOGLE_API_KEY")
    google_agent_model: str = Field(default="gemini-2.5-flash", alias="GOOGLE_AGENT_MODEL")
    google_agent_name: str = Field(default="transmibot-agent", alias="GOOGLE_AGENT_NAME")

    tomtom_api_key: str = Field(..., alias="TOMTOM_API_KEY")

    port: int = Field(default=8080, alias="PORT")

    @validator("telegram_allowed_updates", pre=True)
    def _split_allowed_updates(
        cls, value: object
    ) -> tuple[str, ...]:  # noqa: D417
        return _normalize_allowed_updates(value)

@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return cached settings instance."""

    return Settings()

