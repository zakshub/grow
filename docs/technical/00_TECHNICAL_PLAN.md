# Technical Plan

## Status and authority

This is an implementation plan, not implementation. It was derived from the repository authority in the order required by `docs/18_IMPLEMENTATION_HANDOFF.md`, followed by the remaining product documents. Product behaviour remains governed by `README.md`, `BRAIN.md`, and `docs/01` through `docs/18`.

## Current repository assessment

At planning time the repository contains 21 tracked Markdown files and no application code. It provides a coherent product brain covering vision, audience, career discovery, assessment, participant journey, WhatsApp operations, recruitment, fees, privacy, architecture, automation, MVP, roadmap, measurement, research, open questions, features, and implementation handoff.

Present strengths:

- Clear non-goals: Grow is not a generic chatbot, deterministic career predictor, clinical instrument, or autonomous decision-maker.
- Multi-layer evidence model and explicit separation of interest, ability, potential, constraints, practical behaviour, and market reality.
- Strong human-review, minors, dignity, uncertainty, knowledge-promotion, and Git data boundaries.
- Explicit MVP scope, phased roadmap, and first engineering sequence.

Missing implementation foundations:

- No language/framework selection, package or application skeleton.
- No executable domain schema, migrations, state transition table, API contract, or provider interfaces.
- No authentication/RBAC, secrets, retention schedule, legal consent rule, safeguarding playbook, or incident process.
- No test harness, CI, deployment manifests, observability, backups, or recovery procedure.
- Career taxonomy, assessment v1, experiment rubrics, Urdu content, and market sources are research inputs still requiring validation.

The repository is therefore ready for technical planning but not safe for participant-facing production.

## Recommended technology stack

Use a modular monolith first. The recommendation is intentionally conservative and can be revisited through an architecture decision record (ADR) before Milestone 1.

| Layer | Recommendation | Reasoning |
| --- | --- | --- |
| Backend | Python 3.14, Django 5.2 LTS (latest patches), Django REST Framework | Mature relational modelling, migrations, authentication/admin foundations, strong testing, Unicode support, reliable webhooks, and low-complexity VPS operation. Python also supports later research and scoring work without making AI the architecture. As checked on 2026-10-04, Python 3.14 is current and Django 5.2 LTS has longer extended support than the current feature release; re-verify compatibility and support before Milestone 1. |
| Operator UI | Server-rendered Django templates with HTMX and a small amount of TypeScript | Produces the smallest secure review console; avoids an early SPA and duplicate API/UI complexity. Build a separate frontend only if measured interaction needs justify it. |
| Database | PostgreSQL 18 (latest minor) | Transactions, constraints, JSONB for bounded snapshots, full-text options, row locking, partitioning, and strong audit/reporting support. PostgreSQL remains the source of truth. PostgreSQL recommends the current minor release; re-verify Django/driver compatibility before Milestone 1. |
| Queue/cache | Redis plus Dramatiq | Simple delayed/retryable background jobs with Python support. Business workflow state stays in PostgreSQL; Redis is never authoritative. Celery is a valid fallback if team experience strongly favours it. |
| Object storage | S3-compatible API; MinIO on controlled VPS, managed object storage when durability/operations require it | Keeps voice/media outside the relational database, supports encryption and lifecycle deletion, and avoids coupling to one vendor. |
| Reverse proxy | Caddy | Automatic TLS, concise configuration, and reliable webhook ingress. |
| Packaging/deploy | Docker Compose on one VPS initially | Reproducible local/staging/production topology with low operator burden. No Kubernetes for MVP. |
| Tests/quality | pytest, pytest-django, Hypothesis, Ruff, mypy, Playwright, accessibility checks | Covers deterministic rules, state invariants, property-based ranking cases, operator flows, and browser behaviour. |
| Observability | OpenTelemetry instrumentation, Prometheus, Grafana, Loki, Sentry-compatible error tracking | Correlated metrics/logs/traces with sensitive-data redaction. Start with a small self-hosted subset and add managed error tracking only after data-handling review. |
| CI | GitHub Actions using synthetic fixtures only | Fits the repository; runs lint, type checks, migrations, tests, secret scanning, and build verification without participant data. |
| AI and speech | Internal capability interfaces with approved external provider adapters | Provider-independent, minimised payloads, structured outputs, explicit prompt versions, and deterministic fallbacks. Provider selection remains open. |

Framework and service versions must be verified against current security/support status when implementation begins. No version choice in this plan authorises a product change.

Version check sources: [Python downloads](https://www.python.org/downloads/), [Django supported versions](https://www.djangoproject.com/download/), and [PostgreSQL versioning policy](https://www.postgresql.org/support/versioning/).

## Core architecture decisions

1. One deployable modular monolith with bounded modules; split services only for measured scaling, isolation, or team ownership needs.
2. PostgreSQL is the transactional source of truth for participant state, evidence, decisions, audit metadata, and job intent.
3. WhatsApp is an external transport, not the workflow engine. Every inbound event is verified, deduplicated, persisted, then processed asynchronously.
4. AI can classify, extract, summarise, draft, and propose. It cannot grant consent, change authoritative state, approve fees, close safeguarding cases, publish assessment rules, or issue an MVP final recommendation without a human.
5. Recommendations are versioned artifacts linked to input evidence, career-data versions, scoring configuration, conflicts, confidence, and review decisions.
6. Raw conversations and media are separated from structured evidence. Each has an independent access and retention policy.
7. Every sensitive write, human read of a sensitive case, override, export, consent change, and deletion is auditable.
8. All committed examples and tests are synthetic. Participant data and production exports never enter Git.

## Complete system shape

The system consists of an inbound WhatsApp gateway, conversation workflow, participant/consent domain, assessment/evidence engine, career intelligence registry, deterministic recommendation pipeline, practical experiment workflow, review/override queues, payment/access records, follow-up automation, operator console, audit/observability, and provider adapters. Details are in `01_ARCHITECTURE.md`.

## MVP boundary

In scope:

- Karachi-first, Urdu-first, Grade 8 through graduation primary cohort, with a small explicitly separated adult track if the pilot chooses.
- Official WhatsApp participant channel, text and a defined voice path.
- Consent, minor detection, guardian workflow once legally defined, profile, discovery, bounded v1 assessment, evidence/confidence/contradiction storage.
- Six vocational interest families, core work values, initial career clusters/profiles, at least six practical-experiment families.
- Three to five ranked directions when justified; fewer only after the product question is resolved. Every direction includes support, conflict, tradeoff, route, next experiment/action, and confidence.
- Human review of every final MVP recommendation; human access decisions for reduced/free service.
- Minimal operator console, opt-out, conservative reminders, 7-day and 30-day follow-up, basic funnel/quality reporting.

Out of scope:

- National career coverage, regional languages beyond Urdu, native mobile apps, institutional/white-label features, parent portal, advanced gamification, automated national salary prediction, Grow-trained ML, full alumni/mentor network, and autonomous final recommendations.

## External services eventually required

- Official WhatsApp Business Platform, either Meta Cloud API directly or an approved BSP after comparison.
- A transactional AI text provider only after privacy, retention, regional processing, structured-output, cost, and fallback review.
- A speech-to-text provider for Urdu/Urdu-English code-switching after measured quality tests.
- Payment rail/provider after payment methods and verification rules are resolved.
- DNS/domain registrar, TLS, email for staff identity/recovery, and optionally SMS/TOTP backup for operator MFA.
- Off-site backup/object storage separate from the primary VPS.
- Authoritative research sources: PBS, NAVTTC, HEC, O*NET or other legally usable frameworks, plus reviewed current market sources.

## Self-hosted boundary

Can remain self-hosted: application, operator console, PostgreSQL, queue workers, Redis, scheduler, assessment and recommendation logic, career registry, prompt registry, reporting, audit metadata, dashboards, and optionally encrypted media/object storage.

Cannot responsibly be replaced by ad hoc self-hosting: official WhatsApp transport and telecom identity. AI and speech may be self-hosted later only if Urdu quality, security, hardware, maintenance, and cost are proven; they should be treated as provider adapters, not assumed capabilities. Off-site backup must not share the same failure domain as the VPS. Payment settlement remains with regulated rails/providers.

## Recommended first implementation milestone

After this plan is approved, begin only with Milestone 0/1 in `13_IMPLEMENTATION_MILESTONES.md`: decision gates and a local foundation that can move one synthetic participant through an explicit journey with consent/guardian guards, evidence/confidence/contradictions, review, fees, follow-up, and audit—without WhatsApp or external AI. This matches the canonical handoff and makes the product logic reviewable before integrations.
