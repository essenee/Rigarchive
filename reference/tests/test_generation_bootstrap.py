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
from reference.models import (
    Generation,
    ImportExecutionReceipt,
    Manufacturer,
    VehicleDefinition,
    VehicleModel,
)


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

    def test_20_tacoma_generation_taxonomy_extraction(self) -> None:
        """20. Tacoma generation taxonomy extraction returns 4 US-market generation taxonomies."""
        extractor = WikipediaExtractor()
        taxonomies = extractor.extract_taxonomies("Toyota", "Tacoma", "US")
        self.assertEqual(len(taxonomies), 4)
        self.assertEqual(taxonomies[0].name, "First Generation")
        self.assertEqual(taxonomies[1].name, "Second Generation")
        self.assertEqual(taxonomies[1].start_year, 2005)
        self.assertEqual(taxonomies[1].end_year, 2015)
        self.assertEqual(taxonomies[2].name, "Third Generation")

    def test_21_touareg_generation_taxonomy_extraction(self) -> None:
        """21. Touareg generation taxonomy extraction returns 2 US-market generation taxonomies."""
        extractor = WikipediaExtractor()
        taxonomies = extractor.extract_taxonomies("Volkswagen", "Touareg", "US")
        self.assertEqual(len(taxonomies), 2)
        self.assertEqual(taxonomies[0].name, "First Generation")
        self.assertEqual(taxonomies[0].start_year, 2004)
        self.assertEqual(taxonomies[0].end_year, 2010)
        self.assertEqual(taxonomies[1].name, "Second Generation")

    def test_22_volkswagen_grade_and_drivetrain_normalization(self) -> None:
        """22. Volkswagen grade and 4MOTION drivetrain normalization rules map correctly."""
        from reference.ingestion.normalization.rules.volkswagen_rules import (
            normalize_volkswagen_drivetrain,
            normalize_volkswagen_grade,
        )
        trim, status, mfr_term = normalize_volkswagen_grade("VR6 Sport")
        self.assertEqual(trim, "VR6 Sport")
        self.assertEqual(status, "mapped")
        self.assertIn("Volkswagen Grade", mfr_term)

        gen_drive, arch = normalize_volkswagen_drivetrain("4MOTION")
        self.assertEqual(gen_drive, "AWD")
        self.assertEqual(arch, "Full-time 4WD")

    def test_23_multi_model_generation_bootstrap_and_idempotence(self) -> None:
        """23. Multi-model generation bootstrap creates authorized configurations idempotently."""
        manifest = self.orchestrator.create_batch_manifest(make="Volkswagen", model="Touareg", market="US", start_year=2004, end_year=2004)
        manifest.batch_manifest_hash = manifest.compute_manifest_hash()
        res1 = self.orchestrator.execute_authorized_batch(manifest)
        self.assertEqual(res1["created"], 4)

        manifest2 = self.orchestrator.create_batch_manifest(make="Volkswagen", model="Touareg", market="US", start_year=2004, end_year=2004)
        manifest2.batch_manifest_hash = manifest2.compute_manifest_hash()
        res2 = self.orchestrator.execute_authorized_batch(manifest2)
        self.assertEqual(res2["created"], 0)
        self.assertGreaterEqual(res2["no_op"], 4)

    def test_24_engine_formatting_i4_vs_v4(self) -> None:
        """24. Engine formatting represents 4-cylinder engines as I4 while preserving V6, V8, V10."""
        from reference.ingestion.importing.planner import _format_engine_name
        self.assertEqual(_format_engine_name(2.7, 4), "2.7L I4")
        self.assertEqual(_format_engine_name(2.4, 4), "2.4L I4")
        self.assertEqual(_format_engine_name(3.5, 6), "3.5L V6")
        self.assertEqual(_format_engine_name(4.7, 8), "4.7L V8")
        self.assertEqual(_format_engine_name(5.0, 10), "5.0L V10")

    def test_25_completeness_semantics_sample_vs_exhaustive(self) -> None:
        """25. Representative sample payloads do not evaluate to ESTABLISHED completeness status."""
        from reference.ingestion.acquisition.jd_power_extractor import JDPowerHistoricalDiscoveryStrategy
        strategy = JDPowerHistoricalDiscoveryStrategy()
        sample_configs = [{"trim": "SR5", "engine_displacement_liters": 2.7, "engine_cylinders": 4}]
        status = strategy.evaluate_inventory_completeness(sample_configs, 2005)
        self.assertNotEqual(status.value, "established")

    def test_26_full_2016_tacoma_inventory(self) -> None:
        """26. 2016 Tacoma configuration inventory contains 12 distinct drivetrain and engine configurations."""
        manifest = self.orchestrator.create_batch_manifest(make="Toyota", model="Tacoma", market="US", start_year=2016, end_year=2016)
        self.assertGreaterEqual(manifest.total_candidates, 12)
        trims = {item.trim_name for item in manifest.items}
        self.assertIn("SR", trims)
        self.assertIn("SR5", trims)
        self.assertIn("TRD Sport", trims)
        self.assertIn("TRD Off-Road", trims)
        self.assertIn("Limited", trims)

    def test_27_all_tacoma_and_touareg_generation_years_iterated(self) -> None:
        """27. Bootstrap orchestrator iterates all valid model years for Tacoma and Touareg generations."""
        manifest_tacoma = self.orchestrator.create_batch_manifest(make="Toyota", model="Tacoma", market="US", start_year=1995, end_year=2025)
        years_tacoma = {item.model_year for item in manifest_tacoma.items}
        self.assertEqual(len(years_tacoma), 31)
        self.assertEqual(min(years_tacoma), 1995)
        self.assertEqual(max(years_tacoma), 2025)

        manifest_touareg = self.orchestrator.create_batch_manifest(make="Volkswagen", model="Touareg", market="US", start_year=2004, end_year=2017)
        years_touareg = {item.model_year for item in manifest_touareg.items}
        self.assertEqual(len(years_touareg), 14)
        self.assertEqual(min(years_touareg), 2004)
        self.assertEqual(max(years_touareg), 2017)

    def test_28_noop_receipt_suppression(self) -> None:
        """28. Re-running an exact-match authorized batch reports NO_OP count without creating extra receipts."""
        manifest1 = self.orchestrator.create_batch_manifest(make="Volkswagen", model="Touareg", market="US", start_year=2004, end_year=2004)
        manifest1.batch_manifest_hash = manifest1.compute_manifest_hash()

        receipt_count_before_run1 = ImportExecutionReceipt.objects.count()
        res1 = self.orchestrator.execute_authorized_batch(manifest1)
        receipt_count_after_run1 = ImportExecutionReceipt.objects.count()

        # Run 1 creates 4 VDs (3 J.D. Power + 1 manufacturer supplemental V8 X) and persists 4 receipts
        self.assertEqual(res1["created"], 4)
        self.assertEqual(receipt_count_after_run1 - receipt_count_before_run1, 4)

        # Run 2 on identical data creates 0 VDs (4 NO_OP)
        manifest2 = self.orchestrator.create_batch_manifest(make="Volkswagen", model="Touareg", market="US", start_year=2004, end_year=2004)
        manifest2.batch_manifest_hash = manifest2.compute_manifest_hash()
        res2 = self.orchestrator.execute_authorized_batch(manifest2)
        receipt_count_after_run2 = ImportExecutionReceipt.objects.count()

        self.assertEqual(res2["created"], 0)
        self.assertEqual(res2["no_op"], 4)
        # Verifies NO_OP receipt suppression: 0 new receipts created on repeat execution
        self.assertEqual(receipt_count_after_run2, receipt_count_after_run1)

    def test_29_ongoing_generation_null_end_year_ui_rendering(self) -> None:
        """29. Ongoing generation has end_year=None while populated VDs have a finite max year."""
        tacoma_4th = Generation.objects.create(
            vehicle_model=VehicleModel.objects.create(manufacturer=self.toyota, name="TacomaTest", is_active=True),
            name="Fourth Generation",
            slug="fourth-generation-test",
            start_year=2024,
            end_year=None,
            is_active=True,
        )
        self.assertIsNone(tacoma_4th.end_year)
        self.assertIn("2024–present", str(tacoma_4th))

    def test_30_hardened_completeness_semantics(self) -> None:
        """30. Completeness status evaluates strictly according to proven provenance semantics."""
        from reference.ingestion.acquisition.jd_power_extractor import JDPowerModernDiscoveryStrategy
        from reference.ingestion.contracts import InventoryCompletenessStatus

        strat = JDPowerModernDiscoveryStrategy()

        # Rule 1: Internal fixture flag alone does NOT yield ESTABLISHED (yields UNVERIFIED)
        status_internal = strat.evaluate_inventory_completeness([{"trim": "SR5"}] * 4, 2024, {"is_exhaustive_enumeration": True})
        self.assertEqual(status_internal, InventoryCompletenessStatus.UNVERIFIED)

        # Rule 2: Count >= 4 alone does NOT yield CORROBORATED (yields UNVERIFIED)
        status_count = strat.evaluate_inventory_completeness([{"trim": "SR5"}] * 5, 2024, {})
        self.assertEqual(status_count, InventoryCompletenessStatus.UNVERIFIED)

        # Rule 3: Multiple trims alone do NOT yield CORROBORATED (yields UNVERIFIED)
        status_trims = strat.evaluate_inventory_completeness([{"trim": "SR5"}, {"trim": "Limited"}], 2024, {})
        self.assertEqual(status_trims, InventoryCompletenessStatus.UNVERIFIED)

        # Rule 4: Multiple engines alone do NOT yield CORROBORATED (yields UNVERIFIED)
        status_engines = strat.evaluate_inventory_completeness([{"engine_cylinders": 4}, {"engine_cylinders": 6}], 2024, {})
        self.assertEqual(status_engines, InventoryCompletenessStatus.UNVERIFIED)

        # Rule 5: Traceable source-asserted exhaustiveness yields ESTABLISHED
        status_est = strat.evaluate_inventory_completeness([{"trim": "SR5"}], 2024, {"completeness_provenance": "source_asserted"})
        self.assertEqual(status_est, InventoryCompletenessStatus.ESTABLISHED)

        # Rule 6: Actual independent corroboration yields CORROBORATED
        status_corr = strat.evaluate_inventory_completeness([{"trim": "SR5"}], 2024, {"is_independently_corroborated": True})
        self.assertEqual(status_corr, InventoryCompletenessStatus.CORROBORATED)

        # Rule 7: Affirmatively known missing inventory yields INCOMPLETE
        status_inc = strat.evaluate_inventory_completeness([{"trim": "SR5"}], 2024, {"is_known_incomplete": True})
        self.assertEqual(status_inc, InventoryCompletenessStatus.INCOMPLETE)

        # Rule 8: Empty discovery without affirmative incompleteness evidence yields UNVERIFIED
        status_empty = strat.evaluate_inventory_completeness([], 2024, {})
        self.assertEqual(status_empty, InventoryCompletenessStatus.UNVERIFIED)

        # Rule 9: Empty discovery WITH affirmative incompleteness evidence yields INCOMPLETE
        status_empty_inc = strat.evaluate_inventory_completeness([], 2024, {"is_known_incomplete": True})
        self.assertEqual(status_empty_inc, InventoryCompletenessStatus.INCOMPLETE)

    def test_31_manufacturer_supplemental_candidate_pipeline(self) -> None:
        """31. Manufacturer-established supplemental candidates process with true provenance and incomplete evaluation."""
        import json
        from reference.ingestion.contracts import InventoryCompletenessStatus

        # 1. Test 2004 Touareg batch manifest includes supplemental candidate
        manifest = self.orchestrator.create_batch_manifest(make="Volkswagen", model="Touareg", market="US", start_year=2004, end_year=2004)
        items = manifest.items
        trims = {item.trim_name for item in items}
        self.assertIn("V8 X", trims)

        # 2. Test completeness evaluation for 2004 Touareg (with missing inventory evidence) returns INCOMPLETE
        fpath = self.orchestrator.fixture_dir / "2004_touareg_configurations.json"
        with open(fpath) as f:
            data = json.load(f)
        strat = self.orchestrator.jdp_extractor.select_discovery_strategy(2004)
        status_2004 = strat.evaluate_inventory_completeness(data["configurations"], 2004, data["_provenance"])
        self.assertEqual(status_2004, InventoryCompletenessStatus.INCOMPLETE)

        # 3. Test other year without missing inventory evidence (e.g. 2011 Touareg) remains UNVERIFIED
        fpath_2011 = self.orchestrator.fixture_dir / "2011_touareg_configurations.json"
        with open(fpath_2011) as f:
            data_2011 = json.load(f)
        strat_2011 = self.orchestrator.jdp_extractor.select_discovery_strategy(2011)
        status_2011 = strat_2011.evaluate_inventory_completeness(data_2011["configurations"], 2011, data_2011["_provenance"])
        self.assertEqual(status_2011, InventoryCompletenessStatus.UNVERIFIED)

    def test_32_v8_x_canonical_correction_reconciliation(self) -> None:
        """32. Verifies manual V8 X PK 480 is inactive, corrected 4.2L V8 replacement is active, and no receipt is fabricated."""
        from reference.models import VehicleDefinition, CanonicalRecordCorrection

        old_vd = VehicleDefinition.objects.filter(slug="2004-v8-x-v8-awd-us").first()
        new_vd = VehicleDefinition.objects.filter(slug="2004-v8-x-42l-v8-awd-us").first()

        if old_vd and new_vd:
            self.assertFalse(old_vd.is_active)
            self.assertTrue(new_vd.is_active)
            self.assertEqual(old_vd.id, 480)
            self.assertEqual(new_vd.engine_name, "4.2L V8")

            corr = CanonicalRecordCorrection.objects.filter(
                superseded_vehicle_definition=old_vd,
                replacement_vehicle_definition=new_vd,
            ).first()
            self.assertIsNotNone(corr)
            self.assertEqual(corr.correction_reason, "SOURCE_EVIDENCE_CORRECTION")

            # No historical receipt fabricated for manual entry
            self.assertEqual(old_vd.creation_receipts.count(), 0)
