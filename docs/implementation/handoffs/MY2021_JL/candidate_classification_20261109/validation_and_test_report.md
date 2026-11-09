# MY2021 JL validation and test report

Created: 2026-11-09
Status: Draft — final candidate completeness blocked for JL21-70

## Artifact results

`validation_results.json` records the actual outcome: **73 valid bases, 88 approved
field decisions, 70 approved contract adjudications, 70 candidate revisions and
73 valid current Candidate 2.1.0 artifacts**. Both indices retain 23 two-door and
50 four-door offerings, all 24 approved body/trim names and all 24 earlier-only
combinations. The 73 current candidate identities are unique.

All base/current content digests, serialized-file hashes, source bytes and
assertion references validate. The approved records reference exact retained bases;
the projection validator reproduces each current revision. Candidate/source-set
serialization and adjudication dictionary round trips pass. All 88 separately
indexed field records match their approved contract claims. No approval extends
beyond the exact US MY2021 scope, and no duplicate adjudication is present.

**Complete five-field identities: 72 passed, one failed.** JL21-70 / ESG has
`fuel_type = null`; `candidate_powertrain(..., complete=True, verify_bytes=True)`
raises `Missing evidenced powertrain attribute: fuel_type.` Its approved
aspiration/nonhybrid claims passed. No complete-tuple result is claimed for this
candidate. All three ECX tuples remain complete and unchanged without adjudication.

Sport RHD is preserved outside candidate construction, with CLASS-075 deferred.
All original discovery/review/preflight file hashes match the preservation
baseline. Live `db.sqlite3` SHA-256 matches before/after and the owner-review
baseline: `ec1eb2adb8becf62a6d8ef18e5ae2dee37d5049620faaaeec51ab8c69b0ee4f9`.
The retained owner-review tests also verify read-only SQLite integrity, foreign
keys and original record counts. No live ORM writes or import planning occurred.

## Actual environment

`.venv/bin/python` is Python **3.13.1**, not the earlier documented 3.13.2.
`venv/py313/bin/python` is absent. Installed **Django 6.0.7** and **pypdf 6.16.1**
match the two exact pins in `requirements.txt`. `pip check` returned no broken
requirements; its only warning concerned a disabled nonwritable user cache.
No environment substitution, install or upgrade was performed.

## Executed verification

| Check | Actual result | Retained log |
| --- | --- | --- |
| Artifact base stage | 73 bases passed | `base_build_resume2_log.txt`, `base_validation.json` |
| Classification application | 88 decisions / 70 revisions | `approval_resume_log.txt`, `cli_audit/` |
| Final artifact audit | Contracts/lineage/round trips pass; 72/73 complete | `validation_log.txt`, `validation_results.json` |
| Full Django project suite | 713 tests passed | `full_project_tests.txt` |
| Focused suite | 65 tests passed | `focused_tests.txt` |
| Original owner-review suite | 8 tests passed | `owner_review_tests.txt` |
| Django check | No issues | `django_check.txt` |
| Migration consistency | No changes detected | `migration_check.txt` |
| Dependency consistency | No broken requirements | `dependency_check.txt` |

Commands from the repository root:

```text
.venv/bin/python -B docs/implementation/handoffs/MY2021_JL/candidate_classification_20261109/build_artifacts.py base
.venv/bin/python -B docs/implementation/handoffs/MY2021_JL/candidate_classification_20261109/build_artifacts.py approve
.venv/bin/python -B docs/implementation/handoffs/MY2021_JL/candidate_classification_20261109/build_artifacts.py validate
RIGARCHIVE_TEST_DB_PATH=:memory: .venv/bin/python -B manage.py test reference.tests.test_candidate_construction reference.tests.test_classification_adjudication reference.tests.test_structured_powertrain --noinput
.venv/bin/python -B docs/implementation/handoffs/MY2021_JL/owner_review_20261108/validate_review.py
RIGARCHIVE_TEST_DB_PATH=:memory: .venv/bin/python -B manage.py check
RIGARCHIVE_TEST_DB_PATH=:memory: .venv/bin/python -B manage.py makemigrations --check --dry-run
.venv/bin/python -B -m pip check
```

For the full project suite, a Python launcher set
`DJANGO_SETTINGS_MODULE=config.settings` and `RIGARCHIVE_TEST_DB_PATH=:memory:`,
assigned `settings.MEDIA_ROOT` to a new `TemporaryDirectory` under this dated
checkpoint, then called
`execute_from_command_line(['manage.py', 'test', '--noinput'])`.
All 713 tests passed and the temporary media directory was cleaned up by its
context manager. Tests used isolated databases; no production migrations ran.

The first artifact build halted on serialized source-assertion ordering; a
subsequent build exposed QOP 22L being read as displacement in a full table
segment. These were resolved in the artifact driver by comparing stable assertion
IDs and, where necessary, faithfully isolating the engine column. Full source
segments remain retained. The first approval setup halted because the existing
contract requires a nonempty supporting-document list even when those documents
already occur in the base. Explicit technical supporting documents resolved it
before any approval CLI ran. Original attempt logs are retained. No application
code or validation rule was relaxed, and existing artifacts were never overwritten.

The overall task remains **incomplete**, despite passing project tests, until
the JL21-70 fuel normalization can pass the approved evidence path. Separate
authorization is needed for applicable manufacturer fuel evidence or a bounded
validator correction. Generation-correspondence work has not begun.
