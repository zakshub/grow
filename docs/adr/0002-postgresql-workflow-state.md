# ADR 0002: PostgreSQL Owns Workflow State

- Status: Accepted
- Date: 2026-10-05

## Decision

PostgreSQL is the deployed source of truth for participant journeys, state versions, transitions, evidence, reviews, access decisions, follow-ups, and audit records. State changes use database transactions, row locking, and optimistic expected-version checks.

SQLite is allowed only as a zero-service local/CI test convenience in Milestone 1. It is not the production architecture and must not be used to justify PostgreSQL-specific deployment readiness.

## Consequences

Queue/cache loss cannot erase workflow truth. Migrations remain portable for fast tests, while PostgreSQL integration validation is required before production readiness.
