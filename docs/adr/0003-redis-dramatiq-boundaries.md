# ADR 0003: Redis and Dramatiq Boundaries

- Status: Accepted; runtime introduction deferred
- Date: 2026-10-05

## Decision

Redis and Dramatiq may deliver asynchronous work in later milestones but never own business state, schedules, consent, evidence, review decisions, or idempotency truth. Durable job intent will be committed to PostgreSQL through an outbox before publication. Workers will be retryable and idempotent.

Milestone 1 introduces neither dependency because it contains no background workflow. This avoids unused operational complexity while fixing the future boundary.

## Consequences

Adding queues later requires an ADR update, outbox schema, failure tests, and operational ownership. Direct model mutation from untracked background jobs is prohibited.
