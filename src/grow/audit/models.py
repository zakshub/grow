from __future__ import annotations

from django.db import models

from grow.common.models import AppendOnlyModel, UUIDModel


class AuditEvent(UUIDModel, AppendOnlyModel):
    occurred_at = models.DateTimeField(auto_now_add=True, db_index=True)
    event_type = models.CharField(max_length=100, db_index=True)
    actor_type = models.CharField(max_length=50)
    actor_reference = models.CharField(max_length=100, blank=True)
    target_type = models.CharField(max_length=100, db_index=True)
    target_id = models.UUIDField(db_index=True)
    reason = models.TextField(blank=True)
    correlation_id = models.UUIDField(null=True, blank=True, db_index=True)
    details = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["occurred_at", "id"]
