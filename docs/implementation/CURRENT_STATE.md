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

Milestone 5 — Development Data Preservation & Recovery Implementation

Implementation Task:
RA-009 — Development Data Preservation and Recovery Implementation (Completed)
- Management commands in `core/management/commands/`: `snapshot_db` (Layer 1 SQLite `VACUUM INTO` physical recovery snapshot with integrity verification), `export_dev_data` (Layer 2 natural-key JSON logical export), `verify_dev_data` (isolated OS temporary database restoration verification)
- Isolation: `RIGARCHIVE_TEST_DB_PATH` environment variable support in `config/settings.py` for isolated temporary database test execution
- Ignored storage: Local `backups/` directory (`backups/snapshots/` and `backups/logical/`) with `backups/.gitignore`
- Git hygiene: Safely untracked `db.sqlite3` and all 26 compiled `.pyc` / `__pycache__` files from Git tracking while preserving local development files (zero `.pyc` or `__pycache__` files remain tracked in Git)
- Preserved Database State: 2 Users, 1 Manufacturer, 1 VehicleModel, 1 Generation, 1 VehicleDefinition, 3 Observations
- Documentation: `docs/development/DATA_PRESERVATION.md` developer guide
- Design document: `docs/architecture/designs/RA-008-Development-Data-Preservation-Architecture.md`

Milestone 6 — Reference Data Ingestion Source & Mapping Architecture

Architecture/Research Task:
RA-010 — Reference Data Ingestion Source & Mapping Architecture (Approved Architecture)
- Design document: `docs/architecture/designs/RA-010-Reference-Ingestion-Source-Mapping-Architecture.md`
- Ingestion Pipeline Architecture: Decouples Source Acquisition -> Preserved Source Assertions -> Token-Based Normalization -> Candidate Configurations -> Reconciliation / Validation -> Human Review -> Approved Canonical Import -> Reference Domain
- Manufacturer Taxonomy Rule: Manufacturer's own market-specific configuration taxonomy governs trim/grade identity. Sub-grades (`SR5 Premium`, `Trail Premium`) are preserved as distinct trims. Packages/options not recognized by the manufacturer as distinct trims/grades do not independently create `VehicleDefinition` records
- Non-Lossy Normalization: Preserves rich technical specificity across 7 conceptual drivetrain dimensions (Classification, Architecture, Components, Operating Modes, Mode-Specific States, Capabilities, Manufacturer Terminology) regardless of primary model choice field bounds
- Source Authority & Reconciliation: Attribute-specific source precedence hypotheses (Manufacturer, EPA, NHTSA, J.D. Power) with categorical reconciliation status states (`corroborated`, `single_source`, `conflicting`, `ambiguous`, `incomplete`, `requires_review`)
- Idempotency & Protection: Future canonical import must be deterministic, duplicate-safe, and idempotent without creating duplicate records or overwriting manually validated Reference data (exact matching key/mechanism unresolved)
- Code / Schema Status: Architecture and research only. No Django models, migrations, acquisition tools, scrapers, DB records, or ingestion artifacts created

Milestone 7 — Ingestion Schema & Intermediate Serialization Design

Architecture/Research Task:
RA-011 — Ingestion Schema & Intermediate Serialization Design (Approved Architecture)
- Design document: `docs/architecture/designs/RA-011-Ingestion-Schema-Intermediate-Serialization-Design.md`
- Serialization Format & Versioning: JSON logical contracts with mandatory self-describing envelope (`artifact_type`, `schema_version` SemVer) supporting controlled schema evolution
- Two-Tier Serialization Architecture: Tier 1 `SourceAssertionSet` (<ingestion-runtime-root>/<source-artifacts>/) and Tier 2 `CandidateConfigurationDocument` (<ingestion-runtime-root>/<candidate-artifacts>/)
- Embedded Interpretation Layer: Traceable transformation from raw source assertion → normalized interpretation → candidate attribute
- Decoupled Candidate Context: Real-world vehicle context (`candidate_identity`) and source-specific configuration IDs preserved without mirroring database columns or fixing a canonical import matching key
- High-Fidelity Technical Representation: 7-dimension drivetrain contract, standard units + raw source strings, and preserved `factory_technical_features` (A-TRAC, CRAWL Control, KDSS, X-REAS) carrying both source presentation and unresolved classification status
- Separated Reconciliation & Review: Primary attribute evidence states (`corroborated`, `single_source`, `conflicting`, `ambiguous`, `incomplete`) logically separated from workflow review dispositions (`not_required`, `pending_review`, `resolved`, `rejected_excluded`)
- Deterministic Conventions: Alphabetical key sorting, ISO-8601 UTC timestamps, 2-space indentation, UTF-8 encoding for diffability
- Code / Schema Status: Architecture and research only. No Django models, migrations, serializers, acquisition tools, scrapers, DB records, or ingestion artifacts created

Milestone 8 — Intermediate Serialization Contract Implementation & Fixture Validation

Implementation Task:
RA-012 — Intermediate Serialization Contract Implementation & Fixture Validation (Completed)
- Package Location: `reference/ingestion/` (`__init__.py`, `contracts.py`, `serialization.py`, `validation.py`)
- Executable Contracts: Pure Python dataclasses representing Tier 1 `SourceAssertionSet` and Tier 2 `CandidateConfigurationDocument` with embedded `normalized_assertions`, 7-dimension drivetrain, preserved `factory_technical_features`, and separated reconciliation/review states
- Deterministic Serialization: `serialize_artifact` and `deserialize_artifact` enforcing alphabetical key sorting, 2-space indentation, UTF-8 encoding, ISO-8601 UTC timestamps, and lossless round-trips
- Unknown Field Preservation: Forward-compatible parser preserving unmodeled JSON fields in `unknown_fields` container without data loss upon re-serialization
- Contract Validation: `validate_artifact`, `validate_envelope`, `validate_source_assertion_set`, `validate_candidate_configuration`, and `validate_semantic_missing_value` with actionable error reporting
- Documentation & Task Record: `docs/implementation/tasks/RA-012-intermediate-serialization-implementation.md`

Milestone 9 — Public Source Acquisition Adapters (NHTSA & EPA)

Implementation Task:
RA-013 — Public Source Acquisition Adapters (Completed)
- Package Location: `reference/ingestion/acquisition/` (`__init__.py`, `base.py`, `nhtsa.py`, `epa.py`, `smoke_test.py`)
- Adapters Implemented: `NHTSAAdapter` (NHTSA vPIC REST API `GetModelsForMakeYear`) and `EPAAdapter` (EPA FuelEconomy.gov REST API `vehicle/{id}`)
- Transport Isolation & Security: `default_http_transport` using standard library `urllib.request` with strict TLS certificate verification (`ssl.create_default_context()`), finite timeouts, and explicit User-Agent headers (`RigArchive-Ingestion/0.1.0`); unit tests use mock transport loading test fixtures with zero network calls
- Tier 1 Payload Construction: Converts acquired raw source payloads into valid RA-012 `SourceAssertionSet` objects preserving provenance (`source_id`, `source_type`, `source_locator`, `retrieved_at`, `native_record_id`, `target_context`) and raw factual assertions without candidate normalization. FuelEconomy.gov `city08` and `highway08` map to Tier 1 keys `city_mpg_epa_rating` and `highway_mpg_epa_rating`.
- Response Fixtures: 2 acquisition response fixtures in `reference/tests/fixtures/acquisition/` (`nhtsa/get_models_toyota_2020.json`, `epa/vehicle_42101.json`)
- Live Smoke Test Utility: `smoke_test.py` (`run_all_live_smoke_tests`) for on-demand live API connectivity verification
- Zero ORM / Migration Impact: Pure Python data structures; 0 Django ORM staging models, 0 migrations, 0 database writes, 0 production storage path decisions
- Documentation & Task Record: `docs/implementation/tasks/RA-013-public-source-acquisition-implementation.md`

Milestone 10 — Source Assertion Normalization & Mapping Architecture

Architecture Task:
RA-014 — Source Assertion Normalization & Mapping Architecture (Approved Architecture)
- Design Document Location: `docs/architecture/designs/RA-014-Source-Assertion-Normalization-Mapping-Architecture.md`
- Source-Specific Normalization Ownership: Logic partitioned by source behind shared normalization contract (`NHTSANormalizer`, `EPANormalizer` in `reference/ingestion/normalization/`)
- Evidence-Bounded Normalization Rule: Normalization may only add semantic specificity supported by source assertions + explicit mapping rules; manufacturing unsupported drivetrain modes, ratios, lock states, or capabilities is prohibited
- Transformation Taxonomy: 6 explicit categories (`direct_copy`, `exact_mapping`, `parsed`, `converted`, `interpreted`, `unmapped`)
- Concept Key Strategy: Stable lower_snake_case keys decoupled from Django ORM field names; current concept set treated as provisional
- Semantic Qualifier Preservation: Technical qualifiers (`epa_rating`, `unadjusted`, `measured`, `estimated`) must not be stripped during normalization
- Redesigned Unmapped Behavior: Explicit separation of Case A (known concept, unmapped value) from Case B (unknown concept) without pseudonormalizing raw values
- Drivetrain & Feature Boundaries: 7-dimension drivetrain boundary enforced; unclassified features (KDSS, A-TRAC) remain under `factory_technical_features` as unresolved
- Category C Mappings Authorized for RA-015: 12 empirically validated mappings (`nhtsa_make_id`, `make`, `nhtsa_model_id`, `model`, `model_year`, `generic_drive_classification`, `drivetrain_architecture`, `engine_displacement_liters`, `engine_cylinders`, `city_mpg_epa_rating`, `highway_mpg_epa_rating`)
- Next Proposed Milestone: RA-015 — Source Assertion Normalization Implementation & Fixture Validation

7. Architectural Decision Records (ADRs)
Implemented and Accepted:
- ADR-0001: Entity Identity Strategy (Dual Integer PK + UUID)
- ADR-0002: Immutable Automatic Slugs (Non-editable, auto-generated on creation)
- ADR-0003: Core Infrastructure Application (Shared abstract base models in `core`, domain isolation)

8. Current Testing
Implemented:
- Development Data Preservation tests (`core/tests.py`)
- Observation Domain tests (`observation/tests.py`)
- Application Shell & UX tests (`config/tests.py`)
- Core mixin & inheritance tests (`core/tests.py`)
- Reference Model tests (`reference/tests/test_models.py`)
- Public Reference View & URL tests (`reference/tests/test_views.py`)
Current status:
- All 34 tests passing.
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
- Completed tasks: RA-003 — Core Foundation, RA-005 — Application Shell & UX Foundation, RA-007 — Observation Domain Foundation, RA-009 — Development Data Preservation and Recovery Implementation.

11. Current Repository Structure
RigArchive/
│
├── accounts/
├── backups/
│   ├── .gitignore
│   ├── logical/
│   └── snapshots/
├── core/
│   ├── apps.py
│   ├── management/
│   │   ├── __init__.py
│   │   └── commands/
│   │       ├── __init__.py
│   │       ├── export_dev_data.py
│   │       ├── snapshot_db.py
│   │       └── verify_dev_data.py
│   ├── models.py
│   └── tests.py
├── reference/
│   ├── admin.py
│   ├── apps.py
│   ├── ingestion/
│   │   ├── __init__.py
│   │   ├── acquisition/
│   │   │   ├── __init__.py
│   │   │   ├── base.py
│   │   │   ├── epa.py
│   │   │   ├── nhtsa.py
│   │   │   └── smoke_test.py
│   │   ├── contracts.py
│   │   ├── serialization.py
│   │   └── validation.py
│   ├── models.py
│   ├── tests/
│   │   ├── __init__.py
│   │   ├── fixtures/
│   │   │   ├── acquisition/
│   │   │   │   ├── epa/
│   │   │   │   │   └── vehicle_42101.json
│   │   │   │   └── nhtsa/
│   │   │   │       └── get_models_toyota_2020.json
│   │   │   └── ingestion/
│   │   │       ├── candidate_configuration_4runner_2010_i4_2wd.json
│   │   │       ├── candidate_configuration_4runner_2020_trd_offroad.json
│   │   │       ├── candidate_configuration_4runner_2020_trim_conflict.json
│   │   │       └── source_assertion_set_4runner_2020.json
│   │   ├── test_acquisition_adapters.py
│   │   ├── test_ingestion_serialization.py
│   │   ├── test_models.py
│   │   └── test_views.py
│   ├── urls.py
│   └── views.py
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
│   │       ├── RA-006-Observation-Foundation-Architecture.md
│   │       ├── RA-008-Development-Data-Preservation-Architecture.md
│   │       ├── RA-010-Reference-Ingestion-Source-Mapping-Architecture.md
│   │       ├── RA-011-Ingestion-Schema-Intermediate-Serialization-Design.md
│   │       └── RA-014-Source-Assertion-Normalization-Mapping-Architecture.md
│   ├── blueprint/
│   ├── development/
│   │   └── DATA_PRESERVATION.md
│   ├── handbook/
│   └── implementation/
│       ├── CURRENT_STATE.md
│       ├── ROADMAP.md
│       └── tasks/
│           ├── TASK_TEMPLATE.md
│           ├── RA-003-core-foundation.md
│           ├── RA-005-application-shell-ux-foundation.md
│           ├── RA-007-observation-domain-foundation.md
│           ├── RA-009-development-data-preservation-implementation.md
│           ├── RA-012-intermediate-serialization-implementation.md
│           └── RA-013-public-source-acquisition-implementation.md
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
- Milestone 5: Development Data Preservation & Recovery (✅ Complete — RA-009)
- Milestone 6: Reference Data Ingestion Source & Mapping Architecture (✅ Approved Architecture — RA-010)
- Milestone 7: Ingestion Schema & Intermediate Serialization Design (✅ Approved Architecture — RA-011)
- Milestone 8: Intermediate Serialization Contract Implementation & Fixture Validation (✅ Complete — RA-012)
- Milestone 9: Public Source Acquisition Adapters (✅ Complete — RA-013)
- Milestone 10: Source Assertion Normalization & Mapping Architecture (✅ Approved Architecture — RA-014)

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
- Passing test suite (58 tests passing)
- Shared core infrastructure (`core` app with `UUIDModel`, `TimestampedModel`, `BaseModel`)
- Reference Data Ingestion package (`reference/ingestion/` with contracts, serialization, validation, and `acquisition/` NHTSA & EPA adapters)
- Development data preservation tooling (`snapshot_db`, `export_dev_data`, `verify_dev_data`)
- Accessible application shell and UX foundation (`templates/base.html`, `about.html`, `404.html`, `500.html`)
- Observation Domain foundation (`observation` app with `Observation` model)
- Public reference browser
- Admin interface
- Stable migration history
- Populated Architectural Decision Records (ADR-0001, ADR-0002, ADR-0003)
- Approved Architecture Design Documents (RA-006, RA-008, RA-010, RA-011, RA-014)
- Gemini CLI project instructions (GEMINI.md)
- Task-based implementation workflow (docs/implementation/tasks/)
- Completed implementation tasks: RA-003 — Core Foundation, RA-005 — Application Shell & UX Foundation, RA-007 — Observation Domain Foundation, RA-009 — Development Data Preservation and Recovery Implementation, RA-012 — Intermediate Serialization Contract Implementation & Fixture Validation, RA-013 — Public Source Acquisition Adapters
- Approved Architecture/Research tasks: RA-010 — Reference Data Ingestion Source & Mapping Architecture, RA-011 — Ingestion Schema & Intermediate Serialization Design, RA-014 — Source Assertion Normalization & Mapping Architecture