# Career Intelligence Data Model

## Purpose

Career intelligence describes work, pathways, and opportunity evidence. It is independent of a participant and cannot make a recommendation alone. It must be Pakistan-aware, geography-aware, sourced, dated, confidence-rated, and able to say unknown.

## Taxonomy

Maintain immutable `CareerTaxonomyVersion` records. A version includes broad clusters and careers/roles at an explicitly chosen granularity. The initial taxonomy should cover the MVP's tested career families, not claim national completeness.

Each career profile includes:

- Stable code; Urdu and English names/descriptions.
- Parent cluster and related roles.
- Typical work activities and environments.
- Required/advantageous dimensional patterns across interests, strengths, traits, values, and environment—never one-to-one personality mapping.
- Entry routes, education/training prerequisites, skills, estimated time and cost ranges.
- Accessibility/device/geography considerations as feasibility, not capability.
- Linked practical experiments.
- Evidence gaps and review status.

## Market evidence

`MarketObservation` uses the following dimensions where available:

- Local/regional hiring demand.
- Remote and freelance relevance.
- Training availability and qualification barriers.
- Entry competition and geographic concentration.
- Entry, early-career, and experienced earning ranges separated by local/remote/freelance context.
- Growth potential, automation exposure, and international mobility.

Every observation records career, geography, evidence type, source, observation period/date, access date, value/range and unit, methodology/sample where known, limitations, confidence, expiry/refresh date, and reviewer status.

`unknown` is a first-class status. Absence of data is not low demand and must not produce zero salary or fit penalties.

## Source registry

Sources follow the hierarchy in `docs/15_RESEARCH_AND_EVIDENCE.md`: official/framework, primary research, recognised bodies, quality market data, job-platform data, expert interpretation, and anecdotal/community observations. The registry records licence/usage restrictions so copyrighted or proprietary data is not copied into the repository or product without permission.

Initial research candidates remain those named in the brain—O*NET as a studied foundation, Pakistan Bureau of Statistics, NAVTTC, and HEC—plus separately approved current market sources. Their existence does not validate a final taxonomy or assessment.

## Publication workflow

```text
research question
 -> source capture and limitations
 -> draft observation/profile change
 -> reviewer checks mapping, geography, freshness, licence
 -> publish immutable data version
 -> recommendation runs pin the version
 -> expiry creates refresh task, not silent deletion
```

A correction publishes a superseding record and impact analysis for affected active content. Previously delivered recommendations retain their original evidence snapshot; a serious correction can create a review/recontact task under an approved policy.

## Import and curation

- Use schema-validated CSV/JSON import packages generated from non-sensitive research workflows.
- Validate stable codes, units/currency, ranges, geography, dates, source references, duplicates, and expired evidence.
- Require a diff preview and human approval before publication.
- Store raw licensed/source extracts outside Git when redistribution is not permitted; Git may contain schemas, import code later, and synthetic samples.
- Schedule freshness checks; do not automatically publish scraped or AI-generated market claims.

## Pakistan-wide expansion

Model geography hierarchically (country, province/territory, division/district/city as justified) and permit evidence at different levels with explicit applicability. Add education-board/pathway mappings and language labels by version. Never copy Karachi assumptions nationwide. Regional absence of evidence remains unknown until researched.

## Quality gates

A career may enter candidate generation only when its profile has approved minimum self-fit signals and an explanation. It may be delivered with unknown market evidence only when the recommendation explicitly shows that uncertainty and human review accepts it. Salary claims require sourced ranges, currency, geography, date, career stage, and confidence.

## MVP content boundary

Before MVP use, product/research owners must approve:

1. Career taxonomy and granularity for the pilot.
2. Minimum profile completeness.
3. At least six broad practical-experiment families.
4. Source/licence policy and market refresh cadence.
5. Which opportunity fields may be unknown without blocking delivery.

National taxonomy breadth, automated scraping, salary prediction, emerging-career ingestion, and regional-language content are later phases.
