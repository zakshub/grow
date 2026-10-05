from __future__ import annotations

from typing import Any

from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q
from django.utils import timezone

from grow.assessments.models import AssessmentDimension
from grow.common.models import AppendOnlyModel, TimeStampedModel, UUIDModel


class Lifecycle(models.TextChoices):
    DRAFT = "draft", "Draft"
    PILOT = "pilot", "Pilot"
    ACTIVE = "active", "Active"
    RETIRED = "retired", "Retired"


class ReviewStatus(models.TextChoices):
    DRAFT = "draft", "Draft"
    IN_REVIEW = "in_review", "In review"
    APPROVED = "approved", "Approved"
    PUBLISHED = "published", "Published"
    STALE = "stale", "Stale"
    RETIRED = "retired", "Retired"


class Freshness(models.TextChoices):
    CURRENT = "current", "Current"
    STALE = "stale", "Stale"
    RETIRED = "retired", "Retired"
    UNKNOWN = "unknown", "Unknown"


class OrdinalRelevance(models.TextChoices):
    LOW = "low", "Low"
    MODERATE = "moderate", "Moderate"
    HIGH = "high", "High"
    VARIABLE = "variable", "Variable"
    UNKNOWN = "unknown", "Unknown"


class Confidence(models.TextChoices):
    HIGH = "high", "High"
    MODERATE = "moderate", "Moderate"
    LOW = "low", "Low"
    UNKNOWN = "unknown", "Unknown"


class DataClassification(models.TextChoices):
    SYNTHETIC = "synthetic", "Synthetic"
    REFERENCE_ONLY = "reference_only", "Reference only"
    REVIEWED_REFERENCE = "reviewed_reference", "Reviewed reference"


class CareerTaxonomy(UUIDModel, TimeStampedModel):
    code = models.SlugField(max_length=100, unique=True)
    title = models.CharField(max_length=200)
    scope = models.TextField()
    geography = models.CharField(max_length=100, default="Pakistan")

    def save(self, *args: Any, **kwargs: Any) -> None:
        if (
            not self._state.adding
            and self.versions.filter(
                review_status__in=[
                    ReviewStatus.PUBLISHED,
                    ReviewStatus.STALE,
                    ReviewStatus.RETIRED,
                ]
            ).exists()
        ):
            current = CareerTaxonomy.objects.get(pk=self.pk)
            if any(
                getattr(current, field) != getattr(self, field)
                for field in ("code", "title", "scope", "geography")
            ):
                raise ValueError("A taxonomy with a published version is immutable")
        super().save(*args, **kwargs)


class CareerTaxonomyVersion(UUIDModel, TimeStampedModel):
    taxonomy = models.ForeignKey(CareerTaxonomy, on_delete=models.PROTECT, related_name="versions")
    version = models.PositiveIntegerField()
    lifecycle = models.CharField(max_length=20, choices=Lifecycle.choices, default=Lifecycle.DRAFT)
    review_status = models.CharField(
        max_length=20, choices=ReviewStatus.choices, default=ReviewStatus.DRAFT
    )
    provenance = models.TextField()
    limitations = models.TextField()
    data_markers = models.JSONField(default=list)
    published_at = models.DateTimeField(null=True, blank=True)
    retired_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["taxonomy", "version"], name="unique_career_taxonomy_version"
            )
        ]

    def save(self, *args: Any, **kwargs: Any) -> None:
        if not self._state.adding:
            current = CareerTaxonomyVersion.objects.get(pk=self.pk)
            if current.review_status in {
                ReviewStatus.PUBLISHED,
                ReviewStatus.STALE,
                ReviewStatus.RETIRED,
            }:
                immutable = ("taxonomy_id", "version", "provenance", "limitations", "data_markers")
                if any(getattr(current, field) != getattr(self, field) for field in immutable):
                    raise ValueError("Published taxonomy version content is immutable")
        super().save(*args, **kwargs)


def _require_taxonomy_draft(version: CareerTaxonomyVersion) -> None:
    status = CareerTaxonomyVersion.objects.values_list("review_status", flat=True).get(
        pk=version.pk
    )
    if status not in {ReviewStatus.DRAFT, ReviewStatus.IN_REVIEW}:
        raise ValueError(
            "Approved or published taxonomy content is immutable; create a new version"
        )


class TaxonomyContent(UUIDModel, TimeStampedModel):
    taxonomy_version = models.ForeignKey(CareerTaxonomyVersion, on_delete=models.PROTECT)

    class Meta:
        abstract = True

    def save(self, *args: Any, **kwargs: Any) -> None:
        _require_taxonomy_draft(self.taxonomy_version)
        self.full_clean()
        super().save(*args, **kwargs)

    def delete(self, *args: Any, **kwargs: Any) -> tuple[int, dict[str, int]]:
        _require_taxonomy_draft(self.taxonomy_version)
        return super().delete(*args, **kwargs)


class CareerCluster(TaxonomyContent):
    code = models.SlugField(max_length=100)
    name_en = models.CharField(max_length=200)
    name_ur = models.CharField(max_length=200, blank=True)
    description = models.TextField(blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["taxonomy_version", "code"], name="unique_cluster_code_per_taxonomy"
            )
        ]


class CareerFamily(TaxonomyContent):
    cluster = models.ForeignKey(CareerCluster, on_delete=models.PROTECT, related_name="families")
    parent = models.ForeignKey(
        "self", null=True, blank=True, on_delete=models.PROTECT, related_name="children"
    )
    code = models.SlugField(max_length=100)
    name_en = models.CharField(max_length=200)
    name_ur = models.CharField(max_length=200, blank=True)
    description = models.TextField(blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["taxonomy_version", "code"], name="unique_family_code_per_taxonomy"
            )
        ]

    def clean(self) -> None:
        if self.cluster_id and self.cluster.taxonomy_version_id != self.taxonomy_version_id:
            raise ValidationError("Family cluster must belong to the same taxonomy version")
        if self.parent_id:
            parent = self.parent
            assert parent is not None
            if parent.taxonomy_version_id != self.taxonomy_version_id:
                raise ValidationError("Parent family must belong to the same taxonomy version")


class CareerProfile(UUIDModel, TimeStampedModel):
    code = models.SlugField(max_length=100, unique=True)

    def save(self, *args: Any, **kwargs: Any) -> None:
        if (
            not self._state.adding
            and self.versions.filter(
                review_status__in=[
                    ReviewStatus.PUBLISHED,
                    ReviewStatus.STALE,
                    ReviewStatus.RETIRED,
                ]
            ).exists()
        ):
            current = CareerProfile.objects.get(pk=self.pk)
            if current.code != self.code:
                raise ValueError("A career stable code cannot change after publication")
        super().save(*args, **kwargs)


class CareerProfileVersion(UUIDModel, TimeStampedModel):
    profile = models.ForeignKey(CareerProfile, on_delete=models.PROTECT, related_name="versions")
    taxonomy_version = models.ForeignKey(
        CareerTaxonomyVersion, on_delete=models.PROTECT, related_name="career_versions"
    )
    family = models.ForeignKey(CareerFamily, on_delete=models.PROTECT, related_name="careers")
    version = models.PositiveIntegerField()
    lifecycle = models.CharField(max_length=20, choices=Lifecycle.choices, default=Lifecycle.DRAFT)
    review_status = models.CharField(
        max_length=20, choices=ReviewStatus.choices, default=ReviewStatus.DRAFT
    )
    title_en = models.CharField(max_length=200)
    title_ur = models.CharField(max_length=200, blank=True)
    pakistan_title = models.CharField(max_length=200, blank=True)
    granularity = models.CharField(max_length=50, default="career")
    summary = models.TextField()
    typical_work = models.TextField()
    regulation_notes = models.TextField(blank=True)
    limitations = models.TextField()
    data_classification = models.CharField(
        max_length=30,
        choices=DataClassification.choices,
        default=DataClassification.REFERENCE_ONLY,
    )
    participant_recommendation_ready = models.BooleanField(default=False)
    published_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["profile", "version"], name="unique_career_profile_version"
            ),
            models.UniqueConstraint(
                fields=["taxonomy_version", "profile"], name="unique_profile_per_taxonomy_version"
            ),
        ]

    def clean(self) -> None:
        if self.family_id and self.family.taxonomy_version_id != self.taxonomy_version_id:
            raise ValidationError("Career family must belong to the same taxonomy version")
        if (
            self.participant_recommendation_ready
            and self.data_classification != DataClassification.REVIEWED_REFERENCE
        ):
            raise ValidationError("Synthetic/reference-only careers cannot be recommendation ready")

    def save(self, *args: Any, **kwargs: Any) -> None:
        if not self._state.adding:
            current = CareerProfileVersion.objects.get(pk=self.pk)
            if current.review_status in {
                ReviewStatus.PUBLISHED,
                ReviewStatus.STALE,
                ReviewStatus.RETIRED,
            }:
                mutable = {"lifecycle", "review_status", "published_at", "updated_at"}
                changed = {
                    field.name
                    for field in self._meta.fields
                    if field.name not in {"id", "created_at"}
                    and getattr(current, field.attname) != getattr(self, field.attname)
                }
                if changed - mutable:
                    raise ValueError("Published career profile content is immutable")
        self.full_clean()
        super().save(*args, **kwargs)


def _require_profile_draft(version: CareerProfileVersion) -> None:
    status = CareerProfileVersion.objects.values_list("review_status", flat=True).get(pk=version.pk)
    if status not in {ReviewStatus.DRAFT, ReviewStatus.IN_REVIEW}:
        raise ValueError("Approved or published career content is immutable; create a new version")


class ProfileContent(UUIDModel, TimeStampedModel):
    profile_version = models.ForeignKey(CareerProfileVersion, on_delete=models.PROTECT)

    class Meta:
        abstract = True

    def save(self, *args: Any, **kwargs: Any) -> None:
        _require_profile_draft(self.profile_version)
        self.full_clean()
        super().save(*args, **kwargs)

    def delete(self, *args: Any, **kwargs: Any) -> tuple[int, dict[str, int]]:
        _require_profile_draft(self.profile_version)
        return super().delete(*args, **kwargs)


class CareerAlias(ProfileContent):
    profile_version = models.ForeignKey(
        CareerProfileVersion, on_delete=models.PROTECT, related_name="aliases"
    )

    class AliasType(models.TextChoices):
        ALTERNATE = "alternate", "Alternate title"
        ENTRY = "entry", "Entry title"
        LOCAL = "local", "Local/Pakistan title"

    name = models.CharField(max_length=200)
    language = models.CharField(max_length=10, default="en")
    alias_type = models.CharField(max_length=20, choices=AliasType.choices)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["profile_version", "name", "language"], name="unique_career_alias"
            )
        ]


class CareerRelationship(TaxonomyContent):
    class RelationshipType(models.TextChoices):
        PARENT_CHILD = "parent_child", "Parent/child"
        RELATED = "related", "Related"
        SPECIALISATION = "specialisation", "Specialisation"

    source = models.ForeignKey(
        CareerProfileVersion, on_delete=models.PROTECT, related_name="outgoing_relationships"
    )
    target = models.ForeignKey(
        CareerProfileVersion, on_delete=models.PROTECT, related_name="incoming_relationships"
    )
    relationship_type = models.CharField(max_length=30, choices=RelationshipType.choices)
    notes = models.TextField(blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["taxonomy_version", "source", "target", "relationship_type"],
                name="unique_career_relationship",
            ),
            models.CheckConstraint(
                condition=~Q(source=models.F("target")), name="career_relation_not_self"
            ),
        ]

    def clean(self) -> None:
        if self.source_id and self.source.taxonomy_version_id != self.taxonomy_version_id:
            raise ValidationError("Relationship source must use the same taxonomy version")
        if self.target_id and self.target.taxonomy_version_id != self.taxonomy_version_id:
            raise ValidationError("Relationship target must use the same taxonomy version")


class ResearchSource(UUIDModel, TimeStampedModel):
    class SourceType(models.TextChoices):
        GOVERNMENT = "government", "Government"
        LABOUR_MARKET = "labour_market", "Labour market"
        UNIVERSITY = "university", "University"
        INDUSTRY_REPORT = "industry_report", "Industry report"
        JOB_BOARD = "job_board", "Job board"
        PROFESSIONAL_BODY = "professional_body", "Professional body"
        EDUCATION_PROVIDER = "education_provider", "Education provider"
        ACADEMIC = "academic", "Academic"
        PRIMARY_RESEARCH = "primary_research", "Primary research"
        OTHER = "other", "Other"

    source_type = models.CharField(max_length=30, choices=SourceType.choices)
    title = models.CharField(max_length=300)
    publisher = models.CharField(max_length=200)
    url = models.URLField(blank=True)
    reference = models.CharField(max_length=300, blank=True)
    publication_date = models.DateField(null=True, blank=True)
    accessed_date = models.DateField()
    geography = models.CharField(max_length=200, default="Unknown")
    methodology_notes = models.TextField(blank=True)
    limitations = models.TextField()
    quality_status = models.CharField(
        max_length=20, choices=Confidence.choices, default=Confidence.UNKNOWN
    )
    review_status = models.CharField(
        max_length=20, choices=ReviewStatus.choices, default=ReviewStatus.DRAFT
    )
    freshness = models.CharField(
        max_length=20, choices=Freshness.choices, default=Freshness.UNKNOWN
    )
    expires_at = models.DateField(null=True, blank=True)
    licence_notes = models.TextField(blank=True)
    supersedes = models.ForeignKey(
        "self", null=True, blank=True, on_delete=models.PROTECT, related_name="superseded_by"
    )

    def save(self, *args: Any, **kwargs: Any) -> None:
        if not self._state.adding:
            current = ResearchSource.objects.get(pk=self.pk)
            if current.review_status in {
                ReviewStatus.PUBLISHED,
                ReviewStatus.STALE,
                ReviewStatus.RETIRED,
            }:
                mutable = {"review_status", "freshness", "updated_at"}
                changed = {
                    field.name
                    for field in self._meta.fields
                    if field.name not in {"id", "created_at"}
                    and getattr(current, field.attname) != getattr(self, field.attname)
                }
                if changed - mutable:
                    raise ValueError("Published source content is immutable; create a successor")
        self.full_clean()
        super().save(*args, **kwargs)


class CareerDimensionRelationship(ProfileContent):
    profile_version = models.ForeignKey(
        CareerProfileVersion, on_delete=models.PROTECT, related_name="dimension_relationships"
    )

    class Direction(models.TextChoices):
        SUPPORTS = "supports", "Commonly relevant"
        CONFLICTS = "conflicts", "Potential tension"
        CONTEXTUAL = "contextual", "Context dependent"
        VARIABLE = "variable", "Variable"
        UNKNOWN = "unknown", "Unknown"

    dimension = models.ForeignKey(
        AssessmentDimension, on_delete=models.PROTECT, related_name="career_relationships"
    )
    importance = models.CharField(max_length=20, choices=OrdinalRelevance.choices)
    direction = models.CharField(max_length=20, choices=Direction.choices)
    minimum_relevance = models.CharField(max_length=20, choices=OrdinalRelevance.choices)
    typical_relevance = models.CharField(max_length=20, choices=OrdinalRelevance.choices)
    confidence = models.CharField(max_length=20, choices=Confidence.choices)
    source = models.ForeignKey(ResearchSource, on_delete=models.PROTECT)
    limitations = models.TextField()
    relationship_version = models.PositiveIntegerField(default=1)
    status = models.CharField(
        max_length=20, choices=ReviewStatus.choices, default=ReviewStatus.DRAFT
    )
    country = models.CharField(max_length=100, default="Pakistan")
    industry = models.CharField(max_length=100, blank=True)
    seniority = models.CharField(max_length=100, blank=True)
    employment_model = models.CharField(max_length=100, blank=True)
    specialisation = models.CharField(max_length=100, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=[
                    "profile_version",
                    "dimension",
                    "relationship_version",
                    "country",
                    "industry",
                    "seniority",
                    "employment_model",
                    "specialisation",
                ],
                name="unique_career_dimension_context",
            )
        ]


class CareerEnvironmentObservation(ProfileContent):
    profile_version = models.ForeignKey(
        CareerProfileVersion, on_delete=models.PROTECT, related_name="environment_observations"
    )

    class Prevalence(models.TextChoices):
        COMMON = "common", "Common"
        VARIABLE = "variable", "Variable"
        RARE = "rare", "Rare"
        UNKNOWN = "unknown", "Unknown"

    dimension = models.ForeignKey(AssessmentDimension, on_delete=models.PROTECT)
    prevalence = models.CharField(max_length=20, choices=Prevalence.choices)
    context = models.CharField(max_length=200, blank=True)
    source = models.ForeignKey(ResearchSource, on_delete=models.PROTECT)
    confidence = models.CharField(max_length=20, choices=Confidence.choices)
    limitations = models.TextField()
    status = models.CharField(
        max_length=20, choices=ReviewStatus.choices, default=ReviewStatus.DRAFT
    )


class CareerSkill(UUIDModel, TimeStampedModel):
    class Category(models.TextChoices):
        TECHNICAL = "technical", "Technical"
        DOMAIN = "domain", "Domain"
        COMMUNICATION = "communication", "Communication"
        ANALYTICAL = "analytical", "Analytical"
        CREATIVE = "creative", "Creative"
        DIGITAL = "digital", "Digital"
        MANAGEMENT = "management", "Management"
        TOOL_PLATFORM = "tool_platform", "Tool/platform"
        CERTIFICATION = "certification", "Certification"

    code = models.SlugField(max_length=100, unique=True)
    name = models.CharField(max_length=200)
    category = models.CharField(max_length=30, choices=Category.choices)


class CareerSkillRequirement(ProfileContent):
    profile_version = models.ForeignKey(
        CareerProfileVersion, on_delete=models.PROTECT, related_name="skill_requirements"
    )

    class RequirementLevel(models.TextChoices):
        CORE = "core", "Core"
        COMMON = "common", "Common"
        SPECIALISATION = "specialisation", "Specialisation"
        OPTIONAL = "optional", "Optional"
        UNKNOWN = "unknown", "Unknown"

    skill = models.ForeignKey(CareerSkill, on_delete=models.PROTECT, related_name="requirements")
    requirement = models.CharField(max_length=20, choices=RequirementLevel.choices)
    source = models.ForeignKey(ResearchSource, on_delete=models.PROTECT)
    limitations = models.TextField()
    freshness = models.CharField(
        max_length=20, choices=Freshness.choices, default=Freshness.UNKNOWN
    )
    status = models.CharField(
        max_length=20, choices=ReviewStatus.choices, default=ReviewStatus.DRAFT
    )
    requirement_version = models.PositiveIntegerField(default=1)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["profile_version", "skill", "requirement_version"],
                name="unique_career_skill_version",
            )
        ]


class CareerPathway(ProfileContent):
    profile_version = models.ForeignKey(
        CareerProfileVersion, on_delete=models.PROTECT, related_name="pathways"
    )

    class RouteType(models.TextChoices):
        DEGREE = "degree", "Degree"
        DIPLOMA = "diploma", "Diploma"
        CERTIFICATION = "certification", "Certification"
        SKILLS_FIRST = "skills_first", "Skills-first"
        APPRENTICESHIP = "apprenticeship", "Apprenticeship"
        SELF_TAUGHT = "self_taught", "Self-taught"
        PORTFOLIO = "portfolio", "Portfolio"
        INTERNSHIP = "internship", "Internship"
        ENTRY_ROLE = "entry_role", "Entry-level role"
        CAREER_SWITCH = "career_switch", "Career switch"

    route_type = models.CharField(max_length=30, choices=RouteType.choices)
    title = models.CharField(max_length=200)
    country = models.CharField(max_length=100, default="Pakistan")
    region = models.CharField(max_length=100, blank=True)
    education_requirement = models.TextField()
    skills = models.ManyToManyField(CareerSkill, blank=True, related_name="pathways")
    duration = models.CharField(max_length=100, default="Unknown")
    cost_category = models.CharField(
        max_length=20, choices=OrdinalRelevance.choices, default=OrdinalRelevance.UNKNOWN
    )
    prerequisites = models.TextField()
    typical_next_step = models.TextField()
    source = models.ForeignKey(ResearchSource, on_delete=models.PROTECT)
    limitations = models.TextField()
    source_date = models.DateField()
    reviewed_at = models.DateField(null=True, blank=True)
    valid_from = models.DateField(null=True, blank=True)
    expires_at = models.DateField(null=True, blank=True)
    freshness = models.CharField(
        max_length=20, choices=Freshness.choices, default=Freshness.UNKNOWN
    )
    status = models.CharField(
        max_length=20, choices=ReviewStatus.choices, default=ReviewStatus.DRAFT
    )
    pathway_version = models.PositiveIntegerField(default=1)
    supersedes = models.ForeignKey(
        "self", null=True, blank=True, on_delete=models.PROTECT, related_name="superseded_by"
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["profile_version", "route_type", "title", "pathway_version"],
                name="unique_career_pathway_version",
            )
        ]


class MarketObservation(UUIDModel, AppendOnlyModel):
    class ObservationType(models.TextChoices):
        DEMAND = "demand", "Demand"
        SALARY_RANGE = "salary_range", "Salary range"
        ENTRY_DIFFICULTY = "entry_difficulty", "Entry difficulty"
        REMOTE_AVAILABILITY = "remote_availability", "Remote availability"
        FREELANCE_RELEVANCE = "freelance_relevance", "Freelance relevance"
        AUTOMATION_EXPOSURE = "automation_exposure", "Automation exposure"
        INTERNATIONAL_MOBILITY = "international_mobility", "International mobility"
        HIRING_CONCENTRATION = "hiring_concentration", "Hiring concentration"
        TRAINING_AVAILABILITY = "training_availability", "Training availability"

    class ValueState(models.TextChoices):
        KNOWN = "known", "Known"
        UNKNOWN = "unknown", "Unknown"
        NOT_APPLICABLE = "not_applicable", "Not applicable"

    profile_version = models.ForeignKey(
        CareerProfileVersion, on_delete=models.PROTECT, related_name="market_observations"
    )
    observation_type = models.CharField(max_length=40, choices=ObservationType.choices)
    country = models.CharField(max_length=100, default="Pakistan")
    region = models.CharField(max_length=100, blank=True)
    city = models.CharField(max_length=100, blank=True)
    remote = models.BooleanField(null=True, blank=True)
    freelance = models.BooleanField(null=True, blank=True)
    employment_type = models.CharField(max_length=100, blank=True)
    industry = models.CharField(max_length=100, blank=True)
    seniority = models.CharField(max_length=100, blank=True)
    value_state = models.CharField(
        max_length=20, choices=ValueState.choices, default=ValueState.UNKNOWN
    )
    value = models.JSONField(null=True, blank=True)
    unit = models.CharField(max_length=50, blank=True)
    source = models.ForeignKey(ResearchSource, on_delete=models.PROTECT)
    source_date = models.DateField()
    confidence = models.CharField(
        max_length=20, choices=Confidence.choices, default=Confidence.UNKNOWN
    )
    limitations = models.TextField()
    valid_from = models.DateField(null=True, blank=True)
    expires_at = models.DateField(null=True, blank=True)
    freshness = models.CharField(
        max_length=20, choices=Freshness.choices, default=Freshness.UNKNOWN
    )
    review_status = models.CharField(
        max_length=20, choices=ReviewStatus.choices, default=ReviewStatus.DRAFT
    )
    reviewed_at = models.DateField(null=True, blank=True)
    observation_version = models.PositiveIntegerField(default=1)
    supersedes = models.ForeignKey(
        "self", null=True, blank=True, on_delete=models.PROTECT, related_name="superseded_by"
    )
    recorded_at = models.DateTimeField(default=timezone.now)

    def clean(self) -> None:
        if self.value_state == self.ValueState.UNKNOWN and (self.value is not None or self.unit):
            raise ValidationError("UNKNOWN market observations cannot contain a value or unit")
        if self.value_state == self.ValueState.KNOWN and self.value is None:
            raise ValidationError("Known market observations require a structured value")
        if (
            self.observation_type == self.ObservationType.SALARY_RANGE
            and self.value_state == self.ValueState.KNOWN
        ):
            if not isinstance(self.value, dict) or not {
                "minimum",
                "maximum",
                "currency",
                "period",
            }.issubset(self.value):
                raise ValidationError(
                    "Salary evidence requires minimum, maximum, currency, and period"
                )
            if self.value["minimum"] > self.value["maximum"]:
                raise ValidationError("Salary minimum cannot exceed maximum")

    def save(self, *args: Any, **kwargs: Any) -> None:
        _require_profile_draft(self.profile_version)
        self.full_clean()
        super().save(*args, **kwargs)


class CareerReviewDecision(UUIDModel, AppendOnlyModel):
    target_type = models.CharField(max_length=100)
    target_id = models.UUIDField(db_index=True)
    from_status = models.CharField(max_length=20, choices=ReviewStatus.choices)
    to_status = models.CharField(max_length=20, choices=ReviewStatus.choices)
    reviewer_reference = models.CharField(max_length=100)
    reason = models.TextField()
    source_evidence = models.JSONField(default=list)
    changes = models.JSONField(default=dict)
    decision = models.CharField(max_length=30)
    decided_at = models.DateTimeField(default=timezone.now)


class CareerImportBatch(UUIDModel, TimeStampedModel):
    class Status(models.TextChoices):
        STAGED = "staged", "Staged"
        VALIDATED = "validated", "Validated"
        DIFF_READY = "diff_ready", "Diff ready"
        APPROVED = "approved", "Approved"
        PUBLISHED = "published", "Published"
        REJECTED = "rejected", "Rejected"

    taxonomy = models.ForeignKey(CareerTaxonomy, on_delete=models.PROTECT, related_name="imports")
    base_version = models.ForeignKey(
        CareerTaxonomyVersion,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="imports",
    )
    schema_version = models.CharField(max_length=30)
    payload = models.JSONField()
    payload_hash = models.CharField(max_length=64, unique=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.STAGED)
    validation_errors = models.JSONField(default=list)
    approved_by = models.CharField(max_length=100, blank=True)
    approved_at = models.DateTimeField(null=True, blank=True)
    published_version = models.ForeignKey(
        CareerTaxonomyVersion,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="published_imports",
    )


class CareerImportDiff(UUIDModel, AppendOnlyModel):
    class ChangeType(models.TextChoices):
        NEW = "new", "New"
        CHANGED = "changed", "Changed"
        REMOVED = "removed", "Removed"

    batch = models.ForeignKey(CareerImportBatch, on_delete=models.PROTECT, related_name="diffs")
    entity_type = models.CharField(max_length=50)
    entity_key = models.CharField(max_length=150)
    change_type = models.CharField(max_length=20, choices=ChangeType.choices)
    before = models.JSONField(null=True, blank=True)
    after = models.JSONField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["batch", "entity_type", "entity_key"], name="unique_import_diff_entity"
            )
        ]
