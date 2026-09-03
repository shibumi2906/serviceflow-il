# ServiceFlow IL

ServiceFlow IL is a phased learning project for building and operating a small
service-request application. The current repository contains **Phase 0 only**:
a minimal FastAPI application, a liveness endpoint, quality tooling, and project
decision records. It does not contain business features or AWS infrastructure.

## Requirements

- Python 3.12 (Python 3.13 is also supported by the Phase 0 tooling)
- `pip`

## Local setup

Create and activate a virtual environment, then install the locked dependencies:

```bash
python -m venv .venv
python -m pip install --upgrade pip
python -m pip install -r requirements.lock
```

On Windows PowerShell, activate the environment with:

```powershell
.\.venv\Scripts\Activate.ps1
```

On Linux or macOS, use:

```bash
source .venv/bin/activate
```

## Run the application

```bash
uvicorn serviceflow.main:app --app-dir src --reload
```

Then open `http://127.0.0.1:8000/health/live`. The endpoint returns HTTP 200 and:

```json
{"status":"ok"}
```

No environment variables are required in Phase 0. `.env.example` contains safe
placeholders for baseline settings only.

## Run all checks

```bash
python scripts/check.py
```

This single command checks formatting, lint, types, and unit tests. A `Makefile`
alias is also available as `make check` on systems with Make installed.

## Documentation

- [Contributing guide](CONTRIBUTING.md)
- [Architecture decisions](docs/adr/)
- [AWS cost safety](docs/aws-cost-safety.md)
- [Project specification](SPEC.md)

## Current limitations

Phase 0 intentionally has no database, authentication, business workflows,
HTML UI, container image, Terraform, or AWS resources. These belong to later
phases and must not be started before Phase 0 is accepted.
