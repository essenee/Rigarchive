"""Regression checks for the reviewed MY2018 JL order-guide inventory."""
from dataclasses import replace
from pathlib import Path

from django.conf import settings
from django.test import SimpleTestCase

from reference.ingestion.acquisition.base import AcquisitionError
from reference.ingestion.acquisition.jeep import (
    JL_MOAB_INVENTORY, JL_ORDER_GUIDE_INVENTORY, extract_jl_order_guide_inventory, jl_order_guide_generation_sets,
)
from reference.ingestion.candidate.builder import construct_candidate_configuration
from reference.ingestion.contracts import CandidateIdentity
from reference.ingestion.normalization.jeep import normalize_jeep


class JLOrderGuideTests(SimpleTestCase):
    def setUp(self):
        path = Path(settings.BASE_DIR) / JL_ORDER_GUIDE_INVENTORY
        if not path.is_file():
            self.skipTest("Private reviewed order-guide inventory is unavailable.")
        self.raw = path.read_bytes()
        self.rows = extract_jl_order_guide_inventory(self.raw)

    def test_fourteen_candidates_use_five_model_code_documents(self):
        bindings = jl_order_guide_generation_sets(self.rows)
        self.assertEqual(set(bindings), {"JLJL72", "JLJS72", "JLJL74", "JLJP74", "JLJS74"})
        identities = set()
        for source in self.rows:
            facts = {row.attribute_key: row.raw_value for row in source.source_assertions}
            normalized = normalize_jeep(source)
            values = {item.target_attribute_key: item.normalized_concept for item in normalized}
            trim = values["trim"]
            candidate = construct_candidate_configuration(
                CandidateIdentity("Jeep", "Wrangler", model_year=2018, market="US", trim_name=trim),
                [source, bindings[facts["manufacturer_model_code"]]], normalized,
                schema_version="2.0.0", candidate_reference=source.provenance.native_record_id,
                created_at="2026-11-06T00:00:00Z",
            )
            self.assertEqual(len(candidate.generation_evidence), 1)
            self.assertEqual(candidate.generation_evidence[0]["native_identifier"], facts["manufacturer_model_code"])
            self.assertEqual(len(normalized), 8)
            identities.add((trim, values["engine_cylinders"]))
            self.assertEqual("order_code_six_speed_manual" in facts, values["engine_cylinders"] == 6)
            self.assertIn("order_code_eight_speed_automatic", facts)
        self.assertEqual(len(self.rows), 14)
        self.assertEqual(len(identities), 14)
        self.assertTrue({("Sport S", 4), ("Unlimited Sport S", 6)} <= identities)

    def test_altered_inventory_and_cross_generation_assertions_are_rejected(self):
        with self.assertRaises(AcquisitionError):
            extract_jl_order_guide_inventory(self.raw + b" ")
        source = self.rows[0]
        rows = [replace(row, raw_value="JK") if row.attribute_key == "manufacturer_model_code" else row
                for row in source.source_assertions]
        with self.assertRaises(ValueError):
            normalize_jeep(replace(source, source_assertions=rows))

    def test_moab_is_a_single_v6_identity_with_august_lineage(self):
        path = Path(settings.BASE_DIR) / JL_MOAB_INVENTORY
        if not path.is_file():
            self.skipTest("Private reviewed Moab supplement is unavailable.")
        source, = extract_jl_order_guide_inventory(path.read_bytes())
        facts = {row.attribute_key: row.raw_value for row in source.source_assertions}
        normalized = normalize_jeep(source)
        values = {item.target_attribute_key: item.normalized_concept for item in normalized}
        self.assertEqual(values["trim"], "Unlimited Moab")
        self.assertEqual(values["engine_cylinders"], 6)
        self.assertEqual(values["engine_displacement_liters"].normalized_value, 3.6)
        self.assertEqual(values["generic_drive_classification"], "4WD")
        self.assertEqual(facts["manufacturer_grade"], "Moab Edition")
        self.assertEqual(facts["manufacturer_model_code"], "JLJP74")
        self.assertEqual(facts["order_code_eight_speed_automatic"], "24M")
        self.assertNotIn("order_code_six_speed_manual", facts)
        self.assertNotIn("28G", facts.values())
        self.assertNotIn("transmission", values)
        binding = jl_order_guide_generation_sets(self.rows)["JLJP74"]
        candidate = construct_candidate_configuration(
            CandidateIdentity("Jeep", "Wrangler", model_year=2018, market="US", trim_name="Unlimited Moab"),
            [source, binding], normalized, schema_version="2.0.0",
            candidate_reference=source.provenance.native_record_id,
            created_at="2026-11-06T00:00:00Z",
        )
        self.assertEqual(len(candidate.generation_evidence), 1)
        self.assertEqual(candidate.generation_evidence[0]["native_identifier"], "JLJP74")
        self.assertEqual(len(self.rows), 14)
