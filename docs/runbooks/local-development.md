# Local development runbook

## Expected state

- Python 3.12 or 3.13 is active in `.venv`.
- `.env` exists and contains local-only values based on `.env.example`.
- Docker Desktop is running and `docker info` succeeds.
- `docker compose ps` reports `db` as healthy.

## Start from a clean checkout

1. Create `.venv` with the installed compatible Python and activate it.
2. Run `python -m pip install -r requirements.lock`, then install the local project
   without re-resolving dependencies: `python -m pip install --no-deps -e .`.
3. Copy `.env.example` to `.env` and replace `APP_SECRET_KEY` with a random local
   value of at least 32 characters.
4. Run `docker compose up --detach --wait db`.
5. Run `python -m alembic upgrade head`.
6. Run `python -m serviceflow.cli create-admin --email you@example.com
   --display-name "Local Admin"`; enter a password when prompted.
7. Optionally run `python -m serviceflow.cli seed-demo --admin-email
   you@example.com`.
8. Start the app with `uvicorn serviceflow.main:app --app-dir src --reload`.

Expected results: `/health/live` and `/health/ready` both return HTTP 200, `/login`
renders a Hebrew RTL page, and the administrator can sign in.

## Run the complete gate

Run `python scripts/check.py`. It checks formatting, lint, strict types, unit tests,
starts the PostgreSQL Compose service when not in CI, creates a disposable
`serviceflow_test` database, applies Alembic from an empty schema, and runs the
integration/API/web tests. Test cleanup drops only the database whose name ends in
`_test`.

## Diagnose failures

1. **`docker info` fails:** start Docker Desktop. If Docker itself reports a stale
   socket or WSL failure, repair Docker before changing application code.
2. **DB container is unhealthy:** run `docker compose ps` and `docker compose logs
   db`. Expected log: `database system is ready to accept connections`.
3. **Migration fails:** verify `DATABASE_URL`, then run `python -m alembic current`
   and `python -m alembic heads`. They should both identify `20260903_0001`.
4. **Readiness is 503:** confirm the container is healthy and the database name is
   `serviceflow_dev`; liveness should remain 200 because it does not query the DB.
5. **Login fails:** verify the user was created by the CLI and remains active. No
   public registration endpoint exists.

## Stop local services

Run `docker compose down`. This stops the container and network but preserves the
named development volume. Deleting that volume destroys local data and is not part
of the normal shutdown procedure.
