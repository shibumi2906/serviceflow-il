"""FastAPI application entry point."""

from __future__ import annotations

import uuid
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker
from starlette.exceptions import HTTPException
from starlette.middleware.base import RequestResponseEndpoint
from starlette.responses import Response

from serviceflow.config import Settings, get_settings
from serviceflow.domain.errors import ServiceFlowError
from serviceflow.infrastructure.database import build_engine, build_session_factory
from serviceflow.presentation.api.router import router as api_router
from serviceflow.presentation.errors import (
    http_error_handler,
    serviceflow_error_handler,
    unexpected_error_handler,
    validation_error_handler,
)
from serviceflow.presentation.web.router import router as web_router

PACKAGE_DIR = Path(__file__).resolve().parent


def create_app(
    settings: Settings | None = None,
    session_factory: sessionmaker[Session] | None = None,
) -> FastAPI:
    """Construct an application with replaceable infrastructure for tests."""
    settings = settings or get_settings()
    if settings.app_mode == "full" and session_factory is None:
        if settings.database_url is None:  # guarded by Settings validation
            raise RuntimeError("DATABASE_URL is required in full mode")
        session_factory = build_session_factory(build_engine(settings.database_url))
    docs_url = (
        None
        if settings.app_env == "production" or settings.app_mode == "smoke"
        else "/docs"
    )
    application = FastAPI(
        title="ServiceFlow IL",
        version="0.3.0",
        debug=settings.app_debug,
        docs_url=docs_url,
        redoc_url=None,
    )
    application.state.settings = settings
    application.state.session_factory = session_factory
    application.state.templates = Jinja2Templates(
        directory=PACKAGE_DIR / "presentation" / "templates"
    )
    application.mount(
        "/static",
        StaticFiles(directory=PACKAGE_DIR / "presentation" / "static"),
        name="static",
    )

    @application.middleware("http")
    async def request_context(
        request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        request.state.request_id = request.headers.get("X-Request-ID") or str(
            uuid.uuid4()
        )
        response = await call_next(request)
        response.headers["X-Request-ID"] = request.state.request_id
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "same-origin"
        return response

    application.add_exception_handler(ServiceFlowError, serviceflow_error_handler)  # type: ignore[arg-type]
    application.add_exception_handler(RequestValidationError, validation_error_handler)  # type: ignore[arg-type]
    application.add_exception_handler(HTTPException, http_error_handler)  # type: ignore[arg-type]
    application.add_exception_handler(Exception, unexpected_error_handler)
    if settings.app_mode == "full":
        application.include_router(api_router)
        application.include_router(web_router)

    @application.get("/health/live", tags=["health"])
    async def liveness() -> dict[str, str]:
        return {"status": "ok"}

    @application.get("/health/ready", tags=["health"])
    def readiness() -> JSONResponse:
        if settings.app_mode == "smoke":
            return JSONResponse({"status": "ok", "mode": "smoke"})
        if session_factory is None:  # guarded by the full-mode setup above
            return JSONResponse({"status": "not_ready"}, status_code=503)
        try:
            with session_factory() as session:
                session.execute(text("SELECT 1"))
        except SQLAlchemyError:
            return JSONResponse({"status": "not_ready"}, status_code=503)
        return JSONResponse({"status": "ok"})

    return application


app = create_app()
