from django.contrib import admin
from django.db.models import Model
from django.http import HttpRequest

from grow.assessments.models import (
    AssessmentDefinition,
    AssessmentDimension,
    AssessmentDimensionRequirement,
    AssessmentItem,
    AssessmentItemPresentation,
    AssessmentItemVariant,
    AssessmentObservation,
    AssessmentResponse,
    AssessmentSection,
    AssessmentSession,
    AssessmentVersion,
    Contradiction,
    ContradictionEvidence,
    DimensionEvidence,
    DimensionResult,
    EvidenceItem,
    EvidenceSource,
)


class InspectionOnlyAdmin(admin.ModelAdmin):
    """Milestone 2 inspection surface; audited mutations stay in services."""

    def has_add_permission(self, request: HttpRequest) -> bool:
        return False

    def has_change_permission(self, request: HttpRequest, obj: Model | None = None) -> bool:
        return False

    def has_delete_permission(self, request: HttpRequest, obj: Model | None = None) -> bool:
        return False


admin.site.register(
    [
        AssessmentSession,
        AssessmentDefinition,
        AssessmentVersion,
        AssessmentSection,
        AssessmentDimension,
        AssessmentDimensionRequirement,
        AssessmentItem,
        AssessmentItemVariant,
        AssessmentItemPresentation,
        AssessmentResponse,
        AssessmentObservation,
        EvidenceSource,
        EvidenceItem,
        DimensionEvidence,
        DimensionResult,
        Contradiction,
        ContradictionEvidence,
    ],
    InspectionOnlyAdmin,
)
