# Engine internal variant key and historical import compatibility

Created: 2026-11-16
Last Updated: 2026-11-16
Status: Implemented; focused verification passed; full-suite baseline failures remain; live migration pending

## Authorized scope and boundaries

Owner-authorized field/composite identity, bounded resolver/consumer compatibility,
Admin, tests, new migration and isolated rehearsal. No live migration, Engine creation,
assignment, receipt rewrite, canonical data operation, commit or deployment is performed.
The field does not mechanically enforce evidence review. Nonempty keys must be backed
by existing retained research/task evidence describing the distinction, application,
source references/hashes, limitations, approval and eventual Engine PK/UUID. No keys
are derived from names, years, horsepower, torque or vehicle tuples.

## Model and migration

`normalize_internal_variant_key` requires a string, rejects non-ASCII before lowercasing,
strips outer whitespace, lowercases and accepts exactly `[a-z0-9_-]{0,100}`. Empty
means unestablished, never gasoline/default/preferred. Authentic engine-code behavior
and public `Engine.__str__` are unchanged. Saved manufacturer/code/key/UUID identity
is immutable; complete validated transactional saves and bulk-write restrictions remain.

Migration **reference.0015_engine_internal_variant_key**, depending on 0014:

1. Remove `reference_unique_engine_manufacturer_code`.
2. Add the non-null, blank/default-empty 100-character field.
3. Add manufacturer + Upper(Trim(code)) + Lower(Trim(key)) uniqueness.
4. Add canonical key storage check: SQLite built-in GLOB allowlist, explicit NUL
   rejection via INSTR/CHAR, and Length <=100. No REGEXP extension is required.
5. Add a forward no-op / reverse guard. On reversal this runs first and refuses
   ANY nonempty key, before dropping constraints/column or restoring old uniqueness.
   Recovery after authored variants requires a separately reviewed plan, not silent loss.

No data migration generates keys or saves existing Engine instances/timestamps.
The live database remains at 0014: application code requires separately authorized
migration before this feature can operate there. No server restart or deployment.

## Resolution and historical boundaries

`UNSET_VARIANT` distinguishes omission from explicit empty. Missing is an error;
omitted keys require exactly one manufacturer/code row BEFORE property checks.
Multiple same-code variants remain ambiguous regardless of partial five-field claims.
Explicit keys normalize and select that composite. Exact PK and/or UUID lookup checks
all supplied pins, manufacturer/code/optional key and complete compatible properties.
Both incoming property dictionaries in unsaved vehicle construction are still checked
separately. There is no registration, ranking, empty-key preference or Engine inference.

Reconciliation retains existing FKs and authorized receipt pins; unpinned same-code
variants cannot be selected by name/property elimination. The original 507-row
approval is unchanged, not a new authorization.

Body3.1 reads exact authorized Engine pins, validates properties on the selected
instance and compares the unchanged full binding. Unrelated same-code additions do
not invalidate that pin. Binding construction/verification rejects nonempty keys.
MY2026 uses the existing inventory PK/UUID pins; MY2025's code-only inputs require
unique resolution. All existing profile versions/hashes remain unchanged.

`HISTORICAL_SNAPSHOT_FIELDS` in the MY2025 module explicitly projects the six historical
model shapes shared by MY2025 /1 and MY2026 /1,/2. The retained complete preimages
establish the original columns, order and all-string/non-null encoding; Decimal
`2.00`, datetime space/offset, UUID and null handling remain exact. Later namespace
columns `base_msrp`/`is_public` were absent from those approvals and are not silently
inserted. Future columns cannot expand this projection. Nonempty Engine keys reject.
No Candidate, Body3.1 or new Jeep wire version is introduced.

Full-field `.values()` preservation remains exhaustive and includes the new key.
MY2021/MY2022 receipt metadata enumeration is unrelated to adding an Engine column
and remains unchanged. Future receipt-column and review-dataclass schema compatibility
work, variant-aware ingestion and horsepower/torque remain deferred.

## Admin and public identity

Creation exposes the neutral key help text. List/search includes it; existing records
show it read-only. A dedicated Admin autocomplete view/widget keeps Django's source
field, model permission and to-field checks, rejects non-Engine targets, and labels
choices with key (or “no explicit discriminator”) and PK. Public Engine names, vehicle
slugs/UUIDs, rendering, canonical ordering and five-field identity remain unchanged.

## Isolated preservation rehearsal

Capture: **2026-11-17T02:43:21Z** (2026-11-16 PST). SQLite supported backup from a
read-only live connection, then another supported backup to the disposable rehearsal.
The capture contains **12 Engines, 1,150 VehicleDefinitions and 3,591 receipts**;
these are capture-time counts, not assumptions that authoring has ended.

Ignored, private local evidence directory:
`backups/review/engine_variant_20261117T024321Z/`

- `capture.sqlite3`: preserved capture, SHA-256
  `09282d0dccfc34421eb913200212a1e09bc9e93308acc6dccb6d2c86eba428cf`.
- `rehearsal.sqlite3`: migration applied only here.
- `preservation_verification.json`: all original columns compared across **51 tables**.
- `historical_readers_verification.json`: scoped historical reader/hash results.
- `working_files_before.json`: pre-existing file hashes, not an approval artifact.

Every original Engine field (PK/UUID/code/name/specifications/timestamps), every
VehicleDefinition/FK, all receipt JSON/metadata and unrelated table rows match the
capture. Unrelated schema objects are identical. Expected exceptions are precisely
the added migration-history row and its autoincrement counter; other sequences match.
All 12 keys are empty; integrity is `ok`, FK violations zero. Test-only records
exercise uniqueness, raw-storage checks, concurrent duplicate attempts, safe reversal
while empty and fail-closed reversal after a nonempty variant exists.

## Verification results and limitations

Runtime: `.venv/bin/python`, Python **3.13.1**, Django **6.0.7**, pypdf **6.16.1**.
The repository-prescribed `venv/py313/bin/python` is absent. The existing verified
runtime was used without installation, dependency changes or PYTHONPATH substitution.
All Django commands explicitly set `RIGARCHIVE_TEST_DB_PATH` to an isolated path.

- Focused Engine/registry/body/profile/reconciliation/assignment/Admin/compact tests:
  **188 passed** (27.904 seconds); final **14 new tests passed** after Admin target
  permission hardening and projection formatting (0.712 seconds). No live test database.
- Full Django suite: **1,205 tests**, **25 assertion failures**, 118.684 seconds.
  All failures are in `test_configuration_label_formatting` and
  `test_configurator_drive_wheels`, involving existing missing drive labels.
- Baseline diagnosis: exported committed Python/templates to a separate temporary
  tree, without a database or working-tree replacement, then ran those two modules.
  **17 tests reproduce exactly the same 25 failing test/subtest identifiers**.
  Thus they predate this implementation. They were not fixed or tests weakened.
  The full suite is **not passing**; this checkpoint is not claimed fully verified.
- Six complete historical MY2025/MY2026 preview preimages reproduce their approved
  constant hashes, including all model projection shapes and future-field regression.
- Migrated-copy readers validate **73 MY2021 +55 MY2022** compact records unchanged.
- Original assignment preview hash remains
  `sha256:7ab06c7f7afa590ff7bcd4172e196b5e4b19e596305987467c76ed2b3676bbb8`.
- Django system checks pass; migration-consistency dry-run reports no changes.

No historical approval is replayed as authority for new assignments. Current plan
staleness from real Engine edits/timestamps remains correct. No nonempty variant
can be executed through legacy import formats merely because the model supports it.
SQLite GLOB/INSTR checks follow the existing SQLite-only deployment boundary; no
claim of new multi-backend portability is made.

## Files and handoff

Application: `reference/models.py`, `engine_registry.py`, `engine_reconciliation.py`,
`admin.py`, `my2025_wrangler_import.py`, `my2026_wrangler_import.py`,
`ingestion/importing/registry_body_import.py`.
Migration: `reference/migrations/0015_engine_internal_variant_key.py`.
Tests: `reference/tests/test_engine_internal_variant_key.py`,
`test_registry_body_import.py`, `test_my2026_wrangler_import.py`.
Documentation: this record, `CURRENT_STATE.md`, `CHANGELOG.md`,
`IMPORT_CONTRACT_REGISTRY.md` (pre-existing untracked audit, explicitly updated).

Pre-existing live `db.sqlite3` difference and Engine readiness report are preserved.
No historical migration, evidence/approval artifact, public label service, application
contract version, normal/isolated Git index or deployment configuration is changed.
Separate owner authorization is required for the live migration and later evidence-
reviewed Engine authoring/assignments. Existing configurator baseline failures remain
an independently scoped follow-up decision, not a reason to broaden this task.

Final preservation check: the live database SHA-256 matches the task-start file
baseline, `14974ac34f1bf33351bdb9795dfbc6ee5a6d23a1387de709b7cbccec24b161b9`.
Live integrity/FKs still pass, 0015 is absent, and the variant column is absent.
The pre-existing readiness report is byte-identical; only approved application/test/
documentation files differ from the working-file baseline. Backups are Git-ignored.
`git diff --check` passes; the normal index is empty and untouched. No commit or push.
