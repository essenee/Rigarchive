from django.shortcuts import get_object_or_404
from django.views.generic import TemplateView

from reference.models import Generation

from .models import MeasurementResult


class GenerationMeasurementsView(TemplateView):
    """
    Public view presenting physical vehicle measurements for a specific Generation.
    """

    template_name = "measurements/generation_measurements.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        manufacturer_slug = kwargs.get("manufacturer_slug")
        vehicle_model_slug = kwargs.get("vehicle_model_slug")
        generation_slug = kwargs.get("generation_slug")

        generation = get_object_or_404(
            Generation,
            vehicle_model__manufacturer__slug=manufacturer_slug,
            vehicle_model__slug=vehicle_model_slug,
            slug=generation_slug,
            is_active=True,
            vehicle_model__is_active=True,
            vehicle_model__manufacturer__is_active=True,
        )

        vehicle_model = generation.vehicle_model
        manufacturer = vehicle_model.manufacturer

        results = (
            MeasurementResult.objects.filter(
                generation=generation,
                is_active=True,
            )
            .select_related("definition", "generation__vehicle_model__manufacturer")
            .prefetch_related("conditions__state__feature")
            .order_by("definition__name", "id")
        )

        context.update(
            {
                "generation": generation,
                "vehicle_model": vehicle_model,
                "manufacturer": manufacturer,
                "results": results,
            }
        )

        return context
