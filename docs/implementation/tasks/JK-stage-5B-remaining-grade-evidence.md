# Jeep Wrangler JK Stage 5B remaining-grade evidence

Completed 2026-11-05 at the extraction and normalization boundary. Stage 5C awaits separate approval.

The four authentic MY2018 US JK evidence sets each provide nine assertions and eight interpretations. PDF page 9 supplies the grade-specific standard Pentastar V6 and Command-Trac or Rock-Trac evidence and the body qualifications. Pages 3, 6–7 and 11 corroborate the manufacturer Unlimited names and body scope. The common reviewed publication gate uses retained FCA US LLC form `74-383-3802 (9/17 143M)` and SHA-256 `800f8ecd964e4df584cf6c382216f8401c5b273b85befa686faf93f92841a158`. Each production normalization admission binds the exact assertion IDs, native values and locations. The existing mapper produces Sahara, Unlimited Sahara, Rubicon and Unlimited Rubicon with 3.6 L, six cylinders and 4WD. Stage 1 assertion content and W1 behavior remain intact.

Changed `reference/ingestion/acquisition/jeep.py` and `reference/ingestion/normalization/jeep.py`. Added `reference/tests/test_jeep_jk_remaining_grades.py`. Updated this record, current state and Unreleased changelog. No models, migrations, shared contracts, candidate assembly, planning, resolver or execution services changed. Stage 3 regressions exercised downstream contracts only in isolated tests.

## Verification

Used repository Python 3.13 and `RIGARCHIVE_TEST_DB_PATH=:memory:`.

```bash
venv/py313/bin/python -B manage.py test reference.tests.test_jeep_jk_remaining_grades reference.tests.test_jeep_jk_unlimited_sport reference.tests.test_jeep_jk_normalization reference.tests.test_jeep_w1 --noinput
venv/py313/bin/python -B manage.py test reference.tests.test_jeep_jk_remaining_grades reference.tests.test_jeep_jk_unlimited_sport reference.tests.test_jeep_jk_normalization reference.tests.test_jeep_w1 reference.tests.test_jeep_release_identity reference.tests.test_jeep_jk_stage3 reference.tests.test_normalization reference.tests.test_ingestion_serialization reference.tests.test_candidate_construction --noinput
venv/py313/bin/python -B manage.py check
venv/py313/bin/python -B manage.py makemigrations --check --dry-run
git diff --check
```

The focused selection passed 31 tests. The broader selection passed 83 tests with zero failures or skips. System check passed, migration dry run detected no changes, and whitespace checks passed.

The Stage 5B database SHA-256 was unchanged at `608ed0a986aee4761c2f65cd688cac493bf9d20009289a1d235597e544e2b4fc`, with no sidecars. Compared with the retained pre-Stage 4C snapshot and closing reconciliation, the current schema and canonical delta match the authorized creation and receipt. PK 714 is unchanged from the snapshot. PK 716 and the recorded fields of receipt 2759 match the Stage 4C closing artifact. Apart from the expected creation, receipt and sequence increments, the logical comparison found one changed existing django_session row, with the session key set unchanged. The exact cause and timing of the file hash drift remain unestablished. All 71 retained storage files matched the initial inventory. No Git staging, commits or pushes occurred.
