# Automation Blueprint

## Objective

Automate repetitive operations while preserving human judgement for sensitive, ambiguous, or high consequence decisions.

## Automation principle

Automation should reduce operator effort without reducing participant dignity, safety, or recommendation quality.

## Fully automatable workflows

### Lead intake

1. Receive incoming WhatsApp message
2. Identify new or returning participant
3. Record acquisition source when available
4. Create participant record
5. Start consent flow

### Basic profile

1. Collect name
2. Collect age
3. Collect education level
4. Collect location
5. Collect study or work status
6. Detect minor status
7. Collect language preference

### Career discovery conversation

1. Ask adaptive questions
2. Extract evidence from answers
3. Detect missing information
4. Detect contradictions
5. Request clarification
6. Maintain progress state

### Assessment

1. Select next assessment item
2. Score structured items
3. Store evidence by dimension
4. Estimate confidence
5. Stop unnecessary questioning once evidence is sufficient

### Practical experiments

1. Select suitable experiment
2. Send instructions
3. Send reminder
4. Receive submission
5. Extract observable evidence
6. Queue for human review when subjective judgement is important

### Recommendations

1. Generate candidate career clusters
2. Calculate fit signals
3. Attach supporting evidence
4. Identify tradeoffs
5. Attach current market evidence when available
6. Generate participant friendly explanation
7. Route to human review according to confidence and pilot rules

### Follow up

1. Schedule follow up
2. Ask whether the participant acted
3. Capture outcome
4. Detect recommendation mismatch
5. Offer next step

### Referrals

1. Invite satisfied participants to refer suitable people
2. Generate referral identifier
3. Attribute incoming participant
4. Measure downstream quality

### Reporting

1. Daily funnel summary
2. Weekly source summary
3. Assessment completion summary
4. Human review queue summary
5. Fee summary
6. Dropout summary
7. Outcome summary

## Human in the loop workflows

Human review should remain required for:

1. Free access approval
2. Reduced fee exceptions
3. Safeguarding issues
4. Sensitive minor cases
5. Permanent programme rejection
6. Fraud suspicion
7. Very low confidence recommendation
8. Major contradiction between assessment and observed behaviour
9. Participant complaint about recommendation
10. New assessment rule promotion

## Escalation model

Each escalation should include:

1. Reason
2. Urgency
3. Participant stage
4. Concise evidence summary
5. Relevant conversation excerpts
6. Decision required
7. Suggested options

## Automation confidence

Each automated decision should have one of four states.

### Deterministic

Rule based and safe to execute automatically.

Example: participant under required age threshold needs guardian flow.

### High confidence

AI or scoring result is well supported and can proceed with logging.

### Review recommended

Evidence is mixed and human review improves quality.

### Review required

System must not proceed without human action.

## Reminder automation

Suggested reminders:

1. Incomplete profile
2. Incomplete assessment
3. Practical task due
4. Scheduled interview
5. Recommendation ready
6. Payment due
7. Follow up due

Reminder logic should stop after a small number of attempts.

## Operator workload goal

The mature system should allow one operator to focus on exceptions rather than routine conversation.

The operator should primarily handle:

1. Sensitive cases
2. Ambiguous career interpretation
3. Access decisions
4. Safeguarding
5. Quality review
6. System improvement

## Learning automation

The system may automatically produce weekly observations such as:

1. A question has unusually high dropout
2. One referral source produces stronger completion
3. One experiment poorly differentiates careers
4. One career recommendation appears too frequent
5. A region shows a different constraint pattern

These should enter a review queue as hypotheses.

They must not automatically become permanent product rules.

## Automation anti patterns

Do not automate:

1. Harassment through repeated messages
2. Automatic rejection based on one score
3. Poverty classification from weak evidence
4. Mental health diagnosis
5. Career certainty claims
6. Unreviewed changes to assessment weights
7. Bulk unsolicited WhatsApp outreach
8. Silent collection of unnecessary personal data

## End state

The intended mature workflow is:

Routine work is automated.

Sensitive judgement is escalated.

Every important action is auditable.

Every recommendation can explain its evidence.

Every learning rule is promoted deliberately.
