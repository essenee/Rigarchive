# RA-025 — Production Manufacturer Extraction & Review-Adjudication Architecture

- **Status**: Approved Architecture
- **Date**: 2026-08-15
- **Author**: RigArchive Core Engineering Team

---

## 1. Purpose

This document establishes the approved architecture for two critical production boundaries in the RigArchive reference ingestion and canonical promotion pipeline:

1. **Deterministic Manufacturer Extraction Boundary**: Extracting structured manufacturer spec assertions (`SourceAssertionSet`) deterministically from retained, immutable raw publisher snapshots (`storage/raw_source_artifacts/`), eliminating production runtime sidecar dependencies while retaining manually verified transcriptions as golden test evidence.
2. **Review-Adjudication Boundary**: Formalizing a durable, category-specific human domain adjudication mechanism (`CanonicalImportAdjudication`) for bounded `FLAG_REVIEW` conditions, introducing a third explicit `ImportCreateBasis` (`ADJUDICATED_DISTINCT_GRADE`), enforcing exact-plan execution boundaries (zero execution-time basis conversion), and preserving immutable manifest versioning (`CanonicalImportReviewManifest` v1.1).

---

## 2. Governing Architecture

RigArchive operates under a strict authority hierarchy:
1. Current approved task specifications
2. Architectural Decision Records ([ADR-0001](file:///Users/esse/dev/Rigarchive/docs/architecture/ADR/ADR-0001-Entity-Identity-Strategy.md) through [ADR-0008](file:///Users/esse/dev/Rigarchive/docs/architecture/ADR/ADR-0008-Deterministic-Extraction-Review-Adjudication-Adjudicated-Grade-Promotion.md))
3. [`docs/implementation/CURRENT_STATE.md`](file:///Users/esse/dev/Rigarchive/docs/implementation/CURRENT_STATE.md)
4. Engineering Handbook
5. Project Blueprint

Governing prior work includes:
- **[RA-018](file:///Users/esse/dev/Rigarchive/docs/architecture/designs/RA-018-Canonical-Reference-Matching-Import-Architecture.md) / [ADR-0004](file:///Users/esse/dev/Rigarchive/docs/architecture/ADR/ADR-0004-Canonical-Reference-Matching-Import-Promotion-Strategy.md)**: Set-based evidence trust boundary, create-only promotion, and initial `FIRST_REPRESENTATION` and `MECHANICAL_DIMENSION` bases.
- **[RA-020](file:///Users/esse/dev/Rigarchive/docs/architecture/designs/RA-020-Trim-Grade-Market-Applicability-Source-Normalization-Architecture.md) / [ADR-0005](file:///Users/esse/dev/Rigarchive/docs/architecture/ADR/ADR-0005-Manufacturer-Grade-Taxonomy-Market-Applicability-Normalization.md)**: Manufacturer grade taxonomy, commercial market applicability, and Source-Independence Test.
- **[RA-022](file:///Users/esse/dev/Rigarchive/docs/architecture/designs/RA-022-Production-Manufacturer-Evidence-Acquisition-Orchestration-Architecture.md) / [ADR-0006](file:///Users/esse/dev/Rigarchive/docs/architecture/ADR/ADR-0006-Immutable-Raw-Acquisition-Snapshots-Layered-Manufacturer-Profiles.md)**: Immutable raw snapshot retention (`storage/raw_source_artifacts/`), SHA-256 revision hashing (`sha256:<64_hex>`), and layered manufacturer profiles.
- **[RA-024](file:///Users/esse/dev/Rigarchive/docs/architecture/designs/RA-024-Canonical-Reference-Import-Execution-Execution-Provenance-Workflow-Architecture.md) / [ADR-0007](file:///Users/esse/dev/Rigarchive/docs/architecture/ADR/ADR-0007-Explicit-Human-Authorization-Execution-Audit-Receipts-Canonical-Promotion.md)**: Executable review manifest contract (`CanonicalImportReviewManifest` v1.0), exact-plan execution authorization, `ImportExecutionReceipt` audit records, and transactional atomicity.

---

## 3. Current Production Extraction Boundary

Currently, manufacturer spec acquisition ([RA-023](file:///Users/esse/dev/Rigarchive/docs/implementation/tasks/RA-023-production-manufacturer-artifact-acquisition-dry-run-orchestration-implementation.md)) retains immutable raw publisher snapshots (e.g. `2020_4runner_specs.html`), but relies on a manually verified sidecar JSON transcription (`2020_4runner_specs.json`) during runtime candidate construction.

RA-025 replaces this runtime sidecar dependency with **deterministic strategy extractors** operating directly over retained raw publisher snapshots.

```text
               Production Extraction Flow (RA-025 / RA-026)
                                     │
   ┌─────────────────────────────────┴─────────────────────────────────┐
   ▼                                                                   ▼
Immutable Raw Publisher Snapshot                     Versioned Extractor Strategy
(e.g., storage/raw_source_artifacts/.../             (e.g., ToyotaPressroomHtmlTableStrategy)
 2020_4runner_specs.html)                                              │
                                                                       ▼
                                                             SourceAssertionSet
                                                                       │
                                                                       ▼
                                                          Normalizer & Candidate Builder
```

---

## 4. Deterministic Extraction Strategy

Production extraction is executed by versioned, deterministic strategy extractors that parse raw HTML/DOM snapshots into structured `SourceAssertionSet` objects.

### Initial Empirical Scope: `ToyotaPressroomHtmlTableStrategy`
- **Scope**: Targets strictly the empirically verified HTML specification table grid layout preserved in `2020_4runner_specs.html`.
- **Empirical Grounding**: Only the 2020 Toyota pressroom HTML specification grid table is verified by retained repository artifacts. 2010–2024 layouts are NOT assumed to be uniform and MUST NOT be asserted as facts until additional raw publisher snapshots are acquired and inspected empirically.
- **Future Layouts**: Extractors for other layouts (e.g. embedded JSON or PDF specifications) will be implemented as distinct strategy classes when corresponding raw artifacts are acquired.

---

## 5. Extraction vs. Normalization Separation

Strict separation between extraction and normalization is maintained:

* **Extractor Domain**: Reads raw publisher layout structures, extracts verbatim source statements, and preserves raw coexistence grouping (e.g. column groupings, model codes, raw trim headers). Extractors MUST NOT interpret, translate, or normalize source terminology.
* **Normalizer Domain**: Consumes `SourceAssertionSet` output from extractors, applying approved manufacturer profiles and normalization rules to resolve standardized engine, drivetrain, market, and trim concepts under [ADR-0005](file:///Users/esse/dev/Rigarchive/docs/architecture/ADR/ADR-0005-Manufacturer-Grade-Taxonomy-Market-Applicability-Normalization.md).

---

## 6. Extraction Failure Policy

Extractor execution MUST adhere to strict failure policies:
1. **No Silent Row Drops**: If a specification table contains 12 model codes, the extractor MUST extract assertions for all 12 model codes or fail explicitly.
2. **No Guessed Configuration Identities**: Model codes, trim names, and attributes MUST be derived strictly from source DOM nodes; guess-work or fallback synthesis is forbidden.
3. **No Synthetic Attribute-Derived Identities**: Extractors MUST NOT synthesize synthetic IDs or Cartesian configuration combinations.
4. **Controlled Failure**: Unrecognized DOM structures, missing table headers, or corrupted layout tables MUST raise a controlled `ExtractionLayoutError` (or equivalent), preventing partial or false Tier 1 evidence creation.
5. **No Premature Review Flags**: Extractors operate before candidate construction and MUST NOT emit candidate-level `FLAG_REVIEW` flags.

---

## 7. Golden Fixture Validation Strategy

The manually verified transcription `2020_4runner_specs.json` is removed from the production runtime extraction path. It is retained in `reference/tests/fixtures/` as a **golden test fixture**.

### Extractor Test Verification
Extractor test suites MUST execute `ToyotaPressroomHtmlTableStrategy` over the retained raw HTML snapshot `2020_4runner_specs.html` and validate that the generated `SourceAssertionSet` matches the golden fixture across:
- Total configuration count (12 model codes)
- Native model code identities (`8664`, `8666`, `8670`, `8672`, `8674`, `8676`, `8680`, `8682`, `8686`, `8688`, `8690`, `8692`)
- Raw source attribute key/value pairs
- Coexistence grouping and market applicability (`"US"`)

Normalization and candidate construction are tested in separate downstream unit tests.

---

## 8. Review-Adjudication Taxonomy & Adjudicable Categories

When candidate configurations are planned against the canonical database, certain plan conditions result in `planned_action = ImportPlannedAction.FLAG_REVIEW`.

RA-025 classifies `FLAG_REVIEW` conditions into **Adjudicable Categories** and **Non-Adjudicable Hard Blockers**.

```text
                      FLAG_REVIEW Condition Classification
                                       │
         ┌─────────────────────────────┴─────────────────────────────┐
         ▼                                                           ▼
Adjudicable Categories                                Non-Adjudicable Hard Blockers
• distinct_factory_grade                              • Missing required mapped evidence
  (e.g., "SR5 Premium" vs "SR5")                      • Conflicting mapped evidence across attributes
• special_edition_grade                               • Caller/evidence context contradictions
  (e.g., "Nightshade", "Venture")                     • Ambiguous parent Generation matches
                                                      • Target slug collisions with conflicting fields
                                                      • Unrepresented canonical schema dimensions
```

### Approved Adjudicable Categories:
1. `distinct_factory_grade`: Evidence-backed manufacturer trim/grade verified as a distinct factory configuration level (e.g., `"SR5 Premium"` vs `"SR5"`).
2. `special_edition_grade`: Verified manufacturer special edition grade classification (e.g., `"Nightshade Special Edition"`, `"Venture Special Edition"`).

---

## 9. Human Adjudication Semantics

A human adjudication is recorded as a durable, immutable domain finding represented by the `CanonicalImportAdjudication` artifact contract.

### Core Semantic Invariants:
1. **Durable Domain Finding**: An adjudication records a verified human domain proposition (e.g. *"Toyota model code 8670 / trim 'SR5 Premium' represents a legitimate distinct factory grade for the 2020 Toyota 4Runner"*).
2. **NOT an Execution Command**: Adjudication records domain truth; it does NOT mean `"force import"`, `"create now"`, or `"bypass planner"`.
3. **NO In-Place Plan Mutation**: Adjudication NEVER mutates an old `CanonicalImportReviewManifest` or `CanonicalImportPlan` in place.
4. **Mandatory Re-planning**: An approved adjudication serves as a verified semantic input to fresh planning, which produces a NEW reviewed plan requiring NEW explicit operator execution authorization under [ADR-0007](file:///Users/esse/dev/Rigarchive/docs/architecture/ADR/ADR-0007-Explicit-Human-Authorization-Execution-Audit-Receipts-Canonical-Promotion.md).

---

## 10. Non-Adjudicable Hard Blockers

Human adjudication CANNOT override or bypass:
- Missing required mapped evidence (e.g., missing engine displacement or drivetrain)
- Conflicting mapped evidence across source statements
- Context contradiction between caller context and mapped evidence
- Ambiguous parent `Generation` resolution
- Target slug collisions where existing database fields conflict with candidate fields
- Unrepresented canonical dimensions (e.g. candidates differing only by transmission or cab style where `VehicleDefinition` lacks fields)

Any attempt to adjudicate a non-adjudicable condition MUST be rejected with `AdjudicationCategoryError`.

---

## 11. Adjudication Scope vs. Execution Authorization Scope

* **Semantic Adjudication Scope**: Bounded to **exact source-native grade identity within a specific manufacturer/model/year scope** (e.g., `Manufacturer: Toyota`, `VehicleModel: 4Runner`, `ModelYear: 2020`, `Trim: SR5 Premium`).
* **Execution Authorization Scope**: Strictly bounded to **one exact `CanonicalImportPlan` within a single reviewed manifest** under [ADR-0007](file:///Users/esse/dev/Rigarchive/docs/architecture/ADR/ADR-0007-Explicit-Human-Authorization-Execution-Audit-Receipts-Canonical-Promotion.md).

Broad semantic grade approval does NOT grant broad or automatic execution permission.

---

## 12. Adjudication Artifact Contract & Deterministic Hashing

`CanonicalImportAdjudication` is serialized as an immutable JSON artifact (`adjudication_version = "1.0"`):

```json
{
  "adjudication_version": "1.0",
  "created_at": "2026-08-15T15:00:00Z",
  "operator_label": "cli:esse",
  "original_manifest_hash": "sha256:351306bd795582747078573ca851606e40a64e48a996e0cf1f0b573080175eb0",
  "candidate_reference": "cand_ref_8670",
  "source_identity": {
    "source_id": "toyota_usa",
    "source_identity_type": "record_id",
    "native_identifier": "8670"
  },
  "original_review_category": "new_trim_string_in_populated_namespace",
  "adjudication_category": "distinct_factory_grade",
  "adjudication_decision": "approved_distinct_trim",
  "adjudicated_trim_name": "SR5 Premium",
  "adjudication_notes": "Verified against official 2020 Toyota 4Runner pressroom specification hierarchy.",
  "adjudication_hash": "sha256:7a9b8c7d6e5f4a3b2c1d0e9f8a7b6c5d4e3f2a1b0c9d8e7f6a5b4c3d2e1f0a9b"
}
```

### Deterministic Hashing Algorithm
`compute_adjudication_hash()` calculates `sha256:<64_lowercase_hex>` over UTF-8 encoded compact JSON (`separators=(",", ":")`, `sort_keys=True`, `ensure_ascii=False`), excluding `adjudication_hash` itself.

---

## 13. Five-Stage Promotion Lifecycle

The complete promotion lifecycle for review-required candidates consists of 5 explicit stages:

```text
1. PLANNING ──> Candidate + plan_candidate_import() ──> FLAG_REVIEW Plan & Manifest v1.0
                               │
2. ADJUDICATION ──> Operator evaluates domain evidence ──> CanonicalImportAdjudication Artifact
                               │
3. RE-PLANNING ──> Candidate + Adjudication + plan_candidate_import_with_adjudications()
                   ──> NEW ADJUDICATED_DISTINCT_GRADE Plan & Manifest v1.1
                               │
4. AUTHORIZATION ──> execute_canonical_import --manifest new_manifest.json
                     ──> Interactive Operator Confirmation [y/N]
                               │
5. EXECUTION ──> execute_candidate_import() ──> transaction.atomic()
                 ──> VehicleDefinition + ImportExecutionReceipt
```

---

## 14. The Third `ImportCreateBasis` (`ADJUDICATED_DISTINCT_GRADE`)

RA-025 extends `ImportCreateBasis` in `reference/ingestion/importing/__init__.py` by introducing a third explicit enum value:

* `FIRST_REPRESENTATION`: Automated proof that the entire `(generation, model_year, market)` namespace contains zero `VehicleDefinition` rows.
* `MECHANICAL_DIMENSION`: Automated proof from an existing same-trim canonical row in the namespace with a structured drivetrain difference (`2WD` vs `4WD`).
* `ADJUDICATED_DISTINCT_GRADE`: Validated human semantic proof that a previously review-required manufacturer grade is a legitimate distinct canonical grade in an already-populated namespace.

---

## 15. Adjudicated CREATE Prerequisites

`plan_candidate_import_with_adjudications()` will ONLY assign `create_basis = ADJUDICATED_DISTINCT_GRADE` if:
1. All 8 required canonical concepts are present and mapped.
2. Zero evidence conflicts or caller context contradictions exist.
3. Parent `Manufacturer`, `VehicleModel`, and `Generation` resolve uniquely.
4. Target configuration is representable in current `VehicleDefinition` schema.
5. Original review condition is an approved adjudicable category.
6. A valid, hash-verified `CanonicalImportAdjudication` artifact matches `manifest_hash`, `candidate_reference`, `adjudicated_trim_name == evidence_trim`, and decision `"approved_distinct_trim"`.
7. No existing canonical row in the DB already uses the target slug or same trim name.

Setting the `ADJUDICATED_DISTINCT_GRADE` enum value alone without satisfying these prerequisites is strictly forbidden.

---

## 16. Exact-Plan Execution Rule (No Basis Conversion)

Execution in `execute_candidate_import()` operates under strict exact-plan invariants:
- An authorized `ADJUDICATED_DISTINCT_GRADE` plan MUST execute under that exact basis or abort.
- Execution-time revalidation MUST NEVER dynamically re-plan, change `create_basis`, or convert an `ADJUDICATED_DISTINCT_GRADE` plan into `MECHANICAL_DIMENSION` or `FIRST_REPRESENTATION`.
- If database state changes such that a different basis is appropriate, execution MUST return `ImportExecutionOutcome.ABORTED_STALE_PLAN`. Fresh planning and new authorization are required.

---

## 17. Stale-State Rules for `ADJUDICATED_DISTINCT_GRADE`

During `execute_candidate_import()` inside `transaction.atomic()` for `create_basis == ADJUDICATED_DISTINCT_GRADE`:

1. **Parent Entity Check**: Resolved parent IDs must remain active in the database.
2. **Exact-Target Concurrency Check**:
   - If an existing record matching `plan.target_slug` exists:
     * Matching fields $\rightarrow$ returns `NO_OP_EXACT_MATCH` (idempotent, 0 writes).
     * Conflicting fields $\rightarrow$ returns `ABORTED_STALE_PLAN`.
3. **Same-Trim Presence Revalidation**:
   - Re-queries `VehicleDefinition` for `(generation_id, model_year, market, trim_name=target_trim)`.
   - If **ANY** non-target canonical record with matching `trim_name` now exists in the database (e.g. `SR5 Premium 4WD` was inserted while `SR5 Premium 2WD` was in flight), execution returns **`ABORTED_STALE_PLAN`**.
4. **Unrelated-Trim Insertion (Non-Material)**:
   - Insertion of an unrelated trim (e.g. `Limited 2WD`) does NOT invalidate the grade adjudication for `SR5 Premium 2WD`. The plan remains valid and executes (`CREATED`).

---

## 18. Manifest Versioning & Contract Linkage (v1.1)

To support per-plan adjudication linkage while maintaining manifest immutability:
- `CanonicalImportReviewManifest` version `"1.1"` is introduced.
- `CanonicalImportReviewPlan` per-plan dictionary includes optional fields:
  - `adjudication_reference`: `Optional[str] = None` (e.g. `"adjudication_8670.json"`)
  - `adjudication_hash`: `Optional[str] = None` (e.g. `"sha256:7a9b..."`)
- **Backward Compatibility**: Manifest readers MUST maintain explicit backward compatibility so that existing version `"1.0"` manifests remain fully executable.

---

## 19. Execution Receipt Linkage

`ImportExecutionReceipt` will be extended with an optional field:
- `adjudication_hash = models.CharField(max_length=71, blank=True)`

For ordinary executions (`FIRST_REPRESENTATION`, `MECHANICAL_DIMENSION`, `NO_OP_EXACT_MATCH`), `adjudication_hash` remains empty (`""`). For `ADJUDICATED_DISTINCT_GRADE` executions, the verified `adjudication_hash` is persisted, completing the unbroken audit trail:

```text
Raw Snapshot ──> Original Review ──> Adjudication ──> New Review Manifest ──> Execution Receipt
```

---

## 20. Canonical Representability Gate

Human adjudication CANNOT manufacture canonical distinctions that the database schema cannot represent.

If two source configurations differ only by an unrepresented dimension (e.g. transmission type, cab style, or wheelbase):
- Adjudication may record that a real-world manufacturer distinction exists.
- Canonical database promotion remains **BLOCKED** (`FLAG_REVIEW`) pending schema evolution.
- Slug manipulation, notes-based uniqueness hacks, or force-creation are strictly prohibited.

---

## 21. 2020 Toyota 4Runner Controlled Population Study

Tracing the exact incremental population sequence for all 12 2020 Toyota 4Runner model codes into an empty database:

```text
1. 8664 (SR5 2WD)          ──> Empty DB namespace ──> FIRST_REPRESENTATION CREATE (0 adjudications)
2. 8666 (SR5 4WD)          ──> Same trim (SR5) + 4WD vs 2WD ──> MECHANICAL_DIMENSION CREATE (0 adjudications)
3. 8670 (SR5 Premium 2WD)  ──> FLAG_REVIEW ──> Adjudication #1 (SR5 Premium) ──> ADJUDICATED_DISTINCT_GRADE CREATE
4. 8672 (SR5 Premium 4WD)  ──> Re-planned AFTER 8670 in DB ──> MECHANICAL_DIMENSION CREATE (0 adjudications)
5. 8674 (TRD Off-Road 4WD) ──> FLAG_REVIEW ──> Adjudication #2 (TRD Off-Road) ──> ADJUDICATED_DISTINCT_GRADE CREATE
6. 8676 (TRD Off-Road Prem)──> FLAG_REVIEW ──> Adjudication #3 (TRD Off-Road Premium) ──> ADJUDICATED_DISTINCT_GRADE CREATE
7. 8682 (Venture 4WD)      ──> FLAG_REVIEW ──> Adjudication #4 (Venture Special Edition) ──> ADJUDICATED_DISTINCT_GRADE CREATE
8. 8686 (Limited 2WD)      ──> FLAG_REVIEW ──> Adjudication #5 (Limited) ──> ADJUDICATED_DISTINCT_GRADE CREATE
9. 8688 (Limited 4WD)      ──> Re-planned AFTER 8686 in DB ──> MECHANICAL_DIMENSION CREATE (0 adjudications)
10. 8690 (Nightshade 2WD)  ──> FLAG_REVIEW ──> Adjudication #6 (Nightshade Special Edition) ──> ADJUDICATED_DISTINCT_GRADE CREATE
11. 8692 (Nightshade 4WD)  ──> Re-planned AFTER 8690 in DB ──> MECHANICAL_DIMENSION CREATE (0 adjudications)
12. 8680 (TRD Pro 4WD)     ──> FLAG_REVIEW ──> Adjudication #7 (TRD Pro) ──> ADJUDICATED_DISTINCT_GRADE CREATE
```

### Exact Study Breakdown:
- **Total Individual Execution Authorizations**: **12 separately authorized executions** under [ADR-0007](file:///Users/esse/dev/Rigarchive/docs/architecture/ADR/ADR-0007-Explicit-Human-Authorization-Execution-Audit-Receipts-Canonical-Promotion.md).
- **Execution Basis Distribution**:
  - `FIRST_REPRESENTATION`: **1** (`8664`)
  - `MECHANICAL_DIMENSION`: **4** (`8666`, `8672`, `8688`, `8692`)
  - `ADJUDICATED_DISTINCT_GRADE`: **7** (`8670`, `8674`, `8676`, `8682`, `8686`, `8690`, `8680`)
- **Total Human Domain Adjudications Required**: **EXACTLY 7 ADJUDICATIONS**.

---

## 22. Manufacturer Model Code Role

Toyota model codes (e.g. `8664`, `8670`) serve as **supporting evidence** of a source-established configuration identity. They strongly support human grade adjudications, but MUST NOT be used as a primary key or universal canonical distinctness key, and CANNOT replace evidence-backed concept attributes (`trim`, `drivetrain`, `engine`, `market`).

---

## 23. Explicit Non-Goals

RA-025 explicitly excludes:
- Automatic execution on web acquisition.
- Multi-plan batch execution.
- Arbitrary "force import" or plan mutation.
- Production extraction support for unverified 2010–2024 layouts without retained raw snapshots.
- Direct population of canonical reference data.

---

## 24. Future Roadmap: RA-026 & RA-027 Boundaries

* **`RA-026 — Deterministic Toyota Extraction & Review-Adjudication Implementation`** (Engineering Milestone):
  Implements `ToyotaPressroomHtmlTableStrategy` for the 2020 HTML table, golden fixture tests, `CanonicalImportAdjudication` artifact contract, adjudication hashing/validation, adjudication-aware re-planner, `ImportCreateBasis.ADJUDICATED_DISTINCT_GRADE`, manifest v1.1 reader, `adjudicate_canonical_import` CLI, `ImportExecutionReceipt.adjudication_hash` migration, and focused tests.
* **`RA-027 — Controlled Toyota 4Runner Canonical Population`** (Operational Milestone):
  Executes controlled canonical population for Toyota 4Runner model lines using verified RA-026 engineering tooling across empirically supported model-year source coverage.
