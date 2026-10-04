# Implementation Handoff

## Purpose

This document tells Codex or any future implementation agent how to start building Grow without reinterpreting the product from scratch.

## Read first

Before changing architecture or product behaviour, read in this order:

1. `README.md`
2. `BRAIN.md`
3. `docs/01_PRODUCT_VISION.md`
4. `docs/02_AUDIENCE_AND_SCOPE.md`
5. `docs/03_CAREER_DISCOVERY_ENGINE.md`
6. `docs/04_ASSESSMENT_MODEL.md`
7. `docs/05_PARTICIPANT_JOURNEY.md`
8. `docs/09_DATA_PRIVACY_AND_SAFETY.md`
9. `docs/10_SYSTEM_ARCHITECTURE.md`
10. `docs/12_MVP_BUILD_PLAN.md`
11. `docs/13_ROADMAP.md`
12. `docs/17_FEATURE_INVENTORY.md`

## Implementation rule

Do not begin by building a large AI chatbot.

Build the product state, evidence model, assessment structure, and human review path first.

AI assists the system. AI is not the system architecture.

## Recommended first engineering milestone

Create a local development foundation that can represent one participant moving through the complete MVP state machine without connecting WhatsApp yet.

### Required outputs

1. Application skeleton
2. Database schema
3. Participant entity
4. Consent entity
5. Guardian entity
6. Referral entity
7. Conversation state entity
8. Assessment session
9. Evidence item
10. Assessment dimension
11. Career cluster
12. Career profile
13. Recommendation
14. Practical experiment
15. Human review
16. Fee decision
17. Follow up
18. Audit event

## Suggested implementation sequence

### Milestone 1: Domain model

Build the core entities and state transitions.

Acceptance criteria:

1. A synthetic participant can be created
2. Minor status can trigger guardian requirements
3. Participant state transitions are explicit
4. Assessment evidence can be stored with confidence and source
5. No identifiable test data is committed

### Milestone 2: Assessment engine

Build a deterministic assessment shell before advanced AI adaptation.

Acceptance criteria:

1. Questions belong to dimensions
2. Answers produce evidence
3. Evidence has confidence
4. Contradictions can be recorded
5. Completion is based on evidence sufficiency rather than only question count

### Milestone 3: Career intelligence model

Build career profiles and matching inputs.

Acceptance criteria:

1. Careers map to traits, interests, values, and environment preferences
2. Career data supports geography and freshness
3. Market evidence can be unknown
4. Salary data is represented as sourced ranges, not guarantees

### Milestone 4: Recommendation engine

Build transparent recommendation logic.

Acceptance criteria:

1. Returns multiple ranked options
2. Shows supporting evidence
3. Shows conflicting evidence
4. Shows confidence
5. Supports human override
6. Logs override reason

### Milestone 5: Practical experiments

Build experiment assignment and result capture.

Acceptance criteria:

1. Experiment belongs to one or more career clusters
2. Submission can generate evidence
3. Human review can be required
4. Recommendation can change after experiment evidence

### Milestone 6: Operator review

Build the smallest internal interface needed to review cases.

Acceptance criteria:

1. Reviewer sees participant stage
2. Reviewer sees evidence summary
3. Reviewer sees proposed recommendations
4. Reviewer can approve or override
5. Reviewer can make fee decision
6. Reviewer can escalate safety concerns

### Milestone 7: WhatsApp integration

Only after the domain workflow works locally.

Acceptance criteria:

1. Incoming message maps to participant
2. Workflow state determines response
3. Opt out works
4. Message failures are logged
5. Voice input has a defined transcription path
6. Platform templates are separated from free form conversational content

### Milestone 8: Automation and follow up

Add:

1. Reminders
2. Scheduled follow ups
3. Referral attribution
4. Daily report
5. Weekly learning report

## Technical selection rule

Do not choose a framework merely because it is fashionable.

Choose technology that supports:

1. Reliable webhooks
2. Relational data integrity
3. Background jobs
4. Auditability
5. Simple VPS deployment
6. Good testability
7. Low operating complexity

## AI provider rule

Create an internal adapter from the first implementation.

The application should not scatter provider specific calls throughout business logic.

Potential abstract capabilities:

1. Generate structured interpretation
2. Summarise participant evidence
3. Generate adaptive follow up question
4. Draft participant explanation
5. Classify free text answer
6. Transcribe speech through a separate speech interface

## Prompt rule

Prompts are product logic and should be versioned.

Store:

1. Prompt identifier
2. Version
3. Purpose
4. Expected structured output
5. Test cases
6. Failure examples

## Testing requirements

At minimum test:

1. State transitions
2. Minor guardian requirements
3. Consent blocking
4. Assessment scoring
5. Contradiction recording
6. Recommendation ranking
7. Unknown market evidence
8. Human override
9. Opt out
10. Fee decision separation from career capability

## Synthetic data rule

All committed fixtures must be synthetic.

Do not paste real WhatsApp transcripts into tests.

## Documentation rule

When implementation reveals that a product assumption is wrong:

1. Do not silently code around it
2. Record the conflict
3. Update the relevant canonical document
4. Record the decision
5. Then implement the new rule

## First Codex task

When development begins, the first task should be:

Read the entire Grow product brain, inspect the empty or current codebase, propose a minimal technical architecture for the MVP, list unresolved technical decisions, define the domain schema and state machine, and create an implementation plan. Do not start feature coding until the plan has been reviewed against the product brain.

## Definition of done for the foundation

The foundation is ready for real feature implementation when a developer can answer all of the following from the repository without asking the product owner to repeat the concept:

1. Who Grow serves
2. What problem it solves
3. How career discovery works
4. How assessment works
5. How recommendations are formed
6. Where human review is required
7. How WhatsApp fits
8. What data must remain private
9. What the MVP contains
10. What the roadmap intentionally postpones
