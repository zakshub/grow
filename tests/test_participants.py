from __future__ import annotations

import pytest
from django.core.exceptions import ValidationError

from grow.participants.models import (
    ConsentRecord,
    GuardianRequirement,
    KnowledgeState,
    MinorStatus,
    Participant,
    ParticipantIdentifier,
    ParticipantProfile,
)
from grow.participants.services import classify_minor_status, record_consent


@pytest.mark.django_db
def test_participant_and_profile_default_to_unknown() -> None:
    participant = Participant.objects.create()
    profile = ParticipantProfile.objects.create(participant=participant)
    assert participant.status == "unknown"
    assert profile.age_status == KnowledgeState.UNKNOWN
    assert profile.minor_status == MinorStatus.UNKNOWN
    assert profile.guardian_requirement == GuardianRequirement.UNKNOWN
    assert profile.age_years is None


@pytest.mark.django_db
def test_unknown_age_cannot_silently_hold_numeric_value() -> None:
    profile = ParticipantProfile(
        participant=Participant.objects.create(),
        age_status=KnowledgeState.UNKNOWN,
        age_years=0,
    )
    with pytest.raises(ValidationError):
        profile.full_clean()


@pytest.mark.django_db
def test_known_age_requires_value() -> None:
    profile = ParticipantProfile(
        participant=Participant.objects.create(), age_status=KnowledgeState.KNOWN
    )
    with pytest.raises(ValidationError):
        profile.full_clean()


def test_minor_status_is_unknown_without_approved_threshold() -> None:
    assert classify_minor_status(13) == MinorStatus.UNKNOWN
    assert classify_minor_status(None, approved_minor_age_threshold=18) == MinorStatus.UNKNOWN


def test_minor_status_can_be_detected_with_injected_threshold() -> None:
    assert classify_minor_status(13, approved_minor_age_threshold=18) == MinorStatus.MINOR
    assert classify_minor_status(18, approved_minor_age_threshold=18) == MinorStatus.ADULT


@pytest.mark.django_db
def test_identifier_requires_digest_or_ciphertext() -> None:
    identifier = ParticipantIdentifier(participant=Participant.objects.create())
    with pytest.raises(ValidationError):
        identifier.full_clean()


@pytest.mark.django_db
def test_ciphertext_identifier_requires_key_version() -> None:
    identifier = ParticipantIdentifier(
        participant=Participant.objects.create(), ciphertext="synthetic-ciphertext"
    )
    with pytest.raises(ValidationError):
        identifier.full_clean()


@pytest.mark.django_db
def test_consent_record_is_append_only() -> None:
    consent = ConsentRecord.objects.create(
        participant=Participant.objects.create(),
        consent_type=ConsentRecord.ConsentType.PARTICIPATION,
        status=ConsentRecord.ConsentStatus.UNKNOWN,
        policy_version="synthetic-v1",
    )
    consent.status = ConsentRecord.ConsentStatus.GRANTED
    with pytest.raises(ValueError, match="append-only"):
        consent.save()


@pytest.mark.django_db
def test_recording_consent_creates_audit_event() -> None:
    from grow.audit.models import AuditEvent

    participant = Participant.objects.create()
    consent = record_consent(
        participant=participant,
        consent_type=ConsentRecord.ConsentType.PARTICIPATION,
        status=ConsentRecord.ConsentStatus.GRANTED,
        policy_version="synthetic-v1",
        actor_type="synthetic_test",
    )
    event = AuditEvent.objects.get(event_type="consent.recorded")
    assert event.target_id == participant.id
    assert event.details["consent_record_id"] == str(consent.id)
