# MY2021 canonical Matrix revalidation and isolated snapshot replacement

Created: 2026-11-16
Status: Implemented and verified on isolated copy only; live cleanup awaits authorization

## Results

Profile: `my2021-approved-matrix-revalidation/1`.
**73 EXACT_AGREEMENT; 0 NORMALIZED_AGREEMENT; 0 DISAGREEMENT;
0 INSUFFICIENT_EVIDENCE; 0 EVALUATION_BLOCKED.** All 73 identify the same existing
VehicleDefinition, without proposing any additional or replacement record.
Eligible receipt PKs: **3076–3148**, selected by actual operation/outcome, MY2021,
fixed target/current Generation 32, canonical Jeep/Wrangler hierarchy and creation FK.

The new evaluator actually ran; this is not a relabeling of the earlier comparison
report. It authenticates the exact approved Matrix and approval, verifies receipt
association/candidate digest, compares the ten canonical fields, unchanged
manufacturer/model/Generation PK/UUID/slug, exact canonical slug, current authored
Engine tuple/manufacturer and fixed body parent where present, and blocks duplicate
canonical five-field identities or creation receipts. Generation is a fixed field;
no generation resolver, correspondence publication, alternative selection or
historical peer proof is invoked by the evaluator. Existing `decimal_string` and
`record_powertrain` handle DecimalField wire precision without a new identity rule.
Current Engine/body FK UUIDs are pinned in the result, not inferred or assigned.
The historical Matrix does not assert a new body association or Engine FK.

Authority remains the **manufacturer-based approved Matrix with Edmunds
corroboration**. No observation is relabeled Edmunds-derived. No acquisition,
extraction, adjudication, canonical import or historical reconstruction was run.

## Implementation and artifacts

- `reference/my2021_wrangler_revalidation.py`: bounded read-only service, authenticated
  basis loading, deterministic evaluation, retained evidence hash checks, compact
  construction/inspection, and archival-edge classification. No database-write API.
- `reference/ingestion/importing/powertrain_identity.py`: two early MY2021-version-only
  branches for current compact peer inspection and nonidentity tuning guards.
  Other profiles and existing legacy logic are untouched. Current proof hashes bind
  the compact current basis, never pretend to reproduce an original snapshot hash.
- `reference/tests/test_my2021_wrangler_revalidation.py`: focused regression coverage.
- `docs/research/my2021_revalidation_basis_20261116/matrix.json` and `approval.json`:
  byte-identical durable copies of the existing approved artifacts, not a new approval.
  Existing Matrix/approval validators are reused strictly as artifact/hash validators;
  no generation-overlap operation is invoked or tested.

`revalidation_results.json` contains all 73 new 2026 results, field comparisons,
canonical identities, candidate digests, exact Matrix row/digest, version,
evaluation timestamp, code revision plus service-source hash, and evidence refs.
`proposed_compact_records.json` contains all proposed replacements;
`receipt_3135_example.json` is the Unlimited Sahara example (Willys Sport is 3094).

Every candidate's full content hash and evidence-document projections match the
approved Matrix row. Execution-manifest hashes were verified and every referenced
raw source hash matched retained bytes before replacement construction. This checks
retained approved inputs; it does not rerun historical adjudication or claim a new
raw-source interpretation. The current compact inspector later verifies approved
Matrix agreement, not the full old source proof.

Matrix digest: `sha256:6926df6c06e4bd471bbda02c67257cf7a7e2999cf5cdfebfc8b06ead31a9996e`.
The service pins both exact Matrix bytes and existing approval bytes, validates the
existing approval scope and recomputes the Matrix digest. The compact record's
`record_hash` detects content corruption; it is not an authentication signature.

## Compact structure and provenance

The existing `resolution_snapshot_json` can store a clearly versioned **new
revalidation**; original execution columns remain untouched. Top-level keys:

- `version`: bounded MY2021 profile.
- `original_execution`: all-column metadata digest, original candidate hash, original
  Matrix linkage and attribution, original snapshot byte/canonical hashes and archive
  member/hash. Archive identifiers are offline audit metadata, not runtime dependencies.
- `revalidation`: new timestamp/revision/profile/outcome, fixed canonical identity,
  approved Matrix row/digest, candidate hash, normalization and issues.
- `evidence`: compact references/hashes for Matrix, approval, candidate, execution
  manifest and deduplicated source-artifact references. No source assertions embedded.
- `nonidentity_claim_hashes`: empty horsepower/torque claim sets in this fixed
  approved scope; verified from the candidates. No new tuning evidence is invented.
- `record_hash`: canonical SHA-256 of all other compact fields.

No PDFs, document/assertion collections, full candidates, full Matrix or historical
resolution objects are embedded in replacement JSON. Detailed field comparisons
are in the separate revalidation report. The original import is not retrospectively
authorized or dated by the 2026 evaluation. All original receipt columns, outcome,
relationships, timestamps and attribution are preserved unchanged.

## The 88 historical proof references

`proof_reference_treatment.json` records all 88 original source/target pointers and
unchanged original digests. All sources and targets successfully revalidated, so
all 88 become **archival-only after new Matrix agreement**. No historical hash was
rewritten. The original archive preserves their complete preimages; the deployed
application does not reconstruct them.

The active scoped structured-identity reader validates the new basis, original
metadata digest and current canonical state. It produces a **new** current proof
binding. Nonidentity layout checking remains in place; explicit tuning claim hashes
are preserved as summaries (all empty in these approved candidates). Failed/missing
basis, incorrect association, duplicate identity or current drift fails closed.
Only both successfully evaluated endpoints may retire an edge; otherwise its
classification remains a blocked active dependency.

Historical manifests/plans using the old proof digests remain archival, not reusable
current execution authorizations. Generic historical Matrix execution/reconciliation
still has its old generation-resolution assumptions and is **not** a new evaluator
for these compact rows. This task neither executes nor modifies that path. Use the
new bounded evaluator/inspector for ordinary MY2021 agreement; do not run historical
imports to inspect completion. Legacy proof formats are not translated or implicitly
accepted as this new profile. Deployment/runbooks must respect this explicit boundary.

## Isolated simulation and exact measurements

Verified original archive and its existing manifest unchanged, all **73** snapshots
round-trip exactly. Original live DB SHA-256 remains
`sha256:b42fc13d6f3e24614e789a7d727e8ec1d179b1d5ee4749923b8b7439ba8fb899`.

| Measurement | Bytes | MiB |
|---|---:|---:|
| Original DB / initial isolated copy | 64,679,936 | 61.68 |
| Copy after replacement before VACUUM | 64,679,936 | 61.68 |
| Copy after copy-only VACUUM | 32,571,392 | 31.06 |
| **Physical DB reduction** | **32,108,544** | **30.62** |
| Selected snapshot JSON before | 32,170,852 | 30.68 |
| Selected compact JSON after | 488,147 | 0.47 |
| **Snapshot payload reduction** | **31,682,705** | **30.21** |

Physical reclamation also recovers pre-existing free pages; it is not identical to
JSON payload savings. No physical reduction occurred on the original database.

Isolated file: `backups/review/my2021_compact_simulation_20261116T193357Z/simulation.sqlite3`.
Compacted copy SHA-256: `sha256:44abf637cf6757d484ac6b0a19d37e04de68290e577ca75b2f838330bd919274`.
Complete operation script and hash are retained alongside that private copy, outside
Git. An earlier rehearsal directory remains preserved; this timestamped report is
final for the current service-source hash. The copy contains private development
authentication data and is **not** a sanitized deployment database.

## Preservation and verification

- Compared all **51 SQLite tables**, including sequence state, before/after replacement
  and compaction. All non-receipt data exactly equal; all receipt columns except the
  73 approved JSON fields exactly equal. Unrelated receipt JSON remains byte-identical.
- Schema objects, migrations, all 1,150 VehicleDefinitions, ten Engines, 3,591 receipts,
  254 correspondence revisions, manufacturers/models/Generations and all relationships
  unchanged. No creation, deactivation or deletion.
- Clone rollback rehearsal restores original JSON exactly. Integrity `ok`, zero FK violations.
- Every replacement passes compact integrity/current agreement inspection and the
  scoped active structured reader. A trap confirms it does not invoke the old document
  validator. Source/tuning/layout behavior is unchanged outside this specific profile.
- **83 focused tests passed**: new MY2021 profile, MY2025/MY2026 existing evaluators,
  Engine reconciliation and assignment regression suites. Isolated test databases;
  Django checks report no issues. Verification used the existing `.venv/bin/python`
  (Python 3.13.1); historical `venv/py313/bin/python` remains absent. No environment
  change was attempted. No generation-overlap tests or operations were run.
- Tests cover exact agreement/Decimal wire normalization, mismatch, missing/duplicate
  Matrix/canonical/receipt matches, missing/changed approval, wrong candidate and
  receipt mirrors, determinism/no writes, compact tampering/stale metadata, all-88
  edge retirement semantics, archive-free/handoff-free inspection, other-year rejection,
  scoped dispatch and transactional rollback.
- Git index, old archive/manifest and pre-existing unrelated working files unchanged.
  No original DB writes, archive edits, staging, commits, pushes or deployment.

## Deployment and final-cleanup procedure — not executed

The new runtime basis is only Matrix plus approval: **1,162,466 bytes / 1.11 MiB**
if not already deployed. Original candidate/source paths remain explanatory audit
references; current compact inspection does not require those files or the historical
archive. Code and these two basis artifacts must ship together with any later compact
DB; missing basis fails closed. Estimated DB-plus-new-basis saving is approximately
29.51 MiB before code/packaging overhead. The offline archive must not be deployed.
No live PythonAnywhere quota or database state was inspected.

After owner approval only: quiesce writers, reverify original DB hash/state, archive
and manifest, authenticate Matrix/approval and **rerun** evaluation. Reuse no stale
replacement after any identity/receipt change. Make a fresh verified SQLite backup
and exact original JSON export. In one explicit transaction update only selected
receipt JSON using PK/UUID and original-text/hash guards; preserve every other column.
Abort on count/hash mismatch or failed verification. Recheck full-table preservation,
compact readers, integrity/FKs; perform compaction on a separately verified copy with
adequate space. Never replace a later live DB with this rehearsal's older copy.

Rollback after a separately authorized live cleanup: use the existing archive and
manifest to restore exact original UTF-8 snapshot text for the same PK/UUIDs inside
an authorized transaction, then reverify raw/canonical hashes and all unchanged
columns. Keep backups and original archive. Do not rewrite historical proof hashes.

No data disagreements or unresolved rows were found. Owner approval of this exact
new normal profile and archival-only treatment is required before live cleanup.
Historical generation-based Matrix re-execution is intentionally not a supported
inspection route for compact receipts; this boundary must be accepted in the cleanup
runbook. Future generic imports can still generate large snapshots: changing their
writer is outside this MY2021-only milestone. No wider redesign was implemented.
