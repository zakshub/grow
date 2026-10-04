# System Architecture

## Goal

Build Grow so the participant experience remains simple while the system behind it can become highly automated, self hosted where practical, auditable, and easy to evolve.

## Architectural principle

WhatsApp is the participant channel.

Grow owns the intelligence, state, data model, workflows, analytics, and administration layer.

## High level architecture

Participant

→ WhatsApp Business Platform

→ Webhook gateway

→ Conversation and workflow orchestrator

→ Participant state service

→ Assessment engine

→ Career discovery engine

→ Knowledge and evidence layer

→ Recommendation engine

→ Human review queue when required

→ Response composer

→ WhatsApp Business Platform

Supporting services:

1. Participant database
2. Analytics store
3. Payment records
4. Notification scheduler
5. Document and media storage
6. Audit log
7. Operator console
8. Research and market evidence service

## Self hosted boundary

A future VPS can host:

1. Application server
2. Database
3. Workflow service
4. Job scheduler
5. Queue
6. Analytics
7. Operator console
8. Assessment logic
9. Career matching logic
10. Prompt and model orchestration
11. Reporting
12. Audit services

WhatsApp transport should remain connected through the official WhatsApp Business Platform.

## Suggested logical services

### Identity and participant service

Responsibilities:

1. Participant identifier
2. Contact mapping
3. Age and minor status
4. Education profile
5. Language preference
6. Consent state
7. Referral source

### Conversation service

Responsibilities:

1. Incoming message handling
2. Conversation state
3. Message classification
4. Voice input pipeline
5. Next step routing
6. Opt out detection

### Assessment service

Responsibilities:

1. Question selection
2. Score estimation
3. Confidence estimation
4. Contradiction detection
5. Evidence storage
6. Assessment completion logic

### Career intelligence service

Responsibilities:

1. Career taxonomy
2. Career trait profiles
3. Education requirements
4. Market evidence
5. Earning evidence
6. Opportunity confidence
7. Practical experiment library

### Recommendation service

Responsibilities:

1. Candidate generation
2. Fit scoring
3. Tradeoff analysis
4. Confidence
5. Explanation generation
6. Next experiment selection

### Workflow service

Responsibilities:

1. Onboarding
2. Assessment progression
3. Experiment reminders
4. Human review
5. Fee review
6. Follow up
7. Referral

### Human review service

Responsibilities:

1. Review queue
2. Case summary
3. Recommendation override
4. Fee decision
5. Safety escalation
6. Reviewer notes

### Analytics service

Responsibilities:

1. Funnel metrics
2. Source quality
3. Assessment completion
4. Recommendation distribution
5. Experiment completion
6. Follow up outcomes
7. Cost and payment metrics

## Data model concepts

Core entities may include:

1. Participant
2. Guardian
3. Consent record
4. Conversation
5. Message
6. Assessment session
7. Assessment dimension
8. Evidence item
9. Career cluster
10. Career profile
11. Recommendation
12. Practical experiment
13. Experiment submission
14. Human review
15. Fee decision
16. Payment record
17. Referral
18. Follow up
19. Research source
20. Knowledge rule

## State machine

Participant state should be explicit rather than inferred from message history every time.

Possible states:

1. New
2. Consent pending
3. Profile active
4. Discovery active
5. Assessment active
6. Experiment pending
7. Review pending
8. Recommendation ready
9. Roadmap active
10. Follow up
11. Completed
12. Paused
13. Opted out

## AI architecture

AI should be used for tasks such as:

1. Natural language understanding
2. Adaptive follow up questions
3. Voice transcription integration
4. Evidence extraction
5. Contradiction detection assistance
6. Explanation drafting
7. Participant summaries
8. Operator summaries

Deterministic application logic should remain responsible for:

1. Consent requirements
2. State transitions
3. Required fields
4. Access permissions
5. Fee rules
6. Safeguarding routing
7. Data retention rules
8. Audit logging

## Model independence

Do not tightly couple the product to one AI provider.

Create an internal interface for:

1. Text reasoning
2. Classification
3. Summarisation
4. Embeddings if later required
5. Speech transcription

This allows provider changes without rewriting the product.

## Career market data

Market information should be stored with:

1. Source
2. Geography
3. Observation date
4. Confidence
5. Career mapping
6. Evidence type

Do not let stale salary or demand claims silently survive for years.

## Security baseline

Production architecture should include:

1. HTTPS
2. Secret management
3. Database access control
4. Encrypted backups
5. Operator authentication
6. Role based access
7. Audit logs
8. Rate limiting
9. Input validation
10. Monitoring
11. Error tracking
12. Regular dependency updates

## Deployment evolution

### Early pilot

Minimal application plus managed external services where useful.

### Controlled pilot

VPS hosted application and database with official WhatsApp integration.

### Growth

Separate queues, workers, analytics, and operator services when volume requires them.

### Scale

Only introduce infrastructure complexity when measured load or reliability demands it.

## Architecture rule

Do not build distributed complexity before product logic is validated.

A simple modular system serving real participants is better than an elaborate architecture built around untested assumptions.
