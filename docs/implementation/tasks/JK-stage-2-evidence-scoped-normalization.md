# Jeep Wrangler JK Stage 2 evidence-scoped normalization

Completed 2026-11-04 at the normalized-interpretation boundary. Stage 3 remains a separate approval.

The production rule admits the reviewed nine-assertion Stage 1 row from FCA US LLC form `74-383-3802 (9/17 143M)`. It validates publication and extraction provenance and matches the exact reviewed assertion content, including locations. It maps the base SPORT and Wrangler Unlimited evidence to `Unlimited Sport`, preserves native terms and references, and returns the eight existing ingestion concepts. The source set retains the JK designation for later correspondence review. No correspondence is resolved or published here.

Synthetic protocol fixtures exercise all approved Unlimited aliases, the early 3.8 L V6 and 2WD branches, two drivetrain-system designations, and invalid scope or conflicting facts. No retained reviewed 2007 or 2011 assertion set was available for production admission. Existing W1 body-ambiguous normalization remains in place.

Implementation files are `reference/ingestion/normalization/jeep.py` and `reference/tests/test_jeep_jk_normalization.py`. This record, CURRENT_STATE and the Unreleased changelog record verification. No schema, shared contract, Stage 1 extractor, candidate or import workflow changed.

## Verification

The following commands ran with `RIGARCHIVE_TEST_DB_PATH=:memory:` and the repository Python 3.13 environment.

```bash
venv/py313/bin/python -B manage.py test reference.tests.test_jeep_jk_normalization reference.tests.test_jeep_jk_unlimited_sport reference.tests.test_jeep_w1 --noinput
venv/py313/bin/python -B manage.py test reference.tests.test_jeep_jk_normalization reference.tests.test_jeep_jk_unlimited_sport reference.tests.test_jeep_w1 reference.tests.test_jeep_release_identity reference.tests.test_normalization reference.tests.test_ingestion_serialization reference.tests.test_candidate_construction reference.tests.test_generation_correspondence reference.tests.test_canonical_import_execution reference.tests.test_manufacturer_ingestion reference.tests.test_acquisition_adapters --noinput
venv/py313/bin/python -B manage.py check
venv/py313/bin/python -B manage.py makemigrations --check --dry-run
git diff --check
```

Focused selection passed 27 tests. The broader selection passed 141 tests with zero failures or skips. Both selections ran the authentic retained-source test. System checks found zero issues, migration consistency reported no changes, and whitespace checks passed.

The database SHA-256 remained `09754fa3a988df19c984e5a492d4e869ae3f0921ee44517fe7f1113df417e873` with no SQLite sidecars. The 71-file storage inventory digest remained `8d6b57c24dd9ca302b83eb1a36a356614fbf8b84586d0c721d228d85f5e5ff79`. Pre-existing Git work was preserved. No files were staged, committed or pushed.

The existing correspondence pins the exact W1 two-door evidence set. Stage 3 must independently review whether the Unlimited evidence can carry the existing exact JK binding or needs a new reviewed binding.
