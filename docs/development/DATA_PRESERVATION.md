# Development Data Preservation & Recovery Guide

## Overview

RigArchive implements a dual-layer preservation strategy for local development data:
1. **Layer 1: Physical Recovery Snapshot**: Complete physical SQLite recovery copy using `VACUUM INTO`.
2. **Layer 2: Logical Data Export**: Portable JSON serialization using Django `dumpdata --natural-foreign`.

All preservation artifacts are stored locally under `backups/` (`backups/snapshots/` and `backups/logical/`), which is excluded from Git tracking.

> [!WARNING]
> **Local Storage Boundary**: `backups/` is stored in your local repository working directory. Local backups protect against accidental database resets, local migration errors, and experimental database work. They do **not** protect against hard drive hardware failure or total working directory deletion.

---

## Developer Preservation Commands

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
* **Content**: Exports `accounts.User`, `auth.Group`, `reference` models, and `observation.Observation`. Excludes `contenttypes` and `auth.Permission` (re-generated via `post_migrate`).

### 3. Verify a Logical Export
Verify a logical JSON export against an isolated OS temporary database without affecting `db.sqlite3`:

```bash
.venv/bin/python manage.py verify_dev_data --fixture backups/logical/dev_data_<timestamp>.json
```

* **Verification**: Migrates a fresh temporary database in `/tmp`, restores the fixture via `loaddata`, and asserts 11-point actual data invariants.

---

## Clean Database Rebuild Workflow

To rebuild `db.sqlite3` from zero and restore your preserved logical data:

```bash
# 1. Export current logical data
.venv/bin/python manage.py export_dev_data

# 2. Take a physical recovery snapshot as fallback
.venv/bin/python manage.py snapshot_db

# 3. Reset/delete physical db.sqlite3
rm db.sqlite3

# 4. Re-run all Django migrations from scratch
.venv/bin/python manage.py migrate

# 5. Restore preserved logical data
.venv/bin/python manage.py loaddata backups/logical/dev_data_<timestamp>.json

# 6. Verify restored database
.venv/bin/python manage.py verify_dev_data --fixture backups/logical/dev_data_<timestamp>.json
```
