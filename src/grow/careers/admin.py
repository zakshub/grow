from django.contrib import admin

from grow.careers.models import (
    CareerAlias,
    CareerCluster,
    CareerDimensionRelationship,
    CareerEnvironmentObservation,
    CareerFamily,
    CareerImportBatch,
    CareerImportDiff,
    CareerPathway,
    CareerProfile,
    CareerProfileVersion,
    CareerRelationship,
    CareerReviewDecision,
    CareerSkill,
    CareerSkillRequirement,
    CareerTaxonomy,
    CareerTaxonomyVersion,
    MarketObservation,
    ResearchSource,
)


class InspectionAdmin(admin.ModelAdmin):
    list_per_page = 50

    def get_readonly_fields(self, request: object, obj: object | None = None) -> tuple[str, ...]:
        return tuple(field.name for field in self.model._meta.fields)

    def has_add_permission(self, request: object) -> bool:
        return False

    def has_delete_permission(self, request: object, obj: object | None = None) -> bool:
        return False


@admin.register(CareerTaxonomy)
class CareerTaxonomyAdmin(InspectionAdmin):
    list_display = ("code", "title", "geography", "created_at")
    search_fields = ("code", "title")


@admin.register(CareerTaxonomyVersion)
class CareerTaxonomyVersionAdmin(InspectionAdmin):
    list_display = ("taxonomy", "version", "lifecycle", "review_status", "published_at")
    list_filter = ("lifecycle", "review_status")


@admin.register(CareerProfileVersion)
class CareerProfileVersionAdmin(InspectionAdmin):
    list_display = (
        "title_en",
        "profile",
        "taxonomy_version",
        "lifecycle",
        "review_status",
        "data_classification",
        "participant_recommendation_ready",
    )
    list_filter = ("lifecycle", "review_status", "data_classification")
    search_fields = ("profile__code", "title_en", "title_ur", "pakistan_title")


@admin.register(ResearchSource)
class ResearchSourceAdmin(InspectionAdmin):
    list_display = (
        "title",
        "publisher",
        "source_type",
        "quality_status",
        "review_status",
        "freshness",
        "expires_at",
    )
    list_filter = ("source_type", "quality_status", "review_status", "freshness")


@admin.register(MarketObservation)
class MarketObservationAdmin(InspectionAdmin):
    list_display = (
        "profile_version",
        "observation_type",
        "country",
        "value_state",
        "confidence",
        "freshness",
        "expires_at",
    )
    list_filter = ("observation_type", "value_state", "confidence", "freshness", "review_status")


@admin.register(CareerImportBatch)
class CareerImportBatchAdmin(InspectionAdmin):
    list_display = (
        "taxonomy",
        "schema_version",
        "status",
        "created_at",
        "approved_by",
        "published_version",
    )
    list_filter = ("status", "schema_version")


for model in (
    CareerCluster,
    CareerFamily,
    CareerProfile,
    CareerAlias,
    CareerRelationship,
    CareerDimensionRelationship,
    CareerEnvironmentObservation,
    CareerSkill,
    CareerSkillRequirement,
    CareerPathway,
    CareerReviewDecision,
    CareerImportDiff,
):
    admin.site.register(model, InspectionAdmin)
