# Grow

Grow is a WhatsApp first career discovery and guidance system for people who do not yet understand what they are good at, what they are genuinely interested in, or which education and career direction fits them.

The primary audience is students from Grade 8 through graduation. Age is intentionally flexible because career confusion does not end at graduation. A secondary audience includes adults who have already studied or worked for several years but still need to discover a better direction.

The product language is primarily Urdu. Repository documentation is maintained in English so product, research, engineering, design, and automation decisions remain precise and reusable.

## Core problem

Most career guidance starts too late and asks the wrong first question.

It asks a student what they want to become.

Grow starts earlier.

It helps a person discover:

1. How they naturally think
2. What kind of problems they enjoy solving
3. Where their abilities appear strongest
4. What type of work gives or drains energy
5. What they value in work and life
6. What constraints they actually live with
7. Which fields fit the combined evidence
8. Which options have realistic earning and learning potential
9. Which direction survives a small real world trial

Grow does not treat a personality label as destiny. It combines personality signals, interests, strengths, values, constraints, practical tasks, education level, and labour market reality before recommending directions.

## Initial operating model

1. Channel: WhatsApp
2. Primary language: Urdu
3. Initial geography: Karachi
4. Expansion: Sindh and Punjab
5. Long term geography: Pakistan
6. Core audience: Grade 8 through graduation
7. Secondary audience: career switchers and adults with unresolved career direction
8. Standard fee: PKR 500
9. Reduced fee: PKR 200 for people with limited means
10. Free access: available for genuinely deserving participants after human review
11. System delivery: highly automated
12. Future hosting: application logic, database, analytics, orchestration, and knowledge services on a self hosted VPS
13. WhatsApp transport: official WhatsApp Business Platform integration rather than an unofficial automation workaround

## Product promise

Grow helps a person move from confusion to evidence based direction.

The product should answer five questions:

1. Who am I as a learner and worker
2. What am I naturally inclined toward
3. What am I capable of becoming good at
4. Which realistic paths fit me
5. What should I try next before making a major decision

## What Grow is not

1. Not a generic chatbot
2. Not a one time personality quiz
3. Not a deterministic career prediction system
4. Not a course marketplace
5. Not a motivational content product
6. Not an automated poverty classifier
7. Not an AI system that makes irreversible decisions about a student

## System loop

Participant enters through WhatsApp

→ consent and basic profile

→ discovery conversation

→ structured assessment

→ interest and strength hypotheses

→ constraints and work values

→ candidate career clusters

→ short practical experiments

→ updated evidence

→ ranked career directions

→ education and skill roadmap

→ follow up and progress tracking

→ referral and alumni loop

## Repository map

See `docs/00_INDEX.md` for the complete product brain.

Key files:

1. `BRAIN.md` defines how the Grow knowledge system should think and evolve
2. `docs/01_PRODUCT_VISION.md` defines the long term product vision
3. `docs/02_AUDIENCE_AND_SCOPE.md` defines who the system serves
4. `docs/03_CAREER_DISCOVERY_ENGINE.md` defines the core career consultant module
5. `docs/04_ASSESSMENT_MODEL.md` defines the trait, interest, strength, value, and evidence model
6. `docs/05_PARTICIPANT_JOURNEY.md` defines the end to end experience
7. `docs/06_WHATSAPP_OPERATING_MODEL.md` defines the WhatsApp first workflow
8. `docs/07_RECRUITMENT_AND_REFERRALS.md` defines audience acquisition
9. `docs/08_FEES_AND_ACCESS.md` defines paid, reduced, and free access
10. `docs/09_DATA_PRIVACY_AND_SAFETY.md` defines privacy, minors, and human review rules
11. `docs/10_SYSTEM_ARCHITECTURE.md` defines the future technical architecture
12. `docs/11_AUTOMATION_BLUEPRINT.md` defines what is automated and what remains human
13. `docs/12_MVP_BUILD_PLAN.md` defines the first build
14. `docs/13_ROADMAP.md` defines phased expansion
15. `docs/14_MEASUREMENT_AND_LEARNING.md` defines success metrics and learning loops
16. `docs/15_RESEARCH_AND_EVIDENCE.md` defines evidence standards
17. `docs/16_OPEN_QUESTIONS.md` tracks unresolved product decisions

## Current status

Foundation stage.

The immediate goal is to turn the concept into a testable WhatsApp first career discovery service with a rigorous career guidance engine before attempting national scale or full automation.
