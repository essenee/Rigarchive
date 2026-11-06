"""Synthetic contract inputs. These are not retained J.D. Power evidence."""
import json
from types import SimpleNamespace

from django.test import SimpleTestCase

from reference.ingestion.acquisition.jd_power_extractor import JDPowerExtractor
from reference.ingestion.acquisition.snapshots import compute_content_hash
from reference.ingestion.candidate.builder import construct_candidate_configuration
from reference.ingestion.contracts import CandidateIdentity
from reference.ingestion.normalization.jd_power import JDPowerNormalizer


class WranglerJDPowerTests(SimpleTestCase):
    def row(self, **changes):
        return dict(make="Jeep", model="Wrangler", model_year=2007, market="US",
                    trim="Utility 4D Unlimited X 2WD", drivetrain="2WD", native_trim_id="row-1",
                    engine_displacement_liters=3.8, engine_cylinders=6) | changes

    def extract(self, rows, *, hash_override=None, year=2007):
        raw = json.dumps({"_provenance": {"publisher": "J.D. Power", "source_id": "jd_power",
                                              "publication_scope": "US"}, "configurations": rows}).encode()
        meta = SimpleNamespace(source_id="jd_power", content_hash=hash_override or compute_content_hash(raw),
                               storage_path="storage/synthetic.json", acquired_at="2026-11-05T00:00:00Z",
                               publisher_locator=f"https://www.jdpower.com/cars/{year}/jeep/wrangler/trim")
        return JDPowerExtractor().extract(raw, meta)

    def test_eight_explicit_rows_and_candidate_lineage(self):
        variants = [
            ("2D", "X", "4WD"), ("2D", "Sahara", "4WD"), ("2D", "Rubicon", "4WD"),
            ("4D", "Unlimited X", "2WD"), ("4D", "Unlimited X", "4WD"),
            ("4D", "Unlimited Sahara", "2WD"), ("4D", "Unlimited Sahara", "4WD"),
            ("4D", "Unlimited Rubicon", "4WD"),
        ]
        rows = [self.row(trim=f"Utility {body} {grade} {drive}", drivetrain=drive, native_trim_id=f"row-{i}")
                for i, (body, grade, drive) in enumerate(variants)]
        sets = self.extract(rows)
        self.assertEqual(len(sets), 8)
        self.assertEqual(sets, self.extract(rows))
        for i, (source, (_, grade, drive)) in enumerate(zip(sets, variants)):
            interpretations = JDPowerNormalizer().normalize(source)
            facts = {item.target_attribute_key: item.normalized_concept for item in interpretations}
            self.assertEqual((facts["trim"], facts["generic_drive_classification"]), (grade, drive))
            candidate = construct_candidate_configuration(
                CandidateIdentity("Jeep", "Wrangler", model_year=2007, market="US", trim_name=grade),
                [source], interpretations, schema_version="2.0.0",
                candidate_reference=f"test-{i}", created_at="2026-11-05T00:00:00Z",
            )
            self.assertEqual(candidate.evidence_documents[0]["assertion_set_id"], f"row-{i}")
            self.assertTrue(any(item.raw_source_value == rows[i]["trim"] for item in candidate.normalized_assertions))
            self.assertFalse(candidate.generation_evidence)

    def test_incomplete_conflicting_and_out_of_scope_rows_fail_closed(self):
        for changes in (
            {"engine_displacement_liters": None}, {"engine_displacement_liters": 3.6},
            {"drivetrain": "4WD"}, {"trim": "Utility 4D Unlimited Rubicon 2WD"},
            {"trim": "Utility 2D Unlimited X 2WD"}, {"market": None},
            {"model_year": 2018}, {"trim": "Utility 4D Unlimited Sport 2WD"},
        ):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                self.extract([self.row(**changes)])
        with self.assertRaises(ValueError):
            self.extract([self.row()], hash_override="sha256:" + "0" * 64)

    def test_later_engine_and_explicit_selector(self):
        row = self.row(model_year=2012, trim="Utility 4D Unlimited Sport 4WD", drivetrain="4WD",
                       engine_displacement_liters=3.6, source_model_code="synthetic-model-code")
        source, = self.extract([row], year=2012)
        self.assertTrue(any(a.attribute_key == "source_model_code" for a in source.source_assertions))
        self.assertEqual(JDPowerNormalizer().normalize(source)[0].normalized_concept, "Jeep")

    def test_reviewed_inventory_needs_no_webpage_bytes_hash_or_selector(self):
        row = self.row()
        del row["native_trim_id"]
        first, = self.extract([row])
        second, = self.extract([row])
        self.assertEqual(first, second)
        self.assertEqual(first.provenance.native_record_id, "jdp_cfg_1")
        self.assertEqual(JDPowerNormalizer().normalize(first)[1].normalized_concept, "Wrangler")
