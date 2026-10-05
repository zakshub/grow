# ADR 0005: Audit Event Model

- Status: Accepted
- Date: 2026-10-05

## Decision

Important actions create append-only `AuditEvent` records with event type, actor type/reference, target type/UUID, reason, correlation ID, structured minimal details, and server timestamp. State transitions and human overrides write audit events in the same database transaction as the domain change.

Audit details must not contain direct identifiers, raw conversations, secrets, or unnecessary sensitive narrative. Application updates/deletes are rejected; deployment-level database permissions and tamper evidence remain future hardening.

## Consequences

Decisions are traceable without turning audit storage into a second sensitive-data store. Admin superusers can still bypass application methods at the database level; this is documented technical debt before production.
