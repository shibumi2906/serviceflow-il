"""Tests for the non-public first-administrator bootstrap use case."""

import pytest
from sqlalchemy.orm import Session

from serviceflow.application.services import bootstrap_administrator
from serviceflow.domain.enums import Role
from serviceflow.domain.errors import ConflictError
from serviceflow.infrastructure.security import verify_password


@pytest.mark.integration
def test_first_administrator_is_created_once_with_hashed_password(
    db_session: Session,
) -> None:
    password = "correct-horse-battery-staple"
    administrator = bootstrap_administrator(
        db_session,
        email="FIRST.ADMIN@example.com",
        password=password,
        display_name="First Administrator",
    )

    assert administrator.email == "first.admin@example.com"
    assert administrator.role == Role.ADMINISTRATOR
    assert administrator.password_hash != password
    assert verify_password(password, administrator.password_hash)
    with pytest.raises(ConflictError):
        bootstrap_administrator(
            db_session,
            email="second.admin@example.com",
            password=password,
            display_name="Second Administrator",
        )
