# Snapshot archive verification and recovery

The archive is local-only under `backups/review/my2021_snapshot_archival_20261116T191303Z/original_snapshots.zip`.
It is not a deployed application dependency and must not be uploaded to PythonAnywhere.
`archive_manifest.json` in this report directory pins the archive hash and maps every
receipt PK/UUID to one member, exact UTF-8 byte count, raw SHA-256 and canonical SHA-256.
The ZIP members contain the original SQL JSON text, including original whitespace.
The local baseline SQLite backup and complete receipt-row export remain alongside it.
The SQLite copy contains private development data: keep it local and out of Git/deployment.

## Non-mutating verification

From the repository root, use `.venv/bin/python` to load the manifest, SHA-256 the ZIP
bytes against `archive.archive_sha256`, require ZIP CRC checks to pass, then read each
named member without extracting it. Verify raw SHA-256/length; parse JSON and verify
its canonical digest using sorted keys, ensure_ascii=False, compact separators and
allow_nan=False. Compare member bytes against SQL `resolution_snapshot_json` selected
by matching PK **and** UUID from a `mode=ro` SQLite connection. This was executed for
all 73 members. Archive timestamps are fixed to 1980-01-01 for deterministic packaging.

## Future recovery — separate write authorization required

1. Quiesce writers; preserve a verified backup of the target before any recovery.
2. Verify the archive and every selected member as above; check exact receipt identity,
   outcome and canonical target mirrors. Never select rows solely by PK range.
3. Rehearse on a disposable copy. In one explicit transaction, restore only the
   authorized `resolution_snapshot_json` fields using bound SQL parameters and exact
   PK/UUID guards. Use the archived UTF-8 text directly; do not reserialize it.
4. Abort if any receipt identity, expected current hash or selected-row count differs.
5. Verify restored SQL text raw/canonical hashes, integrity, FKs and unchanged remaining
   columns/tables before committing the separately authorized live restoration.
6. Never replace live development or production wholesale with this older baseline:
   that could discard subsequent owner changes. No restoration was performed here.
