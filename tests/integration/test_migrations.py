"""PostgreSQL migration smoke tests."""

import pytest
from sqlalchemy import Engine, inspect, text


@pytest.mark.integration
def test_phase1_schema_is_created_from_empty_database(migrated_engine: Engine) -> None:
    tables = set(inspect(migrated_engine).get_table_names())

    assert {
        "alembic_version",
        "users",
        "user_sessions",
        "customers",
        "service_requests",
        "comments",
        "request_events",
    } <= tables


@pytest.mark.integration
def test_request_event_history_is_append_only(migrated_engine: Engine) -> None:
    with migrated_engine.connect() as connection:
        trigger_count = connection.scalar(
            text(
                "SELECT count(*) FROM pg_trigger "
                "WHERE tgname = 'request_events_append_only'"
            )
        )

    assert trigger_count == 1
