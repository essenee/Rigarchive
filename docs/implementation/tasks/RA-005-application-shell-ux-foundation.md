# RA-005 — Application Shell & UX Foundation

## Objective

Establish a cohesive, responsive, and accessible presentation shell for RigArchive, including primary navigation, a skip link, main layout structure, an About page, custom 404/500 error templates, a reusable breadcrumb include, and CSS refinements.

## User Stories

- As a user, I can navigate between the Homepage, Vehicle Reference domain, and About page using standard primary navigation.
- As a screen-reader or keyboard user, I can use a skip-to-content link to bypass navigation directly to the primary main content element.
- As a user encountering an invalid URL or server error, I see a clear, styled custom error page instead of a default browser message or unstyled trace.
- As a domain contributor, I can review the project mission, factory configuration scope, and evidence-aware data philosophy on the About page.

## Architectural Context

- Belongs to the Presentation tier using Django templates, HTML5 semantic elements, and Vanilla CSS.
- Project-level presentation views (`about`, `custom_404`, `custom_500`) are placed in `config/views.py`.
- `core` remains strictly reserved for reusable, domain-agnostic infrastructure models and utilities.
- Views remain thin and contain no business logic.
- UI layout is extensible without rendering placeholders for unbuilt domain models.

## Scope

- Create `config/views.py` containing project-level presentation views (`about`, `custom_404`, `custom_500`).
- Update `config/urls.py` with routes for `/about/`, `handler404`, and `handler500`.
- Update `templates/base.html` with semantic `<header>`, `<nav aria-label="Primary navigation">`, `<main id="main-content">`, and `<footer>`.
- Add accessibility skip link (`<a class="skip-link" href="#main-content">Skip to main content</a>`).
- Create `templates/about.html` explaining canonical vehicle identity, factory configuration, and evidence-aware technical knowledge.
- Create `templates/includes/breadcrumbs.html` for modular, accessible breadcrumb rendering.
- Create resilient custom error templates `templates/404.html` and `templates/500.html`.
- Update `templates/home.html` to reflect approved project language and mission.
- Refine `static/css/site.css` for clean typography, focus states, responsive layouts, breadcrumb styling, and mobile responsiveness.
- Write unit tests in `config/tests.py` verifying response codes, semantic elements, skip links, main targets, page titles, and custom error handling.

## Out of Scope

- Creating new domain models or database migrations.
- Introducing JavaScript or CSS frameworks (Tailwind, Bootstrap, React, etc.).
- Adding numeric version numbers or version context processors.
- Rendering UI sections or navigation links for unbuilt feature domains (Knowledge, Evidence, Measurements, Maintenance, Modifications, Compatibility, Projects).
- Modifying existing core model behavior or reference URLs.

## Presentation Architecture

- `templates/base.html` acts as the single master application shell containing header, primary navigation, main container target, and footer.
- `templates/includes/breadcrumbs.html` provides a reusable template partial for breadcrumbs.
- Header and footer remain embedded directly inside `base.html`.
- Page templates inherit from `base.html` and override `title`, `breadcrumbs`, and `content` blocks.

## UX Requirements

- Clear primary navigation linking Home, Vehicles, and About.
- Document title structure formatted as `<Page Title> | RigArchive` or `RigArchive`.
- High contrast, legible typography, visual hierarchy, and single `<h1>` per page.
- Clean visual feedback for interactive elements.

## Accessibility Requirements

- Accessible `<nav aria-label="Primary navigation">` container.
- Visually hidden skip link (`.skip-link`) that becomes prominent when focused via keyboard navigation.
- Single, uniquely identified `<main id="main-content">` per page.
- Clear, un-clipped focus rings (`:focus-visible`) for keyboard navigation.

## Responsive Requirements

- Mobile-first responsive layout utilizing flexbox/grid.
- Tested and verified down to 320px viewport width without horizontal scrollbars.

## Expected Files

- `config/views.py`
- `config/urls.py`
- `templates/base.html`
- `templates/home.html`
- `templates/about.html`
- `templates/404.html`
- `templates/500.html`
- `templates/includes/breadcrumbs.html`
- `static/css/site.css`
- `config/tests.py`
- `docs/implementation/CURRENT_STATE.md`
- `CHANGELOG.md`
- `docs/implementation/tasks/RA-005-application-shell-ux-foundation.md`

## Acceptance Criteria

1. Navigating to `/about/` returns HTTP 200 and renders the About page.
2. Navigating to non-existent URLs returns HTTP 404 using `templates/404.html`.
3. Server errors trigger HTTP 500 response using `templates/500.html`.
4. Skip link is present and points to `#main-content`.
5. Document `<title>` tags follow standard naming structure across all pages.
6. Breadcrumbs render consistently via `templates/includes/breadcrumbs.html`.
7. Footer displays non-numeric text: `RigArchive Reference Implementation`.
8. All existing Reference domain URLs and tests continue to function without regression.
9. All verification commands pass cleanly.

## Test Requirements

- Tests verify HTTP 200 status for Home (`/`), Vehicles (`/vehicles/`), and About (`/about/`).
- Tests verify document `<title>` elements and `<h1>` headings.
- Tests verify presence of skip link (`href="#main-content"`) and `<main id="main-content">`.
- Tests verify custom 404 and 500 handler execution and template rendering.
- Tests do not assert exact marketing copy, specific CSS pixel dimensions, or decorative counts.

## Verification Commands

```bash
.venv/bin/python manage.py check
.venv/bin/python manage.py makemigrations --check
.venv/bin/python manage.py test
```

## Documentation Requirements

- Update `docs/implementation/CURRENT_STATE.md`.
- Update `CHANGELOG.md` under `Unreleased`.
- Update completion record in this task file.

## Restrictions

- No new domain models.
- No migrations.
- No application services unless an unforeseen workflow requires one and work stops for review.
- No JavaScript or CSS frameworks.
- No invented version numbers.
- No public placeholders for unimplemented domains.
- No business logic in templates or views.
- No commits or pushes without explicit approval.

## ADR Assessment

No ADR is required for RA-005. Standard template composition, CSS organization, an About page, custom error templates, and project-level presentation views are routine Django implementation details.

## Completion Record

Status: Completed

Completion date: 2026-08-04

Files changed:
- `config/views.py` (Created project-level presentation views: `about`, `custom_404`, `custom_500`)
- `config/urls.py` (Added `/about/` route, `handler404`, and `handler500`)
- `templates/base.html` (Added skip link, primary navigation links, main content ID target, and updated footer string)
- `templates/home.html` (Updated layout and copy using approved project language and links)
- `templates/about.html` (Created About page explaining identity, factory configuration, and evidence-aware data philosophy)
- `templates/404.html` (Created custom 404 error template)
- `templates/500.html` (Created resilient custom 500 error template)
- `templates/includes/breadcrumbs.html` (Created reusable breadcrumb partial template)
- `static/css/site.css` (Added skip link styles, focus rings, breadcrumbs, hero/buttons, and 320px responsive media queries)
- `config/tests.py` (Created unit test suite for application shell, navigation, accessibility, and error handling)
- `docs/implementation/CURRENT_STATE.md` (Updated status, apps, file tree, test count)
- `CHANGELOG.md` (Recorded RA-005 changes under Unreleased)
- `docs/implementation/tasks/RA-005-application-shell-ux-foundation.md` (Updated completion record)

Migrations created:
- None required

Verification results:
- `.venv/bin/python manage.py check`: Passed (`System check identified no issues (0 silenced)`).
- `.venv/bin/python manage.py makemigrations --check`: Passed (`No changes detected`).
- `.venv/bin/python manage.py test`: Passed (`Ran 23 tests in 0.052s — OK`).

Documentation updated:
- `docs/implementation/CURRENT_STATE.md`
- `CHANGELOG.md`
- `docs/implementation/tasks/RA-005-application-shell-ux-foundation.md`

ADR status:
- None required for routine presentation shell and template implementation.
