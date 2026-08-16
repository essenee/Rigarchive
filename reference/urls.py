from django.urls import path

from .views import (
    GenerationDetailView,
    ManufacturerDetailView,
    ManufacturerListView,
    ModelYearOverviewView,
    VehicleDefinitionDetailView,
    VehicleModelDetailView,
)

app_name = "reference"

urlpatterns = [
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