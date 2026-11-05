# Jeep Wrangler JK Stage 3 offline integration

Completed 2026-11-04 at the import planning and review boundary. Stage 4 awaits separate approval.

- Authentic Stage 1 assertions and Stage 2 interpretations produce a valid Candidate v2 for 2018 US Jeep Wrangler JK Unlimited Sport, 3.6L V6, 4WD. The eight normalized interpretations reference only `pdf-page-10-sport-unlimited`.
- The retained W1 correspondence review payload and hash matched the existing database revision. In the isolated fixture, the Unlimited evidence alone fails the exact-document binding despite the shared PDF hash. The original W1 assertion JSON orders its last two assertions differently from the reviewed payload. Assembling the unchanged assertions in reviewed order satisfies the binding. No two-door normalized interpretations are added. The complete generation projection contains both JK assertions.
- The tested plan resolves to JK 31 and produces `eligible / create / source_established_grade`, slug `2018-unlimited-sport-36l-v6-4wd-us`, and namespace snapshot count 1. A seeded exact target yields `no_op_exact_match`.
- A synthetic exact Unlimited correspondence works when it is the sole current applicable chain. With the W1 chain also present, both exact documents are required. Conflicting JK/JL targets, missing evidence, a changed assertion set, withdrawal and year-only overlap block. The preferred Stage 4 path carries the existing W1 evidence in reviewed order.
- Manifest 2.0 round trips and reconstructs the same plan. Tampering with a stale digest fails parsing. Rehashing a changed outer Generation ID can pass parsing but fails read-only parent binding revalidation. Revalidation also rejects stale or withdrawn correspondence.
- The planner considers only active records when checking the target slug. The existing model constraint detects an inactive collision during read-only preflight. Stage 4 must check every target slug regardless of active status before presenting a plan for review.

Only `reference/tests/test_jeep_jk_stage3.py` and the implementation records changed. No production code, schema, evidence, or reviewed artifacts changed. Test correspondence rows were seeded directly in the isolated database. No publisher, canonical executor or receipt workflow was invoked.

## Verification

Commands used `RIGARCHIVE_TEST_DB_PATH=:memory:` and the repository Python 3.13 environment.

```bash
venv/py313/bin/python -B manage.py test reference.tests.test_jeep_jk_stage3 --noinput
venv/py313/bin/python -B manage.py test reference.tests.test_jeep_jk_stage3 reference.tests.test_jeep_jk_normalization reference.tests.test_jeep_jk_unlimited_sport reference.tests.test_jeep_w1 reference.tests.test_jeep_release_identity reference.tests.test_candidate_construction reference.tests.test_normalization reference.tests.test_ingestion_serialization reference.tests.test_generation_correspondence.CorrespondenceTests.test_missing_explicit_and_unidentified_overlap reference.tests.test_generation_correspondence.CorrespondenceTests.test_two_documents_from_same_publisher_keep_local_ids_separate reference.tests.test_canonical_import.CanonicalImportTestCase.test_planning_executes_zero_db_writes reference.tests.test_canonical_import.CanonicalImportTestCase.test_trim_string_inequality_alone_flags_review reference.tests.test_adjudication_workflow.AdjudicationWorkflowTests.test_adjudication_planning_trust_boundary reference.tests.test_adjudication_workflow.AdjudicationWorkflowTests.test_manifest_v1_1_and_v1_0_compatibility --noinput
venv/py313/bin/python -B manage.py check
venv/py313/bin/python -B manage.py makemigrations --check --dry-run
git diff --check
```

Final results were 7 focused tests and 85 combined tests passed, zero failures or skips. The combined run selected planning and contract regressions that avoid execution and publication. Earlier runs corrected a fixture deserialization type error, exposed the W1 order mismatch, and established that outer Generation mismatch rejection occurs during resolution revalidation. Django system check passed and migration consistency reported no changes.

Database SHA-256 remained `09754fa3a988df19c984e5a492d4e869ae3f0921ee44517fe7f1113df417e873` with no SQLite sidecars. The 71-file storage inventory digest remained `8d6b57c24dd9ca302b83eb1a36a356614fbf8b84586d0c721d228d85f5e5ff79`. No Git staging or commit occurred.
