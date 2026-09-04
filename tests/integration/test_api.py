"""API, authorization, history, and concurrency tests on PostgreSQL."""

from __future__ import annotations

import re
from collections.abc import Callable

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from serviceflow.domain.enums import EventType, Role
from serviceflow.infrastructure.models import User

UserFactory = Callable[[Role, str | None, str], User]


def login(client: TestClient, email: str, password: str) -> None:
    response = client.post(
        "/api/v1/auth/login", json={"email": email, "password": password}
    )
    assert response.status_code == 200


@pytest.mark.integration
def test_unauthenticated_error_has_uniform_contract(client: TestClient) -> None:
    response = client.get("/api/v1/requests")

    assert response.status_code == 401
    assert response.json()["code"] == "UNAUTHENTICATED"
    assert response.json()["request_id"] == response.headers["X-Request-ID"]


@pytest.mark.integration
def test_request_workflow_history_permissions_and_optimistic_locking(
    client: TestClient,
    db_session: Session,
    user_factory: UserFactory,
) -> None:
    password = "correct-horse-battery-staple"
    dispatcher = user_factory(Role.DISPATCHER, "dispatcher@example.com", password)
    technician = user_factory(Role.TECHNICIAN, "tech@example.com", password)
    other_technician = user_factory(Role.TECHNICIAN, "other@example.com", password)
    login(client, dispatcher.email, password)

    customer_response = client.post(
        "/api/v1/customers",
        json={"name": "Test Customer", "phone": "+972 50 123 4567"},
    )
    assert customer_response.status_code == 201
    request_response = client.post(
        "/api/v1/requests",
        json={
            "customer_id": customer_response.json()["id"],
            "title": "Broken air conditioner",
            "description": "The unit does not start",
            "priority": "HIGH",
            "assigned_to": str(technician.id),
        },
    )
    assert request_response.status_code == 201
    request_data = request_response.json()
    assert request_data["status"] == "ASSIGNED"
    assert client.get("/api/v1/requests?search=air").json()["total"] == 1
    assert client.get("/api/v1/requests?priority=LOW").json()["total"] == 0
    assert (
        client.get(f"/api/v1/requests?assignee_id={technician.id}").json()["total"] == 1
    )
    client.post("/api/v1/auth/logout")

    login(client, other_technician.email, password)
    assert client.get(f"/api/v1/requests/{request_data['id']}").status_code == 403
    assert client.get("/api/v1/requests").json()["total"] == 0
    client.post("/api/v1/auth/logout")

    login(client, technician.email, password)
    visible = client.get("/api/v1/requests").json()
    assert visible["total"] == 1
    updated = client.patch(
        f"/api/v1/requests/{request_data['id']}",
        json={"version": request_data["version"], "status": "IN_PROGRESS"},
    )
    assert updated.status_code == 200
    assert updated.json()["version"] == 2

    stale = client.patch(
        f"/api/v1/requests/{request_data['id']}",
        json={"version": request_data["version"], "status": "WAITING_CUSTOMER"},
    )
    assert stale.status_code == 409
    assert stale.json()["details"]["current_version"] == 2

    completed = client.patch(
        f"/api/v1/requests/{request_data['id']}",
        json={"version": 2, "status": "COMPLETED"},
    )
    assert completed.status_code == 200
    assert completed.json()["completed_at"] is not None

    comment = client.post(
        f"/api/v1/requests/{request_data['id']}/comments",
        json={"body": "Arriving tomorrow"},
    )
    assert comment.status_code == 201
    client.post("/api/v1/auth/logout")
    login(client, dispatcher.email, password)
    reopened = client.patch(
        f"/api/v1/requests/{request_data['id']}",
        json={"version": 3, "status": "IN_PROGRESS"},
    )
    assert reopened.status_code == 200
    assert reopened.json()["completed_at"] is None
    history = client.get(f"/api/v1/requests/{request_data['id']}/history").json()
    assert [event["event_type"] for event in history] == [
        EventType.REQUEST_CREATED,
        EventType.STATUS_CHANGED,
        EventType.STATUS_CHANGED,
        EventType.COMMENT_ADDED,
        EventType.STATUS_CHANGED,
    ]
    assert all("password" not in str(event["payload"]).casefold() for event in history)


@pytest.mark.integration
def test_deactivated_user_loses_existing_session(
    client: TestClient, db_session: Session, user_factory: UserFactory
) -> None:
    password = "correct-horse-battery-staple"
    user = user_factory(Role.DISPATCHER, "disabled@example.com", password)
    login(client, user.email, password)
    user.is_active = False
    db_session.commit()

    response = client.get("/api/v1/requests")

    assert response.status_code == 401


@pytest.mark.integration
def test_html_forms_and_staff_management_require_csrf(
    client: TestClient, db_session: Session, user_factory: UserFactory
) -> None:
    password = "correct-horse-battery-staple"
    admin = user_factory(Role.ADMINISTRATOR, "admin@example.com", password)
    login_page = client.get("/login")
    login_csrf = client.cookies["serviceflow_login_csrf"]
    assert 'lang="he" dir="rtl"' in login_page.text
    login_response = client.post(
        "/login",
        data={"email": admin.email, "password": password, "csrf_token": login_csrf},
        follow_redirects=False,
    )
    assert login_response.status_code == 303

    invalid_csrf = client.post(
        "/customers",
        data={
            "name": "Invalid CSRF",
            "phone": "050-1234567",
            "csrf_token": "wrong-token",
        },
    )
    assert invalid_csrf.status_code == 403

    customers_page = client.get("/customers")
    match = re.search(r'name="csrf_token" value="([^"]+)"', customers_page.text)
    assert match is not None
    valid_csrf = client.post(
        "/customers",
        data={
            "name": "Valid CSRF",
            "phone": "050-1234567",
            "csrf_token": match.group(1),
        },
        follow_redirects=False,
    )
    assert valid_csrf.status_code == 303

    create_staff = client.post(
        "/admin/users",
        data={
            "email": "new-tech@example.com",
            "password": "a-secure-initial-password",
            "display_name": "New Technician",
            "role": "TECHNICIAN",
            "csrf_token": match.group(1),
        },
        follow_redirects=False,
    )
    assert create_staff.status_code == 303
    created_staff = db_session.scalar(
        select(User).where(User.email == "new-tech@example.com")
    )
    assert created_staff is not None

    deactivate_staff = client.post(
        f"/admin/users/{created_staff.id}/active",
        data={"is_active": "false", "csrf_token": match.group(1)},
        follow_redirects=False,
    )
    assert deactivate_staff.status_code == 303
    db_session.expire_all()
    deactivated_staff = db_session.get(User, created_staff.id)
    assert deactivated_staff is not None
    assert deactivated_staff.is_active is False


@pytest.mark.integration
def test_html_not_found_page_is_hebrew_rtl(client: TestClient) -> None:
    response = client.get("/missing-page")

    assert response.status_code == 404
    assert 'lang="he" dir="rtl"' in response.text
    assert "אירעה שגיאה" in response.text
