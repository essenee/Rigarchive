from django.contrib import admin, messages
from django import forms
from django.contrib.admin.views.autocomplete import AutocompleteJsonView
from django.contrib.admin.widgets import AutocompleteSelect
from django.urls import path, reverse
from django.core import signing
from django.http import Http404, HttpResponseRedirect
from django.template.response import TemplateResponse
from django.db import DatabaseError
from django.core.exceptions import NON_FIELD_ERRORS, ValidationError, PermissionDenied
from reference.powertrain import FIELDS

from .models import (
    Engine,
    EngineIdentityCorrection,
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


class EngineAutocompleteJsonView(AutocompleteJsonView):
    def process_request(self, request):
        result = super().process_request(request)
        if result[1].model is not Engine:
            raise PermissionDenied
        return result

    def serialize_result(self, obj, to_field_name):
        result = super().serialize_result(obj, to_field_name)
        # Admin-only discriminator: public names and Engine.__str__ remain stable.
        key = obj.internal_variant_key or 'no explicit discriminator'
        result['text'] = f"{obj} [{key}] (PK {obj.pk})"
        return result


class EngineAutocompleteSelect(AutocompleteSelect):
    def get_url(self):
        return reverse(f'{self.admin_site.name}:reference_engine_variant_autocomplete')


class EngineIdentityCorrectionForm(forms.Form):
    proposed_key = forms.CharField(max_length=100, required=False, strip=False,
        help_text='Explicitly enter the reviewed key. Empty means no discriminator is established.')
    reason = forms.CharField(widget=forms.Textarea, label='Correction explanation')
    acknowledgment = forms.BooleanField(label='I acknowledge this changes an established Engine registry identity.')

    def clean_proposed_key(self):
        from reference.models import normalize_internal_variant_key
        if 'proposed_key' not in self.data:
            raise ValidationError('Explicit proposed-key entry is required.')
        return normalize_internal_variant_key(self.cleaned_data['proposed_key'])


@admin.register(Engine)
class EngineAdmin(admin.ModelAdmin):
    change_form_template = 'admin/reference/engine/change_form.html'

    def change_view(self, request, object_id, form_url='', extra_context=None):
        from reference.engine_identity_correction import require_authorized
        try:
            require_authorized(request.user); allowed = True
        except PermissionDenied:
            allowed = False
        return super().change_view(request, object_id, form_url,
            {**(extra_context or {}), 'can_correct_engine_identity': allowed})

    def correct_identity_view(self, request, object_id):
        from reference.engine_identity_correction import require_authorized, preview_correction, execute_correction
        require_authorized(request.user)
        engine = self.get_object(request, object_id)
        if engine is None:
            raise Http404
        if not self.has_change_permission(request, engine):
            raise PermissionDenied
        review = None; token = None
        form = EngineIdentityCorrectionForm(request.POST if request.method == 'POST' else None)
        if request.method == 'POST':
            if 'confirm' in request.POST:
                try:
                    acknowledgment = forms.BooleanField(required=True).clean(request.POST.get('acknowledgment'))
                    review = signing.loads(request.POST.get('review_token', ''), salt='engine-identity-correction', max_age=900)
                    if (review.get('before', {}).get('id') != engine.pk
                            or review.get('before', {}).get('uuid') != str(engine.uuid)):
                        raise ValidationError('This preview belongs to a different Engine; review again.')
                    audit = execute_correction(review, actor=request.user, acknowledged=acknowledgment, confirmed=True)
                    self.message_user(request, f'Engine identity corrected; durable audit {audit.uuid}.', messages.SUCCESS)
                    return HttpResponseRedirect(reverse('admin:reference_engine_change', args=[engine.pk]))
                except (signing.BadSignature, ValidationError, DatabaseError) as exc:
                    # No success response until the atomic key+audit operation commits.
                    form.add_error(None, 'Correction not executed. Review again: ' + str(exc))
                    review = None
            elif form.is_valid():
                try:
                    review = preview_correction(engine.pk, proposed_key=form.cleaned_data['proposed_key'],
                        reason=form.cleaned_data['reason'], actor=request.user)
                    token = signing.dumps(review, salt='engine-identity-correction', compress=True)
                except (ValidationError, DatabaseError) as exc:
                    form.add_error(None, str(exc))
        return TemplateResponse(request, 'admin/reference/engine/correct_identity.html', {
            **self.admin_site.each_context(request), 'opts':self.model._meta, 'original':engine,
            'title':'Correct Engine Identity', 'form':form, 'review':review, 'review_token':token,
            'association_count':engine.vehicle_definitions.count(),
        })

    list_display = ("manufacturer", "engine_code", "internal_variant_key", "name", *FIELDS)
    list_filter = ("manufacturer",)
    search_fields = ("manufacturer__name", "engine_code", "internal_variant_key", "name")
    autocomplete_fields = ("manufacturer",)
    readonly_fields = ("uuid", "created_at", "updated_at")

    def get_readonly_fields(self, request, obj=None):
        return self.readonly_fields + (("manufacturer", "engine_code", "internal_variant_key") if obj else ())

    def get_urls(self):
        return [path('<path:object_id>/correct-identity/', self.admin_site.admin_view(self.correct_identity_view),
                     name='reference_engine_correct_identity'), path('variant-autocomplete/', self.admin_site.admin_view(
            EngineAutocompleteJsonView.as_view(admin_site=self.admin_site)),
            name='reference_engine_variant_autocomplete')] + super().get_urls()


@admin.register(EngineIdentityCorrection)
class EngineIdentityCorrectionAdmin(admin.ModelAdmin):
    list_display = ('created_at', 'engine_pk_snapshot', 'engine_uuid_snapshot', 'actor_label', 'request_reference')
    readonly_fields = tuple(field.name for field in EngineIdentityCorrection._meta.fields)
    search_fields = ('engine_uuid_snapshot', 'request_reference', 'actor_label', 'reason')

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


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
    def _update_errors(self, errors):
        # Model invariants still apply to snapshots intentionally absent/read-only
        # in Admin. Django cannot attach a field error to an excluded form field.
        if hasattr(errors, "error_dict"):
            mapped = {}
            for name, problems in errors.error_dict.items():
                if name == NON_FIELD_ERRORS or name in self.fields:
                    mapped.setdefault(name, []).extend(problems)
                else:
                    for problem in problems:
                        mapped.setdefault(NON_FIELD_ERRORS, []).extend(
                            ValidationError(f"{name.replace('_', ' ')}: {message}",
                                            code=getattr(problem, "code", None))
                            for message in problem.messages
                        )
            errors = ValidationError(mapped)
        super()._update_errors(errors)

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
    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == 'engine':
            kwargs['widget'] = EngineAutocompleteSelect(db_field, self.admin_site,
                                                       using=kwargs.get('using'))
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

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
        "is_public",
    )

    list_filter = (
        "is_public",
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
                    "is_public",
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
