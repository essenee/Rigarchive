# MY2021 JL fuel completion verification

Created: 2026-11-09
Status: Accepted

## Environment

Exact interpreter: `/Users/cosmo/dev/Rigarchive/.venv/bin/python`.
Python **3.13.1**, Django **6.0.7**, pypdf **6.16.1**. The two installed dependency
versions match `requirements.txt`; `pip check` reports no broken requirements.
Its nonwritable user-cache warning does not affect dependency validation. No
interpreter substitution, dependency installation or upgrade occurred.

## Executed commands and results

From `/Users/cosmo/dev/Rigarchive`:

```text
.venv/bin/python -B docs/implementation/handoffs/MY2021_JL/fuel_completion_20261109/resolve_fuel.py apply
.venv/bin/python -B docs/implementation/handoffs/MY2021_JL/fuel_completion_20261109/resolve_fuel.py validate
RIGARCHIVE_TEST_DB_PATH=:memory: .venv/bin/python -B manage.py test reference.tests.test_candidate_construction reference.tests.test_classification_adjudication reference.tests.test_structured_powertrain --noinput
RIGARCHIVE_TEST_DB_PATH=:memory: .venv/bin/python -B manage.py check
RIGARCHIVE_TEST_DB_PATH=:memory: .venv/bin/python -B manage.py makemigrations --check --dry-run
.venv/bin/python -B -m pip check
```

The full project suite was launched with the same interpreter and
`RIGARCHIVE_TEST_DB_PATH=:memory:`. The launcher set
`DJANGO_SETTINGS_MODULE=config.settings`, assigned `settings.MEDIA_ROOT` to a new
`TemporaryDirectory` under this checkpoint, and called
`execute_from_command_line(['manage.py', 'test', '--noinput'])`. The temporary
media context cleaned up its own new files. Database creation/migrations performed
by Django tests were confined to isolated test resources, not the live database.

| Verification | Result | Original log |
| --- | --- | --- |
| Existing adjudication CLI | One approved cumulative finding and one new candidate revision | `application_log.txt`, `adjudication_cli.txt` |
| Final artifact audit | 73/73 complete; 23 two-door / 50 four-door; 24 labels | `validation_log.txt`, `validation_results.json` |
| Full project suite | 713 tests passed | `full_project_tests.txt` |
| Focused candidate/classification/powertrain suite | 65 tests passed | `focused_tests.txt` |
| Django system checks | No issues | `django_check.txt` |
| Migration consistency | No changes detected | `migration_check.txt` |
| Dependency consistency | No broken requirements | `dependency_check.txt` |

Focused tests overlap the full project suite; counts are not additive. No test was
altered to obtain these results. No application behavior, schema or contract changed.

## Data and evidence validation

The artifact audit uses existing Candidate 2.1.0, adjudication 1.1 and complete
powertrain validators with byte verification. It verifies all semantic digests,
serialized-file hashes, candidate/source applicability, approved-projection
reproduction, candidate uniqueness and serialization round trips. Every original
approved field claim is compared exactly to the active approval, including the
two unchanged ESG carry-forwards. All 72 other index entries and artifacts are
unchanged. The new 392 tuple differs only in `fuel_type`, which is now gasoline.

The original failure was reproduced before approval: complete validation failed
on missing fuel_type, and the unchanged direct-source predicate returned false
for both the original premium-octane line and the full manufacturer source page.
After the owner-approved human finding, complete validation passes through the
existing human-provenance consumer. The direct-source predicate remains unchanged
and is not bypassed by rewriting a manufacturer assertion.

All preexisting MY2021 handoff files, the original approved artifacts, source
bytes, and inspected application/accepted contract files match the preservation
baseline. The live database SHA-256 before/after is
`ec1eb2adb8becf62a6d8ef18e5ae2dee37d5049620faaaeec51ab8c69b0ee4f9`.
No canonical planning or database write was performed. Sport RHD and CLASS-075
remain preserved/deferred, and ECX direct technical provenance is unchanged.

No unresolved consumer classification or validation issue remains. Generation
correspondence preparation/publication and all subsequent Matrix/import work
remain outside this authorization. No commit or push.
