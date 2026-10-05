# ADR 0006: State Transition Rules

- Status: Accepted
- Date: 2026-10-05

## Decision

Journey state changes occur only through `transition_journey`. The service validates an explicit transition graph, locks the journey row, checks an optional expected version, applies consent/guardian/review guards, records an immutable transition, increments the state version, and writes an audit event atomically.

UNKNOWN minor or guardian requirement blocks the consent gate. An explicitly required guardian case needs a development-workflow acknowledgement; this is not legal guardian consent. The production guardian policy remains blocked.

## Consequences

Invalid and stale transitions fail. The state machine is UI-independent. `RECOMMENDATION_READY` is only a workflow gate name in Milestone 1; no recommendation object or delivery logic exists.
