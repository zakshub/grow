from __future__ import annotations

from django.db import transaction

from grow.access.models import AccessDecision
from grow.audit.services import record_audit_event


@transaction.atomic
def decide_access(
    *,
    pending_decision: AccessDecision,
    status: str,
    final_category: str,
    reviewer_reference: str,
    reason: str,
) -> AccessDecision:
    decision = AccessDecision(
        participant=pending_decision.participant,
        journey=pending_decision.journey,
        decision_chain_id=pending_decision.decision_chain_id,
        version=pending_decision.version + 1,
        supersedes=pending_decision,
        candidate_category=pending_decision.candidate_category,
        status=status,
        final_category=final_category,
        reviewer_reference=reviewer_reference,
        reason=reason,
    )
    decision.full_clean()
    decision.save()
    record_audit_event(
        event_type="access.decision_recorded",
        actor_type="access_reviewer",
        actor_reference=reviewer_reference,
        target_type="access_decision",
        target_id=decision.id,
        reason=reason,
        details={
            "previous_decision_id": str(pending_decision.id),
            "candidate_category": pending_decision.candidate_category,
            "status": status,
            "final_category": final_category,
            "version": decision.version,
        },
    )
    return decision
