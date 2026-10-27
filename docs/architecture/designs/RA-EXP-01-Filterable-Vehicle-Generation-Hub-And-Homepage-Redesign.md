# Architecture Design Document: RA-EXP-01

**Title:** Experimental Vehicle Knowledge Hub and Homepage Redesign  
**Status:** Experimental work in progress / Pending final evaluation — not complete or approved  
**Branch:** `experiment/vehicle-hub-ui` (Not merged into `main`)  
**Date:** 2026-10-25  
**Governing Documents:** Engineering Handbook Part 1 (Chapters 9A–9C, 10), Project Blueprint v1.1, CURRENT_STATE.md, ADR-0001 through ADR-0009  

---

## 1. Motivation and Context

RigArchive exists to build the world's most trusted technical archive of vehicles—and their modifications and maintenance—used for travel, camping, overlanding, expedition, and living.

The original experiment context reported **698 active canonical factory configurations** across 12 generations (Toyota 4Runner Gen 1–6, Toyota Tacoma Gen 1–4, Volkswagen Touareg Gen 1–2) and recorded physical measurements in the `measurements` domain. These inventory counts were not rechecked against the development database during this documentation reconciliation. Recorded measurements are not automatically verified or canonical truth. However, the user experience prior to this experiment suffered from significant presentation limitations:

1. **Placeholder Homepage:** `templates/home.html` was a 19-line placeholder containing a single text paragraph and a button, communicating none of the archive's depth, photography, or technical utility.
2. **Underdeveloped Generation Page:** The Generation landing page (`reference/generation_detail.html`) suffered from visual asymmetry. The left column contained only a two-dropdown specification selector that redirected away from the page, while conditional sections for measurements and builds were completely disconnected (`context["measurements"] = []`).
3. **Navigational Dead Ends and Friction:** Reaching a specific configuration required 5–6 rigid sequential clicks through the hierarchy. Once on a configuration page, users had no route to sibling trims for the same model year.

This experimental design explores an alternative user interaction model where the Generation page becomes a **comprehensive, filterable vehicle knowledge hub** and the homepage becomes a **content-led technical landing page**.

---

## 2. Intended Conceptual Model: Filterable Generation Knowledge Hub

This section preserves the original architectural intent. It is not a statement that every element is implemented; current behavior and gaps are recorded in Section 7.

### 2.1 The Generation Page as a Primary Destination
In this experimental design, the Generation page is the primary vehicle knowledge hub for a model generation.

- **Initial State (Unfiltered):** Presents generation-wide context, production timeline, architectural highlights, generation-wide physical measurements, and an overview of all available trims and powertrains without requiring a model year or trim selection.
- **Filtering Semantics:** When a user selects a model year or a specific trim configuration, **the selection refines the content shown on the Generation page itself, rather than navigating away**.
- **Preserved Identity:** The Generation page retains its URL (`/vehicles/<mfr>/<model>/<gen>/`) and breadcrumb hierarchy (`Toyota → 4Runner → Fourth Generation`) regardless of active filter parameters.
- **Bookmarkable Filter State:** Filters are represented in URL query parameters (`?year=2007` or `?year=2007&configuration=2007-sr5-40l-v6-4wd-us`).

### 2.2 Prominent Context Banner and Full Specifications Action
The intended presentation when an exact configuration is selected is:
- An **Active Configuration Filter Banner** is displayed prominently, identifying the model year, trim, drivetrain, engine, and commercial market scope.
- A dedicated **View Full Specifications →** action is presented, allowing users who require comprehensive technical data to navigate to the canonical specification sheet.
- When only a model year is selected, a banner identifies the year and total matching configurations, with a link to the dedicated model-year overview.

---

## 3. Intended Relationship Between Generation Hub and Full Specifications

The intended roles are separated as follows; the matrix, powertrain chips, and platform notes below are not fully implemented:

| Dimension | Generation Knowledge Hub | Full Specifications Sheet |
| :--- | :--- | :--- |
| **URL** | `/vehicles/<mfr>/<model>/<gen>/` (with query params) | `/vehicles/<mfr>/<model>/<gen>/<def-slug>/` (canonical) |
| **Role** | General-purpose platform hub, comparative trim overview, generation measurements, platform architecture notes. | Comprehensive, singular technical reference for an exact factory configuration. |
| **Scope** | Generation-wide, refined optionally by year and trim. | Strictly one canonical `VehicleDefinition`. |
| **Content** | Multi-year configuration matrix, powertrain chips, forthcoming build/maintenance scaffolding. | Detailed factory attributes, dual-identity UUID, audit receipts with SHA-256 manifest hash, applicable measurements, sibling trims switcher. |
| **Navigation** | Core hub of the vehicle model. | Dedicated leaf node with direct return link to the Generation Hub. |

Canonical route patterns remain available, and `VehicleDefinitionDetailView` supplies the specification destination. Generation query parameters now filter in place instead of following the previous redirects; this is a behavior change, not a claim of complete backward compatibility.

---

## 4. Intended Filtering and Applicability Semantics

These are intended constraints, not verified implementation guarantees. Current terminology, condition visibility, and filtering gaps are listed in Section 7. ADR-0009 remains authoritative: a recorded result is not automatically canonical truth, and applicability cannot be inferred from trim alone.

1. **Generation-Wide Content:** Platform architecture notes, frame design, production years, and generation-wide physical measurements (`is_generation_wide=True`) apply universally across all filter states.
2. **Model-Year Scoped Content:** When filtered by year, configurations belonging to other model years are excluded from the displayed variant lists. The UI explicitly avoids claiming that attributes of one trim apply to all trims of that year.
3. **Exact Configuration Content:** Should identify one canonical configuration and show measurements only where applicability is established. Current specification pages conservatively show generation-wide measurements; no trim-to-feature inference or verification workflow is implemented.
4. **Epistemic Boundaries for Forthcoming Domains:** 
   - Aftermarket builds and owner modifications are explicitly walled off in forthcoming archival notices. They carry mandatory disclaimers clarifying that owner builds represent individual vehicles and are not factory standard equipment.
   - Measurements are never represented as manufacturer brochure claims; their independent recorded provenance is preserved.
   - Speculative cross-domain compatibility logic is strictly prohibited.

---

## 5. Homepage: Original Direction and Current Presentation

The original experiment proposed a positioning headline (“Know your vehicle. Build with confidence.”), live global statistics, architectural platform tags, a Measured Reality result showcase, and a Four Pillars live/forthcoming presentation. Those elements are absent from the current homepage and are not completed capabilities. In particular, “100% verified provenance” is not an established current metric.

The current template follows the approved wireframe composition more closely: a photo/schematic hero, Vehicle Platforms cards with generation counts and year spans, Explore the Archive category cards, Find a Vehicle search, and Recently Viewed generations. Search handles manufacturer/model names only; Recent history is stored in database-backed sessions. Homepage diagrams contain unsupported literal dimensions, not evidence-linked measurement data. Category cards do not establish that builds, service guides, or a measurement-first index are available.

---

## 6. Architectural Discipline and Technical Boundaries

1. **No Database Schema Changes:** Zero migrations created, zero model modifications.
2. **Preserved Canonical Hierarchy:** `Manufacturer → VehicleModel → Generation → VehicleDefinition` remains unaltered.
3. **Views & Service Layer:** `reference/services.py` coordinates homepage, Generation hub, and specification queries. Services import the image helper from `reference.views`, so full separation from presentation is not achieved.
4. **Vanilla Frontend:** Standard Django templates, vanilla CSS (`static/css/site.css`), and page-local progressive enhancement of server-rendered GET filters. No SPA framework or external UI dependency. The final Task 1 configurator uses native GET links as fallback and page-local progressive enhancement; the duplicate upper form was removed.
5. **Task 1 Verification:** Initial Task 1 passed 297/297 and compact refinement passed 303/303; the navigation correction passed 305/305; the final layout refinement passed 306/306; the latest cleanup passed **307/307 Django tests** using an isolated database, plus **11 JavaScript behavior tests** using an instrumented DOM/Fetch boundary. All 53 focused Django tests passed. The JavaScript syntax check also passed; real-browser execution remains unverified. System check passed, migration dry-run found no changes, and diff whitespace checks passed. Historical checkpoint: 286 executed, 273 passed, 13 failed; CSS restoration had resolved two prior CSS failures without introducing new ones. Task 1 repairs functional regressions and reconciles stale presentation assertions with substantive behavior coverage. This is not approval/completion of the overall experiment.

---

## 7. Known Limitations and Evaluation Criteria

### 7.1 Current Implementation and Limitations

- **Implemented:** Data-driven homepage platform cards, manufacturer/model-name search, session-backed Recently Viewed, Generation photo/identity and statistics, year/trim GET filtering, exact-configuration slug handling in the service, generation measurement queries, and a year → trim → matching-configuration browser. Specification pages include canonical identity, engine/drivetrain, configuration notes, generation-wide measurement summaries, receipt information, and same-year sibling links.
- **Task 1 repaired identity/filtering:** Exact selection displays the distinguishing canonical attributes and a canonical specifications link. The dropdown chooses exact configurations and is disabled until a year is selected; trim navigation does not silently choose a configuration. Empty trims are selectable through `trim=` and labeled Unnamed trim, distinct from an absent trim filter. A configuration-only URL resolves its year before dependent choices; explicit blank/invalid/mismatched years cannot be overridden. Invalid, inactive, mismatched and cross-generation configuration selections are rejected with a notice. Year controls both use newest-first ordering; configuration ordering has stable market/slug tie-breakers. The third browser column is Configuration, not an unsupported Package step. The planned grouped multi-year matrix/powertrain-chip overview remains absent.
- **Final layout refinement:** The duplicate Explore This Generation panel, including its upper controls, summary and actions, was removed. The existing three-step configurator was moved rather than recreated/duplicated, immediately below the Generation overview and before Key Dimensions. Its heading is Configurations & Specs with the approved introduction. The placement is **provisional**. As Generation pages accumulate more substantive measurements, builds, and maintenance content, the Configurations & Specs section may be reconsidered for placement below Key Dimensions or farther down the Generation page. This future design consideration does not authorize another relocation or RA-EXP-02 navigation.
- **Preserved behavior:** Compact labels/choices, selected state, unnamed trims, exact canonical Specs links, reset and error notices remain in `#configurations`. The script fetches the same Generation GET route and updates only that section, retaining viewport/focus/history, stale-response protection and ordinary-link fallback. No upper form, change handlers or summary remains. Removed the Service Guides subtitle/wrapper only; its empty state and functionality remain. Browser rendering of the final placement/alignment is unverified locally.
- **No-JavaScript filtering:** Native year, trim, exact-choice and reset links use the existing Generation GET route with `#configurations`. No new endpoint, framework, domain or RA-EXP-02 navigation is introduced.
- **Generation Notes cleanup:** The standalone notes panel is intentionally removed; `Generation.notes`, stored values and backend access remain unchanged. Useful platform information such as N180 may be considered within the Overview's Platform & Design content in a future task; no such content or route is implemented here.
- **Update-announcement cleanup:** A visually hidden, polite/atomic live region inside the configurator replaces the visible bottom-page status. The script replaces only the sibling content wrapper, keeping the live region mounted for repeated announcements and retaining focus management. No visible success message persists after updates; actual assistive-technology behavior remains unverified locally.
- **Task 2 diagram integrity:** Generation diagrams retain only generic outlines/location guides with explicit illustrative/not-to-scale/non-generation-specific labeling; unsupported numeric labels and the cargo-opening/wheel-well conflation are removed. Actual results are shown separately. Evidence-backed generation-specific illustration architecture remains deferred; the separate homepage decorative schematic is not repaired by this task.
- **Task 2 measurement/evidence integrity:** Active results are labeled recorded reports, not automatically verified. All conditions are shown with AND semantics; a year/trim/exact configuration does not establish physical feature states. Specification pages distinguish Generation-wide results from conditional reports with applicability not established. Separate records, units and notes are preserved without averaging or definitive selection. UUIDs remain internal; final presentation uses separate rows/cards without visible result identifiers. Shared applicability/card partials keep Generation/specification/measurements presentation consistent. Receipt wording distinguishes execution/source references from independent verification and shows actual outcome and hashes. No source documents, verification events, features or evidence relationships are invented. Structured measurement provenance/verification and configuration-feature mapping require future approved architecture.
- **Task 2 final presentation:** Additional Measurements uses compact rows with names, values/units, notes and conditions. Long explanatory subtitles and visible result UUIDs are removed; concise illustrative/not-to-scale labeling remains, without unsupported diagram values. The latest run passed 319 Django tests, 91 focused Django tests and 11 JavaScript behavior tests.
- **Deferred measurement evidence:** Physical measurements may eventually have photographs, including tape-measure images showing location/value; manufacturer technical publications are a different evidence form. Preserve this distinction in future approved architecture. Current models do not implement structured source classifications, photographic support or independent verification; existing publication-derived measurements and recorded notes are not altered.
- **Unavailable destinations:** Builds, service guides, Garage, generation history, platform/design, powertrain articles, model-year changes, and production numbers have no implemented content routes. Some controls link to missing anchors. Measurements discovery links add an ignored `view=measurements` parameter, and search prompts imply unsupported configuration/topic search. Empty states do not establish implemented future domains or ongoing field collection.
- **Coverage not reverified:** Earlier reports identified measurements for Fourth Generation 4Runner only; database coverage and record-level changes were not inspected in this reconciliation.
- **Tests:** The 13 checkpoint failures were resolved in Task 1 through functional repairs and reconciliation of obsolete markup/copy expectations. The corrected lifecycle test still requires active canonical configuration links and excludes superseded records, following year selection. Task 2 final presentation passed 319/319 Django tests, 91 focused Django tests and the 11 unchanged configurator JavaScript behavior tests; system/migration/whitespace checks passed. The Task 1 results above are historical.

### 7.2 Sitewide Presentation Repair and Checkpoint Boundaries

Missing shared CSS components were restored for Vehicles, manufacturers, models, model years, specifications, measurements, About, and custom 404. The repair restores directory grouping, generation cards/thumbnails/placeholders, configuration groups, definition lists and notes, measurement summaries/applicability badges, provenance/sibling presentation, prose/breadcrumbs, empty states, recovery buttons, wrapping, and responsive table containment while retaining archival colors and typography. Django admin and the standalone 500 page were not redesigned.

The project director visually confirmed the restored styling as satisfactory. This is not comprehensive desktop/mobile responsive-browser, zoom, keyboard, or functional verification; those behaviors remain unverified beyond the recorded checks/tests. Styling confirmation does not approve the technical claims or complete RA-EXP-01.

The experimental UI/CSS WIP checkpoint was committed before Task 1; Task 1 changes remain uncommitted. Neither checkpoint approval nor the passing Task 1 suite constitutes final approval of RA-EXP-01. Git tracks `db.sqlite3`, which has a pre-existing unstaged modification; preserve the local database and exclude it from UI staging using explicit file selection. No database contents or tracking state were changed for this reconciliation. No model/schema rollback is required by the presentation changes, but switching branches is not a safe substitute for preserving unfinished work. RA-EXP-02 vehicle-contextual navigation decisions remain future work and are not implemented here.

### 7.3 Stakeholder Evaluation Criteria
Human evaluation should focus on:
1. Does in-page filtering on the Generation Hub feel more natural than navigating away to separate year pages?
2. Does the Full Specifications sheet feel sufficiently focused as a comprehensive technical reference?
3. Does the homepage successfully communicate technical authority and expedition relevance without feeling like a generic lifestyle blog?
