"""Application use cases and transaction boundaries."""

from __future__ import annotations

import re
import uuid
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from email_validator import EmailNotValidError, validate_email
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from serviceflow.domain.enums import EventType, RequestPriority, RequestStatus, Role
from serviceflow.domain.errors import (
    AuthenticationError,
    ConflictError,
    ForbiddenError,
    NotFoundError,
    ValidationError,
)
from serviceflow.domain.workflow import validate_status_transition
from serviceflow.infrastructure.models import (
    Comment,
    Customer,
    RequestEvent,
    ServiceRequest,
    User,
    UserSession,
)
from serviceflow.infrastructure.repositories import (
    ActivityRepository,
    CustomerRepository,
    RequestRepository,
    SessionRepository,
    UserRepository,
)
from serviceflow.infrastructure.security import (
    hash_password,
    hash_session_token,
    new_csrf_token,
    new_session_token,
    verify_password,
)


@dataclass(frozen=True)
class AuthenticatedSession:
    user: User
    browser_session: UserSession


PHONE_PATTERN = re.compile(r"^[0-9+()\-\s]{7,40}$")


def _email(value: str) -> str:
    try:
        return validate_email(value.strip(), check_deliverability=False).normalized
    except EmailNotValidError as exc:
        raise ValidationError("Email address is invalid") from exc


def _phone(value: str | None) -> str | None:
    if not value:
        return None
    normalized = value.strip()
    if not PHONE_PATTERN.fullmatch(normalized):
        raise ValidationError("Phone number is invalid")
    return normalized


@dataclass(frozen=True)
class RequestChanges:
    version: int
    title: str | None = None
    description: str | None = None
    status: RequestStatus | None = None
    priority: RequestPriority | None = None
    assigned_to: uuid.UUID | None = None
    assignee_was_set: bool = False


class AuthService:
    def __init__(self, session: Session, *, ttl_hours: int = 8) -> None:
        self.session = session
        self.users = UserRepository(session)
        self.sessions = SessionRepository(session)
        self.ttl_hours = ttl_hours

    def login(self, email: str, password: str) -> tuple[User, str]:
        user = self.users.by_email(email.strip())
        if (
            user is None
            or not user.is_active
            or not verify_password(password, user.password_hash)
        ):
            raise AuthenticationError("Invalid email or password")
        token = new_session_token()
        self.sessions.add(
            UserSession(
                user_id=user.id,
                token_hash=hash_session_token(token),
                csrf_token=new_csrf_token(),
                expires_at=datetime.now(UTC) + timedelta(hours=self.ttl_hours),
            )
        )
        self.session.commit()
        return user, token

    def resolve(self, token: str | None) -> AuthenticatedSession:
        if not token:
            raise AuthenticationError("Authentication is required")
        browser_session = self.sessions.active_by_hash(
            hash_session_token(token), datetime.now(UTC)
        )
        if browser_session is None or not browser_session.user.is_active:
            raise AuthenticationError("Session is invalid or expired")
        return AuthenticatedSession(browser_session.user, browser_session)

    def logout(self, token: str | None) -> None:
        if token:
            self.sessions.delete_by_hash(hash_session_token(token))
            self.session.commit()


class StaffService:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.users = UserRepository(session)

    @staticmethod
    def _require_admin(actor: User) -> None:
        if actor.role != Role.ADMINISTRATOR:
            raise ForbiddenError("Administrator access is required")

    def create(
        self,
        actor: User,
        *,
        email: str,
        password: str,
        display_name: str,
        role: Role,
    ) -> User:
        self._require_admin(actor)
        if len(password) < 12:
            raise ValidationError("Password must contain at least 12 characters")
        user = User(
            email=_email(email).casefold(),
            password_hash=hash_password(password),
            display_name=display_name.strip(),
            role=role,
            is_active=True,
        )
        self.users.add(user)
        try:
            self.session.commit()
        except IntegrityError as exc:
            self.session.rollback()
            raise ConflictError("A user with this email already exists") from exc
        return user

    def set_active(self, actor: User, user_id: uuid.UUID, *, is_active: bool) -> User:
        self._require_admin(actor)
        user = self.users.by_id(user_id)
        if user is None:
            raise NotFoundError("User was not found")
        if actor.id == user.id and not is_active:
            raise ValidationError(
                "An administrator cannot deactivate the current account"
            )
        user.is_active = is_active
        self.session.commit()
        return user

    def list_all(self, actor: User) -> list[User]:
        self._require_admin(actor)
        return self.users.list_all()

    def list_active(self, actor: User) -> list[User]:
        del actor
        return [user for user in self.users.list_all() if user.is_active]


class CustomerService:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.customers = CustomerRepository(session)

    @staticmethod
    def _require_editor(actor: User) -> None:
        if actor.role not in {Role.ADMINISTRATOR, Role.DISPATCHER}:
            raise ForbiddenError(
                "Only administrators and dispatchers can modify customers"
            )

    def create(
        self,
        actor: User,
        *,
        name: str,
        phone: str | None,
        email: str | None,
        address: str | None,
        note: str | None,
    ) -> Customer:
        self._require_editor(actor)
        normalized_phone = _phone(phone)
        normalized_email = _email(email).casefold() if email else None
        if normalized_phone is None and normalized_email is None:
            raise ValidationError("At least one customer contact method is required")
        customer = Customer(
            name=name.strip(),
            phone=normalized_phone,
            email=normalized_email,
            address=address or None,
            note=note or None,
        )
        self.customers.add(customer)
        self.session.commit()
        return customer

    def list(
        self, actor: User, *, limit: int, offset: int
    ) -> tuple[list[Customer], int]:
        del actor
        return self.customers.list(limit=limit, offset=offset)

    def get(self, actor: User, customer_id: uuid.UUID) -> Customer:
        del actor
        customer = self.customers.by_id(customer_id)
        if customer is None:
            raise NotFoundError("Customer was not found")
        return customer

    def update(
        self,
        actor: User,
        customer_id: uuid.UUID,
        *,
        changes: dict[str, str | None],
    ) -> Customer:
        self._require_editor(actor)
        customer = self.get(actor, customer_id)
        for field, value in changes.items():
            if field == "name" and value is not None:
                value = value.strip()
            if field == "email" and value:
                value = _email(value).casefold()
            if field == "phone":
                value = _phone(value)
            setattr(customer, field, value or None)
        if customer.phone is None and customer.email is None:
            raise ValidationError("At least one customer contact method is required")
        self.session.commit()
        return customer


class RequestService:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.requests = RequestRepository(session)
        self.customers = CustomerRepository(session)
        self.users = UserRepository(session)
        self.activity = ActivityRepository(session)

    @staticmethod
    def _require_manager(actor: User) -> None:
        if actor.role not in {Role.ADMINISTRATOR, Role.DISPATCHER}:
            raise ForbiddenError(
                "Only administrators and dispatchers can perform this action"
            )

    @staticmethod
    def _authorize_view(actor: User, request: ServiceRequest) -> None:
        if actor.role == Role.TECHNICIAN and request.assigned_to != actor.id:
            raise ForbiddenError("Technicians can only view assigned requests")

    def create(
        self,
        actor: User,
        *,
        customer_id: uuid.UUID,
        title: str,
        description: str,
        priority: RequestPriority,
        assigned_to: uuid.UUID | None,
    ) -> ServiceRequest:
        self._require_manager(actor)
        if self.customers.by_id(customer_id) is None:
            raise NotFoundError("Customer was not found")
        if assigned_to is not None:
            assignee = self.users.by_id(assigned_to)
            if assignee is None or not assignee.is_active:
                raise ValidationError("Assignee must be an active user")
        request = ServiceRequest(
            customer_id=customer_id,
            title=title.strip(),
            description=description.strip(),
            priority=priority,
            assigned_to=assigned_to,
            created_by=actor.id,
            status=RequestStatus.ASSIGNED if assigned_to else RequestStatus.NEW,
        )
        self.requests.add(request)
        self.activity.add_event(
            RequestEvent(
                request_id=request.id,
                actor_id=actor.id,
                event_type=EventType.REQUEST_CREATED,
                payload={
                    "status": request.status.value,
                    "priority": request.priority.value,
                    "assigned_to": str(assigned_to) if assigned_to else None,
                },
            )
        )
        self.session.commit()
        return request

    def list(
        self,
        actor: User,
        *,
        status: RequestStatus | None = None,
        priority: RequestPriority | None = None,
        assignee_id: uuid.UUID | None = None,
        search: str | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[list[ServiceRequest], int]:
        visible_to = actor.id if actor.role == Role.TECHNICIAN else None
        return self.requests.list(
            status=status,
            priority=priority,
            assignee_id=assignee_id,
            search=search,
            visible_to=visible_to,
            limit=limit,
            offset=offset,
        )

    def get(self, actor: User, request_id: uuid.UUID) -> ServiceRequest:
        request = self.requests.by_id(request_id)
        if request is None:
            raise NotFoundError("Service request was not found")
        self._authorize_view(actor, request)
        return request

    def update(
        self, actor: User, request_id: uuid.UUID, changes: RequestChanges
    ) -> ServiceRequest:
        request = self.requests.by_id(request_id, for_update=True)
        if request is None:
            raise NotFoundError("Service request was not found")
        self._authorize_view(actor, request)
        if request.version != changes.version:
            raise ConflictError(
                "The request was modified by another user",
                {
                    "expected_version": changes.version,
                    "current_version": request.version,
                },
            )
        if actor.role == Role.TECHNICIAN and any(
            value is not None
            for value in (changes.title, changes.description, changes.priority)
        ):
            raise ForbiddenError("Technicians can only change request status")
        if actor.role == Role.TECHNICIAN and changes.assignee_was_set:
            raise ForbiddenError("Technicians cannot assign requests")

        if changes.assignee_was_set:
            self._require_manager(actor)
            if changes.assigned_to is not None:
                assignee = self.users.by_id(changes.assigned_to)
                if assignee is None or not assignee.is_active:
                    raise ValidationError("Assignee must be an active user")
            old_assignee = request.assigned_to
            request.assigned_to = changes.assigned_to
            if old_assignee != request.assigned_to:
                self._event(
                    request,
                    actor,
                    EventType.ASSIGNEE_CHANGED,
                    old=str(old_assignee) if old_assignee else None,
                    new=str(request.assigned_to) if request.assigned_to else None,
                )

        target_status = changes.status
        if (
            target_status is None
            and changes.assignee_was_set
            and request.status == RequestStatus.NEW
            and request.assigned_to is not None
        ):
            target_status = RequestStatus.ASSIGNED
        if (
            target_status is None
            and changes.assignee_was_set
            and request.status == RequestStatus.ASSIGNED
            and request.assigned_to is None
        ):
            target_status = RequestStatus.NEW
        if target_status is not None and target_status != request.status:
            validate_status_transition(
                request.status,
                target_status,
                actor.role,
                has_assignee=request.assigned_to is not None,
            )
            old_status = request.status
            request.status = target_status
            request.completed_at = (
                datetime.now(UTC) if target_status == RequestStatus.COMPLETED else None
            )
            self._event(
                request,
                actor,
                EventType.STATUS_CHANGED,
                old=old_status.value,
                new=target_status.value,
            )

        if changes.priority is not None and changes.priority != request.priority:
            self._require_manager(actor)
            old_priority = request.priority
            request.priority = changes.priority
            self._event(
                request,
                actor,
                EventType.PRIORITY_CHANGED,
                old=old_priority.value,
                new=request.priority.value,
            )
        if changes.title is not None:
            self._require_manager(actor)
            request.title = changes.title.strip()
        if changes.description is not None:
            self._require_manager(actor)
            request.description = changes.description.strip()
        request.version += 1
        self.session.commit()
        return request

    def add_comment(self, actor: User, request_id: uuid.UUID, *, body: str) -> Comment:
        request = self.get(actor, request_id)
        body = body.strip()
        if not body:
            raise ValidationError("Comment body cannot be empty")
        comment = self.activity.add_comment(
            Comment(request_id=request.id, author_id=actor.id, body=body)
        )
        self.activity.add_event(
            RequestEvent(
                request_id=request.id,
                actor_id=actor.id,
                event_type=EventType.COMMENT_ADDED,
                payload={"comment_id": str(comment.id)},
            )
        )
        self.session.commit()
        return comment

    def comments(self, actor: User, request_id: uuid.UUID) -> Sequence[Comment]:
        self.get(actor, request_id)
        return self.activity.comments(request_id)

    def history(self, actor: User, request_id: uuid.UUID) -> Sequence[RequestEvent]:
        self.get(actor, request_id)
        return self.activity.events(request_id)

    def _event(
        self,
        request: ServiceRequest,
        actor: User,
        event_type: EventType,
        *,
        old: str | None,
        new: str | None,
    ) -> None:
        self.activity.add_event(
            RequestEvent(
                request_id=request.id,
                actor_id=actor.id,
                event_type=event_type,
                payload={"old": old, "new": new},
            )
        )


def bootstrap_administrator(
    session: Session, *, email: str, password: str, display_name: str
) -> User:
    """Create the first administrator; public registration is intentionally absent."""
    if len(password) < 12:
        raise ValidationError("Password must contain at least 12 characters")
    users = UserRepository(session)
    if users.list_all():
        raise ConflictError(
            "The first administrator can only be created in an empty user table"
        )
    user = users.add(
        User(
            email=_email(email).casefold(),
            password_hash=hash_password(password),
            display_name=display_name.strip(),
            role=Role.ADMINISTRATOR,
            is_active=True,
        )
    )
    session.commit()
    return user
