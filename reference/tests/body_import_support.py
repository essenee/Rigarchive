"""Synthetic RA-049 source evidence in temporary roots, never real review findings."""
from copy import deepcopy
import csv
from datetime import datetime, timezone
import io
import json
from pathlib import Path
import shutil
from tempfile import TemporaryDirectory
from uuid import uuid4

from django.test import override_settings

from reference import candidate_v3 as wire
from reference.body_identity import body_preimage, canonical_json, semantic_digest
from reference.ingestion.generation_correspondence import publish_correspondence, digest
from reference.ingestion.importing.body_identity import INVENTORY_ROOT, INVENTORIES, SCOPE, Release, byte_hash
from reference.models import Manufacturer, VehicleModel, Generation, FactoryBodyConfiguration

REPOSITORY = Path(__file__).resolve().parents[2]


class BodyImportFixture:
    def __init__(self, *, registry=False):
        self.directory = TemporaryDirectory(prefix="ra049-isolated-")
        self.root = Path(self.directory.name)
        self.settings = override_settings(BASE_DIR=self.root)
        self.settings.enable()
        for name in INVENTORIES:
            p = self.root / (INVENTORY_ROOT + name)
            p.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(REPOSITORY / (INVENTORY_ROOT + name), p)
        rows = [r for r in csv.DictReader((self.root / (INVENTORY_ROOT + "candidate_inventory.csv")).open()) if r["status"] == "ACTIVE_CONSUMER"]
        audit = {r["candidate_id"]: r for r in csv.DictReader((self.root / (INVENTORY_ROOT + "trim_normalization_audit.csv")).open())}
        maker = Manufacturer.objects.create(name="Jeep")
        model = VehicleModel.objects.create(name="Wrangler", manufacturer=maker)
        self.generation = Generation.objects.create(name="JL", vehicle_model=model, start_year=2018)
        self.bodies = {door: FactoryBodyConfiguration.objects.create(generation=self.generation, door_configuration=door) for door in ("two-door", "four-door")}
        template = json.loads((REPOSITORY / "reference/tests/fixtures/ingestion/candidate_v3/B.json").read_text())
        self.paths = []
        self.candidates = {}
        self.docs = {}
        if registry:
            from reference.models import Engine
            seeds = json.loads((REPOSITORY / 'docs/implementation/handoffs/engine_registry_20261114/wrangler_engine_seed_proposal.json').read_text())
            for seed in seeds['proposals']:
                Engine.objects.create(manufacturer=maker, engine_code=seed['engine_code'], name=seed['proposed_name'], **seed['parameters'])
        for row in rows:
            key = row["candidate_id"]
            door = {"2-door": "two-door", "4-door": "four-door"}[row["body_style"]]
            trim = audit[key]["owner_required_canonical_trim"]
            powertrain = {"engine_displacement_liters": row["engine_displacement_liters"], "engine_cylinders": int(row["engine_cylinders"]),
                "engine_aspiration": row["proposed_aspiration"], "fuel_type": row["proposed_fuel_type"], "electrification_type": row["proposed_electrification_type"]}
            # Synthetic direct positive configuration evidence. Real unresolved review
            # proposals are never turned into operational approved findings by this helper.
            values = {"make": "Jeep", "model": "Wrangler", "model_year": 2024, "market": "US", "trim_name": trim,
                      "generic_drive_classification": "4WD", "factory_body.door_configuration": door, **powertrain}
            source_values = ({k:v for k,v in values.items() if k not in powertrain} | {"engine_code":row["engine_code"]}) if registry else values
            assertions = [{"assertion_id": "configuration", "attribute_key": "configuration", "raw_value": source_values,
                           "source_context": "Synthetic isolated RA-049 test configuration " + key},
                          {"assertion_id": "model", "attribute_key": "source_model_code", "raw_value": row["model_code"],
                           "source_context": "Synthetic isolated model code evidence"}]
            raw = canonical_json({"assertions": assertions}).encode()
            raw_path = "evidence/" + key + ".json"
            (self.root / "evidence").mkdir(exist_ok=True)
            (self.root / raw_path).write_bytes(raw)
            h = byte_hash(raw)
            doc = deepcopy(template["evidence_documents"][0])
            doc.update(source_id="ra049-isolated-source-" + key, raw_artifact_reference=raw_path, raw_artifact_hash=h,
                       assertion_set_id=key, assertions=assertions, source_locator="isolated:test", publication_revision="isolated-test")
            q = "|".join((doc["source_id"], h, key, "configuration"))
            candidate = deepcopy(template)
            candidate.update(candidate_reference=key, candidate_identity={"manufacturer_name": "Jeep", "vehicle_model_name": "Wrangler", "model_year": 2024, "market": "US", "trim_name": trim},
                drivetrain="4WD", configuration_refs=[q], evidence_documents=[doc], evidence_raw_hashes=[h], canonical_powertrain=powertrain)
            candidate["applicability"][0].update(configuration_refs=[q], source_assertion_refs=[q])
            candidate["generation_evidence"] = [{"source_id": doc["source_id"], "source_namespace": "source_model_code", "identity_type": "model_code", "native_identifier": row["model_code"],
                "document_hash": h, "assertion_set_id": key, "assertion_id": "model", "normalizer_id": "explicit_generation_identity", "normalizer_version": "1.0.0"}]
            candidate["normalized_assertions"] = sorted([{"interpretation_id": "i-" + target, "source_assertion_ref": q, "target_attribute_key": target,
                "normalized_concept": value, "mapping_status": "mapped", "applicability_ref": "app", "normalization": {"id": "decimal_liters" if target == "engine_displacement_liters" else "source_literal", "version": "1.0.0"}, "finding_refs": []} for target, value in values.items()], key=lambda x: x["interpretation_id"])
            pre = body_preimage(SCOPE, {"door_configuration": door})
            candidate["factory_body"] = {"disposition": "pending", "identity": {"semantic_digest": semantic_digest(pre), "preimage": pre},
                "support": {"applicability_ref": "app", "configuration_refs": [q], "interpretation_refs": ["i-factory_body.door_configuration"], "equivalence_interpretation_ref": None}}
            candidate["candidate_hash"] = wire.candidate_hash(candidate)
            wire.validate_structure(candidate)
            if registry:
                from reference.ingestion.importing.registry_body_import import prepare_registry_candidate
                candidate['canonical_powertrain'] = {k:None for k in powertrain}
                candidate['normalized_assertions'] = [i for i in candidate['normalized_assertions'] if i['target_attribute_key'] not in powertrain]
                candidate['candidate_hash'] = wire.candidate_hash(candidate)
                candidate = prepare_registry_candidate(candidate, q)
            candidate_path = "candidates/" + key + ".json"
            (self.root / "candidates").mkdir(exist_ok=True)
            (self.root / candidate_path).write_text(canonical_json(candidate))
            self.paths.append(candidate_path)
            self.candidates[key] = candidate
            self.docs[(row["model_code"], key)] = [doc]
        for (code, _), documents in self.docs.items():
            doc = documents[0]
            payload = {"review_version": "1.0", "revision_uuid": str(uuid4()), "correspondence_uuid": str(uuid4()), "revision_number": 1, "supersedes_uuid": None,
                "vehicle_model_uuid": str(model.uuid), "generation_uuid": str(self.generation.uuid), "source_id": doc["source_id"], "source_namespace": "source_model_code", "identity_type": "model_code",
                "native_identifier": code, "market": "US", "start_year": 2024, "end_year": 2024, "restrictions": {}, "evidence": documents, "finding": "established", "reviewer": "Isolated test owner",
                "reviewed_at": datetime.now(timezone.utc).isoformat(), "review_notes": "Synthetic isolated correspondence; no operational publication."}
            revision, receipt = publish_correspondence(payload, digest(payload), authorized=True, operator_label="project-owner", execution_agent="implementation-agent")
            assert revision is not None, receipt.messages_json
        if registry:
            from reference.ingestion.importing.registry_body_import import RegistryRelease
            self.release = RegistryRelease(self.paths, root=self.root)
        else:
            self.release = Release(self.paths, root=self.root)

    def close(self):
        self.settings.disable()
        self.directory.cleanup()

    def plan(self, key="JL24-01"):
        plan = self.release.plan(key)
        if "assessment_version" in plan:
            raise AssertionError(plan)
        return plan

    def write_candidate(self, key, value):
        value["candidate_hash"] = wire.candidate_hash(value)
        (self.root / ("candidates/" + key + ".json")).write_text(canonical_json(value))
