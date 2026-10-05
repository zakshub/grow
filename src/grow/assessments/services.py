from __future__ import annotations

import uuid
from decimal import Decimal
from typing import Any

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from grow.assessments.models import (
    AssessmentDimension,
    AssessmentItem,
    AssessmentItemPresentation,
    AssessmentLifecycle,
    AssessmentObservation,
    AssessmentResponse,
    AssessmentSession,
    AssessmentVersion,
    Contradiction,
    ContradictionEvidence,
    DimensionCategory,
    DimensionEvidence,
    EvidenceItem,
    EvidenceSource,
)
from grow.audit.services import record_audit_event
from grow.journeys.models import ParticipantJourney

CATEGORY_MAP: dict[str, str] = {
    DimensionCategory.COGNITIVE_FUNCTIONAL: EvidenceItem.Category.ABILITY,
    DimensionCategory.PERSONALITY_WORK_STYLE: EvidenceItem.Category.PERSONALITY,
    DimensionCategory.COMMUNICATION_SOCIAL: EvidenceItem.Category.ABILITY,
    DimensionCategory.CREATIVITY: EvidenceItem.Category.ABILITY,
    DimensionCategory.VOCATIONAL_INTEREST: EvidenceItem.Category.INTEREST,
    DimensionCategory.WORK_VALUE: EvidenceItem.Category.VALUE,
    DimensionCategory.WORK_ENVIRONMENT: EvidenceItem.Category.ENVIRONMENT,
}


@transaction.atomic
def publish_assessment_version(
    *, assessment_version: AssessmentVersion, lifecycle: str, actor_reference: str
) -> AssessmentVersion:
    allowed: dict[str, set[str]] = {
        AssessmentLifecycle.DRAFT: {AssessmentLifecycle.PILOT, AssessmentLifecycle.ACTIVE},
        AssessmentLifecycle.PILOT: {AssessmentLifecycle.ACTIVE, AssessmentLifecycle.RETIRED},
        AssessmentLifecycle.ACTIVE: {AssessmentLifecycle.RETIRED},
    }
    if lifecycle not in allowed.get(assessment_version.lifecycle, set()):
        raise ValidationError(
            f"Lifecycle transition {assessment_version.lifecycle} -> {lifecycle} is not allowed"
        )
    if not actor_reference.strip():
        raise ValidationError("Publisher reference is required")
    if (
        not assessment_version.items.exists()
        or not assessment_version.dimension_requirements.exists()
    ):
        raise ValidationError("Published assessment versions require items and dimensions")
    assessment_version.lifecycle = lifecycle
    now = timezone.now()
    if assessment_version.published_at is None:
        assessment_version.published_at = now
    if lifecycle == AssessmentLifecycle.RETIRED:
        assessment_version.retired_at = now
    assessment_version.save(update_fields=["lifecycle", "published_at", "retired_at", "updated_at"])
    record_audit_event(
        event_type="assessment.version_lifecycle_changed",
        actor_type="reviewer",
        actor_reference=actor_reference,
        target_type="assessment_version",
        target_id=assessment_version.id,
        reason=f"Assessment version moved to {lifecycle}",
        details={
            "definition_code": assessment_version.definition.code,
            "version": assessment_version.version,
            "lifecycle": lifecycle,
        },
    )
    return assessment_version


@transaction.atomic
def start_assessment_session(
    *,
    journey: ParticipantJourney,
    assessment_version: AssessmentVersion,
    audience: str,
    language: str = "ur",
    locale: str = "pk",
    maximum_items: int | None = None,
    actor_type: str = "system",
    actor_reference: str = "",
) -> AssessmentSession:
    if assessment_version.lifecycle not in {
        AssessmentLifecycle.PILOT,
        AssessmentLifecycle.ACTIVE,
    }:
        raise ValidationError("Only pilot or active assessment versions can start sessions")
    limit = maximum_items or assessment_version.maximum_items
    if limit < 1 or limit > assessment_version.maximum_items:
        raise ValidationError("Session item limit must use the version's allowed range")
    session = AssessmentSession(
        journey=journey,
        assessment_version=assessment_version,
        definition_code=assessment_version.definition.code,
        definition_version=str(assessment_version.version),
        audience=audience,
        language=language,
        locale=locale,
        maximum_items=limit,
        status=AssessmentSession.SessionStatus.IN_PROGRESS,
        started_at=timezone.now(),
    )
    session.full_clean()
    session.save()
    record_audit_event(
        event_type="assessment.session_started",
        actor_type=actor_type,
        actor_reference=actor_reference,
        target_type="assessment_session",
        target_id=session.id,
        reason="Version-pinned assessment session started",
        details={
            "assessment_version_id": str(assessment_version.id),
            "definition_code": assessment_version.definition.code,
            "version": assessment_version.version,
            "audience": audience,
            "language": language,
        },
    )
    return session


def _validate_response(item: AssessmentItem, structured_value: Any, text_value: str) -> None:
    text_types = {AssessmentItem.ItemType.SHORT_TEXT, AssessmentItem.ItemType.LONG_TEXT}
    if item.item_type in text_types:
        if not text_value.strip() or structured_value is not None:
            raise ValidationError("Text items require only a text response")
        return
    if text_value.strip() or structured_value is None:
        raise ValidationError("Structured items require only a structured response")
    schema = item.response_schema
    if item.item_type == AssessmentItem.ItemType.MULTI_CHOICE:
        if not isinstance(structured_value, list):
            raise ValidationError("Multi-choice response must be a list")
    elif item.item_type == AssessmentItem.ItemType.RANKING:
        if not isinstance(structured_value, list) or len(set(structured_value)) != len(
            structured_value
        ):
            raise ValidationError("Ranking response must be an ordered unique list")
    elif item.item_type == AssessmentItem.ItemType.NUMERIC:
        if not isinstance(structured_value, int | float) or isinstance(structured_value, bool):
            raise ValidationError("Numeric response must be a number")
        if "minimum" in schema and structured_value < schema["minimum"]:
            raise ValidationError("Numeric response is below the allowed minimum")
        if "maximum" in schema and structured_value > schema["maximum"]:
            raise ValidationError("Numeric response exceeds the allowed maximum")
    else:
        allowed = schema.get("options", [])
        if allowed and structured_value not in allowed:
            raise ValidationError("Response is not an allowed option")


def _interpret_response(
    item: AssessmentItem, structured_value: Any
) -> tuple[dict[str, Any] | None, str, Decimal | None, str]:
    if item.item_type in {AssessmentItem.ItemType.SHORT_TEXT, AssessmentItem.ItemType.LONG_TEXT}:
        return None, EvidenceItem.Direction.NEUTRAL, None, EvidenceItem.ConfidenceBand.LOW
    rule = item.interpretation_rules.get("map", {}).get(str(structured_value))
    if not rule:
        return None, EvidenceItem.Direction.NEUTRAL, None, EvidenceItem.ConfidenceBand.UNKNOWN
    score = Decimal(str(rule.get("confidence_score", "0.35")))
    return (
        {"pilot_signal": rule.get("signal"), "polarity": rule.get("polarity")},
        rule.get("direction", EvidenceItem.Direction.NEUTRAL),
        score,
        rule.get("confidence_band", EvidenceItem.ConfidenceBand.LOW),
    )


@transaction.atomic
def record_assessment_response(
    *,
    presentation: AssessmentItemPresentation,
    structured_value: Any = None,
    text_value: str = "",
    skipped: bool = False,
    completion_quality: str = "complete",
    actor_type: str = "participant",
    actor_reference: str = "",
) -> AssessmentResponse:
    if hasattr(presentation, "response"):
        raise ValidationError("This item presentation already has a response")
    if presentation.session.status != AssessmentSession.SessionStatus.IN_PROGRESS:
        raise ValidationError("Responses require an in-progress assessment session")
    assessment_version = presentation.session.assessment_version
    if assessment_version is None:
        raise ValidationError("Assessment session must pin a version")
    if presentation.item.assessment_version_id != presentation.session.assessment_version_id:
        raise ValidationError("Response item must belong to the session's pinned version")
    if not skipped:
        _validate_response(presentation.item, structured_value, text_value)
    response = AssessmentResponse(
        presentation=presentation,
        structured_value=structured_value,
        text_value=text_value,
        skipped=skipped,
        completion_quality=completion_quality,
    )
    response.full_clean()
    response.save()

    if not skipped:
        item = presentation.item
        normalized, direction, confidence_score, confidence_band = _interpret_response(
            item, structured_value
        )
        is_text = item.item_type in {
            AssessmentItem.ItemType.SHORT_TEXT,
            AssessmentItem.ItemType.LONG_TEXT,
        }
        source_type = (
            EvidenceSource.SourceType.OPEN_RESPONSE if is_text else item.evidence_source_type
        )
        source = EvidenceSource.objects.create(
            source_type=source_type,
            reference_kind="assessment_response",
            reference_id=response.id,
            provenance_version=assessment_version.calculation_version,
            details={
                "assessment_version_id": str(presentation.session.assessment_version_id),
                "item_id": str(item.id),
                "variant_id": str(presentation.variant_id),
                "completion_quality": completion_quality,
            },
        )
        evidence = EvidenceItem(
            journey=presentation.session.journey,
            assessment_session=presentation.session,
            dimension=item.dimension,
            source=source,
            dimension_code=item.dimension.code,
            category=CATEGORY_MAP[item.dimension.category],
            value_status=EvidenceItem.ValueStatus.KNOWN,
            text_value=text_value if is_text else "",
            structured_value=structured_value if not is_text else None,
            normalized_interpretation=normalized,
            direction=direction,
            confidence_band=confidence_band,
            confidence_score=confidence_score,
            confidence_reason=(
                "Raw open response awaits structured human observation."
                if is_text
                else "Deterministic pilot item rule; not a validated measurement."
            ),
            review_status=(
                EvidenceItem.ReviewStatus.NEEDS_CLARIFICATION
                if is_text
                else EvidenceItem.ReviewStatus.UNREVIEWED
            ),
            supporting_context={"response_id": str(response.id)},
            interpretation_method="none" if is_text else "deterministic_item_rule",
            interpretation_version=("none" if is_text else assessment_version.calculation_version),
            privacy_class=(
                EvidenceItem.PrivacyClass.SENSITIVE
                if is_text
                else EvidenceItem.PrivacyClass.STRUCTURED_EVIDENCE
            ),
        )
        evidence.full_clean()
        evidence.save()
        DimensionEvidence.objects.create(
            session=presentation.session,
            dimension=item.dimension,
            evidence_item=evidence,
            independent_source_key=f"response:{response.id}",
            eligible_for_aggregation=not is_text and normalized is not None,
            eligibility_reason=(
                "Raw text is stored without automatic interpretation."
                if is_text
                else "Deterministic structured response."
            ),
        )

    record_audit_event(
        event_type="assessment.response_recorded",
        actor_type=actor_type,
        actor_reference=actor_reference,
        target_type="assessment_response",
        target_id=response.id,
        reason="Assessment response captured",
        details={
            "session_id": str(presentation.session_id),
            "item_id": str(presentation.item_id),
            "skipped": skipped,
        },
    )
    return response


@transaction.atomic
def add_reviewer_observation(
    *,
    session: AssessmentSession,
    dimension: AssessmentDimension,
    structured_value: dict[str, Any],
    reviewer_reference: str,
    reason: str,
    response: AssessmentResponse | None = None,
) -> AssessmentObservation:
    if not reviewer_reference.strip() or not reason.strip():
        raise ValidationError("Reviewer reference and reason are required")
    if response and response.presentation.session_id != session.id:
        raise ValidationError("Observed response must belong to the assessment session")
    assessment_version = session.assessment_version
    if assessment_version is None:
        raise ValidationError("Assessment session must pin a version")
    direction = structured_value.get("direction", EvidenceItem.Direction.NEUTRAL)
    confidence_band = structured_value.get("confidence_band", EvidenceItem.ConfidenceBand.LOW)
    confidence_score_value = structured_value.get("confidence_score")
    observation = AssessmentObservation.objects.create(
        session=session,
        response=response,
        dimension=dimension,
        observer_type="reviewer",
        observer_reference=reviewer_reference,
        structured_value=structured_value,
        notes=reason,
    )
    source = EvidenceSource.objects.create(
        source_type=EvidenceSource.SourceType.HUMAN_OBSERVATION,
        reference_kind="assessment_observation",
        reference_id=observation.id,
        provenance_version=assessment_version.calculation_version,
        details={"reviewer_reference": reviewer_reference},
    )
    evidence = EvidenceItem(
        journey=session.journey,
        assessment_session=session,
        dimension=dimension,
        source=source,
        dimension_code=dimension.code,
        category=CATEGORY_MAP[dimension.category],
        value_status=EvidenceItem.ValueStatus.KNOWN,
        structured_value=structured_value,
        normalized_interpretation={
            "pilot_signal": structured_value.get("signal"),
            "polarity": structured_value.get("polarity"),
        },
        direction=direction,
        confidence_band=confidence_band,
        confidence_score=(
            Decimal(str(confidence_score_value)) if confidence_score_value is not None else None
        ),
        confidence_reason=reason,
        review_status=EvidenceItem.ReviewStatus.REVIEWED,
        supporting_context={"observation_id": str(observation.id)},
        interpretation_method="human_structured_observation",
        interpretation_version="reviewer-pilot-v1",
    )
    evidence.full_clean()
    evidence.save()
    DimensionEvidence.objects.create(
        session=session,
        dimension=dimension,
        evidence_item=evidence,
        independent_source_key=f"observation:{observation.id}",
        eligibility_reason="Structured human observation.",
    )
    record_audit_event(
        event_type="assessment.observation_added",
        actor_type="reviewer",
        actor_reference=reviewer_reference,
        target_type="assessment_observation",
        target_id=observation.id,
        reason=reason,
        details={"session_id": str(session.id), "dimension_code": dimension.code},
    )
    return observation


@transaction.atomic
def mark_evidence_reviewed(
    *, evidence: EvidenceItem, review_status: str, reviewer_reference: str, reason: str
) -> EvidenceItem:
    if review_status not in {
        EvidenceItem.ReviewStatus.REVIEWED,
        EvidenceItem.ReviewStatus.REJECTED,
        EvidenceItem.ReviewStatus.NEEDS_CLARIFICATION,
    }:
        raise ValidationError("Unsupported evidence review status")
    if not reviewer_reference.strip() or not reason.strip():
        raise ValidationError("Reviewer reference and reason are required")
    fields = {
        field.name: getattr(evidence, field.name)
        for field in EvidenceItem._meta.fields
        if field.name not in {"id", "version", "supersedes", "review_status", "evidence_chain_id"}
    }
    reviewed = EvidenceItem(
        **fields,
        evidence_chain_id=evidence.evidence_chain_id,
        version=evidence.version + 1,
        supersedes=evidence,
        review_status=review_status,
    )
    reviewed.full_clean()
    reviewed.save()
    if hasattr(evidence, "dimension_evidence_link"):
        link = evidence.dimension_evidence_link
        DimensionEvidence.objects.create(
            session=link.session,
            dimension=link.dimension,
            evidence_item=reviewed,
            independent_source_key=link.independent_source_key,
            eligible_for_aggregation=(
                link.eligible_for_aggregation
                and review_status != EvidenceItem.ReviewStatus.REJECTED
            ),
            eligibility_reason=f"Reviewer status: {review_status}. {reason}",
        )
    record_audit_event(
        event_type="evidence.reviewed",
        actor_type="reviewer",
        actor_reference=reviewer_reference,
        target_type="evidence_item",
        target_id=reviewed.id,
        reason=reason,
        details={
            "supersedes_id": str(evidence.id),
            "review_status": review_status,
            "evidence_chain_id": str(evidence.evidence_chain_id),
        },
    )
    return reviewed


@transaction.atomic
def record_contradiction(
    *,
    journey_id: uuid.UUID,
    evidence_ids: list[uuid.UUID],
    summary: str,
    actor_type: str,
    actor_reference: str = "",
    severity: str = Contradiction.Severity.MODERATE,
    reason: str = "",
) -> Contradiction:
    unique_ids = list(dict.fromkeys(evidence_ids))
    if len(unique_ids) < 2:
        raise ValidationError("A contradiction requires at least two evidence items")
    evidence = list(EvidenceItem.objects.select_related("dimension").filter(id__in=unique_ids))
    if len(evidence) != len(unique_ids):
        raise ValidationError("Every evidence item must exist")
    if any(item.journey_id != journey_id for item in evidence):
        raise ValidationError("Contradictory evidence must belong to the same journey")
    dimension_codes = {item.dimension_code for item in evidence}
    if len(dimension_codes) != 1:
        raise ValidationError("Contradictory evidence must concern the same dimension")
    if not summary.strip():
        raise ValidationError("Contradiction summary is required")
    dimension = next((item.dimension for item in evidence if item.dimension_id), None)

    contradiction = Contradiction.objects.create(
        journey_id=journey_id,
        dimension=dimension,
        summary=summary,
        reason=reason or summary,
        severity=severity,
        resolution_status=Contradiction.ResolutionStatus.OPEN,
    )
    for index, item in enumerate(evidence):
        relation = (
            ContradictionEvidence.Relation.CLAIM
            if index == 0
            else ContradictionEvidence.Relation.COUNTEREVIDENCE
        )
        ContradictionEvidence.objects.create(
            contradiction=contradiction, evidence_item=item, relation=relation
        )
    record_audit_event(
        event_type="evidence.contradiction_recorded",
        actor_type=actor_type,
        actor_reference=actor_reference,
        target_type="contradiction",
        target_id=contradiction.id,
        reason=summary,
        details={
            "evidence_ids": [str(item.id) for item in evidence],
            "dimension_code": next(iter(dimension_codes)),
            "severity": severity,
        },
    )
    return contradiction


@transaction.atomic
def resolve_contradiction(
    *,
    contradiction: Contradiction,
    resolution_status: str,
    resolution: str,
    reviewer_reference: str,
) -> Contradiction:
    if resolution_status not in {
        Contradiction.ResolutionStatus.RESOLVED,
        Contradiction.ResolutionStatus.ACCEPTED_UNCERTAINTY,
    }:
        raise ValidationError("Contradiction resolution must be explicit")
    if not resolution.strip() or not reviewer_reference.strip():
        raise ValidationError("Reviewer and resolution are required")
    contradiction.resolution_status = resolution_status
    contradiction.resolution = resolution
    contradiction.reviewer_reference = reviewer_reference
    contradiction.resolved_at = timezone.now()
    contradiction.save(
        update_fields=[
            "resolution_status",
            "resolution",
            "reviewer_reference",
            "resolved_at",
            "updated_at",
        ]
    )
    record_audit_event(
        event_type="evidence.contradiction_resolved",
        actor_type="reviewer",
        actor_reference=reviewer_reference,
        target_type="contradiction",
        target_id=contradiction.id,
        reason=resolution,
        details={"resolution_status": resolution_status},
    )
    return contradiction


@transaction.atomic
def detect_contradictions(
    *, session: AssessmentSession, actor_type: str = "system"
) -> list[Contradiction]:
    evidence = list(
        EvidenceItem.objects.filter(
            assessment_session=session,
            superseded_by__isnull=True,
            value_status=EvidenceItem.ValueStatus.KNOWN,
        )
        .exclude(normalized_interpretation__isnull=True)
        .select_related("dimension")
        .order_by("observed_at", "id")
    )
    created: list[Contradiction] = []
    for index, first in enumerate(evidence):
        first_interpretation = first.normalized_interpretation or {}
        first_polarity = first_interpretation.get("polarity")
        if not isinstance(first_polarity, int | float):
            continue
        for second in evidence[index + 1 :]:
            if first.dimension_code != second.dimension_code:
                continue
            second_interpretation = second.normalized_interpretation or {}
            second_polarity = second_interpretation.get("polarity")
            if not isinstance(second_polarity, int | float):
                continue
            if first_polarity * second_polarity > -0.25:
                continue
            already_exists = Contradiction.objects.filter(
                journey=session.journey,
                contradictionevidence__evidence_item=first,
            ).filter(contradictionevidence__evidence_item=second)
            if already_exists.exists():
                continue
            created.append(
                record_contradiction(
                    journey_id=session.journey_id,
                    evidence_ids=[first.id, second.id],
                    summary=(f"Deterministic pilot signals conflict for {first.dimension_code}."),
                    reason="Opposing normalized pilot signals require clarification.",
                    actor_type=actor_type,
                )
            )
    return created
