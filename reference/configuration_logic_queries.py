"""Read-only queries shared by the Configuration Logic exporters."""
import json
from collections import defaultdict

from django.core.exceptions import ValidationError
from django.db.models import Q

from reference.body_identity import authoring_configuration_key
from reference.models import ImportExecutionReceipt
from reference.specifications.models import SpecificationCatalogueMembership


def sort_by_trim_price(configurations):
    """Keep trims together, ordered by their lowest recorded base MSRP."""
    trim_minimums = {}
    for vehicle in configurations:
        price = vehicle.base_msrp
        if price is not None:
            trim_minimums[vehicle.trim_name] = min(price, trim_minimums.get(vehicle.trim_name, price))

    return sorted(configurations, key=lambda vehicle: (
        vehicle.trim_name not in trim_minimums,
        trim_minimums.get(vehicle.trim_name, 0),
        vehicle.trim_name,
        vehicle.base_msrp is None,
        vehicle.base_msrp or 0,
        vehicle.pk,
    ))


def authored_observations(configurations):
    by_pk = {vehicle.pk: vehicle for vehicle in configurations}
    receipts = ImportExecutionReceipt.objects.filter(
        Q(created_vehicle_definition_id__in=by_pk) | Q(existing_vehicle_definition_id__in=by_pk),
        source_id="human-reviewed-observations",
        execution_outcome__in=("created", "reactivated", "no_op"),
    ).order_by("-executed_at", "-pk")
    matching = {}
    for receipt in receipts:
        pk = receipt.created_vehicle_definition_id or receipt.existing_vehicle_definition_id
        vehicle = by_pk.get(pk)
        if vehicle is None or pk in matching:
            continue
        snapshot = receipt.resolution_snapshot_json
        if (snapshot.get("profile") != "human-body-authoring/1"
                or snapshot.get("vehicle_uuid") != str(vehicle.uuid)):
            continue
        try:
            identity = json.loads(authoring_configuration_key(vehicle))
        except ValidationError:
            continue
        if snapshot.get("identity") == identity:
            matching[pk] = receipt
    return matching


def catalogue_options(configurations):
    memberships = SpecificationCatalogueMembership.objects.filter(
        catalogue_revision__catalogue__vehicle_definition_id__in=[v.pk for v in configurations],
        catalogue_revision__successor__isnull=True,
        catalogue_revision__finding="established",
    ).filter(
        Q(transmission_offering_revision__finding="established")
        | Q(equipment_offering_revision__finding="established",
            equipment_offering_revision__item_revision__kind="factory_package",
            equipment_offering_revision__item_revision__finding="established")
    ).select_related(
        "catalogue_revision__catalogue",
        "transmission_offering_revision__description_revision",
        "equipment_offering_revision__item_revision",
    ).order_by("pk")
    rows = defaultdict(list)
    for member in memberships:
        pk = member.catalogue_revision.catalogue.vehicle_definition_id
        transmission = member.transmission_offering_revision
        if transmission:
            rows[pk].append((
                transmission.description_revision.designation, None, None, None, None,
                f"{transmission.availability.capitalize()} · package pairing unresolved",
                f"Transmission offering {transmission.uuid}",
            ))
        else:
            package = member.equipment_offering_revision
            rows[pk].append((
                None, None, None, None, package.item_revision.name,
                f"{package.assignment.capitalize()} · transmission pairing unresolved",
                f"Equipment offering {package.uuid}",
            ))
    return rows


def option_rows(vehicle, published_rows, receipt):
    rows = list(published_rows)
    if receipt:
        alternatives = receipt.resolution_snapshot_json["observation"]["engine_options"]
        if len(alternatives) > 1:
            note = ("Reviewed output alternative · transmission linkage unresolved"
                    if not vehicle.engine_id else
                    "Reviewed alternative · stored Engine does not establish transmission")
            for engine in alternatives:
                rows.append((
                    None, engine["internal_variant_key"], None, None, None,
                    note,
                    f"Authoring receipt {receipt.pk}",
                ))
    return rows or [(None, None, None, None, None, "Factory options unresolved", None)]
