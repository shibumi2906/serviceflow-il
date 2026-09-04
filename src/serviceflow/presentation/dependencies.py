"""FastAPI dependencies shared by API and web routes."""

from __future__ import annotations

from collections.abc import Generator

from fastapi import Cookie, Depends, Request
from sqlalchemy.orm import Session

from serviceflow.application.services import AuthenticatedSession, AuthService
from serviceflow.infrastructure.models import User

SESSION_COOKIE_NAME = "serviceflow_session"


def get_db(request: Request) -> Generator[Session, None, None]:
    session = request.app.state.session_factory()
    try:
        yield session
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def get_authenticated_session(
    request: Request,
    token: str | None = Cookie(default=None, alias=SESSION_COOKIE_NAME),
    session: Session = Depends(get_db),
) -> AuthenticatedSession:
    return AuthService(
        session, ttl_hours=request.app.state.settings.session_ttl_hours
    ).resolve(token)


def get_current_user(
    authenticated: AuthenticatedSession = Depends(get_authenticated_session),
) -> User:
    return authenticated.user
