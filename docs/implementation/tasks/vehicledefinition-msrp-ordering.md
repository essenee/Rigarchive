# VehicleDefinition MSRP and configurator ordering

Created: 2026-11-15
Status: Proposed
Disposition: Implemented locally; owner manual QA complete; preparing focused commit.
Last Updated: 2026-11-15

## Scope and implementation

Add descriptive, optional `VehicleDefinition.base_msrp` (Decimal 10,2), outside
canonical identity. This is the manufacturer's original base price in the vehicle's
market/model year. US values are USD excluding destination/delivery, taxes,
registration, dealer adjustments and optional equipment. Unknown values remain NULL;
no backfill or automatic price refresh occurs. Authorized Admin users can correct
prices using the normal decimal input and change history. Field validation rejects
negative values and excessive precision/range; a database constraint also rejects
negative values. MSRP edits preserve PK, UUID, slug, body and Engine associations.

The existing grouping service computes the minimum known price for each marketed
trim across its engines and bodies within the selected year's active records. It
sorts known prices ascending, then unknown trims, with trim names resolving ties.
Each trim's body groups remain contiguous and retain their existing label/key order.
All-NULL years retain the prior alphabetical order. No extra queries, fields for
ordering, new filters, engine choices, identity rules or public URLs are introduced.

Files: `reference/models.py`, `reference/admin.py`, `reference/services.py`,
`reference/migrations/0013_vehicledefinition_base_msrp.py`,
`reference/tests/test_vehicle_msrp.py`, this record, CURRENT_STATE and CHANGELOG.

## Owner-approved slug amendment and implementation

The owner explicitly authorized the narrow ADR-0002 amendment on 2026-11-15.
The Accepted ADR now records that decision without replacing its original rationale
or general policy. All other models retain their slug policies.

The stored VehicleDefinition slug remains `editable=False`. An Admin-only correction
input displays its current value on existing records for staff with change permission;
creation retains automatic generation and ignores posted correction values. The input
warns that changing the slug may invalidate existing public URLs without redirects.
SlugField formatting, nonempty values and generation-scoped uniqueness are validated.
Normal Admin history includes the old and new values. PK and UUID stay read-only.
Unrelated edits preserve the existing slug. No aliases/history table/redirects added.

Individual saves reject a changed stored slug unless explicitly supplied an active
staff actor with VehicleDefinition change permission. QuerySet updates, bulk updates
and bulk conflict updates cannot change stored slugs. Existing import creation and
no-op workflows remain supported, including cloned-record construction. This follows
normal application permission enforcement, not protection against privileged raw SQL.
No existing operational slug was corrected during implementation.

Additional files: ADR-0002 and
`reference/tests/test_vehicle_slug_correction.py`; extended model/Admin logic and
updated the MSRP Admin test to submit the unchanged correction field. The canonical
import collision fixture now supplies its slug at creation rather than using an
unauthorized rename; its conflict-rejection assertion remains unchanged. Existing
factory-body Admin submissions without the new input and partial saves with iterator
`update_fields` remain supported; omission produces no false slug-correction history.

## Local migration and preservation

The task explicitly authorizes this local migration. Reviewed `sqlmigrate` output:
add a nullable column, then SQLite table rebuild to enforce the new nonnegative
constraint while copying all existing columns. Took an integrity/FK-verified backup
at `/private/tmp/rigarchive-pre-msrp.sqlite3` before applying reference 0013.
Migration completed successfully. All 1,150 definitions have NULL MSRP.

Compared every pre-existing row and original column across all 49 tables against
the pre-migration snapshot: unchanged, including all seven Engines, identities,
public slugs, timestamps, receipts and historical years. Django post_migrate also
added eight missing permissions for existing Engine/body models and one missing
FactoryBodyConfiguration content type; one migration receipt was added. Existing
permissions/content types remain unchanged. No user/group permission assignments
were changed. SQLite integrity and foreign-key checks pass.

JL counts MY2018–2026: 15, 19, 49, 73, 55, 64, 31, 31, 35. MY2026 retains 19 groups,
ERC PK1=16, EC1 PK2=17, ESG PK3=2, ten two-door/25 four-door, zero PHEV. Read-only
URL-resolved rendering with ephemeral sessions returns HTTP 200 for all nine years.

## Verification

Interpreter: `.venv/bin/python`, Python 3.13.1 / Django 6.0.7.

- `manage.py check`: passes.
- `manage.py makemigrations --check --dry-run`: no drift.
- `manage.py migrate --check`: passes after applying 0013.
- Seven new tests pass: NULL/decimal/range/negative validation, database constraint,
  Admin price editing/history/permissions, stable generated slugs/identities,
  price ordering across bodies/engines, ties/missing/all-NULL prices, exact membership,
  public rendering, no added grouping queries and historical migration compatibility.
- 130 focused/regression tests pass: `test_vehicle_msrp`, `test_models`,
  `test_configurator_body_groups`, `test_experimental_hub`, `test_engine_registry`,
  `test_my2025_wrangler_import`, `test_my2026_wrangler_import`.
- Full suite: 1,072 tests in 107.987 seconds, 25 failure entries in the previously
  documented `test_configuration_label_formatting` / `test_configurator_drive_wheels`
  modules. An isolated process loaded `HEAD:reference/services.py` without modifying
  files and reran those modules: the identical 25 failure headings reproduced across
  17 tests. No new failure entries appeared. These failures were not fixed or hidden;
  the full suite is not green; its known failures remain documented.
- `git diff --check` passes. No files staged; prior status entries preserved.

No dependency installation, ingestion, Engine writes, backfill, unauthorized governance edits,
staging, commit, push, deployment or production changes. Prior unrelated working-tree
changes are preserved. This records the implementation-time state before owner QA. The three requested
behaviors are implemented; known full-suite failures remain a verification limitation.
See the final QA and commit-preparation checkpoint below for the current database.

## Controlled slug editing verification (2026-11-15)

201 focused/regression tests pass, including seven new correction tests: displayed
value/warning, authorized correction and old/new history, immutable PK/UUID/Engine/
MSRP, invalid/empty/duplicate rejection, unauthorized staff/ordinary-user rejection,
automatic creation, unrelated edits, blocked automated/bulk updates and unchanged
other-model Admin policies. Existing MY2025/MY2026 imports remain covered.
System, migration drift/state and whitespace checks pass. No migration is needed.
Read-only comparison confirms all 1,150 VehicleDefinitions, stored slugs, Engine
relationships, seven Engine records and NULL MSRP values remain unchanged. MY2026
remains 35 active definitions and 19 trim/body groups. Integrity/FK checks pass.
Final full-suite rerun: 1,079 tests in 111.784 seconds, exactly the same 25
previously documented label/drive-wheel failure entries, no errors or new failures.
The complete failure-heading set matches the prior MSRP run. The final focused
201-test run passes in 13.172 seconds. No development database writes, staging,
commit, push or deployment performed for the slug enhancement. No remaining
architectural blocker; existing full-suite failures remain the verification limitation.
Owner manual QA subsequently completed, as recorded below.

## Owner QA and final commit preparation (2026-11-15)

Owner QA confirmed editable MSRP and existing slugs, resolution of corrected public
URLs, and stable stored slugs after changing drivetrain from 4WD to 2WD.
Read-only comparison against the pre-MSRP snapshot finds no remaining slug,
drivetrain, UUID, PK, body or Engine-relationship differences in any of the 1,150
VehicleDefinitions. No records were added or removed. Seven definitions have newer
Admin save timestamps: PK721, 1132, 1134, 1136, 1140, 1144 and 1149.

Owner-authored MSRP values are preserved (USD): PK1132 36,035; PK1134 39,040;
PK1136 39,685; PK1140 43,755; PK1144 44,035. The other 1,145 prices remain NULL.
These values are reported as owner edits, not independently verified source prices.
The original seven Engines remain byte-for-byte unchanged. The owner also authored
Engine PK8, Jeep EGT, 3.8L V6, bringing the actual registry count to eight. This is
outside this code milestone; it is reported and preserved, not removed or staged.
No database correction was performed.

Migration 0013 is present and applied. MY2026 retains 35 active definitions and 19
trim/body groups, ERC16/EC1 17/ESG2, ten two-door/25 four-door, zero PHEV. SQLite
integrity/FK checks pass. Fresh final verification: all 201 focused tests pass; system, migration state/drift,
and working/staged whitespace checks pass. The full suite was not repeated for
commit preparation; its prior 1,079-test result with 25 known failures is retained.
Only milestone implementation/tests, ADR amendment, this report and milestone
sections of shared documentation are staged. The development database, unrelated
MY2023/MY2024 documentation and all other untracked artifacts remain unstaged.
Proposed commit: `Add VehicleDefinition MSRP ordering and controlled slug editing`.
No commit, push or deployment performed. Existing full-suite failures remain the
known verification limitation; no new failures were found in the previous full run.
