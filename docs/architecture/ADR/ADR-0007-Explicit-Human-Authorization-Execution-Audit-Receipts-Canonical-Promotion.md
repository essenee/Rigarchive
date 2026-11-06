# ADR-0007: Explicit Human Authorization & Execution Audit Receipts for Canonical Promotion

- **Status**: Accepted  
- **Date**: 2026-08-15  

## Context

RigArchive's canonical promotion pipeline ([ADR-0004](ADR-0004-Canonical-Reference-Matching-Import-Promotion-Strategy.md), [ADR-0005](ADR-0005-Manufacturer-Grade-Taxonomy-Market-Applicability-Normalization.md), [ADR-0006](ADR-0006-Immutable-Raw-Acquisition-Snapshots-Layered-Manufacturer-Profiles.md), [RA-019](../../implementation/tasks/RA-019-canonical-reference-import-planning-create-only-execution-implementation.md), [RA-023](../../implementation/tasks/RA-023-production-manufacturer-artifact-acquisition-dry-run-orchestration-implementation.md)) evaluates candidate configuration documents against the canonical Reference database, producing transient `CanonicalImportPlan` planning decisions (`plan_candidate_import`) and executing create-only database promotion (`execute_candidate_import`). Production manufacturer acquisition ([RA-023](../../implementation/tasks/RA-023-production-manufacturer-artifact-acquisition-dry-run-orchestration-implementation.md)) operates as an operator-invoked dry-run pipeline performing zero automatic canonical database writes.

To safely transition an eligible candidate configuration from dry-run planning into canonical database promotion, RigArchive requires a durable architectural decision governing explicit human authorization, review manifest integrity, execution provenance audit retention, transaction atomicity, and the strict separation between expected domain outcomes and infrastructure failures.

## Decision

Adopt the following durable architectural policies for canonical reference import execution, human authorization, review manifests, and execution audit provenance:

1. **Explicit Human Authorization Requirement**:
   Canonical database promotion MUST require explicit, affirmative human/operator authorization. Planner eligibility (`ImportEligibilityStatus.ELIGIBLE` / `ImportPlannedAction.CREATE`) grants permission to *consider* canonical promotion; it does NOT grant automatic execution authority.

2. **Exact-Plan Authorization Boundary**:
   Human authorization applies strictly to the *exact plan reviewed by the operator*. Authorization does NOT grant permission to silently re-plan or substitute a different creation basis or action under prior authorization.

3. **Stale Plan Re-planning Policy**:
   If live canonical database state changes between human review and execution dispatch, the reviewed plan MUST abort with `ImportExecutionOutcome.ABORTED_STALE_PLAN`. A stale plan MUST NOT be automatically re-planned and executed under previous authorization; a new planning and human review cycle is required.

4. **Transient Planning Objects**:
   `CanonicalImportPlan` MUST remain a short-lived, transient in-memory dataclass representing canonical state at a specific planning moment. Plans MUST NOT be stored as durable canonical records or database models.

5. **Review Manifest Contract**:
   Reviewed plan state MUST be preserved in an immutable, serialized `CanonicalImportReviewManifest` artifact containing exact plan fields and deterministic content hashing (`sha256:<64_lowercase_hex>`) calculated over canonicalized compact JSON (`separators=(",", ":")`).

6. **Permanently Non-Mutating Acquisition Commands**:
   Acquisition CLI commands (such as `acquire_manufacturer_specs`) MUST remain strictly read-only with respect to canonical Reference database records. Acquisition commands MUST NOT accept execution or override flags that mutate canonical data.

7. **Dedicated Execution Command**:
   Canonical database mutation MUST occur exclusively through a separate, dedicated execution command (such as `execute_canonical_import`).

8. **Single-Plan Initial Execution Scope**:
   Canonical execution MUST operate on exactly one reviewed plan per command invocation. Batch execution is explicitly deferred to preserve clear authorization boundaries and prevent intra-batch stale state invalidation.

9. **Durable Execution Audit Receipts**:
   Every authorized canonical execution attempt MUST persist a durable `ImportExecutionReceipt` database record capturing execution metadata, manifest hash, evidence anchors (`raw_artifact_hash`, `raw_artifact_reference`, `source_id`, `native_identifier`), target field snapshots, actual domain outcomes, and resulting canonical entity IDs/UUIDs/slugs.

10. **`CREATED` Outcome Atomicity Invariant**:
    Canonical `VehicleDefinition` creation and `ImportExecutionReceipt` persistence MUST be atomic within the same database transaction. If audit receipt persistence fails after canonical creation succeeds, the entire transaction MUST roll back cleanly. Zero canonical `VehicleDefinition` records MUST exist without a corresponding `CREATED` execution audit receipt.

11. **Separation of Domain Outcomes and Workflow Failures**:
    Expected canonical execution outcomes (`CREATED`, `NO_OP_EXACT_MATCH`, `ABORTED_STALE_PLAN`, `REJECTED`) are domain results and MUST remain distinct from workflow/infrastructure failures (database connectivity drops, audit save failures, unexpected errors). Workflow and infrastructure failures MUST NOT be converted into `REJECTED` canonical import outcomes.

12. **Attribution, Not Authentication**:
    CLI execution MUST record the declared human director in `operator_label` and the actual interface in `execution_channel`. Record the declared execution agent separately in versioned receipt metadata. Resolve director and agent through explicit overrides, project-local configuration, or the documented nonpersonal defaults. Do not discover OS usernames for attribution. These labels do not authenticate the operator or replace affirmative authorization. Historical approval serialization and attribution remain valid.

13. **Decoupling Audit Receipts from Evidence Modeling**:
    Execution audit receipts record historical execution attempt metadata and are strictly distinct from long-term canonical evidence relationships. Audit receipt persistence MUST NOT add speculative evidence foreign keys or join models to `VehicleDefinition`.

## Accepted Stage 6A amendment

The original decisions continue to govern single-plan imports. This amendment qualifies decisions 2, 3, 5, 8 and 9 solely for the dedicated Generation Trim Matrix path. Decision 10 still requires atomic creation and receipt persistence.

- One affirmative human approval binds the digest of a versioned, immutable matrix. It covers only the enumerated configurations, their exact canonical parent chain, market and years, intended actions, permitted creation bases, candidate digests, manufacturer evidence and applicable correspondence.
- Fresh execution plans may be derived for unchanged authorized rows. Namespace counts, plan and execution-manifest digests, receipt IDs and completion status do not alter matrix approval. Material changes require approval of the affected scope. Unchanged rows retain their authorization.
- Execute one model year per batch by default. A failed year rolls back all provisional creates and receipts from that attempt. Previously committed years remain committed. A durable local report records failed attempts.
- Version 1 retains the immutable matrix, approval record and supporting artifacts in backed-up local review storage. Individual receipts link the matrix digest and row identity using the existing receipt JSON. No authorization model or migration is required.

See the [ingestion protocol](../../development/INGESTION_PROTOCOL.md#generation-trim-matrix-stage-6a) for operational rules. This decision approves architecture only. Stage 6B implementation and the 74 remaining defined MY2007–2017 US Jeep Wrangler JK core imports require separate authorization.

## Rationale

- **Preventing Automated Database Corruption**: Requiring explicit human authorization and keeping acquisition commands strictly read-only guarantees that automated web scraping or dry-run acquisition can never corrupt the canonical Reference database.
- **Stale-Plan Safety**: Disallowing silent re-planning ensures that an operator never authorizes one canonical representation only to have the system create a materially different configuration when database state changes.
- **Auditability & Traceability**: Durable `ImportExecutionReceipt` audit records provide complete, unbroken lineage linking canonical `VehicleDefinition` creations back to exact operator authorizations, review manifests, and immutable raw source snapshots.
- **Transaction Safety**: Enforcing atomicity between `VehicleDefinition` creation and `ImportExecutionReceipt` persistence guarantees zero orphaned canonical records lacking audit receipts.

## Consequences

### Positive
- Production acquisition and canonical mutation are cleanly separated into non-mutating acquisition and explicit execution phases.
- Every canonical promotion attempt leaves a permanent, auditable database receipt.
- Stale plan revalidations prevent concurrent or outdated import executions.

### Negative
- Operator workflow requires a two-step process: generating/reviewing a manifest followed by executing a single plan.
- Re-planning after a stale abort requires generating a new review manifest.

## Alternatives Considered

- **Automated Execution on Acquisition**: Rejected because web acquisition must never mutate canonical database records without explicit operator authorization.
- **Silent Re-Planning on Execution**: Rejected because substituting a new plan under prior human authorization violates the trust boundary.
- **Converting Infrastructure Errors to REJECTED**: Rejected because code/database failures are not domain rejection decisions and must surface as workflow errors.
