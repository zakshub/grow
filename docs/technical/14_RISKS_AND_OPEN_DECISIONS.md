# Risks and Open Decisions

## Risk register

| Risk | Impact | Mitigation / validation | Gate |
| --- | --- | --- | --- |
| Assessment lacks cultural/age validity | Harmful or generic guidance | Research public/licensed instruments; Urdu cognitive interviews; small cohorts; reviewer disagreement/outcome tracking | No validity claims or scaled use before evidence |
| Career mapping encodes stereotypes | Biased recommendations | Multi-signal profiles, metamorphic/fairness tests, diverse reviewers, explicit constraint/capability separation | Review distributions before each pilot expansion |
| AI hallucination or overreach | False evidence/claims | Typed output, allowed-ID grounding, deterministic rules, human MVP review, provider-independent fallback | AI never source of truth |
| Urdu/voice misunderstanding | Wrong evidence and exclusion | Human language review, speech benchmark, confidence confirmation, text alternatives | Provider selection and content sign-off |
| Minor consent/safeguarding ambiguity | Legal/safety harm | Qualified local review, configurable fail-closed policy, trained staffed escalation | Blocks real-minor production |
| Excess raw-data retention/breach | Participant harm and loss of trust | Minimisation, separation/encryption, approved schedules, deletion tests, least privilege | Blocks production without policy |
| Stale/weak market and salary evidence | Misleading feasibility | Source/date/geography/confidence/expiry, unknown state, human review | No unsupported numeric claims |
| Human-review bottleneck or inconsistency | Delay and uneven quality | Structured rubrics, role queues/SLAs, calibration sessions, override analysis | Capacity test before cohort growth |
| WhatsApp/provider dependency | Delivery interruption/policy cost | Official API, adapter boundary, outbox/reconciliation, policy monitoring | Contract/failure tests before launch |
| VPS single point of failure | Outage/data loss | Encrypted off-site backups, restore drills, monitoring, later DB/app separation | Restore test before production |
| Scope expansion before method proof | Expensive wrong product | Enforce MVP exclusions and roadmap gates | Product sign-off for scope change |
| Sensitive data reaches Git/logs/staging | Irrecoverable exposure | Synthetic fixtures, ignore/scan hooks and CI, redaction, no production clones | CI and incident playbook |
| Fee/access biases capability | Discriminatory guidance | Separate module/schema permissions and invariant tests | Mandatory tests/review |
| Small-sample learning becomes rule | Overfit product brain | Observation→hypothesis→reviewed promotion workflow | No automatic promotion |

## Decisions required before Milestone 1 or early foundation

1. Confirm backend/database/queue/operator UI stack and exact supported versions through ADRs.
2. Decide monorepo packaging conventions and deployment ownership.
3. Define whether multi-organisation support is explicitly deferred (recommended) and ensure no accidental institutional complexity.
4. Define pseudonymous analytics/fairness dimensions and minimum aggregation thresholds.

## Decisions required before assessment/recommendation content

1. Exact v1 dimensions and legally usable/adaptable instruments.
2. Urdu/Roman Urdu strategy, education-level difficulty, voice scoring policy.
3. Minimum evidence and confidence/calibration method.
4. Pakistan career taxonomy/granularity and profile review ownership.
5. Practical-experiment selection, rubrics, device/language fairness, count, and human-review rules.
6. Whether recommendation count is always three to five or adapts to evidence strength.
7. Definition of recommendation success, participant feedback method, and stop/change criteria.

## Decisions required before real participant production

1. Public product name and official participant identity.
2. Pilot cohort size/mix, adult-track inclusion, journey duration, and reviewer staffing.
3. Qualified Pakistan legal review: minor threshold, assent/consent, guardian verification, sharing boundaries, data rights.
4. Safeguarding playbook, staffed response, local referrals, and communication boundaries/hours.
5. Retention periods for messages, voice, transcripts, evidence, payment, inactive records, audit, and backups; deletion process.
6. WhatsApp account/number, direct Meta vs BSP, opt-in/out language, templates, reminder caps, media policy, and current platform-policy review.
7. AI and speech providers after privacy/security/Urdu-quality/cost/fallback evaluation.
8. Fee qualification/approvers, service/payment gate, payment methods and verification, sustainability/support fund.
9. Operator identity provider/MFA, access approvers, review cadence, incident/on-call owners.
10. VPS/region/provider, off-site backup, RPO/RTO, monitoring/error service data handling.

## Product brain items that cannot yet be implemented safely

- A legally correct minor/guardian flow: exact requirements are deliberately unresolved.
- Safeguarding response beyond detection and holding/routing: no approved staffed playbook is defined.
- Validated assessment scoring/thresholds/confidence: dimensions, instruments, Urdu adaptation, phone tasks, and calibration require research and cohort evidence.
- High-confidence career recommendations: taxonomy, mappings, experiments, and market evidence are not yet validated.
- Salary/demand/remote/freelance claims at participant level: sources and refresh policy are not selected.
- Reliable voice-derived evidence: transcription provider and representative Urdu benchmark are absent.
- Fee eligibility/payment automation: criteria, approvers, rails, and verification are unresolved.
- Production retention/deletion and AI data transfers: policy, legal basis, vendors, and contracts are unresolved.
- Autonomous recommendation delivery or knowledge-rule promotion: explicitly outside MVP/product rules.
- Pakistan-wide/regional expansion: local language, opportunity, education, access, and safety evidence is not yet present.

These gaps do not block building the synthetic local domain foundation; they block real-user activation or specific content decisions.

## Decision record format

Each resolution should record ID, question, status, owner, date, product authority affected, options, evidence, decision/rationale, privacy/safety impact, reversibility, validation/expiry date, and implementation consequences. Update `docs/16_OPEN_QUESTIONS.md` and the relevant canonical document when product behaviour changes; do not resolve only inside technical notes.

## Review cadence

Review this register at every milestone gate and weekly during a participant pilot. New uncertainty is recorded immediately. Closing a technical ticket does not close a product or legal question without the named authority.
