# MY2021 JL milestone Git checkpoint

Created: 2026-11-09
Status: Validated

The owner authorizes preserving and publishing the completed MY2021 milestone,
including the existing approved configurator commit `8d4a6e8`. Preflight verified
local `main` at that commit and remote `main` at `5a451d2`; no divergence or new
unrelated work was found. No further configurator or drive-wheel work was begun.

## Retained evidence and canonical verification

The [inventory](artifact_inventory.json) retains **1,910 original milestone files**,
396,779,261 bytes: discovery evidence/extractions, 32 PDFs (27 guides, four technical
PDFs and the owner manual), owner approvals, base/current candidates, adjudications,
shared selector evidence, correspondence proposals/publications, certified planning,
execution manifests and receipts, and the session-reconciliation record.
All **1,897 previously recorded artifact hash entries** passed. The checkpoint
adds its own scripts/reports separately; historical artifact inventories are unchanged.

Fresh accepted Matrix receipt reconciliation reports **73 previously completed**
rows with no replay. All 73 canonical definitions,PK 877–949, have unique matching
UUIDs/slugs, complete five-field identities and Generation 32. All 73 execution
receipts,PK 3076–3148, match certified candidate/manifest hashes and target snapshots.
All 95 MY2021 correspondence revisions,PK 65–159, and publication receipts reconcile
to their approved review payloads. Totals are **934 VehicleDefinitions / 3,148 receipts /
159 correspondences**; 23 two-door / 50 four-door and 24 labels. All 88 original approved
classification decisions, the additional 392 fuel approval and ECX direct evidence
remain preserved. JLUL74/CLASS-075 remain excluded and deferred.

Certified Matrix:
`sha256:6926df6c06e4bd471bbda02c67257cf7a7e2999cf5cdfebfc8b06ead31a9996e`.

## Operational database preservation and session reconciliation

The initial file-hash gate detected a change since execution. Read-only comparison
using the retained session guard verified **one ordinary session update**, while
all preexisting non-session application rows remained unchanged and additions were
exactly 73 definitions and 73 receipts. Full current identity/receipt/Matrix checks
then passed. The initial gate log is retained in `validation.txt`; the explained
session difference is recorded in `checkpoint_session_assessment_baseline_check.json`.
No unexplained application drift remains.

The operational database SHA-256 before and after checkpoint preparation is:
`sha256:c37823955537d922c708d091a1494188c80f3cdc458b480c0fa955106d752ef6`.
It is **not** the sanitized Git database. No live sessions, accounts or canonical
records were modified. No migrations/backfills/imports were performed.

## Sanitized Git database

Following MY2020 commit `5a451d2`, a consistent SQLite backup was sanitized only
in the ignored copy:

`/Users/cosmo/dev/Rigarchive/backups/review/MY2021_commit_checkpoint_20261109T182304627056Z.sqlite3`

SHA-256: `sha256:431fa5e47d7c80021ed8bc7c63dc8feee0cdb0447664f07b7c406cf57e94ae97`.

Five session rows were removed. Existing account PK 17 retains its foreign-key
identity, roles and relationships; username/display name become the same generic
MY2020 development labels, password becomes unusable (`!`), email becomes blank
and last_login becomes null. No operational credentials/session values are reported.
Secure deletion and VACUUM remove deleted content from the copy. Exact operational
password/session bytes and credential-pattern scans passed. No token/credential
storage tables exist. All other tables, schemas and SQLite sequences match live.

SQLite integrity and foreign keys passed. Restoration via SQLite backup to a
separate temporary development file reproduced every sanitized table exactly.
Read-only Django checks/ORM queries confirmed all totals and 73 MY2021 rows, with
no usable passwords or account emails. To restore for development, use the Git
checkpoint only in a distinct development workspace/database, then establish local
authentication separately. Never overwrite the operational database.

The sanitized file is staged as the tracked `db.sqlite3` blob using explicit Git
object/index operations. The working-tree `db.sqlite3` remains the operational
copy, intentionally different from Git. Ignored backup files are not staged.

## Tests and scope

**713 full-suite tests plus 8 session-baseline regression tests passed**, using an
isolated in-memory database and temporary media. Django system checks passed;
migration consistency dry-run found no changes. Dependency pins and `pip check`
passed. Actual interpreter: `.venv/bin/python`, Python 3.13.1, Django 6.0.7,
pypdf 6.16.1. The governance-documented `venv/py313/bin/python` remains absent;
the already verified milestone environment was retained without installs/upgrades.

Files: [validation report](checkpoint_report.json), [test log](tests_and_checks.txt),
[development restoration check](development_restore_check.json),
[Matrix reconciliation](matrix_receipt_revalidation.json) and [inventory](artifact_inventory.json).
The existing execution completion report remains unchanged. This checkpoint makes
no application, contract, schema, candidate-classification or correspondence changes.

Git whitespace inspection flags CRLF/whitespace in six original retained CSV/HTML artifacts. All match their accepted hashes and are deliberately preserved byte-for-byte. The new checkpoint documents/code pass whitespace checks; see `retained_source_whitespace_assessment.json`. No canonical or contract validation failure remains.
