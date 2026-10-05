from __future__ import annotations

import pytest

from grow.journeys.models import ParticipantJourney
from grow.participants.models import (
    ConsentRecord,
    GuardianRequirement,
    KnowledgeState,
    LifeStageTrack,
    MinorStatus,
    Participant,
    ParticipantProfile,
    ParticipantStatus,
)


@pytest.fixture
def adult_journey(db: object) -> ParticipantJourney:
    participant = Participant.objects.create(
        status=ParticipantStatus.ACTIVE,
        life_stage_track=LifeStageTrack.UNIVERSITY,
        preferred_language="ur",
    )
    ParticipantProfile.objects.create(
        participant=participant,
        age_status=KnowledgeState.KNOWN,
        age_years=21,
        minor_status=MinorStatus.ADULT,
        guardian_requirement=GuardianRequirement.NOT_REQUIRED,
    )
    ConsentRecord.objects.create(
        participant=participant,
        consent_type=ConsentRecord.ConsentType.PARTICIPATION,
        status=ConsentRecord.ConsentStatus.GRANTED,
        policy_version="synthetic-development-v1",
        actor_type="synthetic_test",
    )
    return ParticipantJourney.objects.create(
        participant=participant, track=LifeStageTrack.UNIVERSITY
    )
