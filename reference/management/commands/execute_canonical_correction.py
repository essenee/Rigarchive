"""
Django Management Command: execute_canonical_correction (RA-029).

Executes deliberate, operator-authorized canonical record correction and supersession.
Accepts superseded VehicleDefinition ID, replacement candidate source evidence, and correction reason.

Enforces explicit human authorization (--authorize flag) before performing database mutation.
"""

from pathlib import Path
from django.core.management.base import BaseCommand, CommandError

from reference.ingestion.acquisition.profiles import JDPowerProfile, ToyotaUSAPressroomProfile
from reference.ingestion.acquisition.snapshots import RawSourceSnapshotMetadata
from reference.ingestion.candidate.builder import construct_candidate_configuration
from reference.ingestion.contracts import CandidateIdentity
from reference.ingestion.importing.correction import execute_canonical_record_correction
from reference.ingestion.importing.planner import plan_candidate_import
from reference.ingestion.normalization.jd_power import JDPowerNormalizer
from reference.ingestion.normalization.manufacturer import ManufacturerNormalizer
from reference.models import CanonicalRecordCorrection, VehicleDefinition


class Command(BaseCommand):
    help = "Executes an authorized canonical record correction and supersession workflow."

    def add_arguments(self, parser):
        parser.add_argument(
            "--superseded-id",
            type=int,
            required=True,
            help="Primary Key (ID) of the historical canonical VehicleDefinition to supersede.",
        )
        parser.add_argument(
            "--candidate-source",
            type=str,
            required=True,
            choices=["toyota_usa", "jd_power"],
            help="Source profile ID to build replacement candidate configuration from.",
        )
        parser.add_argument(
            "--native-id",
            type=str,
            required=True,
            help="Native record identifier in source corpus (e.g. '8648' or 'limited_4wd').",
        )
        parser.add_argument(
            "--reason",
            type=str,
            default=CanonicalRecordCorrection.CorrectionReason.NORMALIZATION_RULE_CORRECTION,
            help="Correction reason classification.",
        )
        parser.add_argument(
            "--operator",
            type=str,
            default="cli:correction_operator",
            help="Operator attribution label.",
        )
        parser.add_argument(
            "--authorize",
            action="store_true",
            help="Explicit operator authorization required to perform database mutation.",
        )

    def handle(self, *args, **options):
        superseded_id = options["superseded_id"]
        source_id = options["candidate_source"]
        native_id = options["native_id"]
        reason = options["reason"]
        operator = options["operator"]
        authorized = options["authorize"]

        # 1. Fetch superseded record
        try:
            superseded_vd = VehicleDefinition.objects.get(id=superseded_id)
        except VehicleDefinition.DoesNotExist:
            raise CommandError(f"Superseded VehicleDefinition ID {superseded_id} does not exist.")

        # 2. Extract and build corrected replacement candidate plan
        if source_id == "toyota_usa":
            profile = ToyotaUSAPressroomProfile()
            fixture_path = Path("reference/tests/fixtures/acquisition/toyota/2020_4runner_specs.json")
            if not fixture_path.exists():
                raise CommandError(f"Source fixture path not found: {fixture_path}")
            
            acq = profile.acquire_from_file(fixture_path)
            meta = RawSourceSnapshotMetadata(
                source_id=acq.source_id,
                publisher_locator=acq.source_locator,
                acquired_at=acq.acquired_at,
                content_type=acq.content_type,
                content_hash="sha256:0000000000000000000000000000000000000000000000000000000000000000",
                storage_path=str(fixture_path),
                source_applicability=acq.source_applicability,
                acquisition_method=acq.acquisition_method,
            )
            import json
            transcription_data = json.loads(acq.raw_bytes.decode("utf-8"))
            extracted_sets = profile.extract(meta, transcription_data=transcription_data)
            target_sets = [s for s in extracted_sets if s.provenance.native_record_id == native_id]
            if not target_sets:
                raise CommandError(f"Native record ID '{native_id}' not found in toyota_usa specs corpus.")

            normalizer = ManufacturerNormalizer()
            interps = normalizer.normalize(target_sets[0])
            cid = CandidateIdentity(
                manufacturer_name="Toyota",
                vehicle_model_name="4Runner",
                model_year=superseded_vd.model_year,
                trim_name=superseded_vd.trim_name,
                market=superseded_vd.market,
            )
            cand_doc = construct_candidate_configuration(cid, target_sets, interps)

        elif source_id == "jd_power":
            profile = JDPowerProfile()
            fixture_path = Path("reference/tests/fixtures/acquisition/jd_power/2019_4runner_configurations.json")
            if not fixture_path.exists():
                raise CommandError(f"Source fixture path not found: {fixture_path}")

            acq = profile.acquire_from_file(fixture_path)
            meta = RawSourceSnapshotMetadata(
                source_id=acq.source_id,
                publisher_locator=acq.source_locator,
                acquired_at=acq.acquired_at,
                content_type=acq.content_type,
                content_hash="sha256:0000000000000000000000000000000000000000000000000000000000000000",
                storage_path=str(fixture_path),
                source_applicability=acq.source_applicability,
                acquisition_method=acq.acquisition_method,
            )
            extracted_sets = profile.extract(meta, raw_bytes=acq.raw_bytes)
            target_sets = [s for s in extracted_sets if s.provenance.native_record_id == native_id]
            if not target_sets:
                raise CommandError(f"Native record ID '{native_id}' not found in jd_power configurations corpus.")

            normalizer = JDPowerNormalizer()
            interps = normalizer.normalize(target_sets[0])
            cid = CandidateIdentity(
                manufacturer_name="Toyota",
                vehicle_model_name="4Runner",
                model_year=superseded_vd.model_year,
                trim_name=superseded_vd.trim_name,
                market=superseded_vd.market,
            )
            cand_doc = construct_candidate_configuration(cid, target_sets, interps)

        plan = plan_candidate_import(cand_doc)

        self.stdout.write(self.style.MIGRATE_HEADING("=" * 80))
        self.stdout.write(self.style.MIGRATE_HEADING("CANONICAL RECORD CORRECTION & SUPERSESSION REPORT"))
        self.stdout.write(self.style.MIGRATE_HEADING("=" * 80))
        self.stdout.write(f"Superseded VehicleDefinition ID:   {superseded_vd.id}")
        self.stdout.write(f"Superseded UUID:                 {superseded_vd.uuid}")
        self.stdout.write(f"Superseded Current Slug:         {superseded_vd.slug}")
        self.stdout.write(f"Superseded Current Drivetrain:   {superseded_vd.drivetrain}")
        self.stdout.write(f"Superseded Active Status:         {superseded_vd.is_active}")
        self.stdout.write("-" * 80)
        self.stdout.write(f"Replacement Source ID:           {source_id}")
        self.stdout.write(f"Replacement Native ID:           {native_id}")
        self.stdout.write(f"Replacement Planned Slug:        {plan.target_slug}")
        self.stdout.write(f"Replacement Planned Fields:      {plan.target_vehicle_definition_fields}")
        self.stdout.write(f"Planned Action:                  {plan.planned_action.value}")
        self.stdout.write(f"Correction Reason:               {reason}")
        self.stdout.write(f"Operator Label:                  {operator}")
        self.stdout.write("=" * 80)

        if not authorized:
            self.stdout.write(self.style.WARNING("AUTHORIZATION STATUS: UNAUTHORIZED (DRY RUN ONLY)"))
            self.stdout.write(self.style.WARNING("Zero database writes performed. Pass --authorize to execute correction."))
            return

        self.stdout.write(self.style.SUCCESS("AUTHORIZATION STATUS: AUTHORIZED — EXECUTING CORRECTION..."))
        result = execute_canonical_record_correction(
            superseded_vehicle_definition=superseded_vd,
            candidate_document=cand_doc,
            replacement_plan=plan,
            correction_reason=reason,
            operator_label=operator,
        )

        self.stdout.write(self.style.SUCCESS("=" * 80))
        self.stdout.write(self.style.SUCCESS(f"CANONICAL CORRECTION OUTCOME: {result.outcome}"))
        self.stdout.write(f"Superseded ID:                   {result.superseded_vehicle_definition_id}")
        self.stdout.write(f"Superseded Slug:                 {result.superseded_vehicle_definition_slug}")
        self.stdout.write(f"Replacement ID:                  {result.replacement_vehicle_definition_id}")
        self.stdout.write(f"Replacement UUID:                {result.replacement_vehicle_definition_uuid}")
        self.stdout.write(f"Replacement Slug:                {result.replacement_vehicle_definition_slug}")
        self.stdout.write(f"Correction Audit UUID:           {result.correction_audit_uuid}")
        for msg in result.messages:
            self.stdout.write(f"Execution Message:               {msg}")
        self.stdout.write(self.style.SUCCESS("=" * 80))
