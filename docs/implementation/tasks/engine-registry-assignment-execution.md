# Approved Engine registry assignment execution

Created: 2026-11-15
Status: Implemented and locally verified; documented pre-existing test failures remain

## Authorization and scope

The owner explicitly approved all 507 proposals in the retained reconciliation
artifact: 485 exact matches and 22 Wrangler JL non-hybrid 3.6L V6 ESS aliases,
including five inactive archival rows. No additional correspondence adjudication,
Engine authoring, identity rewriting or importer redesign was authorized.

The original `docs/research/engine_registry_reconciliation_20261115/assignment_preview.json`
is unchanged. Its schema and SHA-256 digest are pinned in the implementation:
`sha256:7ab06c7f7afa590ff7bcd4172e196b5e4b19e596305987467c76ed2b3676bbb8`.
Execution timestamps use UTC (2026-11-16); task/directory dates use owner-local 2026-11-15.

## Implementation and commands

- `reference/engine_assignment.py`: application workflow, approved artifact validation,
  model-validation preflight, transactional individual saves, stale-state checking,
  safe already-applied recognition and full-field preservation checks.
- `reference/management/commands/assign_registered_engines.py`: preview by default;
  explicit execution against DEBUG/local SQLite `db.sqlite3` only; verified physical
  backup, complete ignored baseline and execution receipt. Refuses test database
  overrides, production/nonlocal paths, altered artifacts and existing receipt files.
- `reference/tests/test_engine_assignment_execution.py`: 16 focused regressions.

Preview:
`.venv/bin/python manage.py assign_registered_engines`

Executed once:
`.venv/bin/python manage.py assign_registered_engines --execute --receipt docs/research/engine_registry_reconciliation_20261115/execution_receipt.json`

Verified a second execution with the same command and a new `rerun_receipt.json`.
This command intentionally does not accept new proposal sets or expand approval.
Future assignments require separate owner authorization and an explicit approved artifact.

Revalidation compares Engine PK/UUID/properties/update state and VehicleDefinition
PK/UUID, current unassigned FK, manufacturer, exact/alias uniqueness, five-field
compatibility and the retained preview row. All 507 rows passed model full_clean
before execution. A fresh all-concrete-field baseline is checked again inside the
transaction. Saves use full_clean and the 804edca model behavior with only Engine,
previously unknown fields and updated_at in update_fields. No bulk update is used.

Before commit, every Engine and VehicleDefinition field is compared. Only approved
FKs, verified unknown completions and update metadata are permitted to differ; any
other change rolls back. The receipt is flushed/fsynced within the outer transaction;
receipt I/O failure rolls back the batch. Canonical comparisons and the independent
post-execution report establish the committed result, not a whole-file DB hash.

## Backup and baseline

Established `snapshot_db` VACUUM INTO procedure, verified table/count checks,
integrity_check=ok and zero foreign-key violations. Canonical rows in the backup
were compared with the live database before execution.

Primary backup (ignored, outside version control):
`backups/snapshots/engine_assignments_20261116T024615541749Z.sqlite3`

Complete all-field baseline (ignored):
`backups/review/engine_assignments/20261116T024615541749Z/baseline.json`

The zero-change second execution also created a verified backup:
`backups/snapshots/engine_assignments_20261116T024634002947Z.sqlite3`

## Execution and preservation results

| Metric | Before | After |
| --- | ---: | ---: |
| VehicleDefinitions | 1,150 | 1,150 |
| Linked | 104 | 611 |
| Unlinked | 1,046 | 539 |
| Engines | 10 | 10 |

Initial preview: 507 assign / zero skip / zero block. Execution: 485 exact + 22
aliases assigned, zero failed or skipped. All 507 selected PKs/UUIDs changed and
no other VehicleDefinition changed. No creates/deletes or Engine changes occurred.

Unknown attributes completed: 335 displacement, 335 cylinders, 335 aspiration,
335 fuel type, 335 electrification (1,675 attribute values in total).
Known facts, historical names, slugs, PKs/UUIDs, hierarchy, model years, trims,
drivetrain, body identities, MSRP, public visibility (including PK1116/1155), active
state, creation metadata and all other fields were preserved. All ten complete
Engine rows, including UUID/code/name/properties/update metadata, are identical.

An independent SQLite mode=ro comparison against the primary backup verified every
concrete field and exact changed-row set, not just the service receipt. Integrity
is ok; foreign_key_check has zero violations. Unselected 643 rows are unchanged,
including all 104 previously linked records and all 539 unresolved records.

Rerun preview: zero assign / 507 already applied / zero block. Second execution:
zero assigned / 507 skipped / zero failed, zero changed fields, identical before/after
canonical digests. No repeated updated_at writes.

Post-reconciliation categories: ALREADY_LINKED 611; CONFLICT 61;
INSUFFICIENT_EVIDENCE 412; NO_REGISTERED_ENGINE 66; all other categories zero.

Retained artifacts in `docs/research/engine_registry_reconciliation_20261115/`:

- `execution_receipt.json`: authorization, approved digest, backup/baseline locations,
  before/after canonical digests and all 507 PK/UUID field-level changes.
- `rerun_receipt.json`: zero-change execution proof.
- `post_assignment_preview.json`: complete regenerated 1,150-row inventory.
- `preservation_verification.json`: independent raw-row comparisons, counts and public checks.

## Configurator and tests

All 116 linked non-hybrid ERC Wrangler JL records show exactly `3.6L V6` when
rendered as a single choice; none includes ESS. All 32 linked ERG JL records retain
eTorque and MHEV. Historical descriptors and slugs are unchanged. MY2022/2023/2025/2026
trim/body group labels and membership exactly match the backup; selection/deep-link
resolution succeeds. Current public group counts are 19/25/19/18 respectively,
unchanged by this task (the MY2026 canonical total remains 35).

Focused verification: 168 tests passed in 16.111s, including assignment/reconciliation,
804edca Admin behavior, Engine registry/distinction, structured powertrain, body
grouping, public visibility and MY2025/MY2026 importer tests. The 16 new tests cover
aliases and hybrid exclusion, conflicts/ambiguity, unknown completion, stale/missing
identities and registry state, changed baseline, tampered proposals, safe rerun,
rollback after a second save failure, preservation guard and nonlocal rejection.
An initial test fixture attempted a forbidden Engine queryset update; it was corrected
to simulate external corruption only in isolated test SQL. Final focused tests pass.

Full suite: 1,144 tests in 119.094s, with the identical 25 documented pre-existing
label/drive-wheel failures and no new failures or errors. Failure headings were
compared exactly with the preceding 1,128-test baseline. Existing failures were not
modified. System check, makemigrations --check --dry-run, migrate --check and Git
whitespace checks pass. Tests used isolated in-memory databases.

## Remaining limitations and Git preservation

The 539 exceptions remain unlinked; no automatic Engine creation or new alias rules.
The previously documented MY2025/MY2026 importer mutable-name/identity coupling
remains outside scope; passing fixture tests do not establish live importer rerun
success. No dedicated canonical importer was executed here. No schema changes,
variant key, Full Specs work, commit, staging, push or deployment.

The normal index/HEAD fingerprints are unchanged. Exactly the owner-staged Wrangler
JK JPG modification and PNG deletion remain staged. All unrelated database, image,
research/handoff and documentation work is preserved. The database now also contains
the explicitly authorized assignments. No unrelated files were restored or removed.

This phase adds the three implementation/test files and four result JSON artifacts
above, adds this report, and updates CURRENT_STATE, CHANGELOG and the original
reconciliation report's disposition. Prior uncommitted display/preview implementation
is preserved unchanged. No deviation from the authorized assignment set.

## Finalization and owner-authored follow-up — 2026-11-15

The 611-linked/539-unlinked post-batch checkpoint above is historical. The owner
subsequently assigned VehicleDefinition PK926, UUID caca5d4e-e661-4309-b735-dde058ad46f4
(2021 US Jeep Wrangler JL Unlimited Willys, historical name 3.0L V6) to Engine PK7,
UUID 16b0027f-72a9-49cb-9fd2-c55f064c88ed (EXJ, 3.0L V6 Turbo Diesel). Its complete
3.0L/six-cylinder/turbocharged/diesel/none tuple is compatible. This is intentional
one-row owner authorization, not an extra bulk-execution result or broader alias.

Fresh read-only reconciliation: 612 linked, 538 unlinked, ten Engines, 1,150
VehicleDefinitions; 61 CONFLICT, 411 INSUFFICIENT_EVIDENCE, 66 NO_REGISTERED_ENGINE.
No linked conflicts or binding errors. All current Engine/VehicleDefinition fields,
including the manual assignment, are preserved throughout checkpoint verification.
The original verified pre-execution backup remains in place, never restored.

Final verification reran the same 168 focused tests successfully, Django checks
and makemigrations --check --dry-run (no changes). The full suite was not repeated;
its documented 25 pre-existing failures remain historical unresolved limitations.
The available approved environment is .venv/bin/python (3.13.1); the historical
venv/py313/bin/python path is absent. No environment/dependency changes were made.

Commit scope includes the pinned original preview, execution receipt, idempotent
rerun receipt and preservation verification. The regenerated 3.7MB
post_assignment_preview.json remains preserved locally but is omitted as a redundant
large inventory. Unrelated research, data and image changes are excluded. Shared
CURRENT_STATE/CHANGELOG are partially staged through an isolated index; unrelated
sections remain only in the working tree. The original normal index bytes, including
the two owner-staged JK image operations, are preserved. Advancing HEAD without
rewriting that index may expose reverse staged differences for checkpoint paths;
these are not new work and must not be committed as reversions. No push/deployment.

Checkpoint status: prepared, not committed. Automatic approval review rejected
the attached-file authorization on both commit attempts; no alternate execution
method was used. Direct in-chat authorization is needed before retrying. HEAD
and the normal index remain unchanged, so the possible reverse-index effect
described above has not occurred. Read-only remaining-assignment findings are in
`docs/research/engine_registry_remaining_assignments_20261115/README.md`.
