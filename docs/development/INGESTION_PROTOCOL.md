# Reference ingestion protocol

Authority: accepted [ADR-0010](../architecture/ADR/ADR-0010-Generation-Correspondence-Selectable-Factory-Alternatives.md), particularly Milestone 1, together with ADR-0004/0006/0007/0008. Transmission and factory-package persistence remain future work.

## Wrangler ingestion workflow W2 — Edmunds-first (2026-11-10)

For the remaining Wrangler model years starting MY2022, the owner has approved **Edmunds as the primary provisional working source** for marketed trims, body styles, engines, transmissions, trim-specific Mechanical Options and Quick Order Packages. The working assumption is that Edmunds is likely correct or mostly correct based on prior Wrangler comparisons; this is an explicit provisional source-confidence choice, not completed manufacturer verification. Comprehensive order-guide/revision validation is deferred until usage, time and priorities justify it. Targeted manufacturer evidence remains appropriate for ambiguous, inconsistent or missing relationships.

Do not use only the default powertrain displayed by a trim selector. Preserve QOP-to-engine/transmission links only where supported; co-listed options alone do not authorize a combination or Cartesian expansion. Maintain source URLs, dates, identifiers, retained-original versus research-transcription distinctions and attribution. Unknowns remain unknown. Existing Candidate, Engine Proof, five-field identity, qualified evidence, human adjudication, generation correspondence, Matrix, stale-plan, atomic import and receipt controls are **not waived**. Record any incompatibility between provisional Edmunds evidence and existing eligibility/proof contracts for a separately authorized decision; never fabricate proof or claim manufacturer verification.

This workflow label **W2** is unrelated to the separate **W2 full-specifications domain architecture** documented below. See the [MY2022 change-of-course and original experiment results](../implementation/handoffs/MY2022_JL/WORKFLOW_EXPERIMENT_20261109.md) and the [coverage/deferrals register](../implementation/CANONICAL_COVERAGE_AND_DEFERRALS.md). No general source-policy change for other vehicle models is implied.

## MY2022 JL experimental lightweight workflow (2026-11-09)

The owner-authorized [MY2022 process experiment](../implementation/handoffs/MY2022_JL/WORKFLOW_EXPERIMENT_20261109.md)
uses the existing 21-source discovery and bounded Edmunds offering comparison to
construct 55 provisional Candidate 2.1.0 artifacts, with unsupported fields left null,
one RHD row deferred and eight transmission/QOP gaps preserved. It narrows repeated
acquisition, historical revision research and discrepancy investigation to material
identity questions; it does not replace the established MY2019–MY2021 procedures or
generalize this exception to other ingestions.

Candidate/Engine Proof validation, qualified lineage, human classification approval,
source-bound generation publication, Matrix certification, stale-plan checks, atomic
create-only import and execution receipts remain mandatory. Offering agreement cannot
supply missing five-field identity values or authorize import. See the linked record
for the comparison, rationale, actual measurements and post-MY2022 evaluation criteria;
experiment success is not yet established. No architecture or wire contract changed.

## W2 approved design contracts — not operational yet

The [W2 domain](../architecture/designs/W2-Full-Specifications-Domain-Architecture.md), [property/applicability](../architecture/designs/W2-Specification-Property-Applicability-Contract.md), [enrichment/publication](../architecture/designs/W2-Enrichment-Publication-Contract.md) and [implementation plan](../architecture/designs/W2-Phase-A-Implementation-Plan.md) are approved Phase A architecture contracts. [ADR-0011](../architecture/ADR/ADR-0011-Factory-Body-Configuration-Identity.md) records the accepted narrow van-body identity amendment; historical ADR-0010 remains unchanged. None introduces implemented commands, changes current Candidate v2/manifest 2.0 execution semantics, authorizes data writes or expands accessory scope. Keep using the implemented protocol below until separately authorized implementation supplies new validated operations.

## W2 B1 pure contract APIs (implemented; no publication command)

`reference.specifications` provides deterministic pure-Python validation and serialization of W2 assertions, complete catalogue snapshots, enrichment v1 and publication manifests v1. `validate_enrichment`/`validate_manifest` require explicitly supplied retained artifact bytes, exact existing member/predecessor records and controlled feature/state bindings. They perform no filesystem access, database lookup/write, acquisition, authorization or publication. `serialize_artifact`/`deserialize_artifact` validate and freeze canonical bytes; mutations to a returned dictionary do not change the snapshot. `serialize_catalogue`/`deserialize_catalogue` validate full exact-member state, not incremental patches.

`publication_disposition` compares explicit caller-supplied target/parent/dependency/current-catalogue snapshots and the exact authorized manifest hash. It returns publish or exact-current no-op, or raises ContractError for stale/invalid state. It does not authenticate a director or reviewer, grant authorization, persist receipts or execute the disposition. A future separately authorized B2 boundary must obtain trustworthy live inputs and enforce transactions. No current baseline executor accepts these new operation semantics.

Retained assertion binding supports original SourceAssertionSet v1 (schema 1.0.0/1.1.0) artifacts and checks source/extractor/set/local identity and original values against supplied bytes. Unsupported/unverifiable retained formats fail closed; manufacturer PDF/HTML bytes alone are not substitutes for extracted qualified assertions. Legacy numeric bytes and lexemes remain preserved. Unit registries, referenced definitions and evidence are supplied explicitly; no production seeds/backfills are installed. Categorical qualifiers use the director-approved exact categorical definition revision/hash, not the parent property's terms. Accessory-dependent evaluation and body/series curation publication remain deferred.

## Evidence and interpretation boundaries

### Owner-approved classification adjudication policy (2026-11-08)

Manufacturer technical specifications are preferred evidence, not mandatory.
Sources need not use RigArchive's internal classification terminology. Seek
applicable explicit documentation when reasonably available; otherwise assemble
the best available evidence and present derived conclusions for human review,
including exact source references, reasoning, applicability, limitations,
confidence and unresolved contradictions. Human adjudication is the normal
resolution path for supported classifications that lack explicit source wording.
Unsupported, materially contradictory or unapproved conclusions remain blocked.
Never rewrite an inference as a manufacturer's raw assertion.

`CanonicalImportAdjudication` 1.0 grade decisions retain their original semantics
and hashes. Version 1.1 adds `evidence_backed_classification`, with explicit
`proposed_classifications` and `approved_classifications` decisions. Its existing
`evidence_anchors` bind the exact retained original candidate digest/path,
qualified supporting documents and each value's rationale, applicability,
limitations, confidence, source references and evidence status. This is a finding
about facts, separate from import authorization and generation publication.

The initial consumer fills unknown `engine_aspiration`, `fuel_type` and
`electrification_type` on Candidate 2.1.0 for any manufacturer; it cannot replace
established values, adjudicate unrepresented attributes or bypass other identity
and generation controls. Other classification consumers can reuse the same
review mechanism when explicitly implemented; they are not implicitly enabled.
Candidate/Manifest/Matrix wire versions and existing direct-source validation are
unchanged. Approved declarations use a visibly human evidence source, structured
conclusions and a distinct extractor, rather than forged manufacturer terms or
executable `unknown_fields` extensions.

The existing `adjudicate_canonical_import` command accepts `--classification-review`
with a retained proposal and requires `--output`, `--candidate-output`, a declared
human `--operator`, and exact interactive `APPROVE CLASSIFICATIONS` confirmation.
Decline/EOF creates no files or records. New output paths are exclusive and must
remain inside the repository. On confirmation, it writes a separate approved
artifact and candidate revision, preserving the unapproved proposal and original
candidate. Do not run this mode until the human owner approves the classifications.
Artifact hashes and declared roles are audit records, not cryptographic identity
authentication. The later exact import-manifest/matrix approval is still required.

The ordinary planner and executor consume the classified candidate. Existing
candidate digests, generation-resolution documents, engine proofs, manifests and
receipts retain the approved declaration's semantic hash, original byte hash,
reviewer/time and supporting lineage. Validation and execution recheck the exact
projection, original candidate and retained evidence; stale/changed approvals or
premises block. Human declarations cannot be silently relabelled as direct-source
claims. Historical receipts are not rewritten. See the
[implementation/review record](../implementation/tasks/MY2019-erc-classification-adjudication.md).

Retain original source bytes before extraction. Preserve source ID, locator, retrieval metadata, full SHA-256 hash, document revision and commercial market applicability. A caller's make/model/year/Generation request is context, not evidence. A source code is never a canonical primary key.

SourceAssertionSet remains v1. Extract generation statements verbatim using `generation_designation`, `generation_code`, `source_model_code`, or `generation_section` where the source actually supplies them. Keep document-local assertion IDs and meaningful source locations. Empty explicit identities are errors, not absence of evidence. Do not infer a Generation from a trim name or manufacture an identifier from configuration attributes.

The bounded `explicit_generation_identity` normalizer (version 1.0.0) preserves these identifiers and their source namespaces without selecting a canonical Generation. Configuration-to-section membership and cross-document correspondence must be established in retained evidence, not inferred from equal labels. Acquisition/extractor support for a new publication remains separately scoped work.

## Brochure-governed optional equipment policy

Permanent, manufacturer-neutral policy approved by the project director on 2026-11-04. This section governs ordinary equipment ingestion across all manufacturers, including Jeep W1.

1. The applicable manufacturer brochure governs ordinary ingestion scope for factory optional packages and optional equipment. Preserve model year, market, publication revision and configuration applicability.
2. Ingest a factory package only when the brochure identifies it as a package and documents its contents and applicability. Preserve manufacturer terminology and codes; “Package” or “Group” in a name alone is insufficient classification evidence.
3. Ingest brochure-supported individual factory options as individual options. Never fabricate package groupings from independently listed options.
4. Keep standard equipment, factory optional packages, individual factory options and accessories distinct. Manufacturer availability does not establish factory installation.
5. Manufacturer accessories may be ingested only when explicitly included in the applicable brochure. They remain accessories unless evidence establishes otherwise; exceptional reclassification requires explicit, documented human review and authorization.
6. Manufacturer accessories absent from the applicable brochure are categorically excluded from ingestion, even when separate manufacturer accessory catalogues or press releases describe them. This exclusion has no automatic exception path.
7. Optional equipment identified outside the brochure must not automatically become a factory package. A compelling, documented exception requires explicit human review and authorization scoped to the exact equipment, source revision, classification and applicability. Routine normalization, a caller flag or grade adjudication cannot provide that authorization. The current assessor leaves such cases review-required; it does not execute exception approval.
8. Never use accessory availability to infer factory configuration, trim, package compatibility or canonical VehicleDefinition identity. Independent availability does not prove coexistence.
9. Preserve source identity, document revision/hash, assertion locations, original labels/values/units, contents, standard/optional qualifiers, restrictions and applicability for every ingested equipment assertion. Missing or conflicting applicability remains unresolved.
10. These rules do not require all vehicle identity or technical specifications to originate from brochures. Other authoritative manufacturer publications remain acceptable. A press release may support vehicle/body/grade identity without authorizing ingestion of its accessory catalogue or establishing factory equipment compatibility.

Full original publications may be retained intact even when accessory listings are excluded from structured ingestion. Raw retention is not equipment promotion: record exclusions and their reasons, and do not project excluded listings into candidate factory equipment. For Jeep W1, preserve the established JK Sport two-door finding and correspondence proposal. A retained original Mopar/Jeep release may supplement JL two-door Sport identity only; customization parts do not establish stock mechanical specifications or factory packages.

This policy authorizes neither permanent package/Full Specifications models nor correspondence publication or canonical import. Accepted ADRs remain unchanged; ADR-0010's subordinate-alternative and accessory boundaries continue to apply.

## J.D. Power core configuration evidence

J.D. Power is independently sufficient for core factory identity when a reviewed structured inventory explicitly binds make, model, year, market, grade, body, engine and relevant mechanical distinctions. Manufacturer corroboration is preferred and optional. Manufacturer technical publications remain preferred. J.D. Power technical values may be used when their exact applicability is explicit.

Record disagreements with authentic manufacturer evidence and defer unresolved rows. Missing manufacturer evidence alone is not a conflict. Record publisher, source ID, retrievable citation, model year, market, original designation and explicit identity fields. A reviewed structured JSON inventory is sufficient. Original HTML, webpage digests and HTML selectors are optional. Retain and hash the structured JSON for Candidate v2 lineage and correspondence integrity. A source-local JSON row identifier is sufficient for that lineage. Keep internal artifact digests, approvals and receipts under their existing contracts. Existing brochure rules still govern optional equipment, packages and accessories.

## Reviewed correspondence and publication

A reviewed artifact has exactly two top-level fields: `review` and `content_hash`. The latter is `sha256:<64 lowercase hex>` over sorted, compact UTF-8 JSON of `review`, with `ensure_ascii=False`, excluding the hash itself. Hash integrity is not user authentication or execution authorization.

The review payload version is `1.0` and contains:

- `revision_uuid`, stable `correspondence_uuid`, positive `revision_number`, nullable `supersedes_uuid`.
- Existing `vehicle_model_uuid`, nullable `generation_uuid`, commercial `market`, inclusive `start_year`/`end_year`.
- `source_id`, `source_namespace`, `identity_type`, `native_identifier`.
- `restrictions`, `evidence`, `finding`, `reviewer`, `reviewed_at`, `review_notes`.

Review timestamps use canonical aware UTC ISO format with `+00:00`. Findings are `established`, `ambiguous`, `rejected`, or `withdrawn`. Established findings require an active target and consistent parents/range. The selector must occur in its retained source assertions. Milestone 1 restrictions are exact strings for `trim_name`, `engine_name`, and `drivetrain`; unrepresented restrictions block use rather than becoming executable expressions.

Each evidence document records source ID, raw artifact hash/reference, extractor ID/version/mode, source-local assertion-set ID and original assertion IDs/keys/values/locations. Evidence references resolve within repository `BASE_DIR`; raw bytes are rehashed at publication and import execution. Do not replace retained snapshots. A changed candidate source revision requires a new applicable correspondence review; a historical revision is not automatically transferred to it.

Publish one exact reviewed artifact with:

```bash
venv/py313/bin/python -B manage.py publish_generation_correspondence --review <review.json> --operator <attribution>
```

The command displays the reviewed artifact and requires affirmative confirmation. Repository database-write authorization must also have been granted for the concrete operation; CLI confirmation is not a substitute for project authorization. Decline/EOF writes nothing. No parents are created.

`GenerationCorrespondenceRevision` is append-only. Its UUID identifies the revision; `correspondence_uuid` identifies its chain. Successors retain source identity and model/market/year scope. Scope changes require a separately reviewed chain and can create a conflict with other applicable chains. Supersession and withdrawal preserve history; a withdrawn/unresolved leaf prevents reuse of an earlier established revision.

Database constraints enforce unique chain/revision and at most one successor per predecessor. Supported model/queryset/admin paths disallow mutation/deletion. These controls do not claim protection from privileged direct SQL or database replacement.

Publication creates a revision and a `correspondence_publication` receipt in one transaction. A failed receipt rolls back the revision and raises an infrastructure error. Stale/invalid publication findings leave no revision and retain an attempt receipt outside the rolled-back insertion transaction where storage permits. Exact repeats have receipts. SQLite may reject competing deferred write upgrades; no writer is reported successful without its receipt. Both contenders may abort, requiring a fresh reviewed attempt. There is no automatic replay under old authorization.

## Candidate v2 and document-qualified lineage

Use `construct_candidate_configuration(..., schema_version="2.0.0")` for the new protocol. Explicit generation assertions automatically require v2. Its artifact type is `rigarchive.candidate_configuration.v2`.

Candidates preserve `generation_evidence`, `evidence_documents`, and the complete evidence-hash inventory. Normalized interpretation references are qualified by source ID, document hash, assertion-set ID and original local assertion ID. Inputs are not mutated. The qualifier separator `|` is reserved; source/set/local assertion IDs containing it are rejected to prevent ambiguous lineage encodings. If the same local ID occurs in multiple documents, the interpretation must supply `unknown_fields.document_qualifier` in the form `source_id|sha256:...|assertion_set_id|`; otherwise construction fails. Publisher ID alone cannot identify a document. Document identity does not create independent corroboration automatically.

All supporting evidence remains separate from caller `CandidateIdentity`. Unknown generation terms remain explicit evidence requiring review; they cannot disappear into the year-only fallback. Candidate v2 execution supports exactly schema 2.0.0. Legacy candidates remain readable; generation-aware data cannot be executed as legacy data.

## Deterministic parent resolution

Resolve existing active Manufacturer and VehicleModel from mapped evidence. Never seed parents during planning.

Without explicit generation evidence, exactly one active Generation covering the model year establishes `unique_year_range`. No match rejects; overlapping matches require review.

With explicit evidence, every supplied source identity requires applicable reviewed correspondence. Consider all current applicable chains, not a caller-selected preferred mapping. Require established findings, matching source revisions, restrictions, market/year/model scope, active parents, and one consistent target. Contradictory, withdrawn, missing or mismatched correspondence blocks promotion. A failed explicit correspondence never falls back to year-only resolution. Grade adjudication is not an override.

Preserve legitimate overlapping ranges, UUIDs, slugs and canonical identities. Two-door/four-door distinctions remain governed by approved trim normalization. This protocol creates neither production Jeep data nor new body-identity semantics.

Resolution basis is separate from canonical creation basis. Correspondence review/publication does not authorize vehicle import.

## Local audit attribution

Copy `.rigarchive.example.toml` to the ignored `.rigarchive.toml` at the Django project root if you need different attribution defaults. The resolver uses explicit `--operator` and `--agent` overrides, then `[attribution]` settings, then `project_owner` and `codex`. Use nonpersonal role identifiers. The CLI records its actual interface as `cli`. Configuration supplies attribution only. Matrix approval and execution still require separate affirmative confirmation.

Approval v1 stores the human role in `operator`. The approval prompt displays the declared agent and interface. Those display values do not change approval serialization. Execution records the human role in `operator_label`, the interface in `execution_channel`, and the agent in `resolution_snapshot_json.attribution` with `version: "1.0"` and `execution_agent`. Matrix attempt reports also record the execution agent and interface. Existing approval and execution digests retain their meaning.

## Exact import planning and authorization

Plan a retained candidate offline:

```bash
venv/py313/bin/python -B manage.py plan_canonical_import --candidate <candidate-v2.json> --output <new-manifest.json>
```

Planning performs zero database writes and does not acquire sources. Output uses exclusive creation so an existing reviewed file is not overwritten. A blocked candidate remains blocked; do not edit its action/basis into an executable plan.

Manifest 2.0 binds the complete serialized candidate/hash, evidence documents, actual extraction provenance, target fields/slug, existing target identity where applicable, parent UUIDs/local IDs/activity/relationships/range, resolution basis and correspondence revision UUIDs/hashes. The full manifest has deterministic SHA-256 integrity protection. New metadata survives grade-adjudicated planning without changing creation-basis semantics.

Execute exactly one plan using the existing dedicated command:

```bash
venv/py313/bin/python -B manage.py execute_canonical_import --manifest <manifest.json> --plan-ref <candidate-reference>
```

The command displays generation resolution and candidate hash before confirmation. The workflow verifies manifest integrity, exact membership and equality with the reconstructed plan. It never substitutes fresh planning after authorization. Unknown execution versions, altered targets, inconsistent candidate bindings or fabricated primary provenance are rejected.

## Execution, stale state and audit receipts

Revalidate resolution before both creation and exact no-op handling. Verify parent UUID/ID relationships, activity and ranges; raw bytes; candidate scope; all current applicable correspondence chains; pinned revision hashes; and existing target UUID/slug for an authorized no-op. Re-evaluating these premises is not constructing a replacement import plan.

A new overlap invalidates year-only uniqueness. An unrelated Generation does not invalidate unchanged explicit correspondence. A successor/withdrawal, changed supporting evidence, new applicable contradictory mapping or changed parent state aborts as stale. A repeated exact target cannot hide stale resolution.

For vehicle imports, the workflow encloses execution and receipt insertion in one transaction. A create or no-op is successful only when its `vehicle_definition_import` receipt commits. Stale/rejected results commit only their attempt receipt, with no canonical creation. Infrastructure/receipt failures propagate and roll back; an audit receipt cannot be guaranteed when audit storage is unavailable. Existing namespace/create-basis checks remain in force.

Receipts retain historical fields and add operation type, optional correspondence revision and resolution/candidate-hash snapshots. Existing receipts are not rewritten to assert evidence they never recorded. Primary evidence anchors remain distinct from the full evidence inventory. Admin review of correspondence and receipts is read-only.

## Generation Trim Matrix (Stage 6A)

This is the dedicated matrix path under the [ADR-0007 amendment](../architecture/ADR/ADR-0007-Explicit-Human-Authorization-Execution-Audit-Receipts-Canonical-Promotion.md#accepted-stage-6a-amendment). The existing single-plan authorization, stale-state and receipt rules above continue to apply to single-plan imports.

### Review and approval

Review a versioned matrix for one canonical Generation and market. Enumerate each row's stable identity, model year, canonical fields and slug, action, permitted creation bases, candidate reference and digest, and applicable evidence and correspondence bindings. Pin the exact parent identities and the canonical PK and UUID of any explicitly reviewed existing record. Reject duplicate identities or slugs, ambiguous references and wildcard scope.

Hash the immutable matrix using the existing sorted, compact UTF-8 JSON SHA-256 convention. Specify deterministic row and reference ordering and preserve meaningful evidence order. Record an affirmative approval of the exact digest with declared human operator attribution and UTC timestamp in a separate linked approval record. A digest verifies integrity and grants no authority by itself. Retain the matrix, approval and supporting artifacts in backed-up local review storage. Keep live namespace counts, execution manifests and progress outside the immutable authorization payload. Separately approve exact additions, replacements or withdrawals against the original matrix digest. Unchanged rows keep their existing approval.

### Stage 6C Generation binding

Matrix version `1.0` continues to require nonempty reviewed correspondence pins. Version `2.0` adds a required row `generation_binding` containing `mode`, `strategy`, and `resolution_version`. The binding incorporates the existing matrix parent PKs, UUIDs and slugs, the row year and market, exact candidate and evidence digests, and any correspondence pins. Approval still binds the complete versioned matrix digest.

- `explicit_correspondence` uses `reviewed_source_correspondence` and exact published revision pins.
- `unique_deterministic` uses `unique_year_range` with empty correspondence pins. It requires an eligible Candidate v2 with explicit make, model, year and market, exactly one active applicable Generation, and no explicit source-generation claim or conflicting applicable correspondence. Matrix approval reviews the exact resolved Generation. Overlap, conflicting or unresolved explicit evidence, and unsupported strategies require review through the existing correspondence process.

For version `2.0`, pass each exact candidate file with repeated `--candidate` arguments to both review and approval. The commands re-plan and display the live validated binding and source identity before approval can be requested. Execution revalidates the binding during preflight and immediately before each create. It never substitutes another mode or strategy. Matrix receipt linkage records the binding alongside the existing plan resolution snapshot. A changed binding requires a new matrix digest and approval. No existing v1 matrix or approval changes meaning.

### Model-year execution and reconciliation

1. Verify approval and preflight every row for the selected year. Validate current parents, evidence, correspondence, canonical identity and slug occupancy across active and inactive records. A blocker or conflict stops pending writes for that year.
2. Verify explicitly reviewed existing records against their pinned identities. Recognize a previously completed create only when a committed creation receipt links the matrix digest, row and candidate to a current record with matching PK, UUID, slug and identity. Skip those verified completions. A matching record without this linkage or an inactive slug owner is a conflict for a proposed create.
3. Execute pending creates in deterministic order inside one transaction for the selected year. Re-plan immediately before each create using the existing planner, including earlier creates in that transaction. Require eligibility and agreement with the authorized row, including action and permitted creation basis. Build and validate the exact Manifest 2.0 and use the existing transactional importer and stale checks. A changed namespace count or execution-manifest digest alone does not invalidate approval of an unchanged row. A stale, rejected or unexpected no-op outcome aborts the year.
4. Require one matching receipt per new create before commit. Retain its execution-manifest digest and record the matrix digest and row ID in the existing receipt JSON. Reconcile committed rows and receipts after commit. Report the authorized count, reviewed existing rows, skipped prior completions, new creates, blockers, conflicts, canonical and receipt PKs and UUIDs, evidence and approval linkage, unexpected changes and completion status.
5. On failure, roll back all provisional creates and receipts from the year attempt. Preserve previously committed years. Save a durable human-readable local failure report with matrix digest, year, failed row or operation, reason, rollback status and available plan or manifest digest. Surface a report-write failure as a workflow error. Retry after fresh validation resolves the blocker. Committed receipts and live canonical identities allow report recovery and safe continuation without renewed approval for unchanged rows.

### Stage 6B operator commands

Use backed-up local review storage, such as an existing directory under `backups/review/`. Supply the matrix JSON and exact Candidate v2 files. For each row, evidence references use `source_id|raw_artifact_hash|assertion_set_id` and the digest of the complete evidence document. Correspondence references use the revision UUID and its content digest.

- `review_generation_trim_matrix --matrix MATRIX` validates and displays the scope and digest.
- `approve_generation_trim_matrix --matrix MATRIX --output APPROVAL` displays the same scope, requires affirmative confirmation and creates a separate approval JSON file exclusively.
- `reconcile_generation_trim_matrix --matrix MATRIX --approval APPROVAL --year YEAR --candidate CANDIDATE` reports live status without writes. Repeat `--candidate` for each row input. Candidate inputs for other approved years can support failure-report progress checks.
- `execute_generation_trim_matrix_year` takes the same inputs as reconciliation plus `--output-dir DIRECTORY`. Use `--dry-run` for read-only preflight. Execution requires operator confirmation and retains a separate attempt directory containing the matrix, approval, preflight, candidates, execution manifests and result or failure report.

The attempt records the approval operator from the immutable approval artifact and the executing CLI operator separately. Import receipts attribute execution to the latter. An initial artifact failure stops before canonical execution. If the transaction commits but final reporting fails, the command reports the committed state and attempt location. Run read-only reconciliation with the same matrix, approval and candidates to recover receipt-backed status. A reporting failure does not trigger an automatic retry.

Year reports distinguish years verified complete before the attempt, regardless of model-year order, from the year completed during the attempt. Other years can be pending, blocked, conflicting or unverified when their inputs or state cannot be checked.

The v1 command supports ordinary planner creates and pinned existing identities. Adjudication-backed creates need an exact adjudication binding before they can be admitted. Scoped amendments remain a review procedure. These commands do not merge or supersede approval artifacts.

Architecture approval grants no authority to execute the 74 remaining defined JK core imports.

## Legacy compatibility and guard boundaries

Legacy candidate v1 and manifest 1.0/1.1 inspection remains supported. Legacy execution is limited to the original unique-year semantics: active consistent parent chain, matching target Generation and no correspondence catalogue for that model. Ambiguous or correspondence-aware scopes require candidate v2 and fresh manifest review. Missing historical snapshots are not invented.

`plan_generation_population` no longer creates Manufacturer, VehicleModel or Generation records. Missing parents appear as unresolved/rejected plans. Parent curation is a separate authorized operation.

Batch/bootstrap invocations preflight their full model/range/input fixture scope before mutation. They refuse overlapping or correspondence-catalogue scopes and explicit generation/v2 inputs. Correction refuses these scopes before deactivation. These bounded guards do **not** fix legacy batch re-planning, slug-only authorization, receipt suppression, or ordinary legacy correction semantics. Do not use those paths for this protocol.

Existing Toyota and Volkswagen baselines, navigation and unambiguous generation resolution are preserved. No transmission, package, Full Specifications or measurement changes are part of Milestone 1.

## Deployment and verification

Migration `reference/0006_generationcorrespondencerevision_and_receipt_resolution` is additive. It creates no correspondence or vehicle data and does not modify Generation ranges or VehicleDefinition identities. Apply it to development/production only after separate database-write authorization. Retained evidence publication/import requires separately reviewed data operations.

Tests use isolated databases and temporary media/raw storage. Synthetic JK/JL fixtures validate protocol behavior only and are not manufacturer evidence. Required checks include deterministic resolution, invalid scope/conflicts, v2 lineage and manifest integrity, stale state before create/no-op, concurrent successors, receipt rollback, auditable repeats, pre-write guards, zero-write planning, legacy parsing, and Toyota/Volkswagen regressions.


## Codex Django verification on macOS

When the managed Codex session cannot load the Python.org framework used by the local virtual environment, use the verified Homebrew Python 3.13.2 executable with the current project's Python 3.13 packages. This command is scoped to Codex verification. The project virtual environment and normal Terminal workflow remain unchanged.

```sh
PYTHONDONTWRITEBYTECODE=1 \
PYTHONPATH="$PWD/venv/lib/python3.13/site-packages" \
RIGARCHIVE_TEST_DB_PATH=:memory: \
/opt/homebrew/bin/python3.13 manage.py test
```

Run from the repository root. `RIGARCHIVE_TEST_DB_PATH` sets Django's default SQLite name. For execution rehearsals, use a read-only snapshot of development data and explicitly verify that the Django connection targets a disposable copy before invoking the execution service. Keep rehearsal approvals, manifests, snapshots, and receipts separate from live authorization artifacts.


## RA-044 structured powertrain path (2026-11-07)

The [RA-044 implementation record](../implementation/tasks/RA-044-structured-powertrain-identity-implementation.md) documents the explicitly versioned Candidate 2.1.0 / Manifest 2.1 / Matrix 2.1 path. New structured candidates retain exactly five canonical powertrain attributes and qualified normalized source lineage. Marketed liters use canonical decimal strings; cylinders are positive integers; aspiration, fuel and electrification use the controlled vocabulary. Unknown remains null during preparation and cannot authorize a create. One applicable authoritative source can establish several attributes; explicitly joined sources may jointly establish a tuple. No absent hybrid label, ESS label or engine-code spelling establishes a missing classification.

Read-only planning uses the existing `plan_canonical_import` and Matrix review commands. Complete assessed semantic identity precedes locator matching. Peer source bytes and unique successful receipt bindings must establish the relevant structured premises, including nonpersistent assessment of legacy null records. Missing evidence or unrepresented distinctions remain review-required. New-create slugs use the accepted fixed qualifier recipe; conflicting active or inactive slugs block without renaming. Candidate v1 and schema 2.0.0 retain their established compatibility behavior.

Resolution 1.1 and engine proof 2.0 bind the ten target fields and peer premises. Existing approval and execution commands retain affirmative human authorization, exact digest binding, transaction-time revalidation and model-year rollback. Approval v1 is unchanged. Matrix 2.1 must use schema 2.1.0 candidates and resolution 1.1; mixed executable versions are not silently converted. Historical artifacts are not regenerated or upgraded.

The additive migration `reference.0010` is verified as applied to the development database. Assigning historical attributes and executing imports each require separate authorization. Implementation acceptance does not authorize Wrangler JL MY2019–2026 ingestion. W2 subordinate configurations and specifications remain deferred.
