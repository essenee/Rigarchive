import os
from django.conf import settings
from django.db.models import Prefetch
from django.http import Http404
from django.shortcuts import redirect
from django.views.generic import DetailView, ListView

from .models import Generation, Manufacturer, VehicleDefinition, VehicleModel


def get_presentation_hero_image_url(generation_slug: str) -> str:
    """
    Presentation-local helper resolving static demo images for UI preview.
    Durable Generation <-> Asset association is deferred to future Asset/Media domain architecture.
    """
    img_filename = f"images/generations/{generation_slug}.jpg"
    static_path = os.path.join(settings.BASE_DIR, "static", img_filename)
    if os.path.exists(static_path):
        return f"/static/{img_filename}"
    return ""


class ManufacturerListView(ListView):
    """
    Display active vehicle manufacturers and their active models in the Reference Domain.
    """

    model = Manufacturer
    template_name = "reference/manufacturer_list.html"
    context_object_name = "manufacturers"

    def get_queryset(self):
        return (
            Manufacturer.objects.filter(
                is_active=True,
                vehicle_models__is_active=True,
                vehicle_models__generations__is_active=True,
                vehicle_models__generations__vehicle_definitions__is_active=True,
            )
            .distinct()
            .prefetch_related(
                Prefetch(
                    "vehicle_models",
                    queryset=VehicleModel.objects.filter(
                        is_active=True,
                        generations__is_active=True,
                        generations__vehicle_definitions__is_active=True,
                    ).distinct(),
                    to_attr="active_vehicle_models",
                )
            )
        )


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
                gen_obj.hero_image_url = get_presentation_hero_image_url(gen_obj.slug)
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
            gen_obj.hero_image_url = get_presentation_hero_image_url(gen_obj.slug)
        context["generations"] = generations
        return context


class GenerationDetailView(DetailView):
    """
    Display one generation overview, active model years, and detailed specs selector.
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

    def get(self, request, *args, **kwargs):
        config_slug = request.GET.get("configuration")
        year_str = request.GET.get("year")

        mfr_slug = self.kwargs["manufacturer_slug"]
        model_slug = self.kwargs["vehicle_model_slug"]
        gen_slug = self.kwargs["generation_slug"]

        # Validate configuration choice against current hierarchy, generation, active status, and year
        if config_slug:
            config_qs = VehicleDefinition.objects.filter(
                slug=config_slug,
                is_active=True,
                generation__is_active=True,
                generation__vehicle_model__is_active=True,
                generation__vehicle_model__manufacturer__is_active=True,
                generation__vehicle_model__manufacturer__slug=mfr_slug,
                generation__vehicle_model__slug=model_slug,
                generation__slug=gen_slug,
            )

            if year_str and year_str.isdigit():
                config_qs = config_qs.filter(model_year=int(year_str))

            matching_vd = config_qs.first()
            if matching_vd:
                return redirect(
                    "reference:vehicle-definition-detail",
                    manufacturer_slug=mfr_slug,
                    vehicle_model_slug=model_slug,
                    generation_slug=gen_slug,
                    vehicle_definition_slug=matching_vd.slug,
                )

        # Fallback to year-only redirection if year is valid
        if year_str and year_str.isdigit():
            return redirect(
                "reference:model-year-overview",
                manufacturer_slug=mfr_slug,
                vehicle_model_slug=model_slug,
                generation_slug=gen_slug,
                model_year=int(year_str),
            )

        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        active_defs = self.object.vehicle_definitions.filter(
            is_active=True
        ).order_by("model_year", "trim_name", "drivetrain", "engine_name")

        active_years = sorted(list(set(active_defs.values_list("model_year", flat=True))))

        context["vehicle_model"] = self.object.vehicle_model
        context["manufacturer"] = self.object.vehicle_model.manufacturer
        context["active_model_years"] = active_years
        context["active_configurations"] = active_defs
        context["generation_hero_image"] = get_presentation_hero_image_url(self.object.slug)

        # Reserved presentation hooks for future domain model integration
        # (Will require dedicated query/service integration when domains are implemented)
        context["measurements"] = []
        context["camping_builds"] = []

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

        context["model_year"] = model_year
        context["vehicle_definitions"] = active_defs
        context["total_configurations"] = len(active_defs)
        context["trims_dict"] = trims_dict
        context["vehicle_model"] = self.object.vehicle_model
        context["manufacturer"] = self.object.vehicle_model.manufacturer
        return context


class VehicleDefinitionDetailView(DetailView):
    """
    Display one canonical vehicle definition.
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