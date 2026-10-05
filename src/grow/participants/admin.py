from django.contrib import admin

from grow.participants.models import (
    ConsentRecord,
    GuardianRelationship,
    Participant,
    ParticipantIdentifier,
    ParticipantProfile,
    ReferralSource,
)

admin.site.register(
    [
        Participant,
        ParticipantIdentifier,
        ParticipantProfile,
        ConsentRecord,
        GuardianRelationship,
        ReferralSource,
    ]
)
