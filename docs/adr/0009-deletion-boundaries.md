# ADR 0009: Soft and Hard Deletion Boundaries

- Status: Accepted foundation; retention policy BLOCKED
- Date: 2026-10-05

## Decision

Participant lifecycle removal is represented by `deleted_at` and closed status so related evidence/decision history is not accidentally cascaded by routine application actions. Evidence sources/items, transitions, overrides, consent records, and audit events are append-only in application code. Hard deletion is not exposed as a Milestone 1 service.

This is not a retention decision. Legal bases, deletion rights, schedules, deidentification, audit retention, and backup expiry require owner/legal approval.

## Consequences

Accidental destructive operations are reduced. A future approved deletion graph must deliberately handle identifiers, participants, structured evidence, financial records, audit, and backups; it may supersede this foundation through a new ADR.
