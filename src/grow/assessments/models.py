from __future__ import annotations

import uuid
from decimal import Decimal
from typing import Any

from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q
from django.utils import timezone

from grow.common.models import AppendOnlyModel, TimeStampedModel, UUIDModel
from grow.journeys.models import ParticipantJourney
from grow.participants.models import EducationStage


class AssessmentLifecycle(models.TextChoices):
    DRAFT = "draft", "Draft"
    PILOT = "pilot", "Pilot only"
    ACTIVE = "active", "Active"
    RETIRED = "retired", "Retired"


class DimensionCategory(models.TextChoices):
    COGNITIVE_FUNCTIONAL = "cognitive_functional", "Cognitive / functional"
    PERSONALITY_WORK_STYLE = "personality_work_style", "Personality / work style"
    COMMUNICATION_SOCIAL = "communication_social", "Communication / social"
    CREATIVITY = "creativity", "Creativity"
    VOCATIONAL_INTEREST = "vocational_interest", "Vocational interest"
    WORK_VALUE = "work_value", "Work value"
    WORK_ENVIRONMENT = "work_environment", "Work environment"


class AssessmentDefinition(UUIDModel, TimeStampedModel):
    code = models.SlugField(max_length=100, unique=True)
    title = models.CharField(max_length=200)
    purpose = models.TextField()
    validity_notice = models.TextField(
        default="Pilot engineering content; no psychometric or clinical validity claim."
    )

    def save(self, *args: Any, **kwargs: Any) -> None:
        if (
            not self._state.adding
            and self.versions.exclude(lifecycle=AssessmentLifecycle.DRAFT).exists()
        ):
            persisted = AssessmentDefinition.objects.get(pk=self.pk)
            immutable = ("code", "title", "purpose", "validity_notice")
            if any(getattr(self, field) != getattr(persisted, field) for field in immutable):
                raise ValueError("A definition with a published version is immutable")
        super().save(*args, **kwargs)

    def delete(self, *args: Any, **kwargs: Any) -> tuple[int, dict[str, int]]:
        if self.versions.exclude(lifecycle=AssessmentLifecycle.DRAFT).exists():
            raise ValueError("A definition with a published version cannot be deleted")
        return super().delete(*args, **kwargs)


class AssessmentVersion(UUIDModel, TimeStampedModel):
    definition = models.ForeignKey(
        AssessmentDefinition, on_delete=models.PROTECT, related_name="versions"
    )
    version = models.PositiveIntegerField()
    lifecycle = models.CharField(
        max_length=20, choices=AssessmentLifecycle.choices, default=AssessmentLifecycle.DRAFT
    )
    selection_policy_version = models.CharField(max_length=100, default="deterministic-pilot-v1")
    calculation_version = models.CharField(max_length=100, default="deterministic-pilot-v1")
    maximum_items = models.PositiveSmallIntegerField(default=20)
    limitations = models.TextField(
        default="Synthetic pilot content; not validated for participant guidance."
    )
    published_at = models.DateTimeField(null=True, blank=True)
    retired_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["definition", "version"], name="unique_assessment_definition_version"
            ),
            models.CheckConstraint(
                condition=Q(maximum_items__gte=1), name="assessment_maximum_items_positive"
            ),
        ]

    def save(self, *args: Any, **kwargs: Any) -> None:
        if not self._state.adding:
            persisted = AssessmentVersion.objects.get(pk=self.pk)
            if persisted.lifecycle != AssessmentLifecycle.DRAFT:
                immutable = (
                    "definition_id",
                    "version",
                    "selection_policy_version",
                    "calculation_version",
                    "maximum_items",
                    "limitations",
                )
                if any(getattr(self, field) != getattr(persisted, field) for field in immutable):
                    raise ValueError("Published assessment version content is immutable")
        super().save(*args, **kwargs)


def _require_draft(version: AssessmentVersion) -> None:
    lifecycle = AssessmentVersion.objects.values_list("lifecycle", flat=True).get(pk=version.pk)
    if lifecycle != AssessmentLifecycle.DRAFT:
        raise ValueError("Published assessment content is immutable; create a new version")


class AssessmentSection(UUIDModel, TimeStampedModel):
    assessment_version = models.ForeignKey(
        AssessmentVersion, on_delete=models.PROTECT, related_name="sections"
    )
    code = models.SlugField(max_length=100)
    order = models.PositiveSmallIntegerField()
    title = models.CharField(max_length=200)
    purpose = models.TextField(blank=True)

    class Meta:
        ordering = ["order", "code"]
        constraints = [
            models.UniqueConstraint(
                fields=["assessment_version", "code"], name="unique_section_code_per_version"
            ),
            models.UniqueConstraint(
                fields=["assessment_version", "order"], name="unique_section_order_per_version"
            ),
        ]

    def save(self, *args: Any, **kwargs: Any) -> None:
        _require_draft(self.assessment_version)
        super().save(*args, **kwargs)

    def delete(self, *args: Any, **kwargs: Any) -> tuple[int, dict[str, int]]:
        _require_draft(self.assessment_version)
        return super().delete(*args, **kwargs)


class AssessmentDimension(UUIDModel, AppendOnlyModel):
    code = models.SlugField(max_length=100, unique=True)
    category = models.CharField(max_length=40, choices=DimensionCategory.choices)
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    pilot_only = models.BooleanField(default=True)


class AssessmentDimensionRequirement(UUIDModel, TimeStampedModel):
    assessment_version = models.ForeignKey(
        AssessmentVersion, on_delete=models.PROTECT, related_name="dimension_requirements"
    )
    dimension = models.ForeignKey(
        AssessmentDimension, on_delete=models.PROTECT, related_name="version_requirements"
    )
    required = models.BooleanField(default=True)
    priority = models.PositiveSmallIntegerField(default=100)
    minimum_independent_sources = models.PositiveSmallIntegerField(default=2)
    minimum_source_types = models.PositiveSmallIntegerField(default=2)

    class Meta:
        ordering = ["priority", "dimension__code"]
        constraints = [
            models.UniqueConstraint(
                fields=["assessment_version", "dimension"],
                name="unique_dimension_requirement_per_version",
            ),
            models.CheckConstraint(
                condition=Q(minimum_independent_sources__gte=1),
                name="minimum_independent_sources_positive",
            ),
            models.CheckConstraint(
                condition=Q(minimum_source_types__gte=1),
                name="minimum_source_types_positive",
            ),
        ]

    def save(self, *args: Any, **kwargs: Any) -> None:
        _require_draft(self.assessment_version)
        super().save(*args, **kwargs)

    def delete(self, *args: Any, **kwargs: Any) -> tuple[int, dict[str, int]]:
        _require_draft(self.assessment_version)
        return super().delete(*args, **kwargs)


class AssessmentItem(UUIDModel, TimeStampedModel):
    class ItemType(models.TextChoices):
        LIKERT = "likert", "Likert"
        BINARY = "binary", "Binary"
        SINGLE_CHOICE = "single_choice", "Single choice"
        MULTI_CHOICE = "multi_choice", "Multiple choice"
        RANKING = "ranking", "Ranking"
        NUMERIC = "numeric", "Numeric"
        SHORT_TEXT = "short_text", "Short text"
        LONG_TEXT = "long_text", "Long text"
        SCENARIO_CHOICE = "scenario_choice", "Scenario choice"

    class Purpose(models.TextChoices):
        CORE = "core", "Core evidence"
        CLARIFICATION = "clarification", "Contradiction clarification"
        OPEN_DISCOVERY = "open_discovery", "Open discovery"

    assessment_version = models.ForeignKey(
        AssessmentVersion, on_delete=models.PROTECT, related_name="items"
    )
    section = models.ForeignKey(AssessmentSection, on_delete=models.PROTECT, related_name="items")
    dimension = models.ForeignKey(
        AssessmentDimension, on_delete=models.PROTECT, related_name="items"
    )
    code = models.SlugField(max_length=100)
    item_type = models.CharField(max_length=30, choices=ItemType.choices)
    purpose = models.CharField(max_length=30, choices=Purpose.choices, default=Purpose.CORE)
    order = models.PositiveSmallIntegerField(default=0)
    response_schema = models.JSONField(default=dict, blank=True)
    interpretation_rules = models.JSONField(default=dict, blank=True)
    evidence_source_type = models.CharField(max_length=40, default="structured_question")
    pilot_only = models.BooleanField(default=True)

    class Meta:
        ordering = ["section__order", "order", "code"]
        constraints = [
            models.UniqueConstraint(
                fields=["assessment_version", "code"], name="unique_item_code_per_version"
            )
        ]

    def clean(self) -> None:
        if self.section_id and self.section.assessment_version_id != self.assessment_version_id:
            raise ValidationError("Item section must belong to the same assessment version")

    def save(self, *args: Any, **kwargs: Any) -> None:
        _require_draft(self.assessment_version)
        self.full_clean()
        super().save(*args, **kwargs)

    def delete(self, *args: Any, **kwargs: Any) -> tuple[int, dict[str, int]]:
        _require_draft(self.assessment_version)
        return super().delete(*args, **kwargs)


class AssessmentItemVariant(UUIDModel, TimeStampedModel):
    class ContentStatus(models.TextChoices):
        DRAFT = "draft", "Draft"
        SYNTHETIC_PILOT = "synthetic_pilot", "Synthetic pilot"
        HUMAN_REVIEWED_PILOT = "human_reviewed_pilot", "Human-reviewed pilot"

    class Audience(models.TextChoices):
        GENERAL = "general", "General"
        GRADE_8_10 = "grade_8_10", "Grade 8-10"
        INTERMEDIATE = "intermediate", "Intermediate"
        UNIVERSITY = "university", "University"
        GRADUATE = "graduate", "Graduate"
        ADULT_CAREER_SWITCHER = "adult_career_switcher", "Adult career switcher"

    item = models.ForeignKey(AssessmentItem, on_delete=models.PROTECT, related_name="variants")
    variant_version = models.PositiveIntegerField(default=1)
    language = models.CharField(max_length=10)
    locale = models.CharField(max_length=20, default="pk")
    audience = models.CharField(max_length=30, choices=Audience.choices, default=Audience.GENERAL)
    education_stage = models.CharField(
        max_length=20, choices=EducationStage.choices, default=EducationStage.UNKNOWN
    )
    prompt = models.TextField()
    helper_text = models.TextField(blank=True)
    answer_labels = models.JSONField(default=dict, blank=True)
    examples = models.JSONField(default=list, blank=True)
    content_status = models.CharField(
        max_length=30,
        choices=ContentStatus.choices,
        default=ContentStatus.SYNTHETIC_PILOT,
    )
    provenance = models.CharField(max_length=200, default="synthetic-pilot-authoring")

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=[
                    "item",
                    "variant_version",
                    "language",
                    "locale",
                    "audience",
                    "education_stage",
                ],
                name="unique_item_content_variant",
            )
        ]

    def save(self, *args: Any, **kwargs: Any) -> None:
        _require_draft(self.item.assessment_version)
        super().save(*args, **kwargs)

    def delete(self, *args: Any, **kwargs: Any) -> tuple[int, dict[str, int]]:
        _require_draft(self.item.assessment_version)
        return super().delete(*args, **kwargs)


class AssessmentSession(UUIDModel, TimeStampedModel):
    class SessionStatus(models.TextChoices):
        UNKNOWN = "unknown", "Unknown"
        DRAFT = "draft", "Draft"
        IN_PROGRESS = "in_progress", "In progress"
        COMPLETED = "completed", "Completed"
        STOPPED_EARLY = "stopped_early", "Stopped early"
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
    assessment_version = models.ForeignKey(
        AssessmentVersion,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="sessions",
    )
    definition_code = models.CharField(max_length=100, default="unknown")
    definition_version = models.CharField(max_length=100, default="unknown")
    audience = models.CharField(
        max_length=30,
        choices=AssessmentItemVariant.Audience.choices,
        default=AssessmentItemVariant.Audience.GENERAL,
    )
    language = models.CharField(max_length=10, default="ur")
    locale = models.CharField(max_length=20, default="pk")
    maximum_items = models.PositiveSmallIntegerField(null=True, blank=True)
    status = models.CharField(
        max_length=20, choices=SessionStatus.choices, default=SessionStatus.UNKNOWN
    )
    sufficiency_status = models.CharField(
        max_length=30,
        choices=SufficiencyStatus.choices,
        default=SufficiencyStatus.UNKNOWN,
    )
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    def clean(self) -> None:
        if self.assessment_version_id:
            assessment_version = self.assessment_version
            assert assessment_version is not None
            if self.definition_code not in {"unknown", assessment_version.definition.code}:
                raise ValidationError("Definition code must match the pinned assessment version")
            if self.definition_version not in {"unknown", str(assessment_version.version)}:
                raise ValidationError("Definition version must match the pinned assessment version")


class AssessmentItemPresentation(UUIDModel, AppendOnlyModel):
    session = models.ForeignKey(
        AssessmentSession, on_delete=models.CASCADE, related_name="presentations"
    )
    item = models.ForeignKey(AssessmentItem, on_delete=models.PROTECT)
    variant = models.ForeignKey(AssessmentItemVariant, on_delete=models.PROTECT)
    sequence = models.PositiveSmallIntegerField()
    selection_status = models.CharField(max_length=40)
    selection_reason = models.TextField()
    selection_policy_version = models.CharField(max_length=100)
    presented_at = models.DateTimeField(default=timezone.now)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["session", "item"], name="unique_presented_item_per_session"
            ),
            models.UniqueConstraint(
                fields=["session", "sequence"], name="unique_presentation_sequence_per_session"
            ),
        ]

    def clean(self) -> None:
        if self.item.assessment_version_id != self.session.assessment_version_id:
            raise ValidationError("Presented item must belong to the session's pinned version")
        if self.variant.item_id != self.item_id:
            raise ValidationError("Presented variant must belong to the presented item")
        if self.sequence < 1:
            raise ValidationError("Presentation sequence must be positive")

    def save(self, *args: Any, **kwargs: Any) -> None:
        self.full_clean()
        super().save(*args, **kwargs)


class AssessmentResponse(UUIDModel, AppendOnlyModel):
    presentation = models.OneToOneField(
        AssessmentItemPresentation, on_delete=models.PROTECT, related_name="response"
    )
    structured_value = models.JSONField(null=True, blank=True)
    text_value = models.TextField(blank=True)
    skipped = models.BooleanField(default=False)
    completion_quality = models.CharField(max_length=20, default="unknown")
    responded_at = models.DateTimeField(default=timezone.now)

    def clean(self) -> None:
        has_structured = self.structured_value is not None
        has_text = bool(self.text_value.strip())
        if self.skipped and (has_structured or has_text):
            raise ValidationError("A skipped response cannot contain a value")
        if not self.skipped and not (has_structured or has_text):
            raise ValidationError("A response requires a structured or text value")


class AssessmentObservation(UUIDModel, AppendOnlyModel):
    session = models.ForeignKey(
        AssessmentSession, on_delete=models.CASCADE, related_name="observations"
    )
    response = models.ForeignKey(
        AssessmentResponse,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="observations",
    )
    dimension = models.ForeignKey(AssessmentDimension, on_delete=models.PROTECT)
    observer_type = models.CharField(max_length=40)
    observer_reference = models.CharField(max_length=100, blank=True)
    structured_value = models.JSONField(default=dict)
    notes = models.TextField(blank=True)
    observed_at = models.DateTimeField(default=timezone.now)

    def clean(self) -> None:
        if self.response_id:
            response = self.response
            assert response is not None
            if response.presentation.session_id != self.session_id:
                raise ValidationError("Observed response must belong to the same session")

    def save(self, *args: Any, **kwargs: Any) -> None:
        self.full_clean()
        super().save(*args, **kwargs)


class EvidenceSource(UUIDModel, AppendOnlyModel):
    class SourceType(models.TextChoices):
        UNKNOWN = "unknown", "Unknown"
        SELF_REPORT = "self_report", "Self report"
        STRUCTURED_QUESTION = "structured_question", "Structured question"
        OPEN_RESPONSE = "open_response", "Open response"
        PRACTICAL_TASK = "practical_task", "Practical task"
        HUMAN_OBSERVATION = "human_observation", "Human observation"
        BEHAVIOURAL_SIGNAL = "behavioural_signal", "Behavioural signal"
        HISTORICAL_EXAMPLE = "historical_example", "Historical example"
        FOLLOW_UP = "follow_up", "Follow up"
        REVIEWER_JUDGMENT = "reviewer_judgment", "Reviewer judgment"
        BEHAVIOURAL_STORY = "behavioural_story", "Behavioural story (legacy)"
        STRUCTURED_RESPONSE = "structured_response", "Structured response (legacy)"
        REVIEWER_OBSERVATION = "reviewer_observation", "Reviewer observation (legacy)"
        GUARDIAN_CONTEXT = "guardian_context", "Guardian context (legacy)"

    source_type = models.CharField(
        max_length=40, choices=SourceType.choices, default=SourceType.UNKNOWN
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

    class ReviewStatus(models.TextChoices):
        UNREVIEWED = "unreviewed", "Unreviewed"
        REVIEWED = "reviewed", "Reviewed"
        REJECTED = "rejected", "Rejected"
        NEEDS_CLARIFICATION = "needs_clarification", "Needs clarification"

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
    dimension = models.ForeignKey(
        AssessmentDimension,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
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
    structured_value = models.JSONField(null=True, blank=True)
    normalized_interpretation = models.JSONField(null=True, blank=True)
    direction = models.CharField(
        max_length=20, choices=Direction.choices, default=Direction.UNKNOWN
    )
    confidence_band = models.CharField(
        max_length=20, choices=ConfidenceBand.choices, default=ConfidenceBand.UNKNOWN
    )
    confidence_score = models.DecimalField(max_digits=5, decimal_places=4, null=True, blank=True)
    confidence_reason = models.TextField(blank=True)
    review_status = models.CharField(
        max_length=30, choices=ReviewStatus.choices, default=ReviewStatus.UNREVIEWED
    )
    supporting_context = models.JSONField(default=dict, blank=True)
    interpretation_method = models.CharField(max_length=100, default="none")
    interpretation_version = models.CharField(max_length=100, default="none")
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
        if self.dimension_id:
            dimension = self.dimension
            assert dimension is not None
            if self.dimension_code != dimension.code:
                raise ValidationError("Dimension code must match the linked dimension")
        has_value = (
            self.numeric_value is not None
            or bool(self.text_value)
            or self.structured_value is not None
        )
        if self.value_status == self.ValueStatus.UNKNOWN and has_value:
            raise ValidationError("Unknown evidence cannot contain a value")
        if self.value_status == self.ValueStatus.KNOWN and not has_value:
            raise ValidationError("Known evidence requires an explicit value")
        if self.value_status == self.ValueStatus.NOT_APPLICABLE and has_value:
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


class DimensionEvidence(UUIDModel, AppendOnlyModel):
    session = models.ForeignKey(
        AssessmentSession, on_delete=models.CASCADE, related_name="dimension_evidence"
    )
    dimension = models.ForeignKey(
        AssessmentDimension, on_delete=models.PROTECT, related_name="dimension_evidence"
    )
    evidence_item = models.OneToOneField(
        EvidenceItem, on_delete=models.PROTECT, related_name="dimension_evidence_link"
    )
    independent_source_key = models.CharField(max_length=200)
    eligible_for_aggregation = models.BooleanField(default=True)
    eligibility_reason = models.TextField(blank=True)

    def clean(self) -> None:
        if self.evidence_item.assessment_session_id != self.session_id:
            raise ValidationError("Dimension evidence must belong to the same session")
        if self.evidence_item.journey_id != self.session.journey_id:
            raise ValidationError("Dimension evidence must belong to the session journey")
        if self.evidence_item.dimension_id != self.dimension_id:
            raise ValidationError("Dimension evidence must use the evidence item's dimension")
        if not self.independent_source_key.strip():
            raise ValidationError("Independent source key is required")

    def save(self, *args: Any, **kwargs: Any) -> None:
        self.full_clean()
        super().save(*args, **kwargs)


class Contradiction(UUIDModel, TimeStampedModel):
    class ResolutionStatus(models.TextChoices):
        UNKNOWN = "unknown", "Unknown"
        OPEN = "open", "Open"
        RESOLVED = "resolved", "Resolved"
        ACCEPTED_UNCERTAINTY = "accepted_uncertainty", "Accepted uncertainty"

    class Severity(models.TextChoices):
        LOW = "low", "Low"
        MODERATE = "moderate", "Moderate"
        HIGH = "high", "High"

    journey = models.ForeignKey(
        ParticipantJourney, on_delete=models.CASCADE, related_name="contradictions"
    )
    dimension = models.ForeignKey(
        AssessmentDimension,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="contradictions",
    )
    summary = models.TextField()
    reason = models.TextField(blank=True)
    severity = models.CharField(max_length=20, choices=Severity.choices, default=Severity.MODERATE)
    resolution_status = models.CharField(
        max_length=30, choices=ResolutionStatus.choices, default=ResolutionStatus.UNKNOWN
    )
    resolution = models.TextField(blank=True)
    reviewer_reference = models.CharField(max_length=100, blank=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
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


class DimensionResult(UUIDModel, AppendOnlyModel):
    class Sufficiency(models.TextChoices):
        UNKNOWN = "unknown", "Unknown"
        INSUFFICIENT = "insufficient", "Insufficient"
        TENTATIVE = "tentative", "Tentative"
        SUPPORTED = "supported", "Supported"
        CONTRADICTORY = "contradictory", "Contradictory"

    session = models.ForeignKey(
        AssessmentSession, on_delete=models.CASCADE, related_name="dimension_results"
    )
    dimension = models.ForeignKey(
        AssessmentDimension, on_delete=models.PROTECT, related_name="results"
    )
    result_chain_id = models.UUIDField(default=uuid.uuid4, db_index=True)
    version = models.PositiveIntegerField(default=1)
    supersedes = models.ForeignKey(
        "self", null=True, blank=True, on_delete=models.PROTECT, related_name="superseded_by"
    )
    sufficiency = models.CharField(
        max_length=30, choices=Sufficiency.choices, default=Sufficiency.UNKNOWN
    )
    confidence_band = models.CharField(
        max_length=20,
        choices=EvidenceItem.ConfidenceBand.choices,
        default=EvidenceItem.ConfidenceBand.UNKNOWN,
    )
    confidence_score = models.DecimalField(max_digits=5, decimal_places=4, null=True, blank=True)
    supporting_count = models.PositiveSmallIntegerField(default=0)
    conflicting_count = models.PositiveSmallIntegerField(default=0)
    independent_source_count = models.PositiveSmallIntegerField(default=0)
    source_type_count = models.PositiveSmallIntegerField(default=0)
    unresolved_contradiction_count = models.PositiveSmallIntegerField(default=0)
    calculation_version = models.CharField(max_length=100)
    calculation_inputs = models.JSONField(default=dict)
    reasons = models.JSONField(default=list)
    next_action = models.TextField(blank=True)
    calculated_at = models.DateTimeField(default=timezone.now)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["result_chain_id", "version"], name="unique_dimension_result_version"
            ),
            models.CheckConstraint(
                condition=Q(confidence_score__isnull=True)
                | (Q(confidence_score__gte=0) & Q(confidence_score__lte=1)),
                name="dimension_confidence_score_between_zero_and_one",
            ),
        ]

    def clean(self) -> None:
        if self.confidence_band == EvidenceItem.ConfidenceBand.UNKNOWN:
            if self.confidence_score is not None:
                raise ValidationError("Unknown confidence cannot contain a numeric score")
        if self.supersedes:
            if self.supersedes.session_id != self.session_id:
                raise ValidationError("Result versions must belong to the same session")
            if self.supersedes.dimension_id != self.dimension_id:
                raise ValidationError("Result versions must describe the same dimension")
            if self.supersedes.result_chain_id != self.result_chain_id:
                raise ValidationError("Superseded result must use the same chain identifier")
            if self.version != self.supersedes.version + 1:
                raise ValidationError("Result version must increment by one")
        elif self.version != 1:
            raise ValidationError("A new result chain must begin at version one")
