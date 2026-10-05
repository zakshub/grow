from __future__ import annotations

import uuid
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q
from django.utils import timezone

from grow.common.models import AppendOnlyModel, TimeStampedModel, UUIDModel
from grow.journeys.models import ParticipantJourney


class AssessmentSession(UUIDModel, TimeStampedModel):
    class SessionStatus(models.TextChoices):
        UNKNOWN = "unknown", "Unknown"
        DRAFT = "draft", "Draft"
        IN_PROGRESS = "in_progress", "In progress"
        COMPLETED = "completed", "Completed"
        CANCELLED = "cancelled", "Cancelled"

    class SufficiencyStatus(models.TextChoices):
        UNKNOWN = "unknown", "Unknown"
        SUFFICIENT = "sufficient", "Sufficient"
        INSUFFICIENT = "insufficient", "Insufficient"
        REVIEW_REQUIRED = "review_required", "Review required"
        NOT_APPLICABLE = "not_applicable", "Not applicable"
        UNABLE_TO_ASSESS = "unable_to_assess", "Unable to assess"

    journey = models.ForeignKey(
        ParticipantJourney, on_delete=models.CASCADE, related_name="assessment_sessions"
    )
    definition_code = models.CharField(max_length=100, default="unknown")
    definition_version = models.CharField(max_length=100, default="unknown")
    status = models.CharField(
        max_length=20, choices=SessionStatus.choices, default=SessionStatus.UNKNOWN
    )
    sufficiency_status = models.CharField(
        max_length=30,
        choices=SufficiencyStatus.choices,
        default=SufficiencyStatus.UNKNOWN,
    )


class EvidenceSource(UUIDModel, AppendOnlyModel):
    class SourceType(models.TextChoices):
        UNKNOWN = "unknown", "Unknown"
        SELF_REPORT = "self_report", "Self report"
        BEHAVIOURAL_STORY = "behavioural_story", "Behavioural story"
        STRUCTURED_RESPONSE = "structured_response", "Structured response"
        PRACTICAL_TASK = "practical_task", "Practical task"
        REVIEWER_OBSERVATION = "reviewer_observation", "Reviewer observation"
        GUARDIAN_CONTEXT = "guardian_context", "Guardian context"
        FOLLOW_UP = "follow_up", "Follow up"

    source_type = models.CharField(
        max_length=30, choices=SourceType.choices, default=SourceType.UNKNOWN
    )
    reference_kind = models.CharField(max_length=100, default="unknown")
    reference_id = models.UUIDField(null=True, blank=True)
    provenance_version = models.CharField(max_length=100, default="foundation-v1")
    occurred_at = models.DateTimeField(default=timezone.now)
    details = models.JSONField(default=dict, blank=True)


class EvidenceItem(UUIDModel, AppendOnlyModel):
    class Category(models.TextChoices):
        UNKNOWN = "unknown", "Unknown"
        PERSONALITY = "personality", "Personality tendency"
        INTEREST = "interest", "Interest"
        ABILITY = "ability", "Current ability"
        POTENTIAL = "potential", "Potential and learning speed"
        VALUE = "value", "Work value"
        ENVIRONMENT = "environment", "Environment preference"
        CONSTRAINT = "constraint", "Constraint"
        BEHAVIOUR = "behaviour", "Practical behaviour"

    class ValueStatus(models.TextChoices):
        UNKNOWN = "unknown", "Unknown"
        KNOWN = "known", "Known"
        NOT_APPLICABLE = "not_applicable", "Not applicable"

    class ConfidenceBand(models.TextChoices):
        UNKNOWN = "unknown", "Unknown"
        LOW = "low", "Low"
        MODERATE = "moderate", "Moderate"
        HIGH = "high", "High"

    class Direction(models.TextChoices):
        UNKNOWN = "unknown", "Unknown"
        SUPPORTS = "supports", "Supports"
        CONFLICTS = "conflicts", "Conflicts"
        NEUTRAL = "neutral", "Neutral"

    class PrivacyClass(models.TextChoices):
        OPERATIONAL = "operational", "Operational"
        STRUCTURED_EVIDENCE = "structured_evidence", "Structured guidance evidence"
        SENSITIVE = "sensitive", "Sensitive"

    journey = models.ForeignKey(
        ParticipantJourney, on_delete=models.CASCADE, related_name="evidence_items"
    )
    assessment_session = models.ForeignKey(
        AssessmentSession,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="evidence_items",
    )
    source = models.ForeignKey(
        EvidenceSource, on_delete=models.PROTECT, related_name="evidence_items"
    )
    evidence_chain_id = models.UUIDField(default=uuid.uuid4, db_index=True)
    version = models.PositiveIntegerField(default=1)
    supersedes = models.ForeignKey(
        "self", null=True, blank=True, on_delete=models.PROTECT, related_name="superseded_by"
    )
    dimension_code = models.CharField(max_length=100)
    category = models.CharField(max_length=30, choices=Category.choices, default=Category.UNKNOWN)
    value_status = models.CharField(
        max_length=20, choices=ValueStatus.choices, default=ValueStatus.UNKNOWN
    )
    numeric_value = models.DecimalField(max_digits=8, decimal_places=4, null=True, blank=True)
    text_value = models.TextField(blank=True)
    direction = models.CharField(
        max_length=20, choices=Direction.choices, default=Direction.UNKNOWN
    )
    confidence_band = models.CharField(
        max_length=20, choices=ConfidenceBand.choices, default=ConfidenceBand.UNKNOWN
    )
    confidence_score = models.DecimalField(max_digits=5, decimal_places=4, null=True, blank=True)
    confidence_reason = models.TextField(blank=True)
    privacy_class = models.CharField(
        max_length=30,
        choices=PrivacyClass.choices,
        default=PrivacyClass.STRUCTURED_EVIDENCE,
    )
    observed_at = models.DateTimeField(default=timezone.now)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["evidence_chain_id", "version"], name="unique_evidence_chain_version"
            ),
            models.CheckConstraint(
                condition=Q(confidence_score__isnull=True)
                | (Q(confidence_score__gte=0) & Q(confidence_score__lte=1)),
                name="confidence_score_between_zero_and_one",
            ),
        ]

    def clean(self) -> None:
        if self.value_status == self.ValueStatus.UNKNOWN:
            if self.numeric_value is not None or self.text_value:
                raise ValidationError("Unknown evidence cannot contain a value")
        elif self.value_status == self.ValueStatus.KNOWN:
            if self.numeric_value is None and not self.text_value.strip():
                raise ValidationError("Known evidence requires an explicit value")
        elif self.value_status == self.ValueStatus.NOT_APPLICABLE:
            if self.numeric_value is not None or self.text_value:
                raise ValidationError("Not-applicable evidence cannot contain a value")

        if self.confidence_band == self.ConfidenceBand.UNKNOWN:
            if self.confidence_score is not None:
                raise ValidationError("Unknown confidence cannot contain a numeric score")
        if self.confidence_score is not None and not Decimal(
            "0"
        ) <= self.confidence_score <= Decimal("1"):
            raise ValidationError("Confidence score must be between zero and one")

        if self.supersedes:
            if self.supersedes.journey_id != self.journey_id:
                raise ValidationError("Evidence versions must belong to the same journey")
            if self.supersedes.evidence_chain_id != self.evidence_chain_id:
                raise ValidationError("Superseded evidence must use the same chain identifier")
            if self.version != self.supersedes.version + 1:
                raise ValidationError("Evidence version must increment by one")
        elif self.version != 1:
            raise ValidationError("A new evidence chain must begin at version one")


class Contradiction(UUIDModel, TimeStampedModel):
    class ResolutionStatus(models.TextChoices):
        UNKNOWN = "unknown", "Unknown"
        OPEN = "open", "Open"
        RESOLVED = "resolved", "Resolved"
        ACCEPTED_UNCERTAINTY = "accepted_uncertainty", "Accepted uncertainty"

    journey = models.ForeignKey(
        ParticipantJourney, on_delete=models.CASCADE, related_name="contradictions"
    )
    summary = models.TextField()
    resolution_status = models.CharField(
        max_length=30, choices=ResolutionStatus.choices, default=ResolutionStatus.UNKNOWN
    )
    resolution = models.TextField(blank=True)
    evidence_items: models.ManyToManyField[EvidenceItem, ContradictionEvidence] = (
        models.ManyToManyField(EvidenceItem, through="ContradictionEvidence")
    )


class ContradictionEvidence(UUIDModel, AppendOnlyModel):
    class Relation(models.TextChoices):
        UNKNOWN = "unknown", "Unknown"
        CLAIM = "claim", "Claim"
        COUNTEREVIDENCE = "counterevidence", "Counterevidence"
        CONTEXT = "context", "Context"

    contradiction = models.ForeignKey(Contradiction, on_delete=models.CASCADE)
    evidence_item = models.ForeignKey(EvidenceItem, on_delete=models.PROTECT)
    relation = models.CharField(max_length=30, choices=Relation.choices, default=Relation.UNKNOWN)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["contradiction", "evidence_item"],
                name="unique_evidence_per_contradiction",
            )
        ]
