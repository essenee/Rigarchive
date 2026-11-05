"""Synthetic, manufacturer-neutral policy cases; no files/network/database."""
import copy
from django.test import SimpleTestCase
from reference.ingestion.normalization.equipment import assess_equipment_scope
from reference.ingestion.contracts import SourceAssertion


class EquipmentIngestionPolicyTests(SimpleTestCase):
    def assess(self, kind, **overrides):
        args = dict(brochure_listed=True, brochure_reference="source|sha256:synthetic|brochure",
                    evidence_refs=["source|sha256:synthetic|brochure|equipment"],
                    applicability={"market": "US", "model_year": 2018, "grade": "Synthetic"})
        args.update(overrides)
        return assess_equipment_scope(kind, **args)

    def test_brochure_package_requires_identity_contents_and_scope(self):
        self.assertEqual(self.assess("factory_package", manufacturer_identifies_package=True,
                                     contents=["item A", "item B"])["disposition"], "eligible")
        self.assertEqual(self.assess("factory_package", contents=["item A"])["disposition"], "review_required")
        self.assertEqual(self.assess("factory_package", manufacturer_identifies_package=True)["disposition"], "review_required")
        self.assertEqual(self.assess("factory_package", manufacturer_identifies_package=True,
                                     contents=["item A"], applicability=None)["disposition"], "review_required")

    def test_individual_options_never_become_packages(self):
        result = self.assess("factory_option")
        self.assertEqual((result["disposition"], result["classification"]), ("eligible", "factory_option"))

    def test_accessory_absent_from_brochure_is_categorically_excluded(self):
        result = self.assess("accessory", brochure_listed=False, brochure_reference=None)
        self.assertEqual(result["disposition"], "excluded")
        self.assertEqual(result["classification"], "accessory")

    def test_brochure_accessory_remains_accessory(self):
        result = self.assess("accessory")
        self.assertEqual((result["disposition"], result["classification"]), ("eligible", "accessory"))

    def test_press_release_identity_does_not_authorize_accessory_list(self):
        identity = SourceAssertion("vehicle", "body_grade_identity", "two-door 2018 Wrangler Sport",
                                   "Synthetic manufacturer press release, introductory paragraph")
        before = copy.deepcopy(identity)
        accessory = self.assess("accessory", brochure_listed=False, brochure_reference=None,
                                evidence_refs=["publisher|sha256:synthetic|release|accessory"])
        self.assertEqual(accessory["disposition"], "excluded")
        self.assertEqual(identity, before)  # identity evidence remains separately available for review

    def test_non_brochure_optional_equipment_requires_human_exception(self):
        result = self.assess("factory_package", brochure_listed=False, brochure_reference=None,
                             manufacturer_identifies_package=True, contents=["item A"])
        self.assertEqual(result["disposition"], "review_required")
        self.assertIn("explicit authorization", result["reason"])
        # There is no caller-controlled force/approved-exception bypass.
        with self.assertRaises(TypeError):
            self.assess("factory_package", exception_authorized=True)

    def test_standard_equipment_remains_separate_and_other_sources_allowed(self):
        result = self.assess("standard_equipment", brochure_listed=False, brochure_reference=None)
        self.assertEqual((result["disposition"], result["classification"]), ("eligible", "standard_equipment"))

    def test_provenance_and_brochure_reference_are_required(self):
        self.assertEqual(self.assess("factory_option", evidence_refs=[])["disposition"], "review_required")
        self.assertEqual(self.assess("factory_option", brochure_reference=None)["disposition"], "review_required")
        with self.assertRaises(ValueError):
            self.assess("guessed_package")

    def test_inputs_not_modified_and_refs_preserved(self):
        refs = ["manufacturer|sha256:synthetic|brochure|option"]
        result = self.assess("factory_option", evidence_refs=refs)
        self.assertEqual(refs, result["evidence_refs"])
        self.assertIsNot(refs, result["evidence_refs"])
