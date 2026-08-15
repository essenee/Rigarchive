# Changelog

All notable changes to RigArchive will be documented in this file.

## Unreleased

### Added

- Source Assertion Normalization package `reference/ingestion/normalization/` (`base.py`, `nhtsa.py`, `epa.py`, `rules/`) implementing source-specific normalizers (`NHTSANormalizer`, `EPANormalizer`) extending `BaseSourceNormalizer` and dispatched via `normalize_source_assertions(assertion_set)`, strictly enforcing the 12 Category C mappings authorized by RA-014, Evidence-Bounded Normalization rules, semantic qualifier preservation (`city_mpg_epa_rating`), unmapped handling (Case A vs Case B), parsing failure handling, and 9 automated unit tests in `reference/tests/test_normalization.py` (67 total tests passing).
- Architecture Design Document `RA-014-Source-Assertion-Normalization-Mapping-Architecture.md` defining source-specific normalization ownership (`NHTSANormalizer`, `EPANormalizer`), evidence-bounded normalization rules, 6 explicit transformation categories, initial provisional concept key strategy, semantic qualifier preservation (`city_mpg_epa_rating`), redesigned unmapped value handling, 7-dimension drivetrain boundary, and 12 Category C empirically validated mappings authorized for RA-015 implementation.
- Public Source Acquisition Adapters package `reference/ingestion/acquisition/` (`base.py`, `nhtsa.py`, `epa.py`, `smoke_test.py`) implementing `NHTSAAdapter` (NHTSA vPIC REST API `GetModelsForMakeYear`) and `EPAAdapter` (EPA FuelEconomy.gov REST API `vehicle/{id}`), standard library `urllib.request` HTTP transport isolation with strict TLS certificate verification (`ssl.create_default_context()`), raw assertion extraction into Tier 1 `SourceAssertionSet` objects, 2 test response fixtures in `reference/tests/fixtures/acquisition/`, and 8 automated unit tests (58 total tests passing). FuelEconomy.gov `city08` and `highway08` mapped to Tier 1 keys `city_mpg_epa_rating` and `highway_mpg_epa_rating`.



- Executable Python intermediate serialization contract package `reference/ingestion/` (`contracts.py`, `serialization.py`, `validation.py`) implementing Tier 1 `SourceAssertionSet` and Tier 2 `CandidateConfigurationDocument` logical schemas, embedded normalized interpretation layers, 7-dimension drivetrain details, preserved `factory_technical_features`, separated reconciliation/review states, semantic missing-value handling, deterministic JSON round-trip serialization, forward-compatible unknown-field preservation, and 4 controlled test fixtures in `reference/tests/fixtures/ingestion/` (50 total unit tests passing).
- Architecture Design Document `RA-011-Ingestion-Schema-Intermediate-Serialization-Design.md` defining versioned JSON logical contracts (`SourceAssertionSet` and `CandidateConfigurationDocument`), explicit normalized interpretation layers, envelope metadata standards (`artifact_type`, `schema_version`), candidate configuration contexts, high-fidelity 7-dimension drivetrain contracts, preserved unclassified technical features (`factory_technical_features`), and separated reconciliation and review workflow states.
- Architecture Design Document `RA-010-Reference-Ingestion-Source-Mapping-Architecture.md` defining Reference data ingestion source assessment (NHTSA, EPA, Toyota USA, J.D. Power), non-lossy 7-dimension drivetrain normalization, manufacturer-taxonomy trim mapping rules, candidate configuration representations, and attribute-level reconciliation precedence.



- Development Data Preservation & Recovery tooling (`snapshot_db`, `export_dev_data`, `verify_dev_data`) in `core/management/commands/`.

- Isolated test database support (`RIGARCHIVE_TEST_DB_PATH`) in `config/settings.py` for safe temporary verification.
- Local ignored preservation storage directory `backups/` (`backups/snapshots/` and `backups/logical/`) with `backups/.gitignore`.
- Automated synthetic unit test suite `DataPreservationTestCase` in `core/tests.py` verifying preservation, restoration, and authorization linkages (34 total tests passing).
- Developer guide `docs/development/DATA_PRESERVATION.md`.
- Architecture Design Document `RA-008-Development-Data-Preservation-Architecture.md`.
- Observation Domain application (`observation.apps.ObservationConfig`).

- `Observation` model in `observation/models.py` inheriting from `core.models.BaseModel`, providing dual identity (Integer PK + UUIDField), timestamps, and `PROTECT` foreign keys to `reference.VehicleDefinition` and `accounts.User`.
- Django Admin interface `ObservationAdmin` in `observation/admin.py` for administrator observation record management.
- Initial database migration `observation/migrations/0001_initial.py`.
- Observation domain test suite (`observation/tests.py`) covering validation, dual identity, `PROTECT` deletion, reference non-mutation, and admin integration (32 total tests passing).
- Architecture Design Document `RA-006-Observation-Foundation-Architecture.md`.
- Accessible application shell in `templates/base.html` featuring primary navigation (Home, Vehicles, About, Admin), skip-to-content link (`<a class="skip-link" href="#main-content">`), and `<main id="main-content" tabindex="-1">` target.
- Project-level presentation views (`about`, `custom_404`, `custom_500`) in `config/views.py`.
- About page (`templates/about.html`) presenting canonical vehicle identity, factory configuration reference, and evidence and provenance supporting technical understanding.
- Reusable breadcrumbs template partial (`templates/includes/breadcrumbs.html`).
- Custom 404 (`templates/404.html`) and resilient 500 (`templates/500.html`) error pages.
- Accessibility focus rings, breadcrumb list styles, hero/button styling, and responsive 320px support in `static/css/site.css`.
- Application shell, navigation, accessibility, and error handling unit test suite (`config/tests.py`).
- Reusable `core` Django application (`core.apps.CoreConfig`).
- Abstract model mixins (`UUIDModel`, `TimestampedModel`, `BaseModel`) providing shared UUID identity and timestamp capabilities.
- Unit test suite for core abstract model mixins (`core/tests.py`).
- Architecture Decision Record `ADR-0003-Core-Infrastructure.md`.
- Django project foundation using Python 3.14 and Django 6.0.
- Custom user model (`accounts.User`).
- Reference Domain models (`Manufacturer`, `VehicleModel`, `Generation`, `VehicleDefinition`).
- UUID-based external identities for reference entities.
- Automatically generated stable, immutable slugs.
- Django Admin interfaces for Reference Domain records.
- Public reference vehicle browser with nested URL routing and breadcrumb navigation.
- Shared base template, navigation, and core CSS stylesheet.
- Complete test suite covering models, views, core mixins, shell UX, observations, and URLs (32 tests passing).
- Gemini CLI project instructions (`GEMINI.md`).
- Task-based implementation workflow specification.
- Architecture Decision Records (`ADR-0001-Entity-Identity-Strategy.md`, `ADR-0002-Immutable-Automatic-Slugs.md`).

### Changed

- Updated `templates/home.html` page title to "RigArchive — Technical Vehicle Archive" and secondary button text to "About RigArchive", using approved project language without unbuilt domain placeholders.
- Updated footer description to non-numeric string `RigArchive Reference Implementation`.
- Refactored Reference Domain models (`Manufacturer`, `VehicleModel`, `Generation`, `VehicleDefinition`) to inherit from `core.models.BaseModel`.
- Reference slugs are generated automatically and are non-editable (`editable=False`) to guarantee public URL stability.
- Reference records retain integer database primary keys for performance while exposing UUIDs as stable external identifiers.

### Fixed

- Consolidated documentation hierarchy and populated initial Architecture Decision Records.

### Removed

- Removed obsolete `docs/decisions.md` script file containing duplicate model definitions.

### Security

- Enforced protected deletion (`on_delete=models.PROTECT`) on reference model relationships.