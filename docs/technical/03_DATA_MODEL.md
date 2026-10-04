# Database Schema Plan

## Conventions

- PostgreSQL UUIDv7-compatible application-generated identifiers (or UUIDv4 until UUIDv7 support is standardised in the chosen stack); never expose sequential IDs externally.
- `created_at`, `updated_at`, and when relevant `valid_from`, `valid_to`, `version`, `status`, and `deleted_at`.
- Reference/definition data is versioned and immutable after publication.
- Enumerations that change with product learning use lookup/configuration tables; stable machine states may use constrained enums/checks.
- Foreign keys, unique constraints, check constraints, and transactions enforce invariants. JSONB is limited to provider envelopes, immutable snapshots, rubrics, and structured extensibility—not used to avoid relational design.
- Sensitive columns are tagged in schema documentation and protected with application-level envelope encryption where indicated.

## Core tables

### Participants, consent, and access

| Table | Important fields and constraints |
| --- | --- |
| `participants` | `id`, `preferred_language`, `life_stage_track`, age/DOB precision fields, `minor_policy_result`, education/current-status/geography references, `status`; check valid age precision; no phone number |
| `participant_contacts` | `participant_id`, `channel`, encrypted address, keyed lookup hash, verified state, primary flag; unique channel + lookup hash |
| `guardians` | internal ID and only minimum required encrypted identity/contact fields |
| `guardian_relationships` | participant, guardian, relationship, verification status, communication scope, active dates |
| `consent_records` | subject, participant/guardian actor, consent type, policy version, status, captured channel/time, evidence reference, withdrawn time; append-only status history |
| `communication_permissions` | participant/contact, purpose/channel, granted/withdrawn, source consent, allowed windows where configured |
| `referrals` | referred participant, pseudonymous referrer/source/campaign, date; no exposed referral contact list |

### Journey and conversation

| Table | Important fields and constraints |
| --- | --- |
| `participant_journeys` | participant, track, current state, state version, checkpoint, started/paused/completed timestamps; one active journey per participant unless explicitly supported later |
| `state_transitions` | journey, from/to, command, actor type/ID, policy version, reason, correlation ID; append-only |
| `conversations` | journey, channel, external thread reference (encrypted/tokenised), status |
| `messages` | conversation, direction, provider message ID, type, occurred/received time, body ciphertext or object reference, language, retention class, processing status; provider ID unique |
| `media_objects` | storage key, media type, size/hash, encryption key reference, malware-scan status, retention/delete dates; never public URLs |
| `inbound_events` / `outbound_messages` | provider IDs, event type, status, attempts, next attempt, correlation, minimal payload/reference; uniqueness for idempotency |

### Assessment and evidence

| Table | Important fields and constraints |
| --- | --- |
| `assessment_definitions` / `assessment_versions` | identifier, version, status, audience/language applicability, scoring/sufficiency config, publication record |
| `dimensions` | stable dimension code, category (trait, interest, ability, potential, value, environment, constraint, behaviour), description; no collapsing categories |
| `assessment_items` / `item_variants` | version, target dimensions, response type, Urdu text, education/age variant, scoring keys, provenance/licence |
| `assessment_sessions` | journey, assessment version, status, started/completed, sufficiency result |
| `item_presentations` | session, item variant, order, selection reason/config version |
| `responses` | presentation, source message, structured value, narrative reference, interpretation status, actor/time |
| `evidence_items` | journey, dimension, evidence class/source type, source record ID, direction/strength, confidence value + band, reliability, observed time, interpretation method/version, status, privacy class |
| `evidence_derivations` | derived evidence, parent evidence, transformation/prompt/rule version; creates a lineage DAG and prevents circular derivation |
| `dimension_estimates` | session/snapshot, dimension, score/range, confidence/band, supporting/conflicting counts, calculation version; immutable per snapshot |
| `contradictions` / `contradiction_members` | description/category, severity, resolution status, linked evidence, reviewer/resolution |
| `evidence_sufficiency_results` | scope/dimension, status, policy version, reasons, missing evidence classes, evaluated time |

Scores use a bounded numeric range only after the versioned instrument defines it. Provisional `0–100` interpretations in the brain remain research hypotheses, not hard-coded universal meaning.

### Career intelligence

| Table | Important fields and constraints |
| --- | --- |
| `career_taxonomies` / `career_taxonomy_versions` | scope, geography, version, status, provenance |
| `career_clusters` | taxonomy version, code, names/descriptions by language |
| `career_profiles` | taxonomy version, stable career code, cluster, title, description, status/granularity |
| `career_signal_requirements` | career profile, dimension, desired range/shape, importance, evidence basis, config version |
| `education_pathways`, `skill_requirements`, `entry_routes` | career mapping, geography, prerequisites, time/cost ranges, evidence/source links |
| `research_sources` | source class, publisher, title/URL/reference, geography, accessed/published dates, licence, limitations, confidence |
| `market_observations` | career, geography, evidence type, period, numeric range/unit or finding, source, confidence, observed/expiry/refresh dates, status including `unknown` |
| `career_profile_revisions` | prior/new version, rationale, approver, evidence links |

### Experiments and recommendations

| Table | Important fields and constraints |
| --- | --- |
| `experiment_definitions` / `experiment_versions` | target careers/clusters/dimensions, instructions, resource/device/language needs, duration, rubric, review rule, accessibility/bias notes |
| `experiment_assignments` | journey, version, selection reason, due/status/reminders |
| `experiment_submissions` | assignment, text/media references, submitted time, participant reflection |
| `experiment_observations` | submission, rubric criterion/dimension, value, confidence, observer type/version; may create linked evidence |
| `experiment_reviews` | reviewer, decision, rubric result, notes, time |
| `recommendation_runs` | journey, assessment snapshot, taxonomy/config/prompt versions, status, input hash, created time |
| `recommendation_options` | run/version, career/cluster, rank, overall score/range, confidence, fit category, route/tradeoff/next-action structured references |
| `recommendation_component_scores` | option, component type (interest/strength/personality/value/environment/constraint/experiment/market), raw/weighted result, weight/config, missingness treatment |
| `recommendation_evidence_links` | option, evidence/market observation, relation (`supports`, `conflicts`, `feasibility`, `uncertainty`), contribution, explanation |
| `recommendation_reviews` | run/version, reviewer, decision, reason, required-next-evidence, time |
| `recommendation_overrides` | original option/rank, replacement/change, reason code/narrative, reviewer, outcome-follow-up link when available |

### Operations, learning, and governance

`review_cases`, `review_decisions`, `safety_cases`, `fee_assessments`, `fee_decisions`, `payment_records`, `follow_up_plans`, `follow_up_attempts`, `outcome_observations`, `observations`, `hypotheses`, `knowledge_rules`, `rule_promotion_decisions`, `prompts`, `prompt_versions`, `workflow_versions`, `policy_versions`, `content_templates`, `staff_users`, `roles`, `role_assignments`, `audit_events`, `scheduled_jobs`, and `outbox_events` complete the operational model.

## Privacy classes and separation

Classify data as:

1. Operational identifiers: participant ID, stage, timestamps.
2. Direct identifiers: phone, name, guardian contact—encrypted and isolated.
3. Sensitive narrative: raw messages, transcripts, family/financial context, safety notes—encrypted, restricted, short retention where possible.
4. Structured guidance evidence: dimensions and observations—pseudonymous and access-scoped.
5. Public/reference: published career content and non-personal configuration.

Use separate encryption keys/key scopes for direct identifiers, raw content/media, and highly sensitive safety/financial fields. Backups inherit the highest contained classification.

## Deletion and retention mechanics

Retention durations are unresolved policy decisions. The schema must nevertheless support `retention_class`, `retain_until`, legal/operational hold, consent basis, deletion request, deletion job, and deletion outcome. Deletion proceeds through a documented graph:

- Disable communication and revoke tokens first.
- Remove direct contact mappings and raw media/messages according to policy.
- Remove or irreversibly deidentify structured records unless a documented lawful/consented retention basis applies.
- Retain minimal financial/audit records only where required, with identifiers minimised.
- Record the deletion action without retaining deleted content.
- Document backup expiry; do not promise immediate physical removal from immutable backups.

## Indexing, partitioning, and analytics

- Index active journeys by state, review cases by type/status/priority/age, jobs/outbox by due status, contact lookup hash, messages by provider ID, evidence by journey/dimension/status, market observations by career/geography/type/expiry.
- Start without partitioning; consider monthly partitions for messages, audit events, provider events, and job history only after measured growth.
- Use read-only SQL views/materialized views for funnel and quality metrics. Keep group sizes/privacy thresholds for fairness reports.
- Do not create a separate analytics warehouse for MVP. Export only deidentified aggregates if later required.

## Migration discipline

All schema changes are reviewed migrations. CI tests forward migration from an empty database and from a representative previous schema, validates constraints, and detects accidental destructive operations. Production uses expand/migrate/contract steps with backup and rollback/forward-fix plans. Reference-data imports are versioned, validated, and approved separately from code deploys.
