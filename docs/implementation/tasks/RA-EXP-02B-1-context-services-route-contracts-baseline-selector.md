# RA-EXP-02B-1 — Context Services, Route Contracts, and Baseline Vehicle Selector

Status: Implemented and tested — preservation discrepancy unresolved; later tasks not authorized
Implementation/verification date: 2026-10-26
Branch: `experiment/vehicle-hub-ui`

## Dated status clarification — 2026-10-27

This record retains B-1's original scope, Python 3.14 verification commands and 339-test checkpoint. Current development uses `venv/py313/bin/python` without the historical `PYTHONPATH` workaround. Later authorized photographic selector/thumbnail and compact Vehicles disclosure work is documented in `RA-EXP-vehicles-selector-visual-integration.md` and `RA-EXP-vehicles-navigation-quick-selector.md`; its latest recorded full verification is 350 Django and 17 JavaScript tests passed. The compact disclosure does not implement the deferred five-category contextual shell, B-2–B-5 or selector dialog. Browser responsive/keyboard/accessibility acceptance remains pending.

The historical database/IDE fingerprint discrepancy below remains unresolved. Later task-local matching database hashes do not establish preservation across B-1, and the new intentional SQLite snapshot policy does not retrospectively authorize or explain that change. No database investigation, writes, tests or Git mutation occurred during this clarification.

## Objective and governing scope

Implement validated URL-derived vehicle context, shared manufacturer/model discovery, safe additive route contracts, a functional server-rendered selector, and allowlisted pending navigation intent. Follow AGENTS.md, applicable identity/slug/domain ADRs, CURRENT_STATE and the approved RA-EXP-02 architecture. Preserve canonical URLs, exact identity, legacy directory/homepage eligibility, Generation configurator semantics and independent Recently Viewed history.

No session-selected vehicle, database writes, model/schema changes, global navigation UI, Generation/specification layout changes, model category experiences, JavaScript dialog or autocomplete endpoint. B-2 owns category destinations; B-3 owns model Full Specs integration; B-4 owns global navigation. Each requires separate director authorization. No staging, commit, push, reset, restore, clean or stash.

## Implementation and acceptance

- `VehicleContext` and `get_vehicle_context(route_object)` expose validated manufacturer/model and optional Generation/exact definition. Existing model/Generation/year/exact/Generation measurement views set `vehicle_context` from their resolved objects, with active-ancestry checks. Exact identity is not inferred from year/trim; a hub's existing validated `selected_config` remains separate from its Generation route identity. No arbitrary URL parsing or session selection.
- `discover_vehicle_models` and `discover_manufacturers` share name-search predicates, support manufacturer filtering, and make populated-only eligibility explicit. Selector includes active models without canonical definitions; homepage/directory preserve their existing policies and legacy grouping edge cases.
- `/select-vehicle/` (`reference:vehicle-selector`) supports GET `q`, `manufacturer`, `destination`; optional `model` carries explicit pending model selection within the selector. Native labeled search, grouped manufacturer/model links, manufacturer filter/clear links and distinct empty/no-result states work without JavaScript. Search length/slug input and destination choices are validated. Invalid input returns 400; valid-format unknown/inactive ancestry returns 404. POST returns 405.
- Missing destination defaults to `generations`. Only `generations`, `builds`, `maintenance`, `measurements`, `full-specs` are accepted. Intent survives search/filter/selection links. Arbitrary `next` parameters are ignored and never used as destinations; no redirect endpoint is introduced.
- `VEHICLE_DESTINATIONS` defines token, label, intended route name, path contract and implemented status. `resolve_vehicle_destination` returns real URLs only for implemented routes. Generations uses the canonical model URL. Other selections use same-origin server-generated selector URLs and identify the pending destination and selected model, with an explicit Generations alternative. They do not claim category functionality or navigate to unregistered paths.
- A single reference namespace now includes the canonical vehicle patterns beneath `vehicles/` and the selector outside that slug tree; existing names/URLs, measurements precedence and year-versus-definition ordering are preserved. `/explore/vehicles/...` contracts remain unregistered until their views exist.

## Files changed

- `reference/services.py`: context, active-model resolution, shared discovery, immutable destination contracts, safe URL resolution and selector query coordination; homepage query reuses explicit populated policy.
- `reference/forms.py` (new): bounded search/slug input and allowlisted destination validation.
- `reference/views.py`: thin selector view, shared directory discovery and explicit object-derived context integration.
- `reference/urls.py`, `config/urls.py`: selector route within the existing reference namespace, preserving canonical vehicle routes.
- `measurements/views.py`: expose context from the already validated Generation.
- `templates/reference/vehicle_selector.html` (new): native server-rendered selector and pending state; existing shared shell/styles are sufficient, no CSS added.
- `reference/tests/test_vehicle_navigation.py` (new): 20 focused functional/security/regression tests.
- `docs/implementation/CURRENT_STATE.md`, `CHANGELOG.md`, this task record: verified implementation and deferred boundaries.

## Migrations and architectural decisions

No models, migrations, dependencies or ADRs created/modified. Approved URL authority, separate explore contracts, selector eligibility and server-rendered baseline are reused. The durable context ADR and permanent route policy remain deferred. Pending categories stay on the selector as explicitly permitted by this task; no substitute category experience is introduced. No implementation scope deviations. The final preservation discrepancy is recorded below and remains unresolved.

## Verification actually executed

Environment for every Django invocation:

```bash
export PYTHONDONTWRITEBYTECODE=1
export PYTHONPATH=.venv/lib/python3.14/site-packages
export RIGARCHIVE_TEST_DB_PATH=:memory:
```

Existing `python3` is Python 3.14.6, using existing virtualenv Django 6.0.7 dependencies. No software installation/upgrade occurred. The virtualenv launcher itself is unusable in this sandbox; the existing interpreter/dependency combination matches prior task verification.

```bash
python3 -B manage.py check
python3 -B manage.py makemigrations --check --dry-run
python3 -B manage.py test reference.tests.test_vehicle_navigation --noinput
python3 -B manage.py test reference.tests.test_vehicle_navigation reference.tests.test_views reference.tests.test_experimental_hub measurements.tests --noinput
python3 -B manage.py test --noinput
node --test reference/tests/js/generation_configurator.test.cjs
git diff --check
```

Results: system check passed; no migration changes; **20 focused tests passed**, **99 combined focused tests passed**, **339 full-suite tests passed**, **11 JavaScript tests passed**; whitespace check passed. Full suite was repeated after the final selector service extraction/manufacturer-filter correction and passed 339/339. No required check failed. Tests use isolated in-memory databases and existing tests' temporary artifact resources; this change introduces no uploads/media writes. No application requests or management commands targeted the development database. Existing ingestion tests print simulated execution receipts while operating on their isolated resources; they do not authorize development canonical writes.

Coverage includes active/inactive ancestry; discovery and unpopulated models; legacy directory/homepage behavior; search/filter/empty/error states; all destination tokens; pending-intent/bookmark reproducibility; safe redirect handling; escaping and bounded inputs; native GET/405 behavior; all existing context routes; ambiguous trim without exact inference; no session-selected writes; selector SQL read-only behavior; canonical reversals and Generation slug collision avoidance; deferred paths/names remain unavailable.

## Preservation and limitations

Initial working tree: modified `db.sqlite3`; three untracked Codex probe files; the pre-existing untracked RA-EXP-02 architecture document; no staged changes. An intermediate fingerprint comparison confirmed database/unrelated-file preservation after the first full suite. The final comparison subsequently detected changes to `db.sqlite3` and `.idea/workspace.xml` outside this implementation’s edits. The cause is not established; no development-database write or IDE edit was intentionally issued. Byte-for-byte database and unrelated-file preservation cannot be confirmed across the complete task. No restoration/reset was attempted. Probes, the architecture document, Git staging and all other existing files outside the listed implementation edits remained unchanged. Initial database SHA-256: `164658a5f5ae2cef166cf109e5fa583b601e43b6164d97e14fdfa42ceecde4e5`.

No commit or push performed. No application/browser request was made against the development database. No real-browser visual/assistive-technology verification was performed; later approved visual and acceptance checkpoints remain required. B-2 onward, category routes/views, global navigation, dialog, photographic evidence, provenance/verification, configuration-feature mapping, permanent route acceptance and durable ADR remain deferred. Stop after B-1; await separate director authorization.
