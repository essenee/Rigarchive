from django.views.generic import DetailView, ListView

from .models import Generation, Manufacturer, VehicleDefinition, VehicleModel


class ManufacturerListView(ListView):
    """
    Display active vehicle manufacturers in the Reference Domain.
    """

    model = Manufacturer
    template_name = "reference/manufacturer_list.html"
    context_object_name = "manufacturers"

    def get_queryset(self):
        return Manufacturer.objects.filter(is_active=True)


class ManufacturerDetailView(DetailView):
    """
    Display one manufacturer and its active vehicle models.
    """

    model = Manufacturer
    template_name = "reference/manufacturer_detail.html"
    context_object_name = "manufacturer"
    slug_url_kwarg = "manufacturer_slug"

    def get_queryset(self):
        return Manufacturer.objects.filter(is_active=True).prefetch_related(
            "vehicle_models"
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["vehicle_models"] = self.object.vehicle_models.filter(
            is_active=True
        )
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
        context["generations"] = self.object.generations.filter(
            is_active=True
        )
        return context


class GenerationDetailView(DetailView):
    """
    Display one generation and its active vehicle definitions.
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
        context["vehicle_definitions"] = (
            self.object.vehicle_definitions.filter(is_active=True)
        )
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