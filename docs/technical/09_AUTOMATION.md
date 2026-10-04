# Automation and Workflow Architecture

## Principle

Automation executes repeatable work around an explicit state machine. It does not own product judgement. PostgreSQL records workflow truth and job intent; Redis/Dramatiq delivers work. A queue outage may delay work but cannot erase state.

## Job architecture

- Transactional outbox: domain change and event/job intent commit together.
- Dispatcher publishes due outbox records to named queues.
- Workers claim idempotently using event/job keys, record attempts, heartbeat long work, and commit results transactionally.
- Retry only transient failures with exponential backoff and jitter.
- Non-retryable/exhausted jobs enter a reviewable dead-letter state with participant impact and recovery action.
- Scheduler inserts due jobs under a database uniqueness constraint; it does not depend on one in-memory timer.

Initial queues: `webhook`, `messages`, `media`, `assessment`, `recommendation`, `review_notifications`, `follow_up`, `reporting`, and `maintenance`. Separate concurrency protects interactive messages from slow media/reports.

## Workflow definitions

Versioned workflow definitions declare states, commands, timeouts, reminders, human gates, content/template IDs, and cancellation rules. Active journeys remain pinned unless an approved migration occurs.

Automatable work includes intake, profile prompts, approved adaptive question selection, deterministic item scoring, evidence proposals, experiment instructions/reminders, candidate recommendation calculation/drafting, follow-ups, referral attribution, and aggregate reports.

Required human work includes free/reduced access decisions under policy, MVP final recommendations, sensitive minors, safeguarding, fraud suspicion, permanent rejection, weak/conflicting high-consequence guidance, complaints, and rule promotion.

## Scheduled automation

- Incomplete onboarding/assessment reminders.
- Experiment due reminders.
- 7-day and 30-day MVP follow-ups.
- Payment reminders only after fee/payment policy approval.
- Daily operational/review-queue summary.
- Weekly learning report.
- Market evidence expiry and content review tasks.
- Backup verification, retention/deletion jobs, and access review reminders.

Every scheduled send rechecks consent, opt-out, journey state, quiet hours, attempt cap, and whether the action is still relevant immediately before delivery.

## Human task queues

Review tasks store type, reason, urgency, required role, SLA target, participant stage, minimal evidence summary, decision requested, suggested options, and linked records. Claim/lease prevents concurrent decisions; optimistic versioning prevents stale writes. Escalation alerts do not expose sensitive content.

## Reporting and learning

Daily reports cover delivery failures, backlog/age, participant state funnel, and urgent review counts. Weekly learning reports produce observations about dropout, override patterns, experiments, source quality, differences, and feedback. Reports cannot publish rules.

Knowledge workflow:

```text
aggregate signal -> observation -> reviewed hypothesis -> validation -> promotion decision -> new versioned rule
```

Each transition preserves evidence, limitations, reviewer, and rationale. Rejection is recorded.

## Failure policy

- Provider timeout: retry idempotently, then alert/dead-letter.
- Invalid AI structure: reject output; deterministic/manual fallback.
- Missing career data: mark unknown and create research task; do not scrape/publish automatically.
- Job deployed with incompatible version: fail closed and alert.
- Worker crash after external send: reconcile provider idempotency/status before resending.
- Human SLA breach: escalate queue priority/notification; never auto-approve.

## Operational acceptance criteria

1. Domain write plus job intent cannot split.
2. Duplicate execution causes no duplicate state transition or participant message.
3. Opt-out and withdrawn consent cancel/suppress due sends.
4. Failed jobs are visible, recoverable, and correlated to impact.
5. A weekly observation cannot change assessment or recommendation behaviour without a reviewed version.
