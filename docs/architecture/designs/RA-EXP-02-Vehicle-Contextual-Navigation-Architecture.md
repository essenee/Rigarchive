# RA-EXP-02 — Vehicle-Contextual Navigation Architecture

**APPROVED ARCHITECTURE — ORIGINAL RA-EXP-02A AUTHORIZATION CHECKPOINT**

### Dated implementation clarification — 2026-10-27

The original “implementation not yet authorized” language, route/service inventory, section 13 “implementation has not begun” statement and closing B-1 status below describe the 2026-10-26 architecture-only milestone. They do not describe the current branch. B-1 was subsequently authorized and implemented; separately authorized work added the photographic Explore Vehicles selector, compact thumbnails and the Vehicles manufacturer/model disclosure. See `../../implementation/tasks/RA-EXP-02B-1-context-services-route-contracts-baseline-selector.md`, `../../implementation/tasks/RA-EXP-vehicles-selector-visual-integration.md` and `../../implementation/tasks/RA-EXP-vehicles-navigation-quick-selector.md`.

The compact nonmodal disclosure is a bounded experimental addition beside the Vehicles link. It does not implement or authorize the five-category contextual shell, B-2–B-5, model category destinations, or the optional selector dialog. Original architectural decisions and task-specific approval requirements remain unchanged. Latest recorded checks are 350 Django and 17 JavaScript tests passing under Python 3.13; no tests were rerun for this clarification. Browser responsive/accessibility acceptance remains pending. The historical B-1 database/IDE fingerprint discrepancy remains unresolved; later matching task-local hashes do not resolve it.

The application-inventory omission and RA-EXP-01 Git-status wording reported in the original evidence section are reconciled by dated documentation updates on 2026-10-27. The temporary SQLite staging policy is recorded in `../../development/DATA_PRESERVATION.md`; no tracking or deployment changes are made here.

Date: 2026-10-26. Analysis task: RA-EXP-02A. Branch: `experiment/vehicle-hub-ui`.
The director has approved this experimental architecture and the five-task decomposition in section 11. Each implementation task requires separate director authorization. This documentation-only finalization does not authorize application changes or record implementation.

## 1. Executive summary

Keep **Generations | Builds | Maintenance | Measurements | Full Specs** visible globally. A shared searchable manufacturer/model selector establishes model context. Derive authoritative context from validated URL objects, never from a remembered session selection. Reuse the existing model detail as the Generations destination, preserve Generation and canonical VehicleDefinition URLs, add a model-level Measurements entry, and reuse the RA-EXP-01 Generation configurator for Full Specs.

Builds and Maintenance currently have no public domain implementation. Their approved model-scoped interim landing pages must be useful: identify the selected manufacturer/model, explain that the underlying capability is not implemented, and offer real links to that model’s Generations and Measurements destinations and to Change vehicle. Do not fabricate records, counts, submission actions, or applicability claims. An unavailable capability must not be presented as an empty collection. These landing pages are not yet implemented.

No new app, dependency, model, schema, canonical identity, or package hierarchy is proposed. Navigation presentation belongs in the existing site shell; reference selection queries belong in reference application services; measurement queries remain in measurements. Do not put navigation services in core: ADR-0003 reserves it for abstract model infrastructure.

### Evidence and authority

Inspected AGENTS.md, GEMINI.md, ADR-0001–0009, CURRENT_STATE.md, RA-EXP-01 design and Task 1/2 records, RA-042 measurement design, the Engineering Handbook architecture and relevant implementation chapters (9A–9C, 10), and Project Blueprint. Source inspection covered config/reference/measurements URLconfs and views, reference services/models, installed apps, shell and destination templates, CSS, configurator JavaScript and relevant test files.

ADRs 0001/0002 preserve identity and immutable slugs; ADR-0009 governs measurements. ADRs 0004–0008 govern ingestion/canonicalization; navigation must not invoke those write workflows. Older handbook/blueprint Variant terminology does not introduce a Variant model or mandatory package stage here; the explicit task and actual reference implementation govern this proposal.

Repository status is authoritative: installed local apps include core, accounts, reference, observation, measurements. CURRENT_STATE's initial application list omits measurements; later experiment records describe it. The RA-EXP-01 design still contains historical uncommitted-task wording. Git shows Task 1 (`54ada80`) and Task 2 (`1764499`) committed, consistent with this task. These stale status statements are reported, not edited. No competing identity or measurement rule is resolved by changing governance.

## 2. Current route inventory

Notation: `M` = manufacturer_slug, `V` = vehicle_model_slug, `G` = generation_slug, `D` = vehicle_definition_slug, `Y` = integer model_year; slug segments use Django's slug converter. All vehicle paths start `/vehicles/`. Functional means supported by source, not live-browser or development-data verification. All listed public views render directly; none currently redirects.

| URL | Route name | View | Template | Required context / behavior |
|---|---|---|---|---|
| `/` | home | config.views.home | home.html | None; platform cards, search, session Recent history; functional with some placeholder cards/links |
| `/about/` | about | config.views.about | about.html | None; functional informational page |
| `/vehicles/` | reference:manufacturer-list | ManufacturerListView | reference/manufacturer_list.html | None; active populated manufacturer/model directory; `q` name search; functional |
| `/vehicles/M/` | reference:manufacturer-detail | ManufacturerDetailView | reference/manufacturer_detail.html | Active manufacturer; populated active models/generations; functional |
| `/vehicles/M/V/` | reference:vehicle-model-detail | VehicleModelDetailView | reference/vehicle_model_detail.html | Valid active manufacturer/model pair; active generations including ones without definitions; functional |
| `/vehicles/M/V/G/` | reference:generation-detail | GenerationDetailView | reference/generation_detail.html | Valid active ancestry; hub, configurations and measurements work; editorial/build/service panels incomplete |
| `/vehicles/M/V/G/Y/` | reference:model-year-overview | ModelYearOverviewView | reference/model_year_overview.html | Active generation, bounded year and active definitions; otherwise 404; groups configurations by trim |
| `/vehicles/M/V/G/D/` | reference:vehicle-definition-detail | VehicleDefinitionDetailView | reference/vehicle_definition_detail.html | Active exact definition under validated ancestry; functional canonical specifications |
| `/vehicles/M/V/G/measurements/` | measurements:generation-measurements | GenerationMeasurementsView | measurements/generation_measurements.html | Active generation ancestry; active independent results and empty state; functional |
| `/admin/` and descendants | admin:* | Django admin | Django admin templates | Staff permissions; administrative management, not public selection/navigation |

`/vehicles/?q=...` supports manufacturer/model name substring search. There is no dedicated JSON/autocomplete endpoint, trim search, configuration search, topic search, Builds route, Maintenance/service-guide route, Garage route, or model-level Measurements route. `?view=measurements` is ignored by ManufacturerListView and does not create a measurement workflow. Generation GET parameters `year`, `trim`, `configuration` are filters on the existing hub, not new routes. Query filtering no longer redirects to specifications. The integer year pattern precedes the generic definition slug pattern; preserve that resolution behavior. Measurements URLconf is included before reference URLconf.

## 3. Existing selection-service inventory

| Component | Current responsibility | Reuse / constraint |
|---|---|---|
| ManufacturerListView.get_queryset | `q` across manufacturer/model names; active ancestry and active canonical-definition coverage; filtered model prefetch | Reuse search semantics and extract a shared query service for selector/directory; not a configuration resolver |
| ManufacturerDetailView | Active manufacturer with populated model/generation links | Retain public browsing; not a second selector workflow |
| VehicleModelDetailView | Validates manufacturer/model pair, lists active generations | Reuse as model-scoped Generations experience |
| get_homepage_context | Featured populated models and generation cards, recently viewed | Keep homepage discovery; do not make selector depend on featured ordering or demo image preferences |
| get_generation_hub_context | Resolves active year, trim and exact configuration, options and error notices | Authoritative existing canonical selection rules; reuse unchanged semantics |
| _label_configuration_choices | Distinguishes canonical records by varying trim/engine/drivetrain, then market and slug | Reuse via existing service output; do not collapse ambiguous records |
| ModelYearOverviewView | Bounds checks, active definitions for year, trim grouping and canonical links | Preserve existing direct URLs; not a replacement canonical resolver |
| get_full_specifications_context | Exact identity, same-year siblings, generation-wide vs conditional measurements, receipts | Reuse exact detail destination; no invented feature mapping |
| get_absolute_url on reference models | Named canonical links | Use reverse/model URLs instead of assembled user-provided paths |
| record_recently_viewed_generation | Five generation visits in session | History only; never use as selected vehicle authority |
| generation_configurator.js | Same-path HTML fetch; replaces configuration-content, abort/sequence safety, focus/viewport, pushState/popstate, GET fallback | Keep page-local; selector must not intercept its links or replace its panels |

Canonical hierarchy in storage is Manufacturer → VehicleModel → Generation → VehicleDefinition. Model year and trim are fields on definitions, not new entities. A trim is not an exact identity. Empty `trim=` means an unnamed trim; absent trim means no filter. A configuration-only query can infer its year; explicit blank, invalid or mismatched years cannot be overridden. Invalid/inactive/cross-generation configuration choices produce notices and no exact selection. No year/trim silently selects a default definition, even when a list is small. The browser presents year → trim → configuration with separate canonical Specs links. Packages are not a mandatory stage and no package-selection capability is established by these services.

### Current navigation findings

The shell has Vehicles, Measurements, Builds, Service Guides and About, plus search and unavailable My Garage. Vehicles is marked active for both reference and measurements namespaces; this cannot identify the five new categories correctly. Header search promises configs/topics but searches only manufacturer/model names. Homepage search examples similarly imply unsupported year/trim search. Both forms use the same directory endpoint and can become entry points to the shared selector instead of separate logic.

Builds/service links use fragment placeholders; homepage has no matching content destinations. Generation build/service anchors reach only unavailable panels. Generation overview links for history, platform-design, powertrains, year-changes and production-numbers lack implemented article destinations; `aria-disabled` on an anchor alone does not prevent activation. Garage points to an unavailable homepage fragment. Replace these misleading affordances only in an approved navigation scope; do not invent destinations for editorial articles or Garage.

Breadcrumbs mostly repeat inline markup; an includes/breadcrumbs.html component exists, but destination templates use their own ancestry markup. Exact pages return to the Generation URL with year/configuration query values. Measurement links correctly carry generation ancestry. There is no global selected-model contract. Mobile uses the same header/nav wrapping in CSS (not a separate mobile menu or menu script). Current configurator is the single remaining Generation selection interface; do not add another upper configurator.

## 4. Domain readiness assessment

| Category | Working today | Missing |
|---|---|---|
| Generations | Model detail lists generations; Generation hubs | Global context-aware entry/navigation |
| Builds | Only unavailable copy/panels | Public builds/modifications domain experience and model-scoped listing |
| Maintenance | Only service-guide unavailable copy/panels | Public maintenance/guides domain experience and applicability architecture |
| Measurements | Generation results, hub summaries, exact page conservative presentation | Model entry/discovery page and global continuation |
| Full Specs | Canonical exact detail, model-year overview and Generation year/trim/configuration browser | Model-scoped selection entry and explicit global tab behavior |

Observation foundation is not evidence that Builds or Maintenance are implemented. No development database content or coverage counts were queried for this assessment.

## 5. Approved global navigation

Expose the new global navigation only after every destination has valid functionality or an honest interim landing page. Once exposed, render all five ordinary navigation links on every public shell page, with a nearby “Select vehicle” or “Toyota · 4Runner — Change vehicle” link. Manufacturer/model is the persistent scope; generation/year/trim/exact identity remains visible in page context and breadcrumbs, not silently promoted to a universal applicability claim. Keep About as a secondary/footer link. Do not keep unsupported broad search promises.

Without model context each category href is `/select-vehicle/?destination=<token>`. With model context it points to its model destination, except Full Specs can use a validated exact identity or current Generation as described below. Builds and Maintenance links stay operable and visible, reaching useful model-specific interim landing pages after selection. They are not disabled fake content links.

```text
Any public page → five persistent categories
  no model → selector?destination=measurements → manufacturer/model
                                                ↓
                                  model Measurements entry
                                                ↓
                                  existing Generation measurements

model Full Specs entry → Generation hub#configurations
                       → Model Year → Trim → Exact Configuration
                       → existing canonical specification URL
```

## 6. Vehicle-context authority rules

1. Resolve the object using the route and validate its complete active ancestry. Model page supplies model/manufacturer; Generation supplies its model/manufacturer; exact page supplies Generation/model/manufacturer. Model-year and generation measurements pages do likewise. Invalid ancestry returns 404; never fall back to a session vehicle.
2. Query parameters refine only supported selections under that resolved object. Validated service output, not raw query text, supplies labels and specificity. Contradictory selections follow existing notices and cannot establish exact identity.
3. On homepage/About/directory/error pages without a resolved model, display “No vehicle selected.” Manufacturer alone is insufficient. A manufacturer-specific selector can be prefiltered without implying a selected model.
4. Global selection navigates to a model-scoped URL for the pending category; it does not merely change a header label on the old page. Changing model clears Generation/year/trim/configuration specificity. It preserves only the category intent.
5. Bookmarks and back/forward reconstruct everything from their URL. No global selection is synchronized between browser tabs or through session state. Session Recently Viewed remains separate history. Do not introduce selected-model session writes.
6. Selected objects are request-local presentation values (manufacturer/model and optional Generation/exact definition), not new persisted domain concepts. A small explicit context assembler used by relevant views supplies shell labels, destinations and active category. No middleware that reparses arbitrary URL strings or queries unseen session IDs is needed.

URL authority gives shareable, multi-tab-safe and cookie-independent behavior. Session authority would make identical URLs show conflicting vehicles, allow one browser tab to change another's apparent context, and require stale/inactive-record recovery. A future “Resume last vehicle” convenience may offer a labeled URL link, but must not override current route context; it is outside this proposal.

## 7. Searchable selector design

Use `/select-vehicle/` with GET fields `q`, optional `manufacturer`, and `destination`. The server renders grouped manufacturer headings and explicit model links. Search matches manufacturer OR model names using current case-insensitive substring semantics; manufacturer matches expose its eligible models. A manufacturer filter/browse link narrows results; each model label includes manufacturer. Selecting a model follows a server-generated destination URL. No intermediate hidden session selection is needed.

Use shared reference discovery query primitives for directory and selector with explicit eligibility policies. Selector eligibility is active manufacturer + active model, even without canonical definitions: this supports measurement discovery independently of specification coverage. Show coverage/empty states honestly. Keep existing homepage/directory eligibility rules unchanged unless separately approved; preserve their populated-only behavior explicitly. No new database fields or write services.

Pending intent is an allowlisted category token: `generations`, `builds`, `maintenance`, `measurements`, `full-specs`. Default missing intent to generations; reject unknown tokens with a clear form error. Never accept arbitrary `next` URLs. Preserve token in GET hidden inputs, search submissions, manufacturer-filter links and pagination if later needed; each model result receives the reversed allowed destination. Search terms/filter values are escaped and bounded; manufacturer slugs must resolve as active. No session storage, localStorage or free-form return path.

The approved baseline is explicit server-rendered GET Search submission, manufacturer filter links and model result links, with no autocomplete API. Defer the optional JavaScript dialog until this baseline has been implemented and visually reviewed. The dialog also requires separate authorization; it is not part of RA-EXP-02B-4. Dialog and incremental-fetch behavior described in section 10 are future design constraints only, not part of the baseline implementation scope.

## 8. Destination-specific navigation behavior

**Generations:** Link to existing `/vehicles/M/V/`. Show its current active generation list and links to preserved hubs. No duplicate `/generations/` listing, homepage copy or forced year selection.

**Builds:** A useful model-specific interim landing page identifies the selected manufacturer/model, states that Builds functionality is not implemented, and offers real model Generations/Measurements links and Change vehicle. Do not describe an empty build collection, fabricate records/counts, offer submission capabilities or claim applicability. Future approved build services can replace the interim body at the same URL. No build models/app are authorized here.

**Maintenance:** Equivalent useful model-specific interim landing page, explicitly identifying unimplemented functionality rather than an empty maintenance collection. Include real model Generations/Measurements links and Change vehicle; no fabricated records/counts, submissions or applicability claims. Future content must carry supported applicability, potentially Generation/year/engine/drivetrain/exact configuration; model grouping never implies universal applicability. Do not pretend existing service-guide anchors are a functional guide archive.

**Measurements:** New model entry lists active generations and links to existing generation measurement pages; it may show active report counts calculated by measurements services, including explicit zero states. Do not require exact selection, hide generations solely for lacking factory definitions, aggregate reports into a single truth, or mix results across generations. Retain independent records, result-owned units, notes, zero-condition “Generation-wide” labeling and AND conditions. Selecting trim/year/exact configuration never establishes physical feature states. Feature mapping, evidence uploads/photographs and verification remain deferred.

**Full Specs:** Model entry lists generations for explicit selection, with canonical-coverage notices; generation links go to existing hub `#configurations`. The current hub is suitable for the remaining year → trim → exact configuration steps; do not create a competing wizard. Reuse `get_generation_hub_context` and existing configuration choice labels. Ordinary users may still browse year overview/direct Specs links; the global workflow must not imply that year/trim resolved exact identity. No arbitrary default or implicit first record. If no canonical definitions exist, explain this and keep generation/measurement discovery available.

On a Generation page, Full Specs links directly to its existing `#configurations`; on an exact page, it links to that canonical exact URL. A hub with a valid service-resolved `selected_config` may likewise link to that exact URL. Otherwise a hub stays at the configurator, preserving only validated year/trim query state via server-generated links. No new query mode is necessary. This avoids interfering with the configurator script's panel-only updates. Active tab on a hub remains Generations even at its configuration anchor; label the section “Configurations & Specs.” Full Specs is active on model selection entry, year overview and canonical exact pages. Clicking a model-scoped category otherwise deliberately returns to that category's model entry; narrower context is visible on the current page but is not silently carried as a global filter.

## 9. Approved experimental URL/view map

The additive `/explore/vehicles/M/V/.../` structure is approved for experimental implementation and may be reconsidered before merging into main. Public canonical routes in section 2 remain unchanged. New view/route names below define implementation contracts to verify; they are not claims of existing functionality.

| Pattern | Name | View responsibility / context | Exists / work / canonical relationship |
|---|---|---|---|
| `/select-vehicle/` | reference:vehicle-selector | VehicleSelectorView: GET search, manufacturer browse, allowlisted intent, model destination links; no required model | New; reference service + template needed; outside slug tree |
| `/vehicles/M/V/` | reference:vehicle-model-detail | Existing model/generations listing and shell context | Exists; context/navigation integration only; canonical model URL |
| `/explore/vehicles/M/V/builds/` | vehicle-builds-entry | config model Builds interim landing view; validated manufacturer/model via reference service | New; useful honest interim landing template; no Builds domain implementation |
| `/explore/vehicles/M/V/maintenance/` | vehicle-maintenance-entry | config model Maintenance interim landing view; same validation | New; useful honest interim landing template; no Maintenance domain implementation |
| `/explore/vehicles/M/V/measurements/` | measurements:model-measurements | ModelMeasurementsView: validated model and generation discovery, measurements service queries | New; URL include under explore prefix; existing Generation measurement URLs retained |
| `/explore/vehicles/M/V/full-specs/` | reference:model-full-specs | ModelFullSpecsView: validated model and explicit generation selection with coverage notices | New; reference URL include under explore prefix; links to canonical hub/configurator |
| `/vehicles/M/V/G/` (+ existing GET filters, `#configurations`) | reference:generation-detail | Existing hub/configurator; URL-derived shell context | Exists; shell integration only; no alias/replacement resolver |
| `/vehicles/M/V/G/Y/` | reference:model-year-overview | Existing year browse | Exists; keep URL and 404 rules |
| `/vehicles/M/V/G/D/` | reference:vehicle-definition-detail | Exact Full Specs | Exists; preserve canonical identity and URL |
| `/vehicles/M/V/G/measurements/` | measurements:generation-measurements | Existing results experience | Exists; shell integration; canonical generation measurements URL retained |

Use separate named URLconfs/includes for new explore routes without changing existing reference namespace reversals (Django application/instance namespace setup must be verified in implementation). Names shown are desired reverse contracts, not permission to duplicate a namespace incorrectly.

The `/explore/vehicles/` prefix is deliberate: `/vehicles/M/V/measurements/`, `/builds/`, or `/full-specs/` would compete directly with the existing arbitrary Generation slug segment. Ordering static routes first could make existing generations with those immutable slugs unreachable. No reserved-word assumption or database survey is required with a separate prefix. The prefix also avoids arbitrary manufacturer slug collisions at `/vehicles/select/`.

No existing public view redirect should be retained/changed because none currently implements one. Retain historical Generation-filter URLs as in-place filters, not redirects to guessed configurations. Selector model links directly target reversed routes; no redirect endpoint is necessary. Remove ignored `view=measurements` from rendered discovery links when navigation is implemented. Old bookmarks with that query can retain current directory behavior; do not promise a new redirect that reinterprets a bookmark's manufacturer intent as selected model context.

## 10. Accessibility and progressive enhancement

Use a labeled primary navigation landmark and ordinary links, not ARIA tab widgets: these change documents. Apply `aria-current="page"` only to the current destination; use a visual category indication plus appropriate current semantics for descendant pages without falsely marking several exact pages current. Explicit view metadata maps categories, rather than checking only app namespace. No category is active on the homepage/About/directory. Selector can indicate “Choosing a vehicle for Measurements” without claiming content is loaded.

Keep all five category labels visible on mobile in a wrapping row/grid, outside a collapsed menu. Preserve readable touch targets, focus indicators, contrast, zoom/reflow and a clear Change vehicle control. No hover-only controls. Existing header CSS needs deliberate responsive evaluation; no separate framework or duplicate mobile selector.

The baseline full selector page has an H1, visible search label, native search submit, results count/no-results message and grouped model links; Tab/Shift+Tab, Enter and normal browser navigation suffice. Do not intercept arrow keys in a native link list. Deferred enhancement only, after baseline implementation and visual review: a dialog must have an accessible name, initial search focus, contained keyboard focus, Escape/close control, background inertness and focus restoration to its invoking link. Use polite result announcements without announcing every keystroke. Cancel leaves the original URL/context intact; completed selection performs ordinary navigation to the model destination.

Full-page GET search state is bookmarkable. For that deferred enhancement, dialog opening/search need not push history or change underlying vehicle URL; completion navigates normally. Back returns to the preceding URL; forward restores its context. Keep existing configurator pushState/popstate handling isolated and do not install a global click interceptor over its links. If a browser restores a page from cache, labels must remain tied to that page's URL, never resynchronized from a session/global store.

Breadcrumbs use Home → Vehicles → Manufacturer → Model → current category, with Generation/year/exact detail where actually represented. Preserve canonical ancestor links; avoid inserting invented trim-detail pages. Generation measurements ends Generation → Measurements. Exact details may include a real year-overview link before the exact configuration when available. Use the existing breadcrumb partial where practical with current-page semantics; do not turn this into unrelated sitewide template refactoring.

Distinguish valid empty content (200, explicit no reports/configurations), unavailable capability (200 useful model-specific interim page clearly identifying unimplemented functionality, never an empty collection), invalid/inactive ancestry (404), invalid selector intent (form error) and conflicting hub query filters (existing notices/no exact selection). Never use dead `#` links as substitute destinations. A no-JavaScript category click follows the selector page; hidden intent survives GET submissions; final model result link reaches the intended category. The full Generation configurator already has native GET fallback.

## 11. Approved implementation decomposition

The approved order is **RA-EXP-02B-1 → RA-EXP-02B-2 → RA-EXP-02B-3 → RA-EXP-02B-4 → RA-EXP-02B-5**. Each task requires separate director authorization. Architecture approval alone does not authorize implementation, including RA-EXP-02B-1. Each task builds on the preceding contracts and experiences; focused verification belongs within each task, followed by complete integration verification in task 5.

### RA-EXP-02B-1 — Context Services, Route Contracts, and Baseline Vehicle Selector

Implement:

- Validated URL-derived vehicle context.
- Shared reference discovery queries.
- Safe route contracts.
- Server-rendered manufacturer/model selector.
- Allowlisted pending destination tokens.
- Model eligibility independent of canonical-definition coverage.

Preserve existing canonical URLs, directory behavior, and Generation configurator semantics. Do not introduce session-selected vehicle state. Keep existing homepage eligibility rules unchanged. Route contracts for later destinations do not justify exposing global navigation before those destinations exist.

**Completion checkpoint:** Functional route, context, selection, and regression tests.

### RA-EXP-02B-2 — Model-Scoped Category Destinations

Implement:

- Model-scoped Measurements discovery.
- Useful, model-specific interim Builds landing pages.
- Useful, model-specific interim Maintenance landing pages.
- Reuse of the existing Generations model-detail experience.

Builds and Maintenance must clearly identify that their underlying functionality is not implemented. Do not fabricate records, counts, submission capabilities, or applicability claims. Do not confuse an unavailable feature with an empty collection. Preserve existing Generation-level Measurements functionality and applicability rules.

**Completion checkpoint:** Route and content review.

### RA-EXP-02B-3 — Full Specs Navigation Integration

Connect model-level Full Specs discovery to:

1. Explicit Generation selection.
2. The existing Generation Configurations & Specs selector.
3. Existing canonical exact-configuration specification pages.

Reuse existing reference application services and canonical configuration-selection rules. Do not introduce a competing configuration wizard, implicit configuration defaults, a mandatory package-selection stage, or new canonical identity rules. Preserve year, trim, configuration ambiguity handling, and existing no-JavaScript fallback.

**Completion checkpoint:** Exact-identity and configuration-selection regression tests.

### RA-EXP-02B-4 — Global Navigation and Selector UI

Implement persistent global navigation: **Generations | Builds | Maintenance | Measurements | Full Specs**.

Include:

- Selected manufacturer/model display.
- Change Vehicle control.
- Context-aware navigation destinations.
- Responsive layouts.
- Clear active-category indication.
- Integration with the server-rendered selector.
- Accurate search wording.
- Removal of misleading global navigation links.

All five categories must remain visible. Do not expose a category until it has a functioning destination or an honest interim landing page. Accordingly, expose the complete new navigation only after all five destinations are ready. The server-rendered selector is the required baseline.

**A visual review checkpoint is mandatory before considering an optional JavaScript dialog enhancement.** Do not implement the dialog as part of this task without separate authorization.

**Completion checkpoint:** Director visual and interaction review.

### RA-EXP-02B-5 — Accessibility and Integration Verification

Verify the complete navigation system, including:

- URL resolution and route reversals.
- Context correctness across direct links and bookmarks.
- Invalid or inactive vehicle ancestry.
- Pending destination preservation.
- Search and selector behavior.
- Keyboard navigation and focus management.
- Responsive/mobile presentation.
- No-JavaScript fallback.
- Browser back/forward navigation.
- Exact configuration identity preservation.
- Existing Generation configurator behavior.
- Measurements applicability and independent-result presentation.
- Honest unavailable-content states.
- No open redirects.

Use isolated test databases and preserve the development database. Run Django system checks (`python manage.py check`), migration-consistency checks (`python manage.py makemigrations --check`), focused tests, and the full test suite (`python manage.py test`). These are requirements for the separately authorized implementation verification task, not commands executed during architecture finalization.

**Completion checkpoint:** Final experimental navigation acceptance review.

### Remaining deferred capabilities

- Builds domain implementation.
- Maintenance domain implementation.
- Photographic measurement evidence.
- Structured measurement provenance and verification.
- Configuration-to-feature-state applicability mapping.
- Optional JavaScript vehicle-selector dialog.
- Permanent route-policy acceptance before merging into `main`.
- A durable navigation/context ADR, to be considered after experimental evaluation.

No task authorizes canonical data population or development database writes. Experimental route approval is not permanent route-policy acceptance for main.

## 12. Risks and compatibility considerations

- Additive discovery URLs avoid immutable slug collisions and preserve inbound links. Verify include ordering and named reverse behavior explicitly.
- Discovery currently couples eligibility to canonical definition coverage. Broadening selector coverage must be explicit and tested, with empty specifications states; do not silently change homepage counts or directory semantics.
- Existing Generation visits modify database-backed sessions through Recent history. Source inspection did not request pages or invoke that view; implementation verification must use isolated databases and must not casually browse/write the development database without authorization.
- A new context helper is a presentation contract using reference services, not a global domain layer. Keep config status views thin and measurements queries owned by measurements; future domain ownership may replace status views without changing URLs.
- Exact identity and ambiguous trims must remain untouched. Receipt presence and recorded measurements do not establish verification; never infer feature applicability from commercial trim/package names.
- Existing editorial/Garage placeholders and homepage illustration limitations remain separate unless a bounded navigation task explicitly includes those links. This document does not authorize broad content cleanup.
- No live route requests, record counts, browser behavior or accessibility claims were verified. Runtime tests were unnecessary for this design-only task. The repository virtualenv interpreter could not load its Python framework in this sandbox; the available Homebrew Python was used only for standard-library file/document inspection.

## 13. Director-approved architectural decisions

The following decisions are approved for the experiment; implementation is not yet authorized and has not begun:

1. **Vehicle context:** validated URL objects are authoritative. Do not introduce session-selected vehicle state; Recently Viewed remains independent.
2. **Routes:** approve additive `/explore/vehicles/<manufacturer>/<model>/.../` routes for experimental implementation. Preserve canonical URLs. Reconsider the experimental route structure before merging into main if appropriate.
3. **Generations:** reuse existing model detail and Generation hubs.
4. **Builds/Maintenance:** provide useful model-specific interim landing pages that explicitly identify unimplemented functionality. No fabricated records, counts, submission capabilities or applicability claims; unavailable functionality is not an empty collection.
5. **Measurements:** provide model-level Generation measurement discovery, preserving independent results, recorded units, applicability conditions and existing Generation URLs.
6. **Full Specs:** reuse the Generation configurator and canonical specification pages; preserve exact identity and ambiguity handling. No competing wizard or mandatory package-selection stage.
7. **Selector:** server-rendered GET baseline; allowlisted pending category token; support active models without canonical definitions. Existing homepage/directory eligibility rules stay unchanged unless separately approved.
8. **Enhancement:** defer the optional JavaScript dialog until baseline implementation and visual review.
9. **Global navigation:** keep all five categories visible after exposure; do not expose it until every destination has valid functionality or an honest interim landing page.
10. **ADRs:** defer a new context-policy ADR until evaluation for integration into main. Do not create one during experimental documentation finalization.

The complete approved decomposition is recorded in section 11. Architecture finalization is complete; each implementation task still requires separate director authorization.

### Analysis verification and preservation

Correct branch confirmed. Initial working tree: modified `db.sqlite3`; untracked `.codex-protected-test`, `.codex-writable-test`, `.codex-write-test`; no staged changes. Task 1/2 commit IDs inspected. Only this architecture document is added by RA-EXP-02A. No application/template/CSS/JavaScript/model/migration, CURRENT_STATE, changelog, ADR, governance or probe edits; no database connection/management command, migrations, staging, commit or push. Database bytes and existing file fingerprints were compared after document creation. No full test suite was run because this is design-only. The ten architectural decisions and complete decomposition are approved. No implementation task has begun or been authorized by this documentation task.

### Documentation finalization verification

Only this architecture document was edited during finalization. Existing repository file fingerprints, including the development database and Codex probes, were compared before and after the edit and remained unchanged. No application changes, database operations, management commands, migrations, staging, commits or pushes were performed. No runtime tests were required or run. The complete approved decomposition, sequential dependencies, completion checkpoints and deferred capabilities are recorded. Superseded conditional-approval and missing-instruction language has been removed. RA-EXP-02A documentation finalization is complete; RA-EXP-02B-1 has not begun.
