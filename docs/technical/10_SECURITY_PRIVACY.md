# Security and Privacy Architecture

## Threat and trust model

Grow processes direct identifiers, minors' data, private conversations, voice, family/financial context, assessments, and recommendations. Principal risks are unauthorised staff access, leaked credentials/backups/media, excessive collection/retention, unsafe AI/provider disclosure, incorrect guardian handling, webhook abuse, account takeover, cross-participant data exposure, and sensitive data entering Git/logs/analytics.

## Privacy by design

- Purpose-limit every field and evidence item; do not collect speculative data.
- Separate direct identity/contact, raw conversation/media, structured evidence, financial, and safeguarding stores/permissions.
- Use pseudonymous participant IDs throughout business logic, logs, jobs, and analytics.
- Encrypt all traffic; encrypt database volumes/backups; envelope-encrypt direct identifiers, raw content/media references, financial narratives, and safety notes with independently rotatable keys.
- Redact secrets, phone numbers, names, message bodies, transcripts, and provider payloads from logs/errors/traces.
- Production exports require authorisation, purpose, time limit, encryption, and audit; default is aggregate/deidentified output.

## Minors and guardians

Implementation must not guess the consent age, guardian verification method, communication boundaries, or what may be shared. Before participant production, qualified Pakistani legal/privacy review and an approved operating policy must define:

1. Age/decision rule and how uncertain age is handled.
2. Participant assent and guardian consent texts/versions.
3. Guardian identity/contact verification proportional to risk.
4. Direct communication rules, hours, and content.
5. Participant-private vs guardian-shareable outputs.
6. Preference conflict and safeguarding escalation procedures.
7. Retention/deletion and access rights.

The schema and state machine support configurable policy versions and fail closed when guardian requirements are unresolved. Guardian context remains separately attributed; it cannot replace the participant's voice.

## Safeguarding

AI may flag possible risk but must not diagnose or decide the response. An approved playbook must define categories, urgency, on-call roles, message templates, local referral/emergency resources, escalation time, documentation, and closure. Restrict safety cases to authorised reviewers and audit reads. Until the playbook and staffed response exist, production conversations capable of receiving such disclosures cannot be operated safely.

## Authentication and operator access

- Staff accounts only; no shared credentials.
- MFA required for reviewers/admins, phishing-resistant where practical.
- Short sessions, secure `HttpOnly`/`SameSite` cookies, CSRF protection, login throttling, recovery controls, and prompt revocation.
- RBAC plus case/type scope and explicit purpose for sensitive access.
- Separate system administration from participant-content access; emergency elevation is time-bound and audited.
- Quarterly access review initially and immediate offboarding.
- Secrets in a protected deployment secret store/files with minimum permissions, never Git/images/logs.

## Application and integration controls

- Validate signatures, timestamps/replay, schema, size, type, and rate limits on public webhooks.
- Strict output escaping, parameterised ORM/SQL, CSRF, CSP/security headers, dependency and container scanning.
- Media quarantine, MIME/content verification, malware scanning, random non-public object keys, short-lived signed access.
- Egress allow-list where feasible; provider timeouts/circuit breakers.
- Service accounts use least privilege and separate environment credentials.
- Backups encrypted with keys separate from stored archives; restore tests are mandatory.

## AI/provider privacy

Each use case requires a data protection review recording purpose, minimum fields, deidentification, provider/model, geography/subprocessors, training/retention settings, security, access, deletion, contractual terms, fallback, and cost. Send evidence excerpts rather than entire histories where possible. Do not send direct identifiers unless strictly required and approved. Provider responses are untrusted input.

## Retention and deletion

Before production, approve durations for raw WhatsApp payloads/messages, voice, transcripts, structured evidence, assessments/recommendations, financial/payment data, inactive contacts, safety cases, audit, and backups. The system enforces versioned retention classes and holds. Participants need a documented request/identity-verification process and honest explanation of backup expiry limitations.

## Git and development boundary

- `.env*`, credentials, data exports, media, database dumps, and production logs must be ignored and blocked by secret/PII scanning.
- Tests, screenshots, demos, and documentation use synthetic personas only.
- Staging is never populated from a production clone.
- Security incidents or accidental commits follow credential rotation, history/removal assessment, notification, and documented response—not simple deletion alone.

## Incident response

Before pilot: owner/on-call contacts, severity levels, containment steps, evidence preservation, participant/legal notification decision path, provider contacts, credential/key rotation, restore procedure, post-incident review, and drills. Monitor suspicious login/access/export, webhook signature failures, enumeration, unusual message volume, privilege changes, backup failures, and sensitive-case access.

## Production privacy gate

No real participant may enter the system until consent/minor/legal policy, safeguarding, retention/deletion, provider data handling, staff roles/training, incident response, backup restore, and opt-out have documented owners, approved procedures, and tested controls.
