"""Pure service-request workflow rules."""

from serviceflow.domain.enums import RequestStatus, Role
from serviceflow.domain.errors import ValidationError

TRANSITIONS: dict[RequestStatus, frozenset[RequestStatus]] = {
    RequestStatus.NEW: frozenset({RequestStatus.ASSIGNED, RequestStatus.CANCELLED}),
    RequestStatus.ASSIGNED: frozenset(
        {RequestStatus.IN_PROGRESS, RequestStatus.NEW, RequestStatus.CANCELLED}
    ),
    RequestStatus.IN_PROGRESS: frozenset(
        {
            RequestStatus.WAITING_CUSTOMER,
            RequestStatus.COMPLETED,
            RequestStatus.CANCELLED,
        }
    ),
    RequestStatus.WAITING_CUSTOMER: frozenset(
        {
            RequestStatus.IN_PROGRESS,
            RequestStatus.COMPLETED,
            RequestStatus.CANCELLED,
        }
    ),
    RequestStatus.COMPLETED: frozenset({RequestStatus.IN_PROGRESS}),
    RequestStatus.CANCELLED: frozenset({RequestStatus.NEW}),
}


def validate_status_transition(
    current: RequestStatus,
    target: RequestStatus,
    role: Role,
    *,
    has_assignee: bool,
) -> None:
    """Raise a domain error when a requested workflow transition is invalid."""
    if current == target:
        return
    if target not in TRANSITIONS[current]:
        raise ValidationError(
            "Status transition is not allowed",
            {"from": current.value, "to": target.value},
        )
    if current in {RequestStatus.COMPLETED, RequestStatus.CANCELLED} and role not in {
        Role.ADMINISTRATOR,
        Role.DISPATCHER,
    }:
        raise ValidationError(
            "Only an administrator or dispatcher can reopen a request"
        )
    if target == RequestStatus.ASSIGNED and not has_assignee:
        raise ValidationError("An assignee is required for ASSIGNED status")
