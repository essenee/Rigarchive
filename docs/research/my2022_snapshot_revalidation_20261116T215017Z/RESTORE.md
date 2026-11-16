# MY2022 archive verification and restoration

Created: 2026-11-16
Status: Instructions only; no live restoration or cleanup authorized

## Durable offline package

Archive: `backups/review/my2022_snapshot_revalidation_20261116T215017Z/original_snapshots.zip`
SHA-256: `sha256:1fbb51a9622811a41715f031e1c5c678fc266d961a18196cc2bd938cbc99f382`
Bytes: 765,339.

Transfer the ZIP together with this report's `archive_manifest.json`,
`historical_proof_references.json` and these instructions to separately retained
durable storage before future live cleanup. Member paths are portable and do not
require the original repository absolute location. The ZIP is ignored by Git and
must not be part of PythonAnywhere deployment. It contains exact original snapshot
SQL JSON text plus the 66 original proof references, including unchanged digests.
The baseline backup also remains retained locally; it contains private development
data and must not be uploaded or committed.

## Verification (no writes)

1. Compute SHA-256 of ZIP bytes and compare with the archive manifest above.
2. Require ZIP CRC validation to pass. Read members directly, without extracting
   arbitrary paths. Reject missing, duplicate or extra unexpected members.
3. For each of 55 entries, check receipt PK/UUID, canonical PK/UUID/slug, member name,
   original byte count, raw SHA-256 and canonical JSON SHA-256.
4. Canonical algorithm: sorted object keys, ensure_ascii=False, compact separators,
   allow_nan=False, UTF-8, SHA-256 with `sha256:` prefix. Preserve array order.
5. Verify `historical_proof_references.json` member bytes against its manifest hash,
   and the 66 source/target pointer/digest records. Do not recompute old hashes to
   describe a different compact snapshot.
6. Compare snapshot member bytes with read-only SQL JSON selected by PK **and** UUID.
   All 55 matched byte-for-byte in this task; every proof digest matched its target.

## Restore/recovery — separate explicit write approval required

Preserve the then-current database and quiesce writers. Reverify archive and scope;
never restore an old whole baseline over subsequent owner changes. Rehearse on a
copy. Under one atomic transaction, guard each approved target by exact PK/UUID and
expected current snapshot hash, and restore only the archived original UTF-8 JSON
text using bound SQL parameters. Do not reserialize it. Require exactly 55 updates
or roll back. All other receipt columns and every unrelated table must remain
identical. Check raw/canonical hashes, integrity/FKs and receipt relationships.
A later cleanup's rollback procedure must retain its own fresh verified full backup.
The existing baseline is not permission to overwrite the original database.

A rollback of an injected first-row update was tested on the simulation copy and
restored the original JSON exactly. No original database data was altered here.
