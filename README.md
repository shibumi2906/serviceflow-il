# ServiceFlow IL

ServiceFlow IL is a Hebrew-first service-request application for small service
organizations in Israel. It combines a server-rendered FastAPI application,
PostgreSQL, a versioned REST API, and a deliberately small AWS Fargate smoke
deployment used to validate the container delivery path.

The project currently covers Phases 0–2 of [SPEC.md](SPEC.md). Phase 1 provides
the complete local application. Phase 2 adds a production-style container and a
strictly scoped, approval-gated AWS smoke environment. The smoke environment is
not a production deployment and does not expose business functionality.

## What is included

- Local email/password authentication with Argon2 password hashes.
- Revocable server-side sessions in HttpOnly, SameSite=Lax cookies.
- CSRF protection for all mutating HTML forms.
- Administrator, dispatcher, and technician roles and permissions.
- Customers, service requests, priorities, assignment, comments, filtering,
  search, pagination, append-only history, and optimistic concurrency control.
- Hebrew-first responsive pages with `lang="he"` and `dir="rtl"`.
- A versioned REST API with consistent errors and local OpenAPI documentation.
- PostgreSQL 16 through Docker Compose and schema-only Alembic migrations.
- A multi-stage Python 3.12 image running as non-root UID/GID `10001`.
- A restricted smoke mode with health endpoints only and no database dependency.
- Terraform for ECR, ECS, narrowly scoped IAM roles, and seven-day CloudWatch
  logs, with an optional one-task Fargate smoke service.

## Architecture and runtime modes

```text
Local full mode                         Phase 2 smoke mode

Browser / API client                   ECS Fargate (one temporary task)
        |                                         |
        v                                         v
FastAPI + Jinja2  --->  PostgreSQL 16   FastAPI health endpoints only
                                               |
                                               v
                                        CloudWatch Logs
```

`APP_MODE=full` enables the UI, API, sessions, and PostgreSQL-backed application.
`APP_MODE=smoke` exposes only `/health/live`, `/health/ready`, and static files;
it needs neither a database nor an application secret and cannot perform business
writes.

## Requirements

- Python 3.12 or 3.13
- `pip`
- Docker Desktop, or another Docker Engine with Docker Compose support
- GNU Make is optional; every Make target has an equivalent Python command

AWS CLI credentials and Terraform are not required for normal local development.
Terraform is executed through a pinned Docker image when infrastructure checks or
an explicitly approved AWS operation are needed.

## Quick start

Create and activate a virtual environment:

```powershell
# Windows PowerShell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

```bash
# Linux or macOS
python -m venv .venv
source .venv/bin/activate
```

Install the locked development dependencies and the project itself:

```bash
python -m pip install --upgrade pip
python -m pip install -r requirements.lock
python -m pip install --no-deps -e .
```

Create the local configuration file:

```powershell
# Windows PowerShell
Copy-Item .env.example .env
```

```bash
# Linux or macOS
cp .env.example .env
```

Replace `APP_SECRET_KEY` in `.env` with a random value of at least 32 characters.
For example, generate one locally with:

```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

Start PostgreSQL, apply all migrations, and run the application:

```bash
docker compose up --detach --wait db
python -m alembic upgrade head
uvicorn serviceflow.main:app --app-dir src --reload
```

Open <http://127.0.0.1:8000/login>. Local OpenAPI documentation is available at
<http://127.0.0.1:8000/docs>.

## Initial administrator and demo data

There is no public registration route. Create the first administrator from the
command line; the password is read from an interactive prompt and is never passed
as a command-line argument:

```bash
python -m serviceflow.cli create-admin \
  --email admin@example.com \
  --display-name "Local Admin"
```

After creating the administrator, optional Hebrew demo data can be added with:

```bash
python -m serviceflow.cli seed-demo --admin-email admin@example.com
```

## Configuration

The application reads environment variables and an optional local `.env` file.
The committed [.env.example](.env.example) is safe to copy, but its secret value
must be replaced outside throwaway local development.

| Variable | Purpose | Local example |
| --- | --- | --- |
| `APP_MODE` | `full` application or restricted `smoke` mode | `full` |
| `APP_ENV` | `local`, `test`, or `production` validation rules | `local` |
| `APP_DEBUG` | Enable framework debug behavior | `true` |
| `APP_BASE_URL` | Public base URL used by the application | `http://localhost:8000` |
| `APP_SECRET_KEY` | Session-signing secret; at least 32 characters in full mode | replace locally |
| `DATABASE_URL` | SQLAlchemy PostgreSQL connection URL for full mode | see `.env.example` |
| `SESSION_COOKIE_SECURE` | Require HTTPS for the session cookie | `false` locally |
| `LOG_LEVEL` | Application log level | `INFO` |
| `SESSION_TTL_HOURS` | Session lifetime from 1 to 168 hours | `8` |

Production full mode rejects debug mode, insecure session cookies, and the
placeholder secret.

## Health endpoints

- `GET /health/live` confirms that the process is running.
- `GET /health/ready` checks PostgreSQL in full mode and returns HTTP 503 when the
  database is unavailable.
- In smoke mode, readiness returns `{"status":"ok","mode":"smoke"}` because
  that mode has no external critical dependency.

## Quality checks

Run the complete local quality gate with one command:

```bash
python scripts/check.py
```

Or, when Make is installed:

```bash
make check
```

The gate runs Ruff formatting and linting, strict mypy, dependency audits, unit
tests, PostgreSQL integration/API/web tests, a hardened container smoke test,
container vulnerability scanning, and Terraform formatting, validation, linting,
and security checks. Docker must be running. The integration suite uses a separate
disposable test database and does not modify the development database.

Useful focused commands are:

```bash
python -m pytest tests/unit
python -m pytest tests/integration
python -m ruff format --check .
python -m ruff check .
python -m mypy
python scripts/container_smoke.py
python scripts/image_scan.py
python scripts/infra_check.py
```

CI runs the same complete gate on Python 3.12 with PostgreSQL 16.

## Container smoke image

The normal local container check builds `serviceflow-il:phase2-local`, starts it
on a random loopback port, and verifies:

- HTTP 200 from liveness and smoke readiness;
- HTTP 404 from a business API route;
- runtime UID `10001`;
- a read-only root filesystem;
- all Linux capabilities dropped; and
- `no-new-privileges` enabled.

Run it with:

```bash
python scripts/container_smoke.py
```

The container defaults to `APP_MODE=smoke`. It contains only runtime dependencies
from `requirements.runtime.lock`; development and scanning tools are not shipped
in the final image.

## Phase 2 AWS scope

The Terraform root is [infra/terraform/environments/dev](infra/terraform/environments/dev).
With `deploy_service=false`, it manages only the bootstrap resources:

- one immutable-tag ECR repository;
- one ECS cluster;
- one CloudWatch log group with seven-day retention; and
- one ECS execution role, one task role, and the execution role's narrow inline
  pull-and-log policy.

An independently reviewed plan with `deploy_service=true` can additionally create
one temporary security group, task definition, and one-task Fargate service in the
account's default VPC. The task has no inbound security-group rules and runs only
the restricted smoke mode.

This phase intentionally contains no ALB, RDS, S3, Secrets Manager, NAT Gateway,
custom VPC, or long-running production environment. Plans, applies, image pushes,
deployments, and destroys require explicit approval. Images use immutable full Git
SHA tags; `latest` is not used. See the
[Phase 2 runbook](docs/runbooks/phase-2-ecr-ecs-smoke.md) for the controlled
bootstrap, deployment, verification, and cleanup sequence.

Terraform uses local state in this phase. Never commit state files, saved plans,
credentials, generated secrets, or the `.terraform` directory.

## Common commands

| Task | Command |
| --- | --- |
| Start PostgreSQL | `make db-up` or `docker compose up --detach --wait db` |
| Stop local services | `make db-down` or `docker compose down` |
| Apply migrations | `make migrate` or `python -m alembic upgrade head` |
| Run the application | `make run` or `uvicorn serviceflow.main:app --app-dir src --reload` |
| Run the full quality gate | `make check` or `python scripts/check.py` |
| Build and smoke-test the image | `make image` or `python scripts/container_smoke.py` |
| Scan the local image | `make image-scan` or `python scripts/image_scan.py` |
| Validate Phase 2 infrastructure | `make infra-check` or `python scripts/infra_check.py` |

`docker compose down` keeps the named PostgreSQL volume. Removing that volume
deletes local database data and should be done only deliberately.

## Repository layout

```text
src/serviceflow/                  application, domain, infrastructure, and UI
tests/unit/                       isolated unit tests
tests/integration/                PostgreSQL, API, authentication, and web tests
alembic/                          versioned database migrations
infra/terraform/environments/dev Phase 2 Terraform root
scripts/                          quality, container, scan, and Terraform helpers
docs/adr/                         architecture decision records
docs/architecture/                phase architecture notes
docs/runbooks/                    local and AWS operating procedures
```

## Documentation

- [Project specification](SPEC.md)
- [Contributing guide](CONTRIBUTING.md)
- [Architecture decision records](docs/adr/)
- [Phase 1 architecture](docs/architecture/phase-1.md)
- [Phase 2 architecture](docs/architecture/phase-2.md)
- [Local development runbook](docs/runbooks/local-development.md)
- [Phase 2 ECR/ECS smoke runbook](docs/runbooks/phase-2-ecr-ecs-smoke.md)
- [AWS cost and safety rules](docs/aws-cost-safety.md)

## Current limitations

The Phase 2 cloud target is an operational smoke test, not a user-facing service.
It has no public route, database, persistence, or business API. Production
networking, managed PostgreSQL, attachments, secret storage, CI/CD identity, and
other Phase 3+ capabilities are intentionally deferred.
