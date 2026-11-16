# MY2021 local SQLite snapshot cleanup — completed

Created: 2026-11-16
Status: Executed and verified locally; no deployment or Git publication

## Execution and eligibility

Execution began **2026-11-16T19:51:13.993241+00:00**, completed
**2026-11-16T19:52:37.929567+00:00**, against `/Users/cosmo/dev/Rigarchive/db.sqlite3`.
Applied the exact reviewed `my2021-approved-matrix-revalidation/1` replacements for
**73 receipts (PK 3076–3148)**; no regenerated evaluation timestamp or historical
import timestamp was substituted. All 73 remained EXACT_AGREEMENT immediately before
writing and after both replacement and compaction.

Selection used operation `vehicle_definition_import`, outcome `created`, target and
current MY2021, target and current Generation 32, existing Jeep/Wrangler canonical
hierarchy and creation FK. The selection exactly matched the reviewed replacement
set and archived receipt identities; PK range alone was not used. UUID/slug/FK,
Matrix/candidate pins, original snapshot bytes/hashes and compact integrity all passed.
The implementation source hash matched the successful simulation. No application
code changed during this maintenance task.

The approved Matrix retains manufacturer-based authority with Edmunds corroboration;
Generation was compared as a fixed identity. No generation-resolution operation,
canonical import, acquisition, migration or historical snapshot reconstruction ran.

## Backup and immutable historical evidence

- Original DB SHA-256: `sha256:b42fc13d6f3e24614e789a7d727e8ec1d179b1d5ee4749923b8b7439ba8fb899`.
- Complete supported SQLite backup: `backups/review/my2021_live_snapshot_cleanup_20261116T195113Z/pre_cleanup.sqlite3`.
- Backup SHA-256: `sha256:cd276a0944f57465dc0a78f03cd4cacf5ae07374c0bdea29c25be023e1b3b83d`.
- Historical snapshot ZIP: `backups/review/my2021_snapshot_archival_20261116T191303Z/original_snapshots.zip`.
- ZIP SHA-256: `sha256:7e59b872e589b18d36c3dff231963d9600422549dd19b9c052df7ee57d583b70`.
- Existing archive manifest SHA-256: `sha256:251a8ee06e9702d8db32a012b490999dba1359e2d683ca03c64cf4562b5f65e0`.

The backup was created through SQLite's backup API, opened and integrity/FK checked,
and compared against the full live baseline under an exclusive lock. Both backup
and historical ZIP/manifest remain unchanged and retained. All 73 ZIP members match
original SQL JSON text byte-for-byte with raw and canonical hashes. Backups contain
private development data: keep outside Git/deployment; do not upload to PythonAnywhere.
No backup may be removed without owner authorization.

## Measured storage

| Metric | Before | After |
|---|---:|---:|
| SQLite file bytes | 64,679,936 | 32,571,392 |
| Selected snapshot UTF-8 bytes | 32,170,852 | 488,147 |

**Database saving: 32,108,544 bytes / 30.62 MiB,
49.6422%.** Snapshot payload saving: 31,682,705 bytes.
The database stayed 64,679,936 bytes immediately
after replacement; supported local `VACUUM` reclaimed the free pages only after all
post-write checks passed. Final size differs from the simulation by
**0 bytes**.

Final DB SHA-256: `sha256:e8c07d3da417736ca6e1ae9ae91bb3e830bd4ac4853fda1406ac24ae62e0f126`.
No file-copy replacement/rename of the live database was used. DB Browser had an
open connection, so an SQLite exclusive lock was acquired before preconditions were
rechecked and retained through the transaction, verification and compaction. Other
writers were excluded without killing or altering the owner's application. The
connection was closed and its lock released only after successful final verification.
Journal mode was DELETE; 588 GiB available disk exceeded temporary-space requirements.

## Preservation and functionality

- Exactly 73 JSON fields changed in one atomic transaction. No receipt or vehicle
  was created/deleted; all original outcomes, attribution, timestamps, PKs, UUIDs,
  canonical mirrors and FKs remain byte-for-byte unchanged.
- All **51 SQLite tables**, including sequence state, were
  compared using SQLite-quoted values to avoid Python adapter representation effects.
  All canonical/reference data and schema/migrations remain identical to the backup.
  Every unrelated receipt JSON value remains byte-identical.
- Counts unchanged: 1,150 VehicleDefinitions, ten Engines, 3,591 receipts,
  254 correspondence revisions, 16 Generations, six models, five manufacturers.
- All 73 compact records pass their content hash, original metadata digest,
  authenticated Matrix/approval and current canonical identity checks. Scoped normal
  structured/tuning readers work without the historical source collection or archive.
- All **88 original proof references** retain their documented archival-only treatment;
  original digests/preimages remain recoverable from the unchanged ZIP. No historical
  proof hash was rewritten or falsely claimed to match a compact snapshot.
- SQLite integrity `ok`, zero foreign-key violations after replacement and compaction.
- Django system checks passed preflight, post-write and post-compaction.
- **83 focused regressions passed after writing and again after compaction**, using
  isolated test databases: MY2021 revalidation/consumers, MY2025/MY2026 evaluators,
  Engine reconciliation and assignment tests. Captured logs are beside the backup.
- No application changes, suppressed tests, unrelated canonical work, deployment,
  staging, commit or push. Existing unrelated working-tree content and Git index preserved.

## Deviation and stopped first preflight

An initial preflight attempt stopped **before writing** because its maintenance
comparison compared Django-converted datetimes against raw SQLite timestamp text.
Original DB SHA remained unchanged after rollback. Only the temporary diagnostic
was corrected to compare SQLite `quote(column)` values on both connections; no
application code or data was repaired. A fresh complete preflight then passed.
The first attempt's backup and failure record remain preserved at
`backups/review/my2021_live_snapshot_cleanup_20261116T195023Z/` and
`docs/research/my2021_live_snapshot_cleanup_20261116T195023Z/`.

## Recovery and operational boundaries

The exact selected-row replacement manifest is `receipt_replacement_manifest.json`;
preflight hashes/counts are in `preflight.json`; actual results in
`execution_results.json`. The executed maintenance script and test logs are retained
beside the verified backup, not shipped as application infrastructure.

Future restoration needs separate owner authorization. Quiesce writers and acquire
exclusive access, preserve the then-current DB, verify the retained backup/ZIP and
receipt PK/UUID/expected current hashes, then restore only the original 73 JSON text
values from the archive in a single transaction. Compare raw/canonical snapshot
hashes, every other receipt column, all unrelated tables and integrity/FKs. A full
backup restoration must use supported SQLite recovery under controlled exclusive
access; SQLite header/layout counters may change, so verify both the physical hash
and complete logical baseline rather than falsely claiming byte identity. Never
restore this older whole DB over subsequent owner changes without explicit scope.

PythonAnywhere was not inspected, modified or deployed. Any future deployment must
ship the compact profile and its retained approved Matrix/approval together; the
historical ZIP is offline-only, not an application dependency. Do not deploy the
private development backup or rely on historical generation-based Matrix re-execution
for compact receipt inspection. Future generic import writers remain outside this
MY2021 maintenance task and may still create large snapshots.
