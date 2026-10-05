from __future__ import annotations

from django.core.exceptions import ValidationError
from django.db import models

from grow.common.models import AppendOnlyModel, TimeStampedModel, UUIDModel
from grow.journeys.models import ParticipantJourney


class HumanReview(UUIDModel, TimeStampedModel):
    class ReviewType(models.TextChoices):
        UNKNOWN = "unknown", "Unknown"
        MINOR_HANDLING = "minor_handling", "Minor handling"
        EVIDENCE_CONTRADICTION = "evidence_contradiction", "Evidence contradiction"
        ASSESSMENT_EVIDENCE = "assessment_evidence", "Assessment evidence"
        ACCESS = "access", "Access"
        FOUNDATION = "foundation", "Foundation workflow"

    class ReviewStatus(models.TextChoices):
        UNKNOWN = "unknown", "Unknown"
        REQUIRED = "required", "Required"
        IN_PROGRESS = "in_progress", "In progress"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"
        MORE_INFORMATION = "more_information", "More information required"

    journey = models.ForeignKey(
        ParticipantJourney, on_delete=models.CASCADE, related_name="human_reviews"
    )
    review_type = models.CharField(
        max_length=30, choices=ReviewType.choices, default=ReviewType.UNKNOWN
    )
    status = models.CharField(
        max_length=30, choices=ReviewStatus.choices, default=ReviewStatus.UNKNOWN
    )
    reviewer_reference = models.CharField(max_length=100, blank=True)
    summary = models.TextField(blank=True)
    decision = models.TextField(blank=True)
    decided_at = models.DateTimeField(null=True, blank=True)


class HumanOverride(UUIDModel, AppendOnlyModel):
    review = models.ForeignKey(HumanReview, on_delete=models.PROTECT, related_name="overrides")
    target_type = models.CharField(max_length=100)
    target_id = models.UUIDField()
    original_result = models.JSONField()
    new_result = models.JSONField()
    reviewer_reference = models.CharField(max_length=100)
    reason = models.TextField()
    occurred_at = models.DateTimeField(auto_now_add=True)

    def clean(self) -> None:
        if not self.reviewer_reference.strip():
            raise ValidationError("Reviewer reference is required")
        if not self.reason.strip():
            raise ValidationError("Override reason is required")
        if self.original_result == self.new_result:
            raise ValidationError("An override must preserve a changed result")
