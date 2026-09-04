# Phase 1 architecture

```text
Browser / API client
        |
        v
FastAPI presentation (JSON API + Hebrew Jinja2 pages)
        |
        v
Application services (authorization + transactions)
        |
        v
Domain workflow rules       SQLAlchemy repositories
                                      |
                                      v
                         PostgreSQL 16 in Docker Compose
```

The browser stores only an opaque session token in an HttpOnly, SameSite=Lax
cookie. Its SHA-256 digest and a CSRF token are stored server-side. Every request
resolves the current active user, so deactivation invalidates continued access.
Schema changes are applied exclusively through Alembic; runtime `create_all()` is
not used.
