"""Consistent API and HTML error rendering."""

from __future__ import annotations

import logging
from typing import Any, cast

from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, RedirectResponse, Response
from starlette.exceptions import HTTPException

from serviceflow.domain.errors import ServiceFlowError

logger = logging.getLogger(__name__)

HEBREW_ERROR_MESSAGES = {
    403: "אין הרשאה לבצע פעולה זו",
    404: "הפריט המבוקש לא נמצא",
    409: "הנתונים עודכנו במקום אחר. יש לרענן ולנסות שוב",
    422: "הפעולה המבוקשת אינה תקינה",
}


def error_payload(
    request: Request, *, code: str, message: str, details: Any
) -> dict[str, Any]:
    return {
        "code": code,
        "message": message,
        "details": details,
        "request_id": request.state.request_id,
    }


async def serviceflow_error_handler(
    request: Request, exc: ServiceFlowError
) -> Response:
    if not request.url.path.startswith("/api/"):
        if exc.status_code == 401:
            return RedirectResponse("/login", status_code=303)
        return cast(
            Response,
            request.app.state.templates.TemplateResponse(
                request=request,
                name="error.html",
                context={
                    "status_code": exc.status_code,
                    "message": HEBREW_ERROR_MESSAGES.get(
                        exc.status_code, "הבקשה לא הושלמה"
                    ),
                },
                status_code=exc.status_code,
            ),
        )
    return JSONResponse(
        error_payload(request, code=exc.code, message=exc.message, details=exc.details),
        status_code=exc.status_code,
    )


async def validation_error_handler(
    request: Request, exc: RequestValidationError
) -> Response:
    if not request.url.path.startswith("/api/"):
        return cast(
            Response,
            request.app.state.templates.TemplateResponse(
                request=request,
                name="error.html",
                context={"status_code": 422, "message": "הנתונים שנשלחו אינם תקינים"},
                status_code=422,
            ),
        )
    return JSONResponse(
        error_payload(
            request,
            code="VALIDATION_ERROR",
            message="Request validation failed",
            details=exc.errors(),
        ),
        status_code=422,
    )


async def http_error_handler(request: Request, exc: HTTPException) -> Response:
    if not request.url.path.startswith("/api/"):
        return cast(
            Response,
            request.app.state.templates.TemplateResponse(
                request=request,
                name="error.html",
                context={"status_code": exc.status_code, "message": str(exc.detail)},
                status_code=exc.status_code,
            ),
        )
    return JSONResponse(
        error_payload(
            request,
            code=f"HTTP_{exc.status_code}",
            message=str(exc.detail),
            details={},
        ),
        status_code=exc.status_code,
        headers=exc.headers,
    )


async def unexpected_error_handler(request: Request, exc: Exception) -> Response:
    logger.exception("Unhandled request error", exc_info=exc)
    if not request.url.path.startswith("/api/"):
        return cast(
            Response,
            request.app.state.templates.TemplateResponse(
                request=request,
                name="error.html",
                context={"status_code": 500, "message": "אירעה שגיאה פנימית"},
                status_code=500,
            ),
        )
    return JSONResponse(
        error_payload(
            request,
            code="INTERNAL_ERROR",
            message="An internal error occurred",
            details={},
        ),
        status_code=500,
    )
