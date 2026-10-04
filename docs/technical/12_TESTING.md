# Testing Strategy

## Test pyramid

1. **Unit tests** — domain commands, guards, scoring contributions, confidence/sufficiency, contradiction rules, privacy classification, Urdu/template selection.
2. **Property-based tests** — state-machine invariants, ranking invariants, idempotency, missing-data handling, fee/demographic independence, date/freshness boundaries.
3. **Database/integration tests** — constraints, transactions, row/version locks, migrations, outbox, retention/deletion graph, RBAC query scoping.
4. **Contract tests** — WhatsApp webhook/signature/events/status/media, AI structured schemas, speech responses, payment adapter when chosen. Recorded fixtures are synthetic/redacted.
5. **Workflow tests** — complete synthetic participant journeys, minor/guardian branches, opt-out, pause/resume, experiment, review/override, fee, follow-up, provider failure.
6. **Browser tests** — operator queues, least-privilege views, approvals, overrides, exports, accessibility and concurrency conflicts.
7. **Non-functional tests** — load/soak, security, backup restore, disaster recovery, observability, localisation, accessibility, and chaos/failure injection.
8. **Pilot validation** — human review agreement, participant comprehension, question/experiment quality, confidence calibration, fairness and action outcomes. Software correctness is not assessment validity.

## Mandatory canonical cases

- Allowed and forbidden state transitions.
- Minor/guardian requirement and unresolved-age fail-closed paths.
- Consent blocks processing; withdrawal and opt-out suppress queued messages.
- Assessment scoring traces to evidence and version.
- Contradictions remain visible and reduce confidence or require review.
- Completion uses sufficiency, not question count.
- Recommendation returns ranked multiple options when supported, with support/conflict/confidence/unknowns.
- Unknown market evidence remains unknown.
- Human approve/override retains original, reason, actor, and time.
- Fee/access data cannot affect career capability or ranking.
- Practical experiment evidence can produce a new recommendation version.
- Provider retries and duplicate/out-of-order events are idempotent.

## Golden synthetic personas

Maintain diverse, clearly fictional cases across education levels, language/script preferences, device constraints, contradictory signals, strong/weak evidence, and adult track. Do not encode demographic stereotypes. Golden tests assert reasoning structure and invariants more than brittle exact scores while algorithms are provisional.

## Recommendation validation

- Snapshot/golden comparisons with reviewer-readable contribution diffs.
- Metamorphic tests: changing name, gender, fee status, school brand, or city alone cannot change capability evidence; adding access constraints may change route feasibility only.
- Distribution tests flag career overconcentration and suspicious group correlations.
- Shadow-test new scoring/config versions on synthetic and consented deidentified evaluation sets before publication.
- Track reviewer disagreement and later outcome evidence; do not claim predictive validity from small samples.

## Urdu, voice, and accessibility

- Human linguistic review for naturalness, comprehension, respectful uncertainty, and age-appropriate language.
- Test Urdu script, expected Roman Urdu/code-switching, RTL rendering, numerals, buttons, and text wrapping.
- Speech benchmark by accent, background noise, phone quality, code-switching, age/education bands, and career vocabulary using properly consented data.
- Verify every voice path has a text/clarification alternative and does not penalise transcription uncertainty.
- Operator console keyboard navigation, contrast, focus, labels, and screen-reader smoke tests.

## Security/privacy tests

Threat-model review, dependency/container/secret scanning, SAST, permission matrix tests, object access/URL expiry, webhook forgery/replay, CSRF/XSS/IDOR, rate limiting, encrypted-field/key rotation, log redaction, export authorisation, deletion/retention, and restore isolation. Arrange independent penetration testing before broader production scale.

## Performance and resilience

Model bursty webhook ingress, media queues, reminder batches, report generation, review-console queries, AI/speech slowness, Redis loss, worker restart, DB connection pressure, and provider outages. Acceptance uses queue age and participant-message SLOs, not raw request throughput alone.

## CI gates

Every change: formatting/lint, types, unit/property/integration tests, migration checks, synthetic PII/secret scan, dependency audit, and image build. Main/release additionally runs end-to-end/contract tests. Deploy requires green staging smoke and migration/backup checks. Prompt, assessment, career-data, workflow, and scoring changes receive domain-owner review like code.

## Evidence of completion

Each milestone supplies test report, coverage of its acceptance criteria, known limitations, versioned synthetic fixtures, security/privacy impact, and reviewer sign-off. Test coverage percentage alone is not a release criterion.
