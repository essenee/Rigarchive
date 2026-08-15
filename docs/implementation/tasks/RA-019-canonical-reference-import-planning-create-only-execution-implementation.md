# RA-019 — Canonical Reference Import Planning & Create-Only Execution Implementation

## Purpose

Implement deterministic canonical Reference promotion machinery operating strictly from validated `CandidateConfigurationDocument` artifacts through pure Python read-only planning (`plan_candidate_import`) and transactional create-only execution (`execute_candidate_import`), converting eligible candidate configurations into canonical `VehicleDefinition` records in strict compliance with [ADR-0004](file:///Users/esse/dev/Rigarchive/docs/architecture/ADR/ADR-0004-Canonical-Reference-Matching-Import-Promotion-Strategy.md) and [RA-018 Canonical Reference Matching & Import Architecture](file:///Users/esse/dev/Rigarchive/docs/architecture/designs/RA-018-Canonical-Reference-Matching-Import-Architecture.md).

## Governing Architecture

Governed by [ADR-0004 Canonical Reference Matching & Import Promotion Strategy](file:///Users/esse/dev/Rigarchive/docs/architecture/ADR/ADR-0004-Canonical-Reference-Matching-Import-Promotion-Strategy.md) and [RA-018 Canonical Reference Matching & Import Architecture](file:///Users/esse/dev/Rigarchive/docs/architecture/designs/RA-018-Canonical-Reference-Matching-Import-Architecture.md). Operates downstream of [RA-017 Candidate Configuration Construction & Aggregation Implementation](file:///Users/esse/dev/Rigarchive/docs/implementation/tasks/RA-017-candidate-configuration-construction-aggregation-implementation.md).

## Implementation Design & Package Structure

The canonical importing package is implemented under `reference/ingestion/importing/`:

```text
reference/ingestion/importing/
├── __init__.py         # Package enums, dataclasses, and module exports
├── planner.py          # Pure Python read-only plan_candidate_import engine (0 DB writes)
└── importer.py         # Transactional execute_candidate_import engine (Create-Only)
```

Re-exported through main ingestion package [`reference/ingestion/__init__.py`](file:///Users/esse/dev/Rigarchive/reference/ingestion/__init__.py).

### Public API Signatures

```python
def plan_candidate_import(
    candidate: CandidateConfigurationDocument,
) -> CanonicalImportPlan:
    """Evaluate a candidate configuration against canonical database data without performing writes."""
    ...

def execute_candidate_import(
    plan: CanonicalImportPlan,
) -> CanonicalImportResult:
    """Execute a transient CanonicalImportPlan inside a database transaction enforcing Create-Only policy."""
    ...
```

Canonical promotion operates strictly from `CandidateConfigurationDocument` artifacts. `SourceAssertionSet` is not accepted as a planner input.

## Transient Import Data Structures

Implemented in `reference/ingestion/importing/__init__.py`:

* **`ImportEligibilityStatus`** (`str`, `Enum`): `ELIGIBLE`, `REQUIRES_REVIEW`, `INELIGIBLE`.
* **`ImportPlannedAction`** (`str`, `Enum`): `CREATE`, `NO_OP_EXACT_MATCH`, `FLAG_REVIEW`, `REJECT`.
* **`ImportExecutionOutcome`** (`str`, `Enum`): `CREATED`, `NO_OP_EXACT_MATCH`, `FLAGGED_REVIEW`, `REJECTED`, `ABORTED_STALE_PLAN`.
* **`ImportCreateBasis`** (`str`, `Enum`): `FIRST_REPRESENTATION`, `MECHANICAL_DIMENSION`.
* **`CanonicalImportPlan`** (`dataclass`): Transient, non-persistent, in-process planning artifact.
  * Fields: `candidate_reference`, `eligibility_status`, `planned_action`, `create_basis`, `namespace_snapshot_count`, `mechanical_basis_existing_id`, `resolved_manufacturer_id`, `resolved_vehicle_model_id`, `resolved_generation_id`, `target_vehicle_definition_fields`, `target_slug`, `existing_vehicle_definition_id`, `reasons`.
* **`CanonicalImportResult`** (`dataclass`): Transient execution summary artifact.
  * Fields: `candidate_reference`, `outcome`, `vehicle_definition_id`, `vehicle_definition_uuid`, `vehicle_definition_slug`, `messages`.

`CanonicalImportPlan` is strictly in-process and does not represent a persistent staging table or database entity.

## Evidence Trust Boundary & Direct Evidence Evaluation

* **Evidence Trust Boundary**: Canonical facts are derived strictly from mapped `candidate.normalized_assertions`. Caller-supplied `CandidateIdentity` context (`manufacturer_name`, `vehicle_model_name`, `trim_name`, `market`) is checked ONLY for contradiction signaling and MUST NOT supply missing canonical evidence.
* **8 Required Evidence Concepts**: Automatic `CREATE` requires mapped evidence for:
  1. `make`
  2. `model`
  3. `model_year`
  4. `generic_drive_classification`
  5. `engine_displacement_liters`
  6. `engine_cylinders`
  7. `trim`
  8. `market`
* **Direct Evidence Evaluation**: Mapped interpretations for each required concept key are evaluated directly as sets (`len(distinct)`). If multiple unequal normalized values are present for any concept (e.g. `trim = "SR5"` and `trim = "Limited"`), `plan_candidate_import` flags `REQUIRES_REVIEW` (`FLAG_REVIEW`). No input ordering or source precedence selects a winner.

## Controlled Production 4Runner Behavior

Current RA-015 production normalizers (`EPANormalizer`, `NHTSANormalizer`) emit mapped normalized evidence for `make`, `model`, `model_year`, `generic_drive_classification`, `engine_displacement_liters`, and `engine_cylinders`, but do NOT emit mapped `trim` or `market`.

Therefore, default production 2020 Toyota 4Runner candidates plan to:
* `eligibility_status = ImportEligibilityStatus.REQUIRES_REVIEW`
* `planned_action = ImportPlannedAction.FLAG_REVIEW`

Execution executes **ZERO database writes**. This is the intended evidence trust boundary behavior.

Contract-valid synthetic test candidates carrying mapped `trim` and `market` evidence exercise `CREATE` and `NO_OP_EXACT_MATCH` cleanly in unit tests.

## Parent Entity Resolution

Parent entities are resolved deterministically from mapped evidence against active database records:
1. **Manufacturer**: `name__iexact=evidence_make`, `is_active=True`.
2. **VehicleModel**: `manufacturer=mfr`, `name__iexact=evidence_model`, `is_active=True`.
3. **Generation**: `vehicle_model=vm`, `start_year__lte=evidence_year`, `(end_year is None or end_year >= evidence_year)`, `is_active=True`.

Resolution outcomes:
* Exactly 1 active match $\rightarrow$ resolved.
* 0 active matches $\rightarrow$ `INELIGIBLE` / `REJECT`.
* $>1$ active matches $\rightarrow$ `REQUIRES_REVIEW` / `FLAG_REVIEW`.

The importer **NEVER** automatically creates `Manufacturer`, `VehicleModel`, or `Generation` records.

## Canonical Field & Engine Representation

* **Target Fields**: Target dictionary contains ONLY current `VehicleDefinition` model fields: `model_year`, `trim_name`, `engine_name`, `drivetrain`, `market`. Target slug is constructed via `temp_vd.build_slug()`. Zero candidate references, source IDs, or context-only fields are written.
* **Engine Labeling & Distinctness**: Evidence displacement and cylinders format standard descriptive display labels via `_format_engine_name` (e.g. `"4.0L V6"`). `engine_name` free-text string inequality is **NOT** used as proof of mechanical distinctness against existing canonical records.
* **Drivetrain Dimension**: `drivetrain` (`2WD`, `4WD`, `AWD`) is the ONLY approved structured mechanical dimension under the current schema that establishes `MECHANICAL_DIMENSION` `CREATE` against existing same-trim rows.
* **Trim String Differences**: Trim differences alone (`SR5` vs `SR5 Premium`) without approved manufacturer taxonomy flag `REQUIRES_REVIEW` (`FLAG_REVIEW`, 0 writes).

## Match Classification & Stale-Plan Revalidation

* **Exact Match**: Target slug exists with identical target fields $\rightarrow$ `NO_OP_EXACT_MATCH`. Revalidated at execution time by querying row ID and checking field equality; if modified or deleted $\rightarrow$ `ABORTED_STALE_PLAN`.
* **First-Representation CREATE**: Zero existing rows in `(generation, model_year, market)` namespace $\rightarrow$ `create_basis = FIRST_REPRESENTATION`. At execution time inside `transaction.atomic()`, re-queries namespace: if exact target row appeared $\rightarrow$ `NO_OP_EXACT_MATCH`; if any non-identical row appeared $\rightarrow$ `ABORTED_STALE_PLAN`; if still empty $\rightarrow$ proceeds with `CREATE`.
* **Mechanical-Dimension CREATE**: Existing row shares trim but differs in drivetrain $\rightarrow$ `create_basis = MECHANICAL_DIMENSION`, `mechanical_basis_existing_id = row.id`. At execution time inside `transaction.atomic()`, re-queries `mechanical_basis_existing_id`: if basis row deleted, modified (`generation_id`, `model_year`, `market`, `trim_name`, `drivetrain`), or if namespace count changed $\rightarrow$ `ABORTED_STALE_PLAN`.

## Database Representation Key vs. Semantic Identity

`(generation, slug)` is the current storage uniqueness and representation key for existing model fields, not a universal real-world identity code. Semantic distinctness classification occurs prior to CREATE authorization.

## Transaction & IntegrityError Safety

* `execute_candidate_import` executes `CREATE` inside `transaction.atomic()`.
* Calls `vd.full_clean()` before `vd.save()`. Pre-save `ValidationError` returns `outcome = REJECTED` with zero partial writes.
* `except IntegrityError:` caught outside the failed atomic block after rollback completes. Re-queries database by `(generation_id, target_slug)`. If exact fields match $\rightarrow$ `NO_OP_EXACT_MATCH`; if absent or fields conflict $\rightarrow$ `REJECTED`.

## Create-Only Canonical Protection

RA-019 performs:
* Zero automatic `VehicleDefinition` updates.
* Zero automatic `VehicleDefinition` deletes.
* Zero parent entity auto-creations.

Existing canonical database records are 100% read-only to the automated importer.

## Verification & Test Suite Summary

Implemented 26 unit test methods in [`reference/tests/test_canonical_import.py`](file:///Users/esse/dev/Rigarchive/reference/tests/test_canonical_import.py) covering:
1. `test_production_2020_4runner_missing_trim_and_market_flags_review`
2. `test_context_only_trim_and_market_do_not_satisfy_evidence_boundary`
3. `test_conflicting_trim_evidence_flags_review`
4. `test_synthetic_valid_candidate_plans_create`
5. `test_unsupported_schema_version_rejects`
6. `test_missing_manufacturer_returns_ineligible`
7. `test_multiple_matching_manufacturers_returns_ineligible`
8. `test_missing_vehicle_model_returns_ineligible`
9. `test_missing_generation_returns_ineligible`
10. `test_overlapping_generations_flags_review`
11. `test_first_representation_create_executes_successfully`
12. `test_proven_dimensional_drivetrain_difference_creates_new_row`
13. `test_trim_string_inequality_alone_flags_review`
14. `test_first_representation_plan_becomes_stale_when_namespace_changes`
15. `test_first_representation_concurrent_exact_target_yields_no_op`
16. `test_engine_display_text_difference_does_not_prove_distinctness`
17. `test_mechanical_create_plan_namespace_staleness`
18. `test_mechanical_create_same_count_different_composition_staleness`
19. `test_mechanical_create_basis_row_modified_staleness`
20. `test_exact_existing_match_executes_no_op`
21. `test_no_op_revalidation_detects_stale_deleted_row`
22. `test_concurrent_insert_integrity_error_verifies_field_equality`
23. `test_concurrent_insert_integrity_error_non_identical_row_rejects`
24. `test_planning_executes_zero_db_writes`
25. `test_zero_parent_auto_creation_guarantee`
26. `test_create_only_policy_never_updates_existing_rows`

## Scope Restrictions (Explicit Non-Goals)

* Zero automated updating of existing canonical rows.
* Zero automated deleting of canonical rows.
* Zero parent entity auto-creation.
* Zero persistent ORM staging models or database migrations.
* Zero live network test dependencies.
* Zero source precedence rules or winner selection logic.

## Completion Record

Status: Completed / Verified

Completion date: 2026-08-15

Files created:
- `reference/ingestion/importing/__init__.py`
- `reference/ingestion/importing/planner.py`
- `reference/ingestion/importing/importer.py`
- `reference/tests/test_canonical_import.py`
- `docs/implementation/tasks/RA-019-canonical-reference-import-planning-create-only-execution-implementation.md`

Files modified:
- `reference/ingestion/__init__.py`
- `docs/implementation/CURRENT_STATE.md`
- `CHANGELOG.md`

Migrations created:
- None (0 ORM schema changes).

Verification results:
- `.venv/bin/python manage.py check`: Passed (`System check identified no issues (0 silenced)`).
- `.venv/bin/python manage.py makemigrations --check`: Passed (`No changes detected`).
- `.venv/bin/python manage.py test reference.tests.test_canonical_import`: Passed (`Ran 26 tests in 0.077s — OK`).
- `.venv/bin/python manage.py test`: Passed (`Ran 106 tests in 3.449s — OK`).
- `git diff --check`: Passed cleanly with exit code 0.
- `git status --short`: Verified clean state across all modified and newly created files.
