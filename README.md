# ServiceFlow IL

ServiceFlow IL is a server-rendered service-request application for small Israeli
service organizations. **Phase 1** is a complete local application: staff manage
customers and requests, technicians work assigned requests, and every change is
recorded in PostgreSQL. No AWS resources or infrastructure are included yet.

## Implemented features

- Administrator, dispatcher, and technician authorization.
- Local email/password authentication with Argon2 hashes and revocable server-side
  sessions in HttpOnly, SameSite=Lax cookies.
- CSRF protection for every mutating HTML form.
- Customers, service requests, status workflow, priorities, assignment, comments,
  append-only history, filtering, search, pagination, and optimistic concurrency.
- Hebrew-first responsive server-rendered UI with `lang="he"` and `dir="rtl"`.
- Versioned REST API with consistent error responses and OpenAPI in local mode.
- PostgreSQL 16 through Docker Compose and schema-only Alembic migrations.

## Requirements

- Python 3.12 or 3.13
- `pip`
- Docker Desktop or another Docker Compose-compatible engine

## Local setup

Create and activate a virtual environment, then install the locked dependencies:

```bash
python -m venv .venv
python -m pip install --upgrade pip
python -m pip install -r requirements.lock
python -m pip install --no-deps -e .
```

On Windows PowerShell, activate the environment with:

```powershell
.\.venv\Scripts\Activate.ps1
```

On Linux or macOS, use:

```bash
source .venv/bin/activate
```

Copy the safe local template and replace the application key with a random value
of at least 32 characters:

```powershell
Copy-Item .env.example .env
```

Start PostgreSQL and apply the migration chain:

```bash
docker compose up --detach --wait db
python -m alembic upgrade head
```

Create the first administrator. The password is prompted and is not passed on the
command line:

```bash
python -m serviceflow.cli create-admin --email admin@example.com --display-name "Local Admin"
```

Optional local demo data can then be created with:

```bash
python -m serviceflow.cli seed-demo --admin-email admin@example.com
```

## Run the application

```bash
uvicorn serviceflow.main:app --app-dir src --reload
```

Open `http://127.0.0.1:8000/login`. Liveness and dependency readiness are available
at `/health/live` and `/health/ready`.

```json
{"status":"ok"}
```

## Run all checks

```bash
python scripts/check.py
```

This single command checks formatting, lint, strict types and unit tests; starts
the local PostgreSQL service; migrates a separate disposable test database; and
runs integration, API, authorization, session, CSRF, workflow, and concurrency
tests. A `Makefile` alias is also available as `make check`.

## REST API

Local OpenAPI documentation is available at `/docs`. The Phase 1 API includes
authentication, customers, requests, comments, and request history under
`/api/v1`. Responses use server pagination. Errors contain `code`, `message`,
`details`, and `request_id`; the same request ID is returned in the
`X-Request-ID` header.

## Documentation

- [Contributing guide](CONTRIBUTING.md)
- [Architecture decisions](docs/adr/)
- [AWS cost safety](docs/aws-cost-safety.md)
- [Phase 1 architecture](docs/architecture/phase-1.md)
- [Local development runbook](docs/runbooks/local-development.md)
- [Project specification](SPEC.md)

## Current limitations

Phase 1 is local-only. Attachments, S3, a production application image, ECR, ECS,
ALB, RDS, Secrets Manager, Terraform, and deployment automation belong to later
phases and are intentionally absent. The current UI is functional and responsive,
but does not provide a separate SPA or real-time updates.
