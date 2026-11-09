# MY2021 Matrix certification and planning verification

Created: 2026-11-09
Status: Accepted — planning/certification only

## Actual commands and runtime

Interpreter `/Users/cosmo/dev/Rigarchive/.venv/bin/python` is **Python 3.13.1**.
**Django 6.0.7** and **pypdf 6.16.1** match `requirements.txt`; `pip check` reports
no broken requirements. Its disabled nonwritable user-cache warning does not
affect dependency consistency. No install, upgrade or alternate environment.

Run from the repository root:

```text
.venv/bin/python -B docs/implementation/handoffs/MY2021_JL/final_planning_20261109/build_planning.py build
.venv/bin/python -B docs/implementation/handoffs/MY2021_JL/final_planning_20261109/build_planning.py certify
RIGARCHIVE_TEST_DB_PATH=:memory: .venv/bin/python -B manage.py check
RIGARCHIVE_TEST_DB_PATH=:memory: .venv/bin/python -B manage.py makemigrations --check --dry-run
.venv/bin/python -B -m pip check
git diff --check
```

The build stage invokes existing `plan_canonical_import` for each of the 73 exact
latest candidate paths, with a new exclusive manifest output. Every manifest is
read/reconstructed through the existing serializer and compared to an independent
fresh planner result; each bound resolution is revalidated against live published
state. The certification stage invokes existing `approve_generation_trim_matrix`
with the exact Matrix and all 73 candidate paths, operator `project_owner`, agent
`codex`, and the current task's expressly authorized affirmative certification.
Only a local existing-format approval artifact is written. No execution command,
execution service or actual-candidate rehearsal is invoked.

The focused suite used `RIGARCHIVE_TEST_DB_PATH=:memory:` and the same interpreter.
A Python launcher assigned `settings.MEDIA_ROOT` to a new temporary directory
under this checkpoint and called Django's command runner with:

```text
manage.py test reference.tests.test_generation_correspondence reference.tests.test_generation_projection_completeness reference.tests.test_classification_adjudication reference.tests.test_structured_powertrain reference.tests.test_ingestion_serialization reference.tests.test_candidate_construction reference.tests.test_generation_trim_matrix reference.tests.test_generation_trim_matrix_approval reference.tests.test_matrix_execution --noinput
```

The context cleaned up only its own new media. Synthetic Matrix tests import
isolated synthetic fixtures; no real MY2021 candidates or live canonical records
are imported. Test database migrations are confined to isolated resources; no
live migration is run. No existing test was changed. The full project suite was
not rerun for this artifact-only read-only planning task.

## Results

| Verification | Actual result | Retained record |
| --- | --- | --- |
| Latest candidate/file/content hashes, scope and complete powertrain | 73 pass; 23 two-door / 50 four-door; 24 labels | `plan_index.json`, `planning_validation.json` |
| Prior human approvals and direct ECX evidence | 88 original decisions plus the separate 392 fuel decision unchanged | `engine_proof_index.json` |
| Real published records and receipts | All 95 match approved publication bindings | `resolution_index.json` |
| Engine proof 2.0 | 73 complete actual proofs; current peers empty | `engine_proofs/` |
| Resolution 1.1 | 73 actual published bindings to JL32/expected UUID | `resolutions/` |
| Canonical outcomes | 73 eligible / 0 blocked / 0 conflicting / 0 preexisting | `canonical_peer_and_conflict_assessment.json` |
| Expected actions | 73 creations / 0 no-ops; no execution | `plan_index.json` |
| Namespace and slug occupancy | Actual namespace empty, including inactive; 73 unique unoccupied slugs | `canonical_namespace_snapshot.json` |
| Candidate/manifest round trips and fresh-plan equality | 73 pass | `planning_validation.json` |
| Matrix validation/digest/serialization | Exact 73-row Matrix 2.1 passes | `matrix_2_1.json` |
| Existing approval workflow | Exact digest approved/certified under current task | `matrix_approval.json`, `matrix_certification_cli.txt` |
| Certified current Matrix status | 73 pending_create; no blocked/conflict | `certified_matrix_status.json` |
| Focused suite | 157 tests passed | `focused_tests.txt` |
| Django checks | No issues, including live read-only checks | `django_check.txt`, `matrix_certification_status.json` |
| Migration consistency | No changes detected; none applied | `migration_check.txt` |
| Dependencies | No broken requirements | `dependency_check.txt` |
| SQLite integrity / foreign keys | ok / zero violations | `matrix_certification_status.json` |

All 73 manifest semantic hashes and serialized-file hashes are listed in
`plan_hashes.json` and `plan_index.json`; `plan_hashes.md` provides the complete
human-readable manifest-hash table. Engine/resolution indices retain their own
content/file digests. The package manifest hashes every retained output.

## Snapshot bases and certification boundary

Observed current snapshots all use first_representation and namespace count 0.
Fixed Matrix row-order analysis predicts **1 first representation, 23
source-established grades and 49 mechanical distinctions** during future fresh
transactional replanning. Only the current plus applicable anticipated bases
are permitted per row. No future sibling canonical record, receipt or proof is
fabricated here. Standalone snapshots must not be executed unchanged in sequence.

Certification is an existing local Matrix approval, not import execution
authorization. Pending-create status is expected because no canonical row was
created. Any future execution must revalidate the exact Matrix/approval/candidate/
source bytes, parent and published state, peers, receipt lineage, namespace and
slug occupancy, then freshly plan each row through the accepted Matrix workflow.

## Preservation and intervening state finding

Fresh observed totals are **861 VehicleDefinitions, 3,075 receipts and 159
correspondences**. All 95 relevant review payloads and receipts match publication.
Read-only comparison with its earlier baseline found one preexisting session-row
update but no schema or preexisting canonical-row changes beyond the 95 approved
correspondence and receipt additions. Only the table name/change count is reported;
no session contents or row identifier are exposed or modified. This explains the
intervening logical difference; no historical file hash is reused as proof of the
current task's byte preservation.

The **fresh task baseline and final live database SHA-256 are identical**:
`ecc521242b0d29b659a7195bbfbc498ed80c8f129c472ab9bf445461984520e2`.
All live access is SQLite URI `mode=ro` plus `query_only=ON`. Counts, candidate and
source artifacts, classifications, adjudications, published correspondences and
inspected application/accepted-contract files remain unchanged through this task.
No prior artifact, canonical record, schema or session was restored or rewritten.

Only this planning checkpoint and targeted current-state/changelog updates were
written. No real-candidate import/rehearsal, live database write, migration,
backfill, candidate/correspondence change, application/contract change, commit or
push occurred. No failed check or unresolved technical planning blocker remains.
Canonical execution is explicitly unapproved and awaits separate owner direction.
