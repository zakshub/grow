from __future__ import annotations

import pytest

from grow.assessments.engine import (
    NextAssessmentAction,
    build_assessment_snapshot,
    evaluate_assessment_session,
    present_next_item,
    select_next_item,
)
from grow.assessments.models import (
    AssessmentItemPresentation,
    AssessmentSession,
    Contradiction,
    DimensionResult,
)
from grow.assessments.services import (
    add_reviewer_observation,
    detect_contradictions,
    publish_assessment_version,
    record_assessment_response,
    resolve_contradiction,
)
from grow.audit.models import AuditEvent
from grow.journeys.models import ParticipantJourney
from grow.reviews.models import HumanReview
from tests.assessment_helpers import create_pilot_assessment, start_test_session


def _answer(
    session: AssessmentSession, item_code: str, value: object
) -> AssessmentItemPresentation:
    assessment_version = session.assessment_version
    assert assessment_version is not None
    item = assessment_version.items.get(code=item_code)
    presentation = AssessmentItemPresentation.objects.create(
        session=session,
        item=item,
        variant=item.variants.get(language="ur"),
        sequence=session.presentations.count() + 1,
        selection_status="ASK_MORE",
        selection_reason="Synthetic engine test",
        selection_policy_version=assessment_version.selection_policy_version,
    )
    record_assessment_response(
        presentation=presentation,
        structured_value=value,
        actor_type="synthetic_test",
    )
    return presentation


@pytest.mark.django_db
def test_snapshot_preserves_unknown_dimensions(adult_journey: ParticipantJourney) -> None:
    pilot = create_pilot_assessment()
    session = start_test_session(adult_journey, pilot)
    snapshot = build_assessment_snapshot(session=session)
    assert snapshot.unknown_dimension_count == 3
    assert all(
        result.sufficiency == DimensionResult.Sufficiency.UNKNOWN for result in snapshot.dimensions
    )
    assert all(result.confidence_score is None for result in snapshot.dimensions)


@pytest.mark.django_db
def test_one_signal_is_tentative_not_low_ability(adult_journey: ParticipantJourney) -> None:
    pilot = create_pilot_assessment()
    session = start_test_session(adult_journey, pilot)
    _answer(session, "logic_self_report", "agree")
    snapshot = build_assessment_snapshot(session=session)
    logical = next(
        item for item in snapshot.dimensions if item.dimension_code == "logical_reasoning"
    )
    assert logical.sufficiency == DimensionResult.Sufficiency.TENTATIVE
    assert logical.independent_source_count == 1
    assert logical.next_action == "Collect another independent signal."


@pytest.mark.django_db
def test_diverse_independent_evidence_can_be_supported(
    adult_journey: ParticipantJourney,
) -> None:
    pilot = create_pilot_assessment()
    session = start_test_session(adult_journey, pilot)
    presentation = _answer(session, "logic_self_report", "agree")
    add_reviewer_observation(
        session=session,
        response=presentation.response,
        dimension=pilot.dimensions["logical_reasoning"],
        structured_value={
            "signal": "positive",
            "polarity": 1,
            "direction": "supports",
            "confidence_band": "moderate",
            "confidence_score": "0.60",
        },
        reviewer_reference="synthetic-reviewer",
        reason="Synthetic structured observation.",
    )
    snapshot = build_assessment_snapshot(session=session)
    logical = next(
        item for item in snapshot.dimensions if item.dimension_code == "logical_reasoning"
    )
    assert logical.sufficiency == DimensionResult.Sufficiency.SUPPORTED
    assert logical.confidence_band in {"moderate", "high"}
    persisted = DimensionResult.objects.filter(
        session=session, dimension=pilot.dimensions["logical_reasoning"]
    ).latest("calculated_at")
    assert persisted.calculation_inputs["independent_source_count"] == 2
    assert "formula" in persisted.calculation_inputs


@pytest.mark.django_db
def test_repeated_same_source_type_is_insufficient(adult_journey: ParticipantJourney) -> None:
    pilot = create_pilot_assessment()
    session = start_test_session(adult_journey, pilot)
    _answer(session, "logic_self_report", "agree")
    _answer(session, "logic_second_signal", True)
    snapshot = build_assessment_snapshot(session=session)
    logical = next(
        item for item in snapshot.dimensions if item.dimension_code == "logical_reasoning"
    )
    assert logical.independent_source_count == 2
    assert logical.source_type_count == 1
    assert logical.sufficiency == DimensionResult.Sufficiency.INSUFFICIENT


@pytest.mark.django_db
def test_contradiction_detection_preserves_both_signals(
    adult_journey: ParticipantJourney,
) -> None:
    pilot = create_pilot_assessment()
    session = start_test_session(adult_journey, pilot)
    first = _answer(session, "speaking_self_report", "agree")
    second = _answer(session, "speaking_clarification", "avoid")
    contradictions = detect_contradictions(session=session)
    assert len(contradictions) == 1
    contradiction = contradictions[0]
    assert set(contradiction.evidence_items.values_list("source__reference_id", flat=True)) == {
        first.response.id,
        second.response.id,
    }
    snapshot = build_assessment_snapshot(session=session)
    speaking = next(
        item for item in snapshot.dimensions if item.dimension_code == "public_speaking_comfort"
    )
    assert speaking.sufficiency == DimensionResult.Sufficiency.CONTRADICTORY
    assert speaking.unresolved_contradiction_count == 1


@pytest.mark.django_db
def test_contradiction_resolution_is_audited_and_does_not_delete_evidence(
    adult_journey: ParticipantJourney,
) -> None:
    pilot = create_pilot_assessment()
    session = start_test_session(adult_journey, pilot)
    _answer(session, "speaking_self_report", "agree")
    _answer(session, "speaking_clarification", "avoid")
    contradiction = detect_contradictions(session=session)[0]
    evidence_ids = set(contradiction.evidence_items.values_list("id", flat=True))
    resolve_contradiction(
        contradiction=contradiction,
        resolution_status=Contradiction.ResolutionStatus.ACCEPTED_UNCERTAINTY,
        resolution="Synthetic context-dependent difference retained.",
        reviewer_reference="synthetic-reviewer",
    )
    contradiction.refresh_from_db()
    assert contradiction.resolution_status == Contradiction.ResolutionStatus.ACCEPTED_UNCERTAINTY
    assert set(contradiction.evidence_items.values_list("id", flat=True)) == evidence_ids
    assert AuditEvent.objects.filter(event_type="evidence.contradiction_resolved").exists()


@pytest.mark.django_db
def test_adaptive_selector_prioritises_missing_required_dimension(
    adult_journey: ParticipantJourney,
) -> None:
    pilot = create_pilot_assessment()
    session = start_test_session(adult_journey, pilot)
    decision = select_next_item(session)
    assert decision.action == NextAssessmentAction.ASK_MORE
    assert decision.dimension_code == "logical_reasoning"
    assert decision.variant is not None
    assert decision.variant.language == "ur"


@pytest.mark.django_db
def test_presented_item_records_selection_reason_and_audit(
    adult_journey: ParticipantJourney,
) -> None:
    pilot = create_pilot_assessment()
    session = start_test_session(adult_journey, pilot)
    decision, presentation = present_next_item(session=session)
    assert decision.action == NextAssessmentAction.ASK_MORE
    assert presentation is not None
    assert presentation.selection_reason
    assert AuditEvent.objects.filter(event_type="assessment.item_presented").exists()


@pytest.mark.django_db
def test_maximum_item_limit_requires_human_review(adult_journey: ParticipantJourney) -> None:
    pilot = create_pilot_assessment(maximum_items=1)
    session = start_test_session(adult_journey, pilot, maximum_items=1)
    _answer(session, "logic_self_report", "agree")
    decision = select_next_item(session)
    assert decision.action == NextAssessmentAction.HUMAN_REVIEW_REQUIRED
    snapshot = evaluate_assessment_session(session=session)
    assert snapshot.human_review_required is True
    assert session.sufficiency_status == AssessmentSession.SufficiencyStatus.REVIEW_REQUIRED
    assert HumanReview.objects.filter(
        journey=adult_journey,
        review_type=HumanReview.ReviewType.ASSESSMENT_EVIDENCE,
    ).exists()


@pytest.mark.django_db
def test_presented_unanswered_item_still_counts_toward_burden_limit(
    adult_journey: ParticipantJourney,
) -> None:
    pilot = create_pilot_assessment(maximum_items=1)
    session = start_test_session(adult_journey, pilot, maximum_items=1)
    decision, presentation = present_next_item(session=session)
    assert decision.action == NextAssessmentAction.ASK_MORE
    assert presentation is not None
    assert select_next_item(session).action == NextAssessmentAction.HUMAN_REVIEW_REQUIRED


@pytest.mark.django_db
def test_no_pinned_version_returns_unknown(adult_journey: ParticipantJourney) -> None:
    session = AssessmentSession.objects.create(
        journey=adult_journey,
        status=AssessmentSession.SessionStatus.IN_PROGRESS,
    )
    decision = select_next_item(session)
    snapshot = build_assessment_snapshot(session=session)
    assert decision.action == NextAssessmentAction.UNKNOWN
    assert snapshot.recommended_next_action == NextAssessmentAction.UNKNOWN


@pytest.mark.django_db
def test_supported_required_dimension_can_stop_questioning(
    adult_journey: ParticipantJourney,
) -> None:
    pilot = create_pilot_assessment(publish=False)
    pilot.version.dimension_requirements.exclude(
        dimension=pilot.dimensions["logical_reasoning"]
    ).update(required=False)
    publish_assessment_version(
        assessment_version=pilot.version,
        lifecycle="pilot",
        actor_reference="synthetic-test-publisher",
    )
    session = start_test_session(adult_journey, pilot)
    presentation = _answer(session, "logic_self_report", "agree")
    add_reviewer_observation(
        session=session,
        response=presentation.response,
        dimension=pilot.dimensions["logical_reasoning"],
        structured_value={
            "signal": "positive",
            "polarity": 1,
            "direction": "supports",
            "confidence_band": "moderate",
            "confidence_score": "0.6",
        },
        reviewer_reference="synthetic-reviewer",
        reason="Synthetic independent observation.",
    )
    assert select_next_item(session).action == NextAssessmentAction.SUFFICIENT
    snapshot = evaluate_assessment_session(session=session)
    assert snapshot.recommended_next_action == NextAssessmentAction.SUFFICIENT
    assert session.status == AssessmentSession.SessionStatus.COMPLETED


@pytest.mark.django_db
def test_dimension_result_versions_preserve_historical_calculations(
    adult_journey: ParticipantJourney,
) -> None:
    pilot = create_pilot_assessment()
    session = start_test_session(adult_journey, pilot)
    build_assessment_snapshot(session=session)
    _answer(session, "logic_self_report", "agree")
    build_assessment_snapshot(session=session)
    results = DimensionResult.objects.filter(
        session=session, dimension=pilot.dimensions["logical_reasoning"]
    ).order_by("version")
    assert [result.version for result in results] == [1, 2]
    assert results[1].supersedes == results[0]
    assert results[0].sufficiency == DimensionResult.Sufficiency.UNKNOWN
    assert results[1].sufficiency == DimensionResult.Sufficiency.TENTATIVE
