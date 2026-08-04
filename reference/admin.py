from django.contrib import admin

from .models import Generation, Manufacturer, VehicleDefinition, VehicleModel


@admin.register(Manufacturer)
class ManufacturerAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "country_code",
        "is_active",
        "updated_at",
    )

    list_filter = ("is_active", "country_code")
    search_fields = ("name",)
    prepopulated_fields = {"slug": ("name",)}
    readonly_fields = ("created_at", "updated_at")


@admin.register(VehicleModel)
class VehicleModelAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "manufacturer",
        "is_active",
        "updated_at",
    )

    list_filter = ("is_active", "manufacturer")
    search_fields = ("name", "manufacturer__name")
    autocomplete_fields = ("manufacturer",)
    prepopulated_fields = {"slug": ("name",)}
    readonly_fields = ("created_at", "updated_at")


@admin.register(Generation)
class GenerationAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "vehicle_model",
        "start_year",
        "end_year",
        "generation_number",
        "is_active",
    )

    list_filter = (
        "is_active",
        "vehicle_model__manufacturer",
        "start_year",
    )

    search_fields = (
        "name",
        "vehicle_model__name",
        "vehicle_model__manufacturer__name",
    )

    autocomplete_fields = ("vehicle_model",)
    prepopulated_fields = {"slug": ("name",)}
    readonly_fields = ("created_at", "updated_at")


@admin.register(VehicleDefinition)
class VehicleDefinitionAdmin(admin.ModelAdmin):
    list_display = (
        "model_year",
        "generation",
        "trim_name",
        "engine_name",
        "drivetrain",
        "market",
        "is_active",
    )

    list_filter = (
        "is_active",
        "market",
        "drivetrain",
        "model_year",
        "generation__vehicle_model__manufacturer",
    )

    search_fields = (
        "trim_name",
        "engine_name",
        "generation__name",
        "generation__vehicle_model__name",
        "generation__vehicle_model__manufacturer__name",
    )

    autocomplete_fields = ("generation",)
    readonly_fields = ("created_at", "updated_at")