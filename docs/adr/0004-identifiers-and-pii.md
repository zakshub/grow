# ADR 0004: Identifier and PII Separation

- Status: Accepted
- Date: 2026-10-05

## Decision

`Participant` uses a random internal UUID and contains no phone number, name, email, or external identity. `ParticipantIdentifier` is a separate table containing an equality-search digest and optional ciphertext/key version. Domain services, evidence, jobs, logs, and analytics refer only to the participant UUID.

Milestone 1 stores only synthetic SHA-256 aliases and no ciphertext. The production encryption/key-management implementation remains blocked by security and deployment decisions.

## Consequences

Identity data can receive stricter access and deletion treatment. Digest construction, encryption, and key rotation must be approved before real identifiers are stored.
