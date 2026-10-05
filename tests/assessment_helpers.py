from __future__ import annotations

from dataclasses import dataclass

from grow.assessments.models import (
    AssessmentDefinition,
    AssessmentDimension,
    AssessmentDimensionRequirement,
    AssessmentItem,
    AssessmentItemVariant,
    AssessmentLifecycle,
    AssessmentSection,
    AssessmentSession,
    AssessmentVersion,
    DimensionCategory,
)
from grow.assessments.services import publish_assessment_version, start_assessment_session
from grow.journeys.models import ParticipantJourney
from grow.participants.models import EducationStage


@dataclass(frozen=True)
class PilotAssessment:
    version: AssessmentVersion
    dimensions: dict[str, AssessmentDimension]
    items: dict[str, AssessmentItem]


def add_variant(
    item: AssessmentItem,
    *,
    language: str = "ur",
    audience: str = AssessmentItemVariant.Audience.UNIVERSITY,
    education_stage: str = EducationStage.UNIVERSITY,
    prompt: str = "مصنوعی آزمائشی سوال",
) -> AssessmentItemVariant:
    return AssessmentItemVariant.objects.create(
        item=item,
        language=language,
        locale="pk",
        audience=audience,
        education_stage=education_stage,
        prompt=prompt,
        helper_text="Synthetic pilot test wording.",
    )


def create_pilot_assessment(*, maximum_items: int = 8, publish: bool = True) -> PilotAssessment:
    definition = AssessmentDefinition.objects.create(
        code="test-progressive-assessment",
        title="Synthetic test assessment",
        purpose="Exercise deterministic tests only.",
    )
    version = AssessmentVersion.objects.create(
        definition=definition,
        version=1,
        maximum_items=maximum_items,
        limitations="Synthetic tests; no validity claim.",
    )
    section = AssessmentSection.objects.create(
        assessment_version=version,
        code="core",
        order=1,
        title="Core synthetic items",
    )
    dimensions = {
        "logical_reasoning": AssessmentDimension.objects.create(
            code="logical_reasoning",
            category=DimensionCategory.COGNITIVE_FUNCTIONAL,
            name="Logical reasoning",
        ),
        "public_speaking_comfort": AssessmentDimension.objects.create(
            code="public_speaking_comfort",
            category=DimensionCategory.COMMUNICATION_SOCIAL,
            name="Public speaking comfort",
        ),
        "idea_generation": AssessmentDimension.objects.create(
            code="idea_generation",
            category=DimensionCategory.CREATIVITY,
            name="Idea generation",
        ),
    }
    for priority, dimension in enumerate(dimensions.values(), start=1):
        AssessmentDimensionRequirement.objects.create(
            assessment_version=version,
            dimension=dimension,
            required=True,
            priority=priority,
            minimum_independent_sources=2,
            minimum_source_types=2,
        )
    items: dict[str, AssessmentItem] = {}
    item_specs = (
        (
            "logic_self_report",
            "logical_reasoning",
            AssessmentItem.ItemType.LIKERT,
            AssessmentItem.Purpose.CORE,
        ),
        (
            "logic_second_signal",
            "logical_reasoning",
            AssessmentItem.ItemType.BINARY,
            AssessmentItem.Purpose.CORE,
        ),
        (
            "speaking_self_report",
            "public_speaking_comfort",
            AssessmentItem.ItemType.LIKERT,
            AssessmentItem.Purpose.CORE,
        ),
        (
            "speaking_clarification",
            "public_speaking_comfort",
            AssessmentItem.ItemType.SCENARIO_CHOICE,
            AssessmentItem.Purpose.CLARIFICATION,
        ),
        (
            "open_idea_story",
            "idea_generation",
            AssessmentItem.ItemType.LONG_TEXT,
            AssessmentItem.Purpose.OPEN_DISCOVERY,
        ),
    )
    for order, (code, dimension_code, item_type, purpose) in enumerate(item_specs, start=1):
        response_schema: dict[str, object]
        if item_type == AssessmentItem.ItemType.LIKERT:
            response_schema = {"options": ["disagree", "agree"]}
            rules = {
                "map": {
                    "disagree": {
                        "signal": "negative",
                        "polarity": -1,
                        "direction": "conflicts",
                        "confidence_band": "low",
                        "confidence_score": "0.35",
                    },
                    "agree": {
                        "signal": "positive",
                        "polarity": 1,
                        "direction": "supports",
                        "confidence_band": "low",
                        "confidence_score": "0.35",
                    },
                }
            }
        elif item_type == AssessmentItem.ItemType.BINARY:
            response_schema = {"options": [True, False]}
            rules = {
                "map": {
                    "True": {
                        "signal": "positive",
                        "polarity": 1,
                        "direction": "supports",
                        "confidence_band": "low",
                        "confidence_score": "0.35",
                    },
                    "False": {
                        "signal": "negative",
                        "polarity": -1,
                        "direction": "conflicts",
                        "confidence_band": "low",
                        "confidence_score": "0.35",
                    },
                }
            }
        elif item_type == AssessmentItem.ItemType.SCENARIO_CHOICE:
            response_schema = {"options": ["speak", "avoid"]}
            rules = {
                "map": {
                    "speak": {
                        "signal": "positive",
                        "polarity": 1,
                        "direction": "supports",
                        "confidence_band": "low",
                        "confidence_score": "0.35",
                    },
                    "avoid": {
                        "signal": "negative",
                        "polarity": -1,
                        "direction": "conflicts",
                        "confidence_band": "low",
                        "confidence_score": "0.35",
                    },
                }
            }
        else:
            response_schema, rules = {}, {}
        item = AssessmentItem.objects.create(
            assessment_version=version,
            section=section,
            dimension=dimensions[dimension_code],
            code=code,
            item_type=item_type,
            purpose=purpose,
            order=order,
            response_schema=response_schema,
            interpretation_rules=rules,
            evidence_source_type="self_report",
        )
        add_variant(item)
        add_variant(
            item,
            language="en",
            audience=AssessmentItemVariant.Audience.GENERAL,
            education_stage=EducationStage.UNKNOWN,
            prompt="Synthetic English fallback question.",
        )
        items[code] = item
    if publish:
        publish_assessment_version(
            assessment_version=version,
            lifecycle=AssessmentLifecycle.PILOT,
            actor_reference="synthetic-test-publisher",
        )
    return PilotAssessment(version=version, dimensions=dimensions, items=items)


def start_test_session(
    journey: ParticipantJourney,
    pilot: PilotAssessment,
    *,
    maximum_items: int | None = None,
) -> AssessmentSession:
    return start_assessment_session(
        journey=journey,
        assessment_version=pilot.version,
        audience=AssessmentItemVariant.Audience.UNIVERSITY,
        maximum_items=maximum_items,
        actor_type="synthetic_test",
    )
