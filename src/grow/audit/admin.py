from django.contrib import admin

from grow.audit.models import AuditEvent

admin.site.register(AuditEvent)
