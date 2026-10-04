# Assessment and Evidence Architecture

## Purpose

The assessment engine gathers and evaluates multi-source evidence; it does not label a person or select a career from one result. It keeps personality tendencies, interests, current strengths, learning potential, values, environment preferences, constraints, practical behaviour, and market evidence separate.

## Versioned assessment content

An assessment version contains:

- Audience applicability: life-stage track, education band, language, and accessibility needs.
- Dimension definitions and provisional interpretation guidance.
- Question/item variants and response schemas.
- Scoring and interpretation rules with provenance/licence.
- Selection/sufficiency policy.
- Validation status: draft, pilot-only, validated-for-defined-use, retired.
- Test cases, limitations, approver, and publication date.

Do not implement proprietary question banks or claim psychometric/clinical validity. The v1 dimension set and legally adaptable instruments remain research decisions.

## Evidence model

Each `EvidenceItem` records:

- Who/journey and which dimension/category it concerns.
- Observation/claim direction and strength or structured value.
- Source: self-report, behavioural story, forced choice, reasoning task, practical experiment, reviewer, guardian context, follow-up, or AI-derived proposal.
- Direct source record and derivation lineage.
- Confidence band and numeric representation if defined, with reasons.
- Reliability/quality signals, recency, language/variant, and interpretation version.
- Whether it supports, conflicts with, or is neutral to a hypothesis.
- Privacy/retention class and review status.

AI-extracted evidence begins as `proposed`; deterministic validation or human confirmation promotes it to usable evidence. The raw statement is not silently overwritten by interpretation.

## Confidence

Confidence describes evidence sufficiency and reliability, not participant worth. Calculate it from versioned factors such as:

- Number of independent evidence sources, with diminishing returns.
- Diversity across self-report, structured task, practical behaviour, and follow-up.
- Source reliability and item quality.
- Recency and relevance to the dimension.
- Agreement versus contradiction.
- Applicability of language, age, education, and device conditions.
- Missingness and possible accessibility bias.

Expose low/moderate/high (and unknown where appropriate) plus reasons. Do not imply statistical calibration until validated against real outcomes.

## Dimension estimates

An estimate is a projection over a frozen evidence set:

```text
dimension estimate = bounded aggregate of eligible evidence
confidence = evidence-quality and sufficiency function
uncertainty = missingness + disagreement + applicability limits
```

Store each evidence contribution and calculation version. Initial scores may use the product brain's provisional 0–100 representation, but thresholds must stay configuration/version data marked pilot-only until validated.

## Contradictions

A contradiction links the exact evidence records and records type, severity, possible explanations, next question/experiment, and resolution status. Types include self-report vs behaviour, repeated self-report inconsistency, experiment vs structured task, reviewer vs automation, and context-dependent behaviour.

Contradictions are not automatically errors. The engine may:

1. Ask a contextual clarification.
2. Select a different evidence format.
3. Assign a relevant practical experiment.
4. Reduce confidence.
5. Require human review.

Resolution never deletes the conflicting evidence.

## Adaptive selection

The selector is deterministic first:

1. Filter items by consent, track, education, language, device/accessibility, and items already presented.
2. Prioritise required core dimensions with insufficient evidence.
3. Prioritise severe contradictions and missing source diversity.
4. Apply burden controls: session length, fatigue, skip history, and sensitive-question limits.
5. Select from approved versioned items and store the reason.

AI may propose a follow-up phrasing, but the target dimension, allowed intent, safety constraints, and output schema are application-controlled. Unapproved generated psychometric items cannot affect scores.

## Sufficiency and completion

Completion is a policy result, not a question count. A dimension/session is sufficient only when the current version's minimum evidence classes, confidence, applicability, and contradiction thresholds are met—or a reviewer accepts explicit limitations. Results are:

- `sufficient`
- `insufficient` with missing requirements
- `review_required`
- `not_applicable`
- `unable_to_assess`

The participant-facing explanation states what is strong, mixed, or unknown and what may help next.

## Safety and fairness

- Financial hardship, gender, city, school type, English fluency, device access, and one exam result cannot be capability evidence.
- Constraints can alter route feasibility only through explicit, reviewable links.
- Voice transcription confidence and code-switching quality are recorded; low-confidence transcripts require confirmation.
- Compare item completion, skips, confidence, review disagreement, and outcomes across groups only with lawful/ethical aggregation and minimum group sizes.
- A weak current signal is never phrased as fixed inability.

## Assessment engine acceptance criteria

1. Questions belong to versioned dimensions and audience/language variants.
2. Every score/estimate traces to individual evidence and an algorithm version.
3. Ability and interest remain separately queryable and reportable.
4. Contradictions can be opened, explored, left unresolved, and reflected in confidence.
5. Sufficiency can stop unnecessary questioning and can also return unknown.
6. Changing a scoring version creates a new projection and does not rewrite a delivered recommendation.
7. AI/provider outage leaves deterministic structured assessment and review paths operational.
