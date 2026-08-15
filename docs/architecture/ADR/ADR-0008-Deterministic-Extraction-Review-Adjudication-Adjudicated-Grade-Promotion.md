# ADR-0008: Deterministic Extraction, Review Adjudication & Adjudicated Grade Promotion

- **Status**: Accepted
- **Date**: 2026-08-15

## Context

RigArchive's production manufacturer acquisition ([RA-022](file:///Users/esse/dev/Rigarchive/docs/architecture/designs/RA-022-Production-Manufacturer-Evidence-Acquisition-Orchestration-Architecture.md), [ADR-0006](file:///Users/esse/dev/Rigarchive/docs/architecture/ADR/ADR-0006-Immutable-Raw-Acquisition-Snapshots-Layered-Manufacturer-Profiles.md), [RA-023](file:///Users/esse/dev/Rigarchive/docs/implementation/tasks/RA-023-production-manufacturer-artifact-acquisition-dry-run-orchestration-implementation.md)) retains immutable raw publisher snapshots (`storage/raw_source_artifacts/`), but relied on a manually verified sidecar JSON transcription during runtime candidate construction. Furthermore, when candidate planning ([RA-019](file:///Users/esse/dev/Rigarchive/docs/implementation/tasks/RA-019-canonical-reference-import-planning-create-only-execution-implementation.md), [ADR-0004](file:///Users/esse/dev/Rigarchive/docs/architecture/ADR/ADR-0004-Canonical-Reference-Matching-Import-Promotion-Strategy.md)) flags a candidate for human review (`FLAG_REVIEW`) due to a new manufacturer trim string appearing in a populated namespace, no formal architecture existed to evaluate and resolve that review condition without bypassing planner safety or mutating previously authorized review manifests.

To transition from manually verified sidecar transcriptions to automated deterministic extraction, and to enable safe, auditable human resolution of bounded review conditions, RigArchive requires formal architectural decisions governing extraction strategies, golden fixture testing, human domain adjudications, a third explicit `ImportCreateBasis` (`ADJUDICATED_DISTINCT_GRADE`), exact-plan execution boundaries, manifest versioning, and execution receipt audit linkage.

## Decision

Adopt the following durable architectural decisions for production manufacturer extraction, review adjudication, and adjudicated grade promotion:

1. **Deterministic Extraction from Raw Snapshots**:
   Production manufacturer extraction MUST operate deterministically from retained, immutable raw publisher snapshots using versioned strategy classes (such as `ToyotaPressroomHtmlTableStrategy`). Extractors MUST NOT synthesize missing attributes, drop rows silently, or perform Cartesian configuration reconstruction. Unrecognized layouts MUST raise controlled extraction errors.

2. **Golden Fixture Role for Verified Transcriptions**:
   Manually verified transcriptions (such as `2020_4runner_specs.json`) ARE REMOVED from the production runtime extraction path. They serve as golden test benchmarks to validate that extractor strategies produce identical `SourceAssertionSet` outputs from raw publisher snapshots.

3. **Five-Stage Promotion Lifecycle**:
   Candidate promotion involving human adjudication MUST follow five explicit lifecycle stages:
   ```text
   Planning ──> Adjudication ──> Re-planning ──> Execution Authorization ──> Execution
   ```
   Adjudication is NOT execution authorization; re-planning after adjudication generates a NEW reviewed plan requiring NEW explicit operator authorization under [ADR-0007](file:///Users/esse/dev/Rigarchive/docs/architecture/ADR/ADR-0007-Explicit-Human-Authorization-Execution-Audit-Receipts-Canonical-Promotion.md).

4. **Bounded Human Semantic Adjudication**:
   Human adjudication (`CanonicalImportAdjudication`) is a durable human domain finding (e.g. *"SR5 Premium is verified as a distinct factory grade"*). It is NOT an execution command, force-import switch, or planner bypass.

5. **Category-Specific Adjudication**:
   Adjudication MUST bind strictly to approved adjudicable categories (`distinct_factory_grade`, `special_edition_grade`). Adjudication artifacts MUST cryptographically bind (`adjudication_hash`) to the exact original manifest hash, candidate reference, source identity, and evidence revision.

6. **Non-Adjudicable Hard Blockers**:
   Human adjudication CANNOT override missing required evidence, conflicting mapped evidence, caller/evidence context contradictions, ambiguous parent Generation matches, target slug conflicts, or unrepresented canonical schema dimensions. Such conditions require evidence correction or schema evolution.

7. **Manifest Immutability**:
   Original `CanonicalImportReviewManifest` artifacts MUST remain immutable. Adjudication NEVER mutates an old manifest or plan in place. Re-planning produces a NEW review manifest.

8. **Third Epistemic Basis (`ADJUDICATED_DISTINCT_GRADE`)**:
   Introduce `ImportCreateBasis.ADJUDICATED_DISTINCT_GRADE` to represent validated human semantic proof that a previously review-required manufacturer grade is a legitimate distinct canonical grade in an already-populated namespace.

9. **Prerequisites for Adjudicated CREATE**:
   Setting `ADJUDICATED_DISTINCT_GRADE` requires complete mapped evidence, zero conflicts, unique parent resolution, schema representability, an approved adjudicable category, and a valid, hash-verified `CanonicalImportAdjudication` artifact. Setting the enum alone does NOT grant creation authority.

10. **Exact-Plan Preservation (No Basis Conversion)**:
    Execution NEVER dynamically changes one `create_basis` into another. An authorized `ADJUDICATED_DISTINCT_GRADE` plan MUST execute under that exact basis or abort with `ABORTED_STALE_PLAN`.

11. **Same-Trim Stale-State Rule**:
    If a canonical record with matching trim name appears in the database prior to execution of an `ADJUDICATED_DISTINCT_GRADE` plan, execution MUST abort with `ABORTED_STALE_PLAN`. Fresh planning, a new review manifest, and new authorization are required.

12. **Unrelated-Trim Non-Materiality**:
    Insertion of an unrelated trim into the namespace does NOT invalidate an `ADJUDICATED_DISTINCT_GRADE` plan, as the premise for the adjudicated grade distinction remains valid.

13. **Idempotent Exact-Target Concurrency**:
    If an exact target record appears prior to execution with identical fields, execution returns `NO_OP_EXACT_MATCH` (0 writes). If fields conflict, execution aborts.

14. **Canonical Representability Gate**:
    Human adjudication cannot create canonical distinctions that `VehicleDefinition` cannot represent. Adjudications for unrepresented dimensions (e.g. transmission) record domain truth but CANNOT enable database creation without schema expansion.

15. **Evidence Revision Scope**:
    A `CanonicalImportAdjudication` is historically valid for its original `raw_artifact_hash`. If a new publisher source revision is acquired with a changed hash, the historical adjudication CANNOT be automatically reused; a new candidate/review cycle is required.

16. **Execution Receipt Provenance**:
    `ImportExecutionReceipt` records the verified `adjudication_hash` for adjudication-backed promotions, preserving unbroken audit lineage from raw source snapshot to canonical creation.

## Rationale

- **Runtime Independence**: Removing sidecar JSON files from the runtime path guarantees that production ingestion depends strictly on versioned, auditable code operating over immutable raw snapshots.
- **Planner Integrity**: Establishing `ADJUDICATED_DISTINCT_GRADE` preserves the specific meanings of `FIRST_REPRESENTATION` and `MECHANICAL_DIMENSION` without resorting to force-import plan mutations.
- **Audit Traceability**: Cryptographic hash linkage (`adjudication_hash`) ensures that every human domain decision is verifiably bound to its exact review context and audit receipt.

## Consequences

### Positive
- Production extraction operates directly from retained raw snapshots with golden test verification.
- Review-required candidates can be resolved safely through auditable human domain adjudications.
- Exact-plan execution and stale-state revalidation prevent unauthorized basis transformations.

### Negative
- Human resolution of a flagged plan requires a multi-step workflow: generating an adjudication artifact, re-planning, and authorizing a new review manifest.
- Schema changes are required to represent canonical dimensions that cannot currently be stored.

## Alternatives Considered

- **In-Place Plan Mutation**: Rejected because altering fields on an existing manifest invalidates its hash and violates [ADR-0007](file:///Users/esse/dev/Rigarchive/docs/architecture/ADR/ADR-0007-Explicit-Human-Authorization-Execution-Audit-Receipts-Canonical-Promotion.md).
- **Dynamic Basis Conversion at Execution**: Rejected because substituting a different creation basis under prior human authorization violates the exact-plan authorization boundary.
