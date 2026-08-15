# RA-009 — Development Data Preservation and Recovery Implementation

## Purpose

Implement the approved RA-008 dual-layer development data preservation and recovery architecture to safeguard authored development data, enable clean database rebuilds from migrations, provide automated restoration verification, and safely transition `db.sqlite3` and compiled `.pyc` files out of Git tracking.

## Governing Architecture

Governed by the approved [RA-008 Architecture Document](file:///Users/esse/dev/Rigarchive/docs/architecture/designs/RA-008-Development-Data-Preservation-Architecture.md).

## Scope

### Included
- Create `backups/` directory structure and `backups/.gitignore` (`*` / `!.gitignore`).
- Add `backups/` entry to root `.gitignore`.
- Update `config/settings.py` to support `RIGARCHIVE_TEST_DB_PATH` environment variable override for isolated test database execution.
- Implement management command `snapshot_db` (`core/management/commands/snapshot_db.py`) executing Layer 1 physical SQLite `VACUUM INTO` snapshots with `PRAGMA integrity_check`, table existence, and row count verification.
- Implement management command `export_dev_data` (`core/management/commands/export_dev_data.py`) executing Layer 2 natural-key JSON exports of authored models (`accounts.User`, `auth.Group`, `reference` models, `observation.Observation`) excluding reconstructable framework data (`contenttypes`, `auth.Permission`, `sessions`).
- Implement management command `verify_dev_data` (`core/management/commands/verify_dev_data.py`) executing isolated restoration verification of logical JSON fixtures against an OS temporary SQLite database in `/tmp`.
- Implement `DataPreservationTestCase` in `core/tests.py` verifying preservation tooling and authorization reconnection on synthetic test datasets.
- Safely untrack `db.sqlite3` and all compiled `.pyc` files from Git tracking while retaining local development files.
- Create developer guide `docs/development/DATA_PRESERVATION.md`.
- Update `docs/implementation/CURRENT_STATE.md` and `CHANGELOG.md`.

### Not Included
- Production disaster recovery or cloud object storage integration (S3/R2).
- Automated background backup daemons.
- Generalized schema transformation engines across incompatible schemas.
- End-user export/import interfaces.
- Custom `natural_key()` implementations on domain models or adding UUIDs to `User`.

## Completion Record

Status: Completed

Completion date: 2026-08-15

Files created:
- `backups/.gitignore`
- `core/management/__init__.py`
- `core/management/commands/__init__.py`
- `core/management/commands/snapshot_db.py`
- `core/management/commands/export_dev_data.py`
- `core/management/commands/verify_dev_data.py`
- `docs/development/DATA_PRESERVATION.md`
- `docs/implementation/tasks/RA-009-development-data-preservation-implementation.md`

Files modified:
- `.gitignore`
- `config/settings.py`
- `core/tests.py`
- `docs/implementation/CURRENT_STATE.md`
- `CHANGELOG.md`

Migrations created:
- None (preservation tooling utilizes existing model definitions and migrations).

Verification results:
- `.venv/bin/python manage.py check`: Passed (`System check identified no issues (0 silenced)`).
- `.venv/bin/python manage.py makemigrations --check`: Passed (`No changes detected`).
- `.venv/bin/python manage.py migrate --check`: Passed (`No unapplied migrations`).
- `.venv/bin/python manage.py test`: Passed (`Ran 34 tests in 3.402s — OK`).
- Physical snapshot `snapshot_db`: Passed (`PRAGMA integrity_check` ok, table presence verified, row counts matched).
- Logical export `export_dev_data`: Generated 4,363 bytes JSON fixture (`dev_data_20260815_142629.json` containing 9 serialized model instances).
- Isolated restoration verification `verify_dev_data`: Passed 100% cleanly on isolated `/tmp` database (all 2 Users, 1 Manufacturer, 1 VehicleModel, 1 Generation, 1 VehicleDefinition, and 3 Observations restored and verified).
- Git tracking transition: `db.sqlite3` and all 26 compiled `.pyc` / `__pycache__` files across `accounts`, `config`, and `reference` untracked from Git index while retaining local development files on disk. Zero `.pyc` or `__pycache__` files remain tracked in Git.

Documentation updated:
- `docs/development/DATA_PRESERVATION.md`
- `docs/implementation/CURRENT_STATE.md`
- `CHANGELOG.md`
- `docs/implementation/tasks/RA-009-development-data-preservation-implementation.md`
