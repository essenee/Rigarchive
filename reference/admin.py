from django.contrib import admin

from .models import (
    CanonicalRecordCorrection,
    Generation,
    ImportExecutionReceipt,
    Manufacturer,
    VehicleDefinition,
    VehicleModel,
)



@admin.register(Manufacturer)
class ManufacturerAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "country_code",
        "is_active",
        "updated_at",
    )

    list_filter = (
        "is_active",
        "country_code",
    )

    search_fields = (
        "name",
    )

    readonly_fields = (
        "uuid",
        "slug",
        "created_at",
        "updated_at",
    )

    fieldsets = (
        (
            None,
            {
                "fields": (
                    "name",
                    "country_code",
                    "is_active",
                )
            },
        ),
        (
            "System information",
            {
                "fields": (
                    "uuid",
                    "slug",
                    "created_at",
                    "updated_at",
                ),
                "classes": ("collapse",),
            },
        ),
    )


@admin.register(VehicleModel)
class VehicleModelAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "manufacturer",
        "is_active",
        "updated_at",
    )

    list_filter = (
        "is_active",
        "manufacturer",
    )

    search_fields = (
        "name",
        "manufacturer__name",
    )

    autocomplete_fields = (
        "manufacturer",
    )

    readonly_fields = (
        "uuid",
        "slug",
        "created_at",
        "updated_at",
    )

    fieldsets = (
        (
            None,
            {
                "fields": (
                    "manufacturer",
                    "name",
                    "is_active",
                )
            },
        ),
        (
            "System information",
            {
                "fields": (
                    "uuid",
                    "slug",
                    "created_at",
                    "updated_at",
                ),
                "classes": ("collapse",),
            },
        ),
    )


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

    autocomplete_fields = (
        "vehicle_model",
    )

    readonly_fields = (
        "uuid",
        "slug",
        "created_at",
        "updated_at",
    )

    fieldsets = (
        (
            None,
            {
                "fields": (
                    "vehicle_model",
                    "name",
                    "generation_number",
                    "start_year",
                    "end_year",
                    "notes",
                    "is_active",
                )
            },
        ),
        (
            "System information",
            {
                "fields": (
                    "uuid",
                    "slug",
                    "created_at",
                    "updated_at",
                ),
                "classes": ("collapse",),
            },
        ),
    )


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
        "slug",
        "generation__name",
        "generation__vehicle_model__name",
        "generation__vehicle_model__manufacturer__name",
    )

    autocomplete_fields = (
        "generation",
    )

    readonly_fields = (
        "uuid",
        "slug",
        "created_at",
        "updated_at",
    )

    fieldsets = (
        (
            "Vehicle configuration",
            {
                "fields": (
                    "generation",
                    "model_year",
                    "trim_name",
                    "engine_name",
                    "drivetrain",
                    "market",
                )
            },
        ),
        (
            "Record details",
            {
                "fields": (
                    "notes",
                    "is_active",
                )
            },
        ),
        (
            "System information",
            {
                "fields": (
                    "uuid",
                    "slug",
                    "created_at",
                    "updated_at",
                ),
                "classes": ("collapse",),
            },
        ),
    )


@admin.register(ImportExecutionReceipt)
class ImportExecutionReceiptAdmin(admin.ModelAdmin):
    list_display = (
        "executed_at",
        "operator_label",
        "planned_action",
        "execution_outcome",
        "target_slug",
        "source_id",
    )

    list_filter = (
        "execution_outcome",
        "planned_action",
        "execution_channel",
    )

    search_fields = (
        "manifest_hash",
        "raw_artifact_hash",
        "candidate_reference",
        "target_slug",
        "operator_label",
    )

    readonly_fields = [
        "id",
        "uuid",
        "created_at",
        "updated_at",
        "executed_at",
        "execution_channel",
        "operator_label",
        "manifest_hash",
        "candidate_reference",
        "planned_action",
        "create_basis",
        "adjudication_hash",
        "source_id",
        "raw_artifact_hash",
        "raw_artifact_reference",
        "source_identity_type",
        "native_identifier",
        "resolved_generation_id",
        "target_slug",
        "target_model_year",
        "target_trim_name",
        "target_engine_name",
        "target_drivetrain",
        "target_market",
        "target_fields_json",
        "execution_outcome",
        "messages_json",
        "created_vehicle_definition",
        "existing_vehicle_definition",
        "created_vehicle_definition_pk_snapshot",
        "created_vehicle_definition_uuid_snapshot",
        "created_vehicle_definition_slug_snapshot",
        "existing_vehicle_definition_pk_snapshot",
        "existing_vehicle_definition_uuid_snapshot",
        "existing_vehicle_definition_slug_snapshot",
    ]

    def has_add_permission(self, request) -> bool:
        return False

    def has_delete_permission(self, request, obj=None) -> bool:
        return False

    def has_change_permission(self, request, obj=None) -> bool:
        return False


@admin.register(CanonicalRecordCorrection)
class CanonicalRecordCorrectionAdmin(admin.ModelAdmin):
    list_display = (
        "created_at",
        "operator_label",
        "correction_reason",
        "superseded_vehicle_definition_slug_snapshot",
        "replacement_vehicle_definition_slug_snapshot",
    )

    list_filter = (
        "correction_reason",
        "operator_label",
    )

    search_fields = (
        "superseded_vehicle_definition_slug_snapshot",
        "replacement_vehicle_definition_slug_snapshot",
        "superseded_vehicle_definition_uuid_snapshot",
        "replacement_vehicle_definition_uuid_snapshot",
        "operator_label",
        "correction_reason",
    )

    readonly_fields = [
        "id",
        "uuid",
        "created_at",
        "updated_at",
        "superseded_vehicle_definition",
        "replacement_vehicle_definition",
        "superseded_vehicle_definition_pk_snapshot",
        "superseded_vehicle_definition_uuid_snapshot",
        "superseded_vehicle_definition_slug_snapshot",
        "replacement_vehicle_definition_pk_snapshot",
        "replacement_vehicle_definition_uuid_snapshot",
        "replacement_vehicle_definition_slug_snapshot",
        "correction_reason",
        "operator_label",
        "notes",
        "execution_receipt",
    ]

    def has_add_permission(self, request) -> bool:
        return False

    def has_delete_permission(self, request, obj=None) -> bool:
        return False

    def has_change_permission(self, request, obj=None) -> bool:
        return False