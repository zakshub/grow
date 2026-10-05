# Milestone 3: Versioned Career Intelligence Registry

Last verified: 2026-10-05

## Scope and boundary

Milestone 3 describes careers independently from participants. It can state what a career is,
what work it may involve, which multi-dimensional signals are relevant, which routes and skills
are documented, what market observations exist, and where evidence is unknown, stale, or limited.

It does not match a participant to a career, rank careers, calculate fit, generate advice, or connect
an assessment snapshot to a career snapshot. It contains no external AI, WhatsApp, speech, scraping,
or automatic publication.

## Implemented schema

The `grow.careers` app implements:

- Stable and versioned taxonomy: `CareerTaxonomy`, `CareerTaxonomyVersion`, `CareerCluster`,
  `CareerFamily`, `CareerProfile`, and `CareerProfileVersion`.
- Version-pinned names and structure: `CareerAlias` and `CareerRelationship`.
- Multi-signal profile evidence: `CareerDimensionRelationship` links profile versions to the
  Milestone 2 dimension taxonomy; `CareerEnvironmentObservation` represents environment prevalence.
- Versioned routes and skills: `CareerSkill`, `CareerSkillRequirement`, and `CareerPathway`.
- Source and market evidence: `ResearchSource` and append-only `MarketObservation`.
- Human governance: append-only `CareerReviewDecision` plus audit events.
- Deterministic curation: `CareerImportBatch` and append-only `CareerImportDiff`.

All primary keys are random UUIDs. Careers are stable data rows rather than an enum, so the registry
can expand without code changes. Published content is protected by application-level immutability;
historical versions remain queryable.

## Taxonomy and profile lifecycle

Taxonomy and profile lifecycle is `DRAFT`, `PILOT`, `ACTIVE`, or `RETIRED`. Publication review is
separate: `DRAFT -> IN_REVIEW -> APPROVED -> PUBLISHED -> STALE/RETIRED`.

A reviewer reference and reason are mandatory. Each transition writes both a
`CareerReviewDecision` and minimal `AuditEvent`. Publication is rejected unless every profile in the
taxonomy has been approved. Publishing freezes taxonomy structure, aliases, relationships, profile
content, dimension links, environments, pathways, skills, and observations. Corrections require a
new taxonomy/profile/evidence version rather than history mutation.

`participant_recommendation_ready` is an explicit gate. Synthetic and reference-only profiles
cannot set it true. This milestone does not include any service that consumes that gate for matching.

## Dimension, interest, value, and environment relationships

`CareerDimensionRelationship` references the canonical `AssessmentDimension` record and stores:

- importance and minimum/typical relevance using `LOW`, `MODERATE`, `HIGH`, `VARIABLE`, or `UNKNOWN`;
- direction using relevant, potential tension, contextual, variable, or unknown semantics;
- confidence, source, limitations, relationship version, and review status;
- country, industry, seniority, employment model, and specialisation context.

The linked dimension category keeps cognitive/functional, work-style, communication/social,
creativity, vocational interest, and work-value evidence separate. A career can have several
interests and values. No link is a threshold or a deterministic claim of fit.

`CareerEnvironmentObservation` uses `COMMON`, `VARIABLE`, `RARE`, or `UNKNOWN`, with source,
confidence, limitations, context, and review status. Variation by organisation or specialisation is
preserved rather than collapsed into a universal claim.

## Skills and pathways

Skills use stable codes and categories for technical, domain, communication, analytical, creative,
digital, management, tools/platforms, and certifications. Profile requirements are versioned,
sourced, limitation-bearing, freshness-aware, and use `CORE`, `COMMON`, `SPECIALISATION`, `OPTIONAL`,
or `UNKNOWN`.

Pathways support degree, diploma, certification, skills-first, apprenticeship, self-taught,
portfolio, internship, entry-role, and career-switch routes. Each record includes geography,
education, linked skills, duration, cost category, prerequisites, next step, source and source date,
limitations, review date, validity/expiry, freshness, status, version, and optional supersession.

## Sources, market evidence, and freshness

The research registry supports government, labour-market, university, industry-report, job-board,
professional-body, education-provider, academic, primary-research, and other source types. It stores
title, publisher, URL/reference, dates, geography, methodology, limitations, licence notes, quality,
review, freshness/expiry, and supersession. It stores metadata and short notes, not source extracts.

Market observations support demand, salary ranges, entry difficulty, remote availability, freelance
relevance, automation exposure, international mobility, hiring concentration, and training
availability. Context includes country, province/region, city, remote/freelance flags, employment
type, industry, and seniority. Observations also retain source/date, structured value and unit,
confidence, limitations, validity window, expiry, review status, version, and supersession.

`UNKNOWN` is a distinct value state and rejects any value or unit. It is never converted to zero or
low demand. Known salary observations require a minimum, maximum, currency, and period, and reject
inverted ranges. No bundled fixture contains a salary or demand number.

Freshness is `CURRENT`, `STALE`, `RETIRED`, or `UNKNOWN`. Effective freshness is deterministic: an
expired current record is presented as stale without rewriting history. A replacement points to the
record it supersedes, so the earlier state remains reproducible.

## Import and diff workflow

The structured JSON `career-import-v1` path is intentionally narrow and deterministic:

1. Canonicalise and hash a staged payload.
2. Validate schema, required fields, duplicates, and unexpected fields.
3. Compare stable career codes with a pinned base taxonomy version.
4. Persist `NEW`, `CHANGED`, and `REMOVED` diffs without changing the base.
5. Require a named reviewer and reason to approve the diff.
6. Require a separate publish command, which creates and publishes a new immutable version.

Staging is idempotent by payload hash. Invalid imports are rejected. The importer has no network or
scraping capability and never silently updates the current version.

## Career snapshot

`build_career_snapshot` deterministically returns only career information: stable code/title,
profile/taxonomy version, strong and variable dimension descriptions, interests, values,
environment observations, pathways, skills, market records, effective freshness counts,
limitations, and the recommendation-readiness gate. Unknown values are retained. The service has no
participant, assessment session, matching, score, rank, or recommendation input.

## Synthetic reference pack

`load_synthetic_career_pack` idempotently loads 12 architecture examples:

1. Software Developer
2. Data Analyst
3. UX / Product Designer
4. Graphic Designer
5. Teacher
6. Sales / Business Development
7. Accountant
8. Research Assistant
9. Mechanical Technician
10. Digital Marketer
11. Nurse
12. Lawyer

They vary across technical, creative, social, business, practical, research, and regulated work.
Every profile is marked `SYNTHETIC`, `REFERENCE_ONLY`, and
`NOT_READY_FOR_PARTICIPANT_RECOMMENDATION`. Their profile statements are architecture fixtures, not
validated Pakistan career research. Their demand, remote, and salary observations are all unknown.

## Admin and audit

Django Admin provides read-only development inspection of taxonomies, profile versions, dimensions,
environments, skills, pathways, sources, market observations, stale/expiry fields, decisions, import
batches, and diffs. It is not a production authoring or authorisation interface. Publication, review,
and import approval use services and create audit records.

## Limitations and research blockers

- The synthetic taxonomy does not establish pilot taxonomy breadth or granularity.
- No profile mapping, source, pathway, regulatory statement, labour-market observation, salary range,
  or Pakistan geography claim is approved for participant use.
- Pakistan research ownership, source/licence policy, completeness threshold, refresh cadence, and
  career-review rubric remain unresolved.
- HEC, NAVTTC, PBS, provincial authorities, universities, professional bodies, and market sources are
  future research candidates only; this milestone did not ingest their data.
- Admin reviewer references are strings; production staff authentication, RBAC, and MFA are absent.
- Application immutability can be bypassed by privileged raw SQL or queryset updates; production
  database roles and tamper controls remain required.
- Import v1 covers taxonomy/profile identity and text only. Field-level source bundles, geography
  dictionaries, units/currencies, skill/pathway imports, and impact reports need later schemas.
- Freshness cadence is stored but not inferred by evidence type because no approved cadence exists.

## Acceptance boundary

Milestone 3 acceptance establishes an inspectable, versioned, sourced, unknown-preserving career
registry using synthetic reference material. It does not authorise participant recommendations or
production career claims. Milestone 4 may consume immutable assessment and career snapshots only
after its transparent multi-signal algorithm, configuration, review triggers, and tests are approved.
