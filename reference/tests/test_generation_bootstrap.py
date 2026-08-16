"""
Unit Test Suite for US-Market Generation Bootstrap & Full Configuration Population (RA-031).

Verifies Wikipedia generation taxonomy discovery, market-scoped generation identity,
existing-data short-circuiting, unpopulated generation bootstrap, candidate exception isolation,
multi-year configuration population, idempotence, Sport/V8 discovery, and public archive navigation integration.
"""

from pathlib import Path
from django.conf import settings
from django.test import TestCase

from reference.ingestion.acquisition.wikipedia import GenerationTaxonomy, WikipediaExtractor
from reference.ingestion.orchestration.generation_bootstrap import GenerationBootstrapOrchestrator
from reference.models import Generation, Manufacturer, VehicleDefinition, VehicleModel


class GenerationBootstrapTests(TestCase):
    @classmethod
    def setUpTestData(cls) -> None:
        cls.toyota = Manufacturer.objects.create(name="Toyota", country_code="JP", is_active=True)
        cls.four_runner = VehicleModel.objects.create(manufacturer=cls.toyota, name="4Runner", is_active=True)

        cls.fifth_gen = Generation.objects.create(
            vehicle_model=cls.four_runner,
            name="Fifth Generation",
            slug="fifth-generation",
            generation_number=5,
            start_year=2010,
            end_year=2024,
            is_active=True,
        )

        cls.vd_2020 = VehicleDefinition.objects.create(
            generation=cls.fifth_gen,
            model_year=2020,
            trim_name="SR5",
            engine_name="4.0L V6",
            drivetrain=VehicleDefinition.Drivetrain.TWO_WHEEL_DRIVE,
            market=VehicleDefinition.Market.UNITED_STATES,
            is_active=True,
        )

        cls.orchestrator = GenerationBootstrapOrchestrator()

    def test_1_wikipedia_generation_taxonomy_extraction(self) -> None:
        """1. Wikipedia generation taxonomy extraction returns valid taxonomy list."""
        extractor = WikipediaExtractor()
        taxonomies = extractor.extract_taxonomies("Toyota", "4Runner", "US")

        self.assertEqual(len(taxonomies), 5)
        self.assertEqual(taxonomies[0].name, "First Generation")
        self.assertEqual(taxonomies[3].name, "Fourth Generation")
        self.assertEqual(taxonomies[3].start_year, 2003)
        self.assertEqual(taxonomies[3].end_year, 2009)

    def test_2_market_scoped_generation_identity(self) -> None:
        """2. Market-scoped generation identity preserves market context ('US')."""
        extractor = WikipediaExtractor()
        taxonomies = extractor.extract_taxonomies("Toyota", "4Runner", "US")

        for tax in taxonomies:
            self.assertEqual(tax.market, "US")
            asset = extractor.build_assertion_set(tax)
            self.assertEqual(asset.provenance.source_applicability.market, "US")

    def test_3_existing_populated_generation_detection(self) -> None:
        """3. Existing populated generation detection short-circuits re-population."""
        res = self.orchestrator.run_bootstrap_pipeline(make="Toyota", model="4Runner", market="US")

        gen5_res = [g for g in res.generation_results if g.generation_slug == "fifth-generation"][0]
        self.assertEqual(gen5_res.action, "SHORT_CIRCUIT_EXISTING_DATA")
        self.assertTrue(gen5_res.is_active)
        self.assertEqual(gen5_res.configurations_created, 0)

    def test_4_empty_generation_bootstrap(self) -> None:
        """4. Empty generation bootstrap initializes unrepresented generation safely."""
        res = self.orchestrator.run_bootstrap_pipeline(make="Toyota", model="4Runner", market="US")

        gen4_res = [g for g in res.generation_results if g.generation_slug == "fourth-generation"][0]
        self.assertEqual(gen4_res.action, "BOOTSTRAPPED_AND_POPULATED")
        self.assertTrue(gen4_res.is_active)
        self.assertGreater(gen4_res.configurations_created, 0)

    def test_5_no_publicly_available_empty_generation_after_failed_bootstrap(self) -> None:
        """5. No publicly available empty generation node after bootstrap with 0 valid configs."""
        res = self.orchestrator.run_bootstrap_pipeline(make="Toyota", model="4Runner", market="US")

        gen1_res = [g for g in res.generation_results if g.generation_slug == "first-generation"][0]
        self.assertFalse(gen1_res.is_active)

        gen1_obj = Generation.objects.get(vehicle_model=self.four_runner, slug="first-generation")
        self.assertFalse(gen1_obj.is_active)

    def test_6_jd_power_per_year_configuration_enumeration(self) -> None:
        """6. J.D. Power per-year configuration enumeration extracts multi-year assertion sets."""
        res = self.orchestrator.run_bootstrap_pipeline(make="Toyota", model="4Runner", market="US")

        gen4_res = [g for g in res.generation_results if g.generation_slug == "fourth-generation"][0]
        self.assertEqual(gen4_res.model_years_attempted, [2003, 2004, 2005, 2006, 2007, 2008, 2009])

    def test_7_full_generation_multi_year_population_orchestration(self) -> None:
        """7. Full-generation multi-year population orchestrates across 2003-2009 creating 85 configs."""
        initial_vd_count = VehicleDefinition.objects.count()

        res = self.orchestrator.run_bootstrap_pipeline(make="Toyota", model="4Runner", market="US")

        gen4_res = [g for g in res.generation_results if g.generation_slug == "fourth-generation"][0]
        self.assertEqual(gen4_res.configurations_created, 85)
        self.assertEqual(VehicleDefinition.objects.count(), initial_vd_count + 85)

    def test_8_historical_jd_power_discovery_finds_sport_and_v8_configurations(self) -> None:
        """8. Historical J.D. Power discovery finds Sport Edition and 4.7L V8 configurations."""
        self.orchestrator.run_bootstrap_pipeline(make="Toyota", model="4Runner", market="US")

        sport_defs = VehicleDefinition.objects.filter(
            generation__slug="fourth-generation",
            trim_name="Sport Edition",
            is_active=True,
        )
        self.assertEqual(sport_defs.count(), 28)

        v8_defs = VehicleDefinition.objects.filter(
            generation__slug="fourth-generation",
            engine_name="4.7L V8",
            is_active=True,
        )
        self.assertEqual(v8_defs.count(), 42)

    def test_9_2005_sport_discovers_all_four_v6_v8_2wd_4wd_combinations(self) -> None:
        """9. 2005 Sport discovers all 4 V6/V8 x 2WD/4WD combinations."""
        self.orchestrator.run_bootstrap_pipeline(make="Toyota", model="4Runner", market="US")

        sport_2005 = VehicleDefinition.objects.filter(
            generation__slug="fourth-generation",
            model_year=2005,
            trim_name="Sport Edition",
            is_active=True,
        )
        self.assertEqual(sport_2005.count(), 4)
        combos = {(vd.engine_name, vd.drivetrain) for vd in sport_2005}
        self.assertIn(("4.0L V6", "2WD"), combos)
        self.assertIn(("4.0L V6", "4WD"), combos)
        self.assertIn(("4.7L V8", "2WD"), combos)
        self.assertIn(("4.7L V8", "4WD"), combos)

    def test_10_repeat_run_is_idempotent(self) -> None:
        """10. Repeat run is idempotent (0 new creates, 100% exact matches)."""
        self.orchestrator.run_bootstrap_pipeline(make="Toyota", model="4Runner", market="US")
        vd_count_after_run1 = VehicleDefinition.objects.count()

        res2 = self.orchestrator.run_bootstrap_pipeline(make="Toyota", model="4Runner", market="US")

        vd_count_after_run2 = VehicleDefinition.objects.count()
        self.assertEqual(vd_count_after_run1, vd_count_after_run2)

        gen4_res2 = [g for g in res2.generation_results if g.generation_slug == "fourth-generation"][0]
        self.assertEqual(gen4_res2.action, "SHORT_CIRCUIT_EXISTING_DATA")
        self.assertEqual(gen4_res2.configurations_created, 0)

    def test_11_v6_and_v8_maintain_distinct_canonical_identities(self) -> None:
        """11. 4.0L V6 and 4.7L V8 maintain distinct canonical identities within same year/trim/drivetrain."""
        self.orchestrator.run_bootstrap_pipeline(make="Toyota", model="4Runner", market="US")

        v6_sr5_2003 = VehicleDefinition.objects.get(
            generation__slug="fourth-generation",
            model_year=2003,
            trim_name="SR5",
            engine_name="4.0L V6",
            drivetrain="2WD",
            is_active=True,
        )

        v8_sr5_2003 = VehicleDefinition.objects.get(
            generation__slug="fourth-generation",
            model_year=2003,
            trim_name="SR5",
            engine_name="4.7L V8",
            drivetrain="2WD",
            is_active=True,
        )

        self.assertNotEqual(v6_sr5_2003.id, v8_sr5_2003.id)
        self.assertNotEqual(v6_sr5_2003.slug, v8_sr5_2003.slug)
        self.assertEqual(v6_sr5_2003.slug, "2003-sr5-40l-v6-2wd-us")
        self.assertEqual(v8_sr5_2003.slug, "2003-sr5-47l-v8-2wd-us")

    def test_12_generation_navigation_exposes_successfully_populated_generations(self) -> None:
        """12. Generation navigation exposes successfully populated generations."""
        self.orchestrator.run_bootstrap_pipeline(make="Toyota", model="4Runner", market="US")

        response = self.client.get(self.four_runner.get_absolute_url())
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Fourth Generation")
        self.assertContains(response, "Fifth Generation")
        self.assertNotContains(response, "First Generation")

    def test_13_batch_manifest_assembly_and_hashing(self) -> None:
        """13. Assembles deterministic PopulationBatchManifest with summary and SHA-256 hash."""
        manifest = self.orchestrator.create_batch_manifest(make="Toyota", model="4Runner", market="US", start_year=2003, end_year=2009)
        self.assertEqual(manifest.total_candidates, 85)
        self.assertTrue(manifest.batch_manifest_hash.startswith("sha256:"))
        self.assertIn("RIGARCHIVE POPULATION BATCH REVIEW MANIFEST", manifest.summary_text())

    def test_14_batch_execution_creates_multiple_records_with_receipt_linkage(self) -> None:
        """14. Executing an authorized batch creates multiple records with individual receipts linked to batch hash."""
        from reference.models import ImportExecutionReceipt, VehicleDefinition
        VehicleDefinition.objects.filter(generation__slug="fourth-generation").delete()

        manifest = self.orchestrator.create_batch_manifest(make="Toyota", model="4Runner", market="US", start_year=2003, end_year=2009)
        result = self.orchestrator.execute_authorized_batch(manifest)
        self.assertEqual(result["created"], 85)
        self.assertEqual(result["blocked"], 0)

        # Check receipt linkage
        receipts = ImportExecutionReceipt.objects.filter(manifest_hash=manifest.batch_manifest_hash)
        self.assertEqual(receipts.count(), 85)
        for r in receipts:
            self.assertEqual(r.manifest_hash, manifest.batch_manifest_hash)
            self.assertEqual(r.execution_outcome, "created")

    def test_15_batch_execution_tampered_hash_rejection(self) -> None:
        """15. Tampered or corrupted batch manifest hash is rejected."""
        manifest = self.orchestrator.create_batch_manifest(make="Toyota", model="4Runner", market="US", start_year=2003, end_year=2009)
        manifest.batch_manifest_hash = "sha256:" + "f" * 64

        with self.assertRaises(ValueError):
            self.orchestrator.execute_authorized_batch(manifest)

    def test_16_batch_execution_outside_authorized_slug_exclusion(self) -> None:
        """16. Candidates outside the authorized manifest item list are excluded."""
        from reference.models import VehicleDefinition
        VehicleDefinition.objects.filter(generation__slug="fourth-generation").delete()

        manifest = self.orchestrator.create_batch_manifest(make="Toyota", model="4Runner", market="US", start_year=2003, end_year=2009)
        # Remove one item from authorized manifest
        manifest.items.pop()
        manifest.batch_manifest_hash = manifest.compute_manifest_hash()

        result = self.orchestrator.execute_authorized_batch(manifest)
        self.assertEqual(result["total_attempted"], 84)
        self.assertEqual(result["outside_authorization"], 1)

    def test_17_batch_execution_idempotence(self) -> None:
        """17. Executing the same authorized batch twice is 100% idempotent (0 new creates)."""
        from reference.models import VehicleDefinition
        VehicleDefinition.objects.filter(generation__slug="fourth-generation").delete()

        manifest = self.orchestrator.create_batch_manifest(make="Toyota", model="4Runner", market="US", start_year=2003, end_year=2009)
        
        # First execution
        res1 = self.orchestrator.execute_authorized_batch(manifest)
        self.assertEqual(res1["created"], 85)

        # Second execution
        manifest2 = self.orchestrator.create_batch_manifest(make="Toyota", model="4Runner", market="US", start_year=2003, end_year=2009)
        res2 = self.orchestrator.execute_authorized_batch(manifest2)
        self.assertEqual(res2["created"], 0)
        self.assertEqual(res2["no_op"], 85)

    def test_18_execute_population_batch_management_command(self) -> None:
        """18. execute_population_batch management command loads JSON manifest and executes authorized batch."""
        import json, tempfile
        from reference.models import VehicleDefinition
        VehicleDefinition.objects.filter(generation__slug="fourth-generation").delete()

        manifest = self.orchestrator.create_batch_manifest(make="Toyota", model="4Runner", market="US", start_year=2003, end_year=2009)

        manifest_data = {
            "batch_id": manifest.batch_id,
            "manufacturer_name": manifest.manufacturer_name,
            "vehicle_model_name": manifest.vehicle_model_name,
            "market": manifest.market,
            "start_year": manifest.start_year,
            "end_year": manifest.end_year,
            "total_candidates": manifest.total_candidates,
            "create_count": manifest.create_count,
            "no_op_count": manifest.no_op_count,
            "review_count": manifest.review_count,
            "batch_manifest_hash": manifest.batch_manifest_hash,
            "items": [
                {
                    "candidate_reference": it.candidate_reference,
                    "native_identifier": it.native_identifier,
                    "model_year": it.model_year,
                    "trim_name": it.trim_name,
                    "engine_name": it.engine_name,
                    "drivetrain": it.drivetrain,
                    "planned_action": it.planned_action,
                    "create_basis": it.create_basis,
                    "target_slug": it.target_slug,
                }
                for it in manifest.items
            ],
        }

        with tempfile.NamedTemporaryFile("w+", suffix=".json", delete=False) as tf:
            json.dump(manifest_data, tf)
            tf_path = tf.name

        try:
            from io import StringIO
            from django.core.management import call_command
            out = StringIO()
            call_command("execute_population_batch", "--manifest", tf_path, "--authorize", stdout=out)
            output = out.getvalue()
            self.assertIn("RIGARCHIVE POPULATION BATCH REVIEW MANIFEST", output)
            self.assertIn("Operator authorization confirmed", output)
            self.assertIn("Created:              85", output)
        finally:
            import os
            if os.path.exists(tf_path):
                os.remove(tf_path)

    def test_19_atomicity_receipt_failure_rolls_back_vehicle_definition(self) -> None:
        """19. Atomicity Regression Test: ImportExecutionReceipt creation failure rolls back VehicleDefinition creation cleanly."""
        from unittest.mock import patch
        from reference.models import ImportExecutionReceipt, VehicleDefinition

        # Clear Fourth Generation records for controlled test isolation
        VehicleDefinition.objects.filter(generation__slug="fourth-generation").delete()
        initial_vd_count = VehicleDefinition.objects.count()
        initial_receipt_count = ImportExecutionReceipt.objects.count()

        manifest = self.orchestrator.create_batch_manifest(make="Toyota", model="4Runner", market="US", start_year=2003, end_year=2003)
        self.assertGreater(manifest.create_count, 0)

        # Force ImportExecutionReceipt.objects.create to raise a database exception
        with patch.object(ImportExecutionReceipt.objects, "create", side_effect=RuntimeError("Simulated receipt DB failure")):
            res = self.orchestrator.execute_authorized_batch(manifest)

        # Verify batch report reflects that creations were blocked due to failure
        self.assertEqual(res["created"], 0)
        self.assertEqual(res["blocked"], manifest.total_candidates)

        # Verify VehicleDefinition count is completely unchanged (0 orphan VDs created)
        self.assertEqual(VehicleDefinition.objects.count(), initial_vd_count)

        # Verify no ImportExecutionReceipt records were persisted
        self.assertEqual(ImportExecutionReceipt.objects.count(), initial_receipt_count)

        # Verify specific target slug was not persisted
        self.assertFalse(VehicleDefinition.objects.filter(slug="2003-sr5-40l-v6-2wd-us").exists())
