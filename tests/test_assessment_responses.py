from __future__ import annotations

from typing import Any

import pytest
from django.core.exceptions import ValidationError

from grow.assessments.models import (
    AssessmentItem,
    AssessmentItemPresentation,
    AssessmentLifecycle,
    DimensionEvidence,
    EvidenceItem,
    EvidenceSource,
)
from grow.assessments.services import publish_assessment_version, record_assessment_response
from grow.audit.models import AuditEvent
from grow.journeys.models import ParticipantJourney
from tests.assessment_helpers import add_variant, create_pilot_assessment, start_test_session


def _presentation(
    journey: ParticipantJourney,
    *,
    item_type: str,
    structured_value: Any = None,
    text_value: str = "",
    schema: dict[str, Any] | None = None,
) -> tuple[AssessmentItemPresentation, Any, str]:
    pilot = create_pilot_assessment(publish=False)
    template = pilot.items["logic_self_report"]
    item = AssessmentItem.objects.create(
        assessment_version=pilot.version,
        section=template.section,
        dimension=pilot.dimensions["logical_reasoning"],
        code=f"type-{item_type}",
        item_type=item_type,
        order=90,
        response_schema=schema or {},
        interpretation_rules={},
    )
    variant = add_variant(item)
    publish_assessment_version(
        assessment_version=pilot.version,
        lifecycle=AssessmentLifecycle.PILOT,
        actor_reference="synthetic-test-publisher",
    )
    session = start_test_session(journey, pilot)
    presentation = AssessmentItemPresentation.objects.create(
        session=session,
        item=item,
        variant=variant,
        sequence=1,
        selection_status="ASK_MORE",
        selection_reason="Synthetic response type test",
        selection_policy_version=pilot.version.selection_policy_version,
    )
    return presentation, structured_value, text_value


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("item_type", "value", "text", "schema"),
    [
        (AssessmentItem.ItemType.LIKERT, "agree", "", {"options": ["agree"]}),
        (AssessmentItem.ItemType.BINARY, True, "", {"options": [True, False]}),
        (AssessmentItem.ItemType.SINGLE_CHOICE, "a", "", {"options": ["a", "b"]}),
        (AssessmentItem.ItemType.MULTI_CHOICE, ["a", "b"], "", {}),
        (AssessmentItem.ItemType.RANKING, ["b", "a"], "", {}),
        (AssessmentItem.ItemType.NUMERIC, 7, "", {"minimum": 0, "maximum": 10}),
        (AssessmentItem.ItemType.SHORT_TEXT, None, "Synthetic short answer", {}),
        (AssessmentItem.ItemType.LONG_TEXT, None, "Synthetic long answer", {}),
        (AssessmentItem.ItemType.SCENARIO_CHOICE, "a", "", {"options": ["a"]}),
    ],
)
def test_all_item_types_capture_responses(
    adult_journey: ParticipantJourney,
    item_type: str,
    value: Any,
    text: str,
    schema: dict[str, Any],
) -> None:
    presentation, structured_value, text_value = _presentation(
        adult_journey,
        item_type=item_type,
        structured_value=value,
        text_value=text,
        schema=schema,
    )
    response = record_assessment_response(
        presentation=presentation,
        structured_value=structured_value,
        text_value=text_value,
        actor_type="synthetic_test",
    )
    assert response.presentation == presentation
    assert AuditEvent.objects.filter(event_type="assessment.response_recorded").exists()


@pytest.mark.django_db
def test_structured_response_creates_traceable_evidence(
    adult_journey: ParticipantJourney,
) -> None:
    pilot = create_pilot_assessment()
    session = start_test_session(adult_journey, pilot)
    item = pilot.items["logic_self_report"]
    variant = item.variants.get(language="ur")
    presentation = AssessmentItemPresentation.objects.create(
        session=session,
        item=item,
        variant=variant,
        sequence=1,
        selection_status="ASK_MORE",
        selection_reason="Synthetic trace test",
        selection_policy_version=pilot.version.selection_policy_version,
    )
    response = record_assessment_response(
        presentation=presentation,
        structured_value="agree",
        actor_type="synthetic_test",
    )
    evidence = EvidenceItem.objects.get(source__reference_id=response.id)
    link = DimensionEvidence.objects.get(evidence_item=evidence)
    assert evidence.dimension == pilot.dimensions["logical_reasoning"]
    assert evidence.source.source_type == EvidenceSource.SourceType.SELF_REPORT
    assert evidence.normalized_interpretation == {
        "pilot_signal": "positive",
        "polarity": 1,
    }
    assert link.independent_source_key == f"response:{response.id}"
    assert link.eligible_for_aggregation is True


@pytest.mark.django_db
def test_open_response_is_stored_but_not_automatically_interpreted(
    adult_journey: ParticipantJourney,
) -> None:
    pilot = create_pilot_assessment()
    session = start_test_session(adult_journey, pilot)
    item = pilot.items["open_idea_story"]
    presentation = AssessmentItemPresentation.objects.create(
        session=session,
        item=item,
        variant=item.variants.get(language="ur"),
        sequence=1,
        selection_status="ASK_MORE",
        selection_reason="Synthetic open discovery test",
        selection_policy_version=pilot.version.selection_policy_version,
    )
    response = record_assessment_response(
        presentation=presentation,
        text_value="Synthetic story, not participant data.",
        actor_type="synthetic_test",
    )
    evidence = EvidenceItem.objects.get(source__reference_id=response.id)
    assert evidence.text_value == "Synthetic story, not participant data."
    assert evidence.normalized_interpretation is None
    assert evidence.interpretation_method == "none"
    assert evidence.review_status == EvidenceItem.ReviewStatus.NEEDS_CLARIFICATION
    assert evidence.dimension_evidence_link.eligible_for_aggregation is False


@pytest.mark.django_db
def test_invalid_structured_response_is_rejected(adult_journey: ParticipantJourney) -> None:
    presentation, _, _ = _presentation(
        adult_journey,
        item_type=AssessmentItem.ItemType.SINGLE_CHOICE,
        schema={"options": ["allowed"]},
    )
    with pytest.raises(ValidationError, match="allowed option"):
        record_assessment_response(
            presentation=presentation,
            structured_value="not-allowed",
        )


@pytest.mark.django_db
def test_numeric_range_is_enforced(adult_journey: ParticipantJourney) -> None:
    presentation, _, _ = _presentation(
        adult_journey,
        item_type=AssessmentItem.ItemType.NUMERIC,
        schema={"minimum": 0, "maximum": 10},
    )
    with pytest.raises(ValidationError, match="exceeds"):
        record_assessment_response(presentation=presentation, structured_value=11)


def test_required_evidence_source_types_are_available() -> None:
    values = {value for value, _label in EvidenceSource.SourceType.choices}
    assert {
        "self_report",
        "structured_question",
        "open_response",
        "practical_task",
        "human_observation",
        "behavioural_signal",
        "historical_example",
        "follow_up",
        "reviewer_judgment",
    }.issubset(values)
