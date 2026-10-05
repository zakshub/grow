# Architecture Decision Records

ADRs record implementation decisions that are safe to make technically. They do not resolve product, legal, research, safety, or pilot questions without the named owner/evidence.

| ADR | Decision | Status |
| --- | --- | --- |
| [0001](0001-django-project-structure.md) | Django project structure | Accepted |
| [0002](0002-postgresql-workflow-state.md) | PostgreSQL owns workflow state | Accepted |
| [0003](0003-redis-dramatiq-boundaries.md) | Redis and Dramatiq boundaries | Accepted, deferred runtime |
| [0004](0004-identifiers-and-pii.md) | Identifier and PII separation | Accepted |
| [0005](0005-audit-event-model.md) | Audit event model | Accepted |
| [0006](0006-state-transition-rules.md) | State transition rules | Accepted |
| [0007](0007-evidence-versioning.md) | Evidence versioning | Accepted |
| [0008](0008-human-overrides.md) | Human override model | Accepted |
| [0009](0009-deletion-boundaries.md) | Soft versus hard deletion boundaries | Accepted with policy blocked |
| [0010](0010-development-data-policy.md) | Development data policy | Accepted |
| [0011](0011-configuration-and-secrets.md) | Configuration and secrets | Accepted |
| [0012](0012-test-data-generation.md) | Test data generation | Accepted |

See `docs/implementation/01_OPEN_DECISION_CLASSIFICATION.md` for the complete open-decision classification.
