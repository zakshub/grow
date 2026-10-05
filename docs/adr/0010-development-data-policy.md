# ADR 0010: Development Data Policy

- Status: Accepted
- Date: 2026-10-05

## Decision

Local development, tests, documentation, screenshots, demos, and CI use synthetic data only. Production copies, WhatsApp transcripts, phone numbers, guardian contacts, financial narratives, recordings, and identifiable assessment records are prohibited from Git and non-production environments.

Ignored paths include environments, `.env` files, SQLite databases, media, logs, dumps, backups, coverage, and build artifacts. A leak requires incident response, not merely deletion from the latest commit.

## Consequences

Debugging with production clones is prohibited. Future safe deidentified evaluation data requires separate governance and is not authorised by this ADR.
