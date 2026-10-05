from __future__ import annotations

import uuid

from django.core.exceptions import ValidationError
from django.db import models

from grow.common.models import AppendOnlyModel, UUIDModel
from grow.journeys.models import ParticipantJourney
from grow.participants.models import Participant


class AccessCategory(models.TextChoices):
    UNKNOWN = "unknown", "Unknown"
    STANDARD = "standard", "Standard"
    REDUCED = "reduced", "Reduced"
    FREE = "free", "Free"


class AccessDecision(UUIDModel, AppendOnlyModel):
    class DecisionStatus(models.TextChoices):
        UNKNOWN = "unknown", "Unknown"
        PENDING = "pending", "Pending human review"
        APPROVED = "approved", "Approved"
        DECLINED = "declined", "Declined"

    participant = models.ForeignKey(
        Participant, on_delete=models.CASCADE, related_name="access_decisions"
    )
    journey = models.ForeignKey(
        ParticipantJourney, on_delete=models.CASCADE, related_name="access_decisions"
    )
    decision_chain_id = models.UUIDField(default=uuid.uuid4, db_index=True)
    version = models.PositiveIntegerField(default=1)
    supersedes = models.ForeignKey(
        "self", null=True, blank=True, on_delete=models.PROTECT, related_name="superseded_by"
    )
    candidate_category = models.CharField(
        max_length=20, choices=AccessCategory.choices, default=AccessCategory.UNKNOWN
    )
    status = models.CharField(
        max_length=20, choices=DecisionStatus.choices, default=DecisionStatus.UNKNOWN
    )
    final_category = models.CharField(
        max_length=20, choices=AccessCategory.choices, default=AccessCategory.UNKNOWN
    )
    reviewer_reference = models.CharField(max_length=100, blank=True)
    reason = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["decision_chain_id", "version"], name="unique_access_decision_version"
            )
        ]

    def clean(self) -> None:
        decided = self.status in {self.DecisionStatus.APPROVED, self.DecisionStatus.DECLINED}
        if decided and not self.reviewer_reference.strip():
            raise ValidationError("A decided access record requires a reviewer")
        if decided and not self.reason.strip():
            raise ValidationError("A decided access record requires a reason")
        if self.status == self.DecisionStatus.APPROVED:
            if self.final_category == AccessCategory.UNKNOWN:
                raise ValidationError("Approved access requires an explicit final category")
        elif self.final_category != AccessCategory.UNKNOWN:
            raise ValidationError("Only approved access may set a final category")
        if self.supersedes:
            if self.supersedes.participant_id != self.participant_id:
                raise ValidationError("Access decision versions require the same participant")
            if self.supersedes.journey_id != self.journey_id:
                raise ValidationError("Access decision versions require the same journey")
            if self.supersedes.decision_chain_id != self.decision_chain_id:
                raise ValidationError("Access decision versions require the same chain")
            if self.version != self.supersedes.version + 1:
                raise ValidationError("Access decision version must increment by one")
        elif self.version != 1:
            raise ValidationError("A new access decision chain must begin at version one")
