"""Unit tests for service-request workflow rules."""

import pytest

from serviceflow.domain.enums import RequestStatus, Role
from serviceflow.domain.errors import ValidationError
from serviceflow.domain.workflow import validate_status_transition


@pytest.mark.parametrize(
    ("current", "target"),
    [
        (RequestStatus.NEW, RequestStatus.ASSIGNED),
        (RequestStatus.NEW, RequestStatus.CANCELLED),
        (RequestStatus.ASSIGNED, RequestStatus.IN_PROGRESS),
        (RequestStatus.IN_PROGRESS, RequestStatus.WAITING_CUSTOMER),
        (RequestStatus.IN_PROGRESS, RequestStatus.COMPLETED),
        (RequestStatus.WAITING_CUSTOMER, RequestStatus.IN_PROGRESS),
        (RequestStatus.COMPLETED, RequestStatus.IN_PROGRESS),
        (RequestStatus.CANCELLED, RequestStatus.NEW),
    ],
)
def test_allowed_status_transitions(
    current: RequestStatus, target: RequestStatus
) -> None:
    validate_status_transition(current, target, Role.DISPATCHER, has_assignee=True)


def test_assigned_requires_assignee() -> None:
    with pytest.raises(ValidationError):
        validate_status_transition(
            RequestStatus.NEW,
            RequestStatus.ASSIGNED,
            Role.DISPATCHER,
            has_assignee=False,
        )


def test_technician_cannot_reopen_completed_request() -> None:
    with pytest.raises(ValidationError):
        validate_status_transition(
            RequestStatus.COMPLETED,
            RequestStatus.IN_PROGRESS,
            Role.TECHNICIAN,
            has_assignee=True,
        )


def test_invalid_transition_is_rejected() -> None:
    with pytest.raises(ValidationError):
        validate_status_transition(
            RequestStatus.NEW,
            RequestStatus.COMPLETED,
            Role.ADMINISTRATOR,
            has_assignee=False,
        )
