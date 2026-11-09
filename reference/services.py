"""
Application services for the Reference Domain.

Encapsulates presentation query coordination, filtering semantics,
and multi-domain data aggregation for the Generation Knowledge Hub and Homepage.
Follows the approved wireframes and architectural guidelines.
"""

from collections import Counter
from dataclasses import dataclass
from urllib.parse import urlencode
from typing import Any, Dict, List, Optional
from django.db.models import Prefetch, Q, prefetch_related_objects
from django.http import Http404
from django.shortcuts import get_object_or_404
from django.urls import reverse

from reference.powertrain import engine_label
from reference.models import (
    Generation,
    Manufacturer,
    VehicleDefinition,
    VehicleModel,
)

AUTO_SELECT_TRIM_THRESHOLD = 10


@dataclass(frozen=True)
class VehicleContext:
    """Request-local identity from a validated route object, never session state."""

    manufacturer: Manufacturer
    vehicle_model: VehicleModel
    generation: Generation | None = None
    vehicle_definition: VehicleDefinition | None = None


def get_vehicle_context(route_object):
    """Build context from an already resolved object and check active ancestry.

    No URL parsing, year/trim inference, session access, or persistence occurs.
    Views remain responsible for matching the object to their route kwargs.
    """
    definition = route_object if isinstance(route_object, VehicleDefinition) else None
    generation = definition.generation if definition else (
        route_object if isinstance(route_object, Generation) else None
    )
    model = generation.vehicle_model if generation else route_object
    if not isinstance(model, VehicleModel):
        raise TypeError("Vehicle context requires a model, Generation or exact configuration.")
    manufacturer = model.manufacturer
    if not all(obj.is_active for obj in (manufacturer, model, generation, definition) if obj is not None):
        raise Http404("Vehicle context is unavailable.")
    return VehicleContext(manufacturer, model, generation, definition)


def get_active_vehicle_model(manufacturer_slug, vehicle_model_slug):
    """Resolve a model under its active manufacturer without requiring definitions."""
    return get_object_or_404(
        VehicleModel.objects.select_related("manufacturer"),
        slug=vehicle_model_slug, manufacturer__slug=manufacturer_slug,
        is_active=True, manufacturer__is_active=True,
    )


def _vehicle_name_filter(query, *, model_field="name", manufacturer_field="manufacturer__name"):
    return Q(**{f"{model_field}__icontains": query}) | Q(**{f"{manufacturer_field}__icontains": query})


def discover_vehicle_models(query="", manufacturer_slug=None, *, populated_only=False):
    """Shared name search with an explicit legacy canonical-coverage policy."""
    models = VehicleModel.objects.filter(is_active=True, manufacturer__is_active=True)
    if populated_only:
        models = models.filter(generations__is_active=True, generations__vehicle_definitions__is_active=True)
    if manufacturer_slug:
        models = models.filter(manufacturer__slug=manufacturer_slug)
    query = query.strip()
    if query:
        models = models.filter(_vehicle_name_filter(query))
    return models.select_related("manufacturer").distinct()


def discover_manufacturers(query="", manufacturer_slug=None, *, populated_only=False):
    """Group eligible models, preserving legacy populated-directory grouping."""
    models = discover_vehicle_models(query, manufacturer_slug, populated_only=populated_only)
    if populated_only:
        # Preserve the legacy directory's manufacturer eligibility independently
        # of the filtered model prefetch (including empty matching groups).
        manufacturers = Manufacturer.objects.filter(
            is_active=True, vehicle_models__is_active=True,
            vehicle_models__generations__is_active=True,
            vehicle_models__generations__vehicle_definitions__is_active=True,
        )
        if query.strip():
            manufacturers = manufacturers.filter(_vehicle_name_filter(
                query.strip(), model_field="vehicle_models__name", manufacturer_field="name",
            ))
    else:
        manufacturers = Manufacturer.objects.filter(is_active=True, vehicle_models__in=models)
    if manufacturer_slug:
        manufacturers = manufacturers.filter(slug=manufacturer_slug)
    return manufacturers.distinct().prefetch_related(
        Prefetch("vehicle_models", queryset=models, to_attr="active_vehicle_models")
    )


@dataclass(frozen=True)
class VehicleDestination:
    token: str
    label: str
    route_name: str
    pattern: str
    implemented: bool = False


# Contracts only: deferred routes MUST NOT be registered before their views exist.
VEHICLE_DESTINATIONS = (
    VehicleDestination("generations", "Generations", "reference:vehicle-model-detail",
                       "/vehicles/<manufacturer_slug>/<vehicle_model_slug>/", True),
    VehicleDestination("builds", "Builds", "vehicle-builds-entry",
                       "/explore/vehicles/<manufacturer_slug>/<vehicle_model_slug>/builds/"),
    VehicleDestination("maintenance", "Maintenance", "vehicle-maintenance-entry",
                       "/explore/vehicles/<manufacturer_slug>/<vehicle_model_slug>/maintenance/"),
    VehicleDestination("measurements", "Measurements", "measurements:model-measurements",
                       "/explore/vehicles/<manufacturer_slug>/<vehicle_model_slug>/measurements/"),
    VehicleDestination("full-specs", "Full Specs", "reference:model-full-specs",
                       "/explore/vehicles/<manufacturer_slug>/<vehicle_model_slug>/full-specs/"),
)


def get_vehicle_destination(token="generations"):
    """Reject arbitrary targets, including empty tokens and redirect URLs."""
    for destination in VEHICLE_DESTINATIONS:
        if destination.token == token:
            return destination
    raise ValueError("Choose a valid destination: Generations, Builds, Maintenance, Measurements or Full Specs.")


def resolve_vehicle_destination(vehicle_model, token="generations"):
    """Return a real URL only for implemented contracts; None means pending."""
    get_vehicle_context(vehicle_model)
    destination = get_vehicle_destination(token)
    if not destination.implemented:
        return None
    return reverse(destination.route_name, kwargs={
        "manufacturer_slug": vehicle_model.manufacturer.slug,
        "vehicle_model_slug": vehicle_model.slug,
    })


def vehicle_selector_url(*, destination="generations", query="", manufacturer="", model=""):
    """Generate selector links from allowlisted intent, never user-supplied paths."""
    get_vehicle_destination(destination)
    params = {"destination": destination}
    if query:
        params["q"] = query
    if manufacturer:
        params["manufacturer"] = manufacturer
    if model:
        params["model"] = model
    return reverse("reference:vehicle-selector") + "?" + urlencode(params)


def get_vehicle_selector_context(*, query="", manufacturer_slug="", model_slug="", token="generations"):
    """Coordinate selector results and safe continuation links without writes."""
    destination = get_vehicle_destination(token)
    manufacturer = (
        get_object_or_404(Manufacturer, slug=manufacturer_slug, is_active=True)
        if manufacturer_slug else None
    )
    if model_slug and manufacturer is None:
        raise ValueError("Choose a manufacturer before selecting a model.")
    selected_model = get_active_vehicle_model(manufacturer_slug, model_slug) if model_slug else None
    groups = []
    for group in discover_manufacturers(query, manufacturer_slug):
        choices = []
        for model in group.active_vehicle_models:
            url = resolve_vehicle_destination(model, token)
            choices.append({
                "model": model,
                "url": url or vehicle_selector_url(
                    destination=token, query=query, manufacturer=group.slug, model=model.slug,
                ),
            })
        groups.append({
            "manufacturer": group,
            "filter_url": vehicle_selector_url(destination=token, query=query, manufacturer=group.slug),
            "choices": choices,
        })
    # Canonical Generation chronology is start_year. One windowed prefetch
    # retrieves only the newest active row per model, independent of coverage.
    models = [choice["model"] for group in groups for choice in group["choices"]]
    prefetch_related_objects(models, Prefetch(
        "generations", queryset=Generation.objects.filter(is_active=True).order_by("-start_year")[:1],
        to_attr="selector_latest_generations",
    ))
    for group in groups:
        for choice in group["choices"]:
            choice["generation"] = next(iter(choice["model"].selector_latest_generations), None)
    return {
        "groups": groups, "destination": destination,
        "selected_manufacturer": manufacturer, "selected_model": selected_model,
        "selected_destination_url": resolve_vehicle_destination(selected_model, token) if selected_model else None,
        "clear_manufacturer_url": vehicle_selector_url(destination=token, query=query),
        "reset_selector_url": vehicle_selector_url(destination=token),
        "manufacturer_filters": [
            {"manufacturer": item, "url": vehicle_selector_url(
                destination=token, query=query, manufacturer=item.slug,
            )}
            for item in Manufacturer.objects.filter(
                is_active=True, vehicle_models__is_active=True,
            ).distinct()
        ],
    }


def _label_configuration_choices(configurations):
    """Attach presentation-only labels without collapsing canonical records."""
    choices = list(configurations)
    attributes = [
        lambda vd: vd.trim_name or "Unnamed trim",
        lambda vd: engine_label(vd, short=True),
        lambda vd: vd.get_drivetrain_display(),
    ]
    varying = [attribute for attribute in attributes if len({attribute(vd) for vd in choices}) > 1]
    # A single choice still needs a useful description, even with no variation.
    fields = varying or attributes[1:]
    labels = [" · ".join(attribute(vd) for attribute in fields) for vd in choices]
    counts = Counter(labels)
    labels = [f"{label} · {vd.get_market_display()} ({vd.market})" if counts[label] > 1 else label
              for vd, label in zip(choices, labels)]
    counts = Counter(labels)
    for vd, label in zip(choices, labels):
        vd.choice_label = f"{label} · {vd.slug}" if counts[label] > 1 else label
    return choices


def get_generation_hub_context(
    generation: Generation,
    model_year: Optional[Any] = None,
    trim_name: Optional[str] = None,
    config_slug: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Assemble the complete context for the Generation Knowledge Hub.

    Filtering semantics:
    - Default (unfiltered): Displays generation-wide context, generation-wide
      physical measurements, statistics, and full list of available trims and powertrains.
    - Model Year filter: Refines available configurations and trims to that specific year.
      Generation-wide measurements remain applicable and visible.
    - Trim filter: Refines configurations to a specific manufacturer-marketed trim.
    - Exact Configuration filter: Refines to a single canonical VehicleDefinition.
    """
    # 1. Retrieve all active canonical configurations for this generation
    active_defs = (
        generation.vehicle_definitions.filter(is_active=True)
        .select_related("generation__vehicle_model__manufacturer")
        .order_by("-model_year", "trim_name", "drivetrain", "engine_name", "market", "slug")
    )

    # Resolve explicit filters before deriving their dependent choices.
    active_model_years = sorted(set(active_defs.values_list("model_year", flat=True)), reverse=True)
    active_model_years_asc = sorted(active_model_years)
    selected_year = None
    filter_errors = []
    if model_year not in (None, ""):
        try:
            year = int(model_year)
        except (ValueError, TypeError):
            year = None
        if year in active_model_years:
            selected_year = year
        else:
            filter_errors.append("The requested model year is unavailable. Showing all years.")

    candidate = active_defs.filter(slug=config_slug).first() if config_slug else None
    # Only a configuration-only URL may infer a year. An explicit blank year
    # means All Years; invalid or mismatched years must never be overridden.
    if candidate is not None and model_year is None:
        selected_year = candidate.model_year

    year_filtered_defs = active_defs.filter(model_year=selected_year) if selected_year is not None else active_defs
    available_trims = sorted(set(year_filtered_defs.values_list("trim_name", flat=True))) if selected_year is not None else []
    selected_trim = None
    if trim_name is not None:
        # Empty string is an actual unnamed trim, distinct from no trim filter.
        if selected_year is not None and trim_name in available_trims:
            selected_trim = trim_name
        else:
            filter_errors.append("The requested trim is unavailable for this selection.")

    selected_config = None
    if config_slug:
        if (candidate is not None and selected_year == candidate.model_year
                and not filter_errors
                and (selected_trim is None or candidate.trim_name == selected_trim)):
            selected_config = candidate
            selected_trim = candidate.trim_name
        else:
            filter_errors.append("The requested configuration is unavailable for this selection.")

    # Resolve explicit URL state first, including configuration-only deep links.
    # Invalid selections retain their existing unfiltered/error fallback.
    if (selected_year is not None and selected_trim is None
            and trim_name is None and not filter_errors and available_trims
            and year_filtered_defs.count() > AUTO_SELECT_TRIM_THRESHOLD):
        selected_trim = available_trims[0]

    displayed_defs = year_filtered_defs
    if selected_trim is not None:
        displayed_defs = displayed_defs.filter(trim_name=selected_trim)
    if selected_config is not None:
        displayed_defs = displayed_defs.filter(pk=selected_config.pk)

    # 9. Group displayed configurations by trim name
    trims_dict: Dict[str, List[VehicleDefinition]] = {}
    for vd in displayed_defs:
        trim_key = vd.trim_name or "Base / Standard"
        if trim_key not in trims_dict:
            trims_dict[trim_key] = []
        trims_dict[trim_key].append(vd)

    # 10. Generation statistics
    # Wireframe shows: Model Years, Configurations, Engine Options, Transmissions
    # Note: Transmission is not a field in VehicleDefinition, so we show Drivetrains
    # or omit transmission per instruction ("If a statistic cannot be calculated reliably, omit it").
    distinct_engines = sorted(
        list(
            set(
                vd.engine_name
                for vd in active_defs
                if vd.engine_name
            )
        )
    )
    distinct_drivetrains = sorted(
        list(
            set(
                vd.drivetrain
                for vd in active_defs
                if vd.drivetrain
            )
        )
    )

    stats = {
        "model_years_count": len(active_model_years),
        "configurations_count": active_defs.count(),
        "engine_options_count": len(distinct_engines),
        "drivetrains_count": len(distinct_drivetrains),
    }

    # 11. Multi-domain query: Physical Measurements
    generation_measurements: List[Any] = []
    has_measurements = False
    try:
        from measurements.models import MeasurementResult

        measurement_qs = (
            MeasurementResult.objects.filter(
                generation=generation,
                is_active=True,
            )
            .select_related("definition")
            .prefetch_related("conditions__state__feature")
            .order_by("definition__name", "value", "pk")
        )
        generation_measurements = list(measurement_qs)
        has_measurements = len(generation_measurements) > 0
    except ImportError:
        pass

    # A year or trim is never silently promoted to an exact configuration.
    full_specs_url = selected_config.get_absolute_url() if selected_config is not None else None
    model_year_url = None
    if selected_year is not None:
        from django.urls import reverse
        model_year_url = reverse("reference:model-year-overview", kwargs={
            "manufacturer_slug": generation.vehicle_model.manufacturer.slug,
            "vehicle_model_slug": generation.vehicle_model.slug,
            "generation_slug": generation.slug,
            "model_year": selected_year,
        })

    configuration_choices = _label_configuration_choices(year_filtered_defs) if selected_year is not None else []
    browser_defs = year_filtered_defs.filter(trim_name=selected_trim) if selected_trim is not None else year_filtered_defs
    # Keep sibling choices available after exact selection, with a visible marker.
    browser_choices = _label_configuration_choices(browser_defs) if selected_year is not None else []

    filter_active = (
        (selected_year is not None)
        or (selected_trim is not None)
        or (selected_config is not None)
    )

    return {
        "generation": generation,
        "vehicle_model": generation.vehicle_model,
        "manufacturer": generation.vehicle_model.manufacturer,
        "active_model_years": active_model_years,
        "active_model_years_asc": active_model_years_asc,
        "selected_year": selected_year,
        "selected_trim": selected_trim,
        "selected_config": selected_config,
        "available_trims": available_trims,
        "active_configurations": active_defs,
        "year_filtered_defs": year_filtered_defs,
        "displayed_configurations": displayed_defs,
        "trims_dict": trims_dict,
        "stats": stats,
        "measurements": generation_measurements,
        "has_measurements": has_measurements,
        "filter_active": filter_active,
        "full_specs_url": full_specs_url,
        "model_year_url": model_year_url,
        "filter_errors": filter_errors,
        "trim_filter_active": selected_trim is not None,
        "configuration_choices": configuration_choices,
        "configuration_browser_choices": browser_choices,
        "total_generation_configs": active_defs.count(),
        "filtered_configs_count": displayed_defs.count(),
    }


def get_homepage_context(request: Optional[Any] = None) -> Dict[str, Any]:
    """
    Assemble the context for the approved RigArchive homepage.

    Surfaces:
    - Featured vehicle platform cards (Toyota 4Runner, Tacoma, VW Touareg).
    - Hero photograph and schematic metadata.
    - Session-tracked recently viewed generations.
    """
    from reference.views import get_presentation_hero_image_url

    # Query active vehicle models populated with canonical definitions
    models_qs = (
        discover_vehicle_models(populated_only=True)
        .prefetch_related(
            Prefetch(
                "generations",
                queryset=Generation.objects.filter(
                    is_active=True,
                    vehicle_definitions__is_active=True,
                ).distinct().order_by("generation_number", "start_year"),
                to_attr="active_generations",
            )
        )
    )

    featured_models = []
    # Preferred representative generation for card thumbnail
    preferred_gens = {
        "4runner": "fifth-generation",
        "tacoma": "third-generation",
        "touareg": "first-generation",
    }

    for vm in models_qs:
        generations = getattr(vm, "active_generations", [])
        if not generations:
            continue

        configs_count = VehicleDefinition.objects.filter(
            generation__in=generations,
            is_active=True,
        ).count()

        years_start = min(g.start_year for g in generations)
        has_present = any(g.end_year is None for g in generations)
        if has_present:
            year_span = f"{years_start}–present"
        else:
            years_end = max((g.end_year or years_start) for g in generations)
            year_span = f"{years_start}–{years_end}"

        pref_slug = preferred_gens.get(vm.slug)
        hero_url = ""
        if pref_slug:
            hero_url = get_presentation_hero_image_url(
                vm.manufacturer.slug, vm.slug, pref_slug
            )
        if not hero_url and generations:
            hero_url = get_presentation_hero_image_url(generations[-1])

        featured_models.append({
            "model": vm,
            "manufacturer": vm.manufacturer,
            "generations_count": len(generations),
            "configs_count": configs_count,
            "year_span": year_span,
            "hero_image_url": hero_url,
        })

    # Sort featured models so 4Runner, Tacoma, Touareg match the approved wireframe
    slug_order = {"4runner": 0, "tacoma": 1, "touareg": 2}
    featured_models.sort(key=lambda x: slug_order.get(x["model"].slug, 99))

    # Hero featured generation asset lookup (Toyota 4Runner 5th Gen)
    hero_generation_url = get_presentation_hero_image_url(
        "toyota", "4runner", "fifth-generation"
    )

    # Recently Viewed from session
    recently_viewed: List[Dict[str, Any]] = []
    if request and hasattr(request, "session"):
        recently_viewed = request.session.get("recently_viewed_generations", [])

    return {
        "featured_platforms": featured_models,
        "hero_image_url": hero_generation_url,
        "recently_viewed": recently_viewed,
    }


def record_recently_viewed_generation(request: Any, generation: Generation) -> None:
    """
    Record a generation visit in the user's session history for the Recently Viewed panel.
    Caps at 5 items. Avoids any persistent database overhead.
    """
    if not request or not hasattr(request, "session"):
        return

    from reference.views import get_presentation_hero_image_url

    history = request.session.get("recently_viewed_generations", [])
    gen_url = generation.get_absolute_url()

    # Filter out if already present so it bubbles to top
    history = [item for item in history if item.get("url") != gen_url]

    year_str = (
        f"{generation.start_year}–{generation.end_year}"
        if generation.end_year
        else f"{generation.start_year}–present"
    )

    hero_url = get_presentation_hero_image_url(generation)

    history.insert(
        0,
        {
            "manufacturer_name": generation.vehicle_model.manufacturer.name,
            "model_name": generation.vehicle_model.name,
            "generation_name": generation.name,
            "generation_number": generation.generation_number,
            "year_span": year_str,
            "url": gen_url,
            "image_url": hero_url,
        },
    )

    request.session["recently_viewed_generations"] = history[:5]
    request.session.modified = True


def get_full_specifications_context(
    vehicle_definition: VehicleDefinition,
) -> Dict[str, Any]:
    """
    Assemble the complete context for the Full Specifications page.
    """
    generation = vehicle_definition.generation
    vehicle_model = generation.vehicle_model
    manufacturer = vehicle_model.manufacturer

    # Sibling trims from the same generation and model year
    sibling_configs = (
        generation.vehicle_definitions.filter(
            model_year=vehicle_definition.model_year,
            is_active=True,
        )
        .exclude(pk=vehicle_definition.pk)
        .order_by("trim_name", "drivetrain", "engine_name")
    )

    # Applicable physical measurements
    applicable_measurements = []
    conditional_measurements = []
    try:
        from measurements.models import MeasurementResult

        meas_qs = (
            MeasurementResult.objects.filter(
                generation=generation,
                is_active=True,
            )
            .select_related("definition")
            .prefetch_related("conditions__state__feature")
            .order_by("definition__name", "value", "pk")
        )
        results = list(meas_qs)
        applicable_measurements = [m for m in results if m.is_generation_wide]
        conditional_measurements = [m for m in results if not m.is_generation_wide]
    except ImportError:
        pass

    receipt = (
        vehicle_definition.creation_receipts.first()
        or vehicle_definition.matched_receipts.first()
    )

    return {
        "vehicle_definition": vehicle_definition,
        "generation": generation,
        "vehicle_model": vehicle_model,
        "manufacturer": manufacturer,
        "sibling_configs": sibling_configs,
        "applicable_measurements": applicable_measurements,
        "conditional_measurements": conditional_measurements,
        "receipt": receipt,
    }
