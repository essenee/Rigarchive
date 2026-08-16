"""
Regression and Semantic Audit Tests for Drivetrain Preservation & Display (RA-029).

Verifies:
1. Full-time 4WD normalizes to generic 4WD.
2. Full-time 4WD preserves drivetrain_architecture = "Full-time 4WD".
3. Part-time 4WD normalizes to generic 4WD.
4. Part-time 4WD preserves drivetrain_architecture = "Part-time 4WD".
5. True AWD source terminology still normalizes to AWD.
6. Toyota Limited Full-time 4WD does not become AWD.
7. Candidate identity uses 4WD for Full-time 4WD.
8. Public presentation displays 2WD, 4WD, AWD rather than expanded wording.
9. Existing richer drivetrain normalization is preserved.
10. 2019/2020 ingestion tests reflect corrected Limited drivetrain semantics.
"""

from pathlib import Path
from django.test import TestCase

from reference.ingestion.acquisition.profiles import JDPowerProfile, ToyotaUSAPressroomProfile
from reference.ingestion.candidate.builder import construct_candidate_configuration
from reference.ingestion.contracts import CandidateIdentity
from reference.ingestion.normalization.jd_power import JDPowerNormalizer
from reference.ingestion.normalization.manufacturer import ManufacturerNormalizer
from reference.ingestion.normalization.rules.toyota_rules import normalize_toyota_drivetrain
from reference.models import Generation, Manufacturer, VehicleDefinition, VehicleModel


class DrivetrainPreservationTests(TestCase):
    """RA-029 Drivetrain Semantic Preservation and Public Display Tests."""

    def test_full_time_4wd_normalizes_to_generic_4wd(self):
        """1. Full-time 4WD normalizes to generic 4WD."""
        generic_drive, drive_arch = normalize_toyota_drivetrain("Full-Time 4WD")
        self.assertEqual(generic_drive, "4WD")

    def test_full_time_4wd_preserves_architecture(self):
        """2. Full-time 4WD preserves architecture = Full-time 4WD."""
        generic_drive, drive_arch = normalize_toyota_drivetrain("Full-Time 4WD")
        self.assertEqual(drive_arch, "Full-time 4WD")

    def test_part_time_4wd_normalizes_to_generic_4wd(self):
        """3. Part-time 4WD normalizes to generic 4WD."""
        generic_drive, drive_arch = normalize_toyota_drivetrain("Part-Time 4WD")
        self.assertEqual(generic_drive, "4WD")

    def test_part_time_4wd_preserves_architecture(self):
        """4. Part-time 4WD preserves architecture = Part-time 4WD."""
        generic_drive, drive_arch = normalize_toyota_drivetrain("Part-Time 4WD")
        self.assertEqual(drive_arch, "Part-time 4WD")

    def test_true_awd_normalizes_to_awd(self):
        """5. True AWD source terminology still normalizes to AWD."""
        generic_drive, drive_arch = normalize_toyota_drivetrain("AWD")
        self.assertEqual(generic_drive, "AWD")

        generic_drive_2, _ = normalize_toyota_drivetrain("ALL-WHEEL DRIVE")
        self.assertEqual(generic_drive_2, "AWD")

    def test_toyota_limited_full_time_4wd_does_not_become_awd(self):
        """6. Toyota Limited Full-time 4WD does not become AWD."""
        profile = ToyotaUSAPressroomProfile()
        normalizer = ManufacturerNormalizer()
        from reference.ingestion.acquisition.snapshots import RawSourceSnapshotMetadata
        meta = RawSourceSnapshotMetadata(
            source_id="toyota_usa",
            publisher_locator="https://pressroom.toyota.com/vehicle/2020-toyota-4runner/",
            acquired_at="2026-08-15T18:00:00Z",
            content_type="application/json",
            content_hash="sha256:0000000000000000000000000000000000000000000000000000000000000000",
            storage_path="storage/test.json",
            source_applicability=profile.default_applicability,
            acquisition_method="local_file",
        )

        toyota_data = {
            "_provenance": {"publication_scope": "US", "publisher": "Toyota Motor Sales, U.S.A., Inc."},
            "configurations": [
                {
                    "model_code": "8648",
                    "make": "Toyota",
                    "model": "4Runner",
                    "model_year": 2020,
                    "grade": "Limited",
                    "drivetrain": "Full-Time 4WD",
                    "engine_displacement_liters": 4.0,
                    "engine_cylinders": 6,
                    "market": "US",
                }
            ],
        }
        sets = profile.extract(meta, transcription_data=toyota_data)
        interps = normalizer.normalize(sets[0])

        generic_interp = [i for i in interps if i.target_attribute_key == "generic_drive_classification"][0]
        arch_interp = [i for i in interps if i.target_attribute_key == "drivetrain_architecture"][0]

        self.assertEqual(generic_interp.normalized_concept, "4WD")
        self.assertNotEqual(generic_interp.normalized_concept, "AWD")
        self.assertEqual(arch_interp.normalized_concept, "Full-time 4WD")

    def test_candidate_identity_uses_4wd_for_full_time_4wd(self):
        """7. Candidate identity uses 4WD for Full-time 4WD."""
        profile = ToyotaUSAPressroomProfile()
        normalizer = ManufacturerNormalizer()
        from reference.ingestion.acquisition.snapshots import RawSourceSnapshotMetadata
        meta = RawSourceSnapshotMetadata(
            source_id="toyota_usa",
            publisher_locator="https://pressroom.toyota.com/vehicle/2020-toyota-4runner/",
            acquired_at="2026-08-15T18:00:00Z",
            content_type="application/json",
            content_hash="sha256:0000000000000000000000000000000000000000000000000000000000000000",
            storage_path="storage/test.json",
            source_applicability=profile.default_applicability,
            acquisition_method="local_file",
        )

        toyota_data = {
            "_provenance": {"publication_scope": "US", "publisher": "Toyota Motor Sales, U.S.A., Inc."},
            "configurations": [
                {
                    "model_code": "8648",
                    "make": "Toyota",
                    "model": "4Runner",
                    "model_year": 2020,
                    "grade": "Limited",
                    "drivetrain": "Full-Time 4WD",
                    "engine_displacement_liters": 4.0,
                    "engine_cylinders": 6,
                    "market": "US",
                }
            ],
        }
        sets = profile.extract(meta, transcription_data=toyota_data)
        interps = normalizer.normalize(sets[0])

        cand_id = CandidateIdentity(
            manufacturer_name="Toyota",
            vehicle_model_name="4Runner",
            model_year=2020,
            market="US",
            trim_name="Limited",
        )
        cand_doc = construct_candidate_configuration(cand_id, sets, interps)

        drive_concept = [i.normalized_concept for i in cand_doc.normalized_assertions if i.target_attribute_key == "generic_drive_classification"][0]
        self.assertEqual(drive_concept, "4WD")
        self.assertNotEqual(drive_concept, "AWD")

    def test_public_presentation_displays_abbreviated_labels(self):
        """8. Public presentation displays 2WD, 4WD, AWD rather than expanded wording."""
        mfr = Manufacturer.objects.create(name="Toyota Test", country_code="JP")
        vm = VehicleModel.objects.create(manufacturer=mfr, name="4Runner Test")
        gen = Generation.objects.create(
            vehicle_model=vm,
            name="Fifth Gen Test",
            generation_number=5,
            start_year=2010,
        )

        vd_2wd = VehicleDefinition(generation=gen, model_year=2020, trim_name="SR5", drivetrain="2WD", market="US")
        vd_4wd = VehicleDefinition(generation=gen, model_year=2020, trim_name="Limited", drivetrain="4WD", market="US")
        vd_awd = VehicleDefinition(generation=gen, model_year=2020, trim_name="Crossover", drivetrain="AWD", market="US")

        self.assertEqual(vd_2wd.get_drivetrain_display(), "2WD")
        self.assertEqual(vd_4wd.get_drivetrain_display(), "4WD")
        self.assertEqual(vd_awd.get_drivetrain_display(), "AWD")

        self.assertNotEqual(vd_2wd.get_drivetrain_display(), "Two-wheel drive")
        self.assertNotEqual(vd_4wd.get_drivetrain_display(), "Four-wheel drive")
        self.assertNotEqual(vd_awd.get_drivetrain_display(), "All-wheel drive")

    def test_existing_richer_drivetrain_normalization_preserved(self):
        """9. Existing richer drivetrain normalization is not lost by this correction."""
        g_2wd, a_2wd = normalize_toyota_drivetrain("2WD")
        self.assertEqual((g_2wd, a_2wd), ("2WD", "2WD"))

        g_pt, a_pt = normalize_toyota_drivetrain("Part-time 4WD")
        self.assertEqual((g_pt, a_pt), ("4WD", "Part-time 4WD"))

        g_ft, a_ft = normalize_toyota_drivetrain("Full-time 4WD")
        self.assertEqual((g_ft, a_ft), ("4WD", "Full-time 4WD"))

    def test_jd_power_2019_limited_normalizes_to_4wd(self):
        """10. Relevant 2019/2020 ingestion tests reflect corrected Limited drivetrain semantics."""
        profile = JDPowerProfile()
        normalizer = JDPowerNormalizer()

        fixture_path = Path("reference/tests/fixtures/acquisition/jd_power/2019_4runner_configurations.json")
        acq = profile.acquire_from_file(fixture_path)
        sets = profile.extract(None, raw_bytes=acq.raw_bytes)

        # Find Limited 4WD configuration set
        lim_set = [s for s in sets if s.provenance.native_record_id == "limited_4wd"][0]
        interps = normalizer.normalize(lim_set)

        generic_interp = [i for i in interps if i.target_attribute_key == "generic_drive_classification"][0]
        arch_interp = [i for i in interps if i.target_attribute_key == "drivetrain_architecture"][0]

        self.assertEqual(generic_interp.normalized_concept, "4WD")
        self.assertEqual(arch_interp.normalized_concept, "Full-time 4WD")
