# MY2019 Wrangler JL certified Matrix execution

Created: 2026-11-08
Status: Accepted

The project owner explicitly authorized final certification and create-only
execution of the exact reviewed 19-row US MY2019 Wrangler JL Matrix, conditional
on pre-execution checks. All gates passed. The unchanged accepted approval and
execution CLI workflows received affirmative `yes` responses on behalf of that
explicit authorization, with director `project_owner` and agent `codex`. Neither
confirmation nor validation code was patched. `approval.json` records the exact
approved digest and timestamp. This is a local audit record, not a signature.

Matrix 2.1 digest:

`sha256:d8f11301e230b8485dfd2d15c0b9342aaa0cc778aa7418052ce8da7b10cf6896`

Approval time: `2026-11-08T20:56:29.384551Z`.

## Pre-execution gates

The exact 19-row scope, Matrix digest, all prior planning artifact file hashes,
19 semantic manifest hashes, final candidate digests and five published
correspondence dependencies were verified against the reviewed records. The six
two-door and thirteen Unlimited combinations were checked against an explicit
trim/engine enumeration: ten approved ERC revisions and nine unchanged EC3
revisions, MY2019, US, 4WD only. Every row targets Generation PK 32 / UUID
`38d3c3ac-f825-4406-abb5-c2d12b9129a4`; no other engines, years, markets or parents
were admitted. Published revisions 9–13 and receipts 2857–2861 matched.

All 19 current plans were eligible creates with no conflicts or existing MY2019
JL configurations. Each snapshot plan matched a fresh plan exactly. Current and
anticipated creation bases matched the Matrix's explicit allowed sets and the
accepted RA-044 planner rules. Initial counts were 793 VehicleDefinitions, 2,861
receipts and 13 correspondences. System checks passed.

A consistent pre-import SQLite backup was created using the SQLite backup API
from a read-only source connection. Integrity, foreign keys and every table's
logical rows matched the source. The development database retained its exact
preflight byte hash through backup and certification.

Backup: `backups/review/my2019_jl_import_20261108T205605112634Z/pre-import.sqlite3`

Backup SHA-256: `sha256:346dfed9672b836d84b605a9618d79804f3cfe1ed167809e19780ba229ddf11d`

The backup's physical hash differs from the source's physical hash; SQLite backup
consistency was verified by complete table contents and schema rather than an
assumption of byte-identical database layout. The backup remains preserved.

## Actual execution

The accepted `execute_generation_trim_matrix_year` workflow ran once, for 2019,
in one durable model-year transaction. Each row was freshly planned and
revalidated against preceding creations. The 19 old snapshot manifests were not
executed sequentially. Actual creation bases: `{'first_representation': 1, 'mechanical_dimension': 9, 'source_established_grade': 9}`. Every actual basis was
permitted by its exact Matrix row. No no-op, update, delete, backfill, additional
publication, adjudication repeat or schema migration occurred.

The workflow's retained attempt directory contains exact Matrix/approval copies,
serialized candidates, 19 freshly generated execution manifests, operator labels,
preflight and result records. Execution manifest hashes reflect the new live
peer premises and may differ from the earlier snapshot planning hashes; both are
retained and cross-referenced in `verification.json`. Original reviewed artifacts
were not overwritten.

**Created 19 VehicleDefinitions (PK 809–827) and 19 successful creation receipts
(PK 2862–2880). Totals are 812 definitions and 2,880 receipts; correspondences
remain 13.** All new records are active US MY2019 JL configurations under PK 32.
Ten ERC human conclusions retain approved human provenance, moderate confidence
and documented limitations; they have not become direct manufacturer assertions.
Nine EC3 classifications preserve their evidence-backed provenance.

## Verification

- All new target slugs and ten target fields match the exact approved Matrix;
  UUIDs are valid, globally unique among VehicleDefinitions and bound to receipts.
- Resolution 1.1, engine proof 2.0, exact candidate revisions, authentic retained
  evidence, published correspondence hashes, execution manifests, successful
  receipts, immutable identity snapshots and exact Matrix/approval linkage match.
- Accepted read-only reconciliation reports all 19 `previously_completed`, with
  `complete=true`. No retry or extra no-op receipt was executed.
- Every preexisting row in every application table is unchanged versus backup.
  Only the VehicleDefinition and ImportExecutionReceipt tables gained 19 rows
  each. Only those two SQLite sequence entries advanced. Schema, migrations,
  correspondences and all other tables are unchanged.
- All 233 prior director-review artifacts retain their byte hashes.
- SQLite integrity is `ok`; foreign-key violations are zero. Django system checks
  passed. 98 focused tests passed after execution using an isolated in-memory
  test database; exact command/results are in `focused_tests.json`.
- Tests and read-only verification did not change the post-import database hash.

Database SHA-256 before: `sha256:c0ee965ce9d741c68850b440065876e2f223cc4648006a4bff1c431712a48686`

Database SHA-256 after: `sha256:bde5218712398f0c7b5251abaefa3182f99ea43fd037c442c04518f01b59f410`

The prior final review environment `.venv/bin/python` was used unchanged:
Python 3.13.1, Django 6.0.7, pypdf 6.16.1. The older documented
`venv/py313/bin/python` path remains absent. No interpreter, dependency, system or
version-manager installation/configuration was changed.

No implementation defects, unexpected conflicts, stale evidence or execution
scope deviations were encountered. Existing uncommitted work remains. No
application code or accepted contract changed. No commit or push occurred.
No further import action is pending for this certified set.

## Files

`preflight.json`, `approval.json`, CLI logs and `command_results.json` record gates,
explicit owner authorization and actual command outcomes. `attempts/` retains the
accepted workflow's immutable execution record. `verification.json` contains the
all-table preservation comparison and per-row canonical/receipt/hash inventory.
`reconciliation.json` and `focused_tests.json` record post-execution checks.

## Created records

| Row | VehicleDefinition PK | UUID | Receipt PK | Creation basis |
| --- | --- | --- | --- | --- |
| JL19-01 | 809 | 73e8e697-05bc-42fc-8cc9-b5b8a871ac0a | 2862 | first_representation |
| JL19-02 | 810 | d671cf0f-7737-402c-8d6d-dc4dba238591 | 2863 | mechanical_dimension |
| JL19-03 | 811 | 42d613f0-777f-4851-ab4a-e16281577a74 | 2864 | source_established_grade |
| JL19-04 | 812 | 2eec4dbd-731a-477b-8d4f-3727b72c35cc | 2865 | mechanical_dimension |
| JL19-05 | 813 | 4981e5aa-e354-4389-a51c-30fa9fdb46f8 | 2866 | source_established_grade |
| JL19-06 | 814 | 5bd45d5d-ddb3-4ced-bb66-33198f8c8870 | 2867 | mechanical_dimension |
| JL19-07 | 815 | f4a03389-af27-4f18-b636-4669190d1b5c | 2868 | source_established_grade |
| JL19-08 | 816 | 7625ff74-3822-48bd-b158-409635328e3f | 2869 | mechanical_dimension |
| JL19-09 | 817 | 6157f5df-b8b8-4604-8831-1366ad0094b0 | 2870 | source_established_grade |
| JL19-10 | 818 | 1384a85f-870a-4b1f-84a4-91e300fda732 | 2871 | mechanical_dimension |
| JL19-11 | 819 | 666907f2-e71a-4bd5-ad27-6356bbf7e3cd | 2872 | source_established_grade |
| JL19-12 | 820 | d0dfe4f3-d43b-4ae4-ad9b-f6e7c2596226 | 2873 | mechanical_dimension |
| JL19-13 | 821 | 09fb33a5-8b69-4163-9898-7b7427a542c4 | 2874 | source_established_grade |
| JL19-14 | 822 | 7040ac9d-a844-4d3f-be94-efe299d851b1 | 2875 | mechanical_dimension |
| JL19-15 | 823 | f81d3191-e207-431d-97f9-8e4a0b4ec39b | 2876 | source_established_grade |
| JL19-16 | 824 | 2bba6536-daf8-4466-8208-5d33b820203c | 2877 | mechanical_dimension |
| JL19-17 | 825 | 67ef25d8-3e89-4c84-8574-843dc941851d | 2878 | source_established_grade |
| JL19-18 | 826 | aa85642e-94f6-4c65-bb83-c11616a1b6ab | 2879 | source_established_grade |
| JL19-19 | 827 | ea4bb934-825f-4740-997e-4599ceba3d13 | 2880 | mechanical_dimension |
