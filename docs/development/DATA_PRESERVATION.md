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

Interpreter examples reconciled 2026-10-27 to the approved Python 3.13 environment. These are operator instructions, not commands executed or authorized by this documentation task. Operations capable of modifying the development database still require explicit authorization; reset/rebuild requires separate explicit authorization.

### 1. Take a Physical Database Snapshot (Layer 1)
Use before running risky migrations, experimental database work, or destructive database commands:

```bash
venv/py313/bin/python manage.py snapshot_db
```

* **Output**: `backups/snapshots/db_snapshot_<YYYYMMDD_HHMMSS>.sqlite3`
* **Verification**: Executes SQLite `PRAGMA integrity_check`, verifies table presence, and checks row counts automatically.

### 2. Export Logical Data (Layer 2)
Use before database resets, clean migration rebuilds, or structural branch transitions:

```bash
venv/py313/bin/python manage.py export_dev_data
```

* **Output**: `backups/logical/dev_data_<YYYYMMDD_HHMMSS>.json`
* **Content**: Exports `accounts.User`, `auth.Group`, `reference` models, and `observation.Observation`. Excludes `contenttypes` and `auth.Permission` (re-generated via `post_migrate`).

### 3. Verify a Logical Export
Verify a logical JSON export against an isolated OS temporary database without affecting `db.sqlite3`:

```bash
venv/py313/bin/python manage.py verify_dev_data --fixture backups/logical/dev_data_<timestamp>.json
```

* **Verification**: Migrates a fresh temporary database in `/tmp`, restores the fixture via `loaddata`, and asserts 11-point actual data invariants.

---

## Clean Database Rebuild Workflow

To rebuild `db.sqlite3` from zero and restore your preserved logical data:

```bash
# 1. Export current logical data
venv/py313/bin/python manage.py export_dev_data

# 2. Take a physical recovery snapshot as fallback
venv/py313/bin/python manage.py snapshot_db

# 3. Reset/delete physical db.sqlite3
rm db.sqlite3

# 4. Re-run all Django migrations from scratch
venv/py313/bin/python manage.py migrate

# 5. Restore preserved logical data
venv/py313/bin/python manage.py loaddata backups/logical/dev_data_<timestamp>.json

# 6. Verify restored database
venv/py313/bin/python manage.py verify_dev_data --fixture backups/logical/dev_data_<timestamp>.json
```
