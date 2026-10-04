# System Architecture

## Architectural style

Grow begins as a modular monolith with asynchronous workers. Modules enforce boundaries in code and database access while sharing one transactional PostgreSQL database. This avoids premature distributed failure modes while preserving a future extraction path.

```text
Participant
  -> Official WhatsApp Business Platform
  -> Caddy / webhook ingress
  -> Inbound event inbox (verify + deduplicate + persist)
  -> Workflow dispatcher / background worker
       -> Participant, consent and guardian
       -> Conversation and Urdu response composition
       -> Assessment and evidence
       -> Practical experiments
       -> Career intelligence
       -> Recommendation pipeline
       -> Review, fee and safeguarding queues
  -> Outbound message outbox
  -> Official WhatsApp Business Platform

Operator -> authenticated web console -> same application services

Shared: PostgreSQL | Redis | object storage | audit | metrics/logs/traces
External adapters: WhatsApp | AI text | speech | payment | research imports
```

## Module boundaries

| Module | Owns | May not decide |
| --- | --- | --- |
| Participants | identity, profile, contact mapping, language, life-stage track | consent validity, recommendation content |
| Consent and guardians | consent artifacts, guardian relationships, communication permissions | legal policy itself; policy is configured only after review |
| Conversations | messages, sessions, workflow cursor, opt-out intent, templates | assessment truth from raw chat alone |
| Assessment and evidence | instruments, items, responses, dimensions, evidence, estimates, contradictions, sufficiency | career recommendation approval |
| Experiments | library, assignments, submissions, rubric observations | final recommendation independently |
| Career intelligence | taxonomies, profiles, pathways, market observations, sources/freshness | participant fit |
| Recommendations | candidate generation, scoring, explanations, versions | final MVP delivery without review |
| Reviews and safety | queues, reviewer decisions, overrides, escalations | silent changes to evidence or past artifacts |
| Fees and payments | access decision and payment records | capability scoring |
| Automation and follow-up | jobs, reminders, follow-ups, reports | overriding opt-out or review gates |
| Research and learning | observations, hypotheses, promoted rules, versions | automatic promotion from analytics |
| Identity and access | staff accounts, roles, MFA/session policy | participant domain decisions |
| Audit and observability | append-only activity trail, correlation IDs, operational telemetry | storing unnecessary message content in logs |

Modules communicate through application services and durable domain events/outbox rows, not direct cross-module table mutation.

## Request and message flow

### Inbound WhatsApp

1. Accept only HTTPS; validate Meta/BSP signature and webhook verification challenge.
2. Generate correlation ID; reject oversized/invalid input; rate limit by provider and endpoint.
3. Store provider event ID and a minimally retained encrypted payload or payload reference in `inbound_events` within a transaction. A unique constraint makes retries idempotent.
4. Acknowledge quickly to avoid platform retries.
5. Worker maps the external address through a protected contact mapping, checks opt-out/communication permission, and applies one allowed state-machine command.
6. Text/voice interpretation produces proposed structured observations with source lineage. Uncertain interpretation triggers clarification or review; it never fabricates evidence.
7. Response intent is written to an outbox. A sender renders the correct language/template and records delivery status and provider IDs.

### Recommendation

1. Freeze an assessment snapshot and eligible evidence set.
2. Select career profile and market-evidence versions valid for the geography/date.
3. Deterministically generate candidates, calculate component scores, feasibility and uncertainty, and retain all intermediate contributions.
4. AI may draft a plain-Urdu explanation from the stored structure; output is schema-validated and treated as a draft.
5. Create an immutable recommendation version and mandatory MVP review task.
6. Reviewer approves, requests more evidence, or overrides with reason. Delivery uses only the approved version.

## API shape

- `/webhooks/whatsapp/*`: isolated public webhook endpoints.
- `/internal/api/v1/*`: authenticated operator JSON endpoints where needed.
- Server-rendered operator routes for queues, participant summaries, evidence, recommendations, fees, follow-up, and safety.
- `/health/live` checks process; `/health/ready` checks critical dependencies without exposing detail.
- Management commands/import jobs for versioned career data and content; no production mutation by ad hoc shell scripts.

Publish an OpenAPI contract for integration endpoints and machine-consumed operator APIs. Use optimistic concurrency/version fields on reviewable records and row locks on state transitions.

## AI and speech interfaces

Internal ports:

- `StructuredInterpreter.interpret(input, schema, policy_context)`
- `EvidenceSummarizer.summarize(evidence_ids, audience)`
- `FollowUpDrafting.propose(missing_evidence, language_profile)`
- `ExplanationDrafting.propose(recommendation_version, audience)`
- `TextClassifier.classify(input, labels)`
- `SpeechTranscriber.transcribe(media_ref, language_hints)`

Every invocation stores purpose, provider/model, prompt ID/version, schema version, timestamp, latency, cost metadata, redacted input fingerprint, output status, and linked domain artifact. Store raw provider payloads only when necessary and permitted. Timeouts, retries, circuit breakers, and a manual/deterministic fallback are mandatory.

## Operator access

Use staff-only accounts, not WhatsApp identity. Require MFA for privileged roles. Initial roles:

- Career reviewer: assessment summaries, evidence, experiments, recommendations.
- Access reviewer: minimal affordability and fee information; no detailed assessment unless separately authorised.
- Safeguarding reviewer: sensitive cases on a need-to-know basis.
- Operations administrator: workflow status and messaging, not unrestricted sensitive notes.
- System administrator: configuration and health; participant-content access requires a separate, audited elevation.
- Auditor/read-only: controlled access to decisions and audit evidence.

Enforce permissions in service methods and queries, not only UI visibility. Sensitive-case reads create access events.

## Audit and observability

### Audit

Append an audit event for actor, action, target type/ID, timestamp, request/correlation ID, purpose/reason, prior/new state references, result, and source IP/session metadata where appropriate. High-value events include consent/guardian changes, state transitions, sensitive reads, review decisions, overrides, fee decisions, exports, deletion, policy/config changes, prompt/rule publication, and staff-role changes.

Audit events are append-only to the application. Corrections create new events. Periodic hashes/checkpoints and restricted database permissions provide tamper evidence. Never copy full conversations or secrets into the audit payload.

### Operational telemetry

- Structured logs with correlation IDs, event IDs, job IDs, and participant pseudonymous IDs.
- Metrics: webhook rates/latency, deduplication, queue depth/age, send success, state-transition failures, review queue age, follow-up execution, DB/Redis/object health, backup success, AI/speech latency/cost/failure.
- Traces across webhook, worker, provider, and outbox boundaries with content redaction.
- Alerts based on participant impact: inbound processing delay, outbound failure, consent bypass attempt, review backlog, backup failure, disk pressure, error spike.
- Product analytics are derived from structured domain events, not raw log scraping.

## Environments

| Environment | Data | External access | Purpose |
| --- | --- | --- | --- |
| Local | generated synthetic fixtures only | provider simulators by default | development and deterministic tests |
| CI | ephemeral synthetic DB/object store | network denied except approved build sources | lint, type, security, migration, unit/integration/contract tests |
| Staging | synthetic or specifically consented test identities; never a production clone | provider sandbox/test number | end-to-end validation, migrations, restore drills |
| Production | real participant data | production WhatsApp and approved providers | controlled pilot/service |

Use separate credentials, databases, object buckets, domains, provider apps/numbers, encryption keys, and staff roles. Production data must never be copied down. Promote signed/reproducible images from CI; deploy configuration separately.

## Deployment evolution

- Pilot: one application VPS running proxy, web, worker, scheduler, Redis, and monitoring; PostgreSQL may share the VPS only if encrypted off-site backups and resource isolation are proven. Prefer a separate database volume or managed DB if budget permits.
- Growth: separate database host, separate object storage, multiple stateless web/worker replicas, highly available queue/cache as justified.
- 10,000 participants: still feasible as a modular monolith; split workloads by worker queue and replicas before considering microservices.

See `11_INFRASTRUCTURE.md` for topology, capacity assumptions, recovery, and cost drivers.
