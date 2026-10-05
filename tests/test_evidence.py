from __future__ import annotations

import uuid

import pytest
from django.core.exceptions import ValidationError

from grow.assessments.models import EvidenceItem, EvidenceSource
from grow.assessments.services import record_contradiction
from grow.journeys.models import ParticipantJourney


def evidence_source() -> EvidenceSource:
    return EvidenceSource.objects.create(
        source_type=EvidenceSource.SourceType.SELF_REPORT,
        reference_kind="synthetic_test",
        provenance_version="test-v1",
    )


@pytest.mark.django_db
def test_unknown_evidence_preserves_absence(adult_journey: ParticipantJourney) -> None:
    item = EvidenceItem(
        journey=adult_journey,
        source=evidence_source(),
        dimension_code="logical_reasoning",
        value_status=EvidenceItem.ValueStatus.UNKNOWN,
        confidence_band=EvidenceItem.ConfidenceBand.UNKNOWN,
    )
    item.full_clean()
    item.save()
    assert item.numeric_value is None
    assert item.text_value == ""
    assert item.confidence_score is None


@pytest.mark.django_db
def test_unknown_evidence_cannot_become_zero(adult_journey: ParticipantJourney) -> None:
    item = EvidenceItem(
        journey=adult_journey,
        source=evidence_source(),
        dimension_code="logical_reasoning",
        value_status=EvidenceItem.ValueStatus.UNKNOWN,
        numeric_value=0,
    )
    with pytest.raises(ValidationError, match="Unknown evidence"):
        item.full_clean()


@pytest.mark.django_db
def test_known_evidence_requires_value(adult_journey: ParticipantJourney) -> None:
    item = EvidenceItem(
        journey=adult_journey,
        source=evidence_source(),
        dimension_code="logical_reasoning",
        value_status=EvidenceItem.ValueStatus.KNOWN,
    )
    with pytest.raises(ValidationError, match="explicit value"):
        item.full_clean()


@pytest.mark.django_db
def test_unknown_confidence_cannot_have_score(adult_journey: ParticipantJourney) -> None:
    item = EvidenceItem(
        journey=adult_journey,
        source=evidence_source(),
        dimension_code="logical_reasoning",
        value_status=EvidenceItem.ValueStatus.KNOWN,
        text_value="Synthetic observation",
        confidence_band=EvidenceItem.ConfidenceBand.UNKNOWN,
        confidence_score=0,
    )
    with pytest.raises(ValidationError, match="Unknown confidence"):
        item.full_clean()


@pytest.mark.django_db
def test_evidence_source_provenance_is_preserved(
    adult_journey: ParticipantJourney,
) -> None:
    source = evidence_source()
    item = EvidenceItem.objects.create(
        journey=adult_journey,
        source=source,
        dimension_code="curiosity",
        value_status=EvidenceItem.ValueStatus.KNOWN,
        text_value="Synthetic repeated research behaviour",
        confidence_band=EvidenceItem.ConfidenceBand.LOW,
    )
    assert item.source.reference_kind == "synthetic_test"
    assert item.source.provenance_version == "test-v1"


@pytest.mark.django_db
def test_evidence_is_append_only(adult_journey: ParticipantJourney) -> None:
    item = EvidenceItem.objects.create(
        journey=adult_journey,
        source=evidence_source(),
        dimension_code="curiosity",
    )
    item.dimension_code = "changed"
    with pytest.raises(ValueError, match="append-only"):
        item.save()


@pytest.mark.django_db
def test_evidence_version_requires_same_chain(adult_journey: ParticipantJourney) -> None:
    first = EvidenceItem.objects.create(
        journey=adult_journey,
        source=evidence_source(),
        dimension_code="curiosity",
    )
    second = EvidenceItem(
        journey=adult_journey,
        source=evidence_source(),
        dimension_code="curiosity",
        version=2,
        supersedes=first,
        evidence_chain_id=uuid.uuid4(),
    )
    with pytest.raises(ValidationError, match="same chain"):
        second.full_clean()


@pytest.mark.django_db
def test_contradiction_requires_two_items(adult_journey: ParticipantJourney) -> None:
    item = EvidenceItem.objects.create(
        journey=adult_journey,
        source=evidence_source(),
        dimension_code="curiosity",
    )
    with pytest.raises(ValidationError, match="at least two"):
        record_contradiction(
            journey_id=adult_journey.id,
            evidence_ids=[item.id],
            summary="Synthetic contradiction",
            actor_type="test",
        )


@pytest.mark.django_db
def test_contradiction_preserves_both_evidence_items(
    adult_journey: ParticipantJourney,
) -> None:
    items = [
        EvidenceItem.objects.create(
            journey=adult_journey,
            source=evidence_source(),
            dimension_code="public_speaking",
            value_status=EvidenceItem.ValueStatus.KNOWN,
            text_value=value,
        )
        for value in ("Synthetic stated interest", "Synthetic avoided task")
    ]
    contradiction = record_contradiction(
        journey_id=adult_journey.id,
        evidence_ids=[item.id for item in items],
        summary="Synthetic conflict",
        actor_type="test",
    )
    assert set(contradiction.evidence_items.values_list("id", flat=True)) == {
        item.id for item in items
    }
