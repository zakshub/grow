from django.contrib import admin

from grow.journeys.models import ParticipantJourney, StateTransition

admin.site.register([ParticipantJourney, StateTransition])
