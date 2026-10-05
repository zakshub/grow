from __future__ import annotations

import pytest

from grow.assessments.models import (
    AssessmentDimension,
    AssessmentItem,
    AssessmentItemVariant,
    AssessmentLifecycle,
    AssessmentSession,
    Contradiction,
    DimensionCategory,
)
from grow.reviews.models import HumanReview
from grow.synthetic.assessment_pack import (
    ASSESSMENT_SCENARIOS,
    DIMENSION_CATALOG,
    create_synthetic_assessment_pack,
)


@pytest.mark.django_db
def test_full_requested_pilot_dimension_taxonomy_is_created() -> None:
    create_synthetic_assessment_pack()
    expected_count = sum(len(names) for names in DIMENSION_CATALOG.values())
    assert expected_count == 81
    assert AssessmentDimension.objects.count() == expected_count
    assert set(AssessmentDimension.objects.values_list("category", flat=True)) == {
        value for value, _label in DimensionCategory.choices
    }
    assert AssessmentDimension.objects.filter(pilot_only=True).count() == expected_count


@pytest.mark.django_db
def test_pack_is_explicitly_pilot_and_not_validated() -> None:
    sessions = create_synthetic_assessment_pack()
    version = next(iter(sessions.values())).assessment_version
    assert version is not None
    assert version.lifecycle == AssessmentLifecycle.PILOT
    assert "not psychometrically" in version.limitations
    assert all(item.pilot_only for item in version.items.all())
    assert set(version.items.values_list("variants__content_status", flat=True)) == {
        AssessmentItemVariant.ContentStatus.SYNTHETIC_PILOT
    }


@pytest.mark.django_db
def test_urdu_primary_and_english_fallback_variants_exist() -> None:
    sessions = create_synthetic_assessment_pack()
    version = next(iter(sessions.values())).assessment_version
    assert version is not None
    for item in version.items.all():
        assert item.variants.filter(language="ur").exists()
        assert item.variants.filter(language="en", audience="general").exists()
    audiences = set(
        AssessmentItemVariant.objects.filter(language="ur").values_list("audience", flat=True)
    )
    assert audiences == {
        "grade_8_10",
        "intermediate",
        "university",
        "graduate",
        "adult_career_switcher",
    }


@pytest.mark.django_db
def test_grade_and_adult_urdu_variants_match_education_context() -> None:
    create_synthetic_assessment_pack()
    item = AssessmentItem.objects.get(code="logic_pattern")
    assert item.variants.filter(
        language="ur", audience="grade_8_10", education_stage="grade_10"
    ).exists()
    assert item.variants.filter(
        language="ur", audience="adult_career_switcher", education_stage="graduate"
    ).exists()
    assert (
        item.variants.get(
            language="ur", audience="grade_8_10", education_stage="grade_8"
        ).helper_text
        != item.variants.get(
            language="ur", audience="adult_career_switcher", education_stage="graduate"
        ).helper_text
    )


@pytest.mark.django_db
def test_open_discovery_prompts_are_raw_text_only() -> None:
    create_synthetic_assessment_pack()
    open_items = AssessmentItem.objects.filter(purpose=AssessmentItem.Purpose.OPEN_DISCOVERY)
    assert open_items.count() == 5
    assert set(open_items.values_list("item_type", flat=True)) == {
        AssessmentItem.ItemType.LONG_TEXT
    }
    assert all(not item.interpretation_rules for item in open_items)


@pytest.mark.django_db
def test_all_ten_progressive_synthetic_scenarios_exist() -> None:
    sessions = create_synthetic_assessment_pack()
    assert set(sessions) == set(ASSESSMENT_SCENARIOS)
    assert len(sessions) == 10
    assert sessions["mostly-unknown-dimensions"].presentations.count() == 0
    assert sessions["stopped-assessment-early"].status == (
        AssessmentSession.SessionStatus.STOPPED_EARLY
    )
    assert Contradiction.objects.filter(
        journey=sessions["highly-contradictory-self-report"].journey
    ).exists()


@pytest.mark.django_db
def test_assessment_pack_is_idempotent() -> None:
    first = create_synthetic_assessment_pack()
    second = create_synthetic_assessment_pack()
    assert {code: session.id for code, session in first.items()} == {
        code: session.id for code, session in second.items()
    }
    assert AssessmentSession.objects.filter(assessment_version__isnull=False).count() == 10


@pytest.mark.django_db
def test_human_review_scenario_creates_assessment_review() -> None:
    sessions = create_synthetic_assessment_pack()
    session = sessions["assessment-human-review-required"]
    assert session.sufficiency_status == AssessmentSession.SufficiencyStatus.REVIEW_REQUIRED
    assert HumanReview.objects.filter(
        journey=session.journey,
        review_type=HumanReview.ReviewType.ASSESSMENT_EVIDENCE,
        status=HumanReview.ReviewStatus.REQUIRED,
    ).exists()
