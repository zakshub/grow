from __future__ import annotations

import pytest

from grow.assessments.models import (
    AssessmentItemPresentation,
    AssessmentResponse,
    Contradiction,
    EvidenceItem,
)
from grow.assessments.services import (
    add_reviewer_observation,
    detect_contradictions,
    mark_evidence_reviewed,
    record_assessment_response,
)
from grow.audit.models import AuditEvent
from grow.journeys.models import ParticipantJourney
from grow.reviews.models import HumanReview
from grow.reviews.services import decide_human_review
from tests.assessment_helpers import PilotAssessment, create_pilot_assessment, start_test_session


def _response(
    adult_journey: ParticipantJourney, *, open_text: bool = False
) -> tuple[PilotAssessment, AssessmentResponse]:
    pilot = create_pilot_assessment()
    session = start_test_session(adult_journey, pilot)
    item = pilot.items["open_idea_story" if open_text else "logic_self_report"]
    presentation = AssessmentItemPresentation.objects.create(
        session=session,
        item=item,
        variant=item.variants.get(language="ur"),
        sequence=1,
        selection_status="ASK_MORE",
        selection_reason="Synthetic review test",
        selection_policy_version=pilot.version.selection_policy_version,
    )
    response = record_assessment_response(
        presentation=presentation,
        text_value="Synthetic story" if open_text else "",
        structured_value=None if open_text else "agree",
        actor_type="synthetic_test",
    )
    return pilot, response


@pytest.mark.django_db
def test_reviewer_can_add_structured_observation(adult_journey: ParticipantJourney) -> None:
    pilot, response = _response(adult_journey, open_text=True)
    observation = add_reviewer_observation(
        session=response.presentation.session,
        response=response,
        dimension=pilot.dimensions["idea_generation"],
        structured_value={
            "signal": "positive",
            "polarity": 0.5,
            "direction": "supports",
            "confidence_band": "low",
            "confidence_score": "0.35",
        },
        reviewer_reference="synthetic-reviewer",
        reason="Synthetic structured observation of an open response.",
    )
    evidence = EvidenceItem.objects.get(source__reference_id=observation.id)
    assert evidence.review_status == EvidenceItem.ReviewStatus.REVIEWED
    assert evidence.source.source_type == "human_observation"
    assert AuditEvent.objects.filter(event_type="assessment.observation_added").exists()


@pytest.mark.django_db
def test_evidence_review_creates_new_version_and_audit(
    adult_journey: ParticipantJourney,
) -> None:
    _pilot, response = _response(adult_journey)
    original = EvidenceItem.objects.get(source__reference_id=response.id)
    reviewed = mark_evidence_reviewed(
        evidence=original,
        review_status=EvidenceItem.ReviewStatus.REVIEWED,
        reviewer_reference="synthetic-reviewer",
        reason="Synthetic evidence checked against its response.",
    )
    assert reviewed.supersedes == original
    assert reviewed.version == 2
    assert original.review_status == EvidenceItem.ReviewStatus.UNREVIEWED
    assert AuditEvent.objects.filter(event_type="evidence.reviewed").exists()


@pytest.mark.django_db
def test_reviewer_can_request_more_assessment_evidence(
    adult_journey: ParticipantJourney,
) -> None:
    review = HumanReview.objects.create(
        journey=adult_journey,
        review_type=HumanReview.ReviewType.ASSESSMENT_EVIDENCE,
        status=HumanReview.ReviewStatus.REQUIRED,
    )
    decide_human_review(
        review=review,
        status=HumanReview.ReviewStatus.MORE_INFORMATION,
        reviewer_reference="synthetic-reviewer",
        decision="Collect another independent logical reasoning signal.",
    )
    assert review.status == HumanReview.ReviewStatus.MORE_INFORMATION
    assert AuditEvent.objects.filter(event_type="human.review_decided").exists()


@pytest.mark.django_db
def test_reviewer_can_inspect_response_evidence_and_provenance(
    adult_journey: ParticipantJourney,
) -> None:
    _pilot, response = _response(adult_journey)
    evidence = EvidenceItem.objects.select_related("source", "assessment_session").get(
        source__reference_id=response.id
    )
    assert evidence.source.reference_kind == "assessment_response"
    assert evidence.source.details["item_id"] == str(response.presentation.item_id)
    assert evidence.assessment_session is not None
    assert evidence.assessment_session.definition_version == "1"


@pytest.mark.django_db
def test_detecting_same_contradiction_is_idempotent(adult_journey: ParticipantJourney) -> None:
    pilot = create_pilot_assessment()
    session = start_test_session(adult_journey, pilot)
    for sequence, (code, value) in enumerate(
        (("speaking_self_report", "agree"), ("speaking_clarification", "avoid")), start=1
    ):
        item = pilot.items[code]
        presentation = AssessmentItemPresentation.objects.create(
            session=session,
            item=item,
            variant=item.variants.get(language="ur"),
            sequence=sequence,
            selection_status="ASK_MORE",
            selection_reason="Synthetic contradiction review test",
            selection_policy_version=pilot.version.selection_policy_version,
        )
        record_assessment_response(
            presentation=presentation,
            structured_value=value,
            actor_type="synthetic_test",
        )
    assert len(detect_contradictions(session=session)) == 1
    assert detect_contradictions(session=session) == []
    assert Contradiction.objects.filter(journey=adult_journey).count() == 1
