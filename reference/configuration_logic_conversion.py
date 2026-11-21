"""Verified promotion of the three retained MY2025 Tacoma alternatives."""

from django.core.management.base import CommandError

from reference.admin import factory_body_configuration_label
from reference.configuration_logic_google import entered
from reference.configuration_logic_layout import catalog
from reference.models import ImportExecutionReceipt
from reference.transmission import normalize_source_transmission

TACOMA_GENERATION = "d596373d-196b-4dee-82c8-4fbd0cfbfe8f"
SHEET = "MY2025"
APPROVED = {
    "f018b10317df4711a75633ba27b52247": ("8e47e0c3c2284643a8f8f8068ea98aa8", "7547", "6-Spd Man"),
    "924358b38fa242d59b55e05714c8bad3": ("e7ba530ed4384acabe235167e901b912", "7542", "8-Spd Auto"),
    "04e949d1937e4a08b508ed07ce7684a9": ("33dff6f9a2f04c85ac8fd70cbc1eb384", "7544", "8-Spd Auto"),
}


def created_vehicle(pin, revision, row_id, parent_id, code):
    receipt = ImportExecutionReceipt.objects.select_related(
        "created_vehicle_definition__engine", "created_vehicle_definition__generation",
        "created_vehicle_definition__factory_body_configuration__bed_length",
    ).filter(pk=pin["receipt_pk"], created_vehicle_definition_id=pin["vehicle_pk"],
             execution_outcome="created", source_identity_type="model_code", native_identifier=code).first()
    vehicle = receipt.created_vehicle_definition if receipt else None
    snapshot = receipt.resolution_snapshot_json if receipt else {}
    proof = snapshot.get("observation", {}).get("transmission_evidence", {})
    if (vehicle is None or snapshot.get("profile") != "human-body-authoring/2"
            or proof.get("working_revision") != revision or proof.get("row_id") != row_id
            or proof.get("parent_row_id") != parent_id or str(vehicle.uuid) != pin["vehicle_uuid"]
            or receipt.created_vehicle_definition_uuid_snapshot != str(vehicle.uuid)
            or receipt.created_vehicle_definition_slug_snapshot != vehicle.slug
            or str(vehicle.generation.uuid) != TACOMA_GENERATION or vehicle.model_year != 2025
            or vehicle.market != "US" or not vehicle.is_active or vehicle.engine_id is None):
        raise CommandError("Conversion requires the exact B3 creation receipt and current canonical identity.")
    return vehicle


def conversion_edits(state, binding, rows, pins):
    """Derive the only permitted cell edits from the registered source and receipts."""
    try:
        by_id = {pin["row_id"]: pin for pin in pins}
        if (state["generation"] != TACOMA_GENERATION or len(pins) != len(APPROVED)
                or by_id.keys() != APPROVED.keys() or len(binding["rows"]) != 27
                or any(type(pin["vehicle_pk"]) is not int or type(pin["receipt_pk"]) is not int
                       or not isinstance(pin["vehicle_uuid"], str)
                       for pin in pins)):
            raise ValueError
    except (KeyError, TypeError, ValueError) as exc:
        raise CommandError("Conversion requires the three approved Tacoma rows and receipt pins.") from exc

    width = len(rows[binding["header_row"] - 1])
    fields = [field.removeprefix("configuration.") for field, _ in catalog(SHEET)[:width]]
    source = {item["id"]: dict(zip(fields, rows[item["row"] - 1], strict=True)) for item in binding["rows"]}
    parents = {item["id"]: item["parent_id"] for item in binding["rows"]}
    if {key for key, value in parents.items() if value is not None} != APPROVED.keys():
        raise CommandError("Registered alternatives differ from the approved conversion scope.")
    used = {row["pk"] for key, row in source.items() if parents[key] is None}
    if None in used or len(used) != 24:
        raise CommandError("The 24 existing primary rows require distinct canonical PKs.")
    edits = []
    for number, (row_id, before) in enumerate(source.items(), 1):
        after = {**before, "number": number}
        if row_id in APPROVED:
            parent_id, code, transmission = APPROVED[row_id]
            parent = source.get(parent_id)
            if (parents[row_id] != parent_id or not parent or before["alternate_model_code"] != code
                    or before["pk"] != parent["pk"]
                    or normalize_source_transmission(before["transmission"])
                    != normalize_source_transmission(transmission)):
                raise CommandError("Registered source does not match the approved alternative and parent.")
            vehicle = created_vehicle(by_id[row_id], state["working_revision"], row_id, parent_id, code)
            if (vehicle.pk in used or vehicle.trim_name != parent["trim"]
                    or vehicle.drivetrain != parent["drivetrain"]
                    or vehicle.engine.engine_code != parent["engine_code"]
                    or vehicle.engine.internal_variant_key != before["conditional_output"]
                    or vehicle.base_msrp != before["alternate_msrp"] or vehicle.transmission != transmission
                    or vehicle.factory_body_configuration_id is None
                    or factory_body_configuration_label(vehicle.factory_body_configuration) != parent["body"]):
                raise CommandError("Created vehicle differs from the approved standalone configuration.")
            used.add(vehicle.pk)
            for field in ("trim", "body", "cab", "nominal_bed", "drivetrain", "engine_code", "engine", "market"):
                after[field] = parent[field]
            after.update(pk=vehicle.pk, slug=vehicle.slug, model_code=code,
                         engine_variant=before["conditional_output"], base_msrp=before["alternate_msrp"],
                         transmission=transmission, conditional_output=None,
                         alternate_model_code=None, alternate_msrp=None,
                         applicability="Recorded model selection")
        edits.extend({"sheet_id": binding["sheet_id"], "row_id": row_id,
                      "field_id": f"configuration.{field}", "before": old, "value": after[field]}
                     for field, old in before.items()
                     if f"configuration.{field}" in binding["display_order"] and entered(old) != entered(after[field]))
    return edits
