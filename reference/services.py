"""
Application services for the Reference Domain.

Encapsulates presentation query coordination, filtering semantics,
and multi-domain data aggregation for the Generation Knowledge Hub and Homepage.
Follows the approved wireframes and architectural guidelines.
"""

from collections import Counter
from typing import Any, Dict, List, Optional
from django.db.models import Prefetch

from reference.models import (
    Generation,
    Manufacturer,
    VehicleDefinition,
    VehicleModel,
)


def _label_configuration_choices(configurations):
    """Attach presentation-only labels without collapsing canonical records."""
    choices = list(configurations)
    attributes = [
        lambda vd: vd.trim_name or "Unnamed trim",
        lambda vd: vd.engine_name or "Engine not specified",
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
        VehicleModel.objects.filter(
            is_active=True,
            manufacturer__is_active=True,
            generations__is_active=True,
            generations__vehicle_definitions__is_active=True,
        )
        .distinct()
        .select_related("manufacturer")
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
