# Implementation Task Record: RA-026 — Deterministic Toyota Extraction & Review-Adjudication Implementation

## Task Identity
- **Task ID**: RA-026
- **Task Title**: Deterministic Toyota Extraction & Review-Adjudication Implementation
- **Status**: Completed / Verified
- **Completion Date**: 2026-08-15
- **Governing Blueprint / Handbook**: Project Blueprint, Engineering Handbook
- **Governing Architecture & ADRs**:
  - [RA-025 Architecture Design Document](file:///Users/esse/dev/Rigarchive/docs/architecture/designs/RA-025-Production-Manufacturer-Extraction-Review-Adjudication-Architecture.md)
  - [ADR-0008 Architectural Decision Record](file:///Users/esse/dev/Rigarchive/docs/architecture/ADR/ADR-0008-Deterministic-Extraction-Review-Adjudication-Adjudicated-Grade-Promotion.md)
  - [ADR-0007 Architectural Decision Record](file:///Users/esse/dev/Rigarchive/docs/architecture/ADR/ADR-0007-Explicit-Human-Authorization-Execution-Audit-Receipts-Canonical-Promotion.md)
  - [ADR-0006 Architectural Decision Record](file:///Users/esse/dev/Rigarchive/docs/architecture/ADR/ADR-0006-Immutable-Raw-Acquisition-Snapshots-Layered-Manufacturer-Profiles.md)

---

## 1. Executive Summary & Objective

RA-026 realizes the approved RA-025 / ADR-0008 architecture by implementing two related but distinct engineering capabilities within the RigArchive reference ingestion pipeline:

1. **Deterministic Production PDF Extraction**: Directly parses authentic retained publisher PDF documents (`2020_4runner_pricing.pdf` and `2020_4runner_specs.pdf`) using `pypdf 6.16.1` to produce Tier 1 `SourceAssertionSet` artifacts with zero runtime dependency on intermediate JSON transcriptions or synthetic HTML.
2. **Bounded Review-Adjudication & Re-Planning Engine**: Implements the `CanonicalImportAdjudication` artifact, typed `ImportReviewCategory` taxonomy, adjudication-aware re-planning (`plan_candidate_import_with_adjudications`), the third `ImportCreateBasis` (`ADJUDICATED_DISTINCT_GRADE`), review manifest `v1.1` serialization, execution workflow adjudication artifact verification, and mandatory interactive human authorization.

The implementation was validated against the controlled 2020 Toyota 4Runner specification study (12 model-code configurations), achieving **185/185 passing tests** across the project test suite with zero architectural blockers.

---

## 2. Five-Stage Promotion Lifecycle

RA-026 strictly preserves the 5-stage lifecycle established by ADR-0008:

```
[ Stage 1: Planning ] -> [ Stage 2: Adjudication ] -> [ Stage 3: Re-Planning ] -> [ Stage 4: Execution Auth ] -> [ Stage 5: Execution ]
```

1. **Stage 1 (Planning)**: `plan_candidate_import()` evaluates candidate evidence against the canonical database. First representations yield `FIRST_REPRESENTATION`, proven mechanical dimensional differences yield `MECHANICAL_DIMENSION`, and candidate trims differing only by factory grade string flag `FLAG_REVIEW` with a typed `ImportReviewCategory` (e.g. `DISTINCT_FACTORY_GRADE`). Emits a `v1.0` or `v1.1` review manifest.
2. **Stage 2 (Human Domain Adjudication)**: A human operator evaluates flagged plans via `adjudicate_canonical_import` CLI. If the candidate represents a legitimate factory grade (e.g., `SR5 Premium`), the operator generates a signed `CanonicalImportAdjudication` JSON artifact. **Adjudication performs ZERO canonical database writes and grants ZERO execution authorization.**
3. **Stage 3 (Adjudication-Aware Re-Planning)**: `plan_candidate_import_with_adjudications()` consumes the candidate and validated `CanonicalImportAdjudication` artifact. It re-plans the candidate under `ImportCreateBasis.ADJUDICATED_DISTINCT_GRADE` and produces an executable `v1.1` review manifest bearing `adjudication_reference` and `adjudication_hash`.
4. **Stage 4 (Execution Authorization)**: The operator invokes `execute_canonical_import`. The CLI displays exact target configuration details and requires explicit interactive operator confirmation via an un-bypassable `[y/N]` terminal prompt.
5. **Stage 5 (Transactional Execution)**: `execute_canonical_import_workflow()` loads the actual `CanonicalImportAdjudication` artifact from disk, verifies 6 cryptographic and identity linkage invariants against the review plan, and executes the `CREATE` operation inside `transaction.atomic()`, persisting the canonical `VehicleDefinition` and an `ImportExecutionReceipt` recording `adjudication_hash`.

---

## 3. Authentic Toyota Publisher Source Artifacts

Runtime extraction operates strictly against authentic first-party Toyota publisher artifacts stored under `reference/tests/fixtures/acquisition/toyota/`:

1. **Pricing Master PDF**:
   - **Path**: `reference/tests/fixtures/acquisition/toyota/2020_4runner_pricing.pdf`
   - **SHA-256**: `sha256:e549f02e10849b567424a15690164b7dc21a34aae7e02241222397415958bdd9`
   - **Role**: Source-local configuration identity source for model year 2020 4Runner. Establishes 12 distinct model codes (`8664` through `8692`), grades (`SR5`, `SR5 Premium`, `TRD Off-Road`, `TRD Off-Road Premium`, `Venture Special Edition`, `Limited`, `Nightshade Special Edition`, `TRD Pro`), drivetrains (`2WD`, `4WD`), engine description text (`4.0L V6 DOHC 24-Valve`), transmission, and MSRP.
2. **Product Information PDF**:
   - **Path**: `reference/tests/fixtures/acquisition/toyota/2020_4runner_specs.pdf`
   - **SHA-256**: `sha256:1ca3b58206b17c1aacf4ff196f28eb9559144fc243cbe3e53d68526246e2b4bb`
   - **Role**: Universal 2020 Toyota 4Runner technical evidence source. Contributes model-year universal engine facts (4.0L displacement, 6 cylinders, V6 architecture) under `target_context = {"make": "Toyota", "model": "4Runner", "model_year": 2020, "market": "US"}`.

---

## 4. Golden Test Fixture & Dependency Disposition

### Golden Benchmark Fixture (`2020_4runner_specs.json`)
The file `reference/tests/fixtures/acquisition/toyota/2020_4runner_specs.json` is a **manually verified golden test benchmark**. It is used exclusively in test code (`test_toyota_extractor.py`, `test_canonical_import_execution.py`) to verify extractor equivalence against historical transcriptions.
- **Production Decoupling**: Production runtime code (`ToyotaUSAPressroomProfile`, `ToyotaPricingMasterPdfStrategy`, `ToyotaProductInformationPdfStrategy`) contains **ZERO** runtime references or dependencies on `2020_4runner_specs.json`.

### PDF Extraction Engine & Dependency Management
- **PDF Text Engine**: `pypdf 6.16.1` is used as the pure Python deterministic text extraction engine. Extraction uses direct layout text stream parsing. No OCR, no fallback parser chains, and no custom general-purpose PDF parsers are used.
- **Dependency Disposition**: `pypdf 6.16.1` is an active runtime dependency in the project environment. Because the repository does not yet have a standardized dependency manifest (`requirements.txt` or `pyproject.toml`), this dependency is recorded as a repository tooling follow-up consideration and is not an architectural blocker.

---

## 5. Extractor Implementation & Multi-Document Linkage

### Extractor Strategies (`reference/ingestion/acquisition/toyota_extractor.py`)
1. **`ToyotaPricingMasterPdfStrategy`**: Extracts 12 model-code configurations from `2020_4runner_pricing.pdf` using table row anchor parsing (`Model Code`, `Model`, `MSRP`). Constructs 12 distinct Tier 1 `SourceAssertionSet` objects under `source_id = "toyota_usa"`.
2. **`ToyotaProductInformationPdfStrategy`**: Extracts model-year universal facts from `2020_4runner_specs.pdf` (`engine_displacement_liters = 4.0`, `engine_cylinders = 6`). Emits a universal `SourceAssertionSet` under `source_id = "toyota_usa"`.

### Explicit Multi-Document Linkage (ADR-0006 Compliance)
Candidate configuration construction in `construct_candidate_configuration()` combines model-code configuration assertions with universal model-year technical assertions matching the same `source_id = "toyota_usa"` and target context.
- **Zero Grade-String Joins**: Unrelated documents are NEVER joined by matching grade/trim strings.
- **Same-Source Lineage**: Both PDFs carry `source_id = "toyota_usa"`. Assertion grouping yields `lineage_count = 1` and `corroboration_status = "single_source"`, preventing false cross-source corroboration claims.

---

## 6. Multi-Artifact Evidence Identity & Revision Binding

### Evidence Set Identity (`CandidateConfigurationDocument.evidence_raw_hashes`)
When a candidate configuration is constructed from multiple raw artifacts (Pricing Master PDF + Product Information PDF), `construct_candidate_configuration()` collects all unique raw artifact hashes into a canonicalized, sorted list:
```python
candidate.evidence_raw_hashes = [
    "sha256:1ca3b58206b17c1aacf4ff196f28eb9559144fc243cbe3e53d68526246e2b4bb",
    "sha256:e549f02e10849b567424a15690164b7dc21a34aae7e02241222397415958bdd9"
]
```

### Adjudication Evidence-Revision Binding
`CanonicalImportAdjudication` records the exact evidence hashes reviewed by the human operator in `evidence_anchors = {"raw_artifact_hashes": [...]}`.
During adjudication-aware re-planning in `plan_candidate_import_with_adjudications()`:
- The candidate's `evidence_raw_hashes` set MUST EXACTLY MATCH the adjudication's raw artifact hash set (`cand_raw_hashes == adj_raw_hashes`).
- If EITHER raw artifact revision changes (e.g. Product Information PDF updated), automatic adjudication reuse is refused, and the plan remains `FLAG_REVIEW`.

---

## 7. `CanonicalImportAdjudication` Contract & Hashing

### Contract Schema (`reference/ingestion/contracts.py`)
```python
@dataclass
class CanonicalImportAdjudication:
    adjudication_version: str            # "1.0"
    created_at: str                      # ISO-8601 UTC timestamp
    operator_label: str                  # Operator attribution (e.g. "op:jdoe")
    original_manifest_hash: str          # Hash of original review manifest ("sha256:...")
    candidate_reference: str             # Target candidate reference ("cand_ref_...")
    source_identity: Dict[str, Any]      # {"source_id": "toyota_usa", ...}
    original_review_category: str        # Original typed review category ("distinct_factory_grade")
    adjudication_category: str           # Approved category ("distinct_factory_grade")
    adjudication_decision: str           # "approved_distinct_trim"
    adjudicated_trim_name: str           # Verified trim name ("SR5 Premium")
    evidence_anchors: Dict[str, Any]     # {"raw_artifact_hashes": [...]}
    adjudication_notes: str              # Operator justification notes
    adjudication_hash: str               # Content hash ("sha256:<64_lowercase_hex>")
    unknown_fields: Dict[str, Any] = field(default_factory=dict)
```

### Deterministic Content Hashing (`compute_adjudication_hash`)
Computes `sha256:<64_lowercase_hex>` over UTF-8 JSON key canonicalization (`separators=(",", ":")`, `sort_keys=True`), excluding `adjudication_hash` itself. Any field modification or payload tampering invalidates hash verification.

### Original Manifest Hash Binding
`adjudicate_canonical_import` CLI parses and validates the input review manifest, computing `manifest.manifest_hash`. It binds `original_manifest_hash = manifest.manifest_hash` directly from the verified parsed artifact. The caller cannot supply an arbitrary string. Tampered manifests fail validation before adjudication output.

---

## 8. Typed Review Categories & Adjudicable Boundary

### Typed Review Category Enum (`ImportReviewCategory`)
Defined in `reference/ingestion/importing/__init__.py`:
- `DISTINCT_FACTORY_GRADE = "distinct_factory_grade"`
- `SPECIAL_EDITION_GRADE = "special_edition_grade"`
- `CONTEXT_CONTRADICTION = "context_contradiction"`
- `EVIDENCE_CONFLICT = "evidence_conflict"`
- `MISSING_EVIDENCE = "missing_evidence"`
- `MULTIPLE_OVERLAPPING_GENERATIONS = "multiple_overlapping_generations"`
- `SLUG_CONFLICT = "slug_conflict"`
- `UNFORMATTED_ENGINE_LABEL = "unformatted_engine_label"`

Human-readable `reasons` remain explanatory strings. Machine adjudicability is strictly governed by `base_plan.review_category`.

### Adjudicable Boundary Matrix
- **Adjudicable Categories**: ONLY `DISTINCT_FACTORY_GRADE` and `SPECIAL_EDITION_GRADE` may be resolved via `adjudication_category` in `{"distinct_factory_grade", "special_edition_grade"}`.
- **Non-Adjudicable Blockers**: `CONTEXT_CONTRADICTION`, `EVIDENCE_CONFLICT`, `MISSING_EVIDENCE`, `MULTIPLE_OVERLAPPING_GENERATIONS`, `SLUG_CONFLICT`, and `UNFORMATTED_ENGINE_LABEL` cannot be promoted via adjudication. Re-planning rejects adjudication attempts for these categories.

---

## 9. Adjudication-Aware Re-Planning & `ADJUDICATED_DISTINCT_GRADE`

### Trusted Semantic Re-Planning (`plan_candidate_import_with_adjudications`)
Re-planning is NOT a force-create override. It validates 8 strict criteria:
1. Base planning result must be `FLAG_REVIEW`.
2. Base plan `review_category` must be `DISTINCT_FACTORY_GRADE` or `SPECIAL_EDITION_GRADE`.
3. Adjudication artifact must pass syntactic and hash validation (`validate_adjudication`).
4. Adjudication `candidate_reference` must match candidate reference.
5. Adjudication `adjudicated_trim_name` must match target trim fields.
6. Adjudication `original_review_category` must match `base_plan.review_category.value`.
7. Candidate `evidence_raw_hashes` must equal adjudication raw artifact hash set.
8. Current database state must confirm base trim exists without exact target trim.

### Third Create Basis: `ADJUDICATED_DISTINCT_GRADE`
`ImportCreateBasis.ADJUDICATED_DISTINCT_GRADE` represents human-validated semantic proof of a legitimate factory grade in an already-populated canonical namespace. It is distinct from `FIRST_REPRESENTATION` (namespace empty) and `MECHANICAL_DIMENSION` (proven engine/drivetrain difference).

---

## 10. Review Manifest v1.1 Contract & Forged-Manifest Protection

### Review Manifest v1.1 Schema (`reference/ingestion/manifest.py`)
Adds `adjudication_reference`, `adjudication_hash`, and `review_category` to `CanonicalImportReviewPlan`. `build_review_manifest()` sets `manifest_version = "1.1"` whenever any plan includes adjudication linkage.

### Manifest Acceptance & Backward Compatibility Matrix
- **`v1.0` without adjudication fields**: ACCEPT (Executable backward compatibility).
- **`v1.0` with adjudication fields**: REJECT.
- **`v1.1` with normal non-adjudicated plan**: ACCEPT.
- **`v1.1` with valid adjudicated plan + complete linkage**: ACCEPT.
- **`v1.1` with incomplete adjudication linkage**: REJECT.
- **Adjudication linkage on `FIRST_REPRESENTATION` or `MECHANICAL_DIMENSION`**: REJECT.

### Execution Trust Boundary & Forged-Manifest Protection
In `execute_canonical_import_workflow()`:
- A review manifest with `ADJUDICATED_DISTINCT_GRADE` is NOT alone sufficient to execute.
- The workflow loads the actual `CanonicalImportAdjudication` artifact from disk and verifies 6 explicit linkage points:
  1. `adjudication_artifact.adjudication_hash`
  2. `review_plan.adjudication_hash`
  3. `plan.adjudication_hash`
  4. `adjudication_artifact.candidate_reference == review_plan.candidate_reference`
  5. `adjudication_artifact.adjudicated_trim_name == target_trim`
  6. `review_plan.adjudication_reference == f"adjudication_{candidate_reference}.json"`
- A forged manifest with an arbitrary syntactically valid `adjudication_hash` is refused prior to database transaction entry.

---

## 11. Mandatory Interactive Human Authorization

In accordance with ADR-0007 / RA-024:
- `execute_canonical_import` requires explicit interactive confirmation (`confirm = input("Do you authorize executing this canonical import plan? [y/N]: ")`) on EVERY invocation.
- There is **NO `--no-input` parser flag** and **NO production code path bypassing human authorization**.
- Tests simulate human responses using `unittest.mock.patch("builtins.input", return_value=...)`.
- Tested CLI behavior:
  - Operator responds `"n"`: Aborts execution $\rightarrow$ **0 canonical writes**.
  - Operator responds empty `""`: Aborts execution $\rightarrow$ **0 canonical writes**.
  - Operator responds `"y"`: Authorization granted $\rightarrow$ workflow proceeds to execute plan.

---

## 12. Execution Stale-State Semantics & Audit Receipts

### Stale-State Execution Semantics
- Exact matching target exists in canonical DB $\rightarrow$ `NO_OP_EXACT_MATCH` (0 writes).
- Same trim representation appears before execution $\rightarrow$ `ABORTED_STALE_PLAN` (0 writes).
- Unrelated trim inserted into namespace $\rightarrow$ Non-material; execution proceeds cleanly.
- Zero execution-time basis conversion.

### `ImportExecutionReceipt` Linkage (`reference/models.py`, Migration `0003`)
- Migration `0003_importexecutionreceipt_adjudication_hash.py` adds optional `adjudication_hash` (CharField(64), null=True, blank=True) to `ImportExecutionReceipt`.
- When an `ADJUDICATED_DISTINCT_GRADE` plan is executed, `execute_canonical_import_workflow()` records the verified `adjudication_hash` on the durable receipt. Receipt creation is transactional with `VehicleDefinition` creation inside `transaction.atomic()`.

---

## 13. Controlled 2020 Toyota 4Runner Study Results

The controlled 2020 Toyota 4Runner study processed 12 model-code configurations through the complete 5-stage lifecycle:

| Model Code | Trim Name | Drivetrain | Planned Action | Create Basis | Adjudication Required |
|---|---|---|---|---|---|
| `8664` | SR5 | 2WD | `create` | `FIRST_REPRESENTATION` | No |
| `8666` | SR5 | 4WD | `create` | `MECHANICAL_DIMENSION` | No |
| `8670` | SR5 Premium | 2WD | `create` | `ADJUDICATED_DISTINCT_GRADE` | Yes (`distinct_factory_grade`) |
| `8672` | SR5 Premium | 4WD | `create` | `ADJUDICATED_DISTINCT_GRADE` | Yes (`distinct_factory_grade`) |
| `8674` | TRD Off-Road | 4WD | `create` | `ADJUDICATED_DISTINCT_GRADE` | Yes (`distinct_factory_grade`) |
| `8676` | TRD Off-Road Premium | 4WD | `create` | `ADJUDICATED_DISTINCT_GRADE` | Yes (`distinct_factory_grade`) |
| `8682` | Venture Special Edition | 4WD | `create` | `ADJUDICATED_DISTINCT_GRADE` | Yes (`special_edition_grade`) |
| `8686` | Limited | 2WD | `create` | `ADJUDICATED_DISTINCT_GRADE` | Yes (`distinct_factory_grade`) |
| `8688` | Limited | 4WD | `create` | `MECHANICAL_DIMENSION` | No (differs mechanically from `8686`) |
| `8690` | Nightshade Special Edition | 2WD | `create` | `ADJUDICATED_DISTINCT_GRADE` | Yes (`special_edition_grade`) |
| `8692` | Nightshade Special Edition | 4WD | `create` | `MECHANICAL_DIMENSION` | No (differs mechanically from `8690`) |
| `8680` | TRD Pro | 4WD | `create` | `MECHANICAL_DIMENSION` | No (differs mechanically from `8674`) |

**Summary**: 12 configurations $\rightarrow$ 12 separately authorized executions $\rightarrow$ 7 human adjudications (1 `FIRST_REPRESENTATION`, 4 `MECHANICAL_DIMENSION`, 7 `ADJUDICATED_DISTINCT_GRADE`).

---

## 14. Record of Pre-Approval Implementation Defects Corrected

During implementation review and critical inspection passes, six pre-approval implementation defects were identified and resolved before final approval:
1. **Initial Single-Artifact Evidence-Revision Binding**: Fixed single-hash extraction by adding `evidence_raw_hashes` to `CandidateConfigurationDocument` and enforcing set equality (`cand_raw_hashes == adj_raw_hashes`).
2. **Free-Text Review-Reason Adjudicability**: Replaced `startswith()` string matching with typed `ImportReviewCategory` enum system.
3. **Forged Adjudicated Manifest Trust Gap**: Added disk load and 6-point verification of actual `CanonicalImportAdjudication` artifact in `execute_canonical_import_workflow()`.
4. **Initial Product Information Provenance Gap**: Attached explicit `ExtractionProvenance` to Product Information PDF assertions under `source_id = "toyota_usa"`.
5. **Manifest v1.0 Adjudication-Field Over-Acceptance**: Enforced strict manifest versioning rejecting adjudication fields on `v1.0` manifests.
6. **Temporary `--no-input` Authorization Bypass**: Removed temporary testing flag from production CLI, restoring mandatory interactive `[y/N]` confirmation.

---

## 15. Exact File Inventory

### Production Python Files Modified / Created
- `reference/ingestion/acquisition/toyota_extractor.py` (New: PDF text extractor strategies)
- `reference/ingestion/contracts.py` (Modified: Added `evidence_raw_hashes`, `CanonicalImportAdjudication`)
- `reference/ingestion/candidate/builder.py` (Modified: Populated `evidence_raw_hashes`)
- `reference/ingestion/importing/__init__.py` (Modified: Added `ImportReviewCategory`, `review_category`, `ADJUDICATED_DISTINCT_GRADE`)
- `reference/ingestion/importing/planner.py` (Modified: Typed categories, adjudication re-planning)
- `reference/ingestion/importing/importer.py` (Modified: `ADJUDICATED_DISTINCT_GRADE` execution and stale-state handling)
- `reference/ingestion/importing/workflow.py` (Modified: Execution adjudication verification)
- `reference/ingestion/manifest.py` (Modified: Manifest `v1.1` schema, serialization, validation)
- `reference/ingestion/serialization.py` (Modified: Adjudication serialization & hashing)
- `reference/ingestion/validation.py` (Modified: Adjudication validation)
- `reference/ingestion/acquisition/profiles.py` (Modified: PDF acquisition profile)
- `reference/ingestion/orchestration/manufacturer.py` (Modified: PDF extraction integration)
- `reference/management/commands/acquire_manufacturer_specs.py` (Modified: PDF acquisition CLI)
- `reference/management/commands/adjudicate_canonical_import.py` (New: Adjudication CLI command)
- `reference/management/commands/execute_canonical_import.py` (Modified: Adjudication artifact loading, mandatory interactive prompt)
- `reference/models.py` (Modified: Added `adjudication_hash` to `ImportExecutionReceipt`)
- `reference/admin.py` (Modified: Added `adjudication_hash` to admin read-only list)
- `reference/migrations/0003_importexecutionreceipt_adjudication_hash.py` (New: DB migration)

### Test Files & Fixtures
- `reference/tests/fixtures/acquisition/toyota/2020_4runner_pricing.pdf` (New: Authentic PDF)
- `reference/tests/fixtures/acquisition/toyota/2020_4runner_specs.pdf` (New: Authentic PDF)
- `reference/tests/test_toyota_extractor.py` (New: Extractor unit tests)
- `reference/tests/test_adjudication_workflow.py` (New: Adjudication workflow unit tests)

---

## 16. Verification & Test Accounting

### Required Verification Commands Executed
1. `.venv/bin/python manage.py check`: **Clean (0 issues)**.
2. `.venv/bin/python manage.py makemigrations --check`: **Clean (0 pending changes)**.
3. `.venv/bin/python manage.py test`: **185/185 tests passing**.
4. `git diff --check`: **Clean (0 issues)**.
5. `git status --short`: **All changes unstaged / uncommitted**.

### Test Accounting Summary
- **Baseline Prior to RA-026**: 154 tests
- **Added by RA-026 Extractor & Adjudication Package**: 31 tests
- **Final Project Test Total**: **185 tests passing** (163 `reference`, 5 `config`, 8 `core`, 9 `observation`).
