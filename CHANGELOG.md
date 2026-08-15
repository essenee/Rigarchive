# Changelog

All notable changes to RigArchive will be documented in this file.

## Unreleased

### Added

- Manufacturer Specification Evidence Acquisition & Normalization implementation package (`reference/ingestion/acquisition/manufacturer.py`, `reference/ingestion/normalization/manufacturer.py`, `reference/ingestion/normalization/rules/toyota_rules.py`) implementing `ManufacturerSpecificationAdapter` and `ManufacturerNormalizer`.
- `SourceApplicability` provenance contract (`market`, `applicability_basis`, `publisher_jurisdiction`, `unknown_fields`) attached as optional `source_applicability` on `SourceMetadata`, decoupled from caller `target_context` with zero automatic context-to-applicability conversion.
- Source-Independence Test enforcement in `ManufacturerNormalizer`, emitting mapped commercial `market` evidence (`"US"`) ONLY when independently established by explicit `source_applicability` provenance.
- Controlled first-party Toyota USA 2020 4Runner specification fixture (`reference/tests/fixtures/acquisition/toyota/2020_4runner_specs.json`) containing 12 official model-code configurations (`8664`–`8692`) and complete pressroom publication metadata.
- One `SourceAssertionSet` per model-code configuration grouping, preserving `provenance.native_record_id` and attribute coexistence without list-order inference or Cartesian product expansion.
- `SourceConfigurationIdentity` preservation (`source_id = "toyota_usa"`, `identity_type = "record_id"`, `native_identifier = "8666"`).
- Toyota factory grade normalization (`toyota_rules.py`) with exact uppercase grade matching (`SR5`, `TRD Off-Road`, `Limited`, `TRD Pro`) and safe-unmapped default handling for dealer option packages (`XP PREDATOR`, `PREMIUM AUDIO`).
- Drivetrain and engine normalization reuse (`Full-Time 4WD` $\rightarrow$ `AWD`, `TechnicalValue` displacement, cylinder count), leaving `transmission_descriptor` unmapped.
- Preserved-only `trim` and `market` Category B normalized assertion aggregation in `construct_candidate_configuration()`, enabling downstream [RA-019](file:///Users/esse/dev/Rigarchive/docs/implementation/tasks/RA-019-canonical-reference-import-planning-create-only-execution-implementation.md) candidates to supply all 8 required mapped evidence concepts and reach `ImportEligibilityStatus.ELIGIBLE` / `ImportPlannedAction.CREATE` / `ImportCreateBasis.FIRST_REPRESENTATION` under `plan_candidate_import()`.
- Context contradiction protection extension in `reference/ingestion/importing/planner.py`, checking caller `CandidateIdentity.trim_name` and `CandidateIdentity.market` against mapped evidence and flagging `REQUIRES_REVIEW` / `FLAG_REVIEW` upon contradiction.
- Comprehensive automated test suite `reference/tests/test_manufacturer_ingestion.py` containing 16 test methods (122 total project tests passing).
- Architecture Design Document `RA-020-Trim-Grade-Market-Applicability-Source-Normalization-Architecture.md` establishing the source, normalization, and provenance architecture for manufacturer grade taxonomy (`trim`) and commercial market applicability (`market`), formalizing the Source-Independence Test against context laundering, recommending explicit `SourceApplicability` provenance metadata, establishing manufacturer commercial sales market semantics, prohibiting unsupported cross-source Cartesian candidate joins, defining the cross-source join rule (attribute equality is not a join key), and defining the narrowed scope for `RA-021`.

- Architecture Decision Record `ADR-0005-Manufacturer-Grade-Taxonomy-Market-Applicability-Normalization.md` establishing durable architectural decisions for manufacturer grade taxonomy, factory grade vs option package disambiguation, commercial sales market definition, Source-Independence Test for market evidence, explicit source applicability provenance, prohibition of unsupported Cartesian candidate generation, cross-source join rules, and source-native configuration identifier boundaries.
- Canonical Reference Import Planning & Create-Only Execution package `reference/ingestion/importing/` (`__init__.py`, `planner.py`, `importer.py`) implementing deterministic pure Python candidate-to-canonical promotion machinery (`plan_candidate_import`, `execute_candidate_import`), re-exported through `reference/ingestion/__init__.py`.

- Transient import enums and dataclasses (`ImportEligibilityStatus`, `ImportPlannedAction`, `ImportExecutionOutcome`, `ImportCreateBasis`, `CanonicalImportPlan`, `CanonicalImportResult`). `CanonicalImportPlan` remains transient, non-persistent, and in-process.
- Strict Evidence Trust Boundary deriving canonical facts strictly from 8 mapped evidence concepts (`make`, `model`, `model_year`, `generic_drive_classification`, `engine_displacement_liters`, `engine_cylinders`, `trim`, `market`). Caller-supplied `CandidateIdentity` context (`manufacturer_name`, `vehicle_model_name`, `trim_name`, `market`) is checked ONLY for contradiction signaling and NEVER supplies missing canonical evidence.
- Direct evidence evaluation verifying set-based equality across all required keys. Multiple unequal normalized values for any concept flag `REQUIRES_REVIEW` (`FLAG_REVIEW`). Zero source precedence or winner selection.
- Controlled production 4Runner review/no-write behavior: production candidates (lacking mapped `trim` and `market`) plan to `REQUIRES_REVIEW` / `FLAG_REVIEW` performing 0 database writes.
- Deterministic parent entity resolution (`Manufacturer`, `VehicleModel`, `Generation`). Exactly 1 match resolves; 0 or >1 matches trigger `INELIGIBLE` or `REQUIRES_REVIEW`. Importer NEVER automatically creates parent entities.
- Target field construction containing ONLY current `VehicleDefinition` fields (`model_year`, `trim_name`, `engine_name`, `drivetrain`, `market`). Engine display string formatted via `_format_engine_name` (e.g. `"4.0L V6"`). Free-text `engine_name` string inequality is NOT used as proof of mechanical distinctness.
- Drivetrain-only mechanical dimension (`2WD`, `4WD`, `AWD`) as the ONLY approved structured mechanical dimension establishing `MECHANICAL_DIMENSION` `CREATE` against existing same-trim rows.
- Transactional create-only execution (`execute_candidate_import`) inside `transaction.atomic()` with pre-save `full_clean()`. Pre-save `ValidationError` returns `REJECTED`. `IntegrityError` caught outside failed atomic block after rollback completes: exact field match yields `NO_OP_EXACT_MATCH`; conflicting fields yield `REJECTED`.
- Stale-plan CREATE-basis revalidation inside transaction: `FIRST_REPRESENTATION` plans verify namespace `(generation_id, model_year, market)` remains empty. `MECHANICAL_DIMENSION` plans verify `mechanical_basis_existing_id` record remains unchanged in generation, model_year, market, trim_name, drivetrain, and namespace count. Changed namespaces or modified basis records return `ABORTED_STALE_PLAN`.
- Create-Only canonical protection: ZERO automatic `VehicleDefinition` updates, ZERO automatic deletes, ZERO parent auto-creations. Existing canonical database records are 100% read-only to the automated importer.
- Comprehensive unit test suite `reference/tests/test_canonical_import.py` containing 26 test methods (106 total project tests passing).
- Architecture Design Document `RA-018-Canonical-Reference-Matching-Import-Architecture.md` defining the two-tier Candidate-to-Canonical promotion boundary (`CandidateConfigurationDocument` -> `VehicleDefinition`), strict Evidence Trust Boundary (prohibiting uncorroborated context promotion), database representation key vs semantic identity distinctions (`(generation, slug)` as current storage representation key), missing trim handling (`trim_name = ""`), initial Create-Only & No-Op automated import policy (zero automated updates/deletes, zero parent auto-creation), parent entity resolution rules (`Manufacturer` -> `VehicleModel` -> `Generation`), refined import eligibility model (`ELIGIBLE`, `REQUIRES_REVIEW`, `INELIGIBLE`), transient `CanonicalImportPlan` architecture, controlled 2020 Toyota 4Runner empirical study reassessment, and implementation boundary for RA-019.

- Architecture Decision Record `ADR-0004-Canonical-Reference-Matching-Import-Promotion-Strategy.md` establishing durable architectural decisions for Candidate/Canonical tier separation, Evidence Trust Boundaries, Create-Only/No-Op initial import policy, database representation keys, and plan-first execution.
- Candidate Configuration Construction & Aggregation package `reference/ingestion/candidate/` (`__init__.py`, `builder.py`) implementing pure Python candidate configuration builder (`construct_candidate_configuration`), converting caller `CandidateIdentity` workflow context, Tier 1 `SourceAssertionSet` artifacts, and Tier 2 `NormalizedInterpretation` objects into transient `CandidateConfigurationDocument` artifacts in compliance with RA-016.

- Strict context vs evidence separation preserving caller `CandidateIdentity` without evidence overwriting, internal context verification (`supported`, `partially_supported`, `contradicted`, `unverified`), and context contradiction human review triggers.
- Conservative lineage-based corroboration requiring 2+ independent `source_id` authorities (`nhtsa_vpic` vs `epa_fueleconomy`); repeated retrieval of same record and same-source multi-record payloads yield `single_source` without claiming unestablished corroboration.
- Conflict-safe scalar attribute projection leaving scalar fields (`engine.cylinders`, `drivetrain.architecture`) unset (`None`) under independent-source conflict while preserving all interpretations and provenance links.
- Concept projection vs preservation distinction: Category A projected concepts populate typed destinations and `attribute_provenance`; Category B mapped-but-not-projected concepts (`city_mpg_epa_rating`, `highway_mpg_epa_rating`) and Category C unmapped concepts remain preserved in `normalized_assertions` without fake candidate fields.
- Prohibition of Tier 1 normalization bypass: raw descriptor strings (KDSS, A-TRAC) produce `factory_technical_features = []`.
- Multi-source transitive assertion lookup verifying `source_assertion_ref` links across multi-source payloads.
- Comprehensive automated test suite in `reference/tests/test_candidate_construction.py` containing 13 test methods (80 total project tests passing).
- Architecture Design Document `RA-016-Candidate-Configuration-Construction-Aggregation-Architecture.md` defining transient candidate configuration document (`CandidateConfigurationDocument`) boundaries, Hybrid Context/Evidence Grouping Model (`CandidateIdentity` workflow context), explicit separation of Evidence Reconciliation from Candidate-Context Verification (`supported`, `partially_supported`, `contradicted`, `unverified`), lineage-based corroboration rules, conflict-safe attribute projection without winner selection, consistent review policy, transient `candidate_reference` semantics, semantic determinism, 15-scenario evidence-state matrix, 5th-Gen 4Runner stress test across 3 scenarios, and Outcome B contract support (zero contract extensions required for RA-017).

### Fixed

- Resolved `TechnicalValue` serialization interoperability defect in `reference/ingestion/serialization.py` (`normalized_interpretation_to_dict` and `normalized_interpretation_from_dict`), enabling lossless JSON round-trip serialization of `NormalizedInterpretation` objects containing `TechnicalValue` (emitted by RA-015 EPA displacement normalizer).

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