import os
from django.conf import settings
from django.db.models import Prefetch
from django.http import Http404
from django.views.decorators.http import require_GET
from django.shortcuts import render
from django.views.generic import DetailView, ListView

from .forms import VehicleSelectorForm
from .models import Generation, Manufacturer, VehicleDefinition, VehicleModel
from .services import (
    discover_manufacturers,
    get_vehicle_context,
    get_vehicle_selector_context,
    get_full_specifications_context,
    get_generation_hub_context,
    record_recently_viewed_generation,
)


def get_presentation_hero_image_url(
    mfr_slug_or_gen,
    model_slug: str = None,
    generation_slug: str = None,
) -> str:
    """
    Presentation-local helper resolving static demo images for UI preview.
    Uses manufacturer + model + generation identity to prevent collision across models.
    Durable Generation <-> Asset association is deferred to future Asset/Media domain architecture.
    """
    if hasattr(mfr_slug_or_gen, "slug"):
        gen = mfr_slug_or_gen
        g_slug = gen.slug
        m_slug = gen.vehicle_model.slug if getattr(gen, "vehicle_model", None) else ""
        mfr_s = (
            gen.vehicle_model.manufacturer.slug
            if getattr(gen, "vehicle_model", None)
            and getattr(gen.vehicle_model, "manufacturer", None)
            else ""
        )
    else:
        mfr_s = str(mfr_slug_or_gen or "")
        m_slug = str(model_slug or "")
        g_slug = str(generation_slug or "")

    # Primary model-specific lookup key: static/images/generations/{mfr_s}-{m_slug}-{g_slug}.jpg
    if mfr_s and m_slug and g_slug:
        primary_filename = f"images/generations/{mfr_s}-{m_slug}-{g_slug}.jpg"
        if os.path.exists(os.path.join(settings.BASE_DIR, "static", primary_filename)):
            return f"/static/{primary_filename}"

    # Legacy fallback strictly for 4runner to preserve existing approved 4Runner images
    if m_slug == "4runner" and g_slug:
        legacy_filename = f"images/generations/{g_slug}.jpg"
        if os.path.exists(os.path.join(settings.BASE_DIR, "static", legacy_filename)):
            return f"/static/{legacy_filename}"

    # No cross-model fallback: return empty string (templates render default presentation placeholder)
    return ""


class ManufacturerListView(ListView):
    """
    Display active vehicle manufacturers and their active models in the Reference Domain.
    Supports simple search filtering across manufacturer and model names.
    """

    model = Manufacturer
    template_name = "reference/manufacturer_list.html"
    context_object_name = "manufacturers"

    def get_queryset(self):
        return discover_manufacturers(
            self.request.GET.get("q", ""), populated_only=True,
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["search_query"] = self.request.GET.get("q", "").strip()
        return context


class ManufacturerDetailView(DetailView):
    """
    Display one manufacturer, its active vehicle models, and their active generations.
    """

    model = Manufacturer
    template_name = "reference/manufacturer_detail.html"
    context_object_name = "manufacturer"
    slug_url_kwarg = "manufacturer_slug"

    def get_queryset(self):
        return (
            Manufacturer.objects.filter(is_active=True)
            .prefetch_related(
                Prefetch(
                    "vehicle_models",
                    queryset=VehicleModel.objects.filter(
                        is_active=True,
                        generations__is_active=True,
                        generations__vehicle_definitions__is_active=True,
                    )
                    .distinct()
                    .prefetch_related(
                        Prefetch(
                            "generations",
                            queryset=Generation.objects.filter(
                                is_active=True,
                                vehicle_definitions__is_active=True,
                            ).distinct(),
                            to_attr="active_generations",
                        )
                    ),
                    to_attr="active_vehicle_models",
                )
            )
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        vehicle_models = getattr(self.object, "active_vehicle_models", [])
        for model_obj in vehicle_models:
            for gen_obj in getattr(model_obj, "active_generations", []):
                gen_obj.hero_image_url = get_presentation_hero_image_url(gen_obj)
        context["vehicle_models"] = vehicle_models
        return context


class VehicleModelDetailView(DetailView):
    """
    Display one vehicle model and its active generations.
    """

    model = VehicleModel
    template_name = "reference/vehicle_model_detail.html"
    context_object_name = "vehicle_model"
    slug_url_kwarg = "vehicle_model_slug"

    def get_queryset(self):
        return (
            VehicleModel.objects.filter(
                is_active=True,
                manufacturer__is_active=True,
                manufacturer__slug=self.kwargs["manufacturer_slug"],
            )
            .select_related("manufacturer")
            .prefetch_related("generations")
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        generations = list(self.object.generations.filter(is_active=True))
        for gen_obj in generations:
            gen_obj.hero_image_url = get_presentation_hero_image_url(gen_obj)
        context["vehicle_context"] = get_vehicle_context(self.object)
        context["generations"] = generations
        return context


class GenerationDetailView(DetailView):
    """
    Display one generation knowledge hub with interactive year and configuration filtering.
    """

    model = Generation
    template_name = "reference/generation_detail.html"
    context_object_name = "generation"
    slug_url_kwarg = "generation_slug"

    def get_queryset(self):
        return (
            Generation.objects.filter(
                is_active=True,
                vehicle_model__is_active=True,
                vehicle_model__manufacturer__is_active=True,
                vehicle_model__manufacturer__slug=(
                    self.kwargs["manufacturer_slug"]
                ),
                vehicle_model__slug=self.kwargs["vehicle_model_slug"],
            )
            .select_related(
                "vehicle_model",
                "vehicle_model__manufacturer",
            )
            .prefetch_related("vehicle_definitions")
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        year_param = self.request.GET.get("year")
        trim_param = self.request.GET.get("trim")
        config_param = self.request.GET.get("configuration")

        # Track session history for Recently Viewed panel
        record_recently_viewed_generation(self.request, self.object)

        hub_context = get_generation_hub_context(
            self.object,
            model_year=year_param,
            trim_name=trim_param,
            config_slug=config_param,
        )
        context.update(hub_context)
        # Hub filters do not change the route object into an exact identity.
        context["vehicle_context"] = get_vehicle_context(self.object)
        context["generation_hero_image"] = get_presentation_hero_image_url(self.object)
        return context


class ModelYearOverviewView(DetailView):
    """
    Display a model-year landing page summarizing available canonical vehicle configurations for one year.
    """

    model = Generation
    template_name = "reference/model_year_overview.html"
    context_object_name = "generation"
    slug_url_kwarg = "generation_slug"

    def get_queryset(self):
        return (
            Generation.objects.filter(
                is_active=True,
                vehicle_model__is_active=True,
                vehicle_model__manufacturer__is_active=True,
                vehicle_model__manufacturer__slug=self.kwargs["manufacturer_slug"],
                vehicle_model__slug=self.kwargs["vehicle_model_slug"],
            )
            .select_related("vehicle_model", "vehicle_model__manufacturer")
            .prefetch_related("vehicle_definitions")
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        model_year = self.kwargs["model_year"]

        # Validate year bounds against Generation
        if self.object.end_year is not None:
            if not (self.object.start_year <= model_year <= self.object.end_year):
                raise Http404(f"Model year {model_year} is out of bounds for generation {self.object.name}.")
        else:
            if model_year < self.object.start_year:
                raise Http404(f"Model year {model_year} is out of bounds for generation {self.object.name}.")

        active_defs = list(
            self.object.vehicle_definitions.filter(
                model_year=model_year,
                is_active=True,
            ).order_by("trim_name", "drivetrain", "engine_name")
        )

        if not active_defs:
            raise Http404(f"No active canonical vehicle definitions found for model year {model_year}.")

        # Group configurations by Trim
        trims_dict = {}
        for vd in active_defs:
            t_name = vd.trim_name or "Base / Standard"
            if t_name not in trims_dict:
                trims_dict[t_name] = []
            trims_dict[t_name].append(vd)

        context["vehicle_context"] = get_vehicle_context(self.object)
        context["model_year"] = model_year
        context["vehicle_definitions"] = active_defs
        context["total_configurations"] = len(active_defs)
        context["trims_dict"] = trims_dict
        context["vehicle_model"] = self.object.vehicle_model
        context["manufacturer"] = self.object.vehicle_model.manufacturer
        return context


class VehicleDefinitionDetailView(DetailView):
    """
    Display one canonical vehicle definition with full specifications and applicable measurements.
    """

    model = VehicleDefinition
    template_name = "reference/vehicle_definition_detail.html"
    context_object_name = "vehicle_definition"
    slug_url_kwarg = "vehicle_definition_slug"

    def get_queryset(self):
        return VehicleDefinition.objects.filter(
            is_active=True,
            generation__is_active=True,
            generation__vehicle_model__is_active=True,
            generation__vehicle_model__manufacturer__is_active=True,
            generation__vehicle_model__manufacturer__slug=(
                self.kwargs["manufacturer_slug"]
            ),
            generation__vehicle_model__slug=(
                self.kwargs["vehicle_model_slug"]
            ),
            generation__slug=self.kwargs["generation_slug"],
        ).select_related(
            "generation",
            "generation__vehicle_model",
            "generation__vehicle_model__manufacturer",
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        specs_context = get_full_specifications_context(self.object)
        context.update(specs_context)
        context["vehicle_context"] = get_vehicle_context(self.object)
        context["generation_hero_image"] = get_presentation_hero_image_url(
            self.object.generation
        )
        return context


@require_GET
def vehicle_selector(request):
    """GET-only baseline selection; deferred categories stay on this real page."""
    data = request.GET.copy()
    if "destination" not in data:
        data["destination"] = "generations"
    form = VehicleSelectorForm(data)
    context = {"selector_form": form, "groups": []}
    if not form.is_valid():
        return render(request, "reference/vehicle_selector.html", context, status=400)

    fields = form.cleaned_data
    if fields["model"] and not fields["manufacturer"]:
        form.add_error("model", "Choose a manufacturer before selecting a model.")
        return render(request, "reference/vehicle_selector.html", context, status=400)
    context.update(get_vehicle_selector_context(
        query=fields["q"], manufacturer_slug=fields["manufacturer"],
        model_slug=fields["model"], token=fields["destination"],
    ))
    for group in context["groups"]:
        for choice in group["choices"]:
            newest = choice["generation"]
            choice["image_url"] = get_presentation_hero_image_url(newest) if newest else ""
    return render(request, "reference/vehicle_selector.html", context)
