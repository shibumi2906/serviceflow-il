"""Server-rendered Hebrew web routes."""

from __future__ import annotations

import hmac
import uuid
from typing import Annotated, Any, cast

from fastapi import APIRouter, Cookie, Depends, Form, Request
from fastapi.responses import RedirectResponse, Response
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from serviceflow.application.services import (
    AuthenticatedSession,
    AuthService,
    CustomerService,
    RequestChanges,
    RequestService,
    StaffService,
)
from serviceflow.domain.enums import RequestPriority, RequestStatus, Role
from serviceflow.domain.errors import ForbiddenError
from serviceflow.infrastructure.security import new_csrf_token
from serviceflow.presentation.dependencies import (
    SESSION_COOKIE_NAME,
    get_authenticated_session,
    get_db,
)

router = APIRouter()
LOGIN_CSRF_COOKIE = "serviceflow_login_csrf"

STATUS_LABELS = {
    RequestStatus.NEW: "חדשה",
    RequestStatus.ASSIGNED: "הוקצתה",
    RequestStatus.IN_PROGRESS: "בטיפול",
    RequestStatus.WAITING_CUSTOMER: "ממתינה ללקוח",
    RequestStatus.COMPLETED: "הושלמה",
    RequestStatus.CANCELLED: "בוטלה",
}
PRIORITY_LABELS = {
    RequestPriority.LOW: "נמוכה",
    RequestPriority.NORMAL: "רגילה",
    RequestPriority.HIGH: "גבוהה",
    RequestPriority.URGENT: "דחופה",
}
ROLE_LABELS = {
    Role.ADMINISTRATOR: "מנהל מערכת",
    Role.DISPATCHER: "מוקדן",
    Role.TECHNICIAN: "טכנאי",
}


def _validate_csrf(authenticated: AuthenticatedSession, submitted: str) -> None:
    if not hmac.compare_digest(authenticated.browser_session.csrf_token, submitted):
        raise ForbiddenError("Invalid CSRF token")


def _render(
    request: Request, name: str, context: dict[str, Any], *, status_code: int = 200
) -> Response:
    templates = cast(Jinja2Templates, request.app.state.templates)
    return templates.TemplateResponse(
        request=request, name=name, context=context, status_code=status_code
    )


def _optional_uuid(value: str | None) -> uuid.UUID | None:
    return uuid.UUID(value) if value else None


@router.get("/", include_in_schema=False)
def home() -> RedirectResponse:
    return RedirectResponse("/requests", status_code=303)


@router.get("/login", include_in_schema=False)
def login_page(request: Request) -> Response:
    csrf_token = new_csrf_token()
    response = _render(request, "login.html", {"csrf_token": csrf_token})
    response.set_cookie(
        LOGIN_CSRF_COOKIE,
        csrf_token,
        httponly=True,
        secure=request.app.state.settings.session_cookie_secure,
        samesite="lax",
    )
    return response


@router.post("/login", include_in_schema=False)
def login_submit(
    request: Request,
    email: Annotated[str, Form()],
    password: Annotated[str, Form()],
    csrf_token: Annotated[str, Form()],
    session: Session = Depends(get_db),
    login_csrf: str | None = Cookie(default=None, alias=LOGIN_CSRF_COOKIE),
) -> Response:
    if login_csrf is None or not hmac.compare_digest(login_csrf, csrf_token):
        raise ForbiddenError("Invalid CSRF token")
    user, token = AuthService(
        session, ttl_hours=request.app.state.settings.session_ttl_hours
    ).login(email, password)
    del user
    response = RedirectResponse("/requests", status_code=303)
    response.set_cookie(
        SESSION_COOKIE_NAME,
        token,
        httponly=True,
        secure=request.app.state.settings.session_cookie_secure,
        samesite="lax",
        max_age=request.app.state.settings.session_ttl_hours * 3600,
    )
    response.delete_cookie(LOGIN_CSRF_COOKIE)
    return response


@router.post("/logout", include_in_schema=False)
def logout_submit(
    csrf_token: Annotated[str, Form()],
    authenticated: AuthenticatedSession = Depends(get_authenticated_session),
    session: Session = Depends(get_db),
    token: str | None = Cookie(default=None, alias=SESSION_COOKIE_NAME),
) -> Response:
    _validate_csrf(authenticated, csrf_token)
    AuthService(session).logout(token)
    response = RedirectResponse("/login", status_code=303)
    response.delete_cookie(SESSION_COOKIE_NAME)
    return response


@router.get("/requests", include_in_schema=False)
def requests_page(
    request: Request,
    status: RequestStatus | None = None,
    priority: RequestPriority | None = None,
    assignee_id: uuid.UUID | None = None,
    search: str | None = None,
    page: int = 1,
    authenticated: AuthenticatedSession = Depends(get_authenticated_session),
    session: Session = Depends(get_db),
) -> Response:
    page = max(page, 1)
    items, total = RequestService(session).list(
        authenticated.user,
        status=status,
        priority=priority,
        assignee_id=assignee_id,
        search=search,
        limit=20,
        offset=(page - 1) * 20,
    )
    return _render(
        request,
        "requests/list.html",
        {
            "user": authenticated.user,
            "csrf_token": authenticated.browser_session.csrf_token,
            "requests": items,
            "total": total,
            "page": page,
            "statuses": RequestStatus,
            "priorities": RequestPriority,
            "status_labels": STATUS_LABELS,
            "priority_labels": PRIORITY_LABELS,
            "selected_status": status,
            "selected_priority": priority,
            "selected_assignee": assignee_id,
            "users": StaffService(session).list_active(authenticated.user),
            "search": search or "",
        },
    )


@router.get("/requests/new", include_in_schema=False)
def request_create_page(
    request: Request,
    authenticated: AuthenticatedSession = Depends(get_authenticated_session),
    session: Session = Depends(get_db),
) -> Response:
    if authenticated.user.role == Role.TECHNICIAN:
        raise ForbiddenError("Technicians cannot create requests")
    customers, _ = CustomerService(session).list(
        authenticated.user, limit=100, offset=0
    )
    users = StaffService(session).list_active(authenticated.user)
    return _render(
        request,
        "requests/create.html",
        {
            "user": authenticated.user,
            "csrf_token": authenticated.browser_session.csrf_token,
            "customers": customers,
            "users": users,
            "priorities": RequestPriority,
            "priority_labels": PRIORITY_LABELS,
        },
    )


@router.post("/requests/new", include_in_schema=False)
def request_create_submit(
    customer_id: Annotated[uuid.UUID, Form()],
    title: Annotated[str, Form(min_length=1, max_length=200)],
    description: Annotated[str, Form(min_length=1, max_length=20_000)],
    priority: Annotated[RequestPriority, Form()],
    csrf_token: Annotated[str, Form()],
    assigned_to: Annotated[str | None, Form()] = None,
    authenticated: AuthenticatedSession = Depends(get_authenticated_session),
    session: Session = Depends(get_db),
) -> Response:
    _validate_csrf(authenticated, csrf_token)
    created = RequestService(session).create(
        authenticated.user,
        customer_id=customer_id,
        title=title,
        description=description,
        priority=priority,
        assigned_to=_optional_uuid(assigned_to),
    )
    return RedirectResponse(f"/requests/{created.id}", status_code=303)


@router.get("/requests/{request_id}", include_in_schema=False)
def request_detail_page(
    request: Request,
    request_id: uuid.UUID,
    authenticated: AuthenticatedSession = Depends(get_authenticated_session),
    session: Session = Depends(get_db),
) -> Response:
    service = RequestService(session)
    item = service.get(authenticated.user, request_id)
    users = StaffService(session).list_active(authenticated.user)
    return _render(
        request,
        "requests/detail.html",
        {
            "user": authenticated.user,
            "csrf_token": authenticated.browser_session.csrf_token,
            "item": item,
            "comments": service.comments(authenticated.user, request_id),
            "events": service.history(authenticated.user, request_id),
            "users": users,
            "statuses": RequestStatus,
            "status_labels": STATUS_LABELS,
            "priority_labels": PRIORITY_LABELS,
        },
    )


@router.post("/requests/{request_id}/status", include_in_schema=False)
def request_status_submit(
    request_id: uuid.UUID,
    version: Annotated[int, Form()],
    status: Annotated[RequestStatus, Form()],
    csrf_token: Annotated[str, Form()],
    authenticated: AuthenticatedSession = Depends(get_authenticated_session),
    session: Session = Depends(get_db),
) -> Response:
    _validate_csrf(authenticated, csrf_token)
    RequestService(session).update(
        authenticated.user,
        request_id,
        RequestChanges(version=version, status=status),
    )
    return RedirectResponse(f"/requests/{request_id}", status_code=303)


@router.post("/requests/{request_id}/manage", include_in_schema=False)
def request_manage_submit(
    request_id: uuid.UUID,
    version: Annotated[int, Form()],
    priority: Annotated[RequestPriority, Form()],
    csrf_token: Annotated[str, Form()],
    assigned_to: Annotated[str | None, Form()] = None,
    authenticated: AuthenticatedSession = Depends(get_authenticated_session),
    session: Session = Depends(get_db),
) -> Response:
    _validate_csrf(authenticated, csrf_token)
    RequestService(session).update(
        authenticated.user,
        request_id,
        RequestChanges(
            version=version,
            priority=priority,
            assigned_to=_optional_uuid(assigned_to),
            assignee_was_set=True,
        ),
    )
    return RedirectResponse(f"/requests/{request_id}", status_code=303)


@router.post("/requests/{request_id}/comments", include_in_schema=False)
def request_comment_submit(
    request_id: uuid.UUID,
    body: Annotated[str, Form(min_length=1, max_length=10_000)],
    csrf_token: Annotated[str, Form()],
    authenticated: AuthenticatedSession = Depends(get_authenticated_session),
    session: Session = Depends(get_db),
) -> Response:
    _validate_csrf(authenticated, csrf_token)
    RequestService(session).add_comment(authenticated.user, request_id, body=body)
    return RedirectResponse(f"/requests/{request_id}", status_code=303)


@router.get("/customers", include_in_schema=False)
def customers_page(
    request: Request,
    authenticated: AuthenticatedSession = Depends(get_authenticated_session),
    session: Session = Depends(get_db),
) -> Response:
    customers, _ = CustomerService(session).list(
        authenticated.user, limit=100, offset=0
    )
    return _render(
        request,
        "customers.html",
        {
            "user": authenticated.user,
            "csrf_token": authenticated.browser_session.csrf_token,
            "customers": customers,
        },
    )


@router.post("/customers", include_in_schema=False)
def customer_create_submit(
    name: Annotated[str, Form(min_length=1, max_length=200)],
    csrf_token: Annotated[str, Form()],
    phone: Annotated[str | None, Form(max_length=40)] = None,
    email: Annotated[str | None, Form(max_length=320)] = None,
    address: Annotated[str | None, Form(max_length=2000)] = None,
    note: Annotated[str | None, Form(max_length=5000)] = None,
    authenticated: AuthenticatedSession = Depends(get_authenticated_session),
    session: Session = Depends(get_db),
) -> Response:
    _validate_csrf(authenticated, csrf_token)
    CustomerService(session).create(
        authenticated.user,
        name=name,
        phone=phone,
        email=email,
        address=address,
        note=note,
    )
    return RedirectResponse("/customers", status_code=303)


@router.get("/admin/users", include_in_schema=False)
def users_page(
    request: Request,
    authenticated: AuthenticatedSession = Depends(get_authenticated_session),
    session: Session = Depends(get_db),
) -> Response:
    users = StaffService(session).list_all(authenticated.user)
    return _render(
        request,
        "users.html",
        {
            "user": authenticated.user,
            "csrf_token": authenticated.browser_session.csrf_token,
            "users": users,
            "roles": Role,
            "role_labels": ROLE_LABELS,
        },
    )


@router.post("/admin/users", include_in_schema=False)
def user_create_submit(
    email: Annotated[str, Form(max_length=320)],
    password: Annotated[str, Form(min_length=12, max_length=1024)],
    display_name: Annotated[str, Form(min_length=1, max_length=200)],
    role: Annotated[Role, Form()],
    csrf_token: Annotated[str, Form()],
    authenticated: AuthenticatedSession = Depends(get_authenticated_session),
    session: Session = Depends(get_db),
) -> Response:
    _validate_csrf(authenticated, csrf_token)
    StaffService(session).create(
        authenticated.user,
        email=email,
        password=password,
        display_name=display_name,
        role=role,
    )
    return RedirectResponse("/admin/users", status_code=303)


@router.post("/admin/users/{user_id}/active", include_in_schema=False)
def user_active_submit(
    user_id: uuid.UUID,
    is_active: Annotated[bool, Form()],
    csrf_token: Annotated[str, Form()],
    authenticated: AuthenticatedSession = Depends(get_authenticated_session),
    session: Session = Depends(get_db),
) -> Response:
    _validate_csrf(authenticated, csrf_token)
    StaffService(session).set_active(authenticated.user, user_id, is_active=is_active)
    return RedirectResponse("/admin/users", status_code=303)
