from django.contrib import admin

from .models import Observation


@admin.register(Observation)
class ObservationAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "vehicle_definition",
        "recorded_by",
        "observed_on",
        "created_at",
    )

    list_filter = (
        "observed_on",
        "created_at",
    )

    search_fields = (
        "title",
        "description",
        "source_notes",
        "vehicle_definition__slug",
        "recorded_by__username",
    )

    autocomplete_fields = (
        "vehicle_definition",
        "recorded_by",
    )

    readonly_fields = (
        "uuid",
        "created_at",
        "updated_at",
    )

    fieldsets = (
        (
            None,
            {
                "fields": (
                    "vehicle_definition",
                    "recorded_by",
                    "title",
                    "description",
                    "observed_on",
                    "source_notes",
                )
            },
        ),
        (
            "System information",
            {
                "fields": (
                    "uuid",
                    "created_at",
                    "updated_at",
                ),
                "classes": ("collapse",),
            },
        ),
    )
