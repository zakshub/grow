# Data Privacy and Safety

## Principle

Grow will handle information about students, minors, career uncertainty, family context, finances, and personal preferences.

Trust must be part of the architecture, not a later compliance task.

## Public repository boundary

The public GitHub repository may contain:

1. Product logic
2. Documentation
3. Schemas without real participant data
4. Prompt and workflow templates
5. Research summaries
6. Anonymised aggregate learning
7. Test fixtures using synthetic data

The public repository must not contain:

1. Phone numbers
2. Private WhatsApp conversations
3. Home addresses
4. Identity document numbers
5. Personal financial details
6. Guardian contact details
7. Sensitive personal histories
8. Raw participant recordings
9. Identifiable assessment results

## Participant data store

Production participant data should live in a protected database with access control, auditability, backups, and an explicit retention policy.

Separate raw conversation data from structured assessment evidence where possible.

## Data minimisation

Collect only information that changes guidance, safety, operations, or required consent.

Do not collect data simply because it might become useful later.

## Minor participants

Because the core audience begins at Grade 8, the system will include minors.

The product must support:

1. Age detection
2. Guardian consent where required
3. Guardian contact flow
4. Clear boundaries for direct communication
5. Escalation for safeguarding concerns
6. Minimal collection of unnecessary sensitive information
7. Appropriate communication hours and content

Legal requirements should be reviewed before production deployment and whenever geography or operating model changes.

## Sensitive topics

If a participant reveals issues outside career guidance, the system should not pretend to be a qualified service for that domain.

Examples include:

1. Self harm or immediate safety risk
2. Abuse
3. Severe mental distress
4. Medical diagnosis requests
5. Legal disputes

The system should follow an appropriate escalation or referral policy.

## Assessment safety

Never present personality or aptitude results as a diagnosis.

Avoid statements such as:

You are not intelligent enough for this field.

Prefer evidence based language such as:

Your current assessment shows weaker evidence in this area, but the result is limited and can change with learning and further testing.

## Career recommendation safety

Recommendations must expose uncertainty.

The system should distinguish:

1. Strong evidence
2. Moderate evidence
3. Weak evidence
4. Unknown

High consequence decisions should not be framed as certain predictions.

## Financial data

Financial hardship data should have limited access.

It should be used only for access decisions and relevant planning.

It must not influence career capability scoring.

## Human access

Internal staff should receive only the information required for their role.

Potential future roles:

1. Career reviewer
2. Access reviewer
3. Safeguarding reviewer
4. Operations administrator
5. System administrator

## Logging

Audit sensitive operations such as:

1. Human review
2. Fee status changes
3. Recommendation overrides
4. Data export
5. Data deletion
6. Guardian consent changes
7. Staff access to sensitive cases

## Deletion and retention

Before production, define:

1. Raw message retention
2. Voice recording retention
3. Assessment retention
4. Payment record retention
5. Inactive participant retention
6. Deletion request process
7. Backup deletion limitations

## AI data handling

Before sending participant data to any external AI provider, document:

1. What data is sent
2. Why it is necessary
3. Whether identifiers can be removed
4. Provider retention behaviour
5. Access controls
6. Failure and fallback behaviour

Prefer sending the minimum context required for the task.

## Safety review gate

National scaling should not happen until Grow has documented:

1. Minor consent flow
2. Safeguarding escalation
3. Data retention
4. Staff access roles
5. Incident response
6. AI provider data handling
7. Participant deletion process

## Trust rule

A useful recommendation is not worth obtaining by collecting more sensitive data than the participant reasonably expects.
