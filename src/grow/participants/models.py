from __future__ import annotations

from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q
from django.utils import timezone

from grow.common.models import AppendOnlyModel, TimeStampedModel, UUIDModel


class KnowledgeState(models.TextChoices):
    UNKNOWN = "unknown", "Unknown"
    KNOWN = "known", "Known"


class ParticipantStatus(models.TextChoices):
    UNKNOWN = "unknown", "Unknown"
    ACTIVE = "active", "Active"
    PAUSED = "paused", "Paused"
    CLOSED = "closed", "Closed"


class LifeStageTrack(models.TextChoices):
    UNKNOWN = "unknown", "Unknown"
    SCHOOL = "school", "School discovery"
    COLLEGE = "college", "College direction"
    UNIVERSITY = "university", "University and graduation direction"
    CAREER_RESET = "career_reset", "Career reset"


class MinorStatus(models.TextChoices):
    UNKNOWN = "unknown", "Unknown"
    MINOR = "minor", "Minor"
    ADULT = "adult", "Adult"


class GuardianRequirement(models.TextChoices):
    UNKNOWN = "unknown", "Unknown"
    REQUIRED = "required", "Guardian handling required"
    NOT_REQUIRED = "not_required", "Guardian handling not required"


class EducationStage(models.TextChoices):
    UNKNOWN = "unknown", "Unknown"
    GRADE_8 = "grade_8", "Grade 8"
    GRADE_10 = "grade_10", "Grade 10"
    INTERMEDIATE = "intermediate", "Intermediate or equivalent"
    UNIVERSITY = "university", "University"
    GRADUATE = "graduate", "Graduate"
    OTHER = "other", "Other"


class Participant(UUIDModel, TimeStampedModel):
    status = models.CharField(
        max_length=20, choices=ParticipantStatus.choices, default=ParticipantStatus.UNKNOWN
    )
    life_stage_track = models.CharField(
        max_length=30, choices=LifeStageTrack.choices, default=LifeStageTrack.UNKNOWN
    )
    preferred_language = models.CharField(max_length=20, default="unknown")
    deleted_at = models.DateTimeField(null=True, blank=True)

    def soft_delete(self) -> None:
        self.deleted_at = timezone.now()
        self.status = ParticipantStatus.CLOSED
        self.save(update_fields=["deleted_at", "status", "updated_at"])

    @property
    def is_deleted(self) -> bool:
        return self.deleted_at is not None


class ParticipantIdentifier(UUIDModel, TimeStampedModel):
    class IdentifierType(models.TextChoices):
        UNKNOWN = "unknown", "Unknown"
        WHATSAPP = "whatsapp", "WhatsApp"
        EMAIL = "email", "Email"
        INTERNAL_ALIAS = "internal_alias", "Internal alias"

    participant = models.ForeignKey(
        Participant, on_delete=models.CASCADE, related_name="identifiers"
    )
    identifier_type = models.CharField(
        max_length=30, choices=IdentifierType.choices, default=IdentifierType.UNKNOWN
    )
    lookup_digest = models.CharField(max_length=64, blank=True, db_index=True)
    ciphertext = models.TextField(blank=True)
    key_version = models.CharField(max_length=50, blank=True)
    is_primary = models.BooleanField(default=False)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["identifier_type", "lookup_digest"],
                condition=~Q(lookup_digest=""),
                name="unique_nonempty_identifier_digest",
            )
        ]

    def clean(self) -> None:
        if not self.lookup_digest and not self.ciphertext:
            raise ValidationError("Identifier requires a lookup digest or encrypted value")
        if self.ciphertext and not self.key_version:
            raise ValidationError("Encrypted identifiers require a key version")


class ParticipantProfile(UUIDModel, TimeStampedModel):
    participant = models.OneToOneField(
        Participant, on_delete=models.CASCADE, related_name="profile"
    )
    age_status = models.CharField(
        max_length=10, choices=KnowledgeState.choices, default=KnowledgeState.UNKNOWN
    )
    age_years = models.PositiveSmallIntegerField(null=True, blank=True)
    minor_status = models.CharField(
        max_length=10, choices=MinorStatus.choices, default=MinorStatus.UNKNOWN
    )
    guardian_requirement = models.CharField(
        max_length=20,
        choices=GuardianRequirement.choices,
        default=GuardianRequirement.UNKNOWN,
    )
    education_stage = models.CharField(
        max_length=20, choices=EducationStage.choices, default=EducationStage.UNKNOWN
    )
    city = models.CharField(max_length=100, blank=True)
    current_status = models.CharField(max_length=100, blank=True)

    def clean(self) -> None:
        if self.age_status == KnowledgeState.UNKNOWN and self.age_years is not None:
            raise ValidationError("Unknown age must not have a numeric value")
        if self.age_status == KnowledgeState.KNOWN and self.age_years is None:
            raise ValidationError("Known age requires a numeric value")
        if self.age_years is not None and self.age_years > 120:
            raise ValidationError("Age must be a plausible value")


class ConsentRecord(UUIDModel, AppendOnlyModel):
    class ConsentType(models.TextChoices):
        UNKNOWN = "unknown", "Unknown"
        PARTICIPATION = "participation", "Participation"
        DATA_PROCESSING = "data_processing", "Data processing"
        RESEARCH = "research", "Research"

    class ConsentStatus(models.TextChoices):
        UNKNOWN = "unknown", "Unknown"
        PENDING = "pending", "Pending"
        GRANTED = "granted", "Granted"
        WITHDRAWN = "withdrawn", "Withdrawn"
        EXPIRED = "expired", "Expired"

    participant = models.ForeignKey(
        Participant, on_delete=models.CASCADE, related_name="consent_records"
    )
    consent_type = models.CharField(
        max_length=30, choices=ConsentType.choices, default=ConsentType.UNKNOWN
    )
    status = models.CharField(
        max_length=20, choices=ConsentStatus.choices, default=ConsentStatus.UNKNOWN
    )
    policy_version = models.CharField(max_length=100)
    actor_type = models.CharField(max_length=30, default="unknown")
    actor_reference = models.CharField(max_length=100, blank=True)
    recorded_at = models.DateTimeField(default=timezone.now, db_index=True)
    evidence_reference = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ["recorded_at", "id"]


class GuardianRelationship(UUIDModel, TimeStampedModel):
    class RelationshipType(models.TextChoices):
        UNKNOWN = "unknown", "Unknown"
        PARENT = "parent", "Parent"
        GUARDIAN = "guardian", "Guardian"

    class HandlingStatus(models.TextChoices):
        UNKNOWN = "unknown", "Unknown"
        REQUIRED = "required", "Required"
        ACKNOWLEDGED = "acknowledged", "Acknowledged for development workflow"
        NOT_REQUIRED = "not_required", "Not required"

    participant = models.ForeignKey(
        Participant, on_delete=models.CASCADE, related_name="guardian_relationships"
    )
    guardian_reference_digest = models.CharField(max_length=64, blank=True)
    relationship_type = models.CharField(
        max_length=20, choices=RelationshipType.choices, default=RelationshipType.UNKNOWN
    )
    handling_status = models.CharField(
        max_length=20, choices=HandlingStatus.choices, default=HandlingStatus.UNKNOWN
    )
    policy_version = models.CharField(max_length=100, default="unknown")


class ReferralSource(UUIDModel, TimeStampedModel):
    class SourceType(models.TextChoices):
        UNKNOWN = "unknown", "Unknown"
        SELF = "self", "Self"
        PARTICIPANT = "participant", "Participant referral"
        TEACHER = "teacher", "Teacher"
        INSTITUTION = "institution", "Institution"
        COMMUNITY = "community", "Community"
        SOCIAL = "social", "Social media"

    participant = models.OneToOneField(
        Participant, on_delete=models.CASCADE, related_name="referral_source"
    )
    source_type = models.CharField(
        max_length=30, choices=SourceType.choices, default=SourceType.UNKNOWN
    )
    source_code = models.CharField(max_length=100, blank=True)
    referring_participant = models.ForeignKey(
        Participant,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="referrals_made",
    )
