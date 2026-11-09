# MY2021 correspondence preparation verification

Created: 2026-11-09
Status: Accepted — preparation verified; proposals remain unpublished

## Environment and executed checks

Interpreter: `/Users/cosmo/dev/Rigarchive/.venv/bin/python`, **Python 3.13.1**.
Installed Django **6.0.7** and pypdf **6.16.1** match `requirements.txt`.
`pip check` reports no broken requirements; its nonwritable user-cache warning
does not affect dependency consistency. No environment substitution or dependency
installation/upgrade occurred.

The preparation driver was run from the repository root:

```text
.venv/bin/python -B docs/implementation/handoffs/MY2021_JL/generation_correspondence_review_20261109/prepare_review.py
```

Live Django access used SQLite URI `mode=ro` and `PRAGMA query_only=ON` throughout.
It validated contracts, bytes, published state and target parents; prepared only
local proposals/documents; and simulated the real resolver with unsaved proposed
records at the revision-lookup boundary. It never called correspondence
publication, model save, receipt creation, canonical planning or import services.

Focused tests used the same interpreter with
`RIGARCHIVE_TEST_DB_PATH=:memory:`. A Python launcher set
`DJANGO_SETTINGS_MODULE=config.settings`, assigned `settings.MEDIA_ROOT` to a
new temporary directory under this checkpoint, and called Django's command runner
with:

```text
manage.py test reference.tests.test_generation_correspondence reference.tests.test_generation_projection_completeness reference.tests.test_candidate_construction reference.tests.test_classification_adjudication reference.tests.test_structured_powertrain reference.tests.test_ingestion_serialization --noinput
```

The temporary media context removed only its own new test files. Other checks:

```text
RIGARCHIVE_TEST_DB_PATH=:memory: .venv/bin/python -B manage.py check
RIGARCHIVE_TEST_DB_PATH=:memory: .venv/bin/python -B manage.py makemigrations --check --dry-run
.venv/bin/python -B -m pip check
git diff --check
```

| Verification | Actual result | Record |
| --- | --- | --- |
| Fresh database/target state | 861 definitions / 2,980 receipts / 64 correspondences; active JL32/expected UUID | `repository_and_database_state.json` |
| Prior publication integrity | All 64 payloads, model contracts and evidence bytes valid | `existing_correspondence_reuse_assessment.json` |
| Current candidates | 73 complete; exact 23/50 distribution and 24 labels | `validation_results.json` |
| Proposal contracts/model validation/round trips | 95 unique review artifacts pass | `new_correspondence_proposal_index.json` |
| Exact selector compatibility | One existing shared document for each of 95 keys; no revisions needed | `shared_selector_index.json` |
| Existing-only resolution | 0/73 currently covered; all fail for missing MY2021 mappings | `resolution_simulation_report.json` |
| Combined proposed-state resolution | 73/73 resolve only to PK32/expected UUID | `candidate_resolution_index.json` |
| Missing-proposal necessity controls | 95/95 rejected | `resolution_simulation_report.json` |
| Non-exact-selector controls | 95/95 rejected | `resolution_simulation_report.json` |
| Duplicate keys / conflicts / unmatched proposed-state keys | 0 / 0 / 0 | `validation_results.json` |
| Focused tests | 125 passed | `focused_tests.txt` |
| Django checks | No issues | `django_check.txt` |
| Migration consistency | No changes detected; none applied | `migration_check.txt` |
| Dependencies | No broken requirements | `dependency_check.txt` |

The full project suite was not rerun for this artifact-only preparation task.
Relevant resolver/projection, candidate/approval and serialization tests were run;
no test, application code or accepted contract was changed.

## Preservation and authority

All latest-candidate file/content hashes match the fuel-completion index. All 88
earlier claims match their original approved records and active projections;
the later 392 gasoline revision/digest is unchanged. ECX direct technical evidence
is unchanged. RHD/CLASS-075 remain outside consumer resolution and unmodified.
All 950 preexisting MY2021 handoff files and inspected application/contract files
match the execution baseline. Historical publication artifacts remain unchanged.

Before/after database SHA-256:
`ec1eb2adb8becf62a6d8ef18e5ae2dee37d5049620faaaeec51ab8c69b0ee4f9`.
Counts remain unchanged; SQLite integrity and foreign keys pass. The modified
database already present in Git status was preserved, not restored or staged.

Files created are confined to this dated review directory. Only targeted
`CURRENT_STATE.md` and `CHANGELOG.md` updates record the completed preparation
milestone. No material state discrepancy, failed check, scope deviation or
contract incompatibility remains. No candidate was revised. No publication,
publication receipt, canonical plan, Matrix certification, VehicleDefinition,
migration, backfill, commit or push occurred. Publication needs separate explicit
owner authorization and fresh pre-execution checks.
