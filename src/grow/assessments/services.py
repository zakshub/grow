from __future__ import annotations

import uuid

from django.core.exceptions import ValidationError
from django.db import transaction

from grow.assessments.models import Contradiction, ContradictionEvidence, EvidenceItem
from grow.audit.services import record_audit_event


@transaction.atomic
def record_contradiction(
    *,
    journey_id: uuid.UUID,
    evidence_ids: list[uuid.UUID],
    summary: str,
    actor_type: str,
    actor_reference: str = "",
) -> Contradiction:
    unique_ids = list(dict.fromkeys(evidence_ids))
    if len(unique_ids) < 2:
        raise ValidationError("A contradiction requires at least two evidence items")
    evidence = list(EvidenceItem.objects.filter(id__in=unique_ids))
    if len(evidence) != len(unique_ids):
        raise ValidationError("Every evidence item must exist")
    if any(item.journey_id != journey_id for item in evidence):
        raise ValidationError("Contradictory evidence must belong to the same journey")
    if not summary.strip():
        raise ValidationError("Contradiction summary is required")

    contradiction = Contradiction.objects.create(
        journey_id=journey_id,
        summary=summary,
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
        details={"evidence_ids": [str(item.id) for item in evidence]},
    )
    return contradiction
