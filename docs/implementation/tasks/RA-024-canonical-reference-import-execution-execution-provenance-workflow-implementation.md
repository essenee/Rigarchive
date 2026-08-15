# RA-024 — Canonical Reference Import Execution & Execution Provenance Workflow Implementation

## Purpose

Implement explicit human-authorized canonical reference import execution and durable execution provenance audit receipts. Moves operator-reviewed `CanonicalImportPlan` artifacts across the existing RA-019 execution boundary while preserving explicit human authorization, deterministic review manifest hashing, create-only canonical protection, stale-plan safeguards, and audit survival across canonical entity deletions. Operates in strict compliance with [RA-024 Canonical Reference Import Execution & Execution Provenance Workflow Architecture](file:///Users/esse/dev/Rigarchive/docs/architecture/designs/RA-024-Canonical-Reference-Import-Execution-Execution-Provenance-Workflow-Architecture.md) and [ADR-0007 Explicit Human Authorization & Execution Audit Receipts for Canonical Promotion](file:///Users/esse/dev/Rigarchive/docs/architecture/ADR/ADR-0007-Explicit-Human-Authorization-Execution-Audit-Receipts-Canonical-Promotion.md).

## Governing Authority

Governed by [ADR-0007 Explicit Human Authorization & Execution Audit Receipts for Canonical Promotion](file:///Users/esse/dev/Rigarchive/docs/architecture/ADR/ADR-0007-Explicit-Human-Authorization-Execution-Audit-Receipts-Canonical-Promotion.md) and [RA-024 Canonical Reference Import Execution & Execution Provenance Workflow Architecture](file:///Users/esse/dev/Rigarchive/docs/architecture/designs/RA-024-Canonical-Reference-Import-Execution-Execution-Provenance-Workflow-Architecture.md). Preserves the canonical model invariants, create-only protection, and stale-plan safeguards established by [RA-019](file:///Users/esse/dev/Rigarchive/docs/implementation/tasks/RA-019-canonical-reference-import-planning-create-only-execution-implementation.md) / [ADR-0004](file:///Users/esse/dev/Rigarchive/docs/architecture/ADR/ADR-0004-Canonical-Reference-Import-Planning-Create-Only-Execution.md), as well as the production acquisition snapshot retention and evidence provenance bound by [RA-022](file:///Users/esse/dev/Rigarchive/docs/architecture/designs/RA-022-Production-Manufacturer-Evidence-Acquisition-Orchestration-Architecture.md), [ADR-0006](file:///Users/esse/dev/Rigarchive/docs/architecture/ADR/ADR-0006-Immutable-Raw-Acquisition-Snapshots-Layered-Manufacturer-Profiles.md), and [RA-023](file:///Users/esse/dev/Rigarchive/docs/implementation/tasks/RA-023-production-manufacturer-artifact-acquisition-dry-run-orchestration-implementation.md).

## Architecture & Implementation Workflow

The canonical reference import execution and audit provenance workflow follows:

```text
acquire_manufacturer_specs --output-manifest review_manifest.json
    ↓ (0 canonical writes)
CanonicalImportReviewManifest (v1.0 + sha256:<64_hex> manifest_hash)
    ↓
Operator Review & Human Authorization
    ↓
execute_canonical_import --manifest review_manifest.json --plan-ref <ref>
    ↓
dict_to_manifest() (strict v1.0 validation, strict int type safety, SHA-256 hash check)
    ↓
input("Do you authorize... [y/N]") (mandatory interactive prompt)
    ↓
reconstruct_plan_from_manifest() (exact reviewed plan, 0 replanning calls)
    ↓
execute_canonical_import_workflow()
    ↓
transaction.atomic() {
    execute_candidate_import(plan) (RA-019 revalidation & creation)
    ImportExecutionReceipt.objects.create(...) (durable audit receipt)
}
    ↓
Successful Canonical Write + Audit Receipt / Rollback on Error
```

## Implementation Details & File Summary

### 1. Review Manifest Contracts & Strict Type Validation (`reference/ingestion/manifest.py`)

* **`CanonicalImportReviewPlan`**: Pure-Python dataclass carrying all 13 fields of `CanonicalImportPlan` plus source identity anchors (`source_identity_type`, `native_identifier`).
* **`CanonicalImportReviewManifest`**: Top-level envelope (`manifest_version="1.0"`, `created_at`, `source_id`, `raw_artifact_hash`, `raw_artifact_reference`, `extraction_provenance`, `plans`, `manifest_hash`).
* **Deterministic Compact SHA-256 Content Hashing**:
  - `compute_manifest_hash()` serializes the manifest dictionary (excluding `manifest_hash`) via `json.dumps(d, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode("utf-8")` and returns `sha256:<64_lowercase_hex>`.
  - JSON file formatting/indentation (`indent=2`) does not invalidate parsed dictionary hash. Payload modification causes hash mismatch and raises `ManifestValidationError`.
* **Strict Validation & Unknown-Field Rejection**:
  - `dict_to_manifest()` validates `allowed_top_level` and `allowed_plan_keys` prior to dataclass construction.
  - Enforces duplicate `candidate_reference` rejection.
  - Enforces enum value validation for `eligibility_status`, `planned_action`, and `create_basis`.
* **Strict Integer Type Safety**:
  - Validates integer fields (`namespace_snapshot_count`, `mechanical_basis_existing_id`, `resolved_manufacturer_id`, `resolved_vehicle_model_id`, `resolved_generation_id`, `existing_vehicle_definition_id`).
  - Accepts strictly `int` or `None` where nullable.
  - Explicitly rejects `bool` (`True`, `False`), `float` (`1.0`), and numeric strings (`"1"`).
* **Exact Plan Reconstruction**:
  - `reconstruct_plan_from_manifest()` instantiates `CanonicalImportPlan` directly from reviewed manifest fields. Performs **ZERO** calls to `plan_candidate_import()`.

### 2. Execution Audit Receipt Model & Read-Only Admin (`reference/models.py`, `reference/admin.py`, `reference/migrations/0002_importexecutionreceipt.py`)

* **`ImportExecutionReceipt` ORM Model**:
  - Inherits from `BaseModel` (`id`, `uuid`, `created_at`, `updated_at`).
  - Audit fields: `executed_at`, `execution_channel`, `operator_label`, `manifest_hash`, `candidate_reference`, `planned_action`, `create_basis`, evidence anchors (`source_id`, `raw_artifact_hash`, `raw_artifact_reference`, `source_identity_type`, `native_identifier`), target configuration snapshot (`target_slug`, `target_model_year`, `target_trim_name`, `target_engine_name`, `target_drivetrain`, `target_market`, `target_fields_json`), execution outcome (`execution_outcome`, `messages_json`).
  - FK relationships with `on_delete=models.SET_NULL`: `created_vehicle_definition` and `existing_vehicle_definition`.
  - Primary identity snapshots: `created_vehicle_definition_pk_snapshot`, `created_vehicle_definition_uuid_snapshot`, `created_vehicle_definition_slug_snapshot`, `existing_vehicle_definition_pk_snapshot`, `existing_vehicle_definition_uuid_snapshot`, `existing_vehicle_definition_slug_snapshot`. Guarantees audit log survival even if canonical entities are subsequently deleted.
* **Read-Only Django Admin Viewer**:
  - `ImportExecutionReceiptAdmin` registers `has_add_permission = False`, `has_change_permission = False`, `has_delete_permission = False`, with all fields listed in `readonly_fields`. Viewing receipts is enabled; editing or deleting receipts in Django Admin is prohibited.

### 3. Transactional Workflow Execution Engine (`reference/ingestion/importing/workflow.py`)

* **`execute_canonical_import_workflow()`**:
  - Refuses non-executable plans (`FLAG_REVIEW`, `REJECT`) prior to dispatch.
  - Enforces `transaction.atomic()` binding for `CREATE` operations: `execute_candidate_import(plan)` and `_build_and_save_receipt(result)` commit together or roll back cleanly.
  - Unit test `test_created_receipt_atomicity_rollback` proves that if receipt creation fails after `VehicleDefinition` creation succeeds, Django's outer transaction issues a ROLLBACK, resulting in 0 canonical writes and 0 receipts.
  - Expected domain outcomes (`CREATED`, `NO_OP_EXACT_MATCH`, `ABORTED_STALE_PLAN`, `REJECTED`) produce durable audit receipts. Infrastructure/database errors raise `CanonicalExecutionWorkflowError` and roll back transactions without producing fake `REJECTED` receipts.

### 4. Explicit Authorization CLI & Dry-Run Manifest Command (`reference/management/commands/execute_canonical_import.py` & `acquire_manufacturer_specs.py`)

* **`execute_canonical_import`**:
  - Arguments: `--manifest <path>`, `--plan-ref <ref>`, `--operator <name>`.
  - Validates review manifest structure and SHA-256 hash digest.
  - Prompts mandatory interactive human authorization: `confirm = input("Do you authorize executing this canonical import plan? [y/N]: ")`. Intentionally does not implement `--no-input` flag, ensuring interactive confirmation is required on every run.
  - Single-plan selection (`--plan-ref`) enforced; zero batch execution options exist.
* **`acquire_manufacturer_specs`**:
  - Added `--output-manifest <path>` argument to serialize dry-run planning results into a review manifest JSON file.
  - Preserves guaranteed **ZERO** canonical database writes during production acquisition dry-runs.

### 5. Multi-Candidate Control Study & Test Suite (`reference/tests/test_canonical_import_execution.py`)

* **Sequential 4Runner Control Study**:
  - Step 1: Initial dry-run against empty database (`manifest_1`). Plan 1 (SR5 2WD) executed -> `CREATED`. `VehicleDefinition` count = 1.
  - Step 2: Plan 2 (SR5 4WD) executed from OLD `manifest_1` (planned against empty namespace). Revalidation detects non-empty namespace and returns `ABORTED_STALE_PLAN`.
  - Step 3: Fresh dry-run (`manifest_2`) against updated DB. SR5 2WD is `NO_OP_EXACT_MATCH`; SR5 4WD is `CREATE` on `MECHANICAL_DIMENSION` basis; SR5 Premium 2WD is `FLAG_REVIEW`.
  - Step 4: Executing fresh plan for SR5 4WD succeeds with `CREATED`. `VehicleDefinition` count = 2.
* **Focused & Full Project Test Coverage**:
  - 16 focused test methods in `test_canonical_import_execution.py`.
  - Full project test suite: **164/164 tests passing cleanly**.

## Task Completion Verification

### Verification Commands & Results

1. **System Check**: `.venv/bin/python manage.py check`
   - Output: `System check identified no issues (0 silenced).`
2. **Migration Check**: `.venv/bin/python manage.py makemigrations --check`
   - Output: `No changes detected`
3. **Focused Ingestion/Importing Test Suite**:
   `.venv/bin/python manage.py test reference.tests.test_canonical_import_execution reference.tests.test_canonical_import reference.tests.test_production_manufacturer_acquisition reference.tests.test_manufacturer_ingestion`
   - Output: `Ran 84 tests... OK`
4. **Full Project Test Suite**: `.venv/bin/python manage.py test`
   - Output: `Ran 164 tests... OK` (148 baseline + 16 new RA-024 tests)
5. **Git Diff Check**: `git diff --check`
   - Output: Clean (0 whitespace/formatting errors).

### Documentation Maintenance Status

* `docs/implementation/tasks/RA-024-canonical-reference-import-execution-execution-provenance-workflow-implementation.md`: Created.
* `docs/implementation/CURRENT_STATE.md`: Updated to record RA-024 architecture + implementation completion, `ImportExecutionReceipt` model, migration `0002`, review manifest infrastructure, and 164-test project baseline.
* `CHANGELOG.md`: Updated under `Unreleased` heading with complete RA-024 implementation details.
* ADR Status: `ADR-0007` status is `Accepted` and in full effect.

### Final Task Disposition

* **Status**: Complete
* **Completion Date**: August 15, 2026
* **Files Created/Modified**:
  - Created: `reference/ingestion/manifest.py`, `reference/ingestion/importing/workflow.py`, `reference/management/commands/execute_canonical_import.py`, `reference/migrations/0002_importexecutionreceipt.py`, `reference/tests/test_canonical_import_execution.py`, `docs/implementation/tasks/RA-024-canonical-reference-import-execution-execution-provenance-workflow-implementation.md`.
  - Modified: `reference/models.py`, `reference/admin.py`, `reference/ingestion/__init__.py`, `reference/management/commands/acquire_manufacturer_specs.py`, `docs/implementation/CURRENT_STATE.md`, `CHANGELOG.md`.
* **Migrations Created**: `reference/migrations/0002_importexecutionreceipt.py`.
* **Deviations / Follow-Up Work**: `--no-input` flag was intentionally omitted from `execute_canonical_import` to strictly enforce mandatory interactive operator confirmation `[y/N]` on every execution.
