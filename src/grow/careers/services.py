from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import date
from typing import Any

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from grow.audit.services import record_audit_event
from grow.careers.models import (
    CareerAlias,
    CareerCluster,
    CareerFamily,
    CareerImportBatch,
    CareerImportDiff,
    CareerProfile,
    CareerProfileVersion,
    CareerReviewDecision,
    CareerTaxonomy,
    CareerTaxonomyVersion,
    Freshness,
    Lifecycle,
    ResearchSource,
    ReviewStatus,
)


def effective_freshness(
    *, stored: str, expires_at: date | None, on_date: date | None = None
) -> str:
    """Return freshness without rewriting historical evidence."""
    today = on_date or timezone.localdate()
    if stored == Freshness.RETIRED:
        return Freshness.RETIRED
    if expires_at is not None and expires_at < today:
        return Freshness.STALE
    return stored


def _decision(
    *,
    target: CareerTaxonomyVersion | CareerProfileVersion | ResearchSource,
    from_status: str,
    to_status: str,
    reviewer_reference: str,
    reason: str,
    source_evidence: list[str] | None = None,
    changes: dict[str, Any] | None = None,
) -> CareerReviewDecision:
    if not reviewer_reference.strip() or not reason.strip():
        raise ValidationError("Reviewer and reason are required")
    decision = CareerReviewDecision.objects.create(
        target_type=target._meta.label_lower,
        target_id=target.id,
        from_status=from_status,
        to_status=to_status,
        reviewer_reference=reviewer_reference,
        reason=reason,
        source_evidence=source_evidence or [],
        changes=changes or {},
        decision=to_status,
    )
    record_audit_event(
        event_type="career.review_decided",
        actor_type="reviewer",
        actor_reference=reviewer_reference,
        target_type=target._meta.label_lower,
        target_id=target.id,
        reason=reason,
        details={"from_status": from_status, "to_status": to_status},
    )
    return decision


@transaction.atomic
def transition_review(
    *,
    target: CareerTaxonomyVersion | CareerProfileVersion | ResearchSource,
    to_status: str,
    reviewer_reference: str,
    reason: str,
    source_evidence: list[str] | None = None,
    changes: dict[str, Any] | None = None,
) -> CareerReviewDecision:
    target = target.__class__.objects.select_for_update().get(pk=target.pk)
    allowed: dict[str, set[str]] = {
        ReviewStatus.DRAFT: {ReviewStatus.IN_REVIEW},
        ReviewStatus.IN_REVIEW: {ReviewStatus.DRAFT, ReviewStatus.APPROVED},
        ReviewStatus.APPROVED: {ReviewStatus.PUBLISHED, ReviewStatus.DRAFT},
        ReviewStatus.PUBLISHED: {ReviewStatus.STALE, ReviewStatus.RETIRED},
        ReviewStatus.STALE: {ReviewStatus.RETIRED},
        ReviewStatus.RETIRED: set(),
    }
    old = target.review_status
    if to_status not in allowed[old]:
        raise ValidationError(f"Invalid review transition: {old} -> {to_status}")
    if isinstance(target, CareerTaxonomyVersion) and to_status == ReviewStatus.PUBLISHED:
        unapproved = target.career_versions.exclude(review_status=ReviewStatus.APPROVED)
        if unapproved.exists():
            raise ValidationError(
                "Every career profile must be approved before taxonomy publication"
            )
    target.review_status = to_status
    if to_status == ReviewStatus.PUBLISHED and hasattr(target, "published_at"):
        target.published_at = timezone.now()
    if to_status == ReviewStatus.RETIRED and isinstance(target, CareerTaxonomyVersion):
        target.retired_at = timezone.now()
        target.lifecycle = Lifecycle.RETIRED
    target.save()
    return _decision(
        target=target,
        from_status=old,
        to_status=to_status,
        reviewer_reference=reviewer_reference,
        reason=reason,
        source_evidence=source_evidence,
        changes=changes,
    )


@transaction.atomic
def publish_taxonomy_version(
    *, version: CareerTaxonomyVersion, lifecycle: str, reviewer_reference: str, reason: str
) -> CareerTaxonomyVersion:
    if lifecycle not in {Lifecycle.PILOT, Lifecycle.ACTIVE}:
        raise ValidationError("Published taxonomy lifecycle must be PILOT or ACTIVE")
    version = CareerTaxonomyVersion.objects.select_for_update().get(pk=version.pk)
    if version.review_status != ReviewStatus.APPROVED:
        raise ValidationError("Only an approved taxonomy version can be published")
    profiles = list(version.career_versions.all())
    if not profiles or any(p.review_status != ReviewStatus.APPROVED for p in profiles):
        raise ValidationError("All taxonomy profiles must be approved before publication")
    for profile in profiles:
        old = profile.review_status
        profile.review_status = ReviewStatus.PUBLISHED
        profile.lifecycle = lifecycle
        profile.published_at = timezone.now()
        profile.save()
        _decision(
            target=profile,
            from_status=old,
            to_status=ReviewStatus.PUBLISHED,
            reviewer_reference=reviewer_reference,
            reason=reason,
        )
    old = version.review_status
    version.review_status = ReviewStatus.PUBLISHED
    version.lifecycle = lifecycle
    version.published_at = timezone.now()
    version.save()
    _decision(
        target=version,
        from_status=old,
        to_status=ReviewStatus.PUBLISHED,
        reviewer_reference=reviewer_reference,
        reason=reason,
    )
    return version


def _canonical_payload(payload: dict[str, Any]) -> tuple[str, str]:
    canonical = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return canonical, hashlib.sha256(canonical.encode()).hexdigest()


def validate_import_payload(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if payload.get("schema_version") != "career-import-v1":
        errors.append("schema_version must be career-import-v1")
    careers = payload.get("careers")
    if not isinstance(careers, list) or not careers:
        errors.append("careers must be a non-empty list")
        return errors
    seen: set[str] = set()
    required = {"code", "title", "cluster", "family", "summary", "typical_work"}
    for index, career in enumerate(careers):
        if not isinstance(career, dict):
            errors.append(f"careers[{index}] must be an object")
            continue
        missing = sorted(required - set(career))
        if missing:
            errors.append(f"careers[{index}] missing: {', '.join(missing)}")
        code = career.get("code")
        if not isinstance(code, str) or not code:
            errors.append(f"careers[{index}].code must be non-empty text")
        elif code in seen:
            errors.append(f"duplicate career code: {code}")
        else:
            seen.add(code)
        unexpected = set(career) - (required | {"title_ur", "pakistan_title", "aliases"})
        if unexpected:
            errors.append(f"careers[{index}] unexpected fields: {', '.join(sorted(unexpected))}")
    return errors


def _version_records(version: CareerTaxonomyVersion | None) -> dict[str, dict[str, Any]]:
    if version is None:
        return {}
    return {
        item.profile.code: {
            "code": item.profile.code,
            "title": item.title_en,
            "title_ur": item.title_ur,
            "pakistan_title": item.pakistan_title,
            "cluster": item.family.cluster.name_en,
            "family": item.family.name_en,
            "summary": item.summary,
            "typical_work": item.typical_work,
            "aliases": sorted(item.aliases.values_list("name", flat=True)),
        }
        for item in version.career_versions.select_related("profile", "family__cluster").all()
    }


@transaction.atomic
def stage_import(
    *, taxonomy: CareerTaxonomy, payload: dict[str, Any], base_version: CareerTaxonomyVersion | None
) -> CareerImportBatch:
    _, digest = _canonical_payload(payload)
    batch, _ = CareerImportBatch.objects.get_or_create(
        payload_hash=digest,
        defaults={
            "taxonomy": taxonomy,
            "base_version": base_version,
            "schema_version": str(payload.get("schema_version", "")),
            "payload": payload,
        },
    )
    return batch


@transaction.atomic
def prepare_import_diff(*, batch: CareerImportBatch) -> CareerImportBatch:
    batch = CareerImportBatch.objects.select_for_update().get(pk=batch.pk)
    if batch.status not in {CareerImportBatch.Status.STAGED, CareerImportBatch.Status.VALIDATED}:
        raise ValidationError("Only a staged import can be validated")
    errors = validate_import_payload(batch.payload)
    batch.validation_errors = errors
    if errors:
        batch.status = CareerImportBatch.Status.REJECTED
        batch.save(update_fields=["validation_errors", "status", "updated_at"])
        return batch
    before = _version_records(batch.base_version)
    after = {
        item["code"]: {
            "code": item["code"],
            "title": item["title"],
            "title_ur": item.get("title_ur", ""),
            "pakistan_title": item.get("pakistan_title", ""),
            "cluster": item["cluster"],
            "family": item["family"],
            "summary": item["summary"],
            "typical_work": item["typical_work"],
            "aliases": sorted(item.get("aliases", [])),
        }
        for item in batch.payload["careers"]
    }
    for code in sorted(set(before) | set(after)):
        if code not in before:
            change = CareerImportDiff.ChangeType.NEW
        elif code not in after:
            change = CareerImportDiff.ChangeType.REMOVED
        elif before[code] != after[code]:
            change = CareerImportDiff.ChangeType.CHANGED
        else:
            continue
        CareerImportDiff.objects.create(
            batch=batch,
            entity_type="career",
            entity_key=code,
            change_type=change,
            before=before.get(code),
            after=after.get(code),
        )
    batch.status = CareerImportBatch.Status.DIFF_READY
    batch.validation_errors = []
    batch.save(update_fields=["status", "validation_errors", "updated_at"])
    return batch


@transaction.atomic
def approve_import(
    *, batch: CareerImportBatch, reviewer_reference: str, reason: str
) -> CareerImportBatch:
    if not reviewer_reference.strip() or not reason.strip():
        raise ValidationError("Reviewer and reason are required")
    batch = CareerImportBatch.objects.select_for_update().get(pk=batch.pk)
    if batch.status != CareerImportBatch.Status.DIFF_READY:
        raise ValidationError("Only a diff-ready import can be approved")
    batch.status = CareerImportBatch.Status.APPROVED
    batch.approved_by = reviewer_reference
    batch.approved_at = timezone.now()
    batch.save(update_fields=["status", "approved_by", "approved_at", "updated_at"])
    record_audit_event(
        event_type="career.import_approved",
        actor_type="reviewer",
        actor_reference=reviewer_reference,
        target_type="careers.careerimportbatch",
        target_id=batch.id,
        reason=reason,
        details={"diff_count": batch.diffs.count(), "payload_hash": batch.payload_hash},
    )
    return batch


@transaction.atomic
def publish_import(*, batch: CareerImportBatch, reviewer_reference: str) -> CareerTaxonomyVersion:
    batch = CareerImportBatch.objects.select_for_update().get(pk=batch.pk)
    if batch.status != CareerImportBatch.Status.APPROVED or not batch.approved_by:
        raise ValidationError("Import requires explicit approval before publication")
    number = (
        batch.taxonomy.versions.order_by("-version").values_list("version", flat=True).first() or 0
    ) + 1
    version = CareerTaxonomyVersion.objects.create(
        taxonomy=batch.taxonomy,
        version=number,
        provenance=f"Structured import {batch.payload_hash}",
        limitations=(
            "Imported structured reference content; requires field-level research enrichment."
        ),
        data_markers=["REFERENCE_ONLY", "NOT_READY_FOR_PARTICIPANT_RECOMMENDATION"],
    )
    clusters: dict[str, CareerCluster] = {}
    families: dict[tuple[str, str], CareerFamily] = {}
    for row in sorted(batch.payload["careers"], key=lambda item: item["code"]):
        cluster_key = str(row["cluster"]).lower().replace(" ", "-")
        cluster = clusters.get(cluster_key)
        if cluster is None:
            cluster = CareerCluster.objects.create(
                taxonomy_version=version, code=cluster_key, name_en=row["cluster"]
            )
            clusters[cluster_key] = cluster
        family_key = (cluster_key, str(row["family"]).lower().replace(" ", "-"))
        family = families.get(family_key)
        if family is None:
            family = CareerFamily.objects.create(
                taxonomy_version=version,
                cluster=cluster,
                code=family_key[1],
                name_en=row["family"],
            )
            families[family_key] = family
        profile, _ = CareerProfile.objects.get_or_create(code=row["code"])
        profile_version = CareerProfileVersion.objects.create(
            profile=profile,
            taxonomy_version=version,
            family=family,
            version=profile.versions.count() + 1,
            title_en=row["title"],
            title_ur=row.get("title_ur", ""),
            pakistan_title=row.get("pakistan_title", ""),
            summary=row["summary"],
            typical_work=row["typical_work"],
            limitations="Reference-only structured import; profile evidence is incomplete.",
        )
        for alias in row.get("aliases", []):
            CareerAlias.objects.create(
                profile_version=profile_version,
                name=alias,
                alias_type=CareerAlias.AliasType.ALTERNATE,
            )
    for profile_version in version.career_versions.all():
        for status in (ReviewStatus.IN_REVIEW, ReviewStatus.APPROVED):
            transition_review(
                target=profile_version,
                to_status=status,
                reviewer_reference=reviewer_reference,
                reason="Publish explicitly approved structured import as a new version.",
            )
            profile_version.refresh_from_db()
    for status in (ReviewStatus.IN_REVIEW, ReviewStatus.APPROVED):
        transition_review(
            target=version,
            to_status=status,
            reviewer_reference=reviewer_reference,
            reason="Publish explicitly approved structured import as a new version.",
        )
        version.refresh_from_db()
    version = publish_taxonomy_version(
        version=version,
        lifecycle=Lifecycle.PILOT,
        reviewer_reference=reviewer_reference,
        reason="Publish explicitly approved structured import as a new immutable version.",
    )
    batch.status = CareerImportBatch.Status.PUBLISHED
    batch.published_version = version
    batch.save(update_fields=["status", "published_version", "updated_at"])
    record_audit_event(
        event_type="career.import_published",
        actor_type="reviewer",
        actor_reference=reviewer_reference,
        target_type="careers.careertaxonomyversion",
        target_id=version.id,
        reason="Approved import materialised as a new immutable taxonomy version",
        details={"import_batch_id": str(batch.id), "version": number},
    )
    return version


@dataclass(frozen=True)
class CareerSnapshot:
    career_code: str
    title: str
    profile_status: str
    taxonomy_version: int
    strongly_relevant_dimensions: tuple[str, ...]
    variable_dimensions: tuple[str, ...]
    interests: tuple[str, ...]
    work_values: tuple[str, ...]
    work_environment: tuple[dict[str, str], ...]
    pathways: tuple[str, ...]
    skills: tuple[dict[str, str], ...]
    market_evidence: tuple[dict[str, Any], ...]
    freshness_counts: dict[str, int]
    limitations: tuple[str, ...]
    participant_recommendation_ready: bool

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def build_career_snapshot(
    *, profile_version: CareerProfileVersion, on_date: date | None = None
) -> CareerSnapshot:
    dimensions = profile_version.dimension_relationships.select_related("dimension").all()
    environments = profile_version.environment_observations.select_related("dimension").all()
    pathways = profile_version.pathways.all()
    requirements = profile_version.skill_requirements.select_related("skill").all()
    observations = profile_version.market_observations.select_related("source").all()
    freshness_counts = {choice: 0 for choice in Freshness.values}
    market: list[dict[str, Any]] = []
    limitations = {profile_version.limitations}
    for observation in observations:
        freshness = effective_freshness(
            stored=observation.freshness, expires_at=observation.expires_at, on_date=on_date
        )
        freshness_counts[freshness] += 1
        limitations.add(observation.limitations)
        market.append(
            {
                "type": observation.observation_type,
                "geography": "/".join(
                    part
                    for part in (observation.country, observation.region, observation.city)
                    if part
                ),
                "value_state": observation.value_state,
                "value": observation.value,
                "unit": observation.unit,
                "confidence": observation.confidence,
                "freshness": freshness,
                "source": observation.source.title,
            }
        )
    interest_category = "vocational_interest"
    value_category = "work_value"
    return CareerSnapshot(
        career_code=profile_version.profile.code,
        title=profile_version.title_en,
        profile_status=profile_version.lifecycle,
        taxonomy_version=profile_version.taxonomy_version.version,
        strongly_relevant_dimensions=tuple(
            item.dimension.name for item in dimensions if item.importance == "high"
        ),
        variable_dimensions=tuple(
            item.dimension.name for item in dimensions if item.importance in {"variable", "unknown"}
        ),
        interests=tuple(
            item.dimension.name
            for item in dimensions
            if item.dimension.category == interest_category
        ),
        work_values=tuple(
            item.dimension.name for item in dimensions if item.dimension.category == value_category
        ),
        work_environment=tuple(
            {
                "dimension": item.dimension.name,
                "prevalence": item.prevalence,
                "context": item.context,
            }
            for item in environments
        ),
        pathways=tuple(item.title for item in pathways),
        skills=tuple(
            {
                "skill": item.skill.name,
                "category": item.skill.category,
                "requirement": item.requirement,
            }
            for item in requirements
        ),
        market_evidence=tuple(market),
        freshness_counts=freshness_counts,
        limitations=tuple(sorted(limitations)),
        participant_recommendation_ready=profile_version.participant_recommendation_ready,
    )
