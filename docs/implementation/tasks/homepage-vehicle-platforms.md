# Homepage Vehicle Platforms administration

Created: 2026-11-15
Status: Accepted
Disposition: Complete locally; missing implementation recovered for a separate focused commit.

## Scope

The homepage Vehicle Platforms module now uses `core.HomepageVehiclePlatform`, a
small presentation configuration separate from canonical VehicleModel identity.
The existing templates, card layout, generation image assets and model destinations
remain. No image uploads, generic CMS, new application or new dependency.

Each entry selects one VehicleModel, nonnegative display order, enabled flag and
optional image Generation. One entry per model is enforced by OneToOne uniqueness;
disable/re-enable that entry instead of making duplicates. Equal orders use entry PK
as a stable tie-breaker. Only active models/manufacturers with existing active
configuration coverage appear, preserving the previous homepage eligibility rule.
Newly populated models require an explicit Admin entry; disabling all entries leaves
an empty module rather than silently restoring hardcoded defaults.

Admin: Core → Homepage vehicle platforms. Add the model and save; its edit form
then offers only that model's generations. Model validation also rejects a foreign
Generation on direct saves, including partial updates. Existing Django staff/change
permissions govern access. Display order and enabled state can be changed from the
Admin list. Change a model first and save without an override if choosing a different
model whose generations are not yet in the dropdown.

The optional generation controls only the thumbnail. The card still links to
VehicleModel.get_absolute_url. Its image uses the existing static resolver, including
model-specific assets and the established 4Runner legacy fallback. Missing override
images use the prior default (preferred generation where defined, then the last
covered generation); if none exists the existing text placeholder renders. Assets
are never copied or changed. Existing hero/recently-viewed sections remain unchanged.

The View all vehicles link is constructed through the existing selector URL helper
and resolves to `/select-vehicle/?destination=generations`. `/vehicles/` and other
links/routes are unchanged.

## Initialization migration

`core/migrations/0001_homepage_vehicle_platform.py` creates only the configuration
table and initializes eligible models in exactly the prior stable ordering: preferred
4Runner/Tacoma/Touareg, then remaining models in manufacturer/name order. It does not
set image overrides, so existing thumbnail defaults remain. On this development
snapshot the intended initialization is:

1. Toyota 4Runner (VehicleModel PK17).
2. Toyota Tacoma (PK19).
3. Volkswagen Touareg (PK18).
4. Jeep Wrangler (PK21).

Depends on reference 0013. No canonical model/schema change, canonical import,
Engine update, MSRP backfill or generation-image mutation. Django post_migrate will
add the new content type and ordinary Admin permissions. The owner explicitly approved the local write under AGENTS.md §13. Core migration
0001 is applied and the live homepage is verified against the initialized entries.

## Files

- `core/models.py`, `core/admin.py`, `core/migrations/0001_homepage_vehicle_platform.py`
  and package initializer: isolated configuration, validation, Admin and initialization.
- `reference/services.py`, `templates/home.html`: use configured cards, image override,
  existing fallback and corrected selector destination.
- `reference/tests/test_homepage_platforms.py`: focused configuration/Admin/image/link
  and initialization preservation tests.
- `reference/tests/test_vehicle_navigation.py`, `test_experimental_hub.py`: existing
  homepage fixtures explicitly select their featured model under the new contract.
- `reference/tests/test_vehicle_msrp.py`: restore all migration leaves after its
  historical schema test, including the new dependent core migration.
- CURRENT_STATE, CHANGELOG and this task record: milestone-only documentation.

## Verification

Current interpreter: `.venv/bin/python`, Python 3.13.1 / Django 6.0.7.
All automated tests use isolated databases. All 90 focused homepage/Admin/navigation/
configurator/MSRP tests pass. Full suite: 1,089 tests in 113.626 seconds, the identical
25 known label/drive failure entries, no errors or new failures. The extra partial-save
relationship test was verified in the final focused run. System check, migration-drift
and working-tree whitespace checks pass. SQLite integrity/FK checks pass; read-only
comparison confirms every original row across all pre-existing tables is unchanged.
The migration is now applied with owner approval; initialization is verified both
through the isolated migration test and read-only live homepage rendering.
Read-only pre-migration snapshot captured all original table columns/rows at
`/private/tmp/homepage-platform-baseline.json` for post-application comparison.
The snapshot includes the owner's current prices, Engine registry and image choices.
The pre-existing modified `jeep-wrangler-jk.jpg`, development database, unrelated
MY2023/MY2024 documentation/artifacts and all untracked work are preserved.
No staging, commits, pushes, deployment or environment changes.

## Authorized local application and final verification

The owner approved local migration application on 2026-11-15. Captured a fresh
pre-application snapshot and integrity/FK-verified backup at
`/private/tmp/rigarchive-pre-homepage-platforms.sqlite3`, then applied only
`core.0001_homepage_vehicle_platform` successfully.

Four enabled configuration entries were initialized in order: 4Runner, Tacoma,
Touareg, Wrangler; image overrides are NULL. Read-only live rendering returns HTTP
200 with the same four image URLs as before, model-level card destinations, and
`/select-vehicle/?destination=generations` for View all vehicles.

Exact comparison of all original columns/rows across 49 pre-existing tables passes,
including 1,150 definitions, all eight Engines, owner-authored MSRP, receipts and
canonical identities. Generation image hashes are unchanged. Django added four
permissions, one content type and one migration receipt; no pre-existing metadata
was changed. SQLite integrity/FKs, system check, migration drift/state and whitespace
checks pass. Final post-application focused run: all 90 tests pass (2.425 seconds).

The owner's separately staged/modified Ford Transit image and modified Wrangler JK
image are preserved. No staging, commit, push or deployment was performed by this
milestone. Known full-suite label/drive failures remain the existing limitation.

## Owner-approved commit preparation

The owner approved this implementation for commit preparation. Fresh verification
passes all 90 focused tests (2.418 seconds), Django system checks, migration-drift/
state checks, SQLite integrity/FKs and Git whitespace checks. Core 0001 is included
and applied locally. The previously documented full-suite limitation is unchanged;
no full-suite repeat was needed for this staging-only task.

The owner has since customized the configuration: five entries, with 4Runner,
Wrangler and Tacoma enabled (in that order), and Sprinter/Touareg disabled. Image
overrides are 4Runner Fourth Generation, Wrangler JK and Tacoma Third Generation.
These are owner database settings, preserved and excluded from the commit. Existing
canonical totals remain 1,150 definitions and eight Engines.

Two unrelated images were already staged: Ford Transit fourth-generation JPG and
Wrangler JK PNG. Their normal-index staging is preserved byte-for-byte. Homepage
files and only their shared-document sections are prepared separately using
`GIT_INDEX_FILE=/private/tmp/rigarchive-homepage-commit.index`. This isolated index
contains no database or image files. Review and any later manual commit must use
that index; the normal Git index still contains the unrelated image staging.
Proposed commit: `Add admin-managed homepage vehicle platforms`.
No commit, push, deployment, database write or unrelated cleanup performed.

## Index reconciliation and missing homepage implementation recovery

The owner requested reconciliation after public visibility was committed through
an isolated index as da5356b. The normal index still represented parent 40730c9 for
all 19 visibility paths, producing apparent deletions/reversions. Each of those index
entries was verified equal to the old parent: none contained a new staged owner edit.
The original index was preserved at
`/private/tmp/rigarchive-normal-index-pre-reconcile-20261115T122952` with a matching
hash and an owner-staging patch. Only those 19 entries were updated from HEAD.
The genuine staged Wrangler JK JPG replacement and PNG deletion remain exact.
No working-tree files or database records were changed by reconciliation.

Audit of 40730c9: despite its homepage implementation message, it added only
`static/images/generations/ford-transit-fourth-generation.jpg` and
`static/images/generations/jeep-wrangler-jk.png`. It did not include any Core model,
Admin, migration, homepage service/template, tests or implementation documentation.
Those completed changes remained in the working tree and are prepared now.

Fresh verification: 100 homepage/navigation/configurator/MSRP/public-visibility tests
pass (2.976 seconds). System, migration drift/state and whitespace checks pass.
Core 0001 is already applied; no migration or data write was run in this task.
Read-only homepage rendering is HTTP 200 with correct selector/model destinations,
three enabled cards (4Runner, Wrangler, Tacoma) among five configured entries.
There are still 1,150 definitions/eight Engines; owner-hidden RHD PK1116/1155 remain
hidden. The database hash is unchanged. Public visibility predicates and behavior
are preserved; three homepage fixture lines in `test_public_visibility.py` only
adapt existing visibility tests to explicit homepage selection.

The recovery commit comprises 13 files: Core model/Admin/initial migration/package,
service/template integration, homepage tests and three existing fixture updates,
this report and homepage-only CURRENT_STATE/CHANGELOG sections. The earlier
`test_vehicle_msrp.py` migration-leaf restoration is already committed with visibility
and is not included again. No images, database, scratch or research artifacts included.

Only the 13 homepage entries are added to normal staging; its two owner image entries
remain untouched. A separate index at `/private/tmp/rigarchive-homepage-recovery.index`
contains just the homepage changes against da5356b. The homepage entries are mirrored
identically in both indexes, so a later commit through the separate index will not
produce stale homepage deletions in the normal index: only the original owner image
changes should remain staged. Review/commit must explicitly select the separate index.
Proposed message: `Complete admin-managed homepage vehicle platforms implementation`.
No commit, push, deployment, canonical data change or unrelated cleanup performed.
