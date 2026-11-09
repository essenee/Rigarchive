# MY2021 correspondence publication verification

Created: 2026-11-09
Status: Accepted

## Runtime and commands

Exact interpreter: `/Users/cosmo/dev/Rigarchive/.venv/bin/python`, Python **3.13.1**.
Installed **Django 6.0.7** and **pypdf 6.16.1** match `requirements.txt`.
Dependency consistency passed. No environment substitution, install or upgrade.

From the repository root:

```text
RIGARCHIVE_TEST_DB_PATH=:memory: .venv/bin/python -B manage.py test docs.implementation.handoffs.MY2021_JL.generation_publication_20261109.test_atomic_publication --noinput
.venv/bin/python -B docs/implementation/handoffs/MY2021_JL/generation_publication_20261109/publish_atomic.py preflight
.venv/bin/python -B docs/implementation/handoffs/MY2021_JL/generation_publication_20261109/publish_atomic.py publish
.venv/bin/python -B docs/implementation/handoffs/MY2021_JL/generation_publication_20261109/publish_atomic.py verify
RIGARCHIVE_TEST_DB_PATH=:memory: .venv/bin/python -B manage.py check
RIGARCHIVE_TEST_DB_PATH=:memory: .venv/bin/python -B manage.py makemigrations --check --dry-run
.venv/bin/python -B -m pip check
git diff --check
```

The first pre-write snapshot stop and corrected repeat of the `publish` stage are
separately logged; no publication command ran in the stopped attempt. The same
original backup and exact 95 proposals were retained. See the README and
`prewrite_guard_diagnostic.json` for the resolved connection-conversion issue.

Preflight uses SQLite `mode=ro` and `PRAGMA query_only=ON`. It invokes the existing
Layer 1 `snapshot_db --output <new ignored backup>` command with a read-only source
URI; the command and independent all-table comparison verify the new backup. The
source database hash was unchanged throughout backup preparation.

The publication stage uses one normal live Django connection and one outer durable
transaction. It invokes the unchanged `publish_generation_correspondence` command
95 times in-process, with the owner's authorized affirmative confirmation, operator
`project_owner` and agent `codex`. The command's existing service still creates
each revision/receipt atomically, nested within the batch transaction. Every
non-created result or pre-commit verification error aborts the entire batch.
Independent post-commit verification uses read-only connections and no lookup mock.

The final focused suite used the same interpreter and
`RIGARCHIVE_TEST_DB_PATH=:memory:`. A Python launcher assigned `settings.MEDIA_ROOT`
to a new temporary directory under this dated checkpoint, then called Django's
command runner with:

```text
manage.py test reference.tests.test_generation_correspondence reference.tests.test_generation_projection_completeness reference.tests.test_candidate_construction reference.tests.test_classification_adjudication reference.tests.test_structured_powertrain reference.tests.test_ingestion_serialization docs.implementation.handoffs.MY2021_JL.generation_publication_20261109.test_atomic_publication --noinput
```

The media context cleaned up its own new test files. Test migrations ran only in
isolated databases; no live migration ran. No existing test or application code
was modified. The full project suite was not rerun for this data-publication task.

## Actual results

| Check | Result | Record |
| --- | --- | --- |
| Fresh proposal/candidate/selector/state gates | Passed exact 95/73/95 scope | `preflight.json` |
| Existing physical snapshot command | Passed integrity, foreign keys and all-table logical equality; source unchanged | `backup_command.txt`, `backup_reference.json` |
| Initial isolated atomic regressions | 4 passed before execution | `atomicity_tests.txt` |
| Expanded atomic/snapshot regressions | 5 passed before authorized publication calls | `atomicity_and_snapshot_tests.txt` |
| Atomic publication | 95 revisions / 95 created receipts; one outer commit | `publication_results.json` |
| Exact payload reconciliation | 95/95 approved and published review hashes/payloads equal | `proposal_publication_reconciliation.json` |
| Real committed resolutions | 73/73 to PK32/expected UUID | `candidate_resolution_report.json` |
| All-table preservation | All preexisting rows/schema unchanged; only authorized additions/sequences | `postpublication_verification.json` |
| Focused post-publication suite | 130 passed, including the five task-local tests | `focused_tests.txt` |
| Live read-only and isolated Django checks | No issues | `postpublication_verification.json`, `django_check.txt` |
| Migration consistency | No changes detected | `migration_check.txt` |
| Dependency consistency | No broken requirements | `dependency_check.txt` |

The five task-local tests prove that a second CLI failure rolls back the first
publication, a service rejection rolls back its failure receipt as well as prior
publications, and a failed pre-commit verification rolls back an otherwise
successful batch. They also exercise successful publication and identical native
snapshot hashing across plain and declared-type-converting SQLite connections.
Test counts overlap and are not additive.

## Preservation and limits

Counts changed only as authorized: **861 → 861 VehicleDefinitions, 2,980 → 3,075
audit receipts, 64 → 159 correspondences**. Every old row, table/schema definition,
unrelated sequence, candidate artifact, approval and original review file is
preserved. All 1,165 preexisting MY2021 handoff files and protected application/
contract files match baseline hashes. All 88 prior classification claims, the
additional 392 fuel classification and direct ECX evidence remain intact. RHD and
CLASS-075 remain deferred; no new publication references JLUL74.

The database intentionally changed through the 190 authorized row additions and
normal sequence advances. Post-publication database SHA-256 is
`51cfe5595492b454484f106df9aade9b02e6ded681ce39eaeae3c4590443b975`.
The verified backup remains unchanged at SHA-256
`06502534d35395b97d74447b98c760f237a1e2aba04860f32d349fab62bd1d92`.
No source live database replacement, reset, migration or restore was performed.

No proposal failed or partially committed. The resolved pre-write diagnostic is
retained transparently; no other discrepancy or publication limitation remains.
Canonical eligibility, Matrix certification, planning/import and historical
backfills were not assessed or executed. Those remain separate authorizations.
No application/accepted-contract change, commit or push occurred.
