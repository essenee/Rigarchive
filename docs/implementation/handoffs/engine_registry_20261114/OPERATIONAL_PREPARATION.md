# Engine Registry 3.1.0 — operational preparation

Created: 2026-11-14
Status: Accepted
Execution status: COMPLETE — seven Engines and two JL body records created

The Project Owner authorized migrations 0011/0012 and the nine exact parent records
on 2026-11-14. Both migrations applied; the initial population stopped before any insert.
The owner-authorized constraint correction and resumed population succeeded on
2026-11-14. The chronological execution receipts below retain both outcomes. Accepted
integration commit: `6151984f714070cadb94a68c0261f7822a199346`. This document is intentionally uncommitted.
The prior passing 45 focused / 390 targeted / 1,013 full tests were retained for
acceptance; no suite was rerun for this proposal.

## Observed operational state before execution

Read-only SQLite URI `mode=ro`, with `PRAGMA query_only=ON`, confirms Reference
migrations through `0010_vehicledefinition_electrification_type_and_more`.
Neither `reference_engine` nor `reference_factorybodyconfiguration` exists, so
there are no operational Engine/body records to reuse. Counts remain **1,053
VehicleDefinitions, 3,350 receipts and 242 correspondence revisions**.

Jeep Manufacturer: **PK 20**, UUID `42eefe42-0f2f-4e31-b4b2-f3e520ea0e50`.
Wrangler Model: PK 21. JL Generation: **PK 32**, UUID
`38d3c3ac-f825-4406-abb5-c2d12b9129a4`, start 2018, end null.

Original read-only preparation DB SHA-256:
`be3b1cfe8f03feda457f2aa7ef397b96f2cd673971aaf6a999c171c5523b32a6`.

## Seven exact Engine proposals

All rows use Manufacturer PK 20. Displacement is marketed **liters**, represented
below by its exact canonical decimal string; cylinder counts are the existing
`engine_cylinders` parameter. I4/V6/V8 remain in the accepted descriptive names;
no new cylinder-layout, tuning, transmission, model or year field is introduced.

| Manufacturer | Complete code | Exact Engine name | Liters | Cylinders | Aspiration | Fuel | Electrification | Published support |
| --- | --- | --- | ---: | ---: | --- | --- | --- | --- |
| Jeep | `ERC` | 3.6L V6 ESS | `3.6` | 6 | `naturally_aspirated` | `gasoline` | `none` | VD 1006; receipt 3288; MY2023 |
| Jeep | `EC1` | 2.0L I4 Turbo | `2` | 4 | `turbocharged` | `gasoline` | `none` | VD 1005; receipt 3287; MY2023 |
| Jeep | `ESG` | 6.4L V8 HEMI | `6.4` | 8 | `naturally_aspirated` | `gasoline` | `none` | VD 1001; receipt 3272; MY2022 |
| Jeep | `EC3` | 2.0L I4 | `2` | 4 | `turbocharged` | `gasoline` | `mild_hybrid` | VD 816; receipt 2869; MY2019 |
| Jeep | `ERG` | 3.6L V6 eTorque | `3.6` | 6 | `naturally_aspirated` | `gasoline` | `mild_hybrid` | VD 1007; receipt 3289; MY2023 |
| Jeep | `ECX` | 2.0L I4 Turbo PHEV | `2` | 4 | `turbocharged` | `gasoline` | `plug_in_hybrid` | VD 1002; receipt 3273; MY2022 |
| Jeep | `EXJ` | 3.0L V6 Turbo Diesel | `3` | 6 | `turbocharged` | `diesel` | `none` | VD 1026; receipt 3308; MY2023 |

Values and names are copied unchanged from the accepted
[seven-code seed proposal](wrangler_engine_seed_proposal.json). Its support entries
retain canonical VD/receipt UUIDs, candidate references/digests and qualified original
code evidence. Read-only comparisons of **all 134 published supporting rows** and
their creation-receipt target fields found **zero parameter discrepancies**. This
is an integrity comparison of approved values, not new research or adjudication.
No Engine PK/UUID is invented; normal model defaults allocate them only on an
authorized create. Established definitions apply across models/years without annual
reconfirmation.

## Two exact JL FactoryBodyConfiguration proposals

Both use Generation **PK 32 / UUID `38d3c3ac-f825-4406-abb5-c2d12b9129a4`**.
The exact eight scalar fields are:

| Field | Two-door record | Four-door record |
| --- | --- | --- |
| body_style | null | null |
| wheelbase_designation | null | null |
| body_length_designation | null | null |
| roof_height_designation | null | null |
| door_configuration | `two-door` | `four-door` |
| side_door_arrangement | null | null |
| body_code | null | null |
| body_code_namespace | null | null |

All nulls are intentional. Expected uniqueness is **Generation plus the full
normalized eight-field tuple**, including nulls; these are two distinct exact
identities. Compatible richer sparse tuples are not automatically merged. No body
PK/UUID is preallocated and no unknown designation/code is inferred.

Support: the accepted [RA-048 handoff](../RA048_body_series_persistence_20261113/README.md)
and unchanged [reviewed assignment inventory](../RA048_body_series_persistence_20261113/wrangler_body_assignment_proposals.csv)
establish 77 two-door and 183 four-door MY2019–2023 JL proposals. Representative
reviewed joins are **JL19-01 / VD 809 / receipt 2862** (two-door) and
**JL19-07 / VD 815 / receipt 2868** (four-door), into the retained
[accepted research snapshot](../MY2019_JL/director_review/compact_evidence_revision_2/evidence/accepted_research_snapshot.json),
SHA-256 `44d5baf3d0be3946f2390453b8d567bf9b5529234f94cf6f264f49dd854ff6a3`.
That retained hash still matches. Door support is reused without suffix/trim-name
inference or a second body review. The 260 historical FK proposals are **not** part
of this operation; 15 unresolved MY2018 joins and 80 JK rows remain outside scope.

## Approved execution procedure — actual stopped state recorded below

1. **Quiesce writes and back up.** Record current code revision, DB SHA-256, migration
   history and counts. Use existing `snapshot_db` with a unique timestamped output,
   retaining DB/WAL/SHM/journal files without deletion or replacement. Verify the
   snapshot with plain SQLite integrity check, required tables and logical row counts;
   hash the snapshot and record its path. A VACUUM-based snapshot need not have the
   source file's byte hash. Verify recovery against an isolated copy before changes.
2. **Preflight.** Confirm the exact Manufacturer/Generation identities above, expected
   current hash/schema, no competing writers, and no unexpected existing proposed
   identities. Review `migrate reference 0012_engine_registry --plan`; abort if it
   includes work beyond the expected dependency chain. If identities already exist,
   compare them exactly and obtain a revised operation disposition; never overwrite
   a contradictory registry definition or create duplicates.
3. **Migrate in order.** The existing sequence is
   `0010_vehicledefinition_electrification_type_and_more` →
   `0011_factory_body_configuration` → `0012_engine_registry`.
   0011 creates only the body table/constraints and nullable protected vehicle body
   FK. 0012 depends on 0011 and creates Engine/constraints, nullable protected vehicle
   Engine FK, and engine-name help-text metadata. Neither has data/backfill operations.
   Apply only these existing migrations after explicit authorization; record each
   result. Existing VD PKs/UUIDs/slugs/values/receipts must remain unchanged, with new
   associations null.
4. **Author exactly nine records.** Use ordinary authorized Admin maintenance or
   owner-authorized individual validated model saves with the exact values above.
   Do not use bulk creation (the models reject it), automatic ingestion seeding or
   `get_or_create` with unreviewed defaults. A bounded script, if separately approved,
   should wrap all nine validated saves in one data transaction. Do not touch existing
   VehicleDefinitions, correspondences or publication records. Record actual new
   PKs/UUIDs, operator, timestamps and resulting tuples; retain standard Admin audit
   logging when using Admin.
5. **Verify before resuming writes.** Confirm both migrations applied, exactly seven
   Engines and two body rows, the exact names/codes/five properties, correct parent
   PKs/UUIDs and all intentional body nulls. Check manufacturer/code uniqueness and
   Generation/full-tuple uniqueness; run `PRAGMA foreign_key_check` (no rows) and
   `PRAGMA integrity_check` (`ok`). Compare old canonical rows/original columns and
   receipt snapshots against backup; exclude only the expected migration bookkeeping
   and authorized Admin audit inserts from whole-database equality. New VD FKs remain
   null. Existing counts
   1,053 / 3,350 / 242 must not change. Record the post-write hash and snapshot.
6. **Failure handling.** Stop at the specific error and keep writes paused. Roll back
   an active data transaction; do not retry with guessed values, overwrite records,
   delete partial Admin creations, or blindly reverse migrations. Preserve failed-state
   DB/journals and logs. Inspect/rehearse the verified snapshot in isolation. Restoring
   the operational DB requires **separate explicit owner authorization** and a
   quiescent, SQLite-consistent restore procedure preserving the failed original;
   verify hash/integrity/counts after restoration before resuming. Do not restore an
   old snapshot over newer valuable writes.

The future write scope is limited to the two existing schema migrations, seven
Engine inserts, two body inserts, migration bookkeeping and ordinary authorized
Admin audit entries where applicable. No historical FK assignment, correspondence
publication, MY2024 VehicleDefinition publication or production Matrix is included.
After separately authorized record preparation, generate real 3.1.0 candidate
envelopes and run read-only complete-family planning. Existing Generation and
non-engine source/applicability gates still apply; do not reopen engine classification.

The Project Owner supplied authorization for that operational scope. The failure
below stops the current run; no code repair, validation bypass or automatic restore
is authorized by that execution scope.


## Operational execution receipt — 2026-11-14 08:05:38 PST

**BLOCKED — Engine constraint validation; zero parent records created.**
Execution agent: Codex, under the Project Owner's Authorized Operational Engine and
JL Body Setup instruction. Baseline main/HEAD
`6151984f714070cadb94a68c0261f7822a199346` matched; actual Django settings resolved
`/Users/cosmo/dev/Rigarchive/db.sqlite3`, with no test-database override. Initial
hash/schema/parent identities and integrity/FK checks matched. No open database
handles were reported by the scoped preflight check.

| Phase | Result |
| --- | --- |
| Timestamped backup | Created and verified; source bytes unchanged during backup |
| reference.0011_factory_body_configuration | Applied successfully |
| reference.0012_engine_registry | Applied successfully |
| Seven Engine operations | First Engine (ERC) full_clean failed; no inserts |
| Two body operations | Not reached; no inserts |
| Atomic data transaction | Rolled back; zero data records persisted |
| Post-failure manage.py check | Passed; this does not exercise instance constraint SQL |

Backup: [db_snapshot_pre_engine_jl_body_20261114T160123633348Z.sqlite3](../../../../backups/snapshots/db_snapshot_pre_engine_jl_body_20261114T160123633348Z.sqlite3)

- Absolute path: `/Users/cosmo/dev/Rigarchive/backups/snapshots/db_snapshot_pre_engine_jl_body_20261114T160123633348Z.sqlite3`
- Size: **56,737,792 bytes**.
- SHA-256: `1827d3d9a885d46e43a58b6585255087cd35baecee32ac91d5f8058432add6bd`.
- Opened read-only; integrity `ok`; zero FK violations; every table schema/count
  matched the pre-migration database. Original Reference and migration row values
  matched via ordered original-column fingerprints. No original DB replacement.

Migrations used Django **MigrationExecutor** with the exact two forward targets;
no manual schema/history edits or post_migrate content-type/permission population.
They created the Engine/body tables and nullable vehicle FKs. All pre-existing
Reference values and old table counts were verified before population. An initial
comparison helper mixed Django datetime objects with plain SQLite strings; the
corrected plain-SQLite comparison on both sides confirmed identical original values.
The temporary script's initial import-path invocation also failed before any DB
operation; it was rerun with the repository on Python's module path. Neither issue
changed data or required an application/schema repair.

### Blocking failure

The nine proposed records and parent identities were being validated inside one
Django transaction **before any insert**. The first `Engine.full_clean()` failed
while checking `reference_engine_code_normalized` in `reference/models.py`:

`ProgrammingError: Incorrect number of bindings supplied. The current statement uses 6, and there are 5 supplied.`

The condition's Func template references `%(expressions)s` twice while the bound
expression contributes its parameter once. During instance validation this generates
an unmatched placeholder; Django debug formatting then raises
`TypeError: not enough arguments for format string`. The schema's column-based
CHECK exists, but that does not make the parameterized instance-validation query
valid. No registered value or seed classification is disputed.

The data transaction rolled back. **No Engine/body PKs or persisted UUIDs exist to
report**: seven Engines created = 0; two bodies created = 0; existing matches reused
= 0. No bypass, retry after this validation failure, schema repair, code change or
automatic restoration was attempted.

### Verified stopped state

- Both migrations remain applied; both new tables are empty.
- Existing **1,053 VehicleDefinitions**, **3,350 receipts**, **242 correspondence
  revisions** remain unchanged. All pre-existing Reference original-column values,
  including vehicle PK/UUID/slug/timestamps and complete receipt payloads, match the
  verified pre-migration backup.
- All 1,053 new Engine/body FK pairs are null. No backfill or MY2024 JL publication
  occurred (MY2024 JL VehicleDefinitions = 0).
- All old table counts match, except exactly two expected django_migrations rows.
  Integrity check = `ok`; FK check = zero violations. Backup hash remains unchanged.
- DB SHA-256 before: `be3b1cfe8f03feda457f2aa7ef397b96f2cd673971aaf6a999c171c5523b32a6`.
- DB SHA-256 after migrations and rolled-back population:
  `383f56c645772a269f749e613db53f65ff7436d04e12c75d33fbcf2e571e1b55`.
- No full tests, application/migration/candidate changes, correspondence/approval
  writes, production Matrix, Git staging, commit or push.

**Next smallest step:** separately authorize a targeted fix for Engine constraint
parameter binding with an isolated regression that exercises operational instance
validation. Do not rewrite committed migrations or bypass validation. Then resume
only the nine-record atomic population under explicit authorization; migrations
0011/0012 are already applied. Production candidate preparation/family planning
remains a later separately authorized milestone.

## Constraint correction and resumed population — 2026-11-14

The Project Owner explicitly authorized the narrow runtime fix and conditional
nine-record population. The earlier blocked receipt remains historical.

### Root cause and correction

`models.Func` renders its `expressions` SQL twice in the Engine code GLOB template,
but returns expression parameters once. During `full_clean()`, Django substitutes
a bound code value for the column; the second placeholder therefore lacks its value.
The installed SQLite CHECK uses column references and is correct.

`reference/models.py` now uses `EngineCodeCharacters`, which repeats the parameter
sequence to match the repeated expression. Its migration deconstruction and expression
identity retain the original `models.Func` database definition. Regression tests
compare both the historical constraint and its generated SQL with the current one.
No applied migration was edited, no migration was generated/applied, and no schema
change was required. Normalization, complete codes/hyphens, uniqueness, immutability,
and database validation remain intact.

Changed executable files: `reference/models.py` and
`reference/tests/test_engine_registry.py`. No other application behavior changed.

### Verification actually executed

- Final focused run: **39 tests passed**, covering Engine registry and Engine
  distinction (`reference.tests.test_engine_registry`,
  `reference.tests.test_engine_distinction`). An earlier intermediate run passed
  38 tests before the SQL/migration-equivalence regression was added.
- Explicit regressions cover valid Jeep/hyphenated bound codes, whitespace/case
  normalization, normalized duplicates, invalid values, persistence, raw database
  enforcement, and equivalence with migration 0012's constraint.
- `manage.py check`: passed before population on isolated configuration and after
  population on the operational configuration.
- `manage.py makemigrations --check`: final result **No changes detected**.
  An intermediate check detected expression-class identity drift; retaining the
  original migration expression identity corrected that before population.
- Tests used an isolated test database with
  `RIGARCHIVE_TEST_DB_PATH=/private/tmp/engine-fix-isolated.sqlite3`; the test runner
  created/destroyed its test database. The full suite was not run.
- `git diff --check`: passed.
- Required `venv/py313/bin/python` remains absent; used the previously authorized
  suitable `.venv/bin/python` environment.

### Atomic operational result

Before writes, verified expected HEAD, database SHA, applied migrations 0011/0012,
intact backup, empty Engine/body tables, exact approved seed values, and parent
identities. All nine objects passed `full_clean()` inside one `transaction.atomic()`
before any insert. Exactly **nine inserts committed**, no reuse or updates.

Jeep Manufacturer PK 20 / UUID `42eefe42-0f2f-4e31-b4b2-f3e520ea0e50`.
Body parent JL Generation PK 32 / UUID `38d3c3ac-f825-4406-abb5-c2d12b9129a4`.
Names and powertrain values exactly match the approved tables above.

| Engine code | PK | Persisted UUID |
| --- | ---: | --- |
| ERC | 1 | `f5a7caba-2fdd-43e1-a337-33429399bff3` |
| EC1 | 2 | `ba7b32b8-f69e-4bc4-952f-c493e0e417f4` |
| ESG | 3 | `d56ecfba-5f5d-4166-82a2-77572d4a6f2d` |
| EC3 | 4 | `24414852-63a3-4514-8d34-acae3e0e32e0` |
| ERG | 5 | `4e609d27-c557-4309-b6ee-8ca30f77b5c0` |
| ECX | 6 | `0b84bd7a-2de4-45d9-9f7e-34223e91cb70` |
| EXJ | 7 | `16b0027f-72a9-49cb-9fd2-c55f064c88ed` |

| Door configuration | PK | Persisted UUID |
| --- | ---: | --- |
| two-door | 1 | `f9afec73-6dac-4a51-a409-1a764350c3c6` |
| four-door | 2 | `a2fce731-2203-48a0-8ba6-a0e93770f9f0` |

Both complete eight-field body tuples match the approved table above: only
`door_configuration` is populated; all seven other scalar fields are null.

Post-commit independent read-only verification confirmed exact PKs, UUIDs, parents,
names, all powertrain fields, and complete body tuples. All other table rows match
pre-population fingerprints, including migration history. Existing **1,053
VehicleDefinitions, 3,350 receipts and 242 correspondence revisions** are unchanged.
Historical Engine/body FKs remain null. MY2024 JL VehicleDefinitions: **zero**.
SQLite integrity: **ok**; foreign-key violations: **zero**.

Database SHA-256 before this correction/population:
`383f56c645772a269f749e613db53f65ff7436d04e12c75d33fbcf2e571e1b55`.

Database SHA-256 after committed population and system checks:
`d17261817aea886328b53ab4d6c4f91f03faf14a6dbab5accb863c9c0397aa66`.

The verified pre-migration backup above remains unchanged and was not restored.
No historical FK assignments, production candidates, Matrix operations,
correspondences, vehicle publication, or RA-050 continuation occurred.
No remaining blocker for this nine-record setup. This result does not establish
MY2024 import readiness or authorize further operational work.

Only the two executable files, this handoff and the operational database changed
in this task. All pre-existing unrelated work is preserved. No staging, commit or
push occurred; HEAD remains `6151984f714070cadb94a68c0261f7822a199346`.
