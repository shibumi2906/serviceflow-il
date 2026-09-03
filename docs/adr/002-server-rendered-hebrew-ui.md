# ADR-002: Use a server-rendered Hebrew-first UI

- Status: Accepted
- Date: 2026-09-03

## Context

The primary users are in Israel, and the project is intended to teach backend and
AWS operations rather than introduce a separate frontend deployment pipeline.

## Decision

Render HTML on the server with FastAPI and Jinja2. Pages will use `lang="he"` and
`dir="rtl"`. User-facing labels and errors will be Hebrew, while identifiers and
stored enum values remain English. Small interactions may use HTMX when justified.

## Consequences

The application remains one deployment unit and avoids a separate JavaScript
build system. RTL behavior and Hebrew copy require deliberate testing. Complex
client-side interactions are outside the initial version.

## Alternatives considered

- A React, Vue, or Next.js SPA: rejected because it creates a separate application
  and distracts from the AWS learning goals.
- An English-first interface: rejected because it does not match the intended users.
