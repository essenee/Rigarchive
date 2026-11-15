# MY2025 Wrangler JL registry-backed local import

Created: 2026-11-14
Status: Accepted
Last Updated: 2026-11-14

## Scope and implementation

Owner authorizes the 31 Edmunds inventory rows and exact authored mappings:
gas_36_v6 → ERC, gas_20_turbo → EC1, gas_64_v8 → ESG, phev_20_turbo → ECX.
Operational Engine PKs resolve to 1, 2, 3 and 6 respectively; all explicit inventory
properties agree. Registered complete properties supply new snapshots; source nulls
remain in the original inventory and receipt provenance. No Engine creation, inferred
manufacturer code, schema change, manufacturer research or adjudication pipeline.

`reference/my2025_wrangler_import.py` pins the approved inventory bytes, exact active
parents, existing sparse bodies, registry state, complete family identities/slugs and
current MY2025 namespace. It reuses registry construction, five-field/body identities,
complete-family slug qualification and validated individual model saves. Its dedicated
receipt version does not claim to be a MY2024 Candidate/Matrix contract. Create/no-op
receipts bind the reviewed digest, dependency/row snapshots, source URLs/date and
declared attribution. All 31 rows revalidate in one transaction; any conflict or audit
failure rolls back the entire family. No existing definition is updated.

Preview (read-only):

```sh
.venv/bin/python manage.py import_my2025_wrangler
```

Explicit local execution requires `--execute --approved-plan-hash sha256:...` from
that exact preview. Execution requires desktop SQLite, DEBUG and the exact local
BASE_DIR/db.sqlite3 target. Stale inventory, parent, Engine, body or namespace state
invalidates authorization. Reruns skip exact definitions and add audited no-op receipts.
The MY2024-only body-derived public record name condition is extended to MY2025;
existing generic configurator grouping/filtering is reused unchanged.

## Verification and disposition

Interpreter discovered: `.venv/bin/python`, Python 3.13.1, Django 6.0.7. No environment
changes or installations. The obsolete venv/py313 path was not used.

- Preview: 31 create, zero skip/block. All 31 baselines and slugs distinct.
- 18 isolated focused import/body-group tests pass (13 new import tests).
- System check, migration-drift and whitespace checks pass; no migration created.
- Complete suite: 1,043 tests, 25 failure entries, confined to the two unchanged
  configuration-label test modules. Restoring HEAD __str__ in process memory and
  running those 17 tests reproduces exactly the same 25 failures.
- Existing development DB remained byte-identical through verification. A read-only
  baseline fingerprints all 49 tables; a temporary backup passed integrity/FK checks.

**Publication completed locally.** The owner explicitly answered “Proceed with the
bounded test exception” after reviewing the reproduced pre-existing failures. No
unrelated label behavior or tests were changed to force a passing result.

The executed preview hash was
`sha256:3d07c967c782390f23d26865e49b0c20a34ca75dcc245c25afd15cdfec20581d`.
One atomic invocation created 31 definitions (PK1100–1130) and 31 receipts
(PK3394–3424), with zero skips/failures. A fresh read-only preview then showed zero
creates, 31 skips and zero blocks. Executing that exact new digest skipped all 31,
left every VehicleDefinition field unchanged, and added 31 no-op receipts.

Post-import counts: 31 MY2025 JL definitions, 24 gasoline/seven PHEV, ten two-door/
21 four-door. Engine assignments: ERC PK1 (11), EC1 PK2 (12), ESG PK3 (1), ECX PK6 (7).
All 20 public configurator groups and their exact 31 member identities/labels passed
read-only verification. A field-complete comparison of all preexisting rows in all
49 database tables passed, including every historical definition, receipt, Engine,
body and parent. Only 31 definitions and 62 audit receipts were added; schema is
unchanged. SQLite integrity/FK checks and final Django system/migration-drift checks
pass. No production operation, commit or push.

Preview, execution, rerun, validation and complete preservation summaries are retained
under `docs/research/MY2025_JL_edmunds_builder_20261114/` as `local_import_*.json`.

Changes: service, management command, focused tests, one model display condition,
this task record, CURRENT_STATE and CHANGELOG entries, preview and validation artifacts.
Completion date: 2026-11-14. No migrations or architectural changes. The original
source inventory and ambiguities remain unchanged; registry mappings resolve canonical
engine properties without an aspiration exception. Remaining: owner factual website QA
and the separately scoped pre-existing label-test failures (bounded exception recorded).
All implementation changes remain uncommitted; no push/deploy.

## Focused commit preparation (2026-11-14)

Reverified all 31 active records against the exact authored Engine FKs and all five
registered properties. Preview is zero create/block, 31 skip. All 50 relevant import,
body-group and Engine-registry tests pass under `.venv/bin/python` (Python 3.13.1,
Django 6.0.7), with isolated test databases. System and migration-drift checks pass.
The prior 1,043-test suite result and explicitly approved exception are unchanged;
no broad suite rerun was needed for this documentation/staging task.

Documented the owner-approved permanent Engine rule in `docs/development/INGESTION_PROTOCOL.md`:
resolve existing registry identities and reuse their properties; never automatically
create/modify Engines; stop unrecognized engines for human review/manual authoring,
and resume only after the required Engine exists. No ingestion framework change.

Reviewed all 940 untracked file paths and all four tracked modifications. The focused
stage includes implementation, MY2025-only status/changelog hunks, the permanent rule,
source inventory and final acquisition/execution/verification artifacts. The superseded
blocked-preview diagnostic stays unstaged. Prior MY2023/MY2024/RA050/RA051 handoffs,
Edmunds coverage register, RA050 test, scratch files and read-only helper stay unstaged.
`db.sqlite3` stays unstaged because its working-tree difference includes unrelated
pre-existing data changes as well as this publication; no mixed database checkpoint is
included. No data writes or imports were performed during commit preparation.

Operational totals remain 1,115 definitions, 3,455 receipts and seven Engines; MY2025
remains 24 gasoline/seven PHEV and ten two-door/21 four-door. Development DB SHA-256
remained `531170c9e4cc91139c49c5737c7f08f91e9f69e74c99984bf6156a0a67768a49`
through verification. Outstanding: human factual website QA and separately scoped
pre-existing label-test failures. Commit/push/deployment remain unexecuted.
