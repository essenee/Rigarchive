"""
Comprehensive Unit Test Suite for inspect_reference_state Management Command (RA-031 Part 2 & 9).

Proves that inspect_reference_state is strictly read-only by snapshotting before/after
counts for Manufacturer, VehicleModel, Generation, VehicleDefinition, ImportExecutionReceipt,
and CanonicalRecordCorrection across all options (--summary, --inventory, filtered, --json).

Verifies zero side-effect filesystem mutations.
"""

import json, os
from io import StringIO
from django.core.management import call_command
from django.test import TestCase

from reference.models import (
    CanonicalRecordCorrection,
    Generation,
    ImportExecutionReceipt,
    Manufacturer,
    VehicleDefinition,
    VehicleModel,
)


class InspectReferenceStateHardeningTests(TestCase):
    @classmethod
    def setUpTestData(cls) -> None:
        cls.toyota = Manufacturer.objects.create(name="Toyota", country_code="JP", is_active=True)
        cls.four_runner = VehicleModel.objects.create(manufacturer=cls.toyota, name="4Runner", is_active=True)

        cls.gen4 = Generation.objects.create(
            vehicle_model=cls.four_runner,
            name="Fourth Generation",
            slug="fourth-generation",
            generation_number=4,
            start_year=2003,
            end_year=2009,
            is_active=True,
        )

        cls.vd1 = VehicleDefinition.objects.create(
            generation=cls.gen4,
            model_year=2005,
            trim_name="Sport Edition",
            engine_name="4.7L V8",
            drivetrain=VehicleDefinition.Drivetrain.FOUR_WHEEL_DRIVE,
            market=VehicleDefinition.Market.UNITED_STATES,
            is_active=True,
        )

        cls.vd2 = VehicleDefinition.objects.create(
            generation=cls.gen4,
            model_year=2005,
            trim_name="SR5",
            engine_name="4.0L V6",
            drivetrain=VehicleDefinition.Drivetrain.TWO_WHEEL_DRIVE,
            market=VehicleDefinition.Market.UNITED_STATES,
            is_active=True,
        )

        cls.receipt = ImportExecutionReceipt.objects.create(
            operator_label="cli:test",
            execution_channel="cli",
            manifest_hash="sha256:" + "0" * 64,
            candidate_reference="cand_ref_test",
            planned_action="create",
            create_basis="first_representation",
            source_id="test_source",
            raw_artifact_hash="sha256:" + "1" * 64,
            raw_artifact_reference="test_ref",
            source_identity_type="record_id",
            native_identifier="native_1",
            resolved_generation_id=cls.gen4.pk,
            target_slug=cls.vd1.slug,
            target_model_year=2005,
            target_trim_name="Sport Edition",
            target_engine_name="4.7L V8",
            target_drivetrain="4WD",
            target_market="US",
            target_fields_json={"trim_name": "Sport Edition"},
            execution_outcome="created",
            messages_json=["Created test VD"],
            created_vehicle_definition=cls.vd1,
        )

        cls.correction = CanonicalRecordCorrection.objects.create(
            correction_reason=CanonicalRecordCorrection.CorrectionReason.NORMALIZATION_RULE_CORRECTION,
            superseded_vehicle_definition=cls.vd1,
            replacement_vehicle_definition=cls.vd2,
            operator_label="cli:test_operator",
            execution_receipt=cls.receipt,
        )

    def _snapshot_entity_counts(self) -> dict:
        return {
            "manufacturers": Manufacturer.objects.count(),
            "vehicle_models": VehicleModel.objects.count(),
            "generations": Generation.objects.count(),
            "vehicle_definitions": VehicleDefinition.objects.count(),
            "import_execution_receipts": ImportExecutionReceipt.objects.count(),
            "canonical_record_corrections": CanonicalRecordCorrection.objects.count(),
        }

    def test_read_only_snapshot_verification_summary(self) -> None:
        """Verify summary mode preserves exact entity counts before and after."""
        before = self._snapshot_entity_counts()
        out = StringIO()
        call_command("inspect_reference_state", "--summary", stdout=out)
        after = self._snapshot_entity_counts()
        self.assertEqual(before, after)

    def test_read_only_snapshot_verification_inventory(self) -> None:
        """Verify inventory mode preserves exact entity counts before and after."""
        before = self._snapshot_entity_counts()
        out = StringIO()
        call_command("inspect_reference_state", "--inventory", stdout=out)
        after = self._snapshot_entity_counts()
        self.assertEqual(before, after)

    def test_read_only_snapshot_verification_filtered(self) -> None:
        """Verify filtered mode preserves exact entity counts before and after."""
        before = self._snapshot_entity_counts()
        out = StringIO()
        call_command(
            "inspect_reference_state",
            "--manufacturer", "Toyota",
            "--model", "4Runner",
            "--generation", "fourth-generation",
            "--model-year", "2005",
            "--trim", "Sport Edition",
            "--engine", "4.7L V8",
            "--drivetrain", "4WD",
            stdout=out,
        )
        after = self._snapshot_entity_counts()
        self.assertEqual(before, after)

    def test_read_only_snapshot_verification_json(self) -> None:
        """Verify JSON output mode preserves exact entity counts before and after."""
        before = self._snapshot_entity_counts()
        out = StringIO()
        call_command("inspect_reference_state", "--summary", "--json", stdout=out)
        after = self._snapshot_entity_counts()
        self.assertEqual(before, after)

        data = json.loads(out.getvalue())
        self.assertEqual(data["active_vehicle_definitions"], 2)
        self.assertEqual(data["import_execution_receipts"], 1)
        self.assertEqual(data["canonical_record_corrections"], 1)

    def test_zero_filesystem_side_effects(self) -> None:
        """Verify command execution creates zero side-effect files on disk."""
        files_before = set(os.listdir("."))
        out = StringIO()
        call_command("inspect_reference_state", "--summary", stdout=out)
        files_after = set(os.listdir("."))
        self.assertEqual(files_before, files_after)
