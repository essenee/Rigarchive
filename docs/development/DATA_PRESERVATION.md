# Development Data Preservation & Recovery Guide

## SQLite development and public-staging deployment policy

Approved 2026-10-27. This is a temporary development/public-staging workflow, not a permanent production deployment design.

### Authority and intentional Git tracking

- `db.sqlite3` is intentionally tracked in Git during development and public staging.
- The local development database is authoritative for authored vehicle reference data. Database changes may be deliberately committed and pushed to GitHub; PythonAnywhere staging receives those database snapshots through the existing Git deployment workflow.
- Staging is not an independent authoritative source of vehicle reference data.
- Database changes must not be included automatically in unrelated code commits. Select and review database snapshots deliberately and separately from unrelated code changes.
- Codex must preserve the local development database unless explicitly authorized otherwise. This policy is not authorization for Codex to write, replace, stage, commit, push, stash or deploy a database; task-specific authorization and existing safeguards remain applicable.

### Deployment precautions

1. Check staging for local database modifications before deployment.
2. Quiesce database access before replacing a live SQLite database.
3. Preserve a recoverable backup or stash of staging database changes before replacement. A stash is a deliberate operator action; this policy does not authorize Codex to create one automatically.
4. Do not automatically reapply an old staging database stash after pulling a new snapshot. Preserve it for deliberate review rather than overwriting the new authoritative snapshot.
5. Account for SQLite WAL files and ensure database snapshots are consistent. A copy of `db.sqlite3` alone is not necessarily a complete snapshot when changes remain in WAL; do not treat live WAL/journal/shared-memory sidecars as ordinary Git deployment assets.
6. Never commit real credentials, private user data, session secrets or other sensitive information to the public repository. Tracking the database file does not waive this restriction: review the complete snapshot, not only vehicle reference tables, before publication.

### Future production boundary

Before accepting real production users or independently authored production data, replace database-file deployment with an approved data-promotion mechanism that preserves production operational records. Designing or implementing that mechanism is outside this documentation task.

This policy changes neither actual database tracking configuration nor deployment infrastructure. It does not resolve the historical RA-EXP-02B-1 database/IDE fingerprint discrepancy. Task-local preservation evidence remains limited to its recorded interval.

## Overview

RigArchive implements a dual-layer preservation strategy for local development data:
1. **Layer 1: Physical Recovery Snapshot**: Complete physical SQLite recovery copy using `VACUUM INTO`.
2. **Layer 2: Logical Data Export**: Portable JSON serialization using Django `dumpdata --natural-foreign`.

All preservation artifacts are stored locally under `backups/` (`backups/snapshots/` and `backups/logical/`), which is excluded from Git tracking.

> [!WARNING]
> **Local Storage Boundary**: `backups/` is stored in your local repository working directory. Local backups protect against accidental database resets, local migration errors, and experimental database work. They do **not** protect against hard drive hardware failure or total working directory deletion.

---

## Developer Preservation Commands

Environment verified 2026-11-09: `.venv/bin/python`, Python 3.13.1, Django 6.0.7 (pypdf 6.16.1). The older `venv/py313` directory is absent in this checkout. Protected governance files still describe that older environment; this guide records the actual local environment under the current maintenance task's explicit verification requirement. Historical task logs and deployment-specific environments are not rewritten.

Run every example from `/Users/cosmo/dev/Rigarchive` (or the root of your own checkout). No activation is required when using the explicit interpreter path. Optional activation is `source .venv/bin/activate`; then use `python manage.py ...`. Do not install or rebuild an environment as part of preservation.

For normal operational backup/export, `RIGARCHIVE_TEST_DB_PATH` must be unset: settings otherwise select that database instead of `db.sqlite3`. Check the intended target before running commands. `verify_dev_data` sets this variable itself for its isolated subprocesses. No other environment variable is required by these commands. `PYTHONDONTWRITEBYTECODE=1` (or Python's `-B`) optionally suppresses bytecode caches.

These are operator instructions, not authorization to execute database-changing operations. Obtain explicit authorization identifying affected records and risks before any operation capable of modifying the development database; reset/rebuild requires separate explicit authorization. Quiesce application writers and retain SQLite sidecars with the database until a consistent verified backup exists.

### 1. Take a Physical Database Snapshot (Layer 1)
Use before running risky migrations, experimental database work, or destructive database commands:

```bash
.venv/bin/python manage.py snapshot_db
```

* **Output**: `backups/snapshots/db_snapshot_<YYYYMMDD_HHMMSS>.sqlite3`
* **Verification**: Executes SQLite `PRAGMA integrity_check`, verifies table presence, and checks row counts automatically.

### 2. Export Logical Data (Layer 2)
Use before database resets, clean migration rebuilds, or structural branch transitions:

```bash
.venv/bin/python manage.py export_dev_data
```

* **Output**: `backups/logical/dev_data_<YYYYMMDD_HHMMSS>.json`
* **Content**: The command explicitly exports only `accounts.User`, `auth.Group`, `reference.Manufacturer`, `reference.VehicleModel`, `reference.Generation`, `reference.VehicleDefinition`, and `observation.Observation`. It excludes `contenttypes`, `auth.Permission` and sessions. It does **not** export all current reference models, receipts, correspondences, specification models or measurements, so it cannot alone reconstruct the current project. Retain a verified physical recovery snapshot and evidence artifacts.
* **Privacy**: Physical backups contain operational authentication/session data; logical exports include user/password fields and private observations even though sessions are excluded. Keep both private and ignored. Neither is a sanitized Git checkpoint or suitable for public packaging without separate review and authorized sanitization of a copy.

### 3. Verify a Logical Export
Verify a logical JSON export against an isolated OS temporary database without affecting `db.sqlite3`. Set `fixture` to an actual retained export filename; do not paste angle-bracket placeholders into the shell:

```bash
fixture="backups/logical/dev_data_YYYYMMDD_HHMMSS.json" # replace with the actual filename
test -f "$fixture"
```

```bash
.venv/bin/python manage.py verify_dev_data --fixture "$fixture"
```

* **Verification**: Migrates a fresh database in the OS temporary directory, restores the fixture via `loaddata`, and runs the implemented model/relationship invariants. This checks the exported subset, not completeness of all current canonical/provenance data. Physical snapshot verification likewise checks integrity and six configured table counts, not every current table.

---

## Clean Database Rebuild Workflow

This destructive workflow requires separate explicit authorization to delete/recreate `db.sqlite3`, and authorization for migrations/restoration. It loses records outside the logical export's seven-model subset; use a verified complete physical backup when full current-state recovery is required. Stop if there are active writers or WAL/journal/shared-memory sidecars; do not remove the database independently of its sidecars.

Only after those gates, run from the repository root. First unset any test override. Retain the exact export path emitted by step 1 in `fixture` below and verify it before deletion. The verification command restores into a temporary database; it does not independently verify the rebuilt operational file.

```bash
unset RIGARCHIVE_TEST_DB_PATH

# 1. Export current logical data
.venv/bin/python manage.py export_dev_data

# 2. Take a physical recovery snapshot as fallback
.venv/bin/python manage.py snapshot_db

# 3. Select and verify the exact export BEFORE separately authorized deletion
fixture="backups/logical/dev_data_YYYYMMDD_HHMMSS.json" # replace with actual output
# Execute each following step only if the preceding step succeeds.
test -f "$fixture"
.venv/bin/python manage.py verify_dev_data --fixture "$fixture"
# After explicit reset authorization and all preservation gates:
rm db.sqlite3

# 4. Re-run all Django migrations from scratch
.venv/bin/python manage.py migrate

# 5. Restore preserved logical data
.venv/bin/python manage.py loaddata "$fixture"

# 6. Recheck export restoration in an isolated database; review live counts separately
.venv/bin/python manage.py verify_dev_data --fixture "$fixture"
```


## Local checks and tests

Run from the repository root. These invocations select an isolated in-memory SQLite database; do not export this override into the operational backup shell:

```bash
RIGARCHIVE_TEST_DB_PATH=:memory: .venv/bin/python -B manage.py check
RIGARCHIVE_TEST_DB_PATH=:memory: .venv/bin/python -B manage.py makemigrations --check --dry-run
RIGARCHIVE_TEST_DB_PATH=:memory: .venv/bin/python -B manage.py test --noinput
```

Django tests must retain isolated test databases and temporary media/acquisition storage. Follow the task-specific isolation harness where filesystem fixtures require it; database isolation alone does not isolate media. No development migration is implied by these checks.
