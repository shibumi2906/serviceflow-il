"""Validated application configuration."""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime settings loaded from environment variables or a local .env file."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: Literal["local", "test", "production"] = "local"
    app_debug: bool = False
    app_base_url: str = "http://localhost:8000"
    app_secret_key: SecretStr = Field(min_length=32)
    database_url: str
    session_cookie_secure: bool = False
    log_level: str = "INFO"
    session_ttl_hours: int = Field(default=8, ge=1, le=168)

    def model_post_init(self, __context: object) -> None:
        """Reject insecure production-only combinations."""
        if self.app_env == "production" and not self.session_cookie_secure:
            raise ValueError("SESSION_COOKIE_SECURE must be true in production")
        if self.app_env == "production" and self.app_debug:
            raise ValueError("APP_DEBUG must be false in production")
        if (
            self.app_env == "production"
            and self.app_secret_key.get_secret_value().startswith("replace-with-")
        ):
            raise ValueError("APP_SECRET_KEY must be replaced in production")


@lru_cache
def get_settings() -> Settings:
    """Load and cache validated runtime settings."""
    return Settings()  # type: ignore[call-arg]
