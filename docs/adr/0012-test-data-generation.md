# ADR 0012: Test Data Generation

- Status: Accepted
- Date: 2026-10-05

## Decision

Synthetic scenarios are created deterministically through `grow.synthetic.scenarios`, keyed by non-reversible hashes of explicit synthetic codes. The generator covers the twelve requested participant cases and is idempotent. Names, phone numbers, conversations, addresses, financial histories, and raw guardian details are absent.

Fee scenarios are pending candidates, not eligibility conclusions. Minor scenarios use explicit synthetic classifications and unresolved guardian handling, not a legal age policy. Contradictory evidence is clearly labelled synthetic.

## Consequences

Tests and local inspection are reproducible. Synthetic cases must never be described as validated assessment examples or real participant patterns.
