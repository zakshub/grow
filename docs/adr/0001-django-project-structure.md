# ADR 0001: Django Project Structure

- Status: Accepted
- Date: 2026-10-05
- Authority: Approved technical plan and Milestone 1 request

## Decision

Use a single repository and modular Django monolith under `src/grow/`. Configuration lives in `grow.config`; bounded apps are `participants`, `journeys`, `assessments`, `reviews`, `access`, `followups`, and `audit`. Shared abstract models live in `grow.common`; deterministic synthetic scenarios live in `grow.synthetic`.

The operator inspection surface is Django Admin only. No participant UI, API, WhatsApp adapter, AI adapter, recommendation engine, or background worker is included in Milestone 1.

## Consequences

Domain boundaries remain visible without distributed-service complexity. Cross-app behaviour uses application services. A later split requires evidence. The package uses a `src/` layout and `pyproject.toml`; local commands require an editable installation.
