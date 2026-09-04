"""SQLAlchemy repositories used by application services."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Select, String, func, or_, select
from sqlalchemy.orm import Session, joinedload

from serviceflow.domain.enums import RequestPriority, RequestStatus
from serviceflow.infrastructure.models import (
    Comment,
    Customer,
    RequestEvent,
    ServiceRequest,
    User,
    UserSession,
)


class UserRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def by_id(self, user_id: uuid.UUID) -> User | None:
        return self.session.get(User, user_id)

    def by_email(self, email: str) -> User | None:
        return self.session.scalar(
            select(User).where(func.lower(User.email) == email.casefold())
        )

    def list_all(self) -> list[User]:
        return list(self.session.scalars(select(User).order_by(User.display_name)))

    def add(self, user: User) -> User:
        self.session.add(user)
        self.session.flush()
        return user


class SessionRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def add(self, browser_session: UserSession) -> UserSession:
        self.session.add(browser_session)
        self.session.flush()
        return browser_session

    def active_by_hash(self, token_hash: str, now: datetime) -> UserSession | None:
        return self.session.scalar(
            select(UserSession)
            .options(joinedload(UserSession.user))
            .where(UserSession.token_hash == token_hash, UserSession.expires_at > now)
        )

    def delete_by_hash(self, token_hash: str) -> None:
        browser_session = self.session.scalar(
            select(UserSession).where(UserSession.token_hash == token_hash)
        )
        if browser_session is not None:
            self.session.delete(browser_session)


class CustomerRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def add(self, customer: Customer) -> Customer:
        self.session.add(customer)
        self.session.flush()
        return customer

    def by_id(self, customer_id: uuid.UUID) -> Customer | None:
        return self.session.get(Customer, customer_id)

    def list(self, *, limit: int, offset: int) -> tuple[list[Customer], int]:
        items = list(
            self.session.scalars(
                select(Customer)
                .order_by(Customer.updated_at.desc())
                .limit(limit)
                .offset(offset)
            )
        )
        total = self.session.scalar(select(func.count()).select_from(Customer)) or 0
        return items, total


class RequestRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def add(self, request: ServiceRequest) -> ServiceRequest:
        self.session.add(request)
        self.session.flush()
        return self.by_id(request.id)  # type: ignore[return-value]

    def by_id(
        self, request_id: uuid.UUID, *, for_update: bool = False
    ) -> ServiceRequest | None:
        statement = select(ServiceRequest).where(ServiceRequest.id == request_id)
        if for_update:
            statement = statement.with_for_update()
        else:
            statement = statement.options(
                joinedload(ServiceRequest.customer),
                joinedload(ServiceRequest.assignee),
                joinedload(ServiceRequest.creator),
            )
        return self.session.scalar(statement)

    def list(
        self,
        *,
        status: RequestStatus | None,
        priority: RequestPriority | None,
        assignee_id: uuid.UUID | None,
        search: str | None,
        visible_to: uuid.UUID | None,
        limit: int,
        offset: int,
    ) -> tuple[list[ServiceRequest], int]:
        statement: Select[tuple[ServiceRequest]] = select(ServiceRequest).options(
            joinedload(ServiceRequest.customer), joinedload(ServiceRequest.assignee)
        )
        if status is not None:
            statement = statement.where(ServiceRequest.status == status)
        if priority is not None:
            statement = statement.where(ServiceRequest.priority == priority)
        if assignee_id is not None:
            statement = statement.where(ServiceRequest.assigned_to == assignee_id)
        if visible_to is not None:
            statement = statement.where(ServiceRequest.assigned_to == visible_to)
        if search:
            pattern = f"%{search.strip()}%"
            statement = statement.join(ServiceRequest.customer).where(
                or_(
                    ServiceRequest.title.ilike(pattern),
                    Customer.name.ilike(pattern),
                    Customer.phone.ilike(pattern),
                    func.cast(ServiceRequest.request_number, String).ilike(pattern),
                )
            )
        count_statement = select(func.count()).select_from(
            statement.order_by(None).subquery()
        )
        total = self.session.scalar(count_statement) or 0
        items = list(
            self.session.scalars(
                statement.order_by(ServiceRequest.updated_at.desc())
                .limit(limit)
                .offset(offset)
            ).unique()
        )
        return items, total


class ActivityRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def add_event(self, event: RequestEvent) -> RequestEvent:
        self.session.add(event)
        self.session.flush()
        return event

    def add_comment(self, comment: Comment) -> Comment:
        self.session.add(comment)
        self.session.flush()
        return comment

    def comments(self, request_id: uuid.UUID) -> list[Comment]:
        return list(
            self.session.scalars(
                select(Comment)
                .options(joinedload(Comment.author))
                .where(Comment.request_id == request_id)
                .order_by(Comment.created_at)
            )
        )

    def events(self, request_id: uuid.UUID) -> list[RequestEvent]:
        return list(
            self.session.scalars(
                select(RequestEvent)
                .options(joinedload(RequestEvent.actor))
                .where(RequestEvent.request_id == request_id)
                .order_by(RequestEvent.created_at)
            )
        )
