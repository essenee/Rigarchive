# Canonical Import Contract Registry

Created: 2026-11-16
Last Updated: 2026-11-17
Status: Technical reference; protected Engine corrections implemented; local 0015/0016 applied; other recommendations remain proposed

## Protected identity corrections — 2026-11-17

A separately permissioned Admin/service operation can correct only an Engine variant
key with an actor-bound signed preview, fresh exact-state/uniqueness/dependency
checks and an atomic append-only audit (applied migration 0016). Ordinary identity
edits stay protected. See `reference/engine_identity_correction.py`.

This is not a canonical import contract/version or reusable assignment approval.
Legacy registry bindings and unknown Engine-referencing formats block incompatible
corrections; original source/approval/receipt bytes retain their meaning. Unused
registry observations do not authorize assignments, empty keys are not aliases, and
registry-sensitive pending plans require fresh review after a correction. No import
serializer or historical proof reader is weakened by this operation.

## Engine variant compatibility update — 2026-11-16

The owner-authorized Engine implementation adds migration
`reference.0015_engine_internal_variant_key`; it was **applied locally under separate
authorization on 2026-11-17**, after the isolated rehearsal. No wire version or historical artifact is changed.

- `Engine` identity is manufacturer / normalized full code / normalized immutable
  internal key. Empty means no explicit discriminator, never a preferred variant.
- `engine_registry.resolve_engine` distinguishes omitted/explicit empty/named keys.
  Omitted same-code ambiguity fails before five-field filtering. Exact PK/UUID pins
  are validated directly, including manufacturer, code, optional key and properties.
  Unpinned reconciliation cannot use names/partial properties to select shared codes.
- MY2025 `/1` and MY2026 `/1`,`/2` now use explicit historical model field projections
  in `my2025_wrangler_import.HISTORICAL_SNAPSHOT_FIELDS`, established from all six
  complete retained approvals. Original names, types, ordering, decimal/timestamp
  spellings and hash recipes are preserved. These profiles reject nonempty variants.
  MY2026 uses its approved exact Engine pins rather than re-resolving by code.
- Registry Body3.1 bindings retain their closed schema and hashes. Candidate readers
  validate exact Engine PK/UUID pins despite unrelated same-code rows. Existing
  five-field claims check that instance. Binding production/verification rejects a
  nonempty key; no new variant-aware import contract is introduced.
- Complete `.values()`/SQLite preservation comparisons remain exhaustive, including
  the new key. The original 507-row assignment approval is not extended or reused.
- Compact MY2021/MY2022 metadata enumeration and generic dataclass serialization are
  unchanged. Future receipt/dataclass schema compatibility work is **deferred**, not
  required by this Engine-only migration. New variant-bearing import authorization
  remains separately scoped. Horsepower/torque fields are not added.

Verification, preservation results and pending operations:
[implementation record](tasks/engine-internal-variant-key.md).

The following inventory and hash/usage census retain their original audit context.
Line references describe that inspection unless a changed symbol is identified here;
symbols are the stable lookup references. Historical recommendations below do not
supersede this implemented update or authorize additional changes.

## 1. Scope, authority and inventory method

No consolidated cross-workflow registry was located. Existing RA-011/012 serialization,
RA-024 manifests, RA-044 powertrain, RA-046 Candidate v3, RA-049 body import and local
`SCHEMAS` definitions cover separate boundaries; this index cross-references them
rather than replacing them. Code, retained bytes and read-only database usage are
authoritative for implemented state. This audit grants no new “frozen contract”
authority, schema/version change, data operation or execution authorization.

Authority references: accepted ADR-0006 (immutable acquisition), ADR-0007 (human
execution authorization/atomic receipts), ADR-0008 (adjudication), ADR-0010's existing
versioned correspondence boundary and ADR-0012's five-field identity; [ingestion
protocol](../development/INGESTION_PROTOCOL.md); [current state](CURRENT_STATE.md).
See [Engine variant readiness](../research/engine_internal_variant_key_implementation_readiness_20261116.md),
[receipt decoupling investigation](../research/import_receipt_evidence_decoupling_design_review_20261116.md)
and the linked implementation task records. No generation-overlap policy is reopened.

**Count convention:** **24 core contract families**, **32 named family/version
entries**, **19 distinct version/identity tokens**, and **six unversioned
families**. Related body/registry subcontracts sharing one envelope version are grouped
as families; this is not a count of every nested schema or dataclass. Extractor/plugin
versions and diagnostic schema markers are not counted as canonical wire versions.
Adjacent W2/specification and diagnostic contracts are described separately below.
Legacy major-1 validation permits more minor strings than these observed/documented
versions; that permissiveness is not evidence that another named contract was implemented.

Inspection covered source/tests, **5,276 retained JSON files** in
handoffs, research, source storage and fixtures, all **3,591** live receipt payloads,
and the MY2021/MY2022 original snapshot archives. File counts include drafts, copies
and fixtures; they are not execution counts. Historical-format presence, artifact
hash validity and permission to execute again are distinct facts.

| ID | Contract family | Implemented or historically recognized identifiers |
|---|---|---|
| F01 | Raw acquisition snapshot metadata | **Unversioned** |
| F02 | SourceAssertionSet | `1.0.0`, `1.1.0` |
| F03 | Normalized interpretations / extraction provenance | **Unversioned** |
| F04 | CandidateConfigurationDocument | `1.0.0`, `2.0.0`, `2.1.0`, `3.0.0` |
| F05 | Transient canonical plan / result | **Unversioned** |
| F06 | Generic review manifest / serialized review plan | `1.0`, `1.1`, `2.0`, `2.1` |
| F07 | CanonicalImportAdjudication | `1.0`, `1.1` |
| F08 | Generation correspondence review | `1.0` |
| F09 | Generation resolution | `1.0`, `1.1` |
| F10 | Engine distinction / structured proof | `1.0`, `2.0` |
| F11 | Generation Trim Matrix | `1.0`, `2.0`, `2.1` |
| F12 | Matrix approval | `1.0` |
| F13 | Body-aware import envelope family | `3.0.0` |
| F14 | Registry-aware body import envelope family | `3.1.0` |
| F15 | Generic ORM execution receipt | **Unversioned** |
| F16 | Population batch review manifest | **Unversioned** |
| F17 | Engine assignment preview | `engine-assignment-preview/1` |
| F18 | Engine assignment execution record | `engine-assignment-execution/1` |
| F19 | MY2025 registered import profile | `my2025-edmunds-registry/1` |
| F20 | MY2026 registered import profiles | `my2026-edmunds-registry/1`, `my2026-registry/2` |
| F21 | MY2021 compact revalidation | `my2021-approved-matrix-revalidation/1` |
| F22 | MY2022 compact revalidation | `my2022-approved-matrix-revalidation/1` |
| F23 | Body / baseline semantic preimages | `factory-body-semantic/2`, `vehicle-definition-body/2` |
| F24 | Complete current-state preservation baseline | **Unversioned** |

## 2. Serialization and hash recipes — do not interchange

All digests discussed here are SHA-256 with lowercase `sha256:` prefix unless stated.
Hash equality binds content, not operator authentication or human approval by itself.

| Recipe | Exact implementation / preimage |
|---|---|
| RAW | `ingestion/acquisition/snapshots.py:57`, `compute_content_hash`: original bytes, no JSON normalization. Artifact files and archived SQL JSON have separate raw hashes; preserve original whitespace/newlines for byte recovery. |
| LEGACY-ARTIFACT | `ingestion/serialization.py:771`, `serialize_artifact`: recursive sorted dict keys, `indent=2`, `ensure_ascii=False`, list order retained, no serializer-added trailing newline. Individual file writers may append one; raw file hash is not the semantic artifact digest. |
| C | `ingestion/generation_correspondence.py:32`, `digest`: `json.dumps(sort_keys=True, ensure_ascii=False, separators=(',', ':'), allow_nan=False).encode()`. Resolution/candidate evidence/proof and receipt bindings use specific complete objects under this recipe. |
| MANIFEST | `ingestion/manifest.py:78–90`: sorted compact UTF-8, ensure_ascii=False; historical helper does not explicitly set allow_nan=False. Hash entire manifest without `manifest_hash`, including created_at and all projected plans. Source validators still govern admissible inputs. |
| ADJUDICATION | `ingestion/serialization.py:823`: omit `adjudication_hash`, recursively sort objects, compact UTF-8/ensure_ascii=False; lists and nulls preserved. |
| MATRIX | `ingestion/matrix.py:189–220`: 1.0/2.0/2.1 canonical payload sorts rows by year/row ID, permitted bases, evidence and correspondence references before C-like JSON. 3.0.0/3.1.0 dispatch validates then hashes complete matrix without imposing the legacy sorting transformation. |
| APPROVAL | `ingestion/matrix_approval.py:90–96`: validated compact sorted UTF-8 plus **one LF**. Approval has no self-hash field. Raw approval-file hash, embedded `approval_hash` and Matrix digest are different preimages. |
| BODY | `body_identity.py:33`, `canonical_json`, and `ingestion/body_import_contracts.py:30–42`: strict finite JSON, sorted compact UTF-8. `content_hash` omits its named hash field. Semantic digests validate the identity preimage before hashing. |
| REGISTRY-BODY | `importing/registry_body_import.py:62–70`, `_hash`: BODY of `{registry_import_contract: '3.1.0/'+kind, payload: object_without_own_hash}` for Binding/Candidate/Plan/Manifest/Revalidation/Receipt. **Matrix itself uses the complete validated Matrix digest**, not that wrapper domain. |
| REGISTERED-PROFILE | `my2025_wrangler_import.py:35`, `digest`, also imported by MY2026: sorted compact JSON, `default=str`, default ensure_ascii=True; preview hash omits `plan_hash`. Non-null model snapshot values are already **strings**. Do not substitute C or DjangoJSONEncoder. |
| ASSIGNMENT | `engine_assignment.py:23` and `engine_reconciliation.py:204`: sorted JSON, default separators with spaces, default ensure_ascii=True, default=str. Preview hash omits `snapshot_digest`. Baseline first passes through DjangoJSONEncoder via `wire`; execution records bind before/after baseline digests. |
| POPULATION | `ingestion/manifest.py:531–553`: sorted JSON with default spaces/escaping; hashes selected scope/count fields and each item's ref/year/action/slug. Not a full plan or full-state approval hash. |
| COMPACT | `my2021_wrangler_revalidation.py:32–35`, reused by MY2022: C-like canonical JSON; `record_hash` omits itself. `original_execution.metadata_digest` hashes a **separate** receipt metadata projection; archived raw and historical canonical digests remain distinct. |

Timestamp differences are intentional existing wire behavior: generic manifests use
aware `isoformat()` strings; Approval1 requires canonical UTC `Z`; correspondence
reviews require canonical `+00:00`; registry bindings use `stamp` UTC `Z`; full-profile
snapshots use `str(datetime)` (space separator); compact metadata uses `isoformat()`.
Do not normalize historical timestamp spelling, omitted versus null/empty fields,
array ordering, numeric/boolean types, ASCII escaping or Decimal precision “for consistency.”

## 3. Family inventory: schemas, writers, readers and coupling

Paths below are relative to `reference/` unless a docs/storage path is given. Symbols
identify the authoritative field sets; this reference deliberately does not copy entire
nested schemas into a second executable specification.

### Evidence inputs — F01–F04

**F01 raw snapshots, unversioned:** `ingestion/acquisition/snapshots.py`,
`RawAcquisitionResult`, `RawSourceSnapshotMetadata`, `snapshot_metadata_to_dict/from_dict`,
`RawSnapshotManager.store_snapshot`. Sidecar fields: source_id, publisher_locator,
acquired_at, content_type, content_hash, storage_path, source_applicability,
acquisition_method, transport_metadata, plus preserved unknown fields. Writer uses
2-space sorted JSON with default ASCII escaping; RAW hashes source bytes, not sidecar
text. No Engine enumeration. Sidecar availability/provenance is not import permission.

**F02 SourceAssertionSet 1.0.0/1.1.0:** `ingestion/contracts.py`, `Envelope`,
`SourceMetadata`, `SourceAssertionSet`; `serialization.py`, source converters and
`deserialize_artifact`; `validation.py:27–83`. Root envelope/provenance/assertions/
configuration identities/unknowns; 1.1.0 production inputs include snapshot-bound
extraction provenance (artifact hash/reference, extractor ID/version/mode). Base
major-1 envelope validation and unknown-field retention are open for compatibility;
source-specific normalizers may demand exact 1.1.0. Generic serialization is
LEGACY-ARTIFACT; no universal SourceAssertionSet self-hash. Files are RAW-pinned by
consumers. NHTSA/EPA/manufacturer adapters emit 1.0.0; Toyota/J.D. Power/Jeep parsers,
profile extraction and Wikipedia can emit 1.1.0. Retained fixtures and actual Jeep
handoffs confirm both artifact shapes; presence alone does not prove canonical use.

**F03 embedded normalization/provenance, unversioned:** `NormalizedInterpretation`,
`TechnicalValue`, SourceApplicability and ExtractionProvenance in `contracts.py` /
explicit converters in `serialization.py`; normalizers under `normalization/`.
Qualified assertion reference, target attribute, normalized value/unit, mapping status,
raw value and notes retain source/interpretation separation. Plugins carry independent
extractor/normalizer IDs/versions; these are not Candidate/manifest versions. Some
normalization records are generated diagnostics, others are included in candidate
and approval preimages. No Django Engine enumeration. `normalization/generation.py:9–29`
uses `asdict(source_applicability)`, so dataclass evolution can still change document
hashes; this is distinct from a database schema addition.

**F04 CandidateConfigurationDocument:** `contracts.py`, `candidate/builder.py`,
`serialization.py`, `validation.py`; v3 in `candidate_v3.py`.

| Version | Shape / reader / historical status |
|---|---|
| 1.0.0 | Legacy envelope, caller identity, normalized interpretations/technical details, review/equipment and unknown fields. Major-1-compatible dataclass path; explicit fixture evidence. Canonical use in old population workflows is plausible, but old empty receipts do not prove exact envelope versions. |
| 2.0.0 | Adds qualified source identities, complete retained document collection and generation evidence; exact supported v2 dispatch. Retained MY2018 W1 candidates and 2.0 manifests exist in `storage/acquisition_inputs/jeep_2018/`; historical G1.0 receipts corroborate that workflow. |
| 2.1.0 | Adds canonical_powertrain with exact five controlled fields and canonical decimal strings. Generic v2 validation, candidate hash and execution bindings; confirmed retained MY2019–2023 artifacts. |
| 3.0.0 | Closed RA-046 wire: envelope/schema ID, canonical scope, existing/pending body/series references, qualified evidence/applicability, interpretations, review and self `candidate_hash`; duplicate-aware parser. `candidate_v3.candidate_hash` omits only its own field under BODY; serializer validates exact wire. Confirmed inside actual MY2024 Body3.1 receipts. |

Legacy candidates serialize as LEGACY-ARTIFACT but their generation-aware approval
hash is over the full candidate dictionary using C, **not that pretty JSON text**.
No candidate pulls all current Engine fields automatically. Existing `EngineDetails`
already supports technical horsepower/torque evidence; adding ORM columns does not
change that contract or make those values canonical identity dimensions.
`candidate/v3_foundations.py:43–71` has a 3.0.0 **identity projection checksum**, not a
complete Candidate v3 serializer/proof/authorization; do not interchange it with F04.

### Planning and execution authority — F05–F14

**F05 transient plan/result, unversioned:** `ingestion/importing/__init__.py`,
`CanonicalImportPlan`, `CanonicalImportResult`. Known enums, resolved IDs, target
fields, namespace/mechanical premises, existing ID, reasons/adjudication, optional
resolution/candidate snapshot/hash. Not durable ORM records or standalone approved
wire versions. Exact reviewed projections become F06. Do not infer a plan version
from a filename or dataclass name.

**F06 review manifests 1.0/1.1/2.0/2.1:** `ingestion/manifest.py`,
`CanonicalImportReviewPlan`, `build_review_manifest`, `manifest_to_dict`,
`dict_to_manifest`, `reconstruct_plan_from_review_plan`. Closed top-level fields:
manifest_version, created_at, source_id, raw_artifact_hash/reference,
extraction_provenance, plans, manifest_hash. Plan fields are the named review dataclass
fields at lines 31–59, projected differently by version: 1.0 omits adjudication;
1.1 includes it; 2.0 adds candidate snapshot/hash and resolution; 2.1 requires structured
2.1.0 candidate/1.1 resolution. MANIFEST hash. Strict reader supports these exact
version strings (its older error message listing only 1.0/1.1 is incomplete).
3.0.0/3.1.0 dispatch to F13/F14, not these dataclasses. `asdict` is a **dataclass-schema**
coupling risk even though Engine model fields are not enumerated here.

**F07 adjudication 1.0/1.1:** `contracts.py:CanonicalImportAdjudication`,
`serialization.py:823+`, `validation.py:245+`, `classification_adjudication.py`.
1.0 reviews bounded grade categories; 1.1 adds approved/proposed evidence-backed
classification decisions, candidate digest/reference, supporting documents, per-field
values/rationale/applicability/limitations/confidence and qualified references.
ADJUDICATION hash excludes only adjudication_hash. Legacy unknown preservation is
not permission for executable new fields; 1.1 rejects unknown contract fields.
1.1 actual handoff approvals verified by retained artifacts; 1.0 implementation/tests
exist, but completed execution usage was not established by this scan.

**F08 correspondence review 1.0:** `generation_correspondence.py:REVIEW_KEYS`,
`validate_review_payload`, `publish_correspondence`; model `review_payload()`.
Closed exact UUID/revision/scope/source/native identity, evidence, finding/reviewer/
review time/notes. C `content_hash`; append-only revisions and separate publication
receipts. 254 live publication receipts confirm use. No model Engine fields.

**F09 resolution 1.0/1.1:** `generation_correspondence.py:_resolve_generation`,
`revalidate_resolution`, `validate_bound_plan`; planner 546+. Versioned manually
validated dictionaries, not a universal independent closed serializer. Fields include
basis, parent identity/state, scope/year, target fields, qualified generation evidence,
documents, correspondence UUID/hash pins and target identity; planner adds F10.
1.1 binds all ten target fields. C on exact snapshots/subobjects; preserved live
state is checked separately. Implemented earlier overlap paths and historical ordinary
paths coexist; this inventory does not endorse expanding generation resolution.

**F10 Engine Proof 1.0/2.0:** `importing/engine_distinction.py`,
`powertrain_identity.py:identity_proof/assess_peer/revalidate_identity`.
1.0 uses sourced displacement/cylinders/layout and peer receipt bindings; 2.0 uses
complete canonical_powertrain, ordered peer identities/current five-field state,
receipt UUID/evidence digest, document hashes and projection digest. Manual
version/proof equality validation; C preimages. It is not an all-Engine-field snapshot.
Compact MY2021/MY2022 readers now bind the new compact basis, never recreate original
historical hashes; original 154 combined proof references remain in their archives.

**F11 Matrix 1.0/2.0/2.1:** `ingestion/matrix.py`, `validate_matrix`,
`canonical_matrix_payload`, `compute_matrix_digest`. Closed parents/market/year/rows;
row action, candidate reference/digest, source/correspondence refs, allowed creation
bases and exact target identities. 2.0 adds generation binding; 2.1 uses ten fields
and semantic tuple uniqueness. MATRIX recipe; no generic model field enumeration.
W1 current receipt links confirm 2.0; actual MY2019–2023 executions use 2.1. 1.0 is
implemented/tested; actual completed use was not established here. Body/registry
3.x Matrix dispatch is described in F13/F14.

**F12 Approval1:** `matrix_approval.py`, exact five keys approval_version,
matrix_digest, decision, operator, approved_at_utc. Validates immutable scope and
explicit affirmative approval evidence, not authentication. APPROVAL serialization;
no universal self-hash. Reused in body/registry manifests, where approval_hash hashes
the object separately. Confirmed in retained ordinary and body-aware executions.

**F13 body-aware 3.0.0 family:** `body_import_contracts.py:SCHEMAS` (146–179),
`importing/body_identity.py`, `body_import.py`. Closed explicit `Proof3`, `Plan3`,
`Assessment3`, `Matrix3`, `Manifest3`, `Revalidation3`, `Receipt3`; scope profile
`my2024-wrangler-jl-consumer/1`. Parent/body/evidence/correspondence/family/peer state,
full target tuple, exact actions and hash bindings. BODY hashing excludes each named
self-hash; Matrix full digest plus embedded Approval1. Explicit projections and
array ordering, not `_meta` serialization. **3.0 inner plans/proofs are confirmed in
31 actual 3.1 receipts; standalone 3.0 receipt persistence is not confirmed.**

**F14 registry-aware 3.1.0 family:** `importing/registry_body_import.py:VERSION/LOCAL`,
`engine_binding`, `prepare_registry_candidate`, `RegistryRelease`, `execute` /
`receipt_snapshot`. Adds closed Binding, wrapped Candidate, registry Plan/Matrix/
Manifest/Revalidation/Receipt around unchanged body components. Binding keys exactly
manufacturer {pk,uuid}, engine {pk,uuid}, engine_code, name, properties, updated_at,
state_hash. Registry plans bind complete family and peer Engine UUIDs; Matrix rows
bind plan/state hashes and Engine UUID. REGISTRY-BODY domains; no automatic Engine
field enumeration. Confirmed all 31 MY2024 canonical import receipts. Present loaders
still re-resolve pinned Engines by code; variant-safe exact-reference handling needs
separate approval/implementation.

### Receipts, operational profiles and preservation — F15–F24

**F15 generic ORM receipt, unversioned:** `models.py:ImportExecutionReceipt`,
`importing/workflow.py:_build_and_save_receipt`, migrations 0002/0003/0006.
Columns preserve execution/outcome/attribution, reviewed manifest/candidate/source
anchors, target fields, canonical PK/UUID/slug mirrors/FKs. JSONField has no universal
schema/version; different writers use F09, F14, F19–F22 or legacy empty JSON. Generic
workflow embeds attribution plus exact resolution/candidate hash; Matrix adds row
linkage inside the transaction. Admin exposes records; specialized readers dispatch
by their own format. An empty JSON payload is **not** proof of Manifest 1.0.

**F16 population batch manifest, unversioned:** `manifest.py:PopulationBatchManifest`
and `management/commands/plan_generation_population.py:112` (`asdict` output).
Scope/year/count/items summary and batch_manifest_hash. POPULATION hash omits batch_id,
created_at, review_count and item trim/engine/drivetrain/create_basis despite their
presence in serialized output. Not equivalent to exact canonical import authorization;
source code/tests show intended coarse review use. Do not infer exact historical
manifest version/approval merely from legacy Toyota receipt counts.

**F17 assignment preview /1:** `engine_reconciliation.py:_engine`,
`preview_engine_assignments`; command `preview_engine_assignments`.
Version-tagged manual dictionary: registry list, rows, groups/patterns/exceptions,
totals and snapshot_digest. ASSIGNMENT hash omits snapshot_digest; source timestamp
format and list ordering matter. `_engine` is an explicit projection and already
includes `internal_variant_key=getattr(...,'')`; the ORM now defines the field.
Retained original preview at `docs/research/engine_registry_reconciliation_20261115/assignment_preview.json`
anchors approved 507 assignments. Does not automatically authorize new matches.

**F18 assignment execution /1:** `engine_assignment.py:validate_assignments/execute_assignments`;
command `assign_registered_engines`. Manual version-tagged audit record with original
approval digest, counts, changes, before/after state digests and preservation flags.
Retained execution/rerun artifacts confirm 507 then zero assignments. Not another
ImportExecutionReceipt row format; do not add 507 to the SQL receipt inventory.
Approval digest remains `sha256:7ab06c7f7afa590ff7bcd4172e196b5e4b19e596305987467c76ed2b3676bbb8`.

**F19 MY2025 profile /1:** `my2025_wrangler_import.py:VERSION`, `snapshot`, `preview`,
`execute`. Manual version-tagged preview with version, source_sha256, extraction_date,
parents, engines, bodies, namespace, rows, counts, plan_hash; exact source inventory
hash and human-authorized plan digest. REGISTERED-PROFILE hashing. Receipt keeps row,
source URLs, parent/Engine/body snapshots and plan hash, not full preview namespace.
Source inputs are file-pinned, but these dictionaries are not the closed 3.x schema
checker. Explicit historical field projections now affect authorization and stale checks;
future ORM fields are excluded. Nonempty Engine variants are unsupported by this format.
Confirmed 31 creates and 31 no-ops.

**F20 MY2026 profiles /1 and /2:** `my2026_wrangler_import.py` imports F19's snapshot
and digest helpers. Historical `my2026-edmunds-registry/1` has the earlier preview
shape; current `my2026-registry/2` adds supplement_sha256/source_artifacts and bounded
owner-confirmed supplement. Exact PK/UUID pins are also checked in current inventory.
Both historical versions are recognized by Engine reconciliation; **current writer
emits /2, not /1**. Different scope/authority is not a serializer alias. Closed
Candidate/manifest generic version dispatch must not be assumed for these profiles.

**F21/F22 MY2021/MY2022 compact /1:** separately pinned services
`my2021_wrangler_revalidation.py` and `my2022_wrangler_revalidation.py`.
Top-level exact keys version, original_execution, revalidation, evidence,
nonidentity_claim_hashes, record_hash. COMPACT hashes actual current agreement and
original metadata projection; historical raw/canonical snapshot hashes and archive
member/hash remain identifiers of archived evidence, not operationally reconstructed
proofs. Current inspector authenticates retained Matrix/approval and existing canonical
identity, without original corpus/archive. 73 +55 live records confirmed. Identity
contains Engine PK/UUID and five properties, not new unrelated Engine columns.

**F23 semantic identity preimages:** `body_identity.py:BODY_CONTRACT/BASELINE_CONTRACT`,
`body_preimage`, `baseline_preimage`, `semantic_digest`. Closed explicit scope/body
dimensions and baseline year/trim/drive/market/five-field/body/series references;
BODY recipe. Neither Engine UUID nor variant key is part of these existing semantic
preimages. Used inside actual MY2024 body-aware and MY2025/MY2026 profiles. Not a
license to create canonical variants merely because an Engine record differs.

**F24 complete current-state baseline, unversioned:** `engine_assignment.py:20–30`,
`wire`, `canonical_state`. Every live VehicleDefinition and Engine concrete field
via ordered `.values()`; DjangoJSONEncoder materialization, then ASSIGNMENT digest.
Purpose is preservation/current-state drift, not historical wire replay. Additional
columns **must** appear in fresh baselines. Archived prior baselines are historical
observations, not schemas to impose on current database checks.

## 4. Confirmed historical usage and recoverability

Read-only SQL observation: **3,591 receipts**, database **25,890,816 bytes**,
SHA-256 `sha256:b6963c139288cbfe0e564ab2bfe2b01ee01a09d19af8de4004e3bdf94c9c6d6a`. Integrity `ok`, no FK violations.
The existing working DB differs from Git before this audit; no changes were discarded.
Counts classify actual JSON, not model-year assumptions:

| Persisted format | Scope / count / outcomes | Available preimages and current interpretation |
|---|---|---|
| Unversioned empty JSON | 2,753 Toyota Tacoma/4Runner and VW Touareg receipts; 605 created, 2,040 no-op, 108 stale | Scalar provenance remains; no payload version. Exact original review manifests were not located/matched for all rows. Existing generic model can inspect them, but old execution-version attribution is **unknown**, not inferred 1.0. |
| Correspondence review 1.0 | 254 Jeep publication receipts, created | Complete review payload/content_hash retained and separately persisted revisions. Current review validator exists; replay also depends on original source bytes and revision state. |
| Resolution 1.0 | 95 Jeep creation receipts, JK 2007–2018 and JL 2018 | Current legacy resolution/proof code retained; W1 storage contains actual Candidate2.0/Manifest2.0. This does not authenticate every old approval or authorize replay against changed state. |
| Resolution 1.1, still live | 132 creates: MY2019 19, MY2020 49, MY2023 64 | Actual Candidate2.1/Manifest2.1/Matrix2.1 handoffs retained; content hashes/source pins available. |
| Original Resolution1.1, archived | MY2021 73; MY2022 55 | Lossless archives/manifests verified: 128 original snapshot raw hashes. Originals no longer count as live G1.1 JSON; current compact readers intentionally do not translate old proof hashes. |
| MY2021 compact /1 | 73 creates, PK3076–3148 | Retained exact Matrix/approval and current compact integrity/profile reader; original 88 proof edges offline. |
| MY2022 compact /1 | 55 creates, PK3221–3275 | Same bounded procedure with separate MY2022 basis; original 66 proof edges offline. |
| Body receipt 3.1.0 | 31 MY2024 creates, PK3363–3393 | Actual 3.1 Matrix/manifest/approval in RA056/RA057 handoffs and full receipt envelopes. Inner body plan/proof3.0 and Candidate3.0 confirmed. Current closed parsers exist. |
| MY2025 registered /1 | 62: 31 creates +31 no-ops | Two distinct approved plan hashes. Both full preview preimages retained and recomputed successfully. |
| MY2026 registered /1 | 66: 33 creates +33 no-ops | Two distinct approved preview preimages retained/recomputed. Current runtime recognizes receipts, but no /1 preview writer dispatch remains. |
| MY2026 registry /2 | 70: 2 creates +68 no-ops | Two distinct approved preview preimages retained/recomputed, including supplement scope. Current writer /2. |

Artifact pointers:

- `storage/acquisition_inputs/jeep_2018/w1_20261104T163312Z/jl_candidate_v2.json`;
  `w1_published_20261104T180404Z/{jk,jl}_canonical_import_manifest.json`.
- `docs/implementation/handoffs/MY2019_JL/director_review/canonical_execution_20261108/`;
  MY2020 `canonical_execution_20261108/`; MY2023 `canonical_import_execution_20261112/`.
- `docs/research/my2021_snapshot_archival_revalidation_20261116T191303Z/archive_manifest.json`;
  `my2022_snapshot_revalidation_20261116T215017Z/archive_manifest.json`; their ZIPs are
  retained under ignored `backups/review/`. Raw members reverified without rewriting.
- `docs/implementation/handoffs/RA056_wrangler_jl_my2024_approval/data/matrix.3.1.0.json`;
  `RA057_wrangler_jl_my2024_publication/data/execution_manifest.3.1.0.json`.
- `docs/research/MY2025_JL_edmunds_builder_20261114/`: original and rerun preview JSON;
  MY2026 equivalent plus `america250_incremental_preview_20261114.json` and
  `america250_rerun_preview_20261114.json`.

All **six** distinct MY2025/MY2026 approved preview digests were matched to complete
retained preview files and rehashed with the original recipe. Current source inventory
bytes match original pinned inventory SHA values for both years. Execution summaries
also carry plan_hash but are **not** the complete preview preimage; hashing those
summary objects as plans correctly does not reproduce the approval digest.

Implemented-but-not-confirmed completed execution: Manifest1.0/1.1, adjudication1.0,
Matrix1.0 and standalone BodyReceipt3.0. Source1.0/Candidate1.0 are confirmed in
fixtures, not automatically proven historical by empty receipts. Proposed artifacts
can look versioned: MY2023 `final_adjudication_review_20261112/proposed_import_manifest.json`
says `manifest_version: "2.1.0"`; generic readers accept **"2.1", not "2.1.0"**.
That unapproved draft is not a new implemented manifest version. Research
`schema_version: "1.0"` review/inventory files likewise are not SourceAssertionSet
wire envelopes. Proposed registry3.2, Engine variant keys and future output columns
are not implemented contracts and are not counted here.

## 5. Automatic-field coupling inventory

| Exact path / symbol / lines | Purpose | Consequence and treatment |
|---|---|---|
| `my2025_wrangler_import.py:46–49`, `snapshot(obj)` | Approval preview / live revalidation; called for parents, Engines, bodies and namespace | Original implementation enumerated `_meta.concrete_fields`; now uses the explicit historical projection. Historical key=`attname`, non-null=`str(value)`, null=None. New columns no longer expand the authorization preimage. Nonempty variants reject. Retained original preimages remain the source for old hash verification. |
| `my2026_wrangler_import.py:20,230–234`, imported `snapshot` | Same, /1 historical and /2 current | Shares the explicit projection, not an independent serializer. All six historical model shapes are covered; exact inventory pins are retained. |
| `engine_assignment.py:27–30`, `canonical_state` | Complete preservation baseline and execution before/after digests | Bare QuerySet `.values()` includes new Engine/vehicle columns. **Intentionally keep exhaustive**. Do not change this to an authorization projection to make old hashes equal. |
| `my2021_wrangler_revalidation.py:85–98`, `metadata(receipt)` | Historical metadata integrity preimage in compact records | Enumerates **receipt** `_meta.concrete_fields` except resolution_snapshot_json. New receipt column changes metadata_digest even if default null. Not coupled to Engine additions. Freeze an explicit original metadata field projection per compact version **only after approval**; keep separate full-table preservation checks. |
| `my2022_wrangler_revalidation.py:14–16`, imported `metadata` | Same for MY2022 | Shares the same risk; all 128 current compact records need regression protection for future receipt schema additions. |
| `models.py:758`, `VehicleDefinition.save` | Effective-object partial-save validation | `_meta.concrete_fields` copies only requested fields for validation. **Not a serializer/hash preimage**; preserve complete validation, no freeze. |
| `core/models.py:77`, `HomepageVehiclePlatform.save` | Same effective partial-save protection | Not Engine serialization/import authorization; no change proposed. |
| `reference/admin.py:23`, correspondence `readonly_fields` | Admin readonly coverage via `_meta.fields` | Presentation/permissions, not approval snapshot. No Engine coupling, no change proposed. |
| `ingestion/manifest.py:147,196`, `asdict(review_plan/manifest)` | Versioned authorization payload | Adding review dataclass fields can change old output; replace only authorization serialization with explicit per-version projection under approved compatibility work. Not a Django Engine field enumerator. |
| `ingestion/normalization/generation.py:25`, `asdict(source_applicability)` | Hashed candidate evidence document | Dataclass additions affect generated evidence; do not regenerate historical documents to discover their original hash. Source-applicability version projection may need separate preservation tests. |
| `ingestion/orchestration/manufacturer.py:203`, `asdict(extraction_provenance)` | Dry-run evidence/report projected into acquisition manifests | Dataclass-schema coupling, not direct Engine enumeration. Existing source artifacts must remain exact inputs. |
| `management/commands/plan_generation_population.py:112`, `asdict(batch)` | Review summary output | Output may grow with dataclass fields while POPULATION hash still covers only its explicit subset. Do not assume displayed extra fields were part of approval preimage. |

Search found no application Engine `model_to_dict`/generic Django model serializer
path beyond these relevant enumerators. Dict `.values()` loops and lock QuerySet
iterations (e.g. `select_for_update().filter(...)`) are not field enumeration.
`engine_reconciliation._engine` and registry `engine_binding` are explicit field
projections, not all-field serialization. Raw SQL full-table exports/comparisons in
maintenance scripts are preservation/recovery artifacts, not new import wire contracts.
`ingestion/attribution_rehearsal.py` is an explicitly scoped diagnostic/rehearsal utility
with serialized receipt edits/crosswalks; it is not an authorization serializer to run
as part of Engine evolution. No such utility was executed here.

### Concrete frozen-shape candidates for future approval

Observed Engine full-profile field set in actual MY2025/MY2026 preview preimages:
`id, uuid, created_at, updated_at, manufacturer_id, engine_code, name,
engine_displacement_liters, engine_cylinders, engine_aspiration, fuel_type,
electrification_type`.

Example historical types: id=`"1"`, manufacturer_id=`"20"`, cylinders=`"6"`,
liters=`"3.60"`, timestamp=`"2026-11-14 16:14:39.903598+00:00"`. These are **not**
Binding3.1 types (integer PK, canonical liters string, `Z` timestamp). Preserve them.
The same function also enumerates Manufacturer (8 fields), VehicleModel (8),
Generation (12), FactoryBodyConfiguration (13) and nonempty namespace vehicles.
Use each profile's retained concrete preview to enumerate those historical lists;
do not restrict a proposed fix to the Engine subobject and leave another automatic path.

Current compact receipt metadata comprises the 38 ORM receipt fields minus JSON
snapshot: identity/timestamps/channel/operator, manifest/candidate/action/basis,
source anchors, target scope/fields/outcome/messages, created/existing PK/UUID/slug
mirrors/FKs, adjudication hash, operation_type and correspondence FK. Preserve existing
`isoformat` datetime, UUID-string, integer-FK, dict/null/blank handling; do not copy the
all-string profile serializer onto this different digest. Fresh maintenance baselines
must still inspect all 38 and any new fields.

## 6. Future Engine field effects

| Path | Add empty internal_variant_key / null horsepower, torque or other columns | Genuine later semantic change |
|---|---|---|
| MY2025/MY2026 historical projections | New ORM keys no longer change authorization shape; original stored JSON/hash remains unchanged. Nonempty variants reject | Editing tracked properties or source applicability may legitimately stale plans; variant selection needs exact identity and approved evidence. |
| Explicit 3.1 Binding | No new key automatically serialized; old content hash unaffected by schema addition alone | New explicit variant dimension needs reviewed versioned binding content, not appended closed 3.1 fields. Code-only ambiguity must fail closed; exact PK/UUID pins remain authoritative. |
| Reconciliation preview | Already emits variant key `""` through getattr, so initial empty field adds no projected key | Nonempty keys/new records change approval scope; five-field compatibility remains separate. |
| Full preservation baseline | New fields intentionally appear and change a **new current-state** digest | Every new field continues to be checked; old observation digests are not regenerated to hide schema changes. |
| Compact MY2021/MY2022 | No Engine-field enumeration: new key/output fields alone do not enter stored identity | Current relevant properties/PK/UUID/canonical drift still reject. Receipt-column evolution is the separate metadata risk above. |
| Legacy candidates/resolution/Engine Proof/body semantic preimages | No automatic Engine-column append; controlled FIELDS tuple and explicit evidence remain unchanged | Do not append horsepower/torque to FIELDS, create variants from output alone, or alter VehicleDefinition identity as an incidental model change. |

Default-empty/null schema additions must not save existing Engines merely to populate
the new field: avoid changing updated_at/UUIDs/FKs. Later human edits to any Engine
field can update **updated_at**, which existing bindings/previews already include.
Even with stable field projections such an actual state change may correctly stale an
old plan. Do not backdate timestamps or substitute old live values to manufacture replay.
Engine output versus combined hybrid-system output and units/application need their
own approved specification rules; this audit does not settle their ownership or identity.

## 7. Compatibility Risks and Recommended Corrections

**Original audit recommendations; items 2 (MY2025/MY2026 projections) and 5 now have
the bounded implementation above. Remaining corrections are deferred proposals:**

1. **Separate artifact verification from live execution.** Verify original hashes
   from retained original payloads/archives and their exact historical algorithms,
   not reserialization of today's Django objects. Executing an old plan additionally
   requires current authorization scope, uniqueness, pins and stale-state checks.
   Valid historical content is not perpetual execution permission.
2. **Use explicit immutable per-version projections at authorization boundaries.**
   Implemented for MY2025/MY2026 using reviewed model-and-version field lists
   reproducing existing golden preimages, with original value conversions and hash
   options preserved. Still deferred: address review-dataclass `asdict` and compact
   receipt metadata projection separately; do not invent one universal serializer.
3. **Keep live preservation exhaustive.** Retain all-field `.values()`/raw table
   comparisons for current-state preservation. New columns must not disappear from
   before/after checks simply because old approval formats ignore them.
4. **New approved information needs an explicit version decision.** A variant-bearing
   registry Binding/plan should not silently use 3.1.0's unchanged closed field set.
   New output columns unrelated to an old approval need not change its wire; if new
   output is itself approved/bound, version the affected projection/profile. Do not
   rename hash domains or add implicit defaults to old artifacts by audit fiat.
5. **Resolve ambiguity without abandoning exact pins.** Implement the requested
   composite resolver in the owner-approved bounded scope: uniqueness-dependent
   code-only `.first()` is removed, omission differs from explicit empty, and ambiguous
   codes fail closed. Already
   approved PK/UUID references must not be redirected through arbitrary code lookup.
6. **Golden regression protection before schema work.** Pin all six observed registered
   profile preimages, old Binding3.1 samples, compact record metadata examples, legacy
   Manifest/Candidate examples and archived original receipt digests. Test a new Engine
   and a new receipt field separately: old authorization bytes/hashes stable under
   the chosen policy, current full baseline includes the new field. Cover null/blank,
   decimal/time/escaping/list order, unknown/version rejection and correct stale cases.
   Do not run or implement these tests in this audit.
7. **Unversioned formats need explicit handling, not invented history.** Raw sidecars,
   normalization components, transient plans, generic receipt JSON, population summaries
   and full-state baselines should be documented by purpose. If future semantics require
   a new versioned interface, introduce it prospectively with approval. Old empty receipts
   remain historically underdetermined; do not fill in a version from model year.

The owner has now approved explicit historical projections and strict ambiguity
handling for the bounded Engine implementation above. Remaining owner decisions:
future variant-bearing binding/profile versions and their authoring scope, ownership
of new output specifications, and metadata-version handling for future receipt columns.
Existing explicit approval, full authentic code rules, five-field snapshot semantics
and canonical identity preservation are already established—not reopened decisions.

## 8. Adjacent contracts and original audit verification limits

`reference/specifications/` implements separate W2 enrichment/catalogue/publication
contracts (e.g. artifact `rigarchive.full_specifications_enrichment.v1` and publication
manifest `.v1`, schema1.0.0, predicate1.0). `canonical.py` rejects floats/non-JSON values
and hashes compact sorted UTF-8; publication uses its own models/receipts rather than
ImportExecutionReceipt. They are adjacent evidence/enrichment contracts, not canonical
VehicleDefinition import authorization. The live database contains zero specification publication receipts, so it does not
confirm publication use; this inventory does not import W2 into the Engine plan.
Design documents for later body/series/profile capabilities and proposed registry3.2
remain proposed where no corresponding implementation/usage was located.

Historical hash verification performed without writes: all six registered profile
preview digests and source inventory pins; 128 original archived snapshot raw hashes;
read-only receipt-format census and source/test/artifact inspection. A prior audit
verified MY2021/MY2022 approved bases and all MY2022 execution manifests; this audit
does not claim to re-execute every historical validator or every earlier approval.
Implemented validators are not proof that retained raw sources remain available for
all legacy rows. Inspection/replay capability must be assessed per actual artifact.

The original registry audit (before the separately authorized implementation update
above) ran no tests, migrations, import execution, artifact regeneration, compaction,
Engine creation, code/test modification, governance change, staging, commits or deployment.
Only this registry document is added. All baseline non-database files are byte-for-byte
unchanged, including the untracked Engine readiness report. The live database hash
changed during the audit: the initial file baseline was
`sha256:b6963c139288cbfe0e564ab2bfe2b01ee01a09d19af8de4004e3bdf94c9c6d6a`;
the final observation was
`sha256:14974ac34f1bf33351bdb9795dfbc6ee5a6d23a1387de709b7cbccec24b161b9`.
All audit database connections used SQLite `mode=ro`; no database writes were
performed by this audit. The cause of concurrent change was not investigated.
Final read-only checks found 3,591 receipts, 1,150 VehicleDefinitions, SQLite integrity
`ok`, and zero foreign-key violations. Byte-for-byte database preservation therefore
cannot be certified, despite the audit itself being read-only. This registry is a technical index
for review; proposed compatibility corrections await separate approval.
