RigArchive Project Status Document
Version: 1.1
Last Updated: 2026-08-04
Purpose: Current implementation status and development roadmap

1. Project Overview
RigArchive is a long-term engineering project whose purpose is to build the world's most trusted technical archive of vehicles and their modifications, maintenance, compatibility, measurements, and supporting evidence.
The Project Blueprint defines the architectural vision.
The Engineering Handbook defines implementation standards.
The GitHub repository is the authoritative implementation.
This document summarizes the current implementation status.

2. Project Authority

Repository authority, highest to lowest:

   1. Current implementation task
   2. Architectural Decision Records (ADRs)
   3. CURRENT_STATE.md
   4. Engineering Handbook
   5. Project Blueprint

Conflicts between these documents should never be resolved by assumption.

3. Current Technology Stack
Backend
Python 3.14
Django 6.0.x

Database
Development: SQLite
Future Production: PostgreSQL

Storage
Development: Local filesystem
Future: Cloud object storage (AWS S3 or Cloudflare R2)

Frontend
Django Templates
Vanilla HTML
Vanilla CSS
Minimal JavaScript
No React or SPA framework is planned.

4. Architectural Principles
RigArchive follows the Engineering Handbook architecture:

Presentation
↓
Application Services
↓
Domain Models
↓
Infrastructure

Views remain thin.
Business workflows belong in services.
Models enforce domain invariants.
Infrastructure remains replaceable.

Reference Domain
The Reference Domain is the canonical factory configuration model for supported vehicles.
It models stable engineering identities and factory configuration logic.
It is intentionally distinct from observations, evidence, maintenance history, compatibility knowledge, and other derived information.

5. Current Django Apps
Implemented:
- core (Shared abstract infrastructure mixins: UUIDModel, TimestampedModel, BaseModel)
- accounts (Custom user identity)
- reference (Canonical vehicle reference domain)
- observation (Observation Domain foundation: recorded statements and capture context)

Future application boundaries remain intentionally undecided.

Candidate future domains include:

- Evidence
- Knowledge
- Media / Assets
- Compatibility
- Maintenance
- Projects

The final application structure will be determined through incremental implementation rather than fixed in advance.

6. Completed Milestones
Milestone 1 — Project foundation (Completed)
- Django project
- Git & GitHub repository
- Development environment
- SQLite configuration
- Custom User model
- Initial migrations
- Test infrastructure

Milestone 2 — Reference Domain (Completed)
- Models: Manufacturer, VehicleModel, Generation, VehicleDefinition
- Features: UUID identity, Integer DB PKs, Automatic immutable slug generation, Protected foreign keys, Validation rules, Django Admin, Unit tests

Milestone 2A — Public Reference Browser (Completed)
- Views: Homepage, Manufacturer list/detail, Vehicle model detail, Generation detail, Vehicle definition detail
- Features: Nested URLs, Breadcrumb navigation, Responsive layout, Base template, Shared CSS, Public navigation
- Example URL: /vehicles/toyota/4runner/fourth-generation/2007-sr5-40l-v6-4wd-us/

Milestone 3 — Core Infrastructure (Completed — RA-003)
- App: core (`core.apps.CoreConfig`)
- Shared abstract model mixins: `UUIDModel`, `TimestampedModel`, `BaseModel`
- Refactored `reference` domain models to inherit from shared `core` mixins
- Added unit tests for abstract core mixins and inherited behavior

Milestone 3A — Application Shell & UX Foundation

Implementation Task:
RA-005 — Application Shell & UX Foundation (Completed)
- Views: Project-level presentation views (`about`, `custom_404`, `custom_500`) in `config/views.py`
- Shell: Accessible header, skip link (`<a class="skip-link" href="#main-content">`), main target (`<main id="main-content" tabindex="-1">`), non-numeric footer description
- Navigation: Primary nav linking Home, Vehicles, About, and Admin
- Error handling: Resilient custom 404 (`templates/404.html`) and custom 500 (`templates/500.html`) pages
- CSS: Accessible focus rings, breadcrumb list styles, hero/button styling, responsive 320px support in `static/css/site.css`

Milestone 4 — Observation Domain Foundation

Implementation Task:
RA-007 — Observation Domain Foundation (Completed)
- App: observation (`observation.apps.ObservationConfig`)
- Models: `Observation` (inheriting from `core.models.BaseModel`, referencing `reference.VehicleDefinition` and `accounts.User` via `PROTECT`)
- Admin: `ObservationAdmin` registration in `observation/admin.py`
- Tests: Unit test suite in `observation/tests.py` verifying model validation, dual identity, `PROTECT` deletion, non-mutation of reference data, and admin integration

7. Architectural Decision Records (ADRs)
Implemented and Accepted:
- ADR-0001: Entity Identity Strategy (Dual Integer PK + UUID)
- ADR-0002: Immutable Automatic Slugs (Non-editable, auto-generated on creation)
- ADR-0003: Core Infrastructure Application (Shared abstract base models in `core`, domain isolation)

8. Current Testing
Implemented:
- Observation Domain tests (`observation/tests.py`)
- Application Shell & UX tests (`config/tests.py`)
- Core mixin & inheritance tests (`core/tests.py`)
- Reference Model tests (`reference/tests/test_models.py`)
- Public Reference View & URL tests (`reference/tests/test_views.py`)
Current status:
- All 32 tests passing.
- Verification command: `.venv/bin/python manage.py test`

9. Current Coding Standards
The four Reference Domain models and the Observation Domain model inherit shared UUID and timestamp infrastructure through `core.models.BaseModel`.
Domain entities requiring both UUID identity and timestamps should normally inherit from `BaseModel`. Specialized models may inherit directly from the focused mixins (`UUIDModel`, `TimestampedModel`) where appropriate.
Public URLs use stable slugs.
UUIDs are permanent external identities.
Database relations use integer primary keys.
Reference and Observation data relationships use PROTECT deletion.
Views remain thin; business logic resides in services when coordination complexity mandates it.
Project-level presentation views reside in `config/views.py`; domain views belong in domain applications.

10. Git & Gemini CLI Workflow
- Instructions defined in GEMINI.md.
- Task specs stored under docs/implementation/tasks/.
- Completed tasks: RA-003 — Core Foundation, RA-005 — Application Shell & UX Foundation, RA-007 — Observation Domain Foundation.

11. Current Repository Structure
RigArchive/
│
├── accounts/
├── core/
│   ├── apps.py
│   ├── models.py
│   └── tests.py
├── reference/
├── observation/
│   ├── admin.py
│   ├── apps.py
│   ├── models.py
│   ├── tests.py
│   └── migrations/
│       └── 0001_initial.py
├── config/
│   ├── settings.py
│   ├── urls.py
│   ├── views.py
│   ├── tests.py
│   └── wsgi.py
│
├── templates/
│   ├── base.html
│   ├── home.html
│   ├── about.html
│   ├── 404.html
│   ├── 500.html
│   ├── includes/
│   │   └── breadcrumbs.html
│   └── reference/
├── static/
│   └── css/
│       └── site.css
│
├── docs/
│   ├── architecture/
│   │   ├── ADR/
│   │   │   ├── ADR-0001-Entity-Identity-Strategy.md
│   │   │   ├── ADR-0002-Immutable-Automatic-Slugs.md
│   │   │   └── ADR-0003-Core-Infrastructure.md
│   │   └── designs/
│   │       └── RA-006-Observation-Foundation-Architecture.md
│   ├── blueprint/
│   ├── handbook/
│   └── implementation/
│       ├── CURRENT_STATE.md
│       ├── ROADMAP.md
│       └── tasks/
│           ├── TASK_TEMPLATE.md
│           ├── RA-003-core-foundation.md
│           ├── RA-005-application-shell-ux-foundation.md
│           └── RA-007-observation-domain-foundation.md
│
├── tests/
│
├── CHANGELOG.md
├── GEMINI.md
├── README.md
├── requirements.txt
└── manage.py

12. Planned Milestone Map
- Milestone 1: Project foundation (✅ Complete)
- Milestone 2: Reference Domain (✅ Complete)
- Milestone 2A: Public Reference Browser (✅ Complete)
- Milestone 3: Core Infrastructure (✅ Complete — RA-003)
- Milestone 3A: Application Shell & UX Foundation (✅ Complete)
- Milestone 4: Observation Domain Foundation (✅ Complete — RA-007)

Candidate future domains include:
- Evidence
- Knowledge
- Media / Assets
- Compatibility
- Maintenance
- Projects

13. Current Repository Status
The repository currently contains:
- Functional Django project
- Passing test suite (32 tests passing)
- Shared core infrastructure (`core` app with `UUIDModel`, `TimestampedModel`, `BaseModel`)
- Accessible application shell and UX foundation (`templates/base.html`, `about.html`, `404.html`, `500.html`)
- Observation Domain foundation (`observation` app with `Observation` model)
- Public reference browser
- Admin interface
- Stable migration history
- Populated Architectural Decision Records (ADR-0001, ADR-0002, ADR-0003)
- Approved Architecture Design Documents (RA-006)
- Gemini CLI project instructions (GEMINI.md)
- Task-based implementation workflow (docs/implementation/tasks/)
- Completed implementation tasks: RA-003 — Core Foundation, RA-005 — Application Shell & UX Foundation, RA-007 — Observation Domain Foundation