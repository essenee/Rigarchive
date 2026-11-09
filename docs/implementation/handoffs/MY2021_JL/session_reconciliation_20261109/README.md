# MY2021 canonical execution — read-only session reconciliation

Created: 2026-11-09
Status: Accepted — current operational baseline verified; no import executed

**No unexplained non-session application changes were found across all 48 SQLite
tables.** After separately reconciling the documented MY2021 correspondence
publication, the remaining operational change is one normal Django browsing
session update. A fresh execution baseline is recorded in
`execution_baseline.json` under the owner's conditional re-baselining instruction.

Current live database:

`/Users/cosmo/dev/Rigarchive/db.sqlite3`

Fresh verified SHA-256:

`058bbd44e0811c83bf67c916ae92e27b6a0b062c26be031876e9582190e01473`

Size **13,438,976 bytes**. Observed modification time **2026-11-09 16:33:33 UTC /
08:33:33 America/Los_Angeles**. Exact subsecond modification/birth times, hashes
and sizes are retained in `database_metadata_and_baselines.json`. The live file
hash remained unchanged throughout the audit and was checked again afterward.

## Baseline selection and historical limits

The closest retained verified physical snapshot is:

`backups/review/MY2021_JL_correspondence_prepublication_20261109T154455104372Z.sqlite3`

It was created **2026-11-09 15:44:55 UTC / 07:44:55 America/Los_Angeles** and has
SHA-256 `06502534d35395b97d74447b98c760f237a1e2aba04860f32d349fab62bd1d92`.
The digest matches its original publication preservation record. The metadata
inventory records all relevant retained review backups with hashes and filesystem
creation/modification dates, using birth time only where the filesystem supplies it.

That snapshot precedes the **95 authorized correspondence and 95 publication
receipt additions**. It contains 861 VehicleDefinitions, 2,980 receipts and 64
correspondences. Therefore a raw backup/live comparison is **not literally
session-only**: it also contains those explicitly documented additions and their
two sequence advances. This audit verifies those rows individually against the
immutable reviewed proposals and publication records rather than ignoring them
or classifying them as session activity.

Neither the earlier certified-planning byte state (`ecc52124…`) nor the stopped
preflight byte state (`de2308f1…`) has a matching retained physical snapshot.
**Their precise historical file-byte delta cannot be reconstructed.** This audit
does not claim retrospective proof that a particular HTTP request caused each
intermediate file hash. It establishes the current state by all-table comparison,
explicit publication reconciliation and validated session-change nature.

The new baseline supersedes the old database-byte reference for renewed import
preflight only. It does not change the certified Matrix or overwrite the original
planning, publication or stopped-preflight records.

## Complete table comparison

`all_table_comparison.json` lists every table, exact counts, every added/deleted
primary key, and every changed row's primary key and changed columns. Session
primary keys are authentication tokens, so reports use stable one-way fingerprints
instead of exposing their values.

| Comparison with closest physical snapshot | Actual finding |
| --- | --- |
| VehicleDefinitions and all other unchanged application tables | Every preexisting row and column unchanged |
| Generation correspondences | Exactly documented PKs 65–159 added; all 64 earlier rows unchanged |
| Audit receipts | Exactly documented publication PKs 2981–3075 added; all 2,980 earlier rows unchanged |
| sqlite_sequence | Only correspondence/receipt counters advance by 95 each |
| django_session | Five rows before/after; zero additions/deletions; one changed row |
| Schema/table/column/PK definitions | Unchanged |
| Unexplained application additions/deletions/updates | Zero |

All 95 new correspondence payloads, targets, UUIDs and hashes match their approved
proposals. All 95 publication receipt IDs/UUIDs, source identity, review snapshot,
hash, attribution and outcome match their retained publication records. Remaining
receipt fields match service defaults, and automatic timestamps fall within the
original publication creation window, without evidence of later row updates.
These rows did not exist in the selected physical backup: their full historical
row bytes cannot be compared to it, so this distinct provenance check is explicitly
reported in `documented_publication_reconciliation.json`.

## Session-specific findings

The one changed row has only **`session_data` and `expire_date`** changed.
Both before/after payloads pass Django signature verification. Decoding shows:

- No decoded key added or deleted.
- The **only changed decoded field is `recently_viewed_generations`**.
- Authentication fields and every other decoded value are unchanged.
- History grows from one entry to five, respecting the existing cap, unique-entry
  rule and expected seven-field schema. All retained history entries match actual
  canonical Generation metadata; no browsing URLs/names or session contents are
  disclosed in these reports.
- The payload signing time advances from **04:13:54 UTC to 16:33:33 UTC** on
  2026-11-09. Expiry advances correspondingly, matching Django's normal
  **1,209,600-second (14-day)** session lifetime. Exact expiry metadata is retained
  in the redacted session assessment.

The application provides the matching ordinary write path:
`GenerationHubView.get_context_data` in `reference/views.py` calls
`record_recently_viewed_generation` in `reference/services.py`. That function
bubbles/inserts a generation, caps history at five and marks the session modified.
Django then re-signs the session and renews expiry. The observed changes are
consistent with the owner's stated local-site browsing, not merely assumed benign
because they occur in the session table. The individual request/actor is not
attributed without access logs; that is not necessary to assess the change nature.

No session contents, raw session-key primary keys, credentials, stored password
hashes, authentication hashes, tokens, account names or contact values are disclosed.
The baseline retains only one-way row/column/aggregate fingerprints and schema
metadata for later comparison, never usable session or credential values.

## Committed sanitized checkpoint

`HEAD:db.sqlite3` was read into an isolated in-memory SQLite connection. Its
SHA-256 is
`4c374c89dc2eaec66e308a4679cdad7592d138f2903b5d377126e2ff1e08e573`,
matching the documented `MY2020_commit_checkpoint_20261109T025312470275Z`
sanitized copy exactly. It has zero sessions and the pre-MY2021-publication totals
861 / 2,980 / 64; it is not the current operational database or an appropriate
replacement baseline.

Comparing that committed copy to the closest operational backup finds only the
documented five removed sessions and sanitization of the existing account's
`password`, `last_login`, `username`, `email` and `display_name` columns. The
sanitization record explicitly names these fields. No changed account values are
reported. All other tables are identical. Operational user/account/group data
then remains unchanged between the closest backup and current live database.

## Canonical preservation and fresh baseline

Verified counts are **861 VehicleDefinitions / 3,075 receipts / 159 published
correspondences**. All 861 existing VehicleDefinitions match the verified backup
in every column, including PK, UUID and slug. All correspondence targets and
approved publication bindings are preserved. Prior import receipts and their
lineage are unchanged. The MY2021 US JL namespace still has **zero canonical
records**, and no successful MY2021 JL import receipt was created.

SQLite integrity is **ok**, foreign-key violations **zero**. The certified Matrix
digest is unchanged:

`sha256:6926df6c06e4bd471bbda02c67257cf7a7e2999cf5cdfebfc8b06ead31a9996e`

`execution_baseline.json` records the current file hash/size/times, every table's
count, full row/column fingerprints, schema digest, canonical identity digest,
correspondence identity/target digest, receipt/lineage digest and verified session
fingerprints. It preserves the exact already-authorized 73-row scope, 23/50 body
distribution, target JL32/expected UUID and zero expected no-ops.

This baseline establishes a current verified operational state with no unexplained
application drift. It does **not** waive later drift checks or replace full fresh
candidate/plan/approval validation and a new consistent pre-import backup. Local
site browsing can legitimately update sessions again; a stable next preflight/
backup/execution window will avoid another unrelated session write during those
checks. No server or browser state was changed by this audit.

## Read-only verification and deliverables

The audit used repository `.venv/bin/python`, Python **3.13.1**, with the installed
Django session-signing implementation. All live connections used SQLite URI
**mode=ro** plus **query_only=ON**. A read transaction provided a consistent snapshot;
the committed database copy existed only in memory. No live database write,
session save, import, migration, dependency change, restore or new database backup
was performed. No application code or accepted contract changed. No commit or push.

Files in this directory:

- `database_metadata_and_baselines.json`: live file and historical backup metadata,
  creation dates/hashes, committed checkpoint identity and baseline limitations.
- `all_table_comparison.json`: all 48 tables and every row/column difference.
- `session_nature_assessment.json`: privacy-safe session PK fingerprint, column/key
  changes, signature/lifecycle checks and application write-path assessment.
- `committed_sanitization_assessment.json`: documented private-state differences.
- `documented_publication_reconciliation.json`: all 95 approved publication pairs.
- **`execution_baseline.json`**: new verified baseline for renewed preflight.
- `verification_summary.json`, `audit_log.txt`: actual results and no-write evidence.
- `audit_sessions.py`, `artifact_hashes.json`: bounded audit implementation and
  immutable output hashes.

`CURRENT_STATE.md`, `CHANGELOG.md`, the certified package and the failed execution
checkpoint were left unchanged. This is the requested read-only investigation
and baseline record, not a completed import milestone. **No import ran.**
