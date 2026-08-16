"""
Multi-Source Configuration Aggregation Orchestrator (RA-028).

Coordinates multi-source reference population combining third-party configuration enumeration
(e.g., J.D. Power) with first-party manufacturer technical evidence (e.g., Toyota USA).

Preserves explicit evidence roles, independent source authority, multi-source provenance,
and conflict detection during candidate construction and import planning.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from reference.ingestion.acquisition.profiles import JDPowerProfile, ToyotaUSAPressroomProfile
from reference.ingestion.acquisition.snapshots import RawSnapshotManager, RawSourceSnapshotMetadata
from reference.ingestion.candidate.builder import construct_candidate_configuration
from reference.ingestion.contracts import (
    ApplicabilityScope,
    CandidateConfigurationDocument,
    CandidateIdentity,
    SourceAssertionSet,
)
from reference.ingestion.importing import CanonicalImportPlan
from reference.ingestion.importing.planner import plan_candidate_import
from reference.ingestion.normalization.jd_power import JDPowerNormalizer
from reference.ingestion.normalization.manufacturer import ManufacturerNormalizer


@dataclass
class MultiSourceCandidateResult:
    """Dry-run planning result for a multi-source candidate configuration."""

    native_identifier: str
    candidate_reference: str
    candidate_identity: CandidateIdentity
    candidate_doc: CandidateConfigurationDocument
    plan: CanonicalImportPlan


@dataclass
class MultiSourceRunResult:
    """Aggregated report summary for a multi-source population run."""

    primary_source_id: str
    secondary_source_id: Optional[str]
    total_configurations_discovered: int
    candidate_results: List[MultiSourceCandidateResult] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)


class MultiSourceOrchestrator:
    """
    Orchestrates acquisition, normalization, candidate construction, and import planning
    across J.D. Power configuration enumeration and Toyota USA manufacturer evidence.
    """

    def __init__(
        self,
        jdp_profile: Optional[JDPowerProfile] = None,
        toyota_profile: Optional[ToyotaUSAPressroomProfile] = None,
        snapshot_manager: Optional[RawSnapshotManager] = None,
        jdp_normalizer: Optional[JDPowerNormalizer] = None,
        toyota_normalizer: Optional[ManufacturerNormalizer] = None,
    ):
        self.jdp_profile = jdp_profile or JDPowerProfile()
        self.toyota_profile = toyota_profile or ToyotaUSAPressroomProfile()
        self.snapshot_manager = snapshot_manager or RawSnapshotManager()
        self.jdp_normalizer = jdp_normalizer or JDPowerNormalizer()
        self.toyota_normalizer = toyota_normalizer or ManufacturerNormalizer()

    @staticmethod
    def _target_context_matches(broad_ctx: Dict[str, Any], config_ctx: Dict[str, Any]) -> bool:
        """Check matching across canonical scope attributes (make, model, model_year, market)."""
        for key in ("make", "model", "model_year", "market"):
            b_val = broad_ctx.get(key)
            c_val = config_ctx.get(key)
            if b_val is not None and c_val is not None:
                if str(b_val).strip().lower() != str(c_val).strip().lower():
                    return False
        return True

    def run_multi_source_pipeline(
        self,
        jd_power_input: Union[str, Path],
        toyota_input: Optional[Union[str, Path]] = None,
        is_url: bool = False,
    ) -> MultiSourceRunResult:
        """
        Execute multi-source acquisition, extraction, normalization, aggregation, candidate building,
        and dry-run planning.
        """
        candidate_results: List[MultiSourceCandidateResult] = []
        errors: List[str] = []

        # 1. Acquire & extract J.D. Power configuration enumeration
        if is_url and isinstance(jd_power_input, str):
            jdp_acq = self.jdp_profile.acquire_from_url(jd_power_input)
        else:
            jdp_acq = self.jdp_profile.acquire_from_file(Path(jd_power_input))

        _, jdp_snap_meta = self.snapshot_manager.store_snapshot(jdp_acq)
        jdp_assertion_sets = self.jdp_profile.extract(jdp_snap_meta, raw_bytes=jdp_acq.raw_bytes)

        # 2. Acquire & extract Toyota first-party evidence if provided
        toyota_assertion_sets: List[SourceAssertionSet] = []
        if toyota_input:
            try:
                if is_url and isinstance(toyota_input, str):
                    toyota_acq = self.toyota_profile.acquire_from_url(toyota_input)
                else:
                    toyota_acq = self.toyota_profile.acquire_from_file(Path(toyota_input))

                _, toyota_snap_meta = self.snapshot_manager.store_snapshot(toyota_acq)

                # Extract Toyota assertions (broad or configuration level)
                trans_data = None
                if toyota_acq.raw_bytes and toyota_acq.raw_bytes.strip().startswith((b"{", b"[")):
                    import json
                    trans_data = json.loads(toyota_acq.raw_bytes.decode("utf-8"))

                toyota_assertion_sets = self.toyota_profile.extract(
                    toyota_snap_meta,
                    raw_bytes=toyota_acq.raw_bytes,
                    transcription_data=trans_data,
                )
            except Exception as e:
                errors.append(f"Optional Toyota evidence acquisition note: {str(e)}")

        # 3. Process each J.D. Power configuration set
        for jdp_set in jdp_assertion_sets:
            try:
                config_ctx = jdp_set.provenance.target_context if jdp_set.provenance else {}

                # Normalize J.D. Power assertions
                jdp_norm_interps = self.jdp_normalizer.normalize(jdp_set)

                # Match relevant Toyota first-party assertion sets
                matching_toyota_sets = [
                    t_set for t_set in toyota_assertion_sets
                    if self._target_context_matches(
                        t_set.provenance.target_context if t_set.provenance else {},
                        config_ctx
                    )
                ]

                # Normalize matching Toyota assertions
                toyota_norm_interps = []
                for t_set in matching_toyota_sets:
                    toyota_norm_interps.extend(self.toyota_normalizer.normalize(t_set))

                # Combine assertion sets & normalized interpretations across sources
                combined_sets = [jdp_set] + matching_toyota_sets
                combined_norm_interps = jdp_norm_interps + toyota_norm_interps

                # Extract raw grade/trim string from J.D. Power
                trim_raw = None
                for ast in jdp_set.source_assertions:
                    if ast.attribute_key in ("trim", "manufacturer_grade"):
                        trim_raw = ast.raw_value
                        break

                cand_identity = CandidateIdentity(
                    manufacturer_name=config_ctx.get("make", "Toyota"),
                    vehicle_model_name=config_ctx.get("model", "4Runner"),
                    model_year=config_ctx.get("model_year", 2019),
                    market=config_ctx.get("market", "US"),
                    trim_name=trim_raw,
                )

                candidate_doc = construct_candidate_configuration(
                    candidate_identity=cand_identity,
                    source_assertion_sets=combined_sets,
                    normalized_assertions=combined_norm_interps,
                )

                plan = plan_candidate_import(candidate_doc)

                candidate_results.append(
                    MultiSourceCandidateResult(
                        native_identifier=jdp_set.provenance.native_record_id or "unknown",
                        candidate_reference=candidate_doc.candidate_reference,
                        candidate_identity=cand_identity,
                        candidate_doc=candidate_doc,
                        plan=plan,
                    )
                )
            except Exception as e:
                errors.append(f"J.D. Power configuration '{jdp_set.provenance.native_record_id}' processing failed: {str(e)}")

        return MultiSourceRunResult(
            primary_source_id="jd_power",
            secondary_source_id="toyota_usa" if toyota_assertion_sets else None,
            total_configurations_discovered=len(jdp_assertion_sets),
            candidate_results=candidate_results,
            errors=errors,
        )
