# Import receipt evidence decoupling — compatibility investigation

Created: 2026-11-16
Status: Proposed compatibility design; implementation and cleanup not authorized

## Executive conclusion

A compact receipt can preserve the historical proof identity **if its reader
reconstructs the exact original logical snapshot from immutable retained evidence
before validation or hashing**. Keeping only the old digest is insufficient: it
cannot establish what was approved or reverify assertions. Do not hash the new
compact storage envelope as if it were the original evidence.

The smallest application boundary is a version-dispatched receipt snapshot reader,
plus retained-artifact byte access where deployment does not carry original files.
Keep current planning/execution evidence validation intact; compact only the durable
receipt representation after successful validation. No new database tables,
migrations, general evidence store or change to canonical matching is needed.

Existing execution manifests suffice for a first compatibility implementation on
the development checkout. They do not by themselves solve deployment storage or
availability. For the quota-constrained deployment, recommend a **bounded immutable
MY2021 verification artifact package**, using standard archive packaging and existing
JSON artifacts, rather than deploying the entire ignored handoff tree. Its exact
contents and read contract need owner approval. It must include the classification
dependency closure, not merely the 73 document arrays.

**Identity correction:** actual receipt **3135** is MY2021 **Unlimited Sahara**, VD
936, slug `2021-unlimited-sahara-36l-v6-4wd-us-mhev`. The request's Willys Sport slug
belongs to receipt **3094**. No identity was changed to match the request.

## A. Exact peer requirements

Current source references are repository-relative; line numbers identify the
inspected checkout.

| Reader | Fields and checks | Meaning |
|---|---|---|
| `reference/ingestion/importing/powertrain_identity.py:86–145`, `assess_peer` | Exactly one successful creation receipt; created PK/UUID/slug mirrors; generation; five baseline target fields; current canonical state | Checks the original recorded import **and** compatibility with today's record; this is not a historical replay independent of current state. |
| Same, lines 107–118 | Resolution parent Generation ID, year, market; complete documents; one document matching receipt source ID/raw hash | Historical scope and source binding. |
| `reference/ingestion/generation_correspondence.py:42–73`, `validate_documents` | Source ID, raw hash/reference, extractor ID/version/mode, assertion-set ID, nonempty assertions with local ID/key/raw value/context; uniqueness; source file existence/hash | Requires every supplied document to be structurally sound and every referenced artifact byte-identical. It does not parse the PDF again. |
| `reference/ingestion/classification_adjudication.py:195–206`, `validate_classification_documents` | Human source/extractor marker; exact declaration document; approved adjudication bytes and semantic hash; reviewer/decision, candidate scope, rationale, limitations, confidence, supporting assertion references | Loads `_base` at line 30 and `validate_classification_adjudication` at 59: original candidate, all base/supporting documents and approved projection must remain available. |
| `assess_peer`, lines 119–139 | Resolution 1.1 target tuple, Engine Proof 2.0 tuple, exact target projection; legacy path reads explicit five-field assertions | Direct proof of recorded values, followed by conflict check against current known values. No engine-name guessing or inference from missing hybrid terms. |
| `assess_peer`, lines 140–145 | Hashes whole snapshot and every complete document; records current row identity/activity/fields; hashes resulting projection | Even fields not interpreted are cryptographically significant. |
| `powertrain_identity.py:64–80`, `nonidentity_variation` | Engine layout from labels, horsepower/torque assertion values from old documents versus candidate | Prevents unsupported tuning/layout alternatives from becoming ordinary identity matches. |

`source_applicability`, publication revision, retrieval time and locator are not
all independently interpreted by `assess_peer`; they remain inside hashed documents.
`candidate_powertrain` at line 34 separately checks source market and qualified
interpretations, and classification validation checks exact candidate applicability.
`validate_documents` does **not** independently establish full year/body/trim
applicability from raw PDF text. That distinction must not be lost in the redesign.

For structured 1.1 peers, the tuple comes from recorded fields/proof rather than
re-extracting every table. Nevertheless, the current contract validates **all**
documents, hashes all document objects, and recursively verifies adjudication
lineage. A smaller evidentiary subset has not been certified equivalent. Complete
ordered recovery is safer and smaller in scope than redefining proof sufficiency.

## B. Independent preservation and field mapping

Scanned **1,527 retained MY2021 JSON files**. Across all 73 receipts, PK 3076–3148:

- All candidate hashes match retained candidate objects.
- All generation-resolution objects match retained **execution** manifest objects
  exactly under canonical JSON, including peer proofs from actual execution.
- All manifest hashes match execution manifests; recomputed all **73** hashes with
  the existing manifest hash function successfully.
- Every document matches an independently retained structured document object;
  **zero uniquely receipt-only documents** were found.
- 387 unique document objects total 2,334,503 canonical bytes. Document counts and
  adjudication contents differ by candidate; there is no universal 61-document set.
- All **105** direct raw references exist and match recorded byte hashes. Following
  raw-artifact and adjudication-base candidate references reaches **175 files**,
  58,281,276 bytes, with zero missing paths. Closure traversal is not a complete
  semantic validation of every approved candidate; that remains a prerequisite
  of implementation/cleanup verification.

Define `H = docs/implementation/handoffs/MY2021_JL/` and
`E = H/canonical_execution_20261109/resumed_20261109/attempts/matrix-2021-7ns4m4pv/`.
The ignored status of these files is not a durability/deployment guarantee.

| Required field for receipt 3135 | Current receipt | Independent artifact | Recoverability |
|---|---|---|---|
| Ordered documents; all source assertions and extraction metadata | `generation_resolution.documents` | `E/0059.manifest.json`, plan's generation resolution; same candidate documents in `E/0059.candidate.json` | Direct exact structured objects, no extraction rerun needed. |
| Qualified source ID/hash/reference, assertion IDs/keys/value/context | Each document | Same manifest/candidate; retained source assertion sets and source/excerpt inventories | Direct; PDFs independently byte-verified, not substitutes for transcriptions. |
| Exact approved human declaration | Human-classification document | `H/candidate_classification_20261109/classified_candidates/JL21-60.approved-r1.candidate.2.1.0.json`; declaration's `raw_artifact_reference` names adjudication JSON | Direct; its original base candidate and supporting documents are recursively required. |
| Tuple and peer proof | Resolution `fields`, `engine_distinction`; `target_fields_json` | Exact execution manifest plan, candidate canonical tuple | Direct. Snapshot planning manifests can differ from execution peer state; do not substitute them. |
| Generation/parent UUIDs and correspondence UUID/hash list | Resolution `parents`, `correspondences`, `generation_evidence` | Exact execution manifest resolution; separately retained publication reviews/revisions | Direct; current correspondence alone is insufficient. |
| Candidate digest | Root `candidate_hash` | Exact candidate digest `sha256:66a8a89331560071215c41ab6a88004b0091fad65f24ed6f2cd2ca0c1d6367c3` | Recomputed and matched. |
| Reviewed execution manifest | Receipt `manifest_hash` | `E/0059.manifest.json`, `sha256:bd53d2ffca973eb3cee874d4e5036727764d76d99d8c474dec51a9d1ed96768f` | Recomputed and matched. |
| Matrix row/approval | Root `matrix` | `E/matrix.json`, `E/approval.json`; final planning certification artifacts | Retained exact authorization artifact; approval binds Matrix digest `sha256:6926df6c06e4bd471bbda02c67257cf7a7e2999cf5cdfebfc8b06ead31a9996e`. |
| Receipt UUID, outcome, timestamps, target/FK mirrors and attribution | Columns plus root attribution/Matrix | Preserve existing columns and compact root metadata; original backup | Not supplied by PDFs; keep unchanged. |

Receipt 3135's 61 documents comprise 14 Sahara-family revision tables, 42 package
pages, four supporting evidence sets and one human declaration. They include
alternatives/context, not only positive proof of this engine. It represents the
recovery mechanism, not every candidate's exact evidence coverage. No required
structured field currently needs historical extraction code to regenerate: exact
candidate/execution artifacts exist. If they were absent, PDFs alone would not
establish recovery without reintroducing historical interpretation risk.

## C. Historical hash chain

`generation_correspondence.digest` at line 32 uses
`sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
separators=(',', ':'), allow_nan=False).encode())`, prefixed `sha256:`.
It includes the complete documents array and assertion text when hashing snapshots.
JSON object key order/whitespace are normalized; array order and values are not.
Historical proof comparison needs identical canonical JSON, not original SQLite
text spacing. Preserve original UTF-8 bytes separately for exact recovery/forensics.
Do not substitute MY2025's `default=str` digest helper: its serialization differs.

| Binding | Producer / durable destination |
|---|---|
| Complete snapshot digest, including documents, Matrix and attribution | `assess_peer`: `receipt_evidence_digest` in peer state |
| Full document digests in original order | `assess_peer`: `document_hashes` |
| Current canonical row state plus prior evidence bindings | `projection_digest` of peer state |
| List of peer states plus candidate tuple | `identity_proof`, line 149: Engine Proof 2.0 |
| Proof plus generation/candidate state | Planner resolution; review manifest; Matrix-authorized execution |
| New creation's resolution/proof | Persisted in next receipt; subsequently hashed as another peer |

Database traversal found **88 directed peer references**, in **49 later receipts**,
pointing to **49 MY2021 receipts**. All 88 recorded evidence digests match the
original complete snapshots. Maximum observed chain depth is **three edges**;
receipt 3136 directly references 3135. All observed sources are within the MY2021
receipt range (3077–3144); no cross-year database references to this set were found.
This does not rule out pinned external plans or future consumers.

Legacy `engine_distinction.py:68–86` hashes the resolution object rather than the
whole root; body-aware `_peer` in `body_identity.py:392` hashes the whole snapshot.
Compatibility must preserve each algorithm's original preimage, not merely one
new “evidence hash.” Stale current canonical premises must still reject old plans.
A hydrated historical snapshot preserves proof continuity **and** re-verifiability
only if all assertions/raw/classification dependencies are available and validated.
A retained hash with missing evidence supplies continuity of a label, not verification.

## D. Why future ordinary imports are oversized

`candidate/builder.py:246` → `normalization/generation.py:9` copies all supplied
assertion sets into documents. `importing/planner.py:546` passes them directly to
`resolve_generation`; `generation_correspondence.py:258` retains the entire list.
`importing/workflow.py:124–148` embeds the resolution in the receipt. Matrix execution
at `matrix_workflow.py:280–303` freshly plans each row and adds Matrix linkage before
commit. No candidate-specific reduction occurs at persistence.

The full approved evidence is needed under current validation during planning,
execution and subsequent peer assessment. It need not occupy every database row:
retain it independently and hydrate the identical logical object for existing
validators. Compact at the persistence boundary, not by weakening candidate validation.

ADR-0010 resolution protocol at lines 66–77 already permits `unique_year_range`
when no correspondence evidence is supplied. Supplied explicit evidence must still
be consistently resolved; it cannot be ignored just because a year is unambiguous.
Current v2 generation-aware evidence packaging is more pervasive than the overlap
use case. Storage decoupling should apply to both resolution bases, preserving
2018 JK/JL overlap restrictions and exact revisions. Changing which assertions a
new candidate supplies is a separate evidence-packaging decision, not necessary
for this storage correction. Do not route ordinary imports through legacy fallback
or require new correspondence publication merely to externalize evidence.

### MY2026 comparison

Receipt **3456**, `2026-sport-36l-v6-ess-4wd-us-2-door`, uses
`my2026-registry/2`; canonical snapshot size **7,579 bytes**. It retains source URLs,
extraction date, an observed source row and normalized target row, source engine
code, Engine/body/parent snapshots, row identity and approved plan hash. Its anchor
is `docs/research/MY2026_JL_edmunds_builder_20261114/inventory.json`.

`reference/my2026_wrangler_import.py:101` previews a bounded, hash-pinned inventory;
`execute` at 239 re-previews inside a transaction, validates exact approval hash,
then stores its profile-specific snapshot at 275. This is a **different registered
Engine/body workflow**, not the generic Candidate 2.1/Matrix writer with fewer PDFs.
`reference/engine_reconciliation.py:38` explicitly recognizes these profiles.
Generic `assess_peer` cannot consume it as a generation-resolution receipt.
It supplies useful audit information within its validated scope, but lacks the old
Engine Proof/qualified assertion/adjudication structure. It cannot simply replace
the general contract, including cases where names/codes do not uniquely establish
identity or source evidence is contradictory. Keep versioned semantics explicit.

## E. Alternatives

| Approach | Integrity/recovery | Changes, storage and risk |
|---|---|---|
| A. Existing execution artifacts + compact references | Exact generation resolution and candidate recoverable for all 73; retain root metadata and reconstruct original snapshot | Smallest reader change in development. Files must be pinned by byte hash and canonical content; do not depend on mutable latest indexes. Deploying whole manifests repeats much of the removed evidence; ignored handoffs are not a deployable contract. |
| B. Retain structured evidence once | Existing EvidenceDocument objects plus ordered membership preserve assertions/provenance; shared source files remain required | In-memory JSON layout using 387 documents and receipt→ordered hash lists: **2,618,828 bytes**. Existing non-document snapshot content: **986,541 canonical bytes**. These are payload experiments, not an approved new artifact schema. Classification-base/raw dependencies add significant storage; documents alone are insufficient. |
| C. Historical snapshot compatibility archive | Original full snapshot plus dependency closure preserves every historical hash preimage without rewriting proof chains | Minimal semantic risk; reader resolves immutable original snapshot, checks hash, then validates evidence normally. Compression is ordinary archive packaging, not a database compression framework. Needs a deployment artifact-byte reader if retained paths are not unpacked. Not by itself a full future import contract. |

Recommend **A+C for initial compatibility**, using already exact execution artifacts
in development, and a bounded verification package for deployment. Use B's
individual-document reuse only if later measurements justify extra artifact
projection/serialization code; whole-collection deduplication is not worthwhile.
All approaches can preserve exceptional overlap evidence. A/B can also externalize
future ordinary imports; C must not become an excuse to keep creating huge database
receipts and later cleaning them up.

### Proposed minimum compatibility contract

- Keep scalar columns, original Matrix link, candidate/manifest hashes, attribution,
  selected parent/scope and correspondence revision pins unchanged in compact form.
- Add explicit storage-version metadata in the existing JSONField, containing an
  immutable artifact reference, raw artifact hash, logical original-snapshot digest
  and deterministic member/object selector. Reject unsupported versions/extra fields.
  Exact key names/version require implementation review; this is not a new accepted wire contract.
- One reader returns the legacy logical snapshot for old embedded or new external
  storage. For compact historical receipts, reconstruct the entire original object
  and verify its original digest. Storage envelope metadata is **not** part of the
  old proof preimage. Never blindly trust a stored original digest without recovery.
- Route historical peer/layout/tuning/hash consumers through that reader, including
  `powertrain_identity.assess_peer/nonidentity_variation`, legacy `_existing_engine`,
  body-aware `_peer`, Matrix receipt comparisons and applicable audit/Admin tools.
  Preserve direct scalar/Matrix queries or update their explicit version handling.
- Continue source-byte/classification validations. Existing `validate_documents`
  file reads and `classification_adjudication.retained_path/_base` need a narrow
  retained-artifact byte access path when evidence lives in a package. Existing
  BASE_DIR confinement, exact hashes, approval validation and recursion restrictions remain.
- Fail closed for missing/corrupt package/member, changed bytes, unsafe paths,
  oversized decompression, duplicate identities or unresolved dependency closure.
  No network fallback or lookup through current correspondence/Engine state.
- Persist evidence durably **before** a transaction can commit a receipt reference;
  receipt/canonical atomicity remains. Failed transactions may leave an inert
  orphan artifact; they must never leave a live receipt pointing to unpersisted evidence.

## F. Storage and deployment consequences

Current 73 snapshots: **32,170,852 bytes / 30.68 MiB**. Removing only document arrays
leaves approximately **0.94 MiB canonical JSON**, before reference/version overhead;
roughly **29–30 MiB of payload** could leave SQLite. This is not a measured compacted
DB size. There is no promise of immediate physical shrink without compaction.

Direct referenced artifacts total 21,763,352 bytes, including 32 PDFs / 12,776,720
bytes. Current classification/raw-reference closure totals **55.58 MiB**, including
base candidates. Deploying that unpacked closure solely to save 29 MiB in SQLite
could **increase** total quota consumption.

Memory-only ZIP_DEFLATED level-9 experiment containing all 175 closure files plus
all 73 original snapshot UTF-8 payloads: **18,219,830 bytes / 17.38 MiB**. No archive
was added to the repository/deployment. This is a measured bounded packaging
experiment; approval/manifests and a signed-off index would add overhead, and a
production restoration rehearsal remains necessary. Approximate payload net saving
is **12 MiB**, not 29 MiB, if that package is newly deployed and no dependency copies
already exist there. Do not add snapshot-only compression savings to this estimate.
Do not unpack the full package on the same constrained filesystem and still claim
17.38 MiB storage. A stream/member byte reader or explicitly budgeted extraction
is required; original raw data remains original bytes, not reinterpreted text.

Without handoff files **or** an approved package reader and complete package,
PythonAnywhere historical verification would fail. An off-server backup alone
cannot support online historical verification. Owner must decide whether that
capability is required there; do not silently downgrade it.

Compact on a verified development copy after compatibility tests. A deployment
space check must budget the existing approximately 61.68 MiB DB, replacement DB,
verification package, journal/WAL and safety reserve, plus backups retained locally
or verifiably off-server under approved recovery policy. Actual available quota
has not been inspected. Do not run production VACUUM blindly. Transfer verified
replacement artifacts, stop/quiesce writers, recheck hashes and replace atomically
only under separate deployment authorization. Backup and restore-test the database
and evidence package together. Never overwrite later production changes with an
older development snapshot.

## Implementation sequence for approval

**Phase 1 — Compatibility, no cleanup:** implement the smallest versioned reader
and exact preimage recovery, with existing-file mode first. Inventory all reader/hash
sites above; implement bounded packaged-artifact byte access only if required by the
approved deployment contract. Verify all 73 original objects/hashes and the 88 proof
edges unchanged. Preserve current canonical-state stale detection. No DB migration.

**Phase 2 — Future receipts:** keep candidate/resolution evidence validation and
human approval unchanged. At `importing/workflow.py` receipt construction, persist a
hash-bound evidence artifact and compact reference; ensure Matrix annotation/hash
boundaries remain correct. No automatic generation-overlap bypass. Legacy and
profile-specific writers remain explicitly versioned. This phase can follow Phase 1
separately; Phase 1 alone does not prevent new large receipts.

**Phase 3 — MY2021 cleanup:** only after Phase 1 is deployed/tested and evidence
availability is proved on the target environment. Backup/export original bytes,
pin deterministic PK/UUID/old/new hashes, change only approved 73 JSON fields on a
clone first, and verify every unaffected column/table/receipt byte-for-byte. Compare
hydrated historical hashes, proof edges, source/adjudication checks and Matrix
completion semantics; reclaim storage only after integrity and recovery rehearsal.
Phase 2 is independently releasable and should precede cleanup operationally to
prevent recurrence; Phase 3 must never precede compatible readers.

Recommended tests: legacy unchanged read; exact original canonical and byte recovery;
all 73 snapshots and all 88 proof references including transitive chains; missing/
tampered artifact/base candidate/raw source/adjudication; old and compact peer
assessment parity; known canonical conflicts; tuning/layout guards; exact-match and
Matrix rerun behavior; unsupported versions; rollback on evidence/receipt failure;
BASE_DIR/path traversal/duplicate ZIP members and decompression limits; absent
handoff paths in a packaged-only deployment; preservation of publication receipts,
other years, all canonical fields and receipt scalar metadata. Test ordinary unique
Generation without forcing correspondence and actual JK/JL overlap without fallback.

## Decisions, limitations and verification

Approve the versioned logical-reader boundary, package versus existing-path deployment
policy, and any narrow qualification of RA-044's “historical payload bytes remain
untouched” rule before implementation. Preserve original bytes in an immutable
recoverable artifact; do not relabel new compact bytes as unchanged historical bytes.
ADR-0010 need not be modified. Artifact immutability/backup policy and online
historical verification are required decisions; a new general evidence subsystem
is not justified by this investigation.

44 focused generation projection/correspondence tests passed (isolated test DB);
Django system checks reported no issues. Temporary analysis only under `/tmp`;
archive experiments were in memory. Final before/after hashes confirm the live
DB and all pre-existing tracked/untracked working files unchanged. Sole repository
addition: this report. Existing DB difference and prior audit report preserved.
No application edits, receipt/canonical mutations, migrations, acquisition, staging,
commits, pushes, compaction or deployment. Stop for owner approval.
