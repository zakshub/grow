# Milestone 2: Deterministic Assessment and Evidence Engine

Last verified: 2026-10-05

## Scope and boundary

Milestone 2 progressively records what Grow currently knows, how it knows it, how strong the evidence is, what conflicts, what remains unknown, and which assessment action is useful next.

It does not recommend careers. It contains no career ranking, fit percentage, salary or labour-market claim, AI/LLM interpretation, WhatsApp, speech transcription, diagnosis, personality type, IQ score, or psychometric-validity claim.

All bundled content and scenarios are synthetic pilot engineering material. They are not approved participant content.

## Implemented assessment architecture

`AssessmentDefinition` is the stable identity. `AssessmentVersion` freezes a numbered content release and its selection/calculation policy identifiers. Versions move explicitly through `DRAFT`, `PILOT`, `ACTIVE`, and `RETIRED`.

Sections, dimension requirements, items, and language/audience variants can be changed only while their version is draft. Once published, content mutation and deletion through model methods fail; a change requires a new version. Lifecycle changes are the only permitted published-version update and are audited.

`AssessmentSession` pins the exact version, definition code/version, audience, language, locale, and maximum item limit used. `AssessmentItemPresentation` preserves item, variant, sequence, selection reason, and selection-policy version. `AssessmentResponse` is append-only and stores structured or text input without rewriting history.

Legacy Milestone 1 assessment shells remain valid with a nullable version link. New sessions created through the Milestone 2 service must pin a pilot or active version.

## Dimension taxonomy

The synthetic catalog contains 81 pilot engineering dimensions across:

1. Cognitive / functional
2. Personality / work style
3. Communication / social
4. Creativity
5. Vocational interest
6. Work values
7. Work environment

The names follow the approved Milestone 2 request. They are independent dimensions, not personality types or career mappings. The bundled synthetic assessment version uses eight of them as required dimensions to exercise progressive selection without pretending that 81 dimensions form a validated instrument.

`AssessmentDimensionRequirement` configures whether a dimension is required, its priority, minimum independent-source count, and minimum source-type diversity for one assessment version.

## Item and content model

Supported deterministic item types are:

- `LIKERT`
- `BINARY`
- `SINGLE_CHOICE`
- `MULTI_CHOICE`
- `RANKING`
- `NUMERIC`
- `SHORT_TEXT`
- `LONG_TEXT`
- `SCENARIO_CHOICE`

Business logic contains no participant wording. `AssessmentItemVariant` stores canonical item linkage, variant version, language, locale, audience, education stage, prompt, helper text, answer labels, examples, content status, and provenance.

The synthetic pack provides Urdu-primary variants for Grade 8, Grade 10, Intermediate, University, Graduate, and adult-career-switcher contexts, plus an English general fallback. Urdu content is marked `SYNTHETIC_PILOT`; it is not represented as translated, reviewed, or validated content.

The five open-discovery prompts are stored as long-text items. Their responses are preserved as sensitive raw evidence with no normalized interpretation and are ineligible for deterministic aggregation until a reviewer adds a separate structured observation.

## Evidence model

Every new response evidence record links:

- Journey and participant indirectly through the journey
- Pinned assessment session/version
- Stable dimension and code
- Immutable source and response reference
- Raw structured or text value
- Optional deterministic normalized interpretation
- Direction, confidence, review status, context, method/version, privacy class, and time
- `DimensionEvidence` independence key and aggregation eligibility

Supported source types are `SELF_REPORT`, `STRUCTURED_QUESTION`, `OPEN_RESPONSE`, `PRACTICAL_TASK`, `HUMAN_OBSERVATION`, `BEHAVIOURAL_SIGNAL`, `HISTORICAL_EXAMPLE`, `FOLLOW_UP`, and `REVIEWER_JUDGMENT`. Legacy Milestone 1 source values remain readable.

Evidence corrections create a new append-only version through `mark_evidence_reviewed`; the original remains. A rejected version is excluded from future projections without being deleted.

## Sufficiency model

Each versioned dimension projection is one of:

| Status | Deterministic meaning |
| --- | --- |
| `UNKNOWN` | No evidence exists. This is never interpreted as a low signal. |
| `INSUFFICIENT` | Evidence exists but is ineligible, lacks required source diversity, or otherwise does not meet policy. |
| `TENTATIVE` | At least one eligible known signal exists but the independent-source/confidence requirement is not met. |
| `SUPPORTED` | Configured independence, source diversity, and at least moderate evidence confidence are present with no unresolved contradiction. |
| `CONTRADICTORY` | At least one unresolved contradiction exists for the dimension. |

The status describes evidence sufficiency, not the participant's permanent trait or ability. A dimension can remain `UNKNOWN` indefinitely.

`DimensionResult` is append-only and version-chained. It stores exact evidence IDs, counts, requirements, confidence inputs, calculation version, reasons, and next action. Re-evaluation creates a new result rather than modifying the previous projection.

## Confidence model

Confidence is an inspectable pilot workflow heuristic, not psychometric precision. The internal value is retained only to make deterministic branching reproducible.

Inputs are:

- Eligible evidence count
- Independent-source count, capped after three for diminishing returns
- Source-type diversity, capped after three types
- Presence of reviewed evidence
- Unresolved contradiction count, capped after two penalties

The pilot calculation is:

```text
0.20
+ 0.20 × independent sources (maximum 3)
+ 0.10 × additional source types (maximum 2)
+ 0.10 when reviewed evidence exists
- 0.25 × unresolved contradictions (maximum 2)
```

The value is clamped from 0.10 to 0.95. No eligible evidence produces `UNKNOWN` with no numeric value. Internal values below 0.45 map to `LOW`, values below 0.75 to `MODERATE`, and higher values to `HIGH`. Formula, inputs, and mapped band are stored with every result. These thresholds are engineering controls requiring pilot calibration before real use.

## Contradiction rules

The deterministic detector compares the latest non-superseded known evidence for the same dimension. Two normalized pilot polarity values are flagged when their product is at most `-0.25`. Existing evidence is never overwritten.

A contradiction stores dimension, evidence members, reason, severity, status, reviewer resolution, reviewer reference, and resolution time. Duplicate detection for the same evidence pair is idempotent. Resolution supports `RESOLVED` or `ACCEPTED_UNCERTAINTY`, preserves every linked evidence item, and creates an audit event.

An unresolved contradiction makes the dimension `CONTRADICTORY`, reduces confidence, and prioritises an applicable clarification item. If no clarification is available, or the item limit is reached, the engine requires human review.

## Adaptive selection rules

The selector returns exactly one of:

- `ASK_MORE`
- `SUFFICIENT`
- `HUMAN_REVIEW_REQUIRED`
- `UNKNOWN`

It operates as follows:

1. Require an in-progress session pinned to a version; otherwise return `UNKNOWN`.
2. Recompute the current snapshot from latest eligible evidence.
3. If the presentation maximum is reached, return `SUFFICIENT` only when all required dimensions are supported; otherwise require human review. Presented or skipped items still count toward participant burden.
4. Stop with `SUFFICIENT` as soon as all required dimensions are supported; optional dimensions do not prolong the session.
5. Exclude already presented items.
6. Prioritise contradiction, unknown, insufficient, then tentative dimensions while preserving configured dimension priority.
7. Prefer a clarification item for contradictory evidence.
8. Select a variant by requested language, audience, education stage, and locale; use English general content only as an explicit fallback.
9. If approved items are exhausted before sufficiency, require human review.
10. If items exist but no applicable variant exists, return `UNKNOWN` rather than silently using unsuitable wording.

Every persisted presentation records the decision reason and selection-policy version and creates an audit event.

## Participant assessment snapshot

`build_assessment_snapshot` returns:

- Known and unknown dimension counts
- Per-dimension sufficiency and confidence
- Supporting, conflicting, independent-source, and source-type counts
- Exact evidence IDs
- Unresolved contradiction counts
- Reasons and next action
- Overall completion and recommended next assessment action

The snapshot is an assessment/evidence projection only. It contains no career object or recommendation.

## Human review

Django Admin exposes assessment content, sessions, presentations, responses, observations, evidence, results, and contradictions for internal development inspection.

Services allow a reviewer to:

- Add a structured observation linked to a response or session
- Create a new evidence version with reviewed/rejected/clarification status
- Resolve or accept uncertainty on a contradiction
- Use the Milestone 1 human-review decision service to request more information

Publishing, starting sessions, presenting items, recording responses, adding observations, reviewing evidence, recording/resolving contradictions, evaluating sessions, and human-review decisions create audit events. Reviewer references remain pseudonymous strings because production authentication/RBAC is outside this milestone.

## Synthetic assessment pack

The idempotent `load_synthetic_assessment_pack` command creates:

1. Grade 8 learner unsure of interests
2. Matric learner with logical and investigative signals
3. Intermediate learner with creative and communication signals
4. University learner with conflicting preferences
5. Graduate unsure of direction
6. Adult career switcher
7. Highly contradictory self-report
8. Mostly unknown dimensions
9. Participant who stops early
10. Participant requiring assessment human review

It contains 81 dimensions, 14 items, Urdu audience/education variants, English fallbacks, synthetic responses, raw open discovery, contradiction examples, and review routing. It contains no names, contact details, real conversations, assessment results, or financial narratives.

## What is not implemented

- Validated assessment instruments, scores, norms, or calibration
- Approved Urdu content or linguistic/cognitive validation
- AI/NLP interpretation of text
- Practical-experiment execution
- Career taxonomy, matching, recommendations, rankings, percentages, or salaries
- Participant UI, APIs, WhatsApp, speech, payments, or production operator access
- Production minor/guardian rules

## Known technical debt and validation work

- Application immutability can be bypassed by raw SQL, privileged Admin, or queryset bulk updates; production database roles and publication controls are required.
- The confidence calculation and sufficiency thresholds are transparent pilot heuristics, not validated measures.
- Evidence independence currently relies on a stored key; future sources need explicit anti-duplication policies.
- Recency is preserved in evidence but not yet weighted because no dimension-specific expiry research exists.
- Assessment item sensitivity, accessibility, device fairness, reading level, Urdu wording, and cultural interpretation require research and cohort testing.
- Reviewer identity is not authenticated and Admin is not a production review interface.
- Legacy Milestone 1 shells may have no assessment-version or dimension foreign key; new services do not create such rows.
- PostgreSQL concurrency and constraint validation status is recorded in `00_CURRENT_STATE.md`.

## Milestone 2 acceptance

The engineering acceptance criteria pass when the repository quality gates reported in `00_CURRENT_STATE.md` are green. This establishes a deterministic synthetic assessment shell only; it does not authorise real participant use or any validity claim.
