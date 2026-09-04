"""Versioned REST API routes."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Cookie, Depends, Query, Request, Response, status
from sqlalchemy.orm import Session

from serviceflow.application.services import (
    AuthService,
    CustomerService,
    RequestChanges,
    RequestService,
)
from serviceflow.domain.enums import RequestPriority, RequestStatus
from serviceflow.infrastructure.models import User
from serviceflow.presentation.dependencies import (
    SESSION_COOKIE_NAME,
    get_current_user,
    get_db,
)
from serviceflow.presentation.schemas import (
    CommentCreate,
    CommentRead,
    CustomerCreate,
    CustomerPage,
    CustomerRead,
    CustomerUpdate,
    EventRead,
    LoginInput,
    RequestCreate,
    RequestPage,
    RequestRead,
    RequestUpdate,
    UserRead,
)

router = APIRouter(prefix="/api/v1")


@router.post("/auth/login", response_model=UserRead)
def login(
    payload: LoginInput,
    request: Request,
    response: Response,
    session: Session = Depends(get_db),
) -> User:
    user, token = AuthService(
        session, ttl_hours=request.app.state.settings.session_ttl_hours
    ).login(str(payload.email), payload.password)
    response.set_cookie(
        SESSION_COOKIE_NAME,
        token,
        httponly=True,
        secure=request.app.state.settings.session_cookie_secure,
        samesite="lax",
        max_age=request.app.state.settings.session_ttl_hours * 3600,
    )
    return user


@router.post("/auth/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(
    response: Response,
    session: Session = Depends(get_db),
    token: str | None = Cookie(default=None, alias=SESSION_COOKIE_NAME),
) -> None:
    AuthService(session).logout(token)
    response.delete_cookie(SESSION_COOKIE_NAME)


@router.post("/customers", response_model=CustomerRead, status_code=201)
def create_customer(
    payload: CustomerCreate,
    actor: User = Depends(get_current_user),
    session: Session = Depends(get_db),
) -> object:
    return CustomerService(session).create(actor, **payload.model_dump(mode="json"))


@router.get("/customers", response_model=CustomerPage)
def list_customers(
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
    actor: User = Depends(get_current_user),
    session: Session = Depends(get_db),
) -> CustomerPage:
    items, total = CustomerService(session).list(actor, limit=limit, offset=offset)
    return CustomerPage(
        items=[CustomerRead.model_validate(item) for item in items],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/customers/{customer_id}", response_model=CustomerRead)
def get_customer(
    customer_id: uuid.UUID,
    actor: User = Depends(get_current_user),
    session: Session = Depends(get_db),
) -> object:
    return CustomerService(session).get(actor, customer_id)


@router.patch("/customers/{customer_id}", response_model=CustomerRead)
def update_customer(
    customer_id: uuid.UUID,
    payload: CustomerUpdate,
    actor: User = Depends(get_current_user),
    session: Session = Depends(get_db),
) -> object:
    return CustomerService(session).update(
        actor,
        customer_id,
        changes=payload.model_dump(exclude_unset=True, mode="json"),
    )


@router.post("/requests", response_model=RequestRead, status_code=201)
def create_request(
    payload: RequestCreate,
    actor: User = Depends(get_current_user),
    session: Session = Depends(get_db),
) -> object:
    return RequestService(session).create(actor, **payload.model_dump())


@router.get("/requests", response_model=RequestPage)
def list_requests(
    request_status: Annotated[RequestStatus | None, Query(alias="status")] = None,
    priority: RequestPriority | None = None,
    assignee_id: uuid.UUID | None = None,
    search: str | None = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
    actor: User = Depends(get_current_user),
    session: Session = Depends(get_db),
) -> RequestPage:
    items, total = RequestService(session).list(
        actor,
        status=request_status,
        priority=priority,
        assignee_id=assignee_id,
        search=search,
        limit=limit,
        offset=offset,
    )
    return RequestPage(
        items=[RequestRead.model_validate(item) for item in items],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/requests/{request_id}", response_model=RequestRead)
def get_request(
    request_id: uuid.UUID,
    actor: User = Depends(get_current_user),
    session: Session = Depends(get_db),
) -> object:
    return RequestService(session).get(actor, request_id)


@router.patch("/requests/{request_id}", response_model=RequestRead)
def update_request(
    request_id: uuid.UUID,
    payload: RequestUpdate,
    actor: User = Depends(get_current_user),
    session: Session = Depends(get_db),
) -> object:
    fields = payload.model_fields_set
    return RequestService(session).update(
        actor,
        request_id,
        RequestChanges(
            version=payload.version,
            title=payload.title,
            description=payload.description,
            status=payload.status,
            priority=payload.priority,
            assigned_to=payload.assigned_to,
            assignee_was_set="assigned_to" in fields,
        ),
    )


@router.post(
    "/requests/{request_id}/comments", response_model=CommentRead, status_code=201
)
def add_comment(
    request_id: uuid.UUID,
    payload: CommentCreate,
    actor: User = Depends(get_current_user),
    session: Session = Depends(get_db),
) -> object:
    return RequestService(session).add_comment(actor, request_id, body=payload.body)


@router.get("/requests/{request_id}/history", response_model=list[EventRead])
def request_history(
    request_id: uuid.UUID,
    actor: User = Depends(get_current_user),
    session: Session = Depends(get_db),
) -> object:
    return RequestService(session).history(actor, request_id)
