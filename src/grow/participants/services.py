from __future__ import annotations

from django.db import transaction

from grow.audit.services import record_audit_event
from grow.participants.models import ConsentRecord, MinorStatus, Participant


def classify_minor_status(
    age_years: int | None, *, approved_minor_age_threshold: int | None = None
) -> str:
    """Classify only when an approved threshold is explicitly supplied.

    No production legal threshold is encoded in Milestone 1.
    """
    if age_years is None or approved_minor_age_threshold is None:
        return MinorStatus.UNKNOWN
    if age_years < approved_minor_age_threshold:
        return MinorStatus.MINOR
    return MinorStatus.ADULT


@transaction.atomic
def record_consent(
    *,
    participant: Participant,
    consent_type: str,
    status: str,
    policy_version: str,
    actor_type: str,
    actor_reference: str = "",
    evidence_reference: str = "",
) -> ConsentRecord:
    record = ConsentRecord.objects.create(
        participant=participant,
        consent_type=consent_type,
        status=status,
        policy_version=policy_version,
        actor_type=actor_type,
        actor_reference=actor_reference,
        evidence_reference=evidence_reference,
    )
    record_audit_event(
        event_type="consent.recorded",
        actor_type=actor_type,
        actor_reference=actor_reference,
        target_type="participant",
        target_id=participant.id,
        reason=f"Consent status recorded as {status}",
        details={
            "consent_record_id": str(record.id),
            "consent_type": consent_type,
            "status": status,
            "policy_version": policy_version,
        },
    )
    return record
