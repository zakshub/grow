# Implementation Milestones

## Dependency order

Implementation begins only after this plan is reviewed. Milestones are ordered to validate domain truth before integrations and automation. A milestone is complete only when its acceptance criteria and documentation evidence pass.

## Milestone 0 — Resolve production-blocking policies and ADRs

Deliver approved ADRs for stack/version, modular boundaries, environment/secrets, WhatsApp integration path, AI/speech evaluation plan, and operator authentication. Deliver owners and decision dates for consent/minors, safeguarding, retention/deletion, payment gate, assessment v1, career taxonomy, experiment rubrics, and pilot success.

Acceptance criteria:

1. No unresolved decision is silently converted into code behaviour.
2. Synthetic-data and Git boundaries are enforced in repository policy/CI design.
3. Production-blocking policy items have named owners, evidence needed, and go/no-go gates.
4. Product owner confirms alignment with `BRAIN.md` and `docs/18_IMPLEMENTATION_HANDOFF.md`.

## Milestone 1 — Local foundation and domain model

Create application skeleton, PostgreSQL migrations, module boundaries, participant/contact, consent, guardian, referral, journey/state, assessment session, evidence/dimension, career cluster/profile, recommendation, experiment, review, fee, follow-up, audit, outbox, synthetic factories, and CI. No WhatsApp or external AI.

Acceptance criteria:

1. One synthetic participant completes the full MVP state path locally through application services.
2. Minor-policy result can require and block on guardian action without hard-coding an unresolved legal threshold.
3. Allowed transitions are explicit; invalid/concurrent transitions fail and are audited.
4. Evidence stores source, dimension/category, confidence, lineage, and privacy class; contradictions are first-class.
5. All required handoff entities exist with constraints and synthetic tests; no identifiable data is committed.

## Milestone 2 — Deterministic assessment and evidence engine

Implement versioned assessment definitions/items, responses, deterministic scoring, confidence, contradictions, adaptive selection rules, and evidence sufficiency using pilot-only synthetic content.

Acceptance criteria:

1. Questions map to dimensions and audience/language variants.
2. Answers/tasks produce traceable evidence; ability, interest, potential, values, constraints, and behaviour remain separate.
3. Every estimate explains contributing/conflicting evidence and calculation version.
4. Contradiction and low-confidence paths select clarification/review.
5. Completion is sufficiency-based and supports unable-to-assess/unknown.
6. Canonical assessment tests in `12_TESTING.md` pass.

## Milestone 3 — Career intelligence registry

Implement versioned taxonomy/profiles, signal mappings, pathways, research sources, market observations, freshness/expiry, import validation, and review/publish workflow using approved MVP data.

Acceptance criteria:

1. Careers map to multiple traits/interests/strengths/values/environments and experiments, never one personality label.
2. Geography/date/source/confidence/limitations accompany market evidence.
3. Unknown opportunity and salary are representable and displayed as unknown.
4. Salary is a sourced range by stage/geography/date, never guarantee.
5. Imports are diffed, validated, approved, versioned, and contain no unlicensed/private source extracts in Git.

## Milestone 4 — Transparent recommendation engine

Implement snapshot, candidate generation, component evaluation, configurable ranking, confidence, structured explanation, versioning, comparison, and review trigger without generative dependency.

Acceptance criteria:

1. Produces three to five options when evidence supports them; otherwise requests evidence/review rather than padding.
2. Each option exposes support, conflict, component contributions, unknowns, confidence, tradeoffs, route, and next experiment/action.
3. Constraint feasibility is separate from capability; fee/demographics do not influence fit.
4. Identical inputs/config are reproducible; changes create new versions.
5. Human override retains proposal, before/after, reason, actor, and time.

## Milestone 5 — Practical experiments

Implement versioned experiment library, accessibility/resource metadata, assignment, submission, rubric observation, human review, evidence conversion, reminders (locally), and recommendation revision.

Acceptance criteria:

1. At least six approved broad career-family experiment versions exist and take the product-defined 15–45 minutes.
2. Each maps to careers/dimensions and has observable rubric, bias/accessibility notes, and review rule.
3. Completion, quality, persistence, enjoyment, curiosity, learning speed, prompting need, and desire to repeat can be captured where appropriate.
4. Submission can create evidence only with lineage/confidence and required review.
5. New experiment evidence creates a new recommendation version with an explainable delta.

## Milestone 6 — Operator review, access, and safety shell

Build staff authentication/MFA integration, RBAC, review queues, participant/evidence/recommendation summary, approve/request/override, fee decision separation, safety-case routing, and sensitive-read audit.

Acceptance criteria:

1. Career, access, safeguarding, operations, admin, and audit permissions are enforced server-side.
2. Reviewer sees stage, evidence/missing/conflicts, experiments, proposed recommendation, confidence, and data freshness.
3. Every MVP final recommendation requires approval before deliverable status.
4. Fee reviewer can decide standard/reduced/free without that data reaching recommendation inputs.
5. Safety signals route to a human; automation cannot close them.
6. Sensitive reads, exports, overrides, consent/fee/safety decisions are audited.

## Milestone 7 — Official WhatsApp and Urdu/voice integration

Integrate selected official provider, inbound/outbound inbox/outbox, templates, message status, opt-out, media, approved Urdu content, and selected speech adapter.

Acceptance criteria:

1. Signature/replay validation and duplicate/out-of-order contract tests pass.
2. Incoming identity maps to participant; explicit state determines the next action.
3. Opt-out immediately suppresses queued non-essential messages.
4. Failures/retries/statuses are visible and cannot duplicate logical sends.
5. Voice has secure download, scan, encrypted storage, transcription metadata, uncertainty confirmation, and retention path.
6. Templates/free-form contexts are separated; all MVP Urdu content passes human review.

## Milestone 8 — Automation, follow-up, reporting, and pilot readiness

Enable due jobs/reminders, 7/30-day follow-up, referral attribution, daily operations and weekly learning reports, retention jobs, observability, deployment, backup/restore, and controlled-pilot runbook.

Acceptance criteria:

1. Reminder caps, quiet hours, opt-out/consent rechecks, and pause-after-silence work.
2. Daily queue/failure/funnel and weekly observation reports are reproducible; reports cannot promote rules.
3. Follow-up records action, satisfaction/mismatch, and outcome provenance.
4. Production privacy gate in `10_SECURITY_PRIVACY.md` is signed off.
5. Staging end-to-end, load, security, backup restore, incident, and provider-outage drills pass.
6. Pilot cohort, reviewer coverage, success/stop criteria, support process, and escalation ownership are documented.

## Later milestones, not MVP prerequisites

Career-intelligence expansion, regional evidence/languages, automation maturity, longitudinal roadmap tracking, national product, and institutional offerings follow `docs/13_ROADMAP.md` only after their exit conditions. They must not be pulled into the MVP without a documented product decision.

## Recommended first implementation milestone

Milestone 0 must close the decision gates, then Milestone 1 is the first code milestone. It deliberately excludes WhatsApp and AI so the full product state/evidence/review spine can be tested locally first.
