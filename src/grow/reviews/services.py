from __future__ import annotations

import uuid
from typing import Any

from django.db import transaction
from django.utils import timezone

from grow.audit.services import record_audit_event
from grow.reviews.models import HumanOverride, HumanReview


@transaction.atomic
def decide_human_review(
    *,
    review: HumanReview,
    status: str,
    reviewer_reference: str,
    decision: str,
) -> HumanReview:
    if status not in {
        HumanReview.ReviewStatus.APPROVED,
        HumanReview.ReviewStatus.REJECTED,
        HumanReview.ReviewStatus.MORE_INFORMATION,
    }:
        raise ValueError("Human review decision must be a terminal or information-request state")
    if not reviewer_reference.strip() or not decision.strip():
        raise ValueError("Reviewer and decision reason are required")
    review.status = status
    review.reviewer_reference = reviewer_reference
    review.decision = decision
    review.decided_at = timezone.now()
    review.save(
        update_fields=["status", "reviewer_reference", "decision", "decided_at", "updated_at"]
    )
    record_audit_event(
        event_type="human.review_decided",
        actor_type="reviewer",
        actor_reference=reviewer_reference,
        target_type="human_review",
        target_id=review.id,
        reason=decision,
        details={"status": status, "journey_id": str(review.journey_id)},
    )
    return review


@transaction.atomic
def record_human_override(
    *,
    review: HumanReview,
    target_type: str,
    target_id: uuid.UUID,
    original_result: dict[str, Any],
    new_result: dict[str, Any],
    reviewer_reference: str,
    reason: str,
) -> HumanOverride:
    override = HumanOverride(
        review=review,
        target_type=target_type,
        target_id=target_id,
        original_result=original_result,
        new_result=new_result,
        reviewer_reference=reviewer_reference,
        reason=reason,
    )
    override.full_clean()
    override.save()
    record_audit_event(
        event_type="human.override_recorded",
        actor_type="reviewer",
        actor_reference=reviewer_reference,
        target_type=target_type,
        target_id=target_id,
        reason=reason,
        details={
            "override_id": str(override.id),
            "review_id": str(review.id),
            "original_result": original_result,
            "new_result": new_result,
        },
    )
    return override
