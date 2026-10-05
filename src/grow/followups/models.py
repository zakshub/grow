from django.core.exceptions import ValidationError
from django.db import models

from grow.common.models import TimeStampedModel, UUIDModel
from grow.journeys.models import ParticipantJourney


class FollowUp(UUIDModel, TimeStampedModel):
    class FollowUpKind(models.TextChoices):
        UNKNOWN = "unknown", "Unknown"
        SEVEN_DAY = "seven_day", "Seven day"
        THIRTY_DAY = "thirty_day", "Thirty day"
        CUSTOM = "custom", "Custom"

    class FollowUpStatus(models.TextChoices):
        UNKNOWN = "unknown", "Unknown"
        PLANNED = "planned", "Planned"
        DUE = "due", "Due"
        COMPLETED = "completed", "Completed"
        CANCELLED = "cancelled", "Cancelled"

    class OutcomeStatus(models.TextChoices):
        UNKNOWN = "unknown", "Unknown"
        ACTION_ATTEMPTED = "action_attempted", "Action attempted"
        ACTION_COMPLETED = "action_completed", "Action completed"
        NOT_COMPLETED = "not_completed", "Not completed"
        UNABLE_TO_ASSESS = "unable_to_assess", "Unable to assess"

    journey = models.ForeignKey(
        ParticipantJourney, on_delete=models.CASCADE, related_name="follow_ups"
    )
    kind = models.CharField(
        max_length=20, choices=FollowUpKind.choices, default=FollowUpKind.UNKNOWN
    )
    status = models.CharField(
        max_length=20, choices=FollowUpStatus.choices, default=FollowUpStatus.UNKNOWN
    )
    due_at = models.DateTimeField(null=True, blank=True)
    outcome_status = models.CharField(
        max_length=30, choices=OutcomeStatus.choices, default=OutcomeStatus.UNKNOWN
    )
    notes = models.TextField(blank=True)

    def clean(self) -> None:
        if self.status in {self.FollowUpStatus.PLANNED, self.FollowUpStatus.DUE}:
            if self.due_at is None:
                raise ValidationError("Planned or due follow-up requires a due date")
