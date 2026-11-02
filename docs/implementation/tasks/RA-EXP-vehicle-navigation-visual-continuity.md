# Vehicle Navigation Visual Continuity

Date: 2026-10-31. Status: implemented, automated and managed-browser checks passed; user visual review approved, including final mobile initial-load and skip-link checks. No commit or push.

## Scope

### Vehicle navigation visual continuity (2026-10-31)

- Scoped photographic generation cards retain chronology and canonical whole-card links, use 3:2 photographs, serif generation names, production years and Explore Generation actions; three desktop columns become one at narrow mobile widths. Legacy manufacturer-directory cards are unchanged.
- Generation detail preserves the desktop photo/information panel. At stacked widths, the single identity block precedes a responsive 3:2 photograph; the contradictory image height constraints are removed. Planned overview topics are noninteractive subdued text labeled Coming later, stacked on narrow screens. Existing configuration and measurement links remain intact.
- Model cards retain two columns at 390px with compact Generations actions; desktop wording remains Explore Generations. Manufacturer labels and selector heading align with existing archival typography. Model/detail Vehicles breadcrumbs return to Explore Vehicles. The visible label/caret gap is 6px, retaining the original toggle hit area and keyboard behavior.
- A stylesheet version query refreshes stale browser CSS observed during verification. No assets, image assignments, backend workflows, schema, dependencies or JavaScript changed.
- Verification: 354 Django tests and 17 JavaScript tests passed; system check, migration-consistency dry-run and diff whitespace checks passed. Django checks/tests used Python 3.13, an in-memory database, temporary media and a connection guard. No development migrations ran.
- Managed-browser review covered Explore Vehicles, 4Runner/Tacoma/Touareg generation listings and second-generation detail at 1440px and 390px. Verified grids, mobile identity/image order and crops, no observed horizontal overflow or broken loaded images, no captured console errors, keyboard card navigation/focus and dropdown Enter/Escape/focus restoration; caret gap measured 6px. User visual approval is complete, including final mobile initial-load and skip-link checks. Normal session writes from authorized visits are preserved; no vehicle/reference records were intentionally changed.

## Implementation decisions

No new component abstraction: explicit generation-photo classes in the existing model template isolate the manufacturer directory. The shared site palette, global focus outline, small border radius and model-card hover border are retained. Existing assets and image lookup assignments are untouched. The detail identity is rendered once, before the photograph in document order; explicit desktop grid placement retains the photograph on the left. At <=1024px the information wrapper uses display: contents so identity, photograph, overview and statistics occupy consecutive grid rows. At <=38rem overview topics use one column. Generation grids use 3/2/1 columns; selector grids keep their existing 4/3/2/1 breakpoints. The short mobile action is Generations →, fitting a single line within 163px-wide cards at 390px.

All five overview topics were unavailable; no functioning overview link was removed. Canonical configurator, measurement links and manufacturer/model ancestry are preserved. The deferred contextual shell remains deferred. This task does not approve or complete the overall experimental UI.

## Files

Templates: base.html (stylesheet version query), reference/vehicle_selector.html (responsive action), reference/vehicle_model_detail.html (scoped photographic cards and breadcrumb), reference/generation_detail.html (identity document order, overview text and breadcrumb). CSS: static/css/site.css. Tests: reference/tests/test_vehicle_visual_continuity.py (four new tests), reference/tests/test_views.py (updated model-card contract while retaining legacy-card checks). Documentation: CHANGELOG.md, CURRENT_STATE.md and this record.

## Verification

Used venv/py313/bin/python -B /tmp/rigarchive_ui_verify.py, a temporary wrapper around Django call_command('test'). It sets RIGARCHIVE_TEST_DB_PATH=:memory:, TEST.NAME=:memory:, temporary media/upload directories, and rejects non-memory SQLite connections through connection_created. Final full suite: 354 tests, all passed. The initial 88-test focused run exposed an error in the new test parser assertion (HTML boolean attributes have None values); checking attribute presence fixed the test, and the final full suite covers it. The first wrapper attempt failed before database creation due to replacing TEST defaults; corrected to update NAME only.

venv/py313/bin/python -B /tmp/rigarchive_ui_verify.py checks ran call_command('check') and call_command('makemigrations', check=True, dry_run=True): no issues, no changes. No migrate command or development database migration ran. node --test reference/tests/js/generation_configurator.test.cjs reference/tests/js/vehicle_quick_selector.test.cjs: 17 passed. git diff --check passed.

Browser-only application inspection at 1440x1000 and 390x844 covered all seven requested pages and the dropdown. Model grid measured 163px x 2 at mobile; Generation grid 342px x 1; desktop Generation grid three ~387px columns. Mobile hero image measured 324x216, with identity above it. 4Runner, Tacoma and Touareg crops were checked without asset changes. Overview topics have no anchors. Enter opened the disclosure and focused Toyota; Escape restored the toggle focus. Native Tab moved between photographic cards with a visible solid 2px outline; Enter reached the canonical Second Generation route. Mobile dropdown width was 342px and label/caret gap measured 6px at both widths. No observed horizontal overflow, broken loaded images or captured warnings/errors. Temporary viewport overrides reset. Screenshots saved outside the repository in the chat visualization directory under continuity-* filenames.

## Preservation and review limits

Pre-existing changes: config/settings.py, db.sqlite3; untracked .codex-protected-test, .codex-writable-test, .codex-write-test and homepage builds.png, factory.png, measurements.png, service.png, vehicle-study.svg. Preserved, not reset or staged. No direct development database access or intentional vehicle/reference/measurement writes; browser visits may update permitted Django sessions. Database bytes are therefore not expected to remain identical. No settings changes, dependencies, image asset edits, production changes or Git publication.

The user approved the larger Generation cards and quieter Coming later overview after reviewing the screenshots. The existing tall sticky mobile header remains outside this task. Existing Builds/Service/Garage placeholders elsewhere remain unchanged. Screen-reader, zoom/reflow and exhaustive viewport/device acceptance remain unverified.

## Final review and manual commit preparation

User visual approval includes a fresh Explore Vehicles load at 390x844: scrollX/scrollY were zero, URL fragment empty and body focused. The skip link was wholly above the viewport until the first Tab; focus revealed it at top zero without scrolling, and the next Tab hid it again with scrollY still zero. No implementation changed during that follow-up. The final commit-preparation review changed only task documentation to record approval and these results. Latest successful automated results remain 354 Django tests and 17 JavaScript tests; no tests rerun during preparation. Approved file diffs and untracked test/task-record contents reviewed; no migration files introduced, no unexpected working-tree files, no staging/commit/push. Existing settings/database/markers/homepage assets remain excluded.
