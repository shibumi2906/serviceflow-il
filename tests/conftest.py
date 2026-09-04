"""Shared test configuration and isolated PostgreSQL fixtures."""

from __future__ import annotations

import os
import uuid
from collections.abc import Callable, Generator

import psycopg
import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from psycopg import sql
from pydantic import SecretStr
from sqlalchemy import Engine, create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session, sessionmaker

os.environ.setdefault("APP_ENV", "test")
os.environ.setdefault(
    "APP_SECRET_KEY", "test-secret-key-that-is-at-least-32-characters"
)
os.environ.setdefault(
    "DATABASE_URL",
    "postgresql+psycopg://serviceflow:serviceflow@127.0.0.1:5432/serviceflow_test",
)
os.environ.setdefault("SESSION_COOKIE_SECURE", "false")

from serviceflow.config import Settings  # noqa: E402
from serviceflow.domain.enums import Role  # noqa: E402
from serviceflow.infrastructure.models import User  # noqa: E402
from serviceflow.infrastructure.security import hash_password  # noqa: E402
from serviceflow.main import create_app  # noqa: E402

TEST_DATABASE_URL = os.environ["DATABASE_URL"]


@pytest.fixture(scope="session")
def migrated_engine() -> Generator[Engine, None, None]:
    """Create a disposable database and migrate it from an empty state."""
    parsed = make_url(TEST_DATABASE_URL)
    database_name = parsed.database
    if not database_name or not database_name.endswith("_test"):
        raise RuntimeError("Integration tests require a database ending in _test")
    admin_url = parsed.set(database="postgres").render_as_string(hide_password=False)
    admin_url = admin_url.replace("postgresql+psycopg://", "postgresql://")
    with psycopg.connect(admin_url, autocommit=True) as connection:
        connection.execute(
            sql.SQL("DROP DATABASE IF EXISTS {} WITH (FORCE)").format(
                sql.Identifier(database_name)
            )
        )
        connection.execute(
            sql.SQL("CREATE DATABASE {}").format(sql.Identifier(database_name))
        )

    alembic = Config("alembic.ini")
    alembic.set_main_option("sqlalchemy.url", TEST_DATABASE_URL)
    command.upgrade(alembic, "head")
    engine = create_engine(TEST_DATABASE_URL, pool_pre_ping=True)
    yield engine
    engine.dispose()
    with psycopg.connect(admin_url, autocommit=True) as connection:
        connection.execute(
            sql.SQL("DROP DATABASE IF EXISTS {} WITH (FORCE)").format(
                sql.Identifier(database_name)
            )
        )


@pytest.fixture
def session_factory(migrated_engine: Engine) -> sessionmaker[Session]:
    with migrated_engine.begin() as connection:
        connection.execute(
            text(
                "TRUNCATE user_sessions, request_events, comments, service_requests, "
                "customers, users RESTART IDENTITY CASCADE"
            )
        )
    return sessionmaker(bind=migrated_engine, expire_on_commit=False)


@pytest.fixture
def db_session(
    session_factory: sessionmaker[Session],
) -> Generator[Session, None, None]:
    with session_factory() as session:
        yield session


@pytest.fixture
def settings() -> Settings:
    return Settings(
        app_env="test",
        app_secret_key=SecretStr("test-secret-key-that-is-at-least-32-characters"),
        database_url=TEST_DATABASE_URL,
        session_cookie_secure=False,
    )


@pytest.fixture
def client(
    settings: Settings, session_factory: sessionmaker[Session]
) -> Generator[TestClient, None, None]:
    with TestClient(create_app(settings, session_factory)) as test_client:
        yield test_client


def make_user(
    session: Session,
    *,
    role: Role,
    email: str | None = None,
    password: str = "correct-horse-battery-staple",
) -> User:
    user = User(
        id=uuid.uuid4(),
        email=email or f"{role.value.casefold()}-{uuid.uuid4()}@example.com",
        password_hash=hash_password(password),
        display_name=role.value.title(),
        role=role,
        is_active=True,
    )
    session.add(user)
    session.commit()
    return user


@pytest.fixture
def user_factory(
    db_session: Session,
) -> Callable[[Role, str | None, str], User]:
    def factory(
        role: Role,
        email: str | None = None,
        password: str = "correct-horse-battery-staple",
    ) -> User:
        return make_user(db_session, role=role, email=email, password=password)

    return factory
