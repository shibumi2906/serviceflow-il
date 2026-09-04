"""SQLAlchemy engine and session construction."""

from __future__ import annotations

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker


def build_engine(database_url: str) -> Engine:
    """Create the application engine with conservative local pool settings."""
    return create_engine(
        database_url,
        pool_pre_ping=True,
        pool_size=5,
        max_overflow=5,
        connect_args={"connect_timeout": 3},
    )


def build_session_factory(engine: Engine) -> sessionmaker[Session]:
    """Create non-expiring synchronous SQLAlchemy sessions."""
    return sessionmaker(bind=engine, expire_on_commit=False)
