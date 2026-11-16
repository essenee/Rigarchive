# MY2022 Wrangler JL controlled local snapshot cleanup

Created: 2026-11-16
Status: Executed and verified locally; no deployment or Git publication

## Execution

Started **2026-11-16T22:17:59.155920+00:00**, completed
**2026-11-16T22:18:55.512333+00:00**, against `/Users/cosmo/dev/Rigarchive/db.sqlite3`.
Applied the exact reviewed **55** `my2022-approved-matrix-revalidation/1`
replacements, receipt PKs **3221–3275**, in one atomic transaction.
No evaluation profile, compact payload or application implementation was redesigned.
All implementation hashes, approved Matrix/approval, proposed records and actual
successful simulation-copy JSON matched before writing.

Selection required operation `vehicle_definition_import`, outcome `created`, target
and current MY2022, target and current fixed Generation32, Jeep/Wrangler hierarchy,
creation FK and the approved exact identity set. PK range alone was not used.
Receipt PK/UUID/slug/FK mirrors, original snapshot hashes, actual approved Matrix row,
candidate digest and all compact hashes matched. All 55 freshly evaluated as
EXACT_AGREEMENT before writing and remained so after replacement and compaction.

## Verified backup and immutable history

| Artifact | Path / SHA-256 |
|---|---|
| Original local DB | `sha256:e8c07d3da417736ca6e1ae9ae91bb3e830bd4ac4853fda1406ac24ae62e0f126` |
| Complete pre-cleanup backup | `backups/review/my2022_live_snapshot_cleanup_20261116T221759Z/pre_cleanup.sqlite3` |
| Backup hash | `sha256:90cbf8194660fe6acfcf3c658073d4e98c5a2c5a1f6fd1e4ac1cfb0f4544e327` |
| Backup size | 32,571,392 bytes |
| Historical snapshot archive | `backups/review/my2022_snapshot_revalidation_20261116T215017Z/original_snapshots.zip` |
| Archive hash | `sha256:1fbb51a9622811a41715f031e1c5c678fc266d961a18196cc2bd938cbc99f382` |
| Existing archive manifest hash | `sha256:927c6818367ad35ccbd45192ae99308090051eaba75b748ef2e98b5b297bf4a9` |
| Final compacted local DB | `sha256:1f2f31c9453eea02ae179ddb143f789a9c4260b6b523d636a762bea8754f854d` |

The fresh full backup used SQLite's supported backup API, opened successfully,
passed integrity/FK checks and matched the complete live baseline before mutation.
The original 55 snapshot texts matched archived members byte-for-byte with raw and
canonical hashes. All 66 original proof-reference records were verified in the ZIP
and remain recoverable; their original hashes were not rewritten. The existing ZIP,
manifest and new backup remain unchanged. Retain until separate explicit removal
authorization. They are ignored by Git and must remain outside deployment; the full
backup contains private development data and is not a deployment snapshot.

## Actual storage

| Measurement | Before | After |
|---|---:|---:|
| Local SQLite file bytes | 32,571,392 | 25,890,816 |
| Selected snapshot JSON UTF-8 bytes | 7,021,733 | 336,021 |

**Physical saving: 6,680,576 bytes / 6.37 MiB
(20.5106%).** JSON payload saving: 6,685,712 bytes.
After replacement but before compaction the file was
32,575,488 bytes, temporarily one page larger
because of SQLite allocation. Supported in-place local `VACUUM` then reclaimed
space, after all post-write checks passed. Final file size differs from the
successful simulation by **0 bytes**.
JSON byte reduction and physical page reclamation are separate measured values.

DB Browser had the file open, so the maintenance connection acquired an SQLite
exclusive lock before rechecking baseline/eligibility and retained it after commit
through verification, tests and compaction. Other writers were excluded without
terminating the owner's app or using an unsafe file-copy/rename replacement.
Journal mode was DELETE; 588 GiB free disk exceeded required temporary space.
The lock was released after completion. No PythonAnywhere operation occurred.

## Preservation and verification

- Exactly 55 `resolution_snapshot_json` values changed, with exact original-text,
  PK and UUID update guards. No partial cleanup, receipt creation/deletion or import.
- All **51 SQLite tables** were compared against the verified backup using SQLite
  quoted values. All canonical/reference rows, schemas/migrations and sequences are
  identical. Receipt identities, timestamps, attribution, outcomes, target fields,
  mirrors and relationships remain byte-identical. Every unrelated receipt snapshot
  remains byte-identical, including the existing MY2021 compact values.
- Counts remain **1,150 VehicleDefinitions**, **ten Engines**, **3,591 receipts**,
  **254 correspondence revisions**, 16 Generations, six models, five manufacturers.
  No canonical create/update/deactivation/delete or relationship change occurred.
- All 55 MY2022 compact records pass integrity, original metadata digest, approved
  basis and current identity checks. All 55 remain EXACT_AGREEMENT. Existing ordinary
  structured/tuning inspection works without reconstructing historical documents.
- All **73 MY2021 compact records** still validate. All **66 MY2022 historical proof
  references** retain documented archival-only treatment after endpoint agreement;
  original import history is not misrepresented as a new import.
- Integrity `ok`; zero foreign-key violations after writing and compaction.
- Django system checks pass before/after. **107 focused regressions passed after
  replacement and again after compaction** using isolated test databases: MY2022 and
  MY2021 profile/consumer tests, MY2025/MY2026 normal evaluators, Engine reconciliation
  and assignment execution. These are the relevant full focused suite; unrelated
  full-project tests were not added to this maintenance operation.
- Approved Matrix, source evidence, original authorization/execution artifacts,
  archive and implementation remained unchanged. No migration, acquisition, canonical
  import or generation-resolution operation was invoked. No test suppression/code repair.

The current bounded profile independently records new 2026 agreement with the approved
manufacturer-based Matrix, preserving Edmunds corroboration. Original execution
columns and candidate/Matrix attribution remain historical. The deployed application
must use the current compact inspection profile, not historical generation-based
Matrix re-execution or reconstructed original snapshot hashes.

## Evidence and changed files

`preflight.json` records exact original hashes/counts and selection.
`receipt_replacement_manifest.json` records all 55 original/compact hash mappings.
`execution_results.json` records actual sizes, hashes and preservation/test results.
The executed maintenance script and all post-write/post-compaction logs are retained
beside the backup, outside Git. Previous investigation/simulation reports were not
modified. There were no deviations requiring corrective data or code changes.

Files changed in this task: `db.sqlite3`, `docs/implementation/CURRENT_STATE.md`,
`CHANGELOG.md`, plus this new timestamped maintenance report directory. Pre-existing
source modifications, untracked files and the normal Git index are preserved.
No staging, commit, push, deployment or unrelated work performed.

## Recovery instructions

Keep the verified full backup and existing ZIP/manifest. Any future restoration
requires separate explicit authorization and a fresh backup of the then-current
state. Quiesce writers and acquire exclusive access; verify exact receipt PK/UUID,
expected current compact hash and original archive member hash. Rehearse on a copy.
Restore only the authorized original UTF-8 JSON text with bound SQL parameters and
exact guards in one atomic transaction; preserve all other columns and unrelated
rows. Check all 55 raw/canonical hashes, complete table preservation, integrity/FKs
and applicable readers before committing recovery. Do not rewrite original proof
hashes. Do not blindly overwrite subsequent owner work with this older whole backup.

If full recovery is necessary, use a supported SQLite recovery mechanism under
controlled exclusive access, then verify complete logical contents and record its
physical hash; SQLite header/layout counters can differ after a supported restore.
No recovery was necessary here. Historical archive instructions remain in
`docs/research/my2022_snapshot_revalidation_20261116T215017Z/RESTORE.md`.

No outstanding cleanup issue was found. Future generic snapshot-writer optimization,
other model years, Git publication and PythonAnywhere deployment remain out of scope.
