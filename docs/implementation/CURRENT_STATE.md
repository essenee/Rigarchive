RigArchive Project Status Document
Version: 1.0
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

5. Current Django Apps
Implemented:
- accounts
- reference

Planned:
- core
- knowledge
- evidence
- media
- compatibility
- maintenance
- projects
- assets

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

Milestone 3 — Public Reference Browser (Completed)
- Views: Homepage, Manufacturer list/detail, Vehicle model detail, Generation detail, Vehicle definition detail
- Features: Nested URLs, Breadcrumb navigation, Responsive layout, Base template, Shared CSS, Public navigation
- Example URL: /vehicles/toyota/4runner/fourth-generation/2007-sr5-40l-v6-4wd-us/

7. Architectural Decision Records (ADRs)
Implemented and Accepted:
- ADR-0001: Entity Identity Strategy (Dual Integer PK + UUID)
- ADR-0002: Immutable Automatic Slugs (Non-editable, auto-generated on creation)

8. Current Testing
Implemented:
- Model tests
- View tests
- URL tests
Current status:
- All 12 tests passing.
- Command: .venv/bin/python manage.py test

9. Current Coding Standards
Every model includes:
- UUID
- created_at
- updated_at
Public URLs use stable slugs.
UUIDs are permanent external identities.
Database relations use integer primary keys.
Reference data uses PROTECT deletion.
Views remain thin; business logic resides in services.
Services encapsulate business workflows and orchestrate domain operations.

10. Git & Gemini CLI Workflow
- Instructions defined in GEMINI.md.
- Task specs stored under docs/implementation/tasks/.
- Next approved implementation task: RA-003 — Core Foundation.

11. Current Repository Structure
RigArchive/
│
├── accounts/
├── reference/
├── config/
│
├── templates/
├── static/
│
├── docs/
│   ├── architecture/
│   │   └── ADR/
│   │       ├── ADR-0001-Entity-Identity-Strategy.md
│   │       └── ADR-0002-Immutable-Automatic-Slugs.md
│   ├── blueprint/
│   ├── handbook/
│   └── implementation/
│       ├── CURRENT_STATE.md
│       ├── ROADMAP.md
│       └── tasks/
│           ├── TASK_TEMPLATE.md
│           └── RA-003-core-foundation.md
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
- Milestone 3: Core Infrastructure (Planned — RA-003)
- Milestone 4: Knowledge Domain (Planned)
- Milestone 5: Evidence Domain (Planned)
- Milestone 6: Media Domain (Planned)
- Milestone 7: Compatibility Domain (Planned)
- Milestone 8: Maintenance Domain (Planned)
- Milestone 9: Projects Domain (Planned)

13. Current Repository Status
The repository currently contains:
- Functional Django project
- Passing test suite (12 tests passing)
- Public reference browser
- Admin interface
- Stable migration history
- Populated Architectural Decision Records (ADR-0001, ADR-0002)
- Gemini CLI project instructions (GEMINI.md)
- Task-based implementation workflow (docs/implementation/tasks/)
- AI-assisted engineering workflow established

The next approved task is RA-003 — Core Foundation.


Current Focus

RA-003 — Core Foundation

Status:
Approved

Branch:
main

Next Action:
Implement shared core infrastructure and refactor existing applications to use
shared model mixins.