from django.contrib import admin, messages
from django import forms
from django.contrib.admin.views.autocomplete import AutocompleteJsonView
from django.contrib.admin.views.main import PAGE_VAR, ChangeList
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
    BODY_AUTHORING_ATTRIBUTES,
    NominalBedLength,
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


def factory_body_configuration_label(body):
    """Admin-only sparse label; retain distinguishing keys/tokens on collisions."""
    fields = ('cab_configuration', 'bed_length', 'door_configuration',
              *(f for f in BODY_ATTRIBUTES if f != 'door_configuration'))

    def display(field, value):
        if field == 'cab_configuration':
            return dict(FactoryBodyConfiguration.CabConfiguration.choices)[value]
        if field == 'bed_length':
            return str(value)
        return value.upper() if field in ('body_code', 'body_code_namespace') else value.replace('-', ' ').replace('_', ' ').title()

    def simple(item):
        return ', '.join(display(f, getattr(item, f)) for f in fields if getattr(item, f)
                         and not (f == 'door_configuration' and item.cab_configuration))

    label = simple(body)
    peers = [body, *(other for other in FactoryBodyConfiguration.objects.filter(generation_id=body.generation_id).select_related('bed_length')
                     if other.pk != body.pk and simple(other) == label)]
    if len(peers) == 1:
        return label
    parts = []
    for field in fields:
        value = getattr(body, field)
        if not value:
            continue
        values = {getattr(peer, field) for peer in peers}
        if field == 'door_configuration' and body.cab_configuration and len(values) == 1:
            continue
        shown = display(field, value)
        if len(values) > 1:
            # Preserve raw spelling if humanization itself collapsed distinct tokens.
            if any(v and v != value and display(field, v) == shown for v in values):
                shown = value
            key = field.replace('_designation', '').replace('_configuration', '').replace('_', ' ').title()
            shown = f'{key}: {shown}'
        parts.append(shown)
    return ', '.join(parts)


class FactoryBodyChoiceField(forms.ModelChoiceField):
    def label_from_instance(self, obj):
        return factory_body_configuration_label(obj)


class FactoryBodyAutocompleteJsonView(AutocompleteJsonView):
    def process_request(self, request):
        result = super().process_request(request)
        if result[1].model is not FactoryBodyConfiguration:
            raise PermissionDenied
        return result

    def get_queryset(self):
        queryset = super().get_queryset()
        try:
            generation_id = int(self.request.GET.get('generation', ''))
        except (TypeError, ValueError):
            return queryset.none()
        return queryset.filter(generation_id=generation_id).order_by('pk')

    def serialize_result(self, obj, to_field_name):
        result = super().serialize_result(obj, to_field_name)
        result['text'] = factory_body_configuration_label(obj)
        return result


class FactoryBodyAutocompleteSelect(AutocompleteSelect):
    def get_url(self):
        return reverse(f'{self.admin_site.name}:reference_factorybodyconfiguration_scoped_autocomplete')


class EngineAutocompleteJsonView(AutocompleteJsonView):
    def get_queryset(self):
        queryset = super().get_queryset()
        try:
            generation_id = int(self.request.GET.get('generation', ''))
        except (TypeError, ValueError):
            return queryset.none()
        manufacturer_id = Generation.objects.filter(pk=generation_id).values_list(
            'vehicle_model__manufacturer_id', flat=True).first()
        return queryset.available_for_manufacturer(manufacturer_id)

    def process_request(self, request):
        result = super().process_request(request)
        if result[1].model is not Engine:
            raise PermissionDenied
        return result

    def serialize_result(self, obj, to_field_name):
        result = super().serialize_result(obj, to_field_name)
        # Admin-only discriminator: public names and Engine.__str__ remain stable.
        discriminator = f" [{obj.internal_variant_key}]" if obj.internal_variant_key else ""
        result['text'] = f"{obj}{discriminator} (PK {obj.pk})"
        return result


class EngineAutocompleteSelect(AutocompleteSelect):
    def get_url(self):
        return reverse(f'{self.admin_site.name}:reference_engine_variant_autocomplete')


class EngineAdminForm(forms.ModelForm):
    class Meta:
        model = Engine
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.manufacturer_id:
            self.fields['also_available_for_manufacturers'].queryset = Manufacturer.objects.exclude(
                pk=self.instance.manufacturer_id)

    def clean(self):
        cleaned = super().clean()
        manufacturer = cleaned.get('manufacturer') or (self.instance.manufacturer if self.instance.manufacturer_id else None)
        additional = cleaned.get('also_available_for_manufacturers')
        if manufacturer and additional is not None and additional.filter(pk=manufacturer.pk).exists():
            self.add_error('also_available_for_manufacturers', 'Do not include the primary manufacturer.')
        return cleaned


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
    form = EngineAdminForm
    filter_horizontal = ('also_available_for_manufacturers',)
    readonly_fields = ("uuid", "created_at", "updated_at")

    def get_fields(self, request, obj=None):
        fields = list(super().get_fields(request, obj))
        fields.remove('also_available_for_manufacturers')
        fields.append('also_available_for_manufacturers')
        return fields

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
    def get_urls(self):
        return [path('scoped-autocomplete/', self.admin_site.admin_view(
            FactoryBodyAutocompleteJsonView.as_view(admin_site=self.admin_site)),
            name='reference_factorybodyconfiguration_scoped_autocomplete')] + super().get_urls()

    list_display = ("generation", *BODY_AUTHORING_ATTRIBUTES)
    list_filter = ("generation",)
    search_fields = ("generation__name", "generation__vehicle_model__name", *BODY_ATTRIBUTES,
                     'cab_configuration', 'bed_length__designation')
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


@admin.register(NominalBedLength)
class NominalBedLengthAdmin(admin.ModelAdmin):
    list_display = ('designation',)
    search_fields = ('designation',)
    readonly_fields = ('uuid', 'created_at', 'updated_at')


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
        if 'engine' in self.fields or 'factory_body_configuration' in self.fields:
            generation_id = (self.data.get(self.add_prefix('generation')) if self.is_bound
                             else self.initial.get('generation', self.instance.generation_id))
            try:
                generation_id = int(getattr(generation_id, 'pk', generation_id))
            except (TypeError, ValueError):
                generation_id = None
        if 'factory_body_configuration' in self.fields:
            self.fields['factory_body_configuration'].queryset = FactoryBodyConfiguration.objects.filter(
                generation_id=generation_id) if generation_id is not None else FactoryBodyConfiguration.objects.none()
        if 'engine' in self.fields:
            manufacturer_id = Generation.objects.filter(pk=generation_id).values_list(
                'vehicle_model__manufacturer_id', flat=True).first()
            engines = Engine.objects.available_for_manufacturer(manufacturer_id)
            # Retain an unchanged historical selection even if availability was removed.
            if self.instance.pk and self.instance.generation_id == generation_id and self.instance.engine_id:
                engines = (engines | Engine.objects.filter(pk=self.instance.engine_id).distinct()).distinct()
            self.fields['engine'].queryset = engines
        if self.instance.pk:
            transmission_key = self.add_prefix("transmission")
            if self.is_bound and "transmission" in self.fields and transmission_key not in self.data:
                self.data = self.data.copy()
                self.data[transmission_key] = self.instance.transmission
            self.initial["slug_correction"] = self.instance.slug
            # Older Admin submissions omit this new input; omission is not a correction.
            key = self.add_prefix("slug_correction")
            if self.is_bound and key not in self.data:
                self.data = self.data.copy()
                self.data[key] = self.instance.slug

    def clean(self):
        cleaned = super().clean()
        engine = cleaned.get('engine')
        if engine and (not self.instance.pk or engine.pk != self.instance.engine_id):
            name = cleaned.get('engine_name', self.instance.engine_name)
            if name != engine.name:
                self.add_error(None, 'Set Engine name to the exact registered Engine name before assigning the Engine.')
        return cleaned

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


VEHICLE_MANUFACTURER_FILTER = "generation__vehicle_model__manufacturer"


class VehicleDefinitionModelFilter(admin.SimpleListFilter):
    title = "Model"
    parameter_name = "vehicle_model"

    def lookups(self, request, model_admin):
        manufacturer_field = VehicleModel._meta.get_field("manufacturer")
        manufacturer_lookup = f"{VEHICLE_MANUFACTURER_FILTER}__{manufacturer_field.target_field.name}__exact"
        manufacturer = request.GET.get(manufacturer_lookup)
        represented = model_admin.get_queryset(request).order_by().values("generation__vehicle_model_id")
        models = VehicleModel.objects.filter(pk__in=represented).select_related("manufacturer")
        if manufacturer is not None:
            try:
                models = models.filter(manufacturer_id=int(manufacturer))
            except ValueError:
                return ()
        return [(model.pk, str(model)) for model in models]

    def has_output(self):
        return self.value() is not None or super().has_output()

    def queryset(self, request, queryset):
        if self.value() is None:
            return queryset
        try:
            return queryset.filter(generation__vehicle_model_id=int(self.value()))
        except ValueError:
            return queryset.none()


class VehicleDefinitionYearFilter(admin.AllValuesFieldListFilter):
    template = "admin/reference/vehicledefinition/year_filter.html"
    order_parameter = "year_filter_order"

    def __init__(self, field, request, params, model, model_admin, field_path):
        # Sidebar order is presentation state, so consume it before ORM filtering.
        params.pop(self.order_parameter, None)
        self.oldest_first = request.GET.get(self.order_parameter) == "asc"
        super().__init__(field, request, params, model, model_admin, field_path)
        if not self.oldest_first:
            self.lookup_choices = self.lookup_choices.reverse()

    def choices(self, changelist):
        params = {self.order_parameter: None if self.oldest_first else "asc"}
        if changelist.page_num > 1:
            params[PAGE_VAR] = changelist.page_num
        self.toggle_url = changelist.get_query_string(params)
        return super().choices(changelist)


class VehicleDefinitionChangeList(ChangeList):
    def _get_default_ordering(self):
        return ("-model_year", "pk")


@admin.register(VehicleDefinition)
class VehicleDefinitionAdmin(admin.ModelAdmin):
    class Media:
        js = ('admin/js/jquery.init.js', 'admin/js/autocomplete.js',
              'js/admin_engine_availability.js')

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == 'engine':
            kwargs['widget'] = EngineAutocompleteSelect(db_field, self.admin_site,
                                                       using=kwargs.get('using'))
        elif db_field.name == 'factory_body_configuration':
            kwargs['form_class'] = FactoryBodyChoiceField
            kwargs['widget'] = FactoryBodyAutocompleteSelect(db_field, self.admin_site,
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

    def get_changelist(self, request, **kwargs):
        return VehicleDefinitionChangeList

    list_display = (
        "model_year",
        "record_pk",
        "generation",
        "factory_body_configuration_label",
        "engine",
        "trim_name",
        "engine_name",
        "transmission",
        "drivetrain",
        "market",
        "base_msrp",
        "is_active",
        "is_public",
    )

    @admin.display(description="PK", ordering="pk")
    def record_pk(self, obj):
        return obj.pk

    list_filter = (
        VEHICLE_MANUFACTURER_FILTER,
        VehicleDefinitionModelFilter,
        "drivetrain",
        ("model_year", VehicleDefinitionYearFilter),
        "is_public",
        "is_active",
        "market",
    )

    @admin.display(description='Body configuration', ordering='factory_body_configuration')
    def factory_body_configuration_label(self, obj):
        if obj.factory_body_configuration_id:
            return factory_body_configuration_label(obj.factory_body_configuration)
        return None

    list_select_related = ('generation__vehicle_model__manufacturer', 'factory_body_configuration', 'engine')

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
        "record_pk",
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
                    "record_pk",
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
