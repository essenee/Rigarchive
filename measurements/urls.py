from django.urls import path

from .views import GenerationMeasurementsView

app_name = "measurements"

urlpatterns = [
    path(
        (
            "<slug:manufacturer_slug>/"
            "<slug:vehicle_model_slug>/"
            "<slug:generation_slug>/"
            "measurements/"
        ),
        GenerationMeasurementsView.as_view(),
        name="generation-measurements",
    ),
]
