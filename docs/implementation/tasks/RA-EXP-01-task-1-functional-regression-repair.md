# RA-EXP-01 Task 1 — Homepage and Generation Hub Functional Regression Repair

## Approved scope

Restore existing Generation notes safely, repair dependent and exact-configuration selection, preserve unnamed trims and canonical URLs, validate query parameters consistently, and provide deterministic year ordering. Restore a passing suite by distinguishing obsolete presentation expectations from substantive behavioral requirements. Preserve the experimental design, development database, untracked work, and Git staging; do not commit or push.

## Implementation

- Notes render conditionally with escaped Django `linebreaks` output.
- The year-scoped selector chooses exact canonical configurations, starts disabled, and includes unnamed trims. The lower browser retains trim filtering with `trim=` representing the actual empty trim and an absent parameter representing all trims.
- Configuration-only URLs infer the year before dependent choices. Explicit blank, invalid or mismatched years do not infer a replacement year. Invalid/inactive/cross-generation configurations fail safely with notices.
- Exact identity includes model year, model, trim, engine, drivetrain and market. Year/trim selection never silently chooses one configuration. Full specifications use canonical URLs; model-year overview actions have distinct labels.
- Both year controls use descending years. Configuration ordering includes market and slug tie-breakers.
- Apply Filters provides GET submission without JavaScript; optional year-change submission clears exact selection. Reset and empty states are explicit. The third browser column is labeled Configuration without introducing package modeling.
- Existing test expectations were updated for current homepage/Generation markup while retaining domain separation, real content, and active-record protections. Added 11 tests for notes safety, selection state, inference, unnamed/shared trims, invalid selections, ordering, and reset/empty states.

## Completion record

- Status: Task 1 implemented and checks passing; RA-EXP-01 remains WIP pending final evaluation.
- Completion date: 2026-10-26.
- Files changed: `reference/services.py`; `templates/reference/generation_detail.html`; `static/css/site.css` (selector width containment); `config/tests.py`; `reference/tests/test_views.py`; `reference/tests/test_experimental_hub.py`; `reference/tests/test_canonical_correction_lifecycle.py`; `CHANGELOG.md`; `docs/implementation/CURRENT_STATE.md`; `docs/architecture/designs/RA-EXP-01-Filterable-Vehicle-Generation-Hub-And-Homepage-Redesign.md`; this task record.
- Migrations/ADRs: None. Models, routing, measurements, ingestion, and session persistence are unchanged.
- Verification environment: Existing Python 3.14 with `PYTHONDONTWRITEBYTECODE=1`, `PYTHONPATH=.venv/lib/python3.14/site-packages`, and `RIGARCHIVE_TEST_DB_PATH=:memory:`. The virtualenv launcher cannot load its framework library; no packages were installed.
- Commands: `python3 -B manage.py check`; `python3 -B manage.py makemigrations --check --dry-run`; `python3 -B manage.py test --noinput`; `git diff --check`.
- Results: System check passed, no migration changes detected, 297 tests passed, no whitespace errors. Earlier checkpoint result was 286 executed, 273 passed, 13 failed.
- Limitations: Browser tooling unavailable; no comprehensive responsive/keyboard or optional JavaScript execution verification. Unsupported diagram dimensions, verification terminology, hidden measurement conditions, unavailable navigation destinations, and broader service dependency cleanup remain separate work.
- Preservation: Development database and untracked probes preserved; no staging, commit or push performed.


## Authorized pre-commit configurator UX refinement

- Status: Implemented; no commit or staging performed.
- Native `#configurations` fragment on GET form action, reset and selection links; desktop/mobile sticky-header scroll margins. Named and unnamed trim filters are preserved by hidden form values; changing year with optional JavaScript clears dependent state. No script-based scrolling dependency.
- Replaced tall configuration cards with compact wrapping selection/Specs links. Current selection has a visible marker and `aria-current`; sibling options and exact canonical specification links remain available.
- Labels use varying trim, engine and drivetrain attributes; if none vary, engine/drivetrain provide useful context. Market is omitted unless needed to distinguish labels; canonical slug disambiguates otherwise identical records. Canonical market validation/identity remains intact. No transmission values are invented. Subtitle: Factory Configurations.
- Additional files modified for this refinement: Generation template, CSS, `reference/services.py` (presentation labels/sibling choices only), `reference/tests/test_experimental_hub.py`, and relevant status/changelog/design/task documentation.
- Verification: Django system check passed; migration-consistency dry-run detected no changes; 30 focused configurator tests passed; full isolated suite passed **303/303**. Six new UX tests preserve existing regression coverage. Initial Task 1 result above remains historical.
- Limitation: Browser tooling unavailable; native fragment and CSS behavior verified structurally, not through desktop/mobile browser execution. The wider experiment remains pending evaluation.
- Refinement preservation check: Git index and unrelated source/probe fingerprints match their starting values. The development database fingerprint changed during the turn despite all verification commands using the isolated database setting and no agent-issued development-database writes. The source was not established; the database was left untouched rather than restored. Byte-for-byte preservation across this turn cannot be confirmed.


## Navigation and scroll behavior correction

- Diagnosis: Existing links and inline `form.submit()` handlers always navigated the full page. Fragment presence in generated HTML did not prove viewport preservation. Explore form/reset actions had also been indiscriminately targeted at the lower configurator. The director reproduced the failure; the precise browser-specific fragment-reset cause was not reproduced locally because browser tooling is unavailable.
- Corrected Explore behavior: Only Explore Configurations intentionally scrolls downward. Specs/model-year actions retain canonical destinations; form/reset fallback targets Explore itself. Lower configurator links retain their own native fragment fallback.
- Progressive enhancement: New `static/js/generation_configurator.js` uses existing same-origin Generation GET responses and replaces only Explore/configurator panels. Delegated listeners survive replacements; canonical navigation and modified clicks are not intercepted. In-flight requests are cancelled and stale responses ignored. It retains viewport position at response commit time (including user scroll during a pending request), focus without scrolling, loading/completion announcements, URL history and back/forward updates. Invalid/error responses fall back to native GET navigation. Inline submit handlers were removed so they cannot bypass enhancement. No view/service/schema changes are needed.
- Files changed in this correction: Generation template, CSS fragment offsets for Explore, focused Python tests, new page-local JavaScript and `reference/tests/js/generation_configurator.test.cjs`, plus status/changelog/design/task documentation. Compact configuration layout and label rules are unchanged.
- Verification: 51 focused Django tests passed; full isolated suite **305/305** passed. System check, migration-consistency dry-run, `node --check static/js/generation_configurator.js` and diff whitespace checks passed. `node --test reference/tests/js/generation_configurator.test.cjs`: **10/10** passed, covering repeated selection, layout shifts, native destinations/modified clicks, GET state, stale requests, back/forward, unsupported enhancement, HTTP/network failure, and malformed responses.
- Limitations: Node tests execute the real script against an instrumented DOM/Fetch boundary, not a browser renderer. Desktop/mobile scroll position, image layout timing, and assistive-technology behavior still require real-browser confirmation. No packages were installed; no RA-EXP-02 navigation or canonical route changes were made. Earlier 297/303-test results and the initial fragment-only approach above are historical.
- Correction preservation check: Git index and unrelated source/probe fingerprints are unchanged. The development database fingerprint changed during the turn despite isolated verification and no agent-issued development-database writes; the cause was not established and the database was left untouched. Byte-for-byte preservation cannot be confirmed.


## Final Generation page layout refinement — provisional placement

- Status: Implemented with passing checks; RA-EXP-01 remains WIP pending final evaluation, not complete or approved.
- Removed Explore This Generation because it duplicated the three-step configurator. Removed its introduction, upper filters, selected-configuration summary, Apply/Clear controls and Specs/Explore actions.
- Moved the existing three-step configurator rather than recreating or duplicating it. It now sits immediately beneath the photograph/Generation overview, before notes and Key Dimensions. Heading: **Configurations & Specs**. Introduction: “Explore available factory configurations by model year and trim. Select a configuration to view its detailed technical specifications.”
- Placement is **provisional**. As Generation pages accumulate more substantive measurements, builds, and maintenance content, the Configurations & Specs section may be reconsidered for placement below Key Dimensions or farther down the Generation page. This is a future design consideration, not authorization to move it again.
- Preserved the stable fragment and filter hooks, three-step labels, year/trim/exact selection, unnamed trims, compact labels/options, selected styling, canonical links and keyboard/native GET fallback. Reset and invalid-selection notices now belong to the remaining configurator. The script updates only that section and no longer handles the removed form; viewport/focus/history, cancellation and native fallback remain tested. No filtering-service or label-rule changes.
- Removed only the Service Guides introductory subtitle and extra heading wrapper. Its heading row now matches Builds and Mods, aligning dividers/content starts without changing empty-state functionality or responsive grid rules.
- Files modified in this refinement: Generation template; scoped fragment CSS; page-local configurator script; focused Python and JavaScript tests; current-state, changelog, experimental design and this task record.
- Verification: 52 focused Django tests passed; full isolated Django suite **306/306** passed; JavaScript behavior tests **10/10** passed; system check, migration-consistency dry-run, JS syntax and diff whitespace checks passed. Previous 297/303/305-test runs above remain historical.
- Limitations: Real-browser rendering/scrolling/alignment verification unavailable locally. Director approval of prior compact controls and corrected scrolling is preserved; it does not constitute comprehensive verification of this final placement. No RA-EXP-02 changes, schema/migrations, ingestion or database writes were introduced; no staging, commit or push performed.
- Final layout preservation check: Git index and unrelated source/probe fingerprints are unchanged. `db.sqlite3` changed during the turn despite isolated verification and no agent-issued database writes; the source was not established and no restoration was attempted. Byte-for-byte database preservation cannot be confirmed.


## Final Generation page cleanup

- Status: Implemented with passing checks; RA-EXP-01 remains WIP, not complete or approved.
- Removed the standalone Generation Notes presentation. `Generation.notes`, stored values, model/schema and backend access remain unchanged. Useful platform information (including designations such as N180) may be considered within Generation Overview → Platform & Design in a future task; no new platform content or route is implemented here.
- Removed the stray visible bottom-page “Configurations updated.” status. The announcer now sits inside Configurations & Specs with `role="status"`, polite/atomic live semantics and visually hidden styling, without `display:none`, `hidden` or `aria-hidden`. Only its sibling `#configuration-content` is replaced on async updates, keeping the same live node mounted. Loading and successful-update announcements remain available to screen readers without a persistent visible message. Focus/keyboard and viewport behavior are retained.
- Approved configurator placement, heading/description, selection logic/labels, GET fallback, canonical links, dimensions and Builds/Service Guides alignment are unchanged.
- Files modified in this cleanup: `templates/reference/generation_detail.html`, `static/css/site.css`, `static/js/generation_configurator.js`, `reference/tests/test_experimental_hub.py`, `reference/tests/test_views.py`, `reference/tests/js/generation_configurator.test.cjs`, `CHANGELOG.md`, `docs/implementation/CURRENT_STATE.md`, the RA-EXP-01 design document and this task record.
- Verification: 53 focused Django tests passed; full isolated Django suite **307/307** passed; JavaScript behavior tests **11/11** passed. System check, migration-consistency dry-run, JS syntax and diff whitespace checks passed. Tests verify notes retention/backend access and panel absence, hidden/configurator-associated announcement structure, persistence across repeated updates, and unchanged focus/filter behavior.
- Limitations: No real-browser or screen-reader execution available locally; the JavaScript suite uses an instrumented DOM/Fetch boundary. No packages, schema changes, platform pages, RA-EXP-02 navigation, Git staging, commits or pushes were introduced.
- Cleanup preservation check: Development database fingerprint, Git index and all unrelated source/probe fingerprints match their starting values. The pre-existing database modification remains untouched. No staging, commit or push occurred.
