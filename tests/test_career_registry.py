from __future__ import annotations

from datetime import date, timedelta

import pytest
from django.contrib import admin
from django.core.exceptions import ValidationError

from grow.assessments.models import DimensionCategory
from grow.audit.models import AuditEvent
from grow.careers.models import (
    CareerCluster,
    CareerDimensionRelationship,
    CareerEnvironmentObservation,
    CareerFamily,
    CareerImportBatch,
    CareerImportDiff,
    CareerPathway,
    CareerProfile,
    CareerProfileVersion,
    CareerRelationship,
    CareerReviewDecision,
    CareerSkillRequirement,
    CareerTaxonomy,
    CareerTaxonomyVersion,
    Confidence,
    DataClassification,
    Freshness,
    Lifecycle,
    MarketObservation,
    OrdinalRelevance,
    ResearchSource,
    ReviewStatus,
)
from grow.careers.services import (
    approve_import,
    build_career_snapshot,
    effective_freshness,
    prepare_import_diff,
    publish_import,
    stage_import,
    transition_review,
    validate_import_payload,
)
from grow.synthetic.career_pack import CAREERS, MARKERS, create_synthetic_career_pack


@pytest.fixture
def career_pack(db: object) -> dict[str, CareerProfileVersion]:
    return create_synthetic_career_pack()


def test_synthetic_pack_contains_requested_varied_careers(
    career_pack: dict[str, CareerProfileVersion],
) -> None:
    assert set(career_pack) == {seed.code for seed in CAREERS}
    assert len(career_pack) == 12
    assert {item.family.cluster.name_en for item in career_pack.values()} >= {
        "Technology",
        "Creative and Digital",
        "Education and Social",
        "Business",
        "Healthcare",
        "Skilled Trades",
    }


def test_synthetic_pack_is_idempotent(career_pack: dict[str, CareerProfileVersion]) -> None:
    again = create_synthetic_career_pack()
    assert {key: value.id for key, value in career_pack.items()} == {
        key: value.id for key, value in again.items()
    }
    assert CareerTaxonomyVersion.objects.count() == 1


def test_taxonomy_is_versioned_published_and_marked(
    career_pack: dict[str, CareerProfileVersion],
) -> None:
    version = next(iter(career_pack.values())).taxonomy_version
    assert version.version == 1
    assert version.lifecycle == Lifecycle.PILOT
    assert version.review_status == ReviewStatus.PUBLISHED
    assert version.data_markers == MARKERS
    assert version.published_at is not None


def test_published_taxonomy_content_is_immutable(
    career_pack: dict[str, CareerProfileVersion],
) -> None:
    profile = career_pack["software-developer"]
    profile.summary = "silently rewritten"
    with pytest.raises(ValueError, match="immutable"):
        profile.save()
    cluster = profile.family.cluster
    cluster.name_en = "Rewritten"
    with pytest.raises(ValueError, match="immutable"):
        cluster.save()


def test_stable_profile_code_is_immutable(career_pack: dict[str, CareerProfileVersion]) -> None:
    stable = career_pack["data-analyst"].profile
    stable.code = "changed-code"
    with pytest.raises(ValueError, match="cannot change"):
        stable.save()


def test_aliases_and_related_careers_are_version_pinned(
    career_pack: dict[str, CareerProfileVersion],
) -> None:
    profile = career_pack["teacher"]
    assert profile.aliases.get().name == "Subject Teacher"
    relation = CareerRelationship.objects.filter(
        source__taxonomy_version=profile.taxonomy_version
    ).first()
    assert relation is not None
    assert relation.source.taxonomy_version_id == relation.target.taxonomy_version_id
    assert relation.relationship_type == CareerRelationship.RelationshipType.RELATED


def test_career_dimensions_cover_traits_interests_and_values(
    career_pack: dict[str, CareerProfileVersion],
) -> None:
    profile = career_pack["ux-product-designer"]
    links = profile.dimension_relationships.select_related("dimension")
    assert {link.dimension.category for link in links} >= {
        DimensionCategory.CREATIVITY,
        DimensionCategory.COMMUNICATION_SOCIAL,
        DimensionCategory.VOCATIONAL_INTEREST,
        DimensionCategory.WORK_VALUE,
    }
    assert all(link.direction == CareerDimensionRelationship.Direction.CONTEXTUAL for link in links)
    assert all(link.confidence == Confidence.LOW for link in links)
    assert all(link.limitations for link in links)


def test_interest_profile_allows_multiple_variable_interests(
    career_pack: dict[str, CareerProfileVersion],
) -> None:
    links = career_pack["digital-marketer"].dimension_relationships.select_related("dimension")
    interests = [
        link for link in links if link.dimension.category == DimensionCategory.VOCATIONAL_INTEREST
    ]
    assert len(interests) == 2
    assert {link.importance for link in interests} == {OrdinalRelevance.VARIABLE}


def test_work_values_have_context_fields(career_pack: dict[str, CareerProfileVersion]) -> None:
    links = career_pack["accountant"].dimension_relationships.select_related("dimension")
    values = [link for link in links if link.dimension.category == DimensionCategory.WORK_VALUE]
    assert {link.dimension.code for link in values} == {"stability", "predictability"}
    assert all(link.country == "Pakistan" for link in values)


def test_work_environment_uses_required_prevalence_vocabulary(
    career_pack: dict[str, CareerProfileVersion],
) -> None:
    environments = career_pack["mechanical-technician"].environment_observations.all()
    assert environments.count() == 2
    assert {item.prevalence for item in environments} == {
        CareerEnvironmentObservation.Prevalence.VARIABLE
    }
    assert all(item.context for item in environments)


def test_skills_and_pathways_are_sourced_and_versioned(
    career_pack: dict[str, CareerProfileVersion],
) -> None:
    profile = career_pack["research-assistant"]
    assert profile.skill_requirements.count() == 2
    requirement = profile.skill_requirements.select_related("skill", "source").first()
    assert requirement is not None
    assert requirement.requirement == CareerSkillRequirement.RequirementLevel.COMMON
    assert requirement.source.review_status == ReviewStatus.PUBLISHED
    assert profile.pathways.count() == 2
    pathway = profile.pathways.first()
    assert pathway is not None
    assert pathway.pathway_version == 1
    assert pathway.country == "Pakistan"
    assert pathway.duration == "Unknown"
    assert pathway.skills.count() == 2


def test_pathway_route_types_cover_required_architecture() -> None:
    assert set(CareerPathway.RouteType.values) == {
        "degree",
        "diploma",
        "certification",
        "skills_first",
        "apprenticeship",
        "self_taught",
        "portfolio",
        "internship",
        "entry_role",
        "career_switch",
    }


def test_research_source_preserves_method_limitations_and_licence(
    career_pack: dict[str, CareerProfileVersion],
) -> None:
    source = ResearchSource.objects.get()
    assert source.methodology_notes
    assert source.limitations
    assert source.licence_notes
    assert source.quality_status == Confidence.LOW
    assert source.review_status == ReviewStatus.PUBLISHED
    source.title = "rewrite"
    with pytest.raises(ValueError, match="immutable"):
        source.save()


def test_market_unknown_is_first_class_and_has_no_fake_value(
    career_pack: dict[str, CareerProfileVersion],
) -> None:
    observations = career_pack["nurse"].market_observations.all()
    assert observations.count() == 3
    assert all(item.value_state == MarketObservation.ValueState.UNKNOWN for item in observations)
    assert all(item.value is None and item.unit == "" for item in observations)
    assert observations.filter(
        observation_type=MarketObservation.ObservationType.SALARY_RANGE
    ).exists()


def test_unknown_market_observation_rejects_value(
    career_pack: dict[str, CareerProfileVersion],
) -> None:
    original = career_pack["lawyer"].market_observations.first()
    assert original is not None
    original.pk = None
    original._state.adding = True
    original.value = {"claim": "unsupported"}
    with pytest.raises(ValidationError, match="UNKNOWN"):
        original.full_clean()


def test_salary_range_requires_range_currency_and_period(
    career_pack: dict[str, CareerProfileVersion],
) -> None:
    original = career_pack["software-developer"].market_observations.first()
    assert original is not None
    original.pk = None
    original._state.adding = True
    original.observation_type = MarketObservation.ObservationType.SALARY_RANGE
    original.value_state = MarketObservation.ValueState.KNOWN
    original.value = {"amount": 100}
    with pytest.raises(ValidationError, match="minimum"):
        original.full_clean()


def test_expiry_deterministically_transitions_effective_freshness() -> None:
    today = date(2026, 10, 5)
    assert (
        effective_freshness(stored=Freshness.CURRENT, expires_at=today, on_date=today)
        == Freshness.CURRENT
    )
    assert (
        effective_freshness(
            stored=Freshness.CURRENT, expires_at=today - timedelta(days=1), on_date=today
        )
        == Freshness.STALE
    )
    assert (
        effective_freshness(stored=Freshness.RETIRED, expires_at=None, on_date=today)
        == Freshness.RETIRED
    )
    assert (
        effective_freshness(stored=Freshness.UNKNOWN, expires_at=None, on_date=today)
        == Freshness.UNKNOWN
    )


def test_source_supersession_preserves_history(
    career_pack: dict[str, CareerProfileVersion],
) -> None:
    source = ResearchSource.objects.get()
    successor = ResearchSource.objects.create(
        source_type=ResearchSource.SourceType.OTHER,
        title="Synthetic successor",
        publisher="Grow tests",
        reference="synthetic-successor",
        accessed_date=date(2026, 10, 5),
        limitations="Synthetic test only.",
        quality_status=Confidence.LOW,
        supersedes=source,
    )
    assert successor.supersedes_id == source.id
    assert ResearchSource.objects.filter(pk=source.pk).exists()


def test_review_workflow_is_human_controlled_and_audited(db: object) -> None:
    taxonomy = CareerTaxonomy.objects.create(code="review-test", title="Review test", scope="Test")
    version = CareerTaxonomyVersion.objects.create(
        taxonomy=taxonomy, version=1, provenance="synthetic", limitations="test"
    )
    with pytest.raises(ValidationError, match="Invalid"):
        transition_review(
            target=version,
            to_status=ReviewStatus.PUBLISHED,
            reviewer_reference="reviewer",
            reason="Skipping review is not allowed",
        )
    transition_review(
        target=version,
        to_status=ReviewStatus.IN_REVIEW,
        reviewer_reference="reviewer",
        reason="Begin review",
    )
    version.refresh_from_db()
    assert version.review_status == ReviewStatus.IN_REVIEW
    assert CareerReviewDecision.objects.filter(target_id=version.id).count() == 1
    assert AuditEvent.objects.filter(target_id=version.id).exists()


def test_review_requires_identified_reviewer(db: object) -> None:
    taxonomy = CareerTaxonomy.objects.create(code="reviewer-test", title="Test", scope="Test")
    version = CareerTaxonomyVersion.objects.create(
        taxonomy=taxonomy, version=1, provenance="synthetic", limitations="test"
    )
    with pytest.raises(ValidationError, match="Reviewer"):
        transition_review(
            target=version,
            to_status=ReviewStatus.IN_REVIEW,
            reviewer_reference="",
            reason="test",
        )


def test_published_source_can_be_marked_stale_without_rewriting_content(
    career_pack: dict[str, CareerProfileVersion],
) -> None:
    source = ResearchSource.objects.get()
    transition_review(
        target=source,
        to_status=ReviewStatus.STALE,
        reviewer_reference="reviewer",
        reason="Source expiry requires refresh.",
    )
    source.refresh_from_db()
    assert source.review_status == ReviewStatus.STALE
    source.title = "Rewritten source"
    with pytest.raises(ValueError, match="immutable"):
        source.save()


def test_career_snapshot_is_career_only_and_exposes_unknowns(
    career_pack: dict[str, CareerProfileVersion],
) -> None:
    snapshot = build_career_snapshot(profile_version=career_pack["ux-product-designer"])
    result = snapshot.to_dict()
    assert result["career_code"] == "ux-product-designer"
    assert result["participant_recommendation_ready"] is False
    assert result["interests"]
    assert result["work_values"]
    assert result["pathways"] == ("Portfolio route", "Skills-first route")
    assert result["freshness_counts"][Freshness.UNKNOWN] == 3
    assert all(item["value_state"] == "unknown" for item in result["market_evidence"])
    assert not any(
        "participant" in key and key != "participant_recommendation_ready" for key in result
    )


def test_all_synthetic_profiles_are_blocked_from_participant_recommendation(
    career_pack: dict[str, CareerProfileVersion],
) -> None:
    assert all(
        item.data_classification == DataClassification.SYNTHETIC for item in career_pack.values()
    )
    assert not any(item.participant_recommendation_ready for item in career_pack.values())


def test_admin_registers_registry_and_import_inspection_models() -> None:
    for model in (
        CareerTaxonomy,
        CareerTaxonomyVersion,
        CareerCluster,
        CareerFamily,
        CareerProfileVersion,
        CareerDimensionRelationship,
        CareerSkillRequirement,
        CareerPathway,
        ResearchSource,
        MarketObservation,
        CareerImportBatch,
        CareerImportDiff,
    ):
        assert model in admin.site._registry


def test_import_validation_rejects_unknown_schema_and_duplicates() -> None:
    payload = {
        "schema_version": "wrong",
        "careers": [
            {"code": "same"},
            {"code": "same"},
        ],
    }
    errors = validate_import_payload(payload)
    assert any("schema_version" in item for item in errors)
    assert any("duplicate" in item for item in errors)
    assert any("missing" in item for item in errors)


def _import_payload(*, title: str = "Imported Career") -> dict[str, object]:
    return {
        "schema_version": "career-import-v1",
        "careers": [
            {
                "code": "imported-career",
                "title": title,
                "cluster": "Synthetic Cluster",
                "family": "Synthetic Family",
                "summary": "Synthetic imported summary.",
                "typical_work": "Synthetic imported work description.",
                "aliases": ["Imported Entry"],
            }
        ],
    }


def test_import_diff_requires_approval_before_publish(db: object) -> None:
    taxonomy = CareerTaxonomy.objects.create(code="imports", title="Imports", scope="Synthetic")
    batch = stage_import(taxonomy=taxonomy, payload=_import_payload(), base_version=None)
    batch = prepare_import_diff(batch=batch)
    assert batch.status == CareerImportBatch.Status.DIFF_READY
    assert list(batch.diffs.values_list("change_type", flat=True)) == [
        CareerImportDiff.ChangeType.NEW
    ]
    with pytest.raises(ValidationError, match="approval"):
        publish_import(batch=batch, reviewer_reference="reviewer")


def test_approved_import_publishes_new_immutable_version(db: object) -> None:
    taxonomy = CareerTaxonomy.objects.create(
        code="approved-import", title="Imports", scope="Synthetic"
    )
    batch = prepare_import_diff(
        batch=stage_import(taxonomy=taxonomy, payload=_import_payload(), base_version=None)
    )
    batch = approve_import(batch=batch, reviewer_reference="reviewer-1", reason="Diff reviewed")
    version = publish_import(batch=batch, reviewer_reference="reviewer-1")
    assert version.version == 1
    assert version.review_status == ReviewStatus.PUBLISHED
    assert version.lifecycle == Lifecycle.PILOT
    assert version.career_versions.get().review_status == ReviewStatus.PUBLISHED
    batch.refresh_from_db()
    assert batch.status == CareerImportBatch.Status.PUBLISHED
    assert batch.published_version_id == version.id


def test_import_diff_shows_changed_and_removed_without_overwrite(
    career_pack: dict[str, CareerProfileVersion],
) -> None:
    base = next(iter(career_pack.values())).taxonomy_version
    taxonomy = base.taxonomy
    payload = _import_payload(title="Changed title")
    batch = prepare_import_diff(
        batch=stage_import(taxonomy=taxonomy, payload=payload, base_version=base)
    )
    changes = set(batch.diffs.values_list("change_type", flat=True))
    assert CareerImportDiff.ChangeType.NEW in changes
    assert CareerImportDiff.ChangeType.REMOVED in changes
    assert base.review_status == ReviewStatus.PUBLISHED
    assert base.career_versions.count() == 12


def test_import_payload_hash_makes_staging_idempotent(db: object) -> None:
    taxonomy = CareerTaxonomy.objects.create(code="hash-test", title="Hash", scope="Synthetic")
    first = stage_import(taxonomy=taxonomy, payload=_import_payload(), base_version=None)
    second = stage_import(taxonomy=taxonomy, payload=_import_payload(), base_version=None)
    assert first.id == second.id


def test_market_model_supports_context_and_supersession_on_draft(db: object) -> None:
    taxonomy = CareerTaxonomy.objects.create(code="market-test", title="Market", scope="Synthetic")
    version = CareerTaxonomyVersion.objects.create(
        taxonomy=taxonomy, version=1, provenance="synthetic", limitations="test"
    )
    cluster = CareerCluster.objects.create(taxonomy_version=version, code="c", name_en="C")
    family = CareerFamily.objects.create(
        taxonomy_version=version, cluster=cluster, code="f", name_en="F"
    )
    stable = CareerProfile.objects.create(code="market-career")
    profile = CareerProfileVersion.objects.create(
        profile=stable,
        taxonomy_version=version,
        family=family,
        version=1,
        title_en="Market Career",
        summary="Synthetic",
        typical_work="Synthetic",
        limitations="Synthetic",
    )
    source = ResearchSource.objects.create(
        source_type=ResearchSource.SourceType.OTHER,
        title="Synthetic source",
        publisher="Tests",
        accessed_date=date(2026, 10, 5),
        limitations="Synthetic",
    )
    first = MarketObservation.objects.create(
        profile_version=profile,
        observation_type=MarketObservation.ObservationType.DEMAND,
        region="Sindh",
        city="Karachi",
        employment_type="full-time",
        industry="synthetic",
        seniority="entry",
        value_state=MarketObservation.ValueState.UNKNOWN,
        source=source,
        source_date=date(2026, 10, 5),
        limitations="Unknown by design",
    )
    second = MarketObservation.objects.create(
        profile_version=profile,
        observation_type=MarketObservation.ObservationType.DEMAND,
        region="Sindh",
        city="Karachi",
        value_state=MarketObservation.ValueState.UNKNOWN,
        source=source,
        source_date=date(2026, 11, 5),
        limitations="Superseding unknown observation",
        observation_version=2,
        supersedes=first,
    )
    assert second.supersedes_id == first.id
    assert MarketObservation.objects.filter(pk=first.pk).exists()
