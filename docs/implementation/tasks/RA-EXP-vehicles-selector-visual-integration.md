# Vehicles Selector Visual Integration

Status: Implemented and automated checks passed; browser visual/accessibility acceptance pending.
Implementation date: 2026-10-27.

## Dated verification clarification — 2026-10-27

The four-query measurement and 346 Django/11 JavaScript results below describe this task before the later Vehicles quick disclosure. The current rendered unfiltered selector totals six queries: the same four selector/discovery queries plus two bounded header queries, independent of model count. Latest recorded verification after the disclosure is 350 Django and 17 JavaScript tests passed; see `RA-EXP-vehicles-navigation-quick-selector.md`. These figures do not replace the historical measurements, and no tests were rerun for this clarification.

The earlier OpenSSL browser-tool failure is historical; Browser Use is now blocked by managed policy. Actual desktop/mobile appearance/cropping, zoom/reflow, native keyboard/focus and screen-reader acceptance remain pending. The completed Vehicles disclosure is distinct from the deferred five-category contextual shell and optional dialog.

## Scope and implementation

Incrementally connect Vehicles to the existing named selector with the approved `generations` destination. Preserve the legacy directory, canonical routes, active-model eligibility, pending destination contracts, Generation presentation and Model Year → Trim → Exact Factory Configuration selector. No session-selected vehicle authority, new images, dependencies, schema, production configuration or five-category shell.

Explore Vehicles uses a native GET search form, manufacturer links with current-filter indication, clear controls, and responsive model cards. Model cards lead to existing canonical model Generation listings. Reference services prefetch one active Generation per model ordered by descending `start_year`, the canonical chronology. Presentation reuses `get_presentation_hero_image_url` for that Generation only. Missing newest images or absent active Generations render a neutral placeholder; no older Generation is searched. Existing deferred tokens continue to retain pending intent. Header search routing is unchanged; its wording now accurately describes manufacturer/model search.

## Files changed

- `templates/base.html`
- `templates/reference/vehicle_selector.html`
- `reference/services.py`
- `reference/views.py`
- `reference/tests/test_vehicle_navigation.py`
- `static/css/site.css`
- `docs/implementation/CURRENT_STATE.md`
- `CHANGELOG.md`
- This completion record.

## Verification

Used `venv/py313/bin/python -B` with Django management `call_command` for focused tests, system checks, migration consistency (`makemigrations --check --dry-run`), and the complete test suite. The harness set `RIGARCHIVE_TEST_DB_PATH=:memory:`, asserted DiscoverRunner and shared-memory SQLite test creation, redirected media/files to a dedicated temporary directory, and rejected SQLite connections outside memory or that directory. Inspected restoration subprocesses retain their explicit temporary database override. No migrations ran against development data.

- 31 focused navigation/shell tests passed.
- Final full suite: 346 discovered, 346 passed, no failures/errors.
- System check passed; migration consistency found no changes.
- `node --test reference/tests/js/generation_configurator.test.cjs`: 11 passed.
- `git diff --check`: passed.
- Query regression: unfiltered selector remains at four queries after adding models and Generations.
- Database SHA-256 before/after: `90e56453d157afb2cb26f4c7393b620246ffb06a591704da7719b372f82c2482`; sidecars absent at both checks.

New tests cover Vehicles entry, unchanged header search route, manufacturer/model filtering, reset, long names, canonical model links, newest chronological image selection despite insertion order and inactive newer rows, absent newest images, models without active Generations, and query scaling. Existing tests retain canonical-route, pending-intent, escaping, ancestry, empty-result and no-JavaScript coverage.

## Limitations and preservation

### Compact-thumbnail follow-up

Refined only the selector's scoped CSS and image dimension attributes: four fixed desktop columns in a maximum 1008px grid; three columns at <=1024px, two at <=768px, one at <=380px. One-model manufacturers retain a single column-width card. Images use reserved 3:2 frames and 600×400 HTML attributes, retaining cover sizing, newest-active-Generation logic, neutral fallback, manufacturer/model labels and Generation links. Card padding and model-name type are reduced. No backend changes or new tests were needed for this visual adjustment. All 346 existing isolated Django tests passed; system check, migration consistency and whitespace checks passed. Development database SHA-256 remained `90e56453d157afb2cb26f4c7393b620246ffb06a591704da7719b372f82c2482`, with sidecars absent. Browser appearance/cropping acceptance remains pending. No staging, commits or pushes.

Browser automation failed to start because its runtime could not read the system OpenSSL configuration. Actual desktop/mobile appearance, cropping, focus navigation and screen-reader behavior require browser review; automated HTML tests do not establish visual acceptance. CSS reserves an image aspect ratio, uses cover sizing, allows long-name wrapping and retains native controls/global focus indicators.

No migrations or ADRs created. No deviations in implementation scope. Existing staged, unstaged and untracked work preserved; no staging, commits or pushes performed.
