# Implemented Current State

This file is the factual source of truth for implemented reality. Planning documents describe intent; only capabilities listed here are present in code and tests.

Last verified: 2026-10-05

## Milestone status

Pre-implementation technical decisions, the synthetic Milestone 1 domain foundation, the deterministic Milestone 2 assessment/evidence engine, and the synthetic Milestone 3 versioned career-intelligence registry are implemented. There is no real participant operation, WhatsApp integration, external AI, speech, participant-to-career matching, recommendation object/logic, experiment workflow, payment processing, production authentication/RBAC, or production deployment.

## Runtime foundation

- Python 3.13+ package using Django 5.2 LTS.
- `src/` modular-monolith layout with apps for participants, journeys, assessments/evidence, career intelligence, reviews/overrides, access/fees, follow-ups, and audit.
- PostgreSQL configuration is available and is the ADR-defined deployed source of truth.
- SQLite is the default for zero-service local development and tests.
- Django Admin registers domain records for development inspection only; it is not the operator UX or production authorisation model.
- Environment-based configuration, development-only fallback secret, and production secret fail-closed behaviour.
- Redis and Dramatiq are not installed or used. Their later boundary is recorded in ADR 0003.

## Implemented schema

Committed migrations create these domain tables:

| App | Models implemented |
| --- | --- |
| `participants` | `Participant`, `ParticipantIdentifier`, `ParticipantProfile`, `ConsentRecord`, `GuardianRelationship`, `ReferralSource` |
| `journeys` | `ParticipantJourney`, `StateTransition` |
| `assessments` | `AssessmentDefinition`, `AssessmentVersion`, `AssessmentSection`, `AssessmentDimension`, `AssessmentDimensionRequirement`, `AssessmentItem`, `AssessmentItemVariant`, `AssessmentSession`, `AssessmentItemPresentation`, `AssessmentResponse`, `AssessmentObservation`, `EvidenceSource`, `EvidenceItem`, `DimensionEvidence`, `DimensionResult`, `Contradiction`, `ContradictionEvidence` |
| `careers` | `CareerTaxonomy`, `CareerTaxonomyVersion`, `CareerCluster`, `CareerFamily`, `CareerProfile`, `CareerProfileVersion`, `CareerAlias`, `CareerRelationship`, `CareerDimensionRelationship`, `CareerEnvironmentObservation`, `CareerSkill`, `CareerSkillRequirement`, `CareerPathway`, `ResearchSource`, `MarketObservation`, `CareerReviewDecision`, `CareerImportBatch`, `CareerImportDiff` |
| `reviews` | `HumanReview`, `HumanOverride` |
| `grow_access` | `AccessDecision` |
| `followups` | `FollowUp` |
| `audit` | `AuditEvent` |

All domain primary keys are random UUIDs. Direct/external identifiers are separated from `Participant`; synthetic fixtures store only SHA-256 lookup aliases. One active journey per participant is database-constrained.

### UNKNOWN behaviour

UNKNOWN is explicit for participant/profile status, age knowledge, minor status, guardian requirement, consent, referral source, assessment/session sufficiency, dimension sufficiency/confidence, evidence category/value/direction/confidence, contradiction resolution, human review, access category/decision, and follow-up/outcome.

Evidence marked UNKNOWN cannot contain a numeric/text value. UNKNOWN confidence cannot contain a numeric score. Missing age does not become age zero. Pending access candidates do not become a final fee category.

Career market UNKNOWN cannot contain a value or unit and is never interpreted as zero demand or salary. Career sources and observations also preserve `CURRENT`, `STALE`, `RETIRED`, and `UNKNOWN` freshness. Expiry makes effective freshness stale without mutating the historical row.

### Evidence and contradiction

Evidence sources are append-only and record source type, reference, provenance version, time, and structured details. Evidence items are append-only, chained by ID/version, can supersede an earlier version without modifying it, and record dimension, category, value state, direction, confidence, reason, privacy class, and time.

Contradictions link at least two evidence items from the same journey and dimension. Detection preserves opposing normalized pilot signals, and audited human resolution never deletes either item.

## Deterministic assessment engine

- Definitions contain immutable numbered versions with `DRAFT`, `PILOT`, `ACTIVE`, and `RETIRED` lifecycle states.
- Sessions pin the exact definition/version, audience, language, locale, and item limit used.
- Sections, items, and Urdu/English audience/education variants are immutable after publication.
- Nine structured/text item types are supported; text is stored without AI/NLP interpretation.
- The pilot taxonomy contains 81 dimensions across seven approved categories. The synthetic v1 assessment uses eight required dimensions and 14 items to exercise the architecture.
- Response evidence retains source, response, dimension, raw/structured value, optional normalized interpretation, confidence, review status, context, method/version, privacy class, and time.
- Append-only `DimensionResult` projections preserve evidence IDs, calculation inputs/version, confidence, sufficiency, contradictions, reasons, and next action.
- Sufficiency states are `UNKNOWN`, `INSUFFICIENT`, `TENTATIVE`, `SUPPORTED`, and `CONTRADICTORY`.
- Adaptive selection returns `ASK_MORE`, `SUFFICIENT`, `HUMAN_REVIEW_REQUIRED`, or `UNKNOWN`; it uses missing/weak/conflicting required dimensions, source requirements, audience/language applicability, answered items, and item limits.
- Confidence uses a documented deterministic pilot heuristic based on independent sources, source diversity, review, and unresolved contradictions. It is confidence in evidence, not a participant score or validity claim.
- A deterministic participant assessment snapshot reports knowns, unknowns, evidence counts, confidence, contradiction state, completion, review need, and next assessment action. It contains no career recommendation.

The exact rules and limitations are documented in `02_MILESTONE_2_ASSESSMENT_ENGINE.md`.

## Versioned career intelligence registry

- Taxonomies contain version-pinned clusters, families, career profile versions, aliases, and career relationships. Careers themselves use stable database codes rather than enums.
- Taxonomy/profile lifecycle is `DRAFT`, `PILOT`, `ACTIVE`, or `RETIRED`; the separate human workflow is `DRAFT`, `IN_REVIEW`, `APPROVED`, `PUBLISHED`, `STALE`, or `RETIRED`.
- Published taxonomy and profile content is application-immutable. Corrections create new versions or superseding evidence, retaining historical reproducibility.
- Career profile relationships reuse the 81-dimension assessment taxonomy and separately preserve cognitive, work-style, communication, creativity, interest, value, and environment evidence. Every relation carries qualitative relevance, direction, confidence, source, limitations, version/status, and optional context.
- Skills and ten pathway route types are supported with geography, requirements, time/cost categories, prerequisites, next step, evidence, limitations, review/freshness, and supersession.
- Research sources preserve type, title/publisher/reference, dates, geography, methodology, limitations, licence notes, quality, review, freshness, expiry, and supersession.
- Market observations cover demand, sourced salary ranges, entry difficulty, remote/freelance relevance, automation exposure, international mobility, hiring concentration, and training availability, with geography and work context. The synthetic pack supplies no numeric market claims.
- Deterministic staged imports validate `career-import-v1`, hash the payload, diff stable codes as new/changed/removed, require human approval, and publish a new immutable version. They cannot fetch or scrape external content.
- `build_career_snapshot` returns career information, unknowns, freshness, evidence, routes, and limitations only. It accepts no participant or assessment input and performs no matching/ranking.
- Django Admin is a read-only inspection surface for registry, evidence freshness, publication, and import diffs. Human review/import services emit append-only review decisions and audit events.

The exact contracts and boundaries are documented in `03_MILESTONE_3_CAREER_INTELLIGENCE.md`.

### Human review and overrides

Human reviews are generic workflow records. Human overrides are append-only and require a changed original/new result, reviewer reference, reason, target, and timestamp. The original system result is retained. Recording an override creates an audit event in the same transaction.

Reviewer identity is currently a pseudonymous string. Authentication, roles, permissions, and MFA are not implemented.

### Fee/access separation

`AccessDecision` references participant/journey only and has no capability, evidence, or scoring field. Reduced/free synthetic examples are pending candidates, not approved eligibility decisions. Approval requires an explicit final category, reviewer, and reason. No fee policy or payment handling is implemented.

## Actual state machine

Implemented normal transitions:

```text
NEW -> CONSENT_PENDING -> PROFILE_INCOMPLETE
PROFILE_INCOMPLETE -> DISCOVERY_IN_PROGRESS -> ASSESSMENT_IN_PROGRESS
ASSESSMENT_IN_PROGRESS -> EXPERIMENT_PENDING | HUMAN_REVIEW_REQUIRED
EXPERIMENT_PENDING -> EXPERIMENT_SUBMITTED -> HUMAN_REVIEW_REQUIRED
HUMAN_REVIEW_REQUIRED -> ASSESSMENT_IN_PROGRESS | EXPERIMENT_PENDING | RECOMMENDATION_READY
RECOMMENDATION_READY -> ROADMAP_ACTIVE -> FOLLOW_UP_DUE
FOLLOW_UP_DUE -> ROADMAP_ACTIVE | COMPLETED
```

Active workflow states can pause and resume to the recorded state. All non-terminal contactable states can opt out. Completion and opt-out close the active journey.

Each transition:

1. Locks the journey row.
2. Optionally verifies the expected state version.
3. Validates the explicit transition graph and guards.
4. Requires a reason.
5. Writes an append-only `StateTransition`.
6. Increments `state_version`.
7. Writes an append-only `AuditEvent` atomically.

Consent-to-profile progression requires the latest participation consent to be granted, minor status to be known, guardian requirement to be known, and explicitly required guardian handling to be acknowledged. The acknowledgement is a development workflow marker, not legal guardian consent. Human-review-to-recommendation-ready progression requires an approved review. `RECOMMENDATION_READY` is only a state-machine gate; there is no recommendation model, content, ranking, or participant delivery.

## Minor handling

`classify_minor_status` returns UNKNOWN unless an approved threshold is explicitly injected. No age threshold is hard-coded. Synthetic minor cases are explicitly labelled synthetic. Production minor consent, guardian verification, communication, sharing, and safeguarding remain BLOCKED.

## Synthetic scenarios

The Milestone 1 idempotent generator creates exactly these 12 foundation cases:

1. Grade 8 minor
2. Grade 10 minor
3. Intermediate student
4. University student
5. Graduate
6. Adult career switcher
7. Unknown age
8. Guardian handling required
9. Contradictory evidence
10. Human review required
11. Reduced-fee candidate
12. Free-access candidate

Run `python manage.py load_synthetic_fixtures` after migrations. No names, phone numbers, conversations, guardian contacts, addresses, financial narratives, recordings, or real assessment results are included.

The separate idempotent `load_synthetic_assessment_pack` command creates ten progressive assessment cases: Grade 8 unsure, Matric logical/investigative, Intermediate creative/communication, University conflicting preferences, Graduate uncertain, adult career switcher, highly contradictory self-report, mostly unknown, stopped early, and assessment human review required. All assessment wording and responses are explicitly synthetic pilot material.

The idempotent `load_synthetic_career_pack` command creates 12 reference careers: Software Developer, Data Analyst, UX / Product Designer, Graphic Designer, Teacher, Sales / Business Development, Accountant, Research Assistant, Mechanical Technician, Digital Marketer, Nurse, and Lawyer. Every profile is explicitly `SYNTHETIC`, `REFERENCE_ONLY`, and `NOT_READY_FOR_PARTICIPANT_RECOMMENDATION`; all bundled demand, remote, and salary observations are UNKNOWN.

## Validation implemented

- Formatting: Ruff formatter.
- Linting: Ruff rules for Python, imports, bug patterns, upgrades, and Django.
- Type checks: mypy on `src` and `tests` with migrations excluded.
- Django system checks and migration drift check.
- Pytest domain suite: 126 tests passing at the last verification.
- GitHub Actions is configured with PostgreSQL 18 to run migrations, all three synthetic loaders, and the same code-quality/test gates.
- Local PostgreSQL validation was unavailable on 2026-10-05 because no PostgreSQL service or Docker daemon was running. Fresh SQLite migration and fixture validation passed; PostgreSQL remains a CI/deployment gate, not a locally proven result.

The test count must be updated here whenever coverage changes; CI output remains the execution evidence.

## Planning deviations

1. Python 3.13 is used because it is the available runtime; the plan recommended Python 3.14. The project declares `>=3.13` and remains compatible with a later supported upgrade.
2. Redis/Dramatiq are boundary decisions only, not dependencies, because Milestone 1 has no asynchronous jobs.
3. SQLite is used locally for speed; PostgreSQL is configured as the authoritative deployment database, and CI is set up to exercise it. This local validation did not exercise PostgreSQL.
4. Career intelligence is now implemented as a separate participant-independent registry. Recommendation and practical-experiment domain models remain intentionally unimplemented because Milestone 3 prohibits matching and recommendations.
5. Django Admin is inspection-only; production operator access is not implemented.
6. The 81 dimensions are an engineering taxonomy. The bundled pilot version requires only eight dimensions and uses 14 synthetic items; neither set is a validated instrument.
7. Numeric confidence is retained internally only for deterministic reproducibility and maps to displayed bands. Its thresholds are pilot workflow controls, not scientific precision.

## Known limitations and technical debt

- Application-level append-only protection can be bypassed by raw database access, bulk updates, or privileged Admin actions; production database roles/tamper evidence are absent.
- Domain model `full_clean()` is called by services/tests but not automatically on every direct ORM write. Production mutations must stay behind services/forms and receive database constraints where practical.
- Reviewer references are strings, not authenticated staff identities.
- No outbox/domain-event model, background jobs, API, or concurrency load validation beyond state row locking/version semantics.
- No production encryption/key management for identifier ciphertext.
- No approved hard-deletion graph or retention executor.
- Local SQLite cannot prove every PostgreSQL concurrency behaviour; the configured CI job covers schema and tests on PostgreSQL once it runs successfully.
- Audit details are schema-light JSON and require event-contract versioning before broader use.
- Published-content immutability can be bypassed through raw SQL or queryset bulk updates; production publication permissions are absent.
- Evidence independence is represented by a stored key and needs source-specific anti-duplication policy.
- Evidence timestamps are retained, but recency is not weighted without dimension-specific research.
- Synthetic Urdu wording, reading level, accessibility, cultural interpretation, and assessment thresholds require human research and pilot validation.
- Synthetic career descriptions and mappings are architecture fixtures, not approved career content. Pakistan taxonomy ownership, completeness thresholds, source/licence policy, pathway/regulatory research, market sources, and refresh cadences remain unresolved.
- Import schema v1 covers taxonomy/profile identity and text only; field-level evidence bundle import and impact analysis need later schemas.

## Remaining blockers

- Minor/guardian consent and verification policy.
- Safeguarding playbook and staffed response.
- Retention, deletion, backup expiry, and production encryption policy.
- Production operator authentication, RBAC, MFA, access review, and incident response.
- Validated assessment instruments, approved Urdu adaptation, evidence sufficiency calibration, and confidence calibration. The implemented rules are synthetic pilot engineering controls only.
- Approved Pakistan career taxonomy/granularity, market/source research, profile completeness rules, career publication ownership, experiments, recommendations, and reviewer rubrics.
- Fee eligibility/approver and payment rules.
- WhatsApp, speech, AI, infrastructure, and pilot decisions.

The full classification is in `01_OPEN_DECISION_CLASSIFICATION.md`.

## Next milestone readiness

The repository is ready to begin Milestone 4 only after owner review confirms the Milestone 2 assessment snapshot and Milestone 3 career snapshot/version contracts. Recommended Milestone 4 is a deterministic, transparent recommendation engine using frozen inputs/configuration, multi-signal candidate generation, support/conflict/unknown explanations, separate capability and feasibility, confidence/review triggers, and immutable human overrides. It must not use AI, make unsupported market claims, or deliver unreviewed participant advice.
