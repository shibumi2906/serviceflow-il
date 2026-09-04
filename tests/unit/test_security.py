"""Unit tests for password and session-token handling."""

from serviceflow.infrastructure.security import (
    hash_password,
    hash_session_token,
    new_session_token,
    verify_password,
)


def test_password_hash_does_not_store_plaintext() -> None:
    password = "correct-horse-battery-staple"
    password_hash = hash_password(password)

    assert password not in password_hash
    assert verify_password(password, password_hash)
    assert not verify_password("wrong-password", password_hash)


def test_session_token_is_only_persisted_as_hash() -> None:
    token = new_session_token()
    digest = hash_session_token(token)

    assert token != digest
    assert len(digest) == 64
