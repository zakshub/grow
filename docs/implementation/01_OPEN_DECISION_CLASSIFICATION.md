# Open Decision Classification

Date: 2026-10-05

This classifies every question in `docs/16_OPEN_QUESTIONS.md` without resolving product or policy by assumption.

Categories:

1. **Must resolve before Milestone 1** — technical foundation decision; now resolved by an ADR where noted.
2. **Can safely defer** — not required for the synthetic local foundation.
3. **Requires external research** — evidence, legal, provider, or market research is required.
4. **Requires owner decision** — product/operations/business owner must decide.
5. **Requires pilot validation** — real, consented pilot learning is required.

`UNKNOWN` means the domain represents absence explicitly. `BLOCKED` means the named production capability must not proceed.

## Product questions

| # | Question | Category | Milestone 1 treatment |
| --- | --- | --- | --- |
| 1 | Public service name | 4 | Deferred; repository name only |
| 2 | Whether Grow is participant-facing name | 4 | Deferred |
| 3 | Complete journey duration | 5 | Deferred |
| 4 | Fixed three-to-five recommendations or adaptive count | 5 | No recommendation logic |
| 5 | Explanation depth by education level | 5 | Deferred |
| 6 | Separate parent summary | 3 | BLOCKED with guardian policy |
| 7 | Outputs private from guardians | 3 | BLOCKED with legal/privacy review |

## Assessment questions

| # | Question | Category | Milestone 1 treatment |
| --- | --- | --- | --- |
| 1 | Version-one personality dimensions | 3 | UNKNOWN; dimension code is unvalidated shell |
| 2 | Legally adaptable validated instruments | 3 | BLOCKED |
| 3 | Own Urdu RIASEC-style assessment or licensed tool | 3 | BLOCKED |
| 4 | Difficulty adaptation by education | 5 | Deferred |
| 5 | Consistent scoring of voice answers | 3 | BLOCKED |
| 6 | Phone-reliable aptitude tasks | 5 | Deferred |
| 7 | Minimum evidence before cluster | 5 | No career clusters/recommendations |
| 8 | Confidence calibration | 5 | UNKNOWN is first-class; no calibration claim |
| 9 | Meaningful score thresholds | 5 | No scoring engine |
| 10 | Reassessment frequency | 5 | Deferred |

## Career intelligence questions

| # | Question | Category | Milestone 1 treatment |
| --- | --- | --- | --- |
| 1 | Pakistan career taxonomy | 3 | BLOCKED; no taxonomy implemented |
| 2 | MVP occupation granularity | 4 | Deferred |
| 3 | Career-to-signal/experiment mappings | 3 | BLOCKED |
| 4 | Salary-range sources | 3 | BLOCKED |
| 5 | Hiring-demand sources | 3 | BLOCKED |
| 6 | Remote/freelance representation | 3 | Deferred |
| 7 | Emerging-career addition | 4 | Deferred |
| 8 | Career-evidence expiry/refresh | 3 | Deferred |

## Practical experiment questions

| # | Question | Category | Milestone 1 treatment |
| --- | --- | --- | --- |
| 1 | Shortest meaningful task | 5 | Deferred |
| 2 | Experiments requiring human review | 5 | Deferred |
| 3 | English/device unfairness | 5 | Deferred; must be tested |
| 4 | Task-quality scoring | 3 | Deferred |
| 5 | Experiments required before recommendation | 5 | Deferred |
| 6 | When experiment overrides questionnaire | 5 | Deferred |

## WhatsApp questions

| # | Question | Category | Milestone 1 treatment |
| --- | --- | --- | --- |
| 1 | WhatsApp account and number | 4 | Out of scope |
| 2 | BSP versus direct Meta | 3 | Out of scope |
| 3 | Required message templates | 4 | Out of scope |
| 4 | Voice transcription provider | 3 | Out of scope |
| 5 | Media storage | 1 | Boundary planned; runtime implementation safely deferred |
| 6 | Reminder cap before pause | 5 | Deferred |
| 7 | Exact opt-out language/handling | 3 | Deferred |

## Minor and guardian questions

| # | Question | Category | Milestone 1 treatment |
| --- | --- | --- | --- |
| 1 | Legally/operationally required consent flow | 3 | BLOCKED; consent shell only |
| 2 | Guardian-action age | 3 | UNKNOWN; threshold injectable, never defaulted |
| 3 | Guardian identity verification | 3 | BLOCKED |
| 4 | Guardian-shareable career information | 3 | BLOCKED |
| 5 | Participant/guardian preference conflict | 4 | BLOCKED |
| 6 | Safeguarding escalation process | 3 | BLOCKED |

## Fee questions

| # | Question | Category | Milestone 1 treatment |
| --- | --- | --- | --- |
| 1 | PKR 500 sustainability | 5 | Deferred |
| 2 | PKR 200 qualification | 4 | UNKNOWN; candidate only |
| 3 | Free-access qualification | 4 | UNKNOWN; candidate only |
| 4 | Exception approver | 4 | BLOCKED before operations |
| 5 | Support fund/sponsored seats | 4 | Deferred |
| 6 | Payment methods | 4 | Deferred |
| 7 | Payment verification | 3 | Deferred |

## Recruitment questions

| # | Question | Category | Milestone 1 treatment |
| --- | --- | --- | --- |
| 1 | First campaign message | 4 | Deferred |
| 2 | First contact-list owner | 4 | Deferred; no contact data |
| 3 | Initial outreach target | 4 | Deferred |
| 4 | Old-student networks | 4 | Deferred |
| 5 | Village/community networks | 4 | Deferred |
| 6 | Teacher/female-student trusted networks | 4 | Deferred |
| 7 | Low-friction source attribution | 5 | Referral shell only |
| 8 | Acceptable first-pilot conversion | 5 | Deferred |

## Technology questions

| # | Question | Category | Milestone 1 treatment |
| --- | --- | --- | --- |
| 1 | Backend language/framework | 1 | Resolved: Python/Django, ADR 0001 |
| 2 | Database | 1 | Resolved: PostgreSQL authority, ADR 0002; SQLite local only |
| 3 | Workflow/queue | 1 | Boundary resolved: Redis/Dramatiq later, ADR 0003 |
| 4 | AI provider | 3 | Deferred; no adapter/integration |
| 5 | Speech provider | 3 | Deferred |
| 6 | VPS/deployment model | 3 | Deferred; planned only |
| 7 | Backup strategy | 3 | Deferred before production |
| 8 | Operator authentication | 4 | Deferred; Django Admin inspection only |
| 9 | Custom versus temporary operator tool | 1 | Resolved for Milestone 1: Django Admin, ADR 0001 |
| 10 | Multiple organisations | 2 | Explicitly deferred |

## Privacy questions

| # | Question | Category | Milestone 1 treatment |
| --- | --- | --- | --- |
| 1 | Raw message retention | 3 | BLOCKED; no messages stored |
| 2 | Voice-note retention | 3 | BLOCKED; no voice storage |
| 3 | Participant deletion process | 3 | BLOCKED; ADR 0009 defines only safe foundation boundary |
| 4 | Fields needing extra encryption | 3 | PII separated; production crypto BLOCKED |
| 5 | AI calls allowed deidentified data | 3 | BLOCKED; no AI integration |
| 6 | Payment-record retention | 3 | BLOCKED; no payments implemented |
| 7 | Access-log review process | 4 | Deferred before operator production |

## Pilot questions

| # | Question | Category | Milestone 1 treatment |
| --- | --- | --- | --- |
| 1 | First cohort size | 4 | Deferred |
| 2 | Participant education mix | 4 | Deferred |
| 3 | Adult career-switcher inclusion | 4 | Synthetic case only; pilot decision deferred |
| 4 | Human career reviewer | 4 | Deferred |
| 5 | Successful recommendation definition | 5 | Deferred |
| 6 | Participant feedback method | 4 | Deferred |
| 7 | Result that changes project direction | 4 | Deferred |

## Additional technical-plan decisions

| Decision | Category | Treatment |
| --- | --- | --- |
| Django module/monorepo packaging | 1 | Resolved by ADR 0001 |
| Identifier/PII separation | 1 | Resolved by ADR 0004 |
| Audit structure | 1 | Resolved by ADR 0005 |
| Transition semantics | 1 | Resolved by ADR 0006 |
| Evidence versioning | 1 | Resolved by ADR 0007 |
| Human override preservation | 1 | Resolved by ADR 0008 |
| Soft/hard deletion boundary | 1 | Foundation resolved, policy BLOCKED by ADR 0009 |
| Development-data policy | 1 | Resolved by ADR 0010 |
| Configuration/secrets | 1 | Resolved by ADR 0011 |
| Synthetic test generation | 1 | Resolved by ADR 0012 |
| Analytics/fairness dimensions and minimum group sizes | 3 | Deferred; requires ethical/legal/statistical research |

## Milestone 1 conclusion

All technical choices necessary for the synthetic local foundation are resolved. No unresolved policy has been disguised as a default. Real participant operation remains blocked on minor/guardian consent, safeguarding, retention/deletion, operator access, incident response, and other production gates in `docs/technical/10_SECURITY_PRIVACY.md`.
