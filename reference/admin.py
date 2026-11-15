from django.contrib import admin, messages
from django import forms
from reference.powertrain import FIELDS

from .models import (
    Engine,
    FactoryBodyConfiguration,
    BODY_ATTRIBUTES,
    GenerationCorrespondenceRevision,
    CanonicalRecordCorrection,
    Generation,
    ImportExecutionReceipt,
    Manufacturer,
    VehicleDefinition,
    VehicleModel,
)


@admin.register(GenerationCorrespondenceRevision)
class GenerationCorrespondenceRevisionAdmin(admin.ModelAdmin):
    list_display = ("correspondence_uuid", "revision_number", "finding", "native_identifier", "reviewer")
    readonly_fields = tuple(f.name for f in GenerationCorrespondenceRevision._meta.fields)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False



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


@admin.register(Engine)
class EngineAdmin(admin.ModelAdmin):
    list_display = ("manufacturer", "engine_code", "name", *FIELDS)
    list_filter = ("manufacturer",)
    search_fields = ("manufacturer__name", "engine_code", "name")
    autocomplete_fields = ("manufacturer",)
    readonly_fields = ("uuid", "created_at", "updated_at")

    def get_readonly_fields(self, request, obj=None):
        return self.readonly_fields + (("manufacturer", "engine_code") if obj else ())


@admin.register(FactoryBodyConfiguration)
class FactoryBodyConfigurationAdmin(admin.ModelAdmin):
    list_display = ("generation", *BODY_ATTRIBUTES)
    list_filter = ("generation",)
    search_fields = ("generation__name", "generation__vehicle_model__name", *BODY_ATTRIBUTES)
    autocomplete_fields = ("generation",)
    readonly_fields = ("uuid", "created_at", "updated_at")

    def change_view(self, request, object_id, form_url="", extra_context=None):
        obj = self.get_object(request, object_id)
        if obj is not None and self.has_view_or_change_permission(request, obj):
            count = obj.vehicle_definitions.count()
            if count:
                self.message_user(request,
                    f"This shared body configuration affects all {count} referencing VehicleDefinitions. "
                    "Prefer correcting an incorrect vehicle body association or creating a distinct body configuration.",
                    level=messages.WARNING)
        return super().change_view(request, object_id, form_url, extra_context)


class VehicleDefinitionAdminForm(forms.ModelForm):
    slug_correction = forms.SlugField(
        label="Slug", max_length=180, required=False,
        help_text="Warning: changing this stored slug may invalidate existing public URLs. No redirect is created.",
    )

    class Meta:
        model = VehicleDefinition
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk:
            self.initial["slug_correction"] = self.instance.slug
            # Older Admin submissions omit this new input; omission is not a correction.
            key = self.add_prefix("slug_correction")
            if self.is_bound and key not in self.data:
                self.data = self.data.copy()
                self.data[key] = self.instance.slug

    def clean_slug_correction(self):
        if self.add_prefix("slug_correction") not in self.data:
            return self.instance.slug
        value = self.cleaned_data["slug_correction"]
        if not value:
            raise forms.ValidationError("A corrected slug cannot be empty.")
        generation = self.cleaned_data.get("generation", self.instance.generation)
        if VehicleDefinition.objects.filter(generation=generation, slug=value).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError("This generation already has that slug.")
        return value


@admin.register(VehicleDefinition)
class VehicleDefinitionAdmin(admin.ModelAdmin):
    form = VehicleDefinitionAdminForm

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        if obj is None or not self.has_change_permission(request, obj):
            form.base_fields.pop("slug_correction", None)
        return form

    def get_fieldsets(self, request, obj=None):
        fieldsets = super().get_fieldsets(request, obj)
        if obj is None or not self.has_change_permission(request, obj):
            return fieldsets
        return tuple((title, {**options, "fields": tuple(
            "slug_correction" if field == "slug" else field for field in options["fields"]
        )}) for title, options in fieldsets)

    def save_model(self, request, obj, form, change):
        if change and "slug_correction" in form.changed_data:
            if not self.has_change_permission(request, obj):
                from django.core.exceptions import PermissionDenied
                raise PermissionDenied
            obj.slug = form.cleaned_data["slug_correction"]
            obj.save(slug_correction_actor=request.user)
        else:
            super().save_model(request, obj, form, change)

    def construct_change_message(self, request, form, formsets, add=False):
        message = super().construct_change_message(request, form, formsets, add)
        if not add and "slug_correction" in form.changed_data:
            message.append({"changed": {"fields": [
                f"Slug: {form.initial['slug_correction']} → {form.cleaned_data['slug_correction']}"
            ]}})
        return message

    def get_readonly_fields(self, request, obj=None):
        # Registered properties are maintained once, on Engine, not per vehicle.
        return self.readonly_fields + (("engine_name", *FIELDS) if obj and obj.engine_id else ())

    list_display = (
        "model_year",
        "generation",
        "factory_body_configuration",
        "engine",
        "trim_name",
        "engine_name",
        "drivetrain",
        "market",
        "base_msrp",
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
        "factory_body_configuration",
        "engine",
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
                    "factory_body_configuration",
                    "engine",
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
                    "base_msrp",
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
        "operation_type", "correspondence_revision", "resolution_snapshot_json",
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
