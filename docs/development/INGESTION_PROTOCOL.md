# Reference ingestion protocol

Authority: accepted [ADR-0010](../architecture/ADR/ADR-0010-Generation-Correspondence-Selectable-Factory-Alternatives.md), particularly Milestone 1, together with ADR-0004/0006/0007/0008. Transmission and factory-package persistence remain future work.

## Evidence and interpretation boundaries

Retain original source bytes before extraction. Preserve source ID, locator, retrieval metadata, full SHA-256 hash, document revision and commercial market applicability. A caller's make/model/year/Generation request is context, not evidence. A source code is never a canonical primary key.

SourceAssertionSet remains v1. Extract generation statements verbatim using `generation_designation`, `generation_code`, `source_model_code`, or `generation_section` where the source actually supplies them. Keep document-local assertion IDs and meaningful source locations. Empty explicit identities are errors, not absence of evidence. Do not infer a Generation from a trim name or manufacture an identifier from configuration attributes.

The bounded `explicit_generation_identity` normalizer (version 1.0.0) preserves these identifiers and their source namespaces without selecting a canonical Generation. Configuration-to-section membership and cross-document correspondence must be established in retained evidence, not inferred from equal labels. Acquisition/extractor support for a new publication remains separately scoped work.

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

## Legacy compatibility and guard boundaries

Legacy candidate v1 and manifest 1.0/1.1 inspection remains supported. Legacy execution is limited to the original unique-year semantics: active consistent parent chain, matching target Generation and no correspondence catalogue for that model. Ambiguous or correspondence-aware scopes require candidate v2 and fresh manifest review. Missing historical snapshots are not invented.

`plan_generation_population` no longer creates Manufacturer, VehicleModel or Generation records. Missing parents appear as unresolved/rejected plans. Parent curation is a separate authorized operation.

Batch/bootstrap invocations preflight their full model/range/input fixture scope before mutation. They refuse overlapping or correspondence-catalogue scopes and explicit generation/v2 inputs. Correction refuses these scopes before deactivation. These bounded guards do **not** fix legacy batch re-planning, slug-only authorization, receipt suppression, or ordinary legacy correction semantics. Do not use those paths for this protocol.

Existing Toyota and Volkswagen baselines, navigation and unambiguous generation resolution are preserved. No transmission, package, Full Specifications or measurement changes are part of Milestone 1.

## Deployment and verification

Migration `reference/0006_generationcorrespondencerevision_and_receipt_resolution` is additive. It creates no correspondence or vehicle data and does not modify Generation ranges or VehicleDefinition identities. Apply it to development/production only after separate database-write authorization. Retained evidence publication/import requires separately reviewed data operations.

Tests use isolated databases and temporary media/raw storage. Synthetic JK/JL fixtures validate protocol behavior only and are not manufacturer evidence. Required checks include deterministic resolution, invalid scope/conflicts, v2 lineage and manifest integrity, stale state before create/no-op, concurrent successors, receipt rollback, auditable repeats, pre-write guards, zero-write planning, legacy parsing, and Toyota/Volkswagen regressions.
