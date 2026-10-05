from __future__ import annotations

import uuid
from typing import Any

from grow.audit.models import AuditEvent


def record_audit_event(
    *,
    event_type: str,
    actor_type: str,
    target_type: str,
    target_id: uuid.UUID,
    actor_reference: str = "",
    reason: str = "",
    correlation_id: uuid.UUID | None = None,
    details: dict[str, Any] | None = None,
) -> AuditEvent:
    return AuditEvent.objects.create(
        event_type=event_type,
        actor_type=actor_type,
        actor_reference=actor_reference,
        target_type=target_type,
        target_id=target_id,
        reason=reason,
        correlation_id=correlation_id,
        details=details or {},
    )
