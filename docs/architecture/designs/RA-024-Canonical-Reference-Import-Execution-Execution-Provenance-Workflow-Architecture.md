# RA-024 — Canonical Reference Import Execution & Execution Provenance Workflow Architecture

## Purpose & Scope

This architecture document establishes the human authorization, review manifest, execution audit provenance, transactionality, and exact-plan promotion workflow for moving an operator-reviewed candidate configuration across the existing [RA-019](file:///Users/esse/dev/Rigarchive/docs/implementation/tasks/RA-019-canonical-reference-import-planning-create-only-execution-implementation.md) execution boundary (`execute_candidate_import`) into canonical database mutation (`VehicleDefinition`). Operates in strict compliance with [ADR-0004](file:///Users/esse/dev/Rigarchive/docs/architecture/ADR/ADR-0004-Canonical-Reference-Matching-Import-Promotion-Strategy.md), [ADR-0005](file:///Users/esse/dev/Rigarchive/docs/architecture/ADR/ADR-0005-Manufacturer-Grade-Taxonomy-Market-Applicability-Normalization.md), [ADR-0006](file:///Users/esse/dev/Rigarchive/docs/architecture/ADR/ADR-0006-Immutable-Raw-Acquisition-Snapshots-Layered-Manufacturer-Profiles.md), and [ADR-0007](file:///Users/esse/dev/Rigarchive/docs/architecture/ADR/ADR-0007-Explicit-Human-Authorization-Execution-Audit-Receipts-Canonical-Promotion.md).

## Governing Architecture & Prior Work

Governed by [ADR-0007 Explicit Human Authorization & Execution Audit Receipts for Canonical Promotion](file:///Users/esse/dev/Rigarchive/docs/architecture/ADR/ADR-0007-Explicit-Human-Authorization-Execution-Audit-Receipts-Canonical-Promotion.md). Integrates existing ingestion contracts, candidate construction, and promotion planning boundaries established by [RA-011](file:///Users/esse/dev/Rigarchive/docs/architecture/designs/RA-011-Ingestion-Schema-Intermediate-Serialization-Design.md), [RA-016](file:///Users/esse/dev/Rigarchive/docs/architecture/designs/RA-016-Candidate-Configuration-Construction-Aggregation-Architecture.md), [RA-018](file:///Users/esse/dev/Rigarchive/docs/architecture/designs/RA-018-Canonical-Reference-Matching-Import-Architecture.md), [RA-019](file:///Users/esse/dev/Rigarchive/docs/implementation/tasks/RA-019-canonical-reference-import-planning-create-only-execution-implementation.md), [RA-020](file:///Users/esse/dev/Rigarchive/docs/architecture/designs/RA-020-Trim-Grade-Market-Applicability-Source-Normalization-Architecture.md), [RA-021](file:///Users/esse/dev/Rigarchive/docs/implementation/tasks/RA-021-manufacturer-specification-evidence-acquisition-normalization-implementation.md), [RA-022](file:///Users/esse/dev/Rigarchive/docs/architecture/designs/RA-022-Production-Manufacturer-Evidence-Acquisition-Orchestration-Architecture.md), and [RA-023](file:///Users/esse/dev/Rigarchive/docs/implementation/tasks/RA-023-production-manufacturer-artifact-acquisition-dry-run-orchestration-implementation.md).

## Human Authorization & Trust Boundary Architecture

The execution workflow enforces a strict trust boundary separating automated evidence evaluation from database mutation authority:

```text
publisher source artifact (raw snapshot)
    ↓
verified extraction & normalization
    ↓
CandidateConfigurationDocument
    ↓
plan_candidate_import() [0 DB writes]
    ↓
CanonicalImportReviewManifest (JSON review artifact)
    ↓
HUMAN OPERATOR REVIEW & EXPLICIT AUTHORIZATION
    ↓
execute_canonical_import --manifest ... --plan-ref ...
    ↓
execute_candidate_import_workflow() [Outer transaction.atomic()]
    ↓
RA-019 execution-time revalidation & execute_candidate_import()
    ↓
VehicleDefinition (CREATED) + ImportExecutionReceipt (ATOMIC)
```

### Core Authorization Principles
1. **Planner Eligibility vs. Execution Authority**: Planner eligibility (`ImportEligibilityStatus.ELIGIBLE` / `ImportPlannedAction.CREATE`) grants permission to *consider* canonical promotion; it does NOT grant automatic execution authority.
2. **Explicit Authorization Boundary**: Canonical Reference database mutation requires explicit, affirmative operator authorization. Automated web acquisition and dry-run planning MUST NEVER silently mutate canonical data.
3. **Preservation of RA-019 Safeguards**: Human authorization never weakens evidence completeness rules, context contradiction protection, parent active validation, create-only guarantees, exact-match no-op logic, or stale-plan namespace checks.

## Exact-Plan Authorization & Stale-Plan Re-planning Policy

* **Exact-Plan Scope**: Human authorization applies strictly to the *exact plan reviewed by the operator*. Authorization does NOT grant permission to execute whatever different plan a future re-run generates.
* **No Silent Re-planning**: The execution workflow reconstructs the exact reviewed `CanonicalImportPlan` from the review manifest and submits that plan to `execute_candidate_import()`. It MUST NOT call `plan_candidate_import()` again to replace the plan silently under prior authorization.
* **Stale Plan Abort**: If live database state changed between review and execution dispatch, `execute_candidate_import()` aborts with `ImportExecutionOutcome.ABORTED_STALE_PLAN`.
* **Re-planning Boundary**: A stale plan MUST NOT be automatically re-planned and executed under previous authorization. Generating a new plan requires a new dry-run acquisition, new manifest output, and a new human review/authorization cycle.

## Single-Plan Execution Scope Boundary

Initial RA-024 execution is strictly **SINGLE-PLAN ONLY**:
* `execute_canonical_import` accepts `--manifest <path>` and `--plan-ref <candidate_reference>`, executing exactly one reviewed plan per command invocation.
* Batch execution flags (`--all`, `--all-eligible`) are explicitly deferred to prevent intra-batch stale state invalidation.
* **Rationale**: Executing one plan mutates canonical database state, which may invalidate the planning assumptions of other candidates. Single-plan execution guarantees predictable authorization boundaries and unambiguous audit trails.

## Corrected Multi-Candidate Planning & Execution Semantics

When multiple candidates are planned during a single dry-run against an empty canonical database namespace (`generation_id`, `model_year`, `market`):
1. **Dry-Run Planning**: Dry-run planning performs zero database writes. Therefore, all 12 candidates independently see the namespace as empty and each receives `ImportCreateBasis.FIRST_REPRESENTATION` `CREATE`.
2. **Sequential Execution of Reviewed Plans**:
   - Executing the first reviewed plan (`8664` SR5 2WD) succeeds and creates `VehicleDefinition` (`SR5 2WD`).
   - Executing the second reviewed plan (`8666` SR5 4WD from the same manifest) re-checks namespace count (`1 > 0`), invalidates the `FIRST_REPRESENTATION` assumption, and aborts cleanly with `ABORTED_STALE_PLAN`. This is the intended behavior of RA-019 stale-plan protection.
3. **Fresh Planning Cycle**:
   - Re-planning candidate `8666` (SR5 4WD) against the updated database (containing `SR5 2WD`) evaluates shared trim (`SR5`) and distinct drivetrain (`4WD` vs `2WD`) $\rightarrow$ qualifies for `ImportCreateBasis.MECHANICAL_DIMENSION` `CREATE` under current RA-019 rules.
   - Re-planning a candidate with a different trim alone (e.g. `SR5 Premium` vs `SR5`) does NOT automatically qualify for `CREATE` $\rightarrow$ evaluates to `REQUIRES_REVIEW` / `FLAG_REVIEW` requiring human review under RA-019 rules.

## Non-Mutating Acquisition vs. Dedicated Execution Command

* **`acquire_manufacturer_specs`**: Permanently non-mutating CLI command (`0` canonical DB writes). Responsible for acquisition, snapshot storage, extraction, normalization, candidate building, dry-run planning, and review manifest output (`--output-manifest`). It MUST NOT gain `--execute` or `--apply` flags.
* **`execute_canonical_import`**: Dedicated canonical mutation CLI command (`--manifest <path> --plan-ref <ref>`). Performs manifest validation, candidate plan reconstruction, interactive operator confirmation `[y/N]`, execution dispatch, and durable audit receipt creation.

## Transient `CanonicalImportPlan` & Review Manifest Architecture

* **`CanonicalImportPlan`**: Remains a transient, short-lived in-memory dataclass representing planning decisions at a specific moment. It is NOT stored as a Django ORM database model.
* **`CanonicalImportReviewManifest`**: Pure Python contract (`reference/ingestion/manifest.py`) representing an immutable, serialized snapshot of a dry-run planning pass. Preserves *exactly what the operator reviewed*.

## Deterministic Manifest Hashing & Strict Validation

### Canonical Serialization Algorithm
Manifest content identity is calculated over compact canonical JSON excluding the `manifest_hash` field:
```python
canonical_bytes = json.dumps(
    manifest_dict_without_hash,
    sort_keys=True,
    ensure_ascii=False,
    separators=(",", ":"),
).encode("utf-8")

manifest_hash = f"sha256:{hashlib.sha256(canonical_bytes).hexdigest()}"
```
* `separators=(",", ":")` eliminates non-canonical formatting whitespace for digest computation.
* File formatting (pretty-printed `indent=2`) in `review_manifest.json` does not affect validation because hashing operates on parsed dictionary canonicalization.

### Validation Rules
Upon loading `review_manifest.json`:
1. Parse JSON file and verify `manifest_version == "1.0"`.
2. Extract `manifest_hash` and verify format `sha256:<64_lowercase_hex>`.
3. Recompute canonical SHA-256 digest over dictionary contents and assert string equality against `manifest_hash`. Mismatch raises `ManifestValidationError`.
4. Validate required top-level and per-plan fields, enum values, and target field types.
5. Enforce **Strict Rejection of Unknown Fields**: Any unexpected key raises `ManifestValidationError`.

## Plan Reconstruction Contract

`reconstruct_plan_from_manifest(review_plan)` instantiates `CanonicalImportPlan` directly from validated manifest fields. **Zero calls to `plan_candidate_import()` are made during execution**, guaranteeing the exact reviewed plan is submitted to `execute_candidate_import()`.

## Durable Execution Audit Receipt Architecture

Located in `reference/models.py`:

```python
class ImportExecutionReceipt(BaseModel):
    """
    Durable execution audit record detailing an authorized canonical promotion attempt.
    """
    executed_at = models.DateTimeField(auto_now_add=True)
    execution_channel = models.CharField(max_length=50, default="cli")
    operator_label = models.CharField(max_length=150)

    # Reviewed Plan & Manifest Provenance
    manifest_hash = models.CharField(max_length=71)
    candidate_reference = models.CharField(max_length=150)
    planned_action = models.CharField(max_length=30)
    create_basis = models.CharField(max_length=30, blank=True)

    # Primary Evidence Anchors
    source_id = models.CharField(max_length=100)
    raw_artifact_hash = models.CharField(max_length=71)
    raw_artifact_reference = models.CharField(max_length=255)
    source_identity_type = models.CharField(max_length=50, default="record_id")
    native_identifier = models.CharField(max_length=100)

    # Target Configuration Snapshot
    resolved_generation_id = models.IntegerField(null=True, blank=True)
    target_slug = models.CharField(max_length=180)
    target_model_year = models.PositiveSmallIntegerField(null=True, blank=True)
    target_trim_name = models.CharField(max_length=100, blank=True)
    target_engine_name = models.CharField(max_length=100, blank=True)
    target_drivetrain = models.CharField(max_length=3, blank=True)
    target_market = models.CharField(max_length=2, blank=True)
    target_fields_json = models.JSONField(default=dict)

    # Actual Domain Outcome
    execution_outcome = models.CharField(max_length=30)
    messages_json = models.JSONField(default=list)

    # Canonical Result Identity (ForeignKeys + Immutable Snapshots)
    created_vehicle_definition = models.ForeignKey(
        VehicleDefinition, on_delete=models.SET_NULL, null=True, blank=True, related_name="creation_receipts"
    )
    existing_vehicle_definition = models.ForeignKey(
        VehicleDefinition, on_delete=models.SET_NULL, null=True, blank=True, related_name="matched_receipts"
    )
    created_vehicle_definition_pk_snapshot = models.IntegerField(null=True, blank=True)
    created_vehicle_definition_uuid_snapshot = models.CharField(max_length=36, blank=True)
    created_vehicle_definition_slug_snapshot = models.CharField(max_length=180, blank=True)
    existing_vehicle_definition_pk_snapshot = models.IntegerField(null=True, blank=True)
    existing_vehicle_definition_uuid_snapshot = models.CharField(max_length=36, blank=True)
    existing_vehicle_definition_slug_snapshot = models.CharField(max_length=180, blank=True)
```

## Primary Evidence Anchors & Target Field Snapshots

`ImportExecutionReceipt` anchors directly to primary evidence:
* `raw_artifact_hash` (`sha256:<64_hex>`)
* `raw_artifact_reference` (`storage/raw_source_artifacts/...`)
* `source_id` (`toyota_usa`)
* `native_identifier` (`8664`)

`candidate_reference` is retained as secondary workflow metadata.

## Canonical Result Identity & FK Deletion Policy

* Foreign keys (`created_vehicle_definition`, `existing_vehicle_definition`) use `on_delete=models.SET_NULL`.
* Immutable identity snapshot fields (`_pk_snapshot`, `_uuid_snapshot`, `_slug_snapshot`) preserve historical audit traceability even if canonical records are deleted or relationship policies alter.
* Snapshot attribute names use `_pk_snapshot` suffix to prevent Django FK attribute collisions (`created_vehicle_definition_id`).

## Operator Attribution Strategy

* `operator_label = f"cli:{getpass.getuser()}"`
* `execution_channel = "cli"`
* Provides honest audit attribution without fabricating fake Django user authentication sessions.

## Transaction Layering & `CREATED` Receipt Atomicity Invariant

* Service: `reference/ingestion/importing/workflow.py` (`execute_canonical_import_workflow`).
* **Atomicity Invariant**: *Zero successfully created canonical `VehicleDefinition` records without a corresponding `CREATED` execution audit receipt.*
* Outer `transaction.atomic()` block wraps `execute_candidate_import(plan)` AND `receipt.save()`.
* If `receipt.save()` fails after `VehicleDefinition.save()` succeeds, the outer atomic transaction issues a database ROLLBACK, rolling back BOTH operations cleanly.

## Domain Outcomes vs. Workflow / Infrastructure Failures

* **Domain Outcomes** (`CREATED`, `NO_OP_EXACT_MATCH`, `ABORTED_STALE_PLAN`, `REJECTED`): Returned normally by `execute_candidate_import()`. Persisted in `ImportExecutionReceipt`.
* **Workflow / Infrastructure Failures** (DB connection drops, receipt save failures, manifest I/O errors): MUST NOT be converted into `ImportExecutionOutcome.REJECTED`. Surface as `CanonicalExecutionWorkflowError`. Outer transaction rolls back cleanly.

## Controlled 2020 Toyota 4Runner Workflow Study

1. `acquire_manufacturer_specs --file specs.json --output-manifest review_manifest.json` $\rightarrow$ 12 candidates produce `FIRST_REPRESENTATION` `CREATE` in manifest.
2. `execute_canonical_import --manifest review_manifest.json --plan-ref cand_toyota_usa_8664_2020` $\rightarrow$ `CREATED` (`SR5 2WD`) + Receipt 1.
3. `execute_canonical_import --manifest review_manifest.json --plan-ref cand_toyota_usa_8666_2020` $\rightarrow$ namespace count is 1 $\rightarrow$ `ABORTED_STALE_PLAN` + Receipt 2.
4. Re-run acquisition to produce `review_manifest_v2.json` $\rightarrow$ Candidate `8666` plans as `MECHANICAL_DIMENSION` `CREATE`.
5. `execute_canonical_import --manifest review_manifest_v2.json --plan-ref cand_toyota_usa_8666_2020` $\rightarrow$ `CREATED` (`SR5 4WD`) + Receipt 3.

## Manufacturer Independence & Future UI Compatibility

* Workflow services (`workflow.py`), manifest contracts (`manifest.py`), and audit models (`ImportExecutionReceipt`) operate exclusively on generic canonical promotion boundaries. Zero Toyota-specific logic exists in RA-024 execution code.
* Fully compatible with future Django Admin action buttons or dedicated web approval queues.

## Explicit Non-Goals

* Zero canonical `UPDATE` or `DELETE` operations.
* Zero automatic parent entity creation (`Manufacturer`, `VehicleModel`, `Generation`).
* Zero automatic/unauthorized background execution.
* Zero batch execution (`--all`) in initial RA-024.
* Zero modification of RA-019 distinctness rules.
* Zero web UI or permissions framework additions.

## Implementation Boundary & Sequence

1. **Pass 1**: Architecture & ADR Documentation (`RA-024` design doc and `ADR-0007`).
2. **Pass 2**: Core Contracts, Models & Migration (`manifest.py`, `ImportExecutionReceipt` model, migration, read-only Admin).
3. **Pass 3**: Execution Workflow Service (`reference/ingestion/importing/workflow.py`).
4. **Pass 4**: Management Commands (`acquire_manufacturer_specs --output-manifest` & `execute_canonical_import`).
5. **Pass 5**: Unit Tests & Critical Inspection (`test_canonical_import_execution.py`).
6. **Pass 6**: Documentation Finalization (`RA-024` task doc, `CURRENT_STATE.md`, `CHANGELOG.md`).
