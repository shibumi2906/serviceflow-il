# ADR-004: Manage Python dependencies with pip-tools

- Status: Accepted
- Date: 2026-09-03

## Context

The specification requires one package-management workflow and a committed lock
file. The project should remain usable with the standard Python toolchain.

## Decision

Declare direct runtime and development dependencies in `pyproject.toml`. Use
`pip-tools` to resolve them into `requirements.lock` for development and CI and
`requirements.runtime.lock` for the smaller production image. Install from those
locks with `pip`. Application packaging uses the standard PEP 517 build interface
through setuptools.

## Consequences

CI and local development install the same pinned development graph; the image uses
the matching pinned runtime subset without test tooling. A dependency change
requires regenerating and reviewing both lock files. Developers need no
project-specific package manager beyond the locked Python tools.

## Alternatives considered

- Unpinned `pip install`: rejected because resolution could change between runs.
- Poetry or uv: both are viable, but each adds a separate executable that is not
  available in every baseline Python environment.
