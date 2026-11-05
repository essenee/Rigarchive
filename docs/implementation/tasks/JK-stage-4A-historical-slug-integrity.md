# Stage 4A historical slug collision integrity

Completed 2026-11-05. The Stage 3 fixture reproduced an eligible create for an inactive slug owner while the unconditional Generation/slug constraint rejected the target. The cause was an active-only occupancy query before eligibility classification.

The shared planner now checks every row in the resolved Generation at the target slug. It preserves no-op for an active exact match and ordinary slug conflict for an active mismatched record. An inactive or superseded owner yields requires review, flag review and slug conflict, with an explicit historical collision reason. Active semantic reconciliation and namespace snapshots keep their existing scope. The create transaction checks the same namespace and aborts stale plans on inactive occupancy before save. Existing active exact-match concurrency behavior and the database constraint remain in force.

Changed the shared planner and importer, canonical import regression tests, and Stage 3 regression expectation. Updated current state, changelog and this record. No migration or architecture decision was needed.

## Verification

Used repository Python 3.13 and `RIGARCHIVE_TEST_DB_PATH=:memory:`. Commands:

```bash
venv/py313/bin/python -B manage.py test reference.tests.test_jeep_jk_stage3.JKStage3Tests.test_exact_match_and_inactive_slug_collision --noinput
venv/py313/bin/python -B manage.py test reference.tests.test_canonical_import reference.tests.test_jeep_jk_stage3 --noinput
venv/py313/bin/python -B manage.py test reference.tests.test_canonical_import reference.tests.test_canonical_import_execution reference.tests.test_canonical_correction_lifecycle reference.tests.test_generation_correspondence reference.tests.test_adjudication_workflow reference.tests.test_jeep_jk_stage3 --noinput
venv/py313/bin/python -B manage.py check
venv/py313/bin/python -B manage.py makemigrations --check --dry-run
git diff --check
```

The initial one-test run reproduced the defect with the previous expected behavior. After correction, the focused run passed 37 tests and the combined run passed 111 tests with zero failures or skips. System check passed, migration dry run reported no changes, and whitespace checks passed. The regression covers inactive and superseded slug owners, late active and inactive occupancy, and an identical slug in another Generation. Execution tests used isolated synthetic state.

The persistent database SHA-256 remained `09754fa3a988df19c984e5a492d4e869ae3f0921ee44517fe7f1113df417e873`. SQLite sidecars were absent. All 71 storage files retained inventory digest `8d6b57c24dd9ca302b83eb1a36a356614fbf8b84586d0c721d228d85f5e5ff79`. Pre-existing Git work was preserved. No real import, staging, commit or push occurred.
