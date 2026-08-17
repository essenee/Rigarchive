from django.contrib import admin

from .models import (
    ApplicabilityFeature,
    ApplicabilityState,
    MeasurementDefinition,
    MeasurementResult,
    MeasurementResultCondition,
)


class ApplicabilityStateInline(admin.TabularInline):
    model = ApplicabilityState
    extra = 1
    readonly_fields = ("slug",)


@admin.register(ApplicabilityFeature)
class ApplicabilityFeatureAdmin(admin.ModelAdmin):
    list_display = ("name", "slug")
    search_fields = ("name", "description")
    readonly_fields = ("slug",)
    inlines = [ApplicabilityStateInline]


@admin.register(ApplicabilityState)
class ApplicabilityStateAdmin(admin.ModelAdmin):
    list_display = ("name", "feature", "slug")
    list_filter = ("feature",)
    search_fields = ("name", "feature__name")
    readonly_fields = ("slug",)


@admin.register(MeasurementDefinition)
class MeasurementDefinitionAdmin(admin.ModelAdmin):
    list_display = ("name", "category", "slug", "is_active")
    list_filter = ("category", "is_active")
    search_fields = ("name", "description")
    readonly_fields = ("slug",)


class MeasurementResultConditionInline(admin.TabularInline):
    model = MeasurementResultCondition
    extra = 1


@admin.register(MeasurementResult)
class MeasurementResultAdmin(admin.ModelAdmin):
    list_display = (
        "generation",
        "definition",
        "value",
        "unit",
        "get_is_generation_wide",
        "get_applicability_summary",
        "is_active",
    )

    list_filter = (
        "definition",
        "unit",
        "is_active",
        "generation__vehicle_model__manufacturer",
    )

    search_fields = (
        "generation__name",
        "definition__name",
        "notes",
    )

    inlines = [MeasurementResultConditionInline]

    @admin.display(boolean=True, description="Generation-wide")
    def get_is_generation_wide(self, obj: MeasurementResult) -> bool:
        return obj.is_generation_wide

    @admin.display(description="Applicability")
    def get_applicability_summary(self, obj: MeasurementResult) -> str:
        return obj.applicability_summary
