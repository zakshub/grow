from __future__ import annotations

import uuid
from datetime import timedelta

import pytest
from django.core.exceptions import ValidationError
from django.utils import timezone

from grow.access.models import AccessCategory, AccessDecision
from grow.access.services import decide_access
from grow.audit.models import AuditEvent
from grow.audit.services import record_audit_event
from grow.followups.models import FollowUp
from grow.journeys.models import ParticipantJourney
from grow.reviews.models import HumanOverride, HumanReview
from grow.reviews.services import decide_human_review, record_human_override


@pytest.mark.django_db
def test_override_requires_reviewer_reason_and_change(
    adult_journey: ParticipantJourney,
) -> None:
    review = HumanReview.objects.create(journey=adult_journey)
    override = HumanOverride(
        review=review,
        target_type="synthetic_result",
        target_id=uuid.uuid4(),
        original_result={"state": "unknown"},
        new_result={"state": "unknown"},
        reviewer_reference="",
        reason="",
    )
    with pytest.raises(ValidationError):
        override.full_clean()


@pytest.mark.django_db
def test_override_preserves_both_results_and_audits(
    adult_journey: ParticipantJourney,
) -> None:
    review = HumanReview.objects.create(journey=adult_journey)
    target_id = uuid.uuid4()
    override = record_human_override(
        review=review,
        target_type="synthetic_result",
        target_id=target_id,
        original_result={"state": "unknown"},
        new_result={"state": "review_required"},
        reviewer_reference="synthetic-reviewer-1",
        reason="Synthetic evidence conflict requires review.",
    )
    assert override.original_result == {"state": "unknown"}
    assert override.new_result == {"state": "review_required"}
    event = AuditEvent.objects.get(event_type="human.override_recorded")
    assert event.target_id == target_id
    assert event.details["original_result"] == {"state": "unknown"}


@pytest.mark.django_db
def test_override_is_append_only(adult_journey: ParticipantJourney) -> None:
    review = HumanReview.objects.create(journey=adult_journey)
    override = record_human_override(
        review=review,
        target_type="synthetic_result",
        target_id=uuid.uuid4(),
        original_result={"value": 1},
        new_result={"value": 2},
        reviewer_reference="synthetic-reviewer",
        reason="Synthetic reason",
    )
    override.reason = "Changed"
    with pytest.raises(ValueError, match="append-only"):
        override.save()


@pytest.mark.django_db
def test_pending_access_candidate_has_no_final_category(
    adult_journey: ParticipantJourney,
) -> None:
    decision = AccessDecision(
        participant=adult_journey.participant,
        journey=adult_journey,
        candidate_category=AccessCategory.REDUCED,
        status=AccessDecision.DecisionStatus.PENDING,
    )
    decision.full_clean()
    decision.save()
    assert decision.final_category == AccessCategory.UNKNOWN


@pytest.mark.django_db
def test_access_decision_requires_human_reviewer(
    adult_journey: ParticipantJourney,
) -> None:
    decision = AccessDecision(
        participant=adult_journey.participant,
        journey=adult_journey,
        candidate_category=AccessCategory.FREE,
        status=AccessDecision.DecisionStatus.APPROVED,
        final_category=AccessCategory.FREE,
    )
    with pytest.raises(ValidationError, match="reviewer"):
        decision.full_clean()


@pytest.mark.django_db
def test_access_decision_is_versioned_and_audited(adult_journey: ParticipantJourney) -> None:
    candidate = AccessDecision.objects.create(
        participant=adult_journey.participant,
        journey=adult_journey,
        candidate_category=AccessCategory.REDUCED,
        status=AccessDecision.DecisionStatus.PENDING,
    )
    decided = decide_access(
        pending_decision=candidate,
        status=AccessDecision.DecisionStatus.APPROVED,
        final_category=AccessCategory.REDUCED,
        reviewer_reference="synthetic-access-reviewer",
        reason="Synthetic test decision only.",
    )
    assert decided.supersedes == candidate
    assert decided.version == 2
    assert candidate.status == AccessDecision.DecisionStatus.PENDING
    assert AuditEvent.objects.filter(event_type="access.decision_recorded").exists()


@pytest.mark.django_db
def test_human_review_decision_is_audited(adult_journey: ParticipantJourney) -> None:
    review = HumanReview.objects.create(
        journey=adult_journey, status=HumanReview.ReviewStatus.REQUIRED
    )
    decided = decide_human_review(
        review=review,
        status=HumanReview.ReviewStatus.MORE_INFORMATION,
        reviewer_reference="synthetic-reviewer",
        decision="Synthetic evidence is incomplete.",
    )
    assert decided.decided_at is not None
    assert AuditEvent.objects.filter(event_type="human.review_decided").exists()


def test_access_domain_has_no_evidence_or_capability_field() -> None:
    field_names = {field.name for field in AccessDecision._meta.fields}
    assert "evidence" not in field_names
    assert "capability" not in field_names
    assert "score" not in field_names


@pytest.mark.django_db
def test_audit_event_is_append_only(adult_journey: ParticipantJourney) -> None:
    event = record_audit_event(
        event_type="synthetic.test",
        actor_type="test",
        target_type="participant_journey",
        target_id=adult_journey.id,
    )
    event.reason = "changed"
    with pytest.raises(ValueError, match="append-only"):
        event.save()
    with pytest.raises(ValueError, match="append-only"):
        event.delete()


@pytest.mark.django_db
def test_planned_follow_up_requires_due_date(adult_journey: ParticipantJourney) -> None:
    follow_up = FollowUp(
        journey=adult_journey,
        kind=FollowUp.FollowUpKind.SEVEN_DAY,
        status=FollowUp.FollowUpStatus.PLANNED,
    )
    with pytest.raises(ValidationError, match="due date"):
        follow_up.full_clean()
    follow_up.due_at = timezone.now() + timedelta(days=7)
    follow_up.full_clean()
