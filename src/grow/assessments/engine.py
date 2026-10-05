from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum

from django.db import transaction
from django.db.models import QuerySet
from django.utils import timezone

from grow.assessments.models import (
    AssessmentDimension,
    AssessmentDimensionRequirement,
    AssessmentItem,
    AssessmentItemPresentation,
    AssessmentItemVariant,
    AssessmentSession,
    Contradiction,
    DimensionEvidence,
    DimensionResult,
    EvidenceItem,
)
from grow.audit.services import record_audit_event
from grow.participants.models import EducationStage
from grow.reviews.models import HumanReview


class NextAssessmentAction(StrEnum):
    ASK_MORE = "ASK_MORE"
    SUFFICIENT = "SUFFICIENT"
    HUMAN_REVIEW_REQUIRED = "HUMAN_REVIEW_REQUIRED"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True)
class DimensionSnapshot:
    dimension_code: str
    dimension_name: str
    category: str
    sufficiency: str
    confidence_band: str
    confidence_score: Decimal | None
    supporting_count: int
    conflicting_count: int
    independent_source_count: int
    source_type_count: int
    unresolved_contradiction_count: int
    evidence_ids: tuple[str, ...]
    reasons: tuple[str, ...]
    next_action: str


@dataclass(frozen=True)
class AssessmentSnapshot:
    session_id: str
    assessment_version_id: str | None
    dimensions: tuple[DimensionSnapshot, ...]
    known_dimension_count: int
    unknown_dimension_count: int
    completion: str
    human_review_required: bool
    unresolved_contradiction_count: int
    recommended_next_action: NextAssessmentAction


@dataclass(frozen=True)
class NextItemDecision:
    action: NextAssessmentAction
    reason: str
    item: AssessmentItem | None = None
    variant: AssessmentItemVariant | None = None
    dimension_code: str | None = None


def _latest_dimension_links(
    session: AssessmentSession, dimension: AssessmentDimension
) -> list[DimensionEvidence]:
    return list(
        DimensionEvidence.objects.filter(
            session=session,
            dimension=dimension,
            evidence_item__superseded_by__isnull=True,
        )
        .select_related("evidence_item__source")
        .order_by("evidence_item__observed_at", "evidence_item_id")
    )


def _confidence(
    *,
    links: list[DimensionEvidence],
    independent_count: int,
    source_type_count: int,
    contradiction_count: int,
) -> tuple[Decimal | None, str, dict[str, object]]:
    eligible = [
        link
        for link in links
        if link.eligible_for_aggregation
        and link.evidence_item.value_status == EvidenceItem.ValueStatus.KNOWN
        and link.evidence_item.review_status != EvidenceItem.ReviewStatus.REJECTED
    ]
    inputs: dict[str, object] = {
        "eligible_evidence_count": len(eligible),
        "independent_source_count": independent_count,
        "source_type_count": source_type_count,
        "reviewed_evidence_count": sum(
            link.evidence_item.review_status == EvidenceItem.ReviewStatus.REVIEWED
            for link in eligible
        ),
        "unresolved_contradiction_count": contradiction_count,
        "formula": (
            "0.20 + 0.20*independent(max3) + 0.10*diversity(max2) "
            "+ 0.10*reviewed - 0.25*contradiction(max2)"
        ),
    }
    if not eligible:
        return None, EvidenceItem.ConfidenceBand.UNKNOWN, inputs
    score = Decimal("0.20")
    score += Decimal("0.20") * min(independent_count, 3)
    score += Decimal("0.10") * min(max(source_type_count - 1, 0), 2)
    if inputs["reviewed_evidence_count"]:
        score += Decimal("0.10")
    score -= Decimal("0.25") * min(contradiction_count, 2)
    score = max(Decimal("0.10"), min(score, Decimal("0.95")))
    if score < Decimal("0.45"):
        band = EvidenceItem.ConfidenceBand.LOW
    elif score < Decimal("0.75"):
        band = EvidenceItem.ConfidenceBand.MODERATE
    else:
        band = EvidenceItem.ConfidenceBand.HIGH
    return score, band, inputs


def evaluate_dimension(
    *, session: AssessmentSession, requirement: AssessmentDimensionRequirement
) -> tuple[DimensionSnapshot, dict[str, object]]:
    links = _latest_dimension_links(session, requirement.dimension)
    eligible = [
        link
        for link in links
        if link.eligible_for_aggregation
        and link.evidence_item.value_status == EvidenceItem.ValueStatus.KNOWN
        and link.evidence_item.review_status != EvidenceItem.ReviewStatus.REJECTED
    ]
    independent_keys = {link.independent_source_key for link in eligible}
    source_types = {link.evidence_item.source.source_type for link in eligible}
    unresolved = Contradiction.objects.filter(
        journey=session.journey,
        dimension=requirement.dimension,
        resolution_status__in=[
            Contradiction.ResolutionStatus.UNKNOWN,
            Contradiction.ResolutionStatus.OPEN,
        ],
    ).count()
    supporting = sum(
        link.evidence_item.direction == EvidenceItem.Direction.SUPPORTS for link in eligible
    )
    conflicting = sum(
        link.evidence_item.direction == EvidenceItem.Direction.CONFLICTS for link in eligible
    )
    confidence_score, confidence_band, calculation_inputs = _confidence(
        links=links,
        independent_count=len(independent_keys),
        source_type_count=len(source_types),
        contradiction_count=unresolved,
    )
    reasons: list[str] = []
    if not links:
        sufficiency = DimensionResult.Sufficiency.UNKNOWN
        reasons.append("No evidence has been recorded; absence is not a low signal.")
        next_action = "Ask an applicable pilot item for this dimension."
    elif unresolved:
        sufficiency = DimensionResult.Sufficiency.CONTRADICTORY
        reasons.append(f"{unresolved} unresolved contradiction(s) preserve opposing evidence.")
        next_action = "Ask a clarification item or request human review."
    elif not eligible:
        sufficiency = DimensionResult.Sufficiency.INSUFFICIENT
        reasons.append("Evidence exists but is not eligible for deterministic aggregation.")
        next_action = "Collect a structured signal or reviewer observation."
    elif len(independent_keys) < requirement.minimum_independent_sources:
        sufficiency = DimensionResult.Sufficiency.TENTATIVE
        reasons.append(
            f"{len(independent_keys)} independent signal(s); "
            f"{requirement.minimum_independent_sources} required by this pilot version."
        )
        next_action = "Collect another independent signal."
    elif len(source_types) < requirement.minimum_source_types:
        sufficiency = DimensionResult.Sufficiency.INSUFFICIENT
        reasons.append(
            f"Evidence lacks source diversity: {len(source_types)} type(s), "
            f"{requirement.minimum_source_types} required."
        )
        next_action = "Collect evidence using a different source type."
    elif confidence_band in {
        EvidenceItem.ConfidenceBand.MODERATE,
        EvidenceItem.ConfidenceBand.HIGH,
    }:
        sufficiency = DimensionResult.Sufficiency.SUPPORTED
        reasons.append(
            "Pilot evidence count, independence, diversity, and confidence rules are met."
        )
        next_action = "No additional item is required by the current pilot policy."
    else:
        sufficiency = DimensionResult.Sufficiency.TENTATIVE
        reasons.append("Evidence exists but confidence remains low.")
        next_action = "Collect a stronger or reviewed independent signal."
    calculation_inputs.update(
        {
            "minimum_independent_sources": requirement.minimum_independent_sources,
            "minimum_source_types": requirement.minimum_source_types,
            "evidence_ids": [str(link.evidence_item_id) for link in links],
            "required": requirement.required,
        }
    )
    snapshot = DimensionSnapshot(
        dimension_code=requirement.dimension.code,
        dimension_name=requirement.dimension.name,
        category=requirement.dimension.category,
        sufficiency=sufficiency,
        confidence_band=confidence_band,
        confidence_score=confidence_score,
        supporting_count=supporting,
        conflicting_count=conflicting,
        independent_source_count=len(independent_keys),
        source_type_count=len(source_types),
        unresolved_contradiction_count=unresolved,
        evidence_ids=tuple(str(link.evidence_item_id) for link in links),
        reasons=tuple(reasons),
        next_action=next_action,
    )
    return snapshot, calculation_inputs


def _persist_dimension_result(
    *,
    session: AssessmentSession,
    dimension: AssessmentDimension,
    snapshot: DimensionSnapshot,
    calculation_inputs: dict[str, object],
) -> DimensionResult:
    assessment_version = session.assessment_version
    assert assessment_version is not None
    previous = (
        DimensionResult.objects.filter(session=session, dimension=dimension)
        .order_by("-version")
        .first()
    )
    result_kwargs: dict[str, object] = {
        "session": session,
        "dimension": dimension,
        "version": previous.version + 1 if previous else 1,
        "supersedes": previous,
        "sufficiency": snapshot.sufficiency,
        "confidence_band": snapshot.confidence_band,
        "confidence_score": snapshot.confidence_score,
        "supporting_count": snapshot.supporting_count,
        "conflicting_count": snapshot.conflicting_count,
        "independent_source_count": snapshot.independent_source_count,
        "source_type_count": snapshot.source_type_count,
        "unresolved_contradiction_count": snapshot.unresolved_contradiction_count,
        "calculation_version": assessment_version.calculation_version,
        "calculation_inputs": calculation_inputs,
        "reasons": list(snapshot.reasons),
        "next_action": snapshot.next_action,
    }
    if previous:
        result_kwargs["result_chain_id"] = previous.result_chain_id
    result = DimensionResult(
        **result_kwargs,
    )
    result.full_clean()
    result.save()
    return result


def _completion_action(dimensions: list[DimensionSnapshot]) -> NextAssessmentAction:
    if not dimensions:
        return NextAssessmentAction.UNKNOWN
    if any(item.sufficiency == DimensionResult.Sufficiency.CONTRADICTORY for item in dimensions):
        return NextAssessmentAction.ASK_MORE
    if all(item.sufficiency == DimensionResult.Sufficiency.SUPPORTED for item in dimensions):
        return NextAssessmentAction.SUFFICIENT
    return NextAssessmentAction.ASK_MORE


@transaction.atomic
def build_assessment_snapshot(
    *, session: AssessmentSession, persist: bool = True
) -> AssessmentSnapshot:
    if session.assessment_version_id is None:
        return AssessmentSnapshot(
            session_id=str(session.id),
            assessment_version_id=None,
            dimensions=(),
            known_dimension_count=0,
            unknown_dimension_count=0,
            completion=AssessmentSession.SufficiencyStatus.UNKNOWN,
            human_review_required=False,
            unresolved_contradiction_count=0,
            recommended_next_action=NextAssessmentAction.UNKNOWN,
        )
    assessment_version = session.assessment_version
    assert assessment_version is not None
    requirements = list(
        assessment_version.dimension_requirements.select_related("dimension").order_by(
            "priority", "dimension__code"
        )
    )
    snapshots: list[DimensionSnapshot] = []
    for requirement in requirements:
        snapshot, inputs = evaluate_dimension(session=session, requirement=requirement)
        snapshots.append(snapshot)
        if persist:
            _persist_dimension_result(
                session=session,
                dimension=requirement.dimension,
                snapshot=snapshot,
                calculation_inputs=inputs,
            )
    required_codes = {item.dimension.code for item in requirements if item.required}
    required_results = [item for item in snapshots if item.dimension_code in required_codes]
    action = _completion_action(required_results)
    unresolved_count = sum(item.unresolved_contradiction_count for item in snapshots)
    return AssessmentSnapshot(
        session_id=str(session.id),
        assessment_version_id=str(session.assessment_version_id),
        dimensions=tuple(snapshots),
        known_dimension_count=sum(
            item.sufficiency != DimensionResult.Sufficiency.UNKNOWN for item in snapshots
        ),
        unknown_dimension_count=sum(
            item.sufficiency == DimensionResult.Sufficiency.UNKNOWN for item in snapshots
        ),
        completion=(
            AssessmentSession.SufficiencyStatus.SUFFICIENT
            if action == NextAssessmentAction.SUFFICIENT
            else AssessmentSession.SufficiencyStatus.INSUFFICIENT
        ),
        human_review_required=False,
        unresolved_contradiction_count=unresolved_count,
        recommended_next_action=action,
    )


def _variant_for_session(
    item: AssessmentItem, session: AssessmentSession
) -> AssessmentItemVariant | None:
    education: str = EducationStage.UNKNOWN
    if hasattr(session.journey.participant, "profile"):
        education = session.journey.participant.profile.education_stage
    variants = list(item.variants.filter(locale=session.locale))

    def score(variant: AssessmentItemVariant) -> tuple[int, int, int, int]:
        return (
            1 if variant.language == session.language else 0,
            1 if variant.audience == session.audience else 0,
            1 if variant.education_stage == education else 0,
            1 if variant.language == "en" else 0,
        )

    applicable = [
        variant
        for variant in variants
        if variant.language in {session.language, "en"}
        and variant.audience in {session.audience, AssessmentItemVariant.Audience.GENERAL}
        and (
            education == EducationStage.UNKNOWN
            or variant.education_stage in {education, EducationStage.UNKNOWN}
        )
    ]
    return max(applicable, key=score, default=None)


def _candidate_items(session: AssessmentSession) -> QuerySet[AssessmentItem]:
    assessment_version = session.assessment_version
    assert assessment_version is not None
    presented = session.presentations.values_list("item_id", flat=True)
    return (
        assessment_version.items.exclude(id__in=presented)
        .select_related("dimension", "section")
        .prefetch_related("variants")
    )


def select_next_item(session: AssessmentSession) -> NextItemDecision:
    if session.assessment_version_id is None:
        return NextItemDecision(NextAssessmentAction.UNKNOWN, "No assessment version is pinned.")
    if session.status != AssessmentSession.SessionStatus.IN_PROGRESS:
        return NextItemDecision(
            NextAssessmentAction.UNKNOWN, "Assessment session is not in progress."
        )
    snapshot = build_assessment_snapshot(session=session, persist=False)
    assessment_version = session.assessment_version
    assert assessment_version is not None
    limit = session.maximum_items or assessment_version.maximum_items
    presented_count = session.presentations.count()
    if presented_count >= limit:
        if snapshot.recommended_next_action == NextAssessmentAction.SUFFICIENT:
            return NextItemDecision(
                NextAssessmentAction.SUFFICIENT, "All required dimensions are supported."
            )
        return NextItemDecision(
            NextAssessmentAction.HUMAN_REVIEW_REQUIRED,
            "The maximum item limit was reached before sufficient evidence was available.",
        )
    if snapshot.recommended_next_action == NextAssessmentAction.SUFFICIENT:
        return NextItemDecision(
            NextAssessmentAction.SUFFICIENT, "All required dimensions are supported."
        )

    candidates = list(_candidate_items(session))
    dimension_priority = {
        requirement.dimension.code: requirement.priority
        for requirement in assessment_version.dimension_requirements.select_related("dimension")
    }
    sufficiency_priority: dict[str, int] = {
        DimensionResult.Sufficiency.CONTRADICTORY: 0,
        DimensionResult.Sufficiency.UNKNOWN: 1,
        DimensionResult.Sufficiency.INSUFFICIENT: 2,
        DimensionResult.Sufficiency.TENTATIVE: 3,
        DimensionResult.Sufficiency.SUPPORTED: 4,
    }
    ordered = sorted(
        snapshot.dimensions,
        key=lambda item: (
            sufficiency_priority[item.sufficiency],
            dimension_priority[item.dimension_code],
        ),
    )
    for dimension in ordered:
        if dimension.sufficiency == DimensionResult.Sufficiency.SUPPORTED:
            continue
        dimension_items = [
            item for item in candidates if item.dimension.code == dimension.dimension_code
        ]
        if dimension.sufficiency == DimensionResult.Sufficiency.CONTRADICTORY:
            clarification = [
                item
                for item in dimension_items
                if item.purpose == AssessmentItem.Purpose.CLARIFICATION
            ]
            dimension_items = clarification or dimension_items
        for item in sorted(
            dimension_items, key=lambda candidate: (candidate.order, candidate.code)
        ):
            variant = _variant_for_session(item, session)
            if variant:
                return NextItemDecision(
                    NextAssessmentAction.ASK_MORE,
                    dimension.next_action,
                    item=item,
                    variant=variant,
                    dimension_code=dimension.dimension_code,
                )
    if snapshot.recommended_next_action == NextAssessmentAction.SUFFICIENT:
        return NextItemDecision(
            NextAssessmentAction.SUFFICIENT, "All required dimensions are supported."
        )
    if any(item.sufficiency == DimensionResult.Sufficiency.CONTRADICTORY for item in ordered):
        return NextItemDecision(
            NextAssessmentAction.HUMAN_REVIEW_REQUIRED,
            "Contradictory evidence remains and no applicable clarification item is available.",
        )
    if not candidates:
        return NextItemDecision(
            NextAssessmentAction.HUMAN_REVIEW_REQUIRED,
            "Approved items are exhausted before required evidence is sufficient.",
        )
    return NextItemDecision(
        NextAssessmentAction.UNKNOWN,
        "No language, audience, and education variant is applicable.",
    )


@transaction.atomic
def present_next_item(
    *, session: AssessmentSession, actor_type: str = "system", actor_reference: str = ""
) -> tuple[NextItemDecision, AssessmentItemPresentation | None]:
    decision = select_next_item(session)
    if decision.action != NextAssessmentAction.ASK_MORE:
        return decision, None
    assert decision.item is not None
    assert decision.variant is not None
    assessment_version = session.assessment_version
    assert assessment_version is not None
    sequence = session.presentations.count() + 1
    presentation = AssessmentItemPresentation.objects.create(
        session=session,
        item=decision.item,
        variant=decision.variant,
        sequence=sequence,
        selection_status=decision.action,
        selection_reason=decision.reason,
        selection_policy_version=assessment_version.selection_policy_version,
    )
    record_audit_event(
        event_type="assessment.item_presented",
        actor_type=actor_type,
        actor_reference=actor_reference,
        target_type="assessment_item_presentation",
        target_id=presentation.id,
        reason=decision.reason,
        details={
            "session_id": str(session.id),
            "item_id": str(decision.item.id),
            "variant_id": str(decision.variant.id),
            "dimension_code": decision.dimension_code,
            "selection_policy_version": assessment_version.selection_policy_version,
        },
    )
    return decision, presentation


@transaction.atomic
def evaluate_assessment_session(
    *, session: AssessmentSession, actor_reference: str = "system"
) -> AssessmentSnapshot:
    assessment_version = session.assessment_version
    if assessment_version is None:
        raise ValueError("Assessment session must pin a version")
    snapshot = build_assessment_snapshot(session=session, persist=True)
    decision = select_next_item(session)
    if decision.action == NextAssessmentAction.SUFFICIENT:
        session.sufficiency_status = AssessmentSession.SufficiencyStatus.SUFFICIENT
        session.status = AssessmentSession.SessionStatus.COMPLETED
        session.completed_at = timezone.now()
    elif decision.action == NextAssessmentAction.HUMAN_REVIEW_REQUIRED:
        session.sufficiency_status = AssessmentSession.SufficiencyStatus.REVIEW_REQUIRED
        HumanReview.objects.get_or_create(
            journey=session.journey,
            review_type=HumanReview.ReviewType.ASSESSMENT_EVIDENCE,
            status=HumanReview.ReviewStatus.REQUIRED,
            defaults={"summary": decision.reason},
        )
    else:
        session.sufficiency_status = AssessmentSession.SufficiencyStatus.INSUFFICIENT
    session.save(update_fields=["sufficiency_status", "status", "completed_at", "updated_at"])
    record_audit_event(
        event_type="assessment.session_evaluated",
        actor_type="system",
        actor_reference=actor_reference,
        target_type="assessment_session",
        target_id=session.id,
        reason=decision.reason,
        details={
            "action": decision.action,
            "sufficiency_status": session.sufficiency_status,
            "calculation_version": assessment_version.calculation_version,
        },
    )
    return AssessmentSnapshot(
        **{
            **snapshot.__dict__,
            "completion": session.sufficiency_status,
            "human_review_required": (
                decision.action == NextAssessmentAction.HUMAN_REVIEW_REQUIRED
            ),
            "recommended_next_action": decision.action,
        }
    )
