from __future__ import annotations

import uuid

from django.db import transaction

from grow.audit.services import record_audit_event
from grow.journeys.models import JourneyState, ParticipantJourney, StateTransition
from grow.participants.models import (
    ConsentRecord,
    GuardianRelationship,
    GuardianRequirement,
    MinorStatus,
    ParticipantProfile,
)


class JourneyTransitionError(Exception):
    pass


class InvalidTransition(JourneyTransitionError):
    pass


class TransitionGuardFailed(JourneyTransitionError):
    pass


class StaleJourneyVersion(JourneyTransitionError):
    pass


NORMAL_TRANSITIONS: dict[str, set[str]] = {
    JourneyState.NEW: {JourneyState.CONSENT_PENDING},
    JourneyState.CONSENT_PENDING: {JourneyState.PROFILE_INCOMPLETE},
    JourneyState.PROFILE_INCOMPLETE: {JourneyState.DISCOVERY_IN_PROGRESS},
    JourneyState.DISCOVERY_IN_PROGRESS: {JourneyState.ASSESSMENT_IN_PROGRESS},
    JourneyState.ASSESSMENT_IN_PROGRESS: {
        JourneyState.EXPERIMENT_PENDING,
        JourneyState.HUMAN_REVIEW_REQUIRED,
    },
    JourneyState.EXPERIMENT_PENDING: {JourneyState.EXPERIMENT_SUBMITTED},
    JourneyState.EXPERIMENT_SUBMITTED: {JourneyState.HUMAN_REVIEW_REQUIRED},
    JourneyState.HUMAN_REVIEW_REQUIRED: {
        JourneyState.ASSESSMENT_IN_PROGRESS,
        JourneyState.EXPERIMENT_PENDING,
        JourneyState.RECOMMENDATION_READY,
    },
    JourneyState.RECOMMENDATION_READY: {JourneyState.ROADMAP_ACTIVE},
    JourneyState.ROADMAP_ACTIVE: {JourneyState.FOLLOW_UP_DUE},
    JourneyState.FOLLOW_UP_DUE: {JourneyState.ROADMAP_ACTIVE, JourneyState.COMPLETED},
}

PAUSABLE_STATES = {
    JourneyState.CONSENT_PENDING,
    JourneyState.PROFILE_INCOMPLETE,
    JourneyState.DISCOVERY_IN_PROGRESS,
    JourneyState.ASSESSMENT_IN_PROGRESS,
    JourneyState.EXPERIMENT_PENDING,
    JourneyState.EXPERIMENT_SUBMITTED,
    JourneyState.HUMAN_REVIEW_REQUIRED,
    JourneyState.RECOMMENDATION_READY,
    JourneyState.ROADMAP_ACTIVE,
    JourneyState.FOLLOW_UP_DUE,
}

OPT_OUT_STATES = {state for state, _label in JourneyState.choices} - {
    JourneyState.COMPLETED,
    JourneyState.OPTED_OUT,
}


def _latest_participation_consent(participant_id: uuid.UUID) -> ConsentRecord | None:
    return (
        ConsentRecord.objects.filter(
            participant_id=participant_id,
            consent_type=ConsentRecord.ConsentType.PARTICIPATION,
        )
        .order_by("-recorded_at", "-id")
        .first()
    )


def _validate_consent_and_guardian(journey: ParticipantJourney) -> None:
    consent = _latest_participation_consent(journey.participant_id)
    if consent is None or consent.status != ConsentRecord.ConsentStatus.GRANTED:
        raise TransitionGuardFailed("Active participation consent is required")

    profile = ParticipantProfile.objects.filter(participant_id=journey.participant_id).first()
    if profile is None:
        raise TransitionGuardFailed("Participant profile is required")
    if profile.minor_status == MinorStatus.UNKNOWN:
        raise TransitionGuardFailed("Minor status is unknown")
    if profile.guardian_requirement == GuardianRequirement.UNKNOWN:
        raise TransitionGuardFailed("Guardian requirement is unknown")
    if profile.guardian_requirement == GuardianRequirement.REQUIRED:
        acknowledged = GuardianRelationship.objects.filter(
            participant_id=journey.participant_id,
            handling_status=GuardianRelationship.HandlingStatus.ACKNOWLEDGED,
        ).exists()
        if not acknowledged:
            raise TransitionGuardFailed("Guardian handling is unresolved")


def _validate_human_review(journey: ParticipantJourney) -> None:
    from grow.reviews.models import HumanReview

    if not HumanReview.objects.filter(
        journey=journey, status=HumanReview.ReviewStatus.APPROVED
    ).exists():
        raise TransitionGuardFailed("An approved human review is required")


def _validate_transition(journey: ParticipantJourney, to_state: str) -> None:
    from_state = journey.current_state
    if to_state == JourneyState.PAUSED and from_state in PAUSABLE_STATES:
        return
    if to_state == JourneyState.OPTED_OUT and from_state in OPT_OUT_STATES:
        return
    if from_state == JourneyState.PAUSED and journey.resume_state == to_state:
        return
    if to_state not in NORMAL_TRANSITIONS.get(from_state, set()):
        raise InvalidTransition(f"Transition {from_state} -> {to_state} is not allowed")

    if from_state == JourneyState.CONSENT_PENDING and to_state == JourneyState.PROFILE_INCOMPLETE:
        _validate_consent_and_guardian(journey)
    if (
        from_state == JourneyState.HUMAN_REVIEW_REQUIRED
        and to_state == JourneyState.RECOMMENDATION_READY
    ):
        _validate_human_review(journey)


@transaction.atomic
def transition_journey(
    *,
    journey_id: uuid.UUID,
    to_state: str,
    command: str,
    reason: str,
    actor_type: str,
    actor_reference: str = "",
    expected_version: int | None = None,
    policy_version: str = "foundation-v1",
    correlation_id: uuid.UUID | None = None,
) -> ParticipantJourney:
    journey = (
        ParticipantJourney.objects.select_for_update()
        .select_related("participant")
        .get(pk=journey_id)
    )
    if expected_version is not None and journey.state_version != expected_version:
        raise StaleJourneyVersion(
            f"Expected state version {expected_version}, found {journey.state_version}"
        )
    if not reason.strip():
        raise JourneyTransitionError("Transition reason is required")

    _validate_transition(journey, to_state)
    from_state = journey.current_state
    from_version = journey.state_version

    if to_state == JourneyState.PAUSED:
        journey.resume_state = from_state
    elif from_state == JourneyState.PAUSED:
        journey.resume_state = ""

    journey.current_state = to_state
    journey.state_version += 1
    if to_state in {JourneyState.COMPLETED, JourneyState.OPTED_OUT}:
        journey.is_active = False
    journey.save(
        update_fields=[
            "current_state",
            "resume_state",
            "state_version",
            "is_active",
            "updated_at",
        ]
    )

    transition = StateTransition.objects.create(
        journey=journey,
        from_state=from_state,
        to_state=to_state,
        command=command,
        reason=reason,
        actor_type=actor_type,
        actor_reference=actor_reference,
        policy_version=policy_version,
        correlation_id=correlation_id,
        state_version_from=from_version,
        state_version_to=journey.state_version,
    )
    record_audit_event(
        event_type="journey.transitioned",
        actor_type=actor_type,
        actor_reference=actor_reference,
        target_type="participant_journey",
        target_id=journey.id,
        reason=reason,
        correlation_id=correlation_id,
        details={
            "transition_id": str(transition.id),
            "from_state": from_state,
            "to_state": to_state,
            "state_version_from": from_version,
            "state_version_to": journey.state_version,
            "policy_version": policy_version,
        },
    )
    return journey
