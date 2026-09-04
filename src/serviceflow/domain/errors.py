"""Transport-independent domain and application errors."""

from __future__ import annotations

from typing import Any


class ServiceFlowError(Exception):
    """Base error that can be rendered consistently by presentation adapters."""

    status_code = 400
    code = "BAD_REQUEST"

    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or {}


class NotFoundError(ServiceFlowError):
    status_code = 404
    code = "NOT_FOUND"


class ForbiddenError(ServiceFlowError):
    status_code = 403
    code = "FORBIDDEN"


class AuthenticationError(ServiceFlowError):
    status_code = 401
    code = "UNAUTHENTICATED"


class ConflictError(ServiceFlowError):
    status_code = 409
    code = "CONFLICT"


class ValidationError(ServiceFlowError):
    status_code = 422
    code = "DOMAIN_VALIDATION_ERROR"
