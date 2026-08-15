"""
Production Manufacturer Acquisition Orchestrator (RA-023).

Executes the production control pipeline:
raw acquisition -> immutable snapshot storage -> snapshot-bound extraction ->
manufacturer normalization -> candidate construction -> plan_candidate_import() dry-run.

STRICT GUARANTEE: NEVER invokes execute_candidate_import().
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from reference.ingestion.acquisition.profiles import ToyotaUSAPressroomProfile
from reference.ingestion.acquisition.snapshots import (
    RawSnapshotManager,
    RawSourceSnapshotMetadata,
)
from reference.ingestion.candidate.builder import construct_candidate_configuration
from reference.ingestion.contracts import (
    CandidateConfigurationDocument,
    CandidateIdentity,
    SourceAssertionSet,
)
from reference.ingestion.importing import CanonicalImportPlan
from reference.ingestion.importing.planner import plan_candidate_import
from reference.ingestion.normalization.manufacturer import ManufacturerNormalizer



@dataclass
class CandidateDryRunResult:
    """Dry-run planning result for a single candidate configuration."""

    native_identifier: str
    candidate_reference: str
    candidate_identity: CandidateIdentity
    candidate_doc: CandidateConfigurationDocument
    plan: CanonicalImportPlan


@dataclass
class ProductionRunResult:
    """Aggregated dry-run report summary for a production acquisition run."""

    source_id: str
    publisher_locator: str
    acquisition_status: str  # "CREATED" or "ALREADY_PRESENT"
    snapshot_meta: RawSourceSnapshotMetadata
    total_extracted_sets: int
    candidate_results: List[CandidateDryRunResult] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)


class ProductionManufacturerOrchestrator:
    """
    Production acquisition and dry-run import planning orchestrator.
    Manages raw snapshot retention, extracted asset construction, normalization, candidate building,
    and downstream dry-run planning against current canonical database state.
    """

    def __init__(
        self,
        profile: Optional[ToyotaUSAPressroomProfile] = None,
        snapshot_manager: Optional[RawSnapshotManager] = None,
        normalizer: Optional[ManufacturerNormalizer] = None,
    ):
        self.profile = profile or ToyotaUSAPressroomProfile()
        self.snapshot_manager = snapshot_manager or RawSnapshotManager()
        self.normalizer = normalizer or ManufacturerNormalizer()

    def run_dry_run_pipeline(
        self,
        source_input: str,
        is_url: bool = False,
        transcription_data: Optional[Dict[str, Any]] = None,
        override_expected_hash: Optional[str] = None,
    ) -> ProductionRunResult:
        """
        Execute the end-to-end dry-run production pipeline.
        Acquires raw payload, stores immutable snapshot, extracts sets, normalizes,
        constructs candidates, calls plan_candidate_import(), and returns ProductionRunResult.
        """
        # 1. Acquire raw payload bytes
        if is_url:
            acq_result = self.profile.acquire_from_url(source_input)
        else:
            acq_result = self.profile.acquire_from_file(Path(source_input))

        # 2. Retain immutable raw artifact snapshot
        acq_status, snapshot_meta = self.snapshot_manager.store_snapshot(acq_result)

        # 3. Extract Tier 1 SourceAssertionSets (bound to raw snapshot hash)
        assertion_sets = self.profile.extract(
            snapshot_meta=snapshot_meta,
            transcription_data=transcription_data,
            override_expected_hash=override_expected_hash,
            raw_bytes=acq_result.raw_bytes,
        )

        candidate_results: List[CandidateDryRunResult] = []
        errors: List[str] = []

        # 4-7. Normalize, Build Candidates, Plan Import (one set per configuration)
        for assertion_set in assertion_sets:
            try:
                # Normalization
                normalized_interps = self.normalizer.normalize(assertion_set)

                # Extract CandidateIdentity context from assertion set
                native_id = assertion_set.provenance.native_record_id or "unknown"
                target_ctx = assertion_set.provenance.target_context

                # Look up extracted grade raw value for workflow identity context
                grade_raw = None
                for ast in assertion_set.source_assertions:
                    if ast.attribute_key == "manufacturer_grade":
                        grade_raw = ast.raw_value
                        break

                cand_identity = CandidateIdentity(
                    manufacturer_name=target_ctx.get("make", "Toyota"),
                    vehicle_model_name=target_ctx.get("model", "4Runner"),
                    model_year=target_ctx.get("model_year", 2020),
                    market=target_ctx.get("market", "US"),
                    trim_name=grade_raw,
                )

                # Candidate Construction
                candidate_doc = construct_candidate_configuration(
                    candidate_identity=cand_identity,
                    source_assertion_sets=[assertion_set],
                    normalized_assertions=normalized_interps,
                )




                # Dry-Run Import Planning (plan_candidate_import ONLY)
                plan = plan_candidate_import(candidate_doc)

                candidate_results.append(
                    CandidateDryRunResult(
                        native_identifier=native_id,
                        candidate_reference=candidate_doc.candidate_reference,
                        candidate_identity=cand_identity,
                        candidate_doc=candidate_doc,
                        plan=plan,
                    )
                )
            except Exception as e:
                errors.append(f"Configuration '{assertion_set.provenance.native_record_id}' processing failed: {str(e)}")

        return ProductionRunResult(
            source_id=self.profile.source_id,
            publisher_locator=snapshot_meta.publisher_locator,
            acquisition_status=acq_status,
            snapshot_meta=snapshot_meta,
            total_extracted_sets=len(assertion_sets),
            candidate_results=candidate_results,
            errors=errors,
        )
