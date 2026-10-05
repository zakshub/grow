# ADR 0008: Human Override Model

- Status: Accepted
- Date: 2026-10-05

## Decision

Human overrides are generic, append-only records attached to a human review. They preserve target, complete original result, complete new result, reviewer reference, mandatory reason, and server timestamp. The service rejects missing reviewers/reasons and unchanged results, and creates an audit event atomically.

No career recommendation override is implemented because recommendations are outside Milestone 1. The model can safely support future versioned domain results without deleting the original.

## Consequences

Review corrections are explainable and learnable. Role-based reviewer authentication/authorisation is not yet implemented and is a blocker before production use.
