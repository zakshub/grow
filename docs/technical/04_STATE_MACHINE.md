# Participant State Machine

## Design

The participant journey is an explicit, persisted state machine. A transition occurs only through a named command, validated guard, transaction, state-version check, transition record, and domain event. Message text never changes state directly.

The canonical documents use slightly different labels; this plan normalises them without changing the journey.

```text
NEW
 -> CONSENT_PENDING
 -> PROFILE_INCOMPLETE
 -> DISCOVERY_IN_PROGRESS
 -> ASSESSMENT_IN_PROGRESS
 -> EXPERIMENT_PENDING
 -> EXPERIMENT_SUBMITTED
 -> HUMAN_REVIEW_REQUIRED
 -> RECOMMENDATION_READY
 -> ROADMAP_ACTIVE
 -> FOLLOW_UP_DUE
 -> COMPLETED

Any active state -> PAUSED -> prior resumable state
Any contactable state -> OPTED_OUT
Any state with safety signal -> safety case + controlled workflow hold/route
```

`PROFILE_ACTIVE` in the high-level architecture is represented by successful completion of `PROFILE_INCOMPLETE` and entry into discovery. `REVIEW_PENDING` is `HUMAN_REVIEW_REQUIRED`. A recommendation may cycle back to assessment or experiment when more evidence is required.

## States and entry criteria

| State | Meaning | Entry criteria | Normal exit |
| --- | --- | --- | --- |
| `NEW` | Contact/event known, no active journey | Deduplicated inbound contact; minimal record | Begin consent explanation |
| `CONSENT_PENDING` | Participation/processing permission incomplete | Required policy identified | Active consent plus guardian requirement satisfied |
| `PROFILE_INCOMPLETE` | Consent valid; minimal context missing | Consent gate passed | Required, minimised profile complete |
| `DISCOVERY_IN_PROGRESS` | Story-based discovery underway | Profile sufficient | Discovery evidence/sufficiency policy permits assessment |
| `ASSESSMENT_IN_PROGRESS` | Structured/adaptive evidence gathering | Applicable assessment version assigned | Core evidence sufficient or review required |
| `EXPERIMENT_PENDING` | One or more practical trials assigned | Eligible experiment version selected and explained | Submission received, waived by reviewer, or return for alternative |
| `EXPERIMENT_SUBMITTED` | Submission awaits interpretation/review | Valid submission captured | Observations/evidence captured and required review completed |
| `HUMAN_REVIEW_REQUIRED` | System must not advance without role-authorised action | Review trigger and summary created | Approve recommendation, request evidence/experiment, safety route, or other decision |
| `RECOMMENDATION_READY` | Approved recommendation may be delivered | Mandatory MVP career review approved | Participant receives/acknowledges; enter roadmap |
| `ROADMAP_ACTIVE` | Participant has evidence-based next actions | Approved recommendation delivered | Follow-up scheduled/due or journey ended by policy |
| `FOLLOW_UP_DUE` | A scheduled check-in is actionable | Due date and communication permission | Outcome recorded; reschedule, revise, or complete |
| `COMPLETED` | Initial journey complete | Required outputs/follow-up condition met | New reassessment creates a new journey; does not rewrite this one |
| `PAUSED` | Temporarily inactive, progress preserved | Participant request, reminder exhaustion, operational hold | Resume to recorded state after guard recheck |
| `OPTED_OUT` | Automated contact stopped | Clear opt-out intent or manual action | Only explicit opt-in under approved policy; no marketing/reminders |

## Transition guards

Minimum guards:

- Consent: required participant consent active; guardian consent/verification only according to the approved age/legal policy. The exact threshold is not yet defined.
- Profile: only required fields for the selected track; unknown values may be allowed when not safety-critical.
- Discovery/assessment: applicable language and education variant exists; no expired consent or safety hold.
- Sufficiency: evaluated against a versioned policy using evidence diversity, quality, recency, confidence, and unresolved contradictions—not question count alone.
- Experiment: accessible for the participant's device, language, education level, time, and constraints; an alternative path exists.
- Recommendation: frozen evidence snapshot, explicit missing/unknown market evidence, no blocking contradiction, and required review case.
- Delivery: recommendation review approved, consent/communication valid, participant not opted out.
- Fee: fee access is an independent workflow and must never alter fit scores. Product owners must decide where payment gates delivery.

## Commands

Representative commands are `start_consent`, `record_consent`, `request_guardian_action`, `complete_profile`, `record_discovery_answer`, `start_assessment`, `record_response`, `evaluate_sufficiency`, `assign_experiment`, `submit_experiment`, `complete_experiment_review`, `propose_recommendation`, `request_review`, `approve_recommendation`, `override_recommendation`, `deliver_recommendation`, `activate_roadmap`, `record_follow_up`, `pause`, `resume`, `opt_out`, and `open_safety_case`.

Each command declares permitted states, actor/role, guard failures, idempotency key, audit class, and emitted events.

## Parallel sub-workflows

The top-level journey state does not overload orthogonal concerns:

- `consent_status`: pending, active, withdrawn, expired, superseded.
- `guardian_status`: not-required, requirement-unresolved, pending, verified/consented, declined, expired.
- `fee_status`: not-assessed, standard, reduced-pending/reviewed, free-pending/reviewed, payment-pending, paid, waived.
- `safety_status`: none, triage, review-required, active, referred, closed.
- `communication_status`: active, paused, opted-out, channel-failed.
- `review_status`: none, queued, claimed, awaiting-information, decided.

Transitions consult these statuses through guards. Safety policy may pause ordinary workflow without erasing its resumable state.

## Failure and recovery

- Duplicate webhook/command: return prior result via idempotency key.
- Concurrent responses: optimistic state version rejects stale transition; messages remain stored for ordered reprocessing/review.
- Worker/provider failure: retry with exponential backoff and dead-letter review; never advance state on an unconfirmed side effect.
- Reminder exhaustion: move to `PAUSED`, preserve progress, stop contact.
- Unclear message/transcript: stay in state, ask a simpler clarification; escalate after configured attempts.
- Rule/version change during journey: continue pinned version unless safety/legal correction requires an explicit migration decision.

## Acceptance invariants

1. No route bypasses consent or an applicable guardian guard.
2. Every state change has actor, reason, old/new state, policy/version, and timestamp.
3. Opt-out suppresses queued non-essential messages before send.
4. Assessment completion records sufficiency reasons and unresolved contradictions.
5. Every MVP recommendation passes human review before delivery.
6. Pausing/resuming and provider retries are idempotent and preserve progress.
