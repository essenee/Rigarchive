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
4. **Vanilla Frontend:** Standard Django templates, vanilla CSS (`static/css/site.css`), and inline selector submission handlers. No SPA framework or external UI dependency. The missing submit button means filtering does not provide the intended progressive-enhancement fallback.
5. **Most Recent Recorded Verification:** Full suite executed **286 tests: 273 passed, 13 failed**. CSS restoration introduced no new failures and resolved two CSS contract failures (15 failures before repair). Recorded system check passed, migration check with `--dry-run` detected no changes, and 14 focused tests passed using isolated resources. These are previously recorded results, not tests executed during this documentation reconciliation. Historical results for earlier completed milestones are not superseded as historical records; they do not describe this WIP tree.

---

## 7. Known Limitations and Evaluation Criteria

### 7.1 Current Implementation and Limitations

- **Implemented:** Data-driven homepage platform cards, manufacturer/model-name search, session-backed Recently Viewed, Generation photo/identity and statistics, year/trim GET filtering, exact-configuration slug handling in the service, generation measurement queries, and a year → trim → matching-configuration browser. Specification pages include canonical identity, engine/drivetrain, configuration notes, generation-wide measurement summaries, receipt information, and same-year sibling links.
- **Partially implemented identity/filtering:** The intended exact-configuration banner is absent. Status text omits engine, drivetrain, and market. The Trim / Configuration dropdown selects trims only. Configuration-only URLs infer a year after available trims are calculated, and blank trim names cannot be selected in the lower browser. The Package column has no package selection/schema. “View Full Specifications” may instead lead to a model-year overview or the browser. The intended grouped multi-year matrix and powertrain-chip overview are absent.
- **No-JavaScript filtering unavailable:** Both selectors submit through inline `onchange` handlers and there is no submit button. The standard GET method does not by itself supply an operable fallback.
- **Known regression:** Generation notes are not rendered, although they remain expected by tests and were previously displayed.
- **Unsupported dimensions:** Generic diagrams repeat literal dimensions across different generations/models without evidence bindings. Cargo-opening width and width between wheel wells are conflated. The diagrams must not be treated as verified geometry or recorded measurements.
- **Verification and applicability limitations:** Active results are labeled verified without a verification criterion. Hub rows hide actual feature conditions behind a Conditional badge; the dedicated measurements page displays the conditions. Receipt presence alone does not establish the “Audited & Verified” claim. Specification pages show generation-wide results only, rather than infer feature states from trim. Multiple recorded results remain permitted under ADR-0009.
- **Unavailable destinations:** Builds, service guides, Garage, generation history, platform/design, powertrain articles, model-year changes, and production numbers have no implemented content routes. Some controls link to missing anchors. Measurements discovery links add an ignored `view=measurements` parameter, and search prompts imply unsupported configuration/topic search. Empty states do not establish implemented future domains or ongoing field collection.
- **Coverage not reverified:** Earlier reports identified measurements for Fourth Generation 4Runner only; database coverage and record-level changes were not inspected in this reconciliation.
- **Remaining tests:** The 13 recorded failures include outdated markup/copy assertions, missing generation notes, and unfinished exact-selection context and other experimental presentation. No tests were changed to hide failures.

### 7.2 Sitewide Presentation Repair and Checkpoint Boundaries

Missing shared CSS components were restored for Vehicles, manufacturers, models, model years, specifications, measurements, About, and custom 404. The repair restores directory grouping, generation cards/thumbnails/placeholders, configuration groups, definition lists and notes, measurement summaries/applicability badges, provenance/sibling presentation, prose/breadcrumbs, empty states, recovery buttons, wrapping, and responsive table containment while retaining archival colors and typography. Django admin and the standalone 500 page were not redesigned.

The project director visually confirmed the restored styling as satisfactory. This is not comprehensive desktop/mobile responsive-browser, zoom, keyboard, or functional verification; those behaviors remain unverified beyond the recorded checks/tests. Styling confirmation does not approve the technical claims or complete RA-EXP-01.

The current working tree is an uncommitted WIP checkpoint, not an approved implementation milestone. Git tracks `db.sqlite3`, which has a pre-existing unstaged modification; preserve the local database and exclude it from UI staging using explicit file selection. No database contents or tracking state were changed for this reconciliation. No model/schema rollback is required by the presentation changes, but switching branches is not a safe substitute for preserving unfinished work. RA-EXP-02 vehicle-contextual navigation decisions remain future work and are not implemented here.

### 7.3 Stakeholder Evaluation Criteria
Human evaluation should focus on:
1. Does in-page filtering on the Generation Hub feel more natural than navigating away to separate year pages?
2. Does the Full Specifications sheet feel sufficiently focused as a comprehensive technical reference?
3. Does the homepage successfully communicate technical authority and expedition relevance without feeling like a generic lifestyle blog?
