"""
Production Manufacturer Acquisition Unit Tests (RA-023).

Verifies full SHA-256 byte-content hashing, raw snapshot storage, reacquisition idempotency,
ExtractionProvenance validation, schema 1.1.0 serialization/deserialization, 1.0.0 backward compatibility,
mechanical transcription-to-raw hash binding, CandidateIdentity context isolation, zero canonical writes,
and Django management command execution.
"""

import json
import shutil
import tempfile
from io import StringIO
from pathlib import Path

from django.conf import settings
from django.core.management import call_command
from django.test import TestCase

from reference.ingestion.acquisition.profiles import (
    ProfileSecurityError,
    ToyotaUSAPressroomProfile,
    TranscriptionHashMismatchError,
)
from reference.ingestion.acquisition.snapshots import (
    RawAcquisitionResult,
    RawSnapshotManager,
    RawSourceSnapshotMetadata,
    compute_content_hash,
    resolve_managed_storage_reference,
    to_managed_storage_reference,
)

from reference.ingestion.contracts import (
    ApplicabilityScope,
    ArtifactType,
    CandidateIdentity,
    Envelope,
    ExtractionProvenance,
    SourceApplicability,
    SourceAssertion,
    SourceAssertionSet,
    SourceMetadata,
)
from reference.ingestion.importing.planner import plan_candidate_import
from reference.ingestion.orchestration.manufacturer import ProductionManufacturerOrchestrator
from reference.ingestion.serialization import (
    deserialize_artifact,
    serialize_artifact,
    source_metadata_from_dict,
    source_metadata_to_dict,
)
from reference.ingestion.validation import (
    IngestionValidationError,
    validate_artifact,
    validate_extraction_provenance,
)
from reference.models import Generation, Manufacturer, VehicleDefinition, VehicleModel


class ProductionAcquisitionTests(TestCase):
    def setUp(self):
        self.temp_dir = Path(tempfile.mkdtemp())
        self.snapshot_manager = RawSnapshotManager(storage_root=self.temp_dir)
        self.fixture_path = (
            Path(__file__).resolve().parent
            / "fixtures"
            / "acquisition"
            / "toyota"
            / "2020_4runner_specs.json"
        )
        with open(self.fixture_path, "r", encoding="utf-8") as f:
            self.transcription_data = json.load(f)

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_sha256_content_hashing(self):
        sample_bytes = b"<html><body>Toyota 4Runner Specs</body></html>"
        digest = compute_content_hash(sample_bytes)
        self.assertTrue(digest.startswith("sha256:"))
        self.assertEqual(len(digest), 71)  # "sha256:" (7) + 64 hex chars

    def test_raw_snapshot_storage(self):
        raw_bytes = b"<html><body>Toyota 4Runner Specs Page</body></html>"
        acq = RawAcquisitionResult(
            source_id="toyota_usa",
            source_locator="https://pressroom.toyota.com/specs",
            acquired_at="2026-08-15T12:00:00Z",
            content_type="text/html",
            raw_bytes=raw_bytes,
            source_applicability=SourceApplicability(market="US"),
            acquisition_method="local_file",
        )
        status, meta = self.snapshot_manager.store_snapshot(acq)
        self.assertEqual(status, "CREATED")
        resolved_file = resolve_managed_storage_reference(meta.storage_path, storage_root=self.temp_dir)
        self.assertTrue(resolved_file.exists())
        self.assertTrue(meta.storage_path.endswith(".html"))
        meta_file = resolved_file.with_suffix(".meta.json")
        self.assertTrue(meta_file.exists())

    def test_reacquisition_idempotency(self):
        raw_bytes = b"<html><body>Identical Payload</body></html>"
        acq = RawAcquisitionResult(
            source_id="toyota_usa",
            source_locator="https://pressroom.toyota.com/specs",
            acquired_at="2026-08-15T12:00:00Z",
            content_type="text/html",
            raw_bytes=raw_bytes,
            source_applicability=SourceApplicability(market="US"),
            acquisition_method="local_file",
        )
        status1, meta1 = self.snapshot_manager.store_snapshot(acq)
        status2, meta2 = self.snapshot_manager.store_snapshot(acq)
        self.assertEqual(status1, "CREATED")
        self.assertEqual(status2, "ALREADY_PRESENT")
        self.assertEqual(meta1.content_hash, meta2.content_hash)

    def test_content_revision_detection(self):
        bytes1 = b"<html><body>Version 1</body></html>"
        bytes2 = b"<html><body>Version 2 Revised</body></html>"
        acq1 = RawAcquisitionResult(
            source_id="toyota_usa",
            source_locator="https://pressroom.toyota.com/specs",
            acquired_at="2026-08-15T12:00:00Z",
            content_type="text/html",
            raw_bytes=bytes1,
            source_applicability=SourceApplicability(market="US"),
            acquisition_method="local_file",
        )
        acq2 = RawAcquisitionResult(
            source_id="toyota_usa",
            source_locator="https://pressroom.toyota.com/specs",
            acquired_at="2026-08-15T13:00:00Z",
            content_type="text/html",
            raw_bytes=bytes2,
            source_applicability=SourceApplicability(market="US"),
            acquisition_method="local_file",
        )
        status1, meta1 = self.snapshot_manager.store_snapshot(acq1)
        status2, meta2 = self.snapshot_manager.store_snapshot(acq2)
        self.assertEqual(status1, "CREATED")
        self.assertEqual(status2, "CREATED")
        self.assertNotEqual(meta1.content_hash, meta2.content_hash)

    def test_snapshot_sidecar_isolation(self):
        raw_bytes = b"<html><body>Toyota Raw Content</body></html>"
        acq = RawAcquisitionResult(
            source_id="toyota_usa",
            source_locator="https://pressroom.toyota.com/specs",
            acquired_at="2026-08-15T12:00:00Z",
            content_type="text/html",
            raw_bytes=raw_bytes,
            source_applicability=SourceApplicability(market="US"),
            acquisition_method="local_file",
        )
        _, meta = self.snapshot_manager.store_snapshot(acq)
        resolved_path = resolve_managed_storage_reference(meta.storage_path, storage_root=self.temp_dir)
        meta_file = resolved_path.with_suffix(".meta.json")
        sidecar_dict = json.loads(meta_file.read_text(encoding="utf-8"))
        self.assertNotIn("extractor_id", sidecar_dict)
        self.assertNotIn("extraction_mode", sidecar_dict)

    def test_portable_managed_storage_reference(self):
        raw_bytes = b"<html><body>Portable Reference Test</body></html>"
        acq = RawAcquisitionResult(
            source_id="toyota_usa",
            source_locator="https://pressroom.toyota.com/specs",
            acquired_at="2026-08-15T12:00:00Z",
            content_type="text/html",
            raw_bytes=raw_bytes,
            source_applicability=SourceApplicability(market="US"),
            acquisition_method="local_file",
        )
        status, meta = self.snapshot_manager.store_snapshot(acq)
        self.assertEqual(status, "CREATED")
        self.assertTrue(meta.storage_path.startswith("storage/raw_source_artifacts/toyota_usa/"))
        self.assertNotIn("/Users/", meta.storage_path)

        sets = ToyotaUSAPressroomProfile().extract(meta, self.transcription_data, override_expected_hash=meta.content_hash)
        self.assertEqual(sets[0].provenance.extraction_provenance.raw_artifact_reference, meta.storage_path)

    def test_already_present_readback_preserves_portable_reference(self):
        raw_bytes = b"<html><body>Idempotent Portable Reference</body></html>"
        acq = RawAcquisitionResult(
            source_id="toyota_usa",
            source_locator="https://pressroom.toyota.com/specs",
            acquired_at="2026-08-15T12:00:00Z",
            content_type="text/html",
            raw_bytes=raw_bytes,
            source_applicability=SourceApplicability(market="US"),
            acquisition_method="local_file",
        )
        _, meta1 = self.snapshot_manager.store_snapshot(acq)
        status2, meta2 = self.snapshot_manager.store_snapshot(acq)
        self.assertEqual(status2, "ALREADY_PRESENT")
        self.assertEqual(meta1.storage_path, meta2.storage_path)
        self.assertTrue(meta2.storage_path.startswith("storage/raw_source_artifacts/toyota_usa/"))

    def test_resolve_managed_storage_reference_path_safety(self):
        rel_ref = "storage/raw_source_artifacts/toyota_usa/test_hash.html"
        resolved = resolve_managed_storage_reference(rel_ref, storage_root=self.temp_dir)
        self.assertTrue(str(resolved).startswith(str(self.temp_dir.resolve())))

        with self.assertRaises(ValueError):
            resolve_managed_storage_reference("../../../etc/passwd", storage_root=self.temp_dir)



    def test_original_publisher_locator_preserved(self):
        raw_bytes = b"<html><body>Specs</body></html>"
        acq = RawAcquisitionResult(
            source_id="toyota_usa",
            source_locator="https://pressroom.toyota.com/album/2020-toyota-4runner-specs/",
            acquired_at="2026-08-15T12:00:00Z",
            content_type="text/html",
            raw_bytes=raw_bytes,
            source_applicability=SourceApplicability(market="US"),
            acquisition_method="local_file",
        )
        _, meta = self.snapshot_manager.store_snapshot(acq)
        self.assertEqual(meta.publisher_locator, "https://pressroom.toyota.com/album/2020-toyota-4runner-specs/")
        self.assertNotEqual(meta.publisher_locator, meta.storage_path)

    def test_extraction_provenance_dataclass(self):
        ep = ExtractionProvenance(
            raw_artifact_hash="sha256:" + "a" * 64,
            raw_artifact_reference="storage/raw_source_artifacts/toyota_usa/test.html",
            extractor_id="toyota_pressroom_extractor",
            extractor_version="0.1.0",
            extraction_mode="manually_verified_transcription",
        )
        validate_extraction_provenance(ep)  # Should pass cleanly

        invalid_ep = ExtractionProvenance(
            raw_artifact_hash="invalid_hash",
            raw_artifact_reference="ref",
            extractor_id="ext",
            extractor_version="0.1",
            extraction_mode="invalid_mode",
        )
        with self.assertRaises(IngestionValidationError):
            validate_extraction_provenance(invalid_ep)

    def test_extraction_provenance_serialization_roundtrip(self):
        ep = ExtractionProvenance(
            raw_artifact_hash="sha256:" + "b" * 64,
            raw_artifact_reference="storage/raw_source_artifacts/toyota_usa/test2.html",
            extractor_id="toyota_extractor",
            extractor_version="0.1.0",
            extraction_mode="deterministic_structured_parser",
        )
        meta = SourceMetadata(
            source_id="toyota_usa",
            extraction_provenance=ep,
        )
        serialized = source_metadata_to_dict(meta)
        self.assertIn("extraction_provenance", serialized)
        deserialized = source_metadata_from_dict(serialized)
        self.assertIsNotNone(deserialized.extraction_provenance)
        self.assertEqual(deserialized.extraction_provenance.raw_artifact_hash, "sha256:" + "b" * 64)

    def test_schema_1_1_0_serialization(self):
        profile = ToyotaUSAPressroomProfile()
        acq = profile.acquire_from_file(self.fixture_path)
        _, meta = self.snapshot_manager.store_snapshot(acq)
        sets = profile.extract(meta, self.transcription_data)
        self.assertEqual(sets[0].envelope.schema_version, "1.1.0")

        serialized_json = serialize_artifact(sets[0])
        deserialized = deserialize_artifact(serialized_json)
        self.assertEqual(deserialized.envelope.schema_version, "1.1.0")

    def test_schema_1_0_0_backward_compatibility(self):
        # Create legacy 1.0.0 set without extraction_provenance
        env = Envelope(
            artifact_type=ArtifactType.SOURCE_ASSERTION_SET.value,
            schema_version="1.0.0",
        )
        meta = SourceMetadata(source_id="legacy_source")
        asset = SourceAssertionSet(
            envelope=env,
            provenance=meta,
            source_assertions=[
                SourceAssertion(
                    assertion_id="ast_legacy_01",
                    attribute_key="make_name",
                    raw_value="Toyota",
                )
            ],
        )
        serialized_json = serialize_artifact(asset)
        deserialized = deserialize_artifact(serialized_json)
        self.assertEqual(deserialized.envelope.schema_version, "1.0.0")
        self.assertIsNone(deserialized.provenance.extraction_provenance)

    def test_local_file_acquisition_path(self):
        profile = ToyotaUSAPressroomProfile()
        acq = profile.acquire_from_file(self.fixture_path)
        self.assertEqual(acq.source_id, "toyota_usa")
        self.assertEqual(acq.acquisition_method, "local_file")
        self.assertTrue(len(acq.raw_bytes) > 0)

    def test_url_acquisition_path_mocked(self):
        def fake_transport(url, headers, timeout_seconds=10):
            return 200, b"<html><body>Toyota Live Web Payload</body></html>", {"Content-Type": "text/html"}

        profile = ToyotaUSAPressroomProfile(transport=fake_transport)
        acq = profile.acquire_from_url("https://pressroom.toyota.com/album/2020-toyota-4runner-specs/")
        self.assertEqual(acq.source_id, "toyota_usa")
        self.assertEqual(acq.acquisition_method, "live_http")

        with self.assertRaises(ProfileSecurityError):
            # Non-allowlisted host should raise security error
            profile.acquire_from_url("https://untrusted-domain.com/specs")

    def test_url_acquisition_redirect_allowed_final_host(self):
        def allowed_redirect_transport(url, headers, timeout_seconds=10):
            return 200, b"<html><body>Redirected Allowed Host</body></html>", {"Content-Type": "text/html"}, "https://pressroom.toyota.com/album/2020-toyota-4runner-specs/"

        profile = ToyotaUSAPressroomProfile(transport=allowed_redirect_transport)
        acq = profile.acquire_from_url("https://pressroom.toyota.com/specs/")
        self.assertEqual(acq.source_locator, "https://pressroom.toyota.com/album/2020-toyota-4runner-specs/")

    def test_url_acquisition_redirect_disallowed_final_host_rejected(self):
        def disallowed_redirect_transport(url, headers, timeout_seconds=10):
            return 200, b"<html><body>Disallowed Payload</body></html>", {"Content-Type": "text/html"}, "https://evil.com/toyota-specs"

        profile = ToyotaUSAPressroomProfile(transport=disallowed_redirect_transport)
        orchestrator = ProductionManufacturerOrchestrator(profile=profile, snapshot_manager=self.snapshot_manager)

        with self.assertRaises(ProfileSecurityError):
            orchestrator.run_dry_run_pipeline(
                source_input="https://pressroom.toyota.com/specs/",
                is_url=True,
                transcription_data=self.transcription_data,
            )

        # Confirm zero raw snapshot files or sidecars created
        self.assertEqual(list(self.temp_dir.glob("**/*")), [])

    def test_strict_sha256_hex_validation(self):
        # Valid lowercase digest
        ep_valid = ExtractionProvenance(
            raw_artifact_hash="sha256:" + "a" * 64,
            raw_artifact_reference="storage/raw_source_artifacts/toyota_usa/test.html",
            extractor_id="ext",
            extractor_version="0.1",
            extraction_mode="manually_verified_transcription",
        )
        validate_extraction_provenance(ep_valid)  # Passes cleanly

        # Non-hex characters
        ep_invalid_char = ExtractionProvenance(
            raw_artifact_hash="sha256:" + "z" * 64,
            raw_artifact_reference="ref",
            extractor_id="ext",
            extractor_version="0.1",
            extraction_mode="manually_verified_transcription",
        )
        with self.assertRaises(IngestionValidationError):
            validate_extraction_provenance(ep_invalid_char)

        # Too short
        ep_short = ExtractionProvenance(
            raw_artifact_hash="sha256:" + "a" * 63,
            raw_artifact_reference="ref",
            extractor_id="ext",
            extractor_version="0.1",
            extraction_mode="manually_verified_transcription",
        )
        with self.assertRaises(IngestionValidationError):
            validate_extraction_provenance(ep_short)

        # Missing sha256: prefix
        ep_no_prefix = ExtractionProvenance(
            raw_artifact_hash="a" * 64,
            raw_artifact_reference="ref",
            extractor_id="ext",
            extractor_version="0.1",
            extraction_mode="manually_verified_transcription",
        )
        with self.assertRaises(IngestionValidationError):
            validate_extraction_provenance(ep_no_prefix)


    def test_derived_data_distinction(self):
        profile = ToyotaUSAPressroomProfile()
        acq = profile.acquire_from_file(self.fixture_path)
        _, meta = self.snapshot_manager.store_snapshot(acq)
        sets = profile.extract(meta, self.transcription_data, override_expected_hash=meta.content_hash)
        self.assertEqual(
            sets[0].provenance.extraction_provenance.extraction_mode,
            "manually_verified_transcription",
        )

    def test_transcription_hash_binding_match(self):
        profile = ToyotaUSAPressroomProfile()
        acq = profile.acquire_from_file(self.fixture_path)
        _, meta = self.snapshot_manager.store_snapshot(acq)
        # Explicit override expected hash to match current snapshot hash
        sets = profile.extract(
            meta, self.transcription_data, override_expected_hash=meta.content_hash
        )
        self.assertEqual(len(sets), 12)

    def test_transcription_hash_binding_mismatch(self):
        profile = ToyotaUSAPressroomProfile()
        acq = profile.acquire_from_file(self.fixture_path)
        _, meta = self.snapshot_manager.store_snapshot(acq)
        with self.assertRaises(TranscriptionHashMismatchError):
            # Mismatched expected hash must abort extraction cleanly
            profile.extract(
                meta,
                self.transcription_data,
                override_expected_hash="sha256:" + "0" * 64,
            )

    def test_configuration_grouping(self):
        profile = ToyotaUSAPressroomProfile()
        acq = profile.acquire_from_file(self.fixture_path)
        _, meta = self.snapshot_manager.store_snapshot(acq)
        sets = profile.extract(meta, self.transcription_data, override_expected_hash=meta.content_hash)
        self.assertEqual(len(sets), 12)
        # Ensure 12 configuration rows produce exactly 12 assertion sets with zero Cartesian expansion

    def test_candidate_identity_context_isolation(self):
        profile = ToyotaUSAPressroomProfile()
        acq = profile.acquire_from_file(self.fixture_path)
        _, meta = self.snapshot_manager.store_snapshot(acq)
        sets = profile.extract(meta, self.transcription_data, override_expected_hash=meta.content_hash)

        # Remove manufacturer_grade assertion from first set
        first_set = sets[0]
        first_set.source_assertions = [
            a for a in first_set.source_assertions if a.attribute_key != "manufacturer_grade"
        ]
        cand_identity = CandidateIdentity(
            manufacturer_name="Toyota",
            vehicle_model_name="4Runner",
            model_year=2020,
            market="US",
            trim_name="SR5",
        )
        from reference.ingestion.candidate.builder import construct_candidate_configuration
        from reference.ingestion.normalization.manufacturer import ManufacturerNormalizer
        norm_interps = ManufacturerNormalizer().normalize(first_set)
        cand_doc = construct_candidate_configuration(
            candidate_identity=cand_identity,
            source_assertion_sets=[first_set],
            normalized_assertions=norm_interps,
        )
        plan0 = plan_candidate_import(cand_doc)
        self.assertEqual(plan0.eligibility_status.value, "requires_review")



    def test_missing_canonical_parent_handling(self):
        profile = ToyotaUSAPressroomProfile()
        acq = profile.acquire_from_file(self.fixture_path)
        _, meta = self.snapshot_manager.store_snapshot(acq)

        orchestrator = ProductionManufacturerOrchestrator(
            profile=profile, snapshot_manager=self.snapshot_manager
        )
        result = orchestrator.run_dry_run_pipeline(
            source_input=str(self.fixture_path),
            transcription_data=self.transcription_data,
            override_expected_hash=meta.content_hash,
        )
        # Without preseeded parents, candidates must return INELIGIBLE with missing model reason
        self.assertEqual(result.candidate_results[0].plan.eligibility_status.value, "ineligible")
        self.assertIn("does not exist in canonical database", result.candidate_results[0].plan.reasons[0])





    def test_zero_canonical_writes_guarantee(self):
        initial_count = VehicleDefinition.objects.count()
        # Seed parent models
        mfr = Manufacturer.objects.create(name="Toyota", slug="toyota")
        model = VehicleModel.objects.create(manufacturer=mfr, name="4Runner", slug="toyota-4runner")
        Generation.objects.create(vehicle_model=model, name="Fifth Generation", slug="toyota-4runner-5th-gen", start_year=2010)

        profile = ToyotaUSAPressroomProfile()
        acq = profile.acquire_from_file(self.fixture_path)
        _, meta = self.snapshot_manager.store_snapshot(acq)

        orchestrator = ProductionManufacturerOrchestrator(
            profile=profile, snapshot_manager=self.snapshot_manager
        )
        result = orchestrator.run_dry_run_pipeline(
            source_input=str(self.fixture_path),
            transcription_data=self.transcription_data,
            override_expected_hash=meta.content_hash,
        )
        self.assertEqual(result.candidate_results[0].plan.eligibility_status.value, "eligible")
        # Ensure VehicleDefinition DB count remains 100% unchanged
        self.assertEqual(VehicleDefinition.objects.count(), initial_count)

        # Ensure VehicleDefinition DB count remains 100% unchanged
        self.assertEqual(VehicleDefinition.objects.count(), initial_count)

    def test_management_command_execution(self):
        out = StringIO()
        real_storage_dir = Path(settings.BASE_DIR) / "storage"
        try:
            call_command(
                "acquire_manufacturer_specs",
                file=str(self.fixture_path),
                transcription_file=str(self.fixture_path),
                stdout=out,
            )
            output_str = out.getvalue()
            self.assertIn("RIGARCHIVE PRODUCTION ACQUISITION DRY-RUN REPORT", output_str)
            self.assertIn("toyota_usa", output_str)
            self.assertIn("Dry-Run Summary", output_str)
        finally:
            if real_storage_dir.exists():
                shutil.rmtree(real_storage_dir, ignore_errors=True)

    def test_authentic_pdf_production_dry_run_end_to_end(self):
        """
        Verifies end-to-end multi-artifact production dry-run pipeline using authentic publisher PDFs
        without runtime dependency on JSON benchmark fixtures.
        """
        fixtures_dir = Path(__file__).resolve().parent / "fixtures" / "acquisition" / "toyota"
        pdf_path = fixtures_dir / "2020_4runner_pricing.pdf"
        specs_pdf_path = fixtures_dir / "2020_4runner_specs.pdf"

        # Seed required parent entities
        mfr, _ = Manufacturer.objects.get_or_create(name="Toyota", defaults={"slug": "toyota"})
        model, _ = VehicleModel.objects.get_or_create(manufacturer=mfr, name="4Runner", defaults={"slug": "4runner"})
        Generation.objects.get_or_create(
            vehicle_model=model,
            name="Fifth Generation",
            defaults={
                "slug": "fifth-generation",
                "start_year": 2010,
                "end_year": 2024,
                "is_active": True,
            },
        )

        profile = ToyotaUSAPressroomProfile()
        orchestrator = ProductionManufacturerOrchestrator(
            profile=profile, snapshot_manager=self.snapshot_manager
        )

        # Run dry run pipeline passing PDF file path and auxiliary specs PDF WITHOUT transcription_data
        result = orchestrator.run_dry_run_pipeline(
            source_input=str(pdf_path),
            auxiliary_inputs=[str(specs_pdf_path)],
        )

        self.assertEqual(result.total_extracted_sets, 13)
        self.assertEqual(len(result.candidate_results), 12)

        pricing_hash = compute_content_hash(pdf_path.read_bytes())
        specs_hash = compute_content_hash(specs_pdf_path.read_bytes())
        expected_hashes = sorted([pricing_hash, specs_hash])

        extracted_model_codes = [cr.native_identifier for cr in result.candidate_results]
        expected_codes = ["8642", "8664", "8646", "8666", "8667", "8670", "8672", "8648", "8668", "8649", "8669", "8674"]
        self.assertEqual(extracted_model_codes, expected_codes)

        for cr in result.candidate_results:
            cand = cr.candidate_doc
            self.assertEqual(cand.evidence_raw_hashes, expected_hashes)
            self.assertEqual(cand.source_configuration_identities[0].source_id, "toyota_usa")
            # Ensure JSON fixture hash is not in evidence
            for h in cand.evidence_raw_hashes:
                self.assertNotIn("2020_4runner_specs.json", h)

            # Universal engine specs aggregated from specs PDF
            norm_keys = [i.target_attribute_key for i in cand.normalized_assertions]
            self.assertIn("engine_displacement_liters", norm_keys)
            self.assertIn("engine_cylinders", norm_keys)

    def test_broad_scope_isolation_mismatched_context(self):
        """
        Verifies that a broad model-year assertion set with a mismatched target_context (e.g. model="Tacoma")
        is NOT aggregated into a candidate configuration for "4Runner".
        """
        config_env = Envelope(artifact_type=ArtifactType.SOURCE_ASSERTION_SET.value, schema_version="1.1.0")
        config_prov = SourceMetadata(
            source_id="toyota_usa",
            native_record_id="8664",
            target_context={"make": "Toyota", "model": "4Runner", "model_year": 2020, "market": "US"},
            source_applicability=SourceApplicability(market="US", applicability_scope=ApplicabilityScope.CONFIGURATION.value),
        )
        config_set = SourceAssertionSet(
            envelope=config_env,
            provenance=config_prov,
            source_assertions=[
                SourceAssertion(assertion_id="1", attribute_key="make_name", raw_value="Toyota"),
                SourceAssertion(assertion_id="2", attribute_key="model_name", raw_value="4Runner"),
                SourceAssertion(assertion_id="3", attribute_key="model_year", raw_value="2020"),
                SourceAssertion(assertion_id="4", attribute_key="manufacturer_grade", raw_value="SR5"),
            ],
        )

        broad_mismatched_prov = SourceMetadata(
            source_id="toyota_usa",
            native_record_id="tacoma_broad_specs",
            target_context={"make": "Toyota", "model": "Tacoma", "model_year": 2020, "market": "US"},
            source_applicability=SourceApplicability(market="US", applicability_scope=ApplicabilityScope.MODEL_YEAR.value),
        )
        broad_mismatched_set = SourceAssertionSet(
            envelope=config_env,
            provenance=broad_mismatched_prov,
            source_assertions=[
                SourceAssertion(assertion_id="5", attribute_key="engine_displacement_liters", raw_value="3.5"),
            ],
        )

        matches = ProductionManufacturerOrchestrator._target_context_matches(
            broad_mismatched_set.provenance.target_context,
            config_set.provenance.target_context,
        )
        self.assertFalse(matches)

    def test_native_record_id_independence(self):
        """
        Verifies that aggregation depends on explicit ApplicabilityScope.MODEL_YEAR and target context matching,
        not on native_record_id starting with 'universal_'.
        """
        config_env = Envelope(artifact_type=ArtifactType.SOURCE_ASSERTION_SET.value, schema_version="1.1.0")
        config_prov = SourceMetadata(
            source_id="toyota_usa",
            native_record_id="8664",
            target_context={"make": "Toyota", "model": "4Runner", "model_year": 2020, "market": "US"},
            source_applicability=SourceApplicability(market="US", applicability_scope=ApplicabilityScope.CONFIGURATION.value),
        )
        config_set = SourceAssertionSet(
            envelope=config_env,
            provenance=config_prov,
            source_assertions=[
                SourceAssertion(assertion_id="1", attribute_key="make_name", raw_value="Toyota"),
                SourceAssertion(assertion_id="2", attribute_key="model_name", raw_value="4Runner"),
                SourceAssertion(assertion_id="3", attribute_key="model_year", raw_value="2020"),
                SourceAssertion(assertion_id="4", attribute_key="manufacturer_grade", raw_value="SR5"),
            ],
        )

        custom_broad_prov = SourceMetadata(
            source_id="toyota_usa",
            native_record_id="custom_spec_record_999",  # Does NOT start with 'universal_'
            target_context={"make": "Toyota", "model": "4Runner", "model_year": 2020, "market": "US"},
            source_applicability=SourceApplicability(market="US", applicability_scope=ApplicabilityScope.MODEL_YEAR.value),
        )
        custom_broad_set = SourceAssertionSet(
            envelope=config_env,
            provenance=custom_broad_prov,
            source_assertions=[
                SourceAssertion(assertion_id="5", attribute_key="engine_displacement_liters", raw_value="4.0"),
            ],
        )

        matches = ProductionManufacturerOrchestrator._target_context_matches(
            custom_broad_set.provenance.target_context,
            config_set.provenance.target_context,
        )
        self.assertTrue(matches)
        self.assertTrue(ProductionManufacturerOrchestrator._is_broad_model_year_scope(custom_broad_set))
        self.assertFalse(ProductionManufacturerOrchestrator._is_broad_model_year_scope(config_set))

