"""Password and opaque session-token helpers."""

from __future__ import annotations

import hashlib
import secrets

from pwdlib import PasswordHash

PASSWORD_HASH = PasswordHash.recommended()


def hash_password(password: str) -> str:
    """Hash a password using the current recommended Argon2 configuration."""
    return PASSWORD_HASH.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    """Verify a password without exposing the stored hash."""
    return PASSWORD_HASH.verify(password, password_hash)


def new_session_token() -> str:
    """Create an opaque token with sufficient entropy for a browser session."""
    return secrets.token_urlsafe(32)


def hash_session_token(token: str) -> str:
    """Hash a session token before persistence."""
    return hashlib.sha256(token.encode()).hexdigest()


def new_csrf_token() -> str:
    """Create a per-session CSRF token."""
    return secrets.token_urlsafe(32)
