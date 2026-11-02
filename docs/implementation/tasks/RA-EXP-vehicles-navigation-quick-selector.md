# Vehicles Navigation Quick Selector

Implementation date: 2026-10-27.
Status: Implemented; automated verification passed. Browser visual/keyboard/accessibility acceptance remains pending.

## Final behavior and scope

Global navigation has separate sibling Vehicles link and chevron button. Vehicles and the panel footer both target the existing named selector with `destination=generations`. The button is named “Choose a vehicle”, exposes `aria-expanded`/`aria-controls`, and is hidden until JavaScript listeners are installed. The hidden disclosure contains ordinary manufacturer buttons (`aria-pressed`/`aria-controls`) and ordinary canonical model links, with labeled Manufacturer and Model sections. It is not an ARIA menu or modal.

An inclusion tag calls existing `discover_manufacturers()`. Active manufacturers must have eligible active models; Generation/definition coverage is not required. Shared prefetching takes two queries per rendered header regardless of manufacturer/model count. Both template loops share the evaluated queryset. No Generation/image queries are introduced. Models use their existing `get_absolute_url()` named-route reversal. Empty eligible catalogue and defensive empty-group messages are rendered; empty manufacturers are excluded by existing discovery rules. Names/URLs remain template escaped. The unfiltered full selector now takes six queries: its unchanged four plus the header's two.

Click opens/closes; opening focuses the previously selected or first manufacturer, falling back to Browse all vehicles for an empty catalogue. Manufacturer selection changes the visible model group and keeps focus on the native button. Native Tab/Shift+Tab reach buttons and model links without arrow-key interception. Escape restores toggle focus, outside clicks dismiss (restoring focus only if it would remain in hidden content), and leaving the disclosure by keyboard closes without stealing destination focus. Model links navigate normally. No hover-only opening, global link interceptor, session authority, fetch endpoint or dependency is introduced.

CSS reuses existing type/colors/borders and global focus indicators. Desktop has two text columns and scrollable lists; <=480px stacks columns with shorter scroll areas. The panel is anchored beneath the navigation, bounded by its width and viewport, and has a maximum height with scrolling. Long names wrap. Other navigation controls and header search are preserved. With JavaScript disabled, the ordinary Vehicles link remains available while the toggle/panel remain hidden.

No new canonical routes/pages, APIs, schema/migrations, images, contextual five-category shell, or Generation configuration changes. No architectural decisions or scope deviations.

## Files created or modified by this task

- `templates/base.html`
- `templates/reference/partials/vehicle_quick_selector.html`
- `reference/templatetags/__init__.py`
- `reference/templatetags/vehicle_navigation.py`
- `static/js/vehicle_quick_selector.js`
- `static/css/site.css`
- `reference/tests/test_vehicle_quick_selector.py`
- `reference/tests/test_vehicle_navigation.py`
- `reference/tests/test_views.py`
- `reference/tests/js/vehicle_quick_selector.test.cjs`
- `docs/implementation/CURRENT_STATE.md`
- `CHANGELOG.md`
- This task record.

## Verification

Executed through `venv/py313/bin/python -B` and Django `call_command` with `RIGARCHIVE_TEST_DB_PATH=:memory:`, asserted DiscoverRunner, isolated temporary files/media, and a runtime SQLite guard allowing only memory/shared-memory test databases or files inside the dedicated test directory. All test temporary paths were directed into that directory, including backup/restore tests. No development-database connection was needed.

- `check`: passed, no issues.
- `makemigrations --check --dry-run`: passed, no changes detected.
- Focused navigation/quick-selector suite: 30 passed.
- Final complete Django suite: 350 passed in 14.211 seconds.
- `node --test reference/tests/js/*.test.cjs`: 17 passed (11 existing configurator, six new disclosure tests).
- `git diff --check`: passed.
- Development database SHA-256 before/after: `90e56453d157afb2cb26f4c7393b620246ffb06a591704da7719b372f82c2482`; no sidecars before/after.

Initial full verification exposed an over-broad legacy directory assertion and a harness restriction on temporary snapshot files. The directory regression now asserts coverage exclusion/inclusion specifically within main content, separately acknowledging the header's approved selector eligibility. The harness was corrected to place all test temporary files inside its permitted directory. Final full verification passed without weakening database protection or changing directory behavior. Existing selector query-count assertions account for the two header queries, and its no-script assertion now verifies the permitted external disclosure enhancement.

Tests cover split controls, accessibility attributes, progressive-enhancement markup, active/inactive ancestry and empty catalogue, escaped/long names, canonical model URLs, preserved links, bounded query count, and disclosure interaction/focus handling using an instrumented DOM. Existing tests retain canonical routes, directory/homepage coverage, pending destinations, and Generation configurator regressions.

Browser Use is blocked by managed policy and was not attempted. Desktop/mobile appearance, actual viewport overflow/zoom/reflow, native keyboard/focus behavior and screen-reader acceptance remain unverified. Automated HTML/DOM tests do not establish those acceptance results.

## Preservation

Pre-existing staged, unstaged and untracked work remains in place, including pre-existing development-database changes and two staged images. Incremental edits preserve the existing navigation integration and other unfinished work. No staging, commits, pushes, reset, restore, clean, stash, migration execution or development-database writes were performed. No governance files or accepted ADRs modified.
