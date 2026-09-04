"""Separated API input and output schemas."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from serviceflow.domain.enums import EventType, RequestPriority, RequestStatus, Role


class LoginInput(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=1024)


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: EmailStr
    display_name: str
    role: Role
    is_active: bool


class CustomerCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    phone: str | None = Field(default=None, max_length=40)
    email: EmailStr | None = None
    address: str | None = Field(default=None, max_length=2000)
    note: str | None = Field(default=None, max_length=5000)


class CustomerUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    phone: str | None = Field(default=None, max_length=40)
    email: EmailStr | None = None
    address: str | None = Field(default=None, max_length=2000)
    note: str | None = Field(default=None, max_length=5000)


class CustomerRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    phone: str | None
    email: EmailStr | None
    address: str | None
    note: str | None
    created_at: datetime
    updated_at: datetime


class CustomerPage(BaseModel):
    items: list[CustomerRead]
    total: int
    limit: int
    offset: int


class RequestCreate(BaseModel):
    customer_id: uuid.UUID
    title: str = Field(min_length=1, max_length=200)
    description: str = Field(min_length=1, max_length=20_000)
    priority: RequestPriority = RequestPriority.NORMAL
    assigned_to: uuid.UUID | None = None


class RequestUpdate(BaseModel):
    version: int = Field(ge=1)
    title: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = Field(default=None, min_length=1, max_length=20_000)
    status: RequestStatus | None = None
    priority: RequestPriority | None = None
    assigned_to: uuid.UUID | None = None


class RequestRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    request_number: int
    customer_id: uuid.UUID
    title: str
    description: str
    status: RequestStatus
    priority: RequestPriority
    assigned_to: uuid.UUID | None
    created_by: uuid.UUID
    version: int
    created_at: datetime
    updated_at: datetime
    completed_at: datetime | None


class RequestPage(BaseModel):
    items: list[RequestRead]
    total: int
    limit: int
    offset: int


class CommentCreate(BaseModel):
    body: str = Field(min_length=1, max_length=10_000)


class CommentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    request_id: uuid.UUID
    author_id: uuid.UUID
    body: str
    created_at: datetime


class EventRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    request_id: uuid.UUID
    actor_id: uuid.UUID | None
    event_type: EventType
    payload: dict[str, Any]
    created_at: datetime


class ErrorBody(BaseModel):
    code: str
    message: str
    details: Any
    request_id: str
