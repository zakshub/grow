from __future__ import annotations

import hashlib
from dataclasses import dataclass

from django.db import transaction

from grow.access.models import AccessCategory, AccessDecision
from grow.assessments.models import (
    AssessmentSession,
    EvidenceItem,
    EvidenceSource,
)
from grow.assessments.services import record_contradiction
from grow.journeys.models import ParticipantJourney
from grow.participants.models import (
    ConsentRecord,
    EducationStage,
    GuardianRelationship,
    GuardianRequirement,
    KnowledgeState,
    LifeStageTrack,
    MinorStatus,
    Participant,
    ParticipantIdentifier,
    ParticipantProfile,
    ParticipantStatus,
    ReferralSource,
)
from grow.reviews.models import HumanReview


@dataclass(frozen=True)
class SyntheticScenario:
    code: str
    age_years: int | None
    education_stage: str
    track: str
    minor_status: str
    guardian_requirement: str
    review_required: bool = False
    contradictory_evidence: bool = False
    access_candidate: str = AccessCategory.UNKNOWN


SCENARIOS = (
    SyntheticScenario(
        "grade-8-minor",
        13,
        EducationStage.GRADE_8,
        LifeStageTrack.SCHOOL,
        MinorStatus.MINOR,
        GuardianRequirement.REQUIRED,
    ),
    SyntheticScenario(
        "grade-10-minor",
        15,
        EducationStage.GRADE_10,
        LifeStageTrack.SCHOOL,
        MinorStatus.MINOR,
        GuardianRequirement.REQUIRED,
    ),
    SyntheticScenario(
        "intermediate-student",
        18,
        EducationStage.INTERMEDIATE,
        LifeStageTrack.COLLEGE,
        MinorStatus.ADULT,
        GuardianRequirement.NOT_REQUIRED,
    ),
    SyntheticScenario(
        "university-student",
        21,
        EducationStage.UNIVERSITY,
        LifeStageTrack.UNIVERSITY,
        MinorStatus.ADULT,
        GuardianRequirement.NOT_REQUIRED,
    ),
    SyntheticScenario(
        "graduate",
        23,
        EducationStage.GRADUATE,
        LifeStageTrack.UNIVERSITY,
        MinorStatus.ADULT,
        GuardianRequirement.NOT_REQUIRED,
    ),
    SyntheticScenario(
        "adult-career-switcher",
        31,
        EducationStage.GRADUATE,
        LifeStageTrack.CAREER_RESET,
        MinorStatus.ADULT,
        GuardianRequirement.NOT_REQUIRED,
    ),
    SyntheticScenario(
        "unknown-age",
        None,
        EducationStage.UNKNOWN,
        LifeStageTrack.UNKNOWN,
        MinorStatus.UNKNOWN,
        GuardianRequirement.UNKNOWN,
    ),
    SyntheticScenario(
        "guardian-handling-required",
        14,
        EducationStage.GRADE_8,
        LifeStageTrack.SCHOOL,
        MinorStatus.MINOR,
        GuardianRequirement.REQUIRED,
        review_required=True,
    ),
    SyntheticScenario(
        "contradictory-evidence",
        20,
        EducationStage.UNIVERSITY,
        LifeStageTrack.UNIVERSITY,
        MinorStatus.ADULT,
        GuardianRequirement.NOT_REQUIRED,
        contradictory_evidence=True,
    ),
    SyntheticScenario(
        "human-review-required",
        22,
        EducationStage.UNIVERSITY,
        LifeStageTrack.UNIVERSITY,
        MinorStatus.ADULT,
        GuardianRequirement.NOT_REQUIRED,
        review_required=True,
    ),
    SyntheticScenario(
        "reduced-fee-candidate",
        19,
        EducationStage.INTERMEDIATE,
        LifeStageTrack.COLLEGE,
        MinorStatus.ADULT,
        GuardianRequirement.NOT_REQUIRED,
        access_candidate=AccessCategory.REDUCED,
    ),
    SyntheticScenario(
        "free-access-candidate",
        17,
        EducationStage.INTERMEDIATE,
        LifeStageTrack.COLLEGE,
        MinorStatus.MINOR,
        GuardianRequirement.REQUIRED,
        access_candidate=AccessCategory.FREE,
    ),
)


def _digest(code: str) -> str:
    return hashlib.sha256(f"grow-synthetic-v1:{code}".encode()).hexdigest()


@transaction.atomic
def create_synthetic_scenarios() -> dict[str, Participant]:
    created: dict[str, Participant] = {}
    for scenario in SCENARIOS:
        digest = _digest(scenario.code)
        identifier = ParticipantIdentifier.objects.filter(
            identifier_type=ParticipantIdentifier.IdentifierType.INTERNAL_ALIAS,
            lookup_digest=digest,
        ).first()
        if identifier:
            created[scenario.code] = identifier.participant
            continue

        participant = Participant.objects.create(
            status=ParticipantStatus.ACTIVE,
            life_stage_track=scenario.track,
            preferred_language="ur",
        )
        ParticipantIdentifier.objects.create(
            participant=participant,
            identifier_type=ParticipantIdentifier.IdentifierType.INTERNAL_ALIAS,
            lookup_digest=digest,
            is_primary=True,
        )
        profile = ParticipantProfile(
            participant=participant,
            age_status=(
                KnowledgeState.UNKNOWN if scenario.age_years is None else KnowledgeState.KNOWN
            ),
            age_years=scenario.age_years,
            minor_status=scenario.minor_status,
            guardian_requirement=scenario.guardian_requirement,
            education_stage=scenario.education_stage,
            city="Synthetic Karachi",
            current_status="Synthetic development scenario",
        )
        profile.full_clean()
        profile.save()
        ReferralSource.objects.create(
            participant=participant,
            source_type=ReferralSource.SourceType.COMMUNITY,
            source_code="synthetic-development",
        )
        ConsentRecord.objects.create(
            participant=participant,
            consent_type=ConsentRecord.ConsentType.PARTICIPATION,
            status=ConsentRecord.ConsentStatus.UNKNOWN,
            policy_version="synthetic-development-no-policy-v1",
            actor_type="synthetic_fixture",
        )
        journey = ParticipantJourney.objects.create(participant=participant, track=scenario.track)

        if scenario.guardian_requirement == GuardianRequirement.REQUIRED:
            GuardianRelationship.objects.create(
                participant=participant,
                guardian_reference_digest=_digest(f"guardian:{scenario.code}"),
                relationship_type=GuardianRelationship.RelationshipType.UNKNOWN,
                handling_status=GuardianRelationship.HandlingStatus.REQUIRED,
                policy_version="unknown-unapproved",
            )

        if scenario.review_required:
            HumanReview.objects.create(
                journey=journey,
                review_type=(
                    HumanReview.ReviewType.MINOR_HANDLING
                    if scenario.minor_status == MinorStatus.MINOR
                    else HumanReview.ReviewType.FOUNDATION
                ),
                status=HumanReview.ReviewStatus.REQUIRED,
                summary="Synthetic scenario requiring human review.",
            )

        if scenario.access_candidate != AccessCategory.UNKNOWN:
            AccessDecision.objects.create(
                participant=participant,
                journey=journey,
                candidate_category=scenario.access_candidate,
                status=AccessDecision.DecisionStatus.PENDING,
                final_category=AccessCategory.UNKNOWN,
            )

        if scenario.contradictory_evidence:
            session = AssessmentSession.objects.create(
                journey=journey,
                definition_code="synthetic-shell",
                definition_version="1",
                status=AssessmentSession.SessionStatus.IN_PROGRESS,
            )
            source_one = EvidenceSource.objects.create(
                source_type=EvidenceSource.SourceType.SELF_REPORT,
                reference_kind="synthetic_fixture",
            )
            source_two = EvidenceSource.objects.create(
                source_type=EvidenceSource.SourceType.PRACTICAL_TASK,
                reference_kind="synthetic_fixture",
            )
            evidence_one = EvidenceItem(
                journey=journey,
                assessment_session=session,
                source=source_one,
                dimension_code="public_speaking_interest",
                category=EvidenceItem.Category.INTEREST,
                value_status=EvidenceItem.ValueStatus.KNOWN,
                text_value="Synthetic strong stated interest",
                direction=EvidenceItem.Direction.SUPPORTS,
                confidence_band=EvidenceItem.ConfidenceBand.MODERATE,
                confidence_reason="Synthetic self-report only",
            )
            evidence_one.full_clean()
            evidence_one.save()
            evidence_two = EvidenceItem(
                journey=journey,
                assessment_session=session,
                source=source_two,
                dimension_code="public_speaking_interest",
                category=EvidenceItem.Category.BEHAVIOUR,
                value_status=EvidenceItem.ValueStatus.KNOWN,
                text_value="Synthetic task was not attempted",
                direction=EvidenceItem.Direction.CONFLICTS,
                confidence_band=EvidenceItem.ConfidenceBand.LOW,
                confidence_reason="One synthetic observation",
            )
            evidence_two.full_clean()
            evidence_two.save()
            record_contradiction(
                journey_id=journey.id,
                evidence_ids=[evidence_one.id, evidence_two.id],
                summary="Synthetic self-report and task behaviour are inconsistent.",
                actor_type="synthetic_fixture",
            )

        created[scenario.code] = participant
    return created
