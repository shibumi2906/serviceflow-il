"""Unit tests for fail-fast runtime configuration."""

import pytest
from pydantic import SecretStr, ValidationError

from serviceflow.config import Settings


def test_production_requires_secure_session_cookie() -> None:
    with pytest.raises(ValidationError, match="SESSION_COOKIE_SECURE"):
        Settings(
            app_env="production",
            app_secret_key=SecretStr(
                "production-secret-that-is-at-least-32-characters"
            ),
            database_url="postgresql+psycopg://database.invalid/serviceflow",
            session_cookie_secure=False,
        )


def test_production_rejects_placeholder_application_secret() -> None:
    with pytest.raises(ValidationError, match="APP_SECRET_KEY"):
        Settings(
            app_env="production",
            app_secret_key=SecretStr(
                "replace-with-a-random-secret-of-at-least-32-characters"
            ),
            database_url="postgresql+psycopg://database.invalid/serviceflow",
            session_cookie_secure=True,
        )
