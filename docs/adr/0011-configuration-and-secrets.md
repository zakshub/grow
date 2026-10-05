# ADR 0011: Configuration and Secrets Handling

- Status: Accepted
- Date: 2026-10-05

## Decision

Runtime configuration comes from environment variables. `.env.example` contains names and development placeholders only. Production refuses to start without a secret key; SQLite is the local default, while PostgreSQL credentials are provided separately when selected. Secrets never enter source, images, logs, fixtures, or audit details.

No production secret manager is selected in Milestone 1 because VPS/deployment ownership is unresolved.

## Consequences

Environment separation is explicit. Secret rotation, encrypted deployment delivery, and CI secret permissions require a later deployment ADR before production.
