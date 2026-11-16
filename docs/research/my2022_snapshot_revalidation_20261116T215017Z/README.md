# MY2022 Wrangler JL compact revalidation and isolated cleanup

Created: 2026-11-16
Status: Implemented and verified on isolated copy only; live cleanup not authorized

## Outcome and scope

**55 EXACT_AGREEMENT; zero normalized agreements, disagreements/conflicts,
insufficient-evidence cases or evaluation blockers.** Every targeted row was actually
evaluated by the new bounded profile `my2022-approved-matrix-revalidation/1`.
All 55 were eligible before simulation began. Receipt PKs **3221–3275** correspond
to 55 existing MY2022 US Jeep Wrangler JL VehicleDefinitions, PKs 950–1004.
Selection used actual operation/outcome, year, fixed Generation32, Jeep/Wrangler
hierarchy, US market and creation relationships; PK range alone was not the selector.

Authority is the executed **manufacturer-based approved MY2022 Matrix**, with retained
Edmunds corroboration—not the MY2021 Matrix and not a new Edmunds-derived inventory.
The Matrix and approval are copied byte-identically under
`docs/research/my2022_revalidation_basis_20261116/` for durable current verification.
Digest: `sha256:e92f9ab6d7b585406e86f697e9cae8400233fc874f4ea884bec718b9148c56cb`.

All 55 retain the same canonical parents, year/market/trim/engine/drivetrain and five
powertrain fields, exact slug and PK/UUID. Current authored Engine associations
are compared without reassigning them; all null factory-body relationships remain
null. High Tide remains distinct; ERC and ERG are not collapsed; diesel, 4xe and
392 remain their approved identities. Deferred RHD is not silently added.

## Implementation and changed-file inventory

- `reference/my2022_wrangler_revalidation.py`: separately pinned, read-only profile,
  approved basis/candidate/source verification, deterministic result and compact
  construction/inspection, and historical-reference classification. It shares only
  side-effect-free wire/identity/metadata helpers with MY2021; no generalized evaluator
  or historical reconstruction layer was introduced. There is no database-write API.
- `reference/ingestion/importing/powertrain_identity.py`: exact-version MY2022 dispatch
  for compact structured inspection and existing nonidentity guards. The MY2021 branch
  remains equivalent; other versions keep the original fallback. No generation
  resolver/correspondence/overlap behavior was changed.
- `reference/tests/test_my2022_wrangler_revalidation.py`: focused, self-contained tests
  use durable basis files, not ignored handoff code or external archive files.
- `docs/research/my2022_revalidation_basis_20261116/`: exact Matrix/approval copies and
  provenance README; no new approval or changed Matrix/source artifact.
- This report directory: archival manifest, original proof inventory, new per-row
  results, proof treatment, proposed compact records, example, measurements and restore
  instructions. CURRENT_STATE and CHANGELOG record simulation only, not live cleanup.

The new service reads/hashes retained approved evidence but does not rerun extraction,
adjudication, generation selection or canonical import execution. Source hashes,
full candidate hashes, document projections and execution-manifest hashes matched
the exact approved Matrix rows. Relevant explicit horsepower/torque assertion sets
are empty across this fixed approved scope; their empty hash sets are preserved,
not replaced with invented outputs. Full source context is retained in candidates
and archived historical snapshots, not embedded in the new compact records.

## Historical preservation

**All 55 original snapshots archived and verified byte-for-byte**, with receipt,
canonical identity, candidate/Matrix/manifest pins, raw and canonical snapshot hashes,
member names and byte counts in `archive_manifest.json`. ZIP timestamps are fixed
for deterministic packaging. All 66 original proof references are also a ZIP member.

Archive: `backups/review/my2022_snapshot_revalidation_20261116T215017Z/original_snapshots.zip`
Archive SHA-256: `sha256:1fbb51a9622811a41715f031e1c5c678fc266d961a18196cc2bd938cbc99f382`
Archive size: **765,339 bytes / 0.73 MiB**.
Full consistent baseline backup: `backups/review/my2022_snapshot_revalidation_20261116T215017Z/baseline.sqlite3`
Backup SHA-256: `sha256:90cbf8194660fe6acfcf3c658073d4e98c5a2c5a1f6fd1e4ac1cfb0f4544e327`.

Archives/backups remain outside Git and deployment. The ZIP and companion manifest
can be copied to independent durable storage without the live SQLite database.
The archive and original manifest were unchanged throughout replacement simulation.
All original snapshots are still present in the original database. No historical
receipt, source evidence, approval, candidate or execution artifact was edited.
See `RESTORE.md` for hash verification and separately authorized restoration steps.

## Proof references and compact current basis

`historical_proof_references.json` records all **66** source/target JSON pointers,
original digests and ordinary structured-identity meaning. All endpoints successfully
revalidated; `proof_reference_treatment.json` therefore marks each edge
**ARCHIVAL_ONLY_AFTER_NEW_MATRIX_AGREEMENT**. Original hashes are untouched and their
original preimages remain in the ZIP. No cross-year incoming proof dependency was
found in the database inventory. Historical plans/approvals are not silently translated
or reauthorized by this new evaluation.

Ordinary MY2022 compact readers verify current approved-Matrix agreement rather than
claim to reconstruct old hashes. Scoped consumers bind the new compact record hash;
layout/tuning guards remain in place. Partial endpoint success leaves an edge blocked,
not retired. Historical generation-based Matrix execution/reconciliation remains an
archival route for this scope, not the compact current-inspection mechanism. No
unrelated legacy workflow or ADR-0010 behavior was modified.

Each compact record retains version; original execution metadata digest, candidate
hash, original Matrix linkage/attribution and archive hashes/member; new revalidation
identity/outcome/profile/revision/timestamp; compact artifact/source references;
nonidentity claim hashes; and its own integrity hash. No PDFs, source-document arrays,
complete candidates, complete Matrix or original resolution snapshots are embedded.
The new evaluation timestamp is not substituted for original execution timestamps.
The retained approval remains original authorization evidence, not a fabricated new
2026 import decision. `representative_compact_record.json` shows the actual format.

## Results and measured storage

`revalidation_results.json` contains every result and field-level comparison, exact
Matrix row/digest, candidate hash, code revision/source hash, timestamp, normalization
and evidence pins. `proposed_compact_records.json` contains all 55 exact candidates
for a later authorized replacement. Successful inspection needs the retained current
Matrix/approval, **not** the historical archive or original handoff corpus.

| Measurement | Before | After |
|---|---:|---:|
| SQLite bytes, including safe copy-only compaction | 32,571,392 | 25,890,816 |
| Selected JSON UTF-8 bytes | 7,021,733 | 336,021 |

**Measured database saving: 6,680,576 bytes /
6.37 MiB (20.51%).**
**JSON payload saving: 6,685,712 bytes /
6.38 MiB.** These are separate measurements.

Before compaction, replacement temporarily grew the copy from 32,571,392
to 32,575,488 bytes (one SQLite page of
allocation). `VACUUM` ran only on the copy after preservation checks. No physical
size projection was substituted for this measurement.

Isolated database: `backups/review/my2022_snapshot_revalidation_20261116T215017Z/simulation.sqlite3`
Compacted-copy SHA-256: `sha256:78218f5f4824654970dd00397f764fcaf3bb0beeea642beecb30b9bc125cd0a6`.
It contains private development data and is not a sanitized deployment snapshot.
Runtime MY2022 Matrix+approval: **343,150 bytes / 0.33 MiB**.
If newly deployed, that overhead reduces estimated database-plus-basis savings to
about 6.04 MiB before code/packaging.
Do not deploy the historical ZIP or private backups merely to shift quota usage.
PythonAnywhere space/state was not inspected or modified.

## Verification

- All **51** SQLite tables compared before/after replacement and compaction using
  SQLite-quoted values. All canonical/reference records and schema/migrations/sequence
  state identical. Receipt identities, outcomes, timestamps, metadata and relationships
  identical; every unrelated receipt snapshot, including all 73 MY2021 compact values,
  remains byte-identical.
- Counts remain 1,150 VehicleDefinitions, ten Engines, 3,591 receipts and 254
  correspondence revisions. No canonical record or receipt created/deleted/deactivated.
- All 55 replacements validate after compaction and work through scoped current
  structured/layout/tuning readers. A trap prevents calling the old document validator.
  All 73 MY2021 current compact records independently validate on the simulated copy.
- Single-transaction clone replacement, exact original JSON guards and an injected
  rollback rehearsal passed. No live database connection was opened writable.
- SQLite integrity `ok`, zero foreign-key violations. Django system checks passed.
- **107 focused regressions passed**: MY2022/MY2021 profile tests, existing MY2025/
  MY2026 normal evaluators, Engine reconciliation and assignment execution tests.
  These use isolated test databases. Coverage includes wrong/missing/duplicate bindings,
  approval failure, Decimal precision, no writes, deterministic results, compact integrity,
  stale canonical/metadata state, 66-edge treatment, year isolation, rollback, High Tide,
  ERC/ERG distinction and archive-free inspection. No generation-overlap tests run.
- Existing `.venv/bin/python` is Python 3.13.1; prescribed historical `venv/py313`
  remains absent. No environment installation or configuration change was attempted.
- Original DB SHA-256 remains `sha256:e8c07d3da417736ca6e1ae9ae91bb3e830bd4ac4853fda1406ac24ae62e0f126`;
  size **32,571,392 bytes**, unchanged. Archive/manifest, Git index
  and unrelated working files are preserved. No staging, commits, pushes or deployment.

## Readiness and next decision

**Ready for owner review and separate live-cleanup authorization:** 55 independently
verified eligible replacements, no data disagreements or unresolved proof endpoints.
This task does **not** authorize writing them to the original database.

Before a future live cleanup: transfer/verify the offline archival package on separate
durable storage; reverify current implementation pins, archive/manifest, Matrix approval,
all 55 identities and original JSON hashes; capture a fresh complete supported SQLite
backup; rerun exact agreement and compact validation. Guard every update by original
PK/UUID/text/hash inside one atomic transaction. Require all 55 or roll back. Compare
all tables and receipt columns, run checks/tests, then compact only with adequate
space and exclusive access under separate explicit authorization. Rehearsal copy
must not replace a later live database or discard subsequent owner changes.

For rollback, preserve the original exact UTF-8 JSON from the archive and fresh
backup, restore only the authorized 55 snapshots under PK/UUID/current-hash guards,
and verify full baseline preservation. Do not rewrite old proof hashes or republish
correspondences. Future generic import-writer optimization remains outside this scope.
