from __future__ import annotations

import pytest
from django.contrib import admin
from django.core.exceptions import ValidationError
from django.test import RequestFactory

from grow.assessments.models import (
    AssessmentDefinition,
    AssessmentItem,
    AssessmentItemPresentation,
    AssessmentItemVariant,
    AssessmentLifecycle,
    AssessmentVersion,
)
from grow.assessments.services import publish_assessment_version
from tests.assessment_helpers import add_variant, create_pilot_assessment, start_test_session


@pytest.mark.django_db
def test_definition_and_version_are_separate() -> None:
    pilot = create_pilot_assessment()
    second = AssessmentVersion.objects.create(
        definition=pilot.version.definition,
        version=2,
        maximum_items=10,
    )
    assert pilot.version.version == 1
    assert second.version == 2
    assert pilot.version.definition_id == second.definition_id


@pytest.mark.django_db
def test_published_definition_is_immutable() -> None:
    pilot = create_pilot_assessment()
    definition = pilot.version.definition
    definition.title = "Silently changed"
    with pytest.raises(ValueError, match="immutable"):
        definition.save()


@pytest.mark.django_db
def test_published_version_content_is_immutable() -> None:
    pilot = create_pilot_assessment()
    pilot.version.maximum_items = 99
    with pytest.raises(ValueError, match="immutable"):
        pilot.version.save()


@pytest.mark.django_db
def test_published_items_and_variants_are_immutable() -> None:
    pilot = create_pilot_assessment()
    item = pilot.items["logic_self_report"]
    item.order = 90
    with pytest.raises(ValueError, match="immutable"):
        item.save()
    with pytest.raises(ValueError, match="immutable"):
        add_variant(item, language="ur", prompt="نیا خاموش سوال")


@pytest.mark.django_db
def test_lifecycle_transitions_are_explicit_and_audited() -> None:
    pilot = create_pilot_assessment()
    publish_assessment_version(
        assessment_version=pilot.version,
        lifecycle=AssessmentLifecycle.RETIRED,
        actor_reference="synthetic-reviewer",
    )
    assert pilot.version.lifecycle == AssessmentLifecycle.RETIRED
    assert pilot.version.retired_at is not None


@pytest.mark.django_db
def test_invalid_lifecycle_transition_fails() -> None:
    pilot = create_pilot_assessment(publish=False)
    with pytest.raises(ValidationError, match="not allowed"):
        publish_assessment_version(
            assessment_version=pilot.version,
            lifecycle=AssessmentLifecycle.RETIRED,
            actor_reference="synthetic-reviewer",
        )


@pytest.mark.django_db
def test_version_requires_items_before_publication() -> None:
    definition = AssessmentDefinition.objects.create(
        code="empty", title="Empty", purpose="Synthetic test"
    )
    version = AssessmentVersion.objects.create(definition=definition, version=1)
    with pytest.raises(ValidationError, match="require items"):
        publish_assessment_version(
            assessment_version=version,
            lifecycle=AssessmentLifecycle.PILOT,
            actor_reference="synthetic-reviewer",
        )


@pytest.mark.django_db
def test_item_variants_preserve_language_audience_and_version() -> None:
    pilot = create_pilot_assessment()
    variants = pilot.items["logic_self_report"].variants.all()
    assert variants.filter(language="ur", audience="university").exists()
    assert variants.filter(language="en", audience="general").exists()
    assert set(variants.values_list("variant_version", flat=True)) == {1}


@pytest.mark.django_db
def test_presentation_rejects_variant_from_another_item(adult_journey: object) -> None:
    from grow.journeys.models import ParticipantJourney

    journey = adult_journey
    assert isinstance(journey, ParticipantJourney)
    pilot = create_pilot_assessment()
    session = start_test_session(journey, pilot)
    item = pilot.items["logic_self_report"]
    wrong_variant = pilot.items["logic_second_signal"].variants.get(language="ur")
    presentation = AssessmentItemPresentation(
        session=session,
        item=item,
        variant=wrong_variant,
        sequence=1,
        selection_status="ASK_MORE",
        selection_reason="Synthetic invalid invariant test",
        selection_policy_version=pilot.version.selection_policy_version,
    )
    with pytest.raises(ValidationError, match="variant"):
        presentation.save()


@pytest.mark.django_db
def test_historical_session_remains_pinned_to_original_version(
    adult_journey: object,
) -> None:
    from grow.assessments.services import start_assessment_session
    from grow.journeys.models import ParticipantJourney

    journey = adult_journey
    assert isinstance(journey, ParticipantJourney)
    pilot = create_pilot_assessment()
    session = start_assessment_session(
        journey=journey,
        assessment_version=pilot.version,
        audience=AssessmentItemVariant.Audience.UNIVERSITY,
    )
    AssessmentVersion.objects.create(
        definition=pilot.version.definition,
        version=2,
        maximum_items=10,
    )
    session.refresh_from_db()
    assert session.assessment_version == pilot.version
    assert session.definition_version == "1"


def test_all_required_item_types_are_declared() -> None:
    values = {value for value, _label in AssessmentItem.ItemType.choices}
    assert values == {
        "likert",
        "binary",
        "single_choice",
        "multi_choice",
        "ranking",
        "numeric",
        "short_text",
        "long_text",
        "scenario_choice",
    }


def test_assessment_admin_is_inspection_only() -> None:
    model_admin = admin.site._registry[AssessmentDefinition]
    request = RequestFactory().get("/admin/")
    assert model_admin.has_add_permission(request) is False
    assert model_admin.has_change_permission(request) is False
    assert model_admin.has_delete_permission(request) is False
