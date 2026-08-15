"""
Canonical Reference Matching & Import Package (RA-018 / RA-019).

Provides deterministic planning and create-only execution for promoting eligible
CandidateConfigurationDocument artifacts into canonical Reference database records.

No automated updates, deletes, or parent entity auto-creations are performed.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


# --- Enums ---

class ImportEligibilityStatus(str, Enum):
    ELIGIBLE = "eligible"
    REQUIRES_REVIEW = "requires_review"
    INELIGIBLE = "ineligible"


class ImportPlannedAction(str, Enum):
    CREATE = "create"
    NO_OP_EXACT_MATCH = "no_op_exact_match"
    FLAG_REVIEW = "flag_review"
    REJECT = "reject"


class ImportExecutionOutcome(str, Enum):
    CREATED = "created"
    NO_OP_EXACT_MATCH = "no_op_exact_match"
    FLAGGED_REVIEW = "flagged_review"
    REJECTED = "rejected"
    ABORTED_STALE_PLAN = "aborted_stale_plan"


class ImportCreateBasis(str, Enum):
    FIRST_REPRESENTATION = "first_representation"
    MECHANICAL_DIMENSION = "mechanical_dimension"


# --- Dataclasses ---

@dataclass
class CanonicalImportPlan:
    candidate_reference: str
    eligibility_status: ImportEligibilityStatus
    planned_action: ImportPlannedAction
    create_basis: Optional[ImportCreateBasis] = None
    namespace_snapshot_count: Optional[int] = None
    mechanical_basis_existing_id: Optional[int] = None
    resolved_manufacturer_id: Optional[int] = None

    resolved_vehicle_model_id: Optional[int] = None
    resolved_generation_id: Optional[int] = None
    target_vehicle_definition_fields: Dict[str, Any] = field(default_factory=dict)
    target_slug: Optional[str] = None
    existing_vehicle_definition_id: Optional[int] = None
    reasons: List[str] = field(default_factory=list)


@dataclass
class CanonicalImportResult:
    candidate_reference: str
    outcome: ImportExecutionOutcome
    vehicle_definition_id: Optional[int] = None
    vehicle_definition_uuid: Optional[str] = None
    vehicle_definition_slug: Optional[str] = None
    messages: List[str] = field(default_factory=list)


# --- Public API Re-exports ---

from reference.ingestion.importing.planner import plan_candidate_import
from reference.ingestion.importing.importer import execute_candidate_import


__all__ = [
    "ImportEligibilityStatus",
    "ImportPlannedAction",
    "ImportExecutionOutcome",
    "ImportCreateBasis",
    "CanonicalImportPlan",
    "CanonicalImportResult",
    "plan_candidate_import",
    "execute_candidate_import",
]
