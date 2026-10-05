# ADR 0007: Evidence Versioning

- Status: Accepted
- Date: 2026-10-05

## Decision

Evidence sources and evidence items are append-only. Every item records source provenance, journey, optional assessment shell, dimension code, category, value status, direction, confidence, privacy class, and observation time. Corrections create a new version in the same evidence chain and link `supersedes`; history is not overwritten.

UNKNOWN, KNOWN, and NOT_APPLICABLE are distinct. UNKNOWN cannot contain zero, empty-derived scoring, or a confidence score. No scoring or assessment-validity rules are implemented.

## Consequences

Future estimates can reproduce their inputs. Storage grows through versions; retention policy remains blocked and must not be inferred from append-only application behaviour.
