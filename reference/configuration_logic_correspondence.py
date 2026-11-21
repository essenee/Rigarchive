"""Receipt-backed completion of empty standalone CL correspondences."""
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.core.management.base import CommandError

from reference.admin import factory_body_configuration_label
from reference.configuration_logic_layout import CONFIG_FIELDS
from reference.models import ImportExecutionReceipt
from reference.transmission import normalize_source_transmission


def correspondence_edits(state, layout, tables, pins):
    seen_rows, seen_vehicles, edits = set(), set(), []
    try:
        for pin in pins:
            name, row_id, receipt_pk = pin["sheet"], pin["row_id"], pin["receipt_pk"]
            if not name.startswith("MY") or not name[2:].isdigit() or type(receipt_pk) is not int:
                raise ValueError
            binding = layout["sheets"][name]
            row, = [row for row in binding["rows"] if row["id"] == row_id]
            source = dict(zip(CONFIG_FIELDS, tables[name][row["row"] - 1]))
            if (row["parent_id"] or (name, row_id) in seen_rows
                    or source["pk"] is not None or source["slug"] is not None
                    or not source["model_code"] or source["market"] != "United States"):
                raise ValueError
            receipt = ImportExecutionReceipt.objects.select_related(
                "created_vehicle_definition__generation", "created_vehicle_definition__engine",
                "created_vehicle_definition__factory_body_configuration__bed_length",
            ).get(pk=receipt_pk, execution_outcome="created", source_identity_type="model_code",
                  native_identifier=source["model_code"])
            vehicle = receipt.created_vehicle_definition
            snapshot = receipt.resolution_snapshot_json
            proof = snapshot.get("observation", {}).get("transmission_evidence", {})
            if (not vehicle or vehicle.pk in seen_vehicles or snapshot.get("profile") != "human-body-authoring/2"
                    or proof.get("working_revision") != state["working_revision"] or proof.get("row_id") != row_id
                    or proof.get("parent_row_id") is not None
                    or receipt.created_vehicle_definition_pk_snapshot != vehicle.pk
                    or receipt.created_vehicle_definition_uuid_snapshot != str(vehicle.uuid)
                    or receipt.created_vehicle_definition_slug_snapshot != vehicle.slug
                    or str(vehicle.generation.uuid) != state["generation"] or vehicle.model_year != int(name[2:])
                    or vehicle.market != "US" or not vehicle.is_active or not vehicle.engine_id
                    or vehicle.trim_name != source["trim"] or vehicle.drivetrain != source["drivetrain"]
                    or vehicle.engine.engine_code != source["engine_code"]
                    or vehicle.engine.internal_variant_key != source["engine_variant"]
                    or vehicle.transmission != normalize_source_transmission(source["transmission"])
                    or vehicle.base_msrp != Decimal(str(source["base_msrp"]))
                    or (factory_body_configuration_label(vehicle.factory_body_configuration)
                        if vehicle.factory_body_configuration_id else None) != source["body"]):
                raise ValueError
            seen_rows.add((name, row_id))
            seen_vehicles.add(vehicle.pk)
            values = {"pk": vehicle.pk, "slug": vehicle.slug}
            for field, suffix in (
                ("applicability", "; no matching VehicleDefinition"),
                ("provenance", "; Evidence gap: No canonical PK correspondence"),
            ):
                if (source[field] or "").endswith(suffix):
                    values[field] = source[field].removesuffix(suffix)
            edits.extend({"sheet_id": binding["sheet_id"], "row_id": row_id,
                          "field_id": f"configuration.{field}", "before": source[field], "value": value}
                         for field, value in values.items())
    except (KeyError, ValueError, TypeError, ArithmeticError, ValidationError,
            ImportExecutionReceipt.DoesNotExist) as exc:
        raise CommandError("Correspondence requires an empty standalone row and its exact B3 creation receipt.") from exc
    return edits
