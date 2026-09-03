# ADR-003: Adopt AWS capabilities in explicit phases

- Status: Accepted
- Date: 2026-09-03

## Context

Introducing networking, containers, databases, secrets, storage, and delivery at
once makes failures expensive and difficult to diagnose. Several intended AWS
resources also have continuous or hourly charges.

## Decision

Add AWS capabilities only in the sequence defined by `SPEC.md`. Phase 0 creates no
AWS resources and includes no Terraform. Every later AWS phase requires read-only
inspection and a reviewed plan before any explicitly authorized mutation. The
project uses one `dev` environment until the user requests another.

## Consequences

Each phase has a small diagnostic surface and an auditable commit. Temporary
limitations are documented honestly. The system is not described as production
ready merely because an intermediate deployment runs.

## Alternatives considered

- Provision the final architecture immediately: rejected because it combines too
  many failure domains and cost sources.
- Configure resources manually in the console: rejected for persistent resources
  because it is not reproducible or reviewable.
