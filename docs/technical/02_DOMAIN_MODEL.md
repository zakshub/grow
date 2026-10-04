# Domain Model

## Modelling principles

- A participant is a person in a journey, not a WhatsApp number. Contact identifiers are replaceable, protected mappings.
- A state is explicit and transitioned by commands with guards; it is not inferred from chat history.
- Evidence is an append-only claim or observation with source, dimension, confidence, provenance, and time. Scores are derived estimates, not truth.
- Interest, demonstrated ability, learning potential, values, preferences, constraints, behaviour, and market evidence remain distinct.
- Unknown and contradictory are valid states.
- Recommendations and reviews are immutable, versioned artifacts. New knowledge produces a new version, not a rewrite of history.
- Financial access never contributes to capability or fit.

## Aggregates and key entities

### Participant aggregate

`Participant` owns a stable internal ID, status, preferred language, life-stage track, age/date-of-birth precision, education/current-status profile, geography, communication preferences, and timestamps. Sensitive contact details live in `ParticipantContact`. `GuardianRelationship`, `ConsentRecord`, and `CommunicationPermission` determine whether work may proceed.

Invariants:

- No assessment/discovery processing before required active consent.
- A participant classified as requiring guardian action cannot pass the consent gate without the configured guardian requirement.
- Opt-out blocks non-essential participant messaging immediately, independent of queue state.
- Parent/guardian context never replaces participant-authored evidence without explicit attribution.

### Journey aggregate

`ParticipantJourney` represents one career-discovery episode and owns current state, state version, audience track, started/paused/completed timestamps, current workflow checkpoint, and reason codes. A participant may have later journeys/reassessments without overwriting the prior journey.

`StateTransition` records requested command, from/to state, actor, policy/rule version, reason, and timestamp.

### Conversation aggregate

`Conversation`, `Message`, `MediaObject`, and `ConversationCheckpoint` preserve channel interaction. Raw text/transcripts and media use separate privacy/retention classes. A structured evidence item references its source message or submission but remains usable according to its own policy after raw-source deletion only when policy and consent permit.

### Assessment aggregate

`AssessmentDefinition` and immutable `AssessmentVersion` contain dimensions, items, age/education/language variants, scoring rules, and sufficiency policy. `AssessmentSession` owns presented items, responses, status, and the versions used.

`EvidenceItem` represents self-report, structured response, behavioural example, task observation, reviewer observation, follow-up, or derived interpretation. `DimensionEstimate` is a versioned projection over evidence. `Contradiction` links conflicting evidence and resolution state. `EvidenceSufficiency` explains why a dimension/session is sufficient, insufficient, or review-required.

### Career intelligence aggregate

`CareerTaxonomyVersion` contains `CareerCluster` and `CareerProfile` entries. Profiles map requirements/preferences to dimensions through `CareerSignalRequirement`; they also link education/skill `Pathway`, practical experiments, and versioned `MarketObservation` records backed by `ResearchSource`.

Market unknowns are explicit missing/unknown observations, never default zeros.

### Experiment aggregate

`ExperimentDefinitionVersion` contains target clusters/dimensions, instructions, accessibility variants, expected duration, required resources, rubric, review policy, and known bias risks. `ExperimentAssignment`, `ExperimentSubmission`, `ExperimentObservation`, and `ExperimentReview` record the participant trial. Observations become evidence only with attribution and confidence.

### Recommendation aggregate

`RecommendationRun` freezes all inputs and configuration. `RecommendationVersion` contains ranked `RecommendationOption` records. Each option links `RecommendationEvidenceLink` records as support, conflict, feasibility, or uncertainty; component scores; market observations; education route; tradeoffs; next experiment/action; and confidence/calibration version.

`RecommendationReview` records approve, request-evidence, or override. An override creates a new reviewed version or explicit decision layer and must retain the system proposal and reason.

### Review and safety aggregate

`ReviewCase` has type, priority, status, reason, required role, SLA target, summary, and linked domain records. `ReviewDecision` is append-only. Safety cases are segregated and expose only minimum necessary data. Product configuration determines which decisions are always human; during MVP all final recommendations are.

### Fees and payments aggregate

`FeeAssessment` captures minimal affordability inputs; `FeeDecision` records standard/reduced/free/review-required plus human approver where required. `PaymentRecord` records provider/reference/status/amount without unnecessary payment credentials. These entities cannot be queried by recommendation scoring services.

### Follow-up, referral, and learning

`FollowUpPlan`, `FollowUpAttempt`, and `OutcomeObservation` track 7-day/30-day MVP actions and later outcomes. `Referral` attributes sources without disclosing referrer private data. `Observation`, `Hypothesis`, `KnowledgeRule`, and `RulePromotionDecision` implement the product brain's observation → hypothesis → promoted-rule discipline.

### Identity, audit, and configuration

`StaffUser`, `Role`, and scoped assignments control operator access. `AuditEvent` records sensitive actions. Versioned `Policy`, `Prompt`, `WorkflowDefinition`, `ScoringConfiguration`, and `ContentTemplate` make product logic reproducible.

## Human authority matrix

| Decision | Automation role | Required human authority |
| --- | --- | --- |
| Consent/guardian requirement | Enforce configured deterministic rule | Legal/operational owners approve the rule before activation |
| Final MVP recommendation | Propose and explain | Career reviewer approves or overrides |
| Reduced/free access | Gather and propose | Access reviewer decides according to approved policy |
| Safeguarding response | Detect/route only | Safeguarding reviewer follows approved playbook |
| Permanent programme rejection | Assemble evidence | Authorised human decides and records reason |
| Assessment weight/rule change | Simulate and report | Product/research review publishes a new version |
| Knowledge promotion | Surface repeated observations | Designated review approves hypothesis/rule |

## Domain events

Important events include `ParticipantCreated`, `ConsentRecorded`, `GuardianActionRequired`, `ParticipantOptedOut`, `JourneyTransitioned`, `EvidenceAdded`, `ContradictionOpened`, `EvidenceSufficiencyChanged`, `ExperimentAssigned`, `ExperimentSubmitted`, `RecommendationProposed`, `ReviewRequested`, `RecommendationApproved`, `RecommendationOverridden`, `FeeDecided`, `FollowUpDue`, `OutcomeRecorded`, and `SafetyEscalated`.

Events are transactional outbox records. Consumers must be idempotent. Events contain internal IDs and minimum necessary metadata, never phone numbers or raw narrative by default.
