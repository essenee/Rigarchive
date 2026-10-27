from django.urls import include, path

from .views import (
    vehicle_selector,
    GenerationDetailView,
    ManufacturerDetailView,
    ManufacturerListView,
    ModelYearOverviewView,
    VehicleDefinitionDetailView,
    VehicleModelDetailView,
)

app_name = "reference"

vehicle_patterns = [
    path(
        "",
        ManufacturerListView.as_view(),
        name="manufacturer-list",
    ),
    path(
        "<slug:manufacturer_slug>/",
        ManufacturerDetailView.as_view(),
        name="manufacturer-detail",
    ),
    path(
        "<slug:manufacturer_slug>/<slug:vehicle_model_slug>/",
        VehicleModelDetailView.as_view(),
        name="vehicle-model-detail",
    ),
    path(
        (
            "<slug:manufacturer_slug>/"
            "<slug:vehicle_model_slug>/"
            "<slug:generation_slug>/"
        ),
        GenerationDetailView.as_view(),
        name="generation-detail",
    ),
    path(
        (
            "<slug:manufacturer_slug>/"
            "<slug:vehicle_model_slug>/"
            "<slug:generation_slug>/"
            "<int:model_year>/"
        ),
        ModelYearOverviewView.as_view(),
        name="model-year-overview",
    ),
    path(
        (
            "<slug:manufacturer_slug>/"
            "<slug:vehicle_model_slug>/"
            "<slug:generation_slug>/"
            "<slug:vehicle_definition_slug>/"
        ),
        VehicleDefinitionDetailView.as_view(),
        name="vehicle-definition-detail",
    ),
]

# A single reference namespace preserves existing reversals and adds a selector
# outside the manufacturer slug tree. Deferred explore views are not registered.
urlpatterns = [
    path("select-vehicle/", vehicle_selector, name="vehicle-selector"),
    path("vehicles/", include(vehicle_patterns)),
]
