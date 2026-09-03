# Contributing

## Scope discipline

Read `SPEC.md` before making changes. Implement only the explicitly requested
phase, preserve completed phases, and record significant architectural changes
in an ADR before implementation.

Never commit credentials, local `.env` files, personal data, or generated cloud
secrets. Do not create, update, or delete AWS resources without the explicit
approval required by the specification.

## Development workflow

1. Use Python 3.12 and create a local virtual environment.
2. Install exactly the versions in `requirements.lock`.
3. Keep route handlers and modules within the architecture boundaries recorded
   in ADR-001.
4. Add or update tests with each behavior change.
5. Run `python scripts/check.py` before committing.
6. Keep one reviewed commit per completed phase.

## Dependency changes

Dependency management uses `pip-tools`; see ADR-004. Change dependency declarations
in `pyproject.toml`, then regenerate the lock file with:

```bash
python -m piptools compile --extra dev --output-file requirements.lock pyproject.toml
```

Install the regenerated lock and run the complete quality gate before committing.

## Commit messages

Use a concise imperative summary. Phase completion commits should identify the
phase, for example: `Establish Phase 0 project baseline`.
