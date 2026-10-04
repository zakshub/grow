# Recommendation Engine Architecture

## Principle

The engine creates a transparent, revisable proposal from multiple evidence layers. It does not predict destiny and does not allow an AI model to become the source of truth.

## Pipeline

1. **Eligibility and snapshot** — validate consent/state and freeze eligible evidence, dimension estimates, contradictions, constraints, assessment/experiment versions, taxonomy version, and market observation versions.
2. **Candidate generation** — select a diverse set of careers whose approved profiles have meaningful overlap with the evidence; apply only explicit hard prerequisites and preserve reasons for exclusion.
3. **Component evaluation** — independently calculate interest, demonstrated-strength, personality-tendency, values, environment, practical-experiment, feasibility, and market components.
4. **Missingness and conflict** — represent unknown components and contradictory signals explicitly. Never convert missing market data to zero.
5. **Ranking** — use a versioned, deterministic, auditable scoring policy with bounded weights and uncertainty penalties validated for the pilot.
6. **Confidence** — estimate from evidence sufficiency/diversity, practical validation, conflicts, profile quality, market freshness, and model calibration status.
7. **Explanation structure** — assemble support, conflict, tradeoffs, route, market limitations, next experiment/action, and unknowns from stored facts.
8. **AI-assisted drafting** — optionally turn the structure into simple Urdu. Schema validation and factual-reference checks prevent new claims.
9. **Human review** — mandatory for every MVP final recommendation. Reviewer may approve, request evidence, or override with reason.
10. **Delivery and learning** — store the delivered version, participant understanding/feedback, follow-up action, and later outcome without rewriting the original.

## Scoring model

Use a configuration-driven formula rather than hard-coded universal weights:

```text
fit = weighted available component contributions
     - explicit conflicts
     - feasibility risks (reported separately from capability)
uncertainty = missing required evidence + weak source diversity + stale/unknown market data
confidence = calibrated evidence sufficiency, not fit score
```

Normalise over available components only under a documented missing-data policy. Show component values and weights to reviewers. Constraint feasibility must not reduce the underlying capability estimate; it changes route viability and tradeoffs.

Weights, thresholds, and confidence mappings remain provisional until pilot validation. A configuration version requires test cases, change rationale, approver, effective date, and shadow comparison against the prior version.

## Ranking and diversity

The canonical MVP expects three to five ranked directions. Candidate selection should avoid superficial duplicates by applying a documented diversity rule across roles/clusters while retaining the strongest evidence-backed options. If evidence cannot responsibly support the expected number, return insufficient evidence to review rather than padding the list. Whether the participant-facing count may vary is an open product decision.

Fit categories are configurable: strong fit, promising/experiment-needed, possible with tradeoffs, and weak current fit. They describe current evidence, not permanent identity.

## Explanation contract

Every option includes:

- Rank and fit category.
- Confidence and why it is at that level.
- Specific participant evidence supporting it.
- Conflicting evidence and unresolved questions.
- Education/training/entry route and approximate effort/cost when sourced.
- Pakistan, regional, remote, and freelance opportunity evidence with date/confidence—or explicit unknown.
- Salary ranges only with source/geography/date/stage and no guarantee.
- Risks/tradeoffs.
- Low-cost practical experiment and next action.

Participant output is narrative and plain Urdu; reviewer output also exposes calculations and provenance.

## AI boundary

AI may propose classifications from free text, summarise evidence, draft follow-ups, identify candidate contradictions, and draft explanations. It may not:

- Create evidence without a source.
- Invent market/salary/pathway facts.
- Modify weights, rules, consent, or state.
- Hide unknowns or contradictions.
- Approve or deliver the MVP recommendation.

All AI output is typed/structured, provider/version/prompt logged, treated as untrusted input, and validated against allowed evidence IDs and career-data IDs.

## Human review and override

The reviewer sees the participant stage, frozen evidence summary, missing evidence, contradictions, experiments, component scores, source freshness, proposed ranks, explanation, and confidence. Decisions:

- `approve`
- `request_more_evidence`
- `request_experiment`
- `override_rank_or_option`
- `reject_draft_and_redo`
- `escalate_safety_or_specialist`

Override requires reason code and narrative, exact before/after, reviewer/time, and optionally evidence links. The system proposal is never deleted. Later outcomes may support or challenge either decision but do not automatically promote a rule.

## Revisions

New evidence or market data starts a new `RecommendationRun`. The UI compares versions and explains changes. Delivered versions are immutable. Participant complaints or strong mismatch open a review case and may trigger reassessment; they do not silently recalculate history.

## Validation

- Golden synthetic cases with explicit evidence contributions and expected ranking properties.
- Property tests: adding strong relevant evidence cannot invisibly lower its component; fee/gender/name changes do not change fit; missing market evidence remains unknown; identical inputs/config yield identical output.
- Reviewer agreement and override pattern analysis.
- Calibration checks linking confidence bands to later corroboration, with no validation claims before adequate data.
- Distribution/fairness checks for fashionable-field dominance, suspicious demographic correlation, and language/device bias.
