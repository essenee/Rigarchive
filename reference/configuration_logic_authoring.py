"""Read registered B3 factory offers into the reviewed pickup-authoring workflow."""
from decimal import Decimal
import hashlib
import json
from pathlib import Path

from django.conf import settings
from django.core.exceptions import ValidationError

from reference.admin import factory_body_configuration_label
from reference.body_identity import authoring_configuration_key
from reference.configuration_logic_google import read_registry
from reference.configuration_logic_revisions import current_draft, load_layout
from reference.models import Engine, FactoryBodyConfiguration, VehicleDefinition
from reference.powertrain import record_powertrain
from reference.transmission import normalize_source_transmission


def b3_offers(table, binding):
    """Expand only explicitly bound alternatives. Keep Toyota codes as evidence."""
    fields = binding["display_order"]
    headers = table.rows[table.header_row - 1]
    if (binding["header_row"] != table.header_row or len(fields) != len(headers)
            or len(set(fields)) != len(fields)):
        raise ValidationError("MY worksheet does not match its registered field map.")
    parents, codes, seen = {}, set(), set()
    result = []
    for row_binding in binding["rows"]:
        position, row_id = row_binding["row"], row_binding["id"]
        if row_id in seen or not table.header_row < position <= len(table.rows):
            raise ValidationError("Duplicate or invalid working-row identity.")
        seen.add(row_id)
        data = dict(zip((field.removeprefix("configuration.") for field in fields),
                        table.rows[position - 1], strict=True))
        parent_id = row_binding["parent_id"]
        if parent_id is None:
            keys = ("trim", "body", "cab", "nominal_bed", "drivetrain", "market", "engine_code")
            if not all(data.get(key) for key in keys):
                raise ValidationError(f"Row {position} has incomplete factory attributes.")
            if any(data.get(key) is not None for key in ("conditional_output", "alternate_model_code", "alternate_msrp")):
                raise ValidationError(f"Parent row {position} contains alternative claims.")
            share = {key: data[key] for key in keys}
            parents[row_id] = (share, data["number"], data.get("pk"))
            code, price, variant = data.get("model_code"), data.get("base_msrp"), data.get("engine_variant")
        else:
            if parent_id not in parents:
                raise ValidationError(f"Row {position} has an unresolved alternative parent.")
            share, number, pk = parents[parent_id]
            if (data["number"] != number or data.get("pk") != pk
                    or any(data.get(k) is not None for k in (*share, "model_code", "base_msrp",
                                                             "engine_variant", "engine", "slug", "inactive"))):
                raise ValidationError(f"Row {position} contradicts or overrides shared factory attributes.")
            code, price, variant = data.get("alternate_model_code"), data.get("alternate_msrp"), data.get("conditional_output")
        if (not isinstance(code, str) or not code or code in codes or not variant or not data.get("provenance")
                or type(price) not in (int, float) or price < 0 or not Decimal(str(price)).is_finite()):
            raise ValidationError(f"Row {position} has incomplete or duplicate offer evidence.")
        codes.add(code)
        result.append({**share, "code": code, "price": price, "variant": variant,
                       "transmission": normalize_source_transmission(data.get("transmission")),
                       "row": position, "row_id": row_id, "parent_id": parent_id,
                       "provenance": data["provenance"], "recorded_engine_name": data.get("engine")})
    if {r["row"] for r in result} != {i for i, row in enumerate(
            table.rows[table.header_row:], table.header_row + 1) if any(value is not None for value in row)}:
        raise ValidationError("Some populated rows lack registered working-row bindings.")
    return result


def prepare_b3_authoring(generation, year, evidence_reference, evidence_hash):
    """Construct exact no-write proposals and evidence observations from reviewed inputs.

    The retained research mapping supplies the independent per-offer assertions.
    This returns input to human-body-authoring/2, not permission to write.
    """
    root = Path(settings.BASE_DIR).resolve()
    evidence_path = (root / evidence_reference).resolve()
    if not evidence_path.is_relative_to(root):
        raise ValidationError("B3 evidence must be retained within the repository.")
    raw = evidence_path.read_bytes()
    if "sha256:" + hashlib.sha256(raw).hexdigest() != evidence_hash:
        raise ValidationError("Reviewed B3 evidence changed.")
    research = json.loads(raw)
    path = root / ".configuration-logic" / f"{generation.uuid}.json"
    state = read_registry(path, str(generation.uuid))
    layout = load_layout(state, path)
    if not layout:
        raise ValidationError("B3 authoring requires an enrolled, registered working revision.")
    name = f"MY{year}"
    draft = current_draft(generation, path, state)
    table = next((t for t in draft.sheets if t.name == name), None)
    if table is None:
        raise ValidationError("Registered model-year worksheet is unavailable.")
    offers = b3_offers(table, layout["sheets"][name])
    evidence = {item["code"]: item for item in research["evidence"]}
    if len(evidence) != len(research["evidence"]) or set(evidence) != {offer["code"] for offer in offers}:
        raise ValidationError("The reviewed evidence does not cover exactly the registered offers.")
    bodies = list(FactoryBodyConfiguration.objects.filter(generation=generation).select_related("bed_length"))
    engines = list(Engine.objects.available_for_manufacturer(generation.vehicle_model.manufacturer_id))
    proposals, observations = [], []
    for offer in offers:
        fact = evidence[offer["code"]]
        # Transmission is retained in the Toyota evidence map as 6MT or 8AT.
        explicit = {"6MT": "6-spd Man", "8AT": "8-spd Auto"}.get(fact["transmission"])
        if not explicit:
            explicit = normalize_source_transmission(fact["transmission"])
        actual = (offer["trim"], offer["cab"], offer["nominal_bed"], offer["drivetrain"],
                  offer["variant"], offer["price"], offer["transmission"])
        if (offer["market"] != "United States" or actual !=
                (fact["grade"], fact["cab"], f"{fact['bed']}-ft", fact["drivetrain"],
                 fact["variant"], fact["msrp"], explicit)
                or not all(fact.get(k) for k in ("code_evidence", "output_evidence", "price_evidence"))):
            raise ValidationError(f"Toyota offer {offer['code']} differs from retained factory evidence.")
        body_links = [body for body in bodies if body.bed_length_id and body.bed_length.designation == offer["nominal_bed"]
                      and body.get_cab_configuration_display() == offer["cab"]
                      and factory_body_configuration_label(body) == offer["body"]]
        engine_links = [engine for engine in engines if engine.engine_code == offer["engine_code"]
                        and engine.internal_variant_key == offer["variant"]]
        if len(body_links) != 1 or len(engine_links) != 1 or (
            offer["recorded_engine_name"] and offer["recorded_engine_name"] != engine_links[0].name
        ):
            raise ValidationError(f"Toyota offer {offer['code']} has ambiguous or missing registry references.")
        body, engine = body_links[0], engine_links[0]
        vehicle = VehicleDefinition(
            generation=generation, model_year=year, market="US", trim_name=offer["trim"],
            drivetrain=offer["drivetrain"], factory_body_configuration=body, engine=engine, engine_name=engine.name,
            transmission=offer["transmission"], base_msrp=Decimal(str(offer["price"])).quantize(Decimal(".01")),
            **record_powertrain(engine),
        )
        proposals.append((vehicle, None))
        observations.append({
            "identity": authoring_configuration_key(vehicle), "engine_name": engine.name,
            "base_msrp": str(vehicle.base_msrp),
            "selected_toyota_model": {"code": offer["code"], "variant": offer["variant"],
                                     "transmission": offer["transmission"]},
            "transmission_evidence": {"working_revision": state["working_revision"], "row_id": offer["row_id"],
                                      "parent_row_id": offer["parent_id"], "source_evidence": fact,
                                      "reference": evidence_reference, "sha256": evidence_hash},
            "engine_options": [{"pk": engine.pk, "uuid": str(engine.uuid), "name": engine.name,
                                "engine_code": engine.engine_code, "internal_variant_key": engine.internal_variant_key,
                                "powertrain": record_powertrain(engine)}],
        })
    if len({row["identity"] for row in observations}) != len(proposals):
        raise ValidationError("Evidence contains duplicate canonical factory configurations.")
    return proposals, {"record_type": "human-reviewed-factory-observations", "configurations": observations}
