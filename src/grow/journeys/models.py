from __future__ import annotations

from django.db import models
from django.db.models import Q

from grow.common.models import AppendOnlyModel, TimeStampedModel, UUIDModel
from grow.participants.models import LifeStageTrack, Participant


class JourneyState(models.TextChoices):
    NEW = "new", "New"
    CONSENT_PENDING = "consent_pending", "Consent pending"
    PROFILE_INCOMPLETE = "profile_incomplete", "Profile incomplete"
    DISCOVERY_IN_PROGRESS = "discovery_in_progress", "Discovery in progress"
    ASSESSMENT_IN_PROGRESS = "assessment_in_progress", "Assessment in progress"
    EXPERIMENT_PENDING = "experiment_pending", "Experiment pending"
    EXPERIMENT_SUBMITTED = "experiment_submitted", "Experiment submitted"
    HUMAN_REVIEW_REQUIRED = "human_review_required", "Human review required"
    RECOMMENDATION_READY = "recommendation_ready", "Recommendation-ready gate"
    ROADMAP_ACTIVE = "roadmap_active", "Roadmap active"
    FOLLOW_UP_DUE = "follow_up_due", "Follow-up due"
    COMPLETED = "completed", "Completed"
    PAUSED = "paused", "Paused"
    OPTED_OUT = "opted_out", "Opted out"


class ParticipantJourney(UUIDModel, TimeStampedModel):
    participant = models.ForeignKey(Participant, on_delete=models.CASCADE, related_name="journeys")
    track = models.CharField(
        max_length=30, choices=LifeStageTrack.choices, default=LifeStageTrack.UNKNOWN
    )
    current_state = models.CharField(
        max_length=40, choices=JourneyState.choices, default=JourneyState.NEW, db_index=True
    )
    resume_state = models.CharField(
        max_length=40, choices=JourneyState.choices, blank=True, default=""
    )
    state_version = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["participant"],
                condition=Q(is_active=True),
                name="one_active_journey_per_participant",
            )
        ]


class StateTransition(UUIDModel, AppendOnlyModel):
    journey = models.ForeignKey(
        ParticipantJourney, on_delete=models.CASCADE, related_name="transitions"
    )
    from_state = models.CharField(max_length=40, choices=JourneyState.choices)
    to_state = models.CharField(max_length=40, choices=JourneyState.choices)
    command = models.CharField(max_length=100)
    reason = models.TextField()
    actor_type = models.CharField(max_length=30)
    actor_reference = models.CharField(max_length=100, blank=True)
    policy_version = models.CharField(max_length=100, default="foundation-v1")
    correlation_id = models.UUIDField(null=True, blank=True)
    state_version_from = models.PositiveIntegerField()
    state_version_to = models.PositiveIntegerField()
    occurred_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["occurred_at", "id"]
