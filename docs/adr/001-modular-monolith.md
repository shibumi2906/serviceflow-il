# ADR-001: Use a modular monolith

- Status: Accepted
- Date: 2026-09-03

## Context

ServiceFlow IL must demonstrate clear application boundaries while remaining
small enough that AWS deployment and operations stay visible. Independent
services would add networking, deployment, data-consistency, and observability
work before the domain requires those trade-offs.

## Decision

Build one deployable FastAPI application as a modular monolith. Code is divided
into presentation, application, domain, and infrastructure layers. The domain
does not import FastAPI, SQLAlchemy, or AWS SDKs. Application use cases coordinate
authorization and transaction boundaries, and presentation adapters remain thin.

## Consequences

The project has one deployment unit and can use in-process calls between modules.
Layer boundaries still make domain rules independently testable and allow external
adapters to be replaced. If operational or scaling evidence later supports a
service split, that change requires a new ADR rather than speculative services.

## Alternatives considered

- Microservices: rejected because their operational cost and complexity do not
  serve the first version.
- An unlayered FastAPI application: rejected because it would couple business
  rules to HTTP and persistence details.
