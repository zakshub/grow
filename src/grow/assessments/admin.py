from django.contrib import admin

from grow.assessments.models import (
    AssessmentSession,
    Contradiction,
    ContradictionEvidence,
    EvidenceItem,
    EvidenceSource,
)

admin.site.register(
    [
        AssessmentSession,
        EvidenceSource,
        EvidenceItem,
        Contradiction,
        ContradictionEvidence,
    ]
)
