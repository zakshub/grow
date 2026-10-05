from __future__ import annotations

import pytest

from grow.audit.models import AuditEvent
from grow.journeys.models import JourneyState, ParticipantJourney, StateTransition
from grow.journeys.services import (
    InvalidTransition,
    StaleJourneyVersion,
    TransitionGuardFailed,
    transition_journey,
)
from grow.participants.models import (
    ConsentRecord,
    GuardianRelationship,
    GuardianRequirement,
    MinorStatus,
)
from grow.reviews.models import HumanReview
from grow.reviews.services import decide_human_review


def move(
    adult_journey: ParticipantJourney, to_state: str, command: str = "test"
) -> ParticipantJourney:
    return transition_journey(
        journey_id=adult_journey.id,
        to_state=to_state,
        command=command,
        reason="Synthetic test transition",
        actor_type="test",
        expected_version=adult_journey.state_version,
    )


@pytest.mark.django_db
def test_successful_transition_is_explicit_and_audited(
    adult_journey: ParticipantJourney,
) -> None:
    move(adult_journey, JourneyState.CONSENT_PENDING, "start_consent")
    transition = StateTransition.objects.get(journey=adult_journey)
    event = AuditEvent.objects.get(target_id=adult_journey.id)
    assert transition.from_state == JourneyState.NEW
    assert transition.to_state == JourneyState.CONSENT_PENDING
    assert event.event_type == "journey.transitioned"
    assert event.details["state_version_to"] == 1


@pytest.mark.django_db
def test_invalid_transition_fails_without_audit(adult_journey: ParticipantJourney) -> None:
    with pytest.raises(InvalidTransition):
        move(adult_journey, JourneyState.ASSESSMENT_IN_PROGRESS)
    assert not AuditEvent.objects.exists()
    assert adult_journey.current_state == JourneyState.NEW


@pytest.mark.django_db
def test_stale_state_version_fails(adult_journey: ParticipantJourney) -> None:
    move(adult_journey, JourneyState.CONSENT_PENDING)
    with pytest.raises(StaleJourneyVersion):
        transition_journey(
            journey_id=adult_journey.id,
            to_state=JourneyState.PROFILE_INCOMPLETE,
            command="complete_consent",
            reason="Synthetic stale request",
            actor_type="test",
            expected_version=0,
        )


@pytest.mark.django_db
def test_consent_guard_blocks_missing_consent(adult_journey: ParticipantJourney) -> None:
    ConsentRecord.objects.filter(participant=adult_journey.participant).delete()
    adult_journey = move(adult_journey, JourneyState.CONSENT_PENDING)
    with pytest.raises(TransitionGuardFailed, match="consent"):
        move(adult_journey, JourneyState.PROFILE_INCOMPLETE)


@pytest.mark.django_db
def test_unknown_minor_status_blocks_consent_gate(adult_journey: ParticipantJourney) -> None:
    profile = adult_journey.participant.profile
    profile.minor_status = MinorStatus.UNKNOWN
    profile.guardian_requirement = GuardianRequirement.UNKNOWN
    profile.save()
    adult_journey = move(adult_journey, JourneyState.CONSENT_PENDING)
    with pytest.raises(TransitionGuardFailed, match="Minor status is unknown"):
        move(adult_journey, JourneyState.PROFILE_INCOMPLETE)


@pytest.mark.django_db
def test_minor_guard_requires_explicit_guardian_handling(
    adult_journey: ParticipantJourney,
) -> None:
    profile = adult_journey.participant.profile
    profile.minor_status = MinorStatus.MINOR
    profile.guardian_requirement = GuardianRequirement.REQUIRED
    profile.save()
    adult_journey = move(adult_journey, JourneyState.CONSENT_PENDING)
    with pytest.raises(TransitionGuardFailed, match="Guardian handling"):
        move(adult_journey, JourneyState.PROFILE_INCOMPLETE)

    GuardianRelationship.objects.create(
        participant=adult_journey.participant,
        handling_status=GuardianRelationship.HandlingStatus.ACKNOWLEDGED,
        policy_version="synthetic-development-only",
    )
    adult_journey = move(adult_journey, JourneyState.PROFILE_INCOMPLETE)
    assert adult_journey.current_state == JourneyState.PROFILE_INCOMPLETE


@pytest.mark.django_db
def test_pause_and_resume_preserve_previous_state(adult_journey: ParticipantJourney) -> None:
    adult_journey = move(adult_journey, JourneyState.CONSENT_PENDING)
    adult_journey = move(adult_journey, JourneyState.PAUSED, "pause")
    assert adult_journey.resume_state == JourneyState.CONSENT_PENDING
    adult_journey = move(adult_journey, JourneyState.CONSENT_PENDING, "resume")
    assert adult_journey.resume_state == ""


@pytest.mark.django_db
def test_opt_out_closes_active_journey(adult_journey: ParticipantJourney) -> None:
    adult_journey = move(adult_journey, JourneyState.OPTED_OUT, "opt_out")
    assert adult_journey.current_state == JourneyState.OPTED_OUT
    assert adult_journey.is_active is False


@pytest.mark.django_db
def test_human_review_gate_blocks_unapproved_review(
    adult_journey: ParticipantJourney,
) -> None:
    adult_journey.current_state = JourneyState.HUMAN_REVIEW_REQUIRED
    adult_journey.save()
    HumanReview.objects.create(journey=adult_journey, status=HumanReview.ReviewStatus.REQUIRED)
    with pytest.raises(TransitionGuardFailed, match="approved human review"):
        move(adult_journey, JourneyState.RECOMMENDATION_READY)


@pytest.mark.django_db
def test_synthetic_adult_can_complete_state_shell(adult_journey: ParticipantJourney) -> None:
    states = [
        JourneyState.CONSENT_PENDING,
        JourneyState.PROFILE_INCOMPLETE,
        JourneyState.DISCOVERY_IN_PROGRESS,
        JourneyState.ASSESSMENT_IN_PROGRESS,
        JourneyState.HUMAN_REVIEW_REQUIRED,
    ]
    for state in states:
        adult_journey = move(adult_journey, state)
    review = HumanReview.objects.create(
        journey=adult_journey, status=HumanReview.ReviewStatus.REQUIRED
    )
    decide_human_review(
        review=review,
        status=HumanReview.ReviewStatus.APPROVED,
        reviewer_reference="synthetic-reviewer",
        decision="Synthetic foundation state shell approved.",
    )
    for state in [
        JourneyState.RECOMMENDATION_READY,
        JourneyState.ROADMAP_ACTIVE,
        JourneyState.FOLLOW_UP_DUE,
        JourneyState.COMPLETED,
    ]:
        adult_journey = move(adult_journey, state)
    assert adult_journey.current_state == JourneyState.COMPLETED
    assert adult_journey.transitions.count() == 9
    assert AuditEvent.objects.filter(target_id=adult_journey.id).count() == 9
