# WhatsApp Operating Model

## Principle

WhatsApp is the primary participant interface.

Participants should not need to learn a new application for the core Grow experience.

The system should feel like a guided conversation with clear stages, not an endless chat.

## Why WhatsApp

1. Low participant friction
2. Familiar interaction model
3. Strong mobile accessibility
4. Voice message support
5. Easy referrals
6. Suitable for reminders and follow up
7. Works across a wide range of device quality

## Channel boundary

Grow can self host its application logic, database, analytics, assessment engine, workflow orchestration, and administration tools.

WhatsApp message transport should use the official WhatsApp Business Platform.

Do not build the core business on browser automation, unofficial session scraping, or fragile workarounds that can break platform rules or participant trust.

## Conversation states

Every participant should have a known state.

Suggested states:

1. New contact
2. Consent pending
3. Profile incomplete
4. Discovery in progress
5. Assessment in progress
6. Experiment pending
7. Experiment submitted
8. Human review required
9. Recommendation ready
10. Roadmap active
11. Follow up due
12. Completed
13. Paused
14. Opted out

The state engine prevents the system from asking random or repeated questions.

## Message design

Participant messages should generally be:

1. Short
2. One clear action at a time
3. Natural Urdu
4. Easy to answer by text or voice
5. Explicit when a longer response is useful
6. Respectful of low literacy or low confidence

## Voice support

Voice should be a first class input method.

Suggested flow:

1. Receive voice note
2. Transcribe
3. Preserve original audio according to retention policy
4. Interpret answer
5. Ask follow up when transcription or meaning is uncertain
6. Store structured evidence separately from raw conversation

## Adaptive conversation

The system should decide the next question from:

1. Current stage
2. Missing evidence
3. Contradictions
4. Education level
5. Age and minor status
6. Previous answers
7. Confidence in current hypotheses

Do not force every participant through the same long questionnaire.

## Progress visibility

The participant should periodically receive simple progress messages.

Example structure:

1. Basic profile complete
2. Discovery complete
3. Assessment in progress
4. One practical task remaining
5. Recommendation under review

## Reminder logic

Possible reminder categories:

1. Incomplete onboarding
2. Assessment continuation
3. Practical task due
4. Interview reminder
5. Payment reminder
6. Follow up reminder
7. New cohort reminder

Reminder frequency should be conservative.

Repeated silence should eventually move the participant to paused rather than trigger endless automated contact.

## Human handoff

When escalation is required, the system should create a concise operator summary containing:

1. Participant stage
2. Reason for escalation
3. Relevant evidence
4. Questions already asked
5. What decision is needed
6. Suggested next action

The human should not need to reread the entire conversation unless necessary.

## Operator return

After the human acts, the system should:

1. Record the decision
2. Resume the correct workflow
3. Explain the next step to the participant
4. Preserve the reason for future learning when appropriate

## Referral flow

A participant can receive a simple referral invitation.

The referred person should start their own conversation and consent independently.

Track the referral source without exposing private participant information.

## WhatsApp message categories

Maintain approved operational templates for use cases such as:

1. Continue assessment
2. Interview reminder
3. Practical task reminder
4. Recommendation ready
5. Payment reminder
6. Follow up invitation
7. New programme invitation

Template content and platform rules should be reviewed against current WhatsApp policy before production deployment.

## Opt out

Participants must be able to stop automated messages easily.

The system should recognise clear opt out intent even when the exact wording varies.

## Failure handling

If the AI cannot understand a response:

1. Do not fabricate meaning
2. Ask a simpler clarification
3. Offer selectable options where helpful
4. Escalate after repeated failure

## Future operator console

Even though the participant channel remains WhatsApp, internal staff will eventually need a web console for:

1. Queue management
2. Participant review
3. Assessment evidence
4. Recommendation approval
5. Fee decisions
6. Safeguarding escalation
7. Analytics
8. Content and rule management
9. Template management
10. System health

The participant experience can remain WhatsApp first while the operator experience becomes purpose built.
