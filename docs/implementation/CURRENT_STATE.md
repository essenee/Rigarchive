RigArchive Project Status Document
Version: 1.3
Last Updated: 2026-08-15
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

Milestone 11 — Source Assertion Normalization Implementation & Fixture Validation

Implementation Task:
RA-015 — Source Assertion Normalization Implementation & Fixture Validation (Completed)
- Package Location: `reference/ingestion/normalization/` (`__init__.py`, `base.py`, `nhtsa.py`, `epa.py`, `rules/__init__.py`, `rules/nhtsa_rules.py`, `rules/epa_rules.py`)
- Source Normalizers Implemented: `NHTSANormalizer` (`source_id: "nhtsa_vpic"`) and `EPANormalizer` (`source_id: "epa_fueleconomy"`) extending `BaseSourceNormalizer` and dispatched via top-level function `normalize_source_assertions(assertion_set)`
- Implemented Mappings: Strictly the 12 Category C mappings authorized by RA-014 (NHTSA: `make_id` -> `nhtsa_make_id`, `make_name` -> `make`, `model_id` -> `nhtsa_model_id`, `model_name` -> `model`; EPA: `model_year` -> integer, `make` -> direct copy, `drive_descriptor` -> `generic_drive_classification: "4WD"` & `drivetrain_architecture: "part_time_4wd"`, `engine_displacement_liters` -> `TechnicalValue`, `engine_cylinders` -> integer, `city_mpg_epa_rating` -> integer, `highway_mpg_epa_rating` -> integer)
- Evidence Safety Enforcement: Zero unsupported drivetrain modes (`2H`, `4H`, `4L`), low-range ratios, lock states, or capabilities manufactured; zero Category B mappings implemented
- Unmapped & Error Handling: Case A (known concept, unmapped value) preserves target concept key with `mapping_status: "unmapped"`; Case B (unknown attribute key) emits no `NormalizedInterpretation` while preserving the `SourceAssertion` unchanged in `SourceAssertionSet`; parsing failures fail gracefully into `unmapped` status; unsupported sources raise `UnsupportedSourceError`

- Testing & Offline Validation: 9 comprehensive automated test methods in `reference/tests/test_normalization.py` verifying contract dispatch, Category C mappings, drivetrain safety, unmapped handling, parsing failure handling, determinism, and offline adapter integration (67 total tests passing)
- Zero ORM / Migration Impact: Pure Python dataclasses; 0 Django ORM models, 0 migrations, 0 database writes
- Documentation & Task Record: `docs/implementation/tasks/RA-015-source-assertion-normalization-implementation.md`
Milestone 12 — Candidate Configuration Construction & Aggregation Architecture

Architecture Task:
RA-016 — Candidate Configuration Construction & Aggregation Architecture (Approved Architecture)
- Design Document Location: `docs/architecture/designs/RA-016-Candidate-Configuration-Construction-Aggregation-Architecture.md`
- Candidate Configuration Boundary: Transient, non-canonical, JSON-serializable artifact (`CandidateConfigurationDocument`) representing an evidence-backed hypothesis; completely separate from persistent canonical database entities (`VehicleDefinition`)
- Hybrid Context/Evidence Grouping Model: Caller-supplied `CandidateIdentity` provides workflow aggregation context, but is NOT source evidence and NOT canonical truth; normalized source evidence may support, contradict, or leave context unverified
- Separation of Evidence Reconciliation from Context Verification: `reconciliation_state = "conflicting"` is strictly reserved for evidence-to-evidence conflicts (2+ independent lineages disagreeing); candidate-context contradiction does not alter or manufacture evidence states, while context contradiction triggers top-level human review
- Lineage-Based Corroboration: `corroborated` requires 2+ independent evidence lineages (e.g. `nhtsa_vpic` vs `epa_fueleconomy`); repeated retrieval of the same source record yields `single_source`; multiple interpretations derived from one assertion represent one lineage
- No Tier 1 Normalization Bypass: Candidate attributes and `factory_technical_features` are projected ONLY from approved mapped `NormalizedInterpretation` objects emitted by RA-015; current RA-015 mappings yield `factory_technical_features = []`
- Conflict-Safe Projection & No Winner Selection: Under evidence conflict, scalar projected fields are left UNSET (`None`) while ALL conflicting interpretations, provenance links, and `conflicting` states are retained; winner selection is strictly prohibited
- Review Policy Consistency: `incomplete` state alone does NOT trigger human review (`requires_human_review = False`); automatic review is triggered strictly by evidence conflict (`conflicting`), evidence ambiguity (`ambiguous`), or context contradiction (`contradicted`)
- Transient Non-Semantic `candidate_reference`: Opaque, non-semantic workflow identifier; no semantic hashing from identity fields
- Semantic Determinism: Identical semantic inputs produce identical projected attributes, evidence states, provenance maps, and deterministic array ordering; artifact-generation metadata (`created_at`) may vary per instantiation
- Outcome B Contract Support: Existing RA-011/RA-012 contract is 100% sufficient using implementation conventions; zero contract modifications required for RA-017; formal context-verification enum persistence remains deferred
Milestone 13 — Candidate Configuration Construction & Aggregation Implementation

Implementation Task:
RA-017 — Candidate Configuration Construction & Aggregation Implementation (Completed)
- Package Location: `reference/ingestion/candidate/` (`__init__.py`, `builder.py`)
- Candidate Builder Implemented: Pure Python `construct_candidate_configuration` transforming caller `CandidateIdentity` workflow context, Tier 1 `SourceAssertionSet` artifacts, and Tier 2 `NormalizedInterpretation` objects into transient, non-canonical `CandidateConfigurationDocument` artifacts
- Context vs Evidence Separation: Caller-supplied `CandidateIdentity` is aggregation context, not source evidence; evidence (`make`, `model`, `model_year`) verifies or contradicts context without overwriting `CandidateIdentity`
- Lineage & Corroboration Boundary: `corroborated` requires 2+ independent `source_id` authorities; repeated retrieval of same record yields `single_source`; multiple records from same source yield `single_source` (same-source multi-record independence deferred)
- Conflict-Safe Projection & No Winner Selection: Under true independent-source conflict, scalar projected fields (`engine.cylinders`, `drivetrain.architecture`) are left UNSET (`None`), all evidence is preserved, and human review is required
- Concept Handling: Category A projected concepts receive typed destinations, `attribute_provenance`, and `attribute_states`; Category B mapped-but-not-projected concepts (`city_mpg_epa_rating`, `highway_mpg_epa_rating`) and Category C unmapped concepts remain preserved in `normalized_assertions` without fake candidate fields
- Tier 1 Bypass Prohibition: Consumes only approved mapped interpretations; raw Tier 1 descriptor strings (KDSS, A-TRAC) produce `factory_technical_features = []`
- Context Contradiction & Review Workflow: Contradictory evidence flags `requires_human_review = True`, sets `review_workflow_disposition = "pending_review"`, and records notes in `reconciliation_notes` without altering evidence reconciliation states
- Provenance & Serialization: Transitive assertion lookup verifies all `source_assertion_ref` links across multi-source payloads; includes `TechnicalValue` serialization interoperability fix in `reference/ingestion/serialization.py`
- Testing & Offline Validation: 13 comprehensive test methods in `reference/tests/test_candidate_construction.py` (80 total project tests passing)
- Zero ORM / Migration Impact: Pure Python dataclasses; 0 Django ORM models, 0 migrations, 0 database writes
Milestone 14 — Canonical Reference Matching & Import Architecture

Architecture Task:
RA-018 — Canonical Reference Matching & Import Architecture (Approved Architecture)
- Design Document Location: `docs/architecture/designs/RA-018-Canonical-Reference-Matching-Import-Architecture.md`
- Architectural Decision Record: `docs/architecture/ADR/ADR-0004-Canonical-Reference-Matching-Import-Promotion-Strategy.md`
- Candidate-to-Canonical Promotion Boundary: Two-tier architecture separating transient non-canonical `CandidateConfigurationDocument` artifacts from persistent database `VehicleDefinition` records
- Strict Evidence Trust Boundary: Source evidence governs canonical data; caller `CandidateIdentity` context cannot be written into canonical fields as source evidence. `CandidateIdentity.trim_name = "SR5"` without normalized evidence requires review and blocks auto-creation
- Database Representation Key vs Identity: `(generation_id, slug)` is current storage uniqueness key and deterministic representation key for identical current representations; it is not universal real-world identity
- Trim Sufficiency Policy: `trim_name = ""` represents missing trim evidence; candidates lacking normalized trim on multi-trim model years require human review (`REQUIRES_HUMAN_REVIEW`)
- Initial Create-Only & No-Op Policy: Automated importer creates proven-distinct new records and executes no-ops on exact existing matches; NEVER updates existing records, NEVER deletes records, and NEVER automatically creates parent `Manufacturer`, `VehicleModel`, or `Generation` entities
- Plan-First Architecture: Transient in-process `CanonicalImportPlan` handles read-only eligibility and parent resolution prior to transactional execution
- Controlled 2020 4Runner Assessment: Current NHTSA/EPA evidence lacks normalized trim, planning cleanly into `REQUIRES_HUMAN_REVIEW` (no-write), safely protecting canonical Reference data
- Zero ORM / Migration Impact: Architecture and design document pass; 0 Django ORM models, 0 migrations, 0 database writes, 0 application code changes
Milestone 15 — Canonical Reference Import Planning & Create-Only Execution Implementation

Implementation Task:
RA-019 — Canonical Reference Import Planning & Create-Only Execution Implementation (Completed)
- Package Location: `reference/ingestion/importing/` (`__init__.py`, `planner.py`, `importer.py`)
- Promotion Pipeline: Implemented pure Python read-only planning `plan_candidate_import(candidate)` and transactional create-only execution `execute_candidate_import(plan)` promoting `CandidateConfigurationDocument` artifacts into canonical `VehicleDefinition` records
- Transient Import Types: `ImportEligibilityStatus`, `ImportPlannedAction`, `ImportExecutionOutcome`, `ImportCreateBasis`, `CanonicalImportPlan`, `CanonicalImportResult` re-exported in `reference/ingestion/__init__.py`. `CanonicalImportPlan` remains transient, non-persistent, and in-process
- Strict Evidence Trust Boundary: Canonical facts are derived strictly from mapped `candidate.normalized_assertions` across 8 required concepts (`make`, `model`, `model_year`, `generic_drive_classification`, `engine_displacement_liters`, `engine_cylinders`, `trim`, `market`). Caller-supplied `CandidateIdentity` context (`manufacturer_name`, `vehicle_model_name`, `trim_name`, `market`) is checked ONLY for contradiction signaling and does NOT supply missing canonical evidence
- Direct Evidence Consistency: Evaluates mapped values directly as sets (`len(distinct)`). Multiple unequal normalized values for any concept flag `REQUIRES_REVIEW` (`FLAG_REVIEW`). Zero source precedence or winner selection
- Parent Resolution: Deterministic lookup against active database records (`Manufacturer`, `VehicleModel`, `Generation`). Exactly 1 match resolves; 0 or >1 matches trigger `INELIGIBLE` or `REQUIRES_REVIEW`. Importer NEVER automatically creates parent entities
- Target Field & Engine Representation: Target dictionary contains ONLY current `VehicleDefinition` fields (`model_year`, `trim_name`, `engine_name`, `drivetrain`, `market`). Engine display string formatted via `_format_engine_name` (e.g. `"4.0L V6"`). Free-text `engine_name` string inequality is NOT used as proof of mechanical distinctness
- Drivetrain Mechanical Dimension: `drivetrain` (`2WD`, `4WD`, `AWD`) is the ONLY approved structured mechanical dimension establishing `MECHANICAL_DIMENSION` `CREATE` against existing same-trim rows
- Controlled Production 4Runner Behavior: Default production NHTSA/EPA candidates (lacking mapped `trim` and `market`) plan to `REQUIRES_REVIEW` / `FLAG_REVIEW` performing ZERO database writes
- Stale-Plan Revalidation: Inside `transaction.atomic()`, `FIRST_REPRESENTATION` plans verify namespace `(generation_id, model_year, market)` remains empty. `MECHANICAL_DIMENSION` plans verify `mechanical_basis_existing_id` record remains unchanged in generation, model_year, market, trim_name, drivetrain, and namespace count. Changed namespaces or modified basis records return `ABORTED_STALE_PLAN`
- Transaction & IntegrityError Safety: Execution runs inside `transaction.atomic()` with pre-save `full_clean()`. `IntegrityError` caught outside failed atomic block after rollback completes: exact field match yields `NO_OP_EXACT_MATCH`; conflicting fields yield `REJECTED`
- Create-Only Policy: Zero automatic `VehicleDefinition` updates, zero deletes, zero parent auto-creations
- Testing & Verification: 26 focused test methods in `reference/tests/test_canonical_import.py` (106 total project tests passing)
- Zero ORM / Migration Impact: Pure Python import engines; 0 Django ORM schema changes, 0 migrations

Milestone 16 — Trim/Grade & Market Applicability Source and Normalization Architecture

Architecture Task:
RA-020 — Trim/Grade & Market Applicability Source and Normalization Architecture (Approved Architecture)
- Design Document Location: `docs/architecture/designs/RA-020-Trim-Grade-Market-Applicability-Source-Normalization-Architecture.md`
- Architectural Decision Record: `docs/architecture/ADR/ADR-0005-Manufacturer-Grade-Taxonomy-Market-Applicability-Normalization.md`
- Manufacturer Grade Taxonomy: Defines `trim` as manufacturer-recognized factory grade/trim identity (`SR5`, `SR5 Premium`, `TRD Off-Road`, `Limited`). Disambiguates factory grades from dealer accessory packages (e.g. `XP Predator`) which belong in Observation/Knowledge domains
- Commercial Sales Market Definition: Defines `VehicleDefinition.market` as manufacturer commercial sales/applicability market (`US`, `CA`, `OT`), distinguishing commercial market from regulatory jurisdiction
- Source-Independence Test: Enforces that market applicability may become normalized evidence ONLY when independently established by the source artifact or acquisition definition. Prohibits laundering caller request context (`CandidateIdentity` or `target_context`) into canonical facts
- Explicit Source Applicability Provenance: Recommends `source_applicability` provenance metadata structure (`market`, `applicability_basis`, `publisher_jurisdiction`) attached to `SourceMetadata`
- Preserved-Only Candidate Projection: Retains `trim` and `market` as preserved-only mapped normalized assertions in `normalized_assertions` (Category B), satisfying RA-019 promotion without requiring contract changes
- Cross-Source JOIN Rule & Cartesian Prohibition: Attribute equality alone is NOT a configuration join key. Candidate construction MUST NOT generate unsupported Cartesian combinations (8 grades x 3 EPA records != 24 candidates). Requires evidence-backed configuration correspondence
- Manufacturer Acquisition Abstraction: Recommends reusable `ManufacturerSpecificationAdapter` / `StructuredDatasetAdapter` decoupling generic acquisition from manufacturer-specific mapping/taxonomy rules
- Controlled 2020 4Runner Study: Verified 8 U.S. factory grades, Toyota terminology ("Grade"), and 4-digit order model codes (`8666`) providing source-native configuration identity (`SourceConfigurationIdentity`)

Milestone 17 — Manufacturer Specification Evidence Acquisition & Normalization Implementation

Implementation Task:
RA-021 — Manufacturer Specification Evidence Acquisition & Normalization Implementation (Completed)
- Task Record Location: `docs/implementation/tasks/RA-021-manufacturer-specification-evidence-acquisition-normalization-implementation.md`
- Package Components: `reference/ingestion/acquisition/manufacturer.py`, `reference/ingestion/normalization/manufacturer.py`, `reference/ingestion/normalization/rules/toyota_rules.py`, `reference/tests/fixtures/acquisition/toyota/2020_4runner_specs.json`, `reference/tests/test_manufacturer_ingestion.py`
- SourceApplicability Contract: Implemented `SourceApplicability` dataclass (`market`, `applicability_basis`, `publisher_jurisdiction`, `unknown_fields`) attached to `SourceMetadata`. Decoupled from `target_context` with zero automatic context-to-applicability conversion
- Schema Backward Compatibility: Retained major `schema_version = "1.0.0"`. Optional metadata field addition is 100% backward-compatible with legacy deserialization (`source_applicability = None`) and positional constructor safety
- Controlled Toyota USA Fixture: Added `2020_4runner_specs.json` containing 12 official Toyota US model-code configurations (`8664`–`8692`) and complete first-party pressroom provenance metadata
- One SourceAssertionSet Per Configuration: `ManufacturerSpecificationAdapter` emits one `SourceAssertionSet` per model-code configuration row, preserving `provenance.native_record_id` and attribute coexistence without list-order inference
- SourceConfigurationIdentity Preservation: Candidate builder extracts `SourceConfigurationIdentity` (`source_id = "toyota_usa"`, `identity_type = "record_id"`, `native_identifier = "8666"`)
- Manufacturer Normalization & Toyota Rules: `ManufacturerNormalizer` and `toyota_rules.py` enforce exact uppercase factory grade lookup (`SR5`, `TRD Off-Road`, `Limited`, `TRD Pro`). Dealer option packages (`XP PREDATOR`, `PREMIUM AUDIO`) default safely to `mapping_status = "unmapped"`
- Source-Independence Test Enforcement: Mapped `market` normalized assertion (`"US"`) is emitted ONLY when `source_applicability` is present and matches the market assertion. `target_context` market alone is rejected
- Concept & Drivetrain Reuse: Reuses standard `make`, `model`, `model_year`, `generic_drive_classification`, `drivetrain_architecture` (`Full-Time 4WD` $\rightarrow$ `AWD`), `engine_displacement_liters` (`TechnicalValue`), and `engine_cylinders`. `transmission_descriptor` remains raw/unmapped
- Preserved-Only Projection & Candidate Building: `construct_candidate_configuration` aggregates mapped `trim` and `market` as preserved-only mapped assertions (Category B) with zero candidate builder contract changes
- Zero Cross-Source Joins & Cartesian Safety: Zero automatic Toyota/EPA/NHTSA joins. 12 configuration rows produce exactly 12 candidate documents without Cartesian expansion
- RA-019 Downstream Planning Reachability: Fully evidenced candidates supply all 8 required concepts (`make`, `model`, `model_year`, `generic_drive_classification`, `engine_displacement_liters`, `engine_cylinders`, `trim`, `market`), reaching `ImportEligibilityStatus.ELIGIBLE` / `ImportPlannedAction.CREATE` / `ImportCreateBasis.FIRST_REPRESENTATION` under `plan_candidate_import`
- Context Contradiction Correction: Extended `planner.py` to check `CandidateIdentity.trim_name` and `CandidateIdentity.market` against mapped evidence. Contradictions trigger `REQUIRES_REVIEW` / `FLAG_REVIEW`
- Test Baseline: 16 focused tests in `reference/tests/test_manufacturer_ingestion.py` (122 total project tests passing)
- Zero ORM / Migration Impact: Pure Python ingestion adapters and normalizers; 0 Django ORM schema changes, 0 migrations, 0 database writes

Milestone 18 — Production Manufacturer Evidence Acquisition & Orchestration Architecture

Architecture Task:
RA-022 — Production Manufacturer Evidence Acquisition & Orchestration Architecture (Approved Architecture)
- Design Document Location: `docs/architecture/designs/RA-022-Production-Manufacturer-Evidence-Acquisition-Orchestration-Architecture.md`
- Architectural Decision Record: `docs/architecture/ADR/ADR-0006-Immutable-Raw-Acquisition-Snapshots-Layered-Manufacturer-Profiles.md`
- Empirical Cross-Manufacturer Validation: RA-022A research study validated profile layering across Toyota USA, Ford Motor Company, Jeep/Stellantis, and Mercedes-Benz USA, confirming that publication structures and taxonomy vocabulary vary across and within manufacturer ecosystems
- Layered Profile Architecture: Separates `ManufacturerProfile` (taxonomy mappings, package classification, identity semantics) from `PublicationSourceProfile` (locators, fetch options, snapshot capture, extractors). Rejects monolithic per-manufacturer adapters
- Immutable Raw Source Snapshots: Requires all production acquisition operations to retain acquired raw source payloads (HTML, JSON, PDF, CSV, XLS) immutably in raw source artifact storage (`storage/raw_source_artifacts/`) before extraction occurs. Changed locators/content generate new snapshots
- Full SHA-256 Content Hashing & Revisions: Uses full 64-character SHA-256 hex digest for durable content hashing and revision tracking. Shortened hashes are display-only
- Source-Native & Structural Row Identity: Explicit codes (Toyota `8666`, Ford `E5B`, Jeep `JLJL74`) populate `SourceConfigurationIdentity` (`identity_type = "model_code"`). Uncoded sources (Mercedes-Benz `media.mbusa.com`) use source-local structural row identity (`identity_type = "structural_row"`). Rejects synthetic attribute-derived `composite_row` identity
- Explicit Multi-Document Linking: Cross-document configuration joins require explicit, evidence-backed manufacturer cross-reference keys. Joining unlinked documents via matching string names is strictly prohibited
- Plan-First Production Orchestration Boundary: Production acquisition orchestration stops automatically at `plan_candidate_import()`, producing an in-memory `CanonicalImportPlan` dry-run report. Zero automatic database writes (`execute_candidate_import`) are performed
- Initial Operating Mode: Operator-invoked CLI execution. Schedulers, crawlers, and dynamic headless browsers are excluded from initial scope
- Proposed Next Milestone: RA-024 — Canonical Reference Import Execution & Execution Provenance Workflow Architecture & Implementation

Milestone 20 — Canonical Reference Import Execution & Execution Provenance Workflow Implementation

Implementation Task:
RA-024 — Canonical Reference Import Execution & Execution Provenance Workflow Implementation (Completed)
- Design Document: `docs/architecture/designs/RA-024-Canonical-Reference-Import-Execution-Execution-Provenance-Workflow-Architecture.md`
- Architectural Decision Record: `docs/architecture/ADR/ADR-0007-Explicit-Human-Authorization-Execution-Audit-Receipts-Canonical-Promotion.md`
- Review Manifest Contract: Pure-Python dataclasses (`CanonicalImportReviewPlan`, `CanonicalImportReviewManifest`, `v1.0`) for serializing, validating, and reconstructing operator-reviewed import plans prior to execution dispatch (`reference/ingestion/manifest.py`)
- Deterministic Compact SHA-256 Hashing: `compute_manifest_hash()` computes a deterministic digest (`sha256:<64_hex>`) over sorted UTF-8 JSON key canonicalization (`separators=(",", ":")`). File indentation does not invalidate parsed dictionary hash; payload modification invalidates hash
- Strict Validation & Type Safety: `dict_to_manifest()` rejects unknown top-level and per-plan fields, duplicate candidate references, and invalid enum values. Integer fields (`namespace_snapshot_count`, `mechanical_basis_existing_id`, `resolved_manufacturer_id`, `resolved_vehicle_model_id`, `resolved_generation_id`, `existing_vehicle_definition_id`) accept strictly `int` or `None`, explicitly rejecting `bool` (`True`, `False`), `float` (`1.0`), and numeric strings (`"1"`)
- Exact Plan Reconstruction: `reconstruct_plan_from_manifest()` instantiates `CanonicalImportPlan` directly from reviewed manifest fields with **ZERO** dynamic re-planning calls (`plan_candidate_import`)
- Execution Audit Receipts: Created `ImportExecutionReceipt` ORM model (`reference/models.py`) and migration `0002_importexecutionreceipt.py`. Captures `executed_at`, `operator_label`, `manifest_hash`, evidence anchors (`source_id`, `raw_artifact_hash`, `raw_artifact_reference`, `source_identity_type`, `native_identifier`), target configuration snapshot, actual outcome (`CREATED`, `NO_OP_EXACT_MATCH`, `ABORTED_STALE_PLAN`, `REJECTED`), output messages, and `on_delete=models.SET_NULL` FKs + primary identity snapshots (`pk_snapshot`, `uuid_snapshot`, `slug_snapshot`) guaranteeing audit log survival
- Read-Only Django Admin Viewer: `ImportExecutionReceiptAdmin` (`reference/admin.py`) sets `has_add_permission = False`, `has_change_permission = False`, `has_delete_permission = False`, with all fields read-only
- Transactional Workflow Engine: `execute_canonical_import_workflow()` (`reference/ingestion/importing/workflow.py`) wraps `CREATE` operations inside `transaction.atomic()`, ensuring `VehicleDefinition` creation and `ImportExecutionReceipt` persistence succeed together or roll back cleanly
- Explicit Human Authorization CLI: `execute_canonical_import` management command (`reference/management/commands/execute_canonical_import.py`) enforces mandatory interactive operator confirmation (`input("Do you authorize... [y/N]")`) on every run. Intentionally omits `--no-input` flag to guarantee human confirmation
- Production Acquisition Dry-Run Manifest Output: Extended `acquire_manufacturer_specs` (`reference/management/commands/acquire_manufacturer_specs.py`) with `--output-manifest <path>` to emit executable review manifests during production dry-runs with guaranteed **ZERO** canonical database writes
- Test Baseline: 16 focused tests in `reference/tests/test_canonical_import_execution.py` (164 total project tests passing)

Milestone 21 — Production Manufacturer Extraction & Review-Adjudication Architecture

Architecture Task:
RA-025 — Production Manufacturer Extraction & Review-Adjudication Architecture (Approved Architecture)
- Design Document Location: `docs/architecture/designs/RA-025-Production-Manufacturer-Extraction-Review-Adjudication-Architecture.md`
- Architectural Decision Record: `docs/architecture/ADR/ADR-0008-Deterministic-Extraction-Review-Adjudication-Adjudicated-Grade-Promotion.md`
- Deterministic Extraction Boundary: Eliminates runtime sidecar JSON file (`2020_4runner_specs.json`) from production candidate construction path, operating deterministically from retained raw publisher snapshots via versioned strategy extractors (e.g. `ToyotaPressroomHtmlTableStrategy`)
- Golden Test Fixture Strategy: Retains `2020_4runner_specs.json` in `reference/tests/fixtures/` strictly as golden test benchmarks to validate extractor `SourceAssertionSet` outputs against raw publisher snapshots
- Review-Adjudication Boundary: Formalizes `CanonicalImportAdjudication` contract as a durable human domain finding (`adjudication_hash = "sha256:<64_hex>"`) for bounded adjudicable review conditions (`distinct_factory_grade`, `special_edition_grade`)
- Five-Stage Promotion Lifecycle: Establishes explicit lifecycle (`Planning` -> `Adjudication` -> `Re-planning` -> `Execution Authorization` -> `Execution`). Adjudication does NOT execute directly and does NOT inherit old authorizations
- Third Epistemic Basis (`ADJUDICATED_DISTINCT_GRADE`): Introduces `ImportCreateBasis.ADJUDICATED_DISTINCT_GRADE` to represent human-reviewed proof of a legitimate factory grade in a populated namespace, preserving existing `FIRST_REPRESENTATION` and `MECHANICAL_DIMENSION` semantics
- Exact-Plan Preservation: Execution NEVER converts one `create_basis` into another. Stale database conditions abort with `ABORTED_STALE_PLAN`, requiring fresh planning and a NEW review manifest
- Stale Revalidation Rules: An `ADJUDICATED_DISTINCT_GRADE` plan is stale if parent entities become inactive or a same-trim canonical row appears prior to execution. Unrelated trim growth is non-material
- Review Manifest Versioning (v1.1): Supports optional per-plan `adjudication_reference` and `adjudication_hash` while maintaining 100% executable backward compatibility for v1.0 manifests
- Execution Receipt Linkage: Extends `ImportExecutionReceipt` with optional `adjudication_hash` to record complete audit lineage from raw snapshot to canonical creation
- Controlled 2020 Toyota Study: Establishes that populating 12 2020 4Runner configurations requires **12 separately authorized executions** under RA-024 (`[y/N]`), of which **7 require human domain adjudications** and 5 derive from automated bases (1 `FIRST_REP` + 4 `MECH_DIM`)
- Next Planned Milestone: RA-026 — Deterministic Toyota Extraction & Review-Adjudication Implementation


7. Architectural Decision Records (ADRs)
Implemented and Accepted:
- ADR-0001: Entity Identity Strategy (Dual Integer PK + UUID)
- ADR-0002: Immutable Automatic Slugs (Non-editable, auto-generated on creation)
- ADR-0003: Core Infrastructure Application (Shared abstract base models in `core`, domain isolation)
- ADR-0004: Canonical Reference Matching & Import Promotion Strategy (Candidate-to-canonical tiers, Evidence Trust Boundary, Create-Only initial policy)
- ADR-0005: Manufacturer Grade Taxonomy and Market Applicability Normalization Strategy (Factory grade taxonomy, Source-Independence Test, commercial sales market, Cartesian prohibition)
- ADR-0006: Immutable Raw Acquisition Snapshots and Layered Manufacturer Profile Architecture (Immutable raw snapshots, full SHA-256 hashing, layered profiles, structural-row identity, explicit-key multi-document linking, plan-first dry-run orchestration)
- ADR-0007: Explicit Human Authorization & Execution Audit Receipts for Canonical Promotion (Review manifest contract, exact-plan authorization boundary, stale plan aborts, durable execution audit receipts, transactional atomicity)
- ADR-0008: Deterministic Extraction, Review Adjudication & Adjudicated Grade Promotion (Deterministic extraction strategies, golden fixture testing, 5-stage lifecycle, bounded human domain adjudications, `ADJUDICATED_DISTINCT_GRADE` basis, exact-plan preservation, same-trim stale checks, manifest v1.1 linkage, audit receipt linkage)




8. Current Testing
Implemented:
- Development Data Preservation tests (`core/tests.py`)
- Observation Domain tests (`observation/tests.py`)
- Application Shell & UX tests (`config/tests.py`)
- Core mixin & inheritance tests (`core/tests.py`)
- Reference Model tests (`reference/tests/test_models.py`)
- Public Reference View & URL tests (`reference/tests/test_views.py`)
- Intermediate Serialization tests (`reference/tests/test_ingestion_serialization.py`)
- Public Source Acquisition Adapter tests (`reference/tests/test_acquisition_adapters.py`)
- Source Assertion Normalization tests (`reference/tests/test_normalization.py`)
- Candidate Configuration Construction tests (`reference/tests/test_candidate_construction.py`)
- Manufacturer Specification Ingestion tests (`reference/tests/test_manufacturer_ingestion.py`)
- Production Manufacturer Acquisition & Orchestration tests (`reference/tests/test_production_manufacturer_acquisition.py`)
- Canonical Reference Import tests (`reference/tests/test_canonical_import.py`)
- Canonical Import Execution & Execution Provenance tests (`reference/tests/test_canonical_import_execution.py`)
Current status:
- All 164 tests passing.
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
- Completed tasks: RA-003 — Core Foundation, RA-005 — Application Shell & UX Foundation, RA-007 — Observation Domain Foundation, RA-009 — Development Data Preservation and Recovery Implementation, RA-012 — Intermediate Serialization Contract Implementation & Fixture Validation, RA-013 — Public Source Acquisition Adapters, RA-015 — Source Assertion Normalization Implementation & Fixture Validation, RA-017 — Candidate Configuration Construction & Aggregation Implementation, RA-019 — Canonical Reference Import Planning & Create-Only Execution Implementation, RA-021 — Manufacturer Specification Evidence Acquisition & Normalization Implementation, RA-023 — Production Manufacturer Artifact Acquisition & Dry-Run Orchestration Implementation, RA-024 — Canonical Reference Import Execution & Execution Provenance Workflow Implementation.




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
│   │   │   ├── manufacturer.py
│   │   │   ├── nhtsa.py
│   │   │   ├── profiles.py
│   │   │   ├── smoke_test.py
│   │   │   └── snapshots.py
│   │   ├── candidate/
│   │   │   ├── __init__.py
│   │   │   └── builder.py
│   │   ├── importing/
│   │   │   ├── __init__.py
│   │   │   ├── importer.py
│   │   │   └── planner.py
│   │   ├── normalization/
│   │   │   ├── __init__.py
│   │   │   ├── base.py
│   │   │   ├── epa.py
│   │   │   ├── manufacturer.py
│   │   │   ├── nhtsa.py
│   │   │   └── rules/
│   │   │       ├── __init__.py
│   │   │       ├── epa_rules.py
│   │   │       ├── nhtsa_rules.py
│   │   │       └── toyota_rules.py
│   │   ├── orchestration/
│   │   │   ├── __init__.py
│   │   │   └── manufacturer.py
│   │   ├── contracts.py
│   │   ├── serialization.py
│   │   └── validation.py
│   ├── management/
│   │   ├── __init__.py
│   │   └── commands/
│   │       ├── __init__.py
│   │       ├── acquire_manufacturer_specs.py
│   │       └── execute_canonical_import.py
│   ├── migrations/
│   │   ├── migrations/
│   │   │   ├── 0001_initial.py
│   │   │   ├── 0002_importexecutionreceipt.py
│   │   │   └── 0003_importexecutionreceipt_adjudication_hash.py
│   │   ├── models.py
│   │   ├── tests/
│   │   │   ├── __init__.py
│   │   │   ├── fixtures/
│   │   │   │   ├── acquisition/
│   │   │   │   │   ├── epa/
│   │   │   │   │   │   └── vehicle_42101.json
│   │   │   │   │   ├── nhtsa/
│   │   │   │   │   │   └── get_models_toyota_2020.json
│   │   │   │   │   └── toyota/
│   │   │   │   │       ├── 2020_4runner_pricing.pdf
│   │   │   │   │       ├── 2020_4runner_specs.pdf
│   │   │   │   │       └── 2020_4runner_specs.json
│   │   │   │   └── ingestion/
│   │   │   │       ├── candidate_configuration_4runner_2010_i4_2wd.json
│   │   │   │       ├── candidate_configuration_4runner_2020_trd_offroad.json
│   │   │   │       ├── candidate_configuration_4runner_2020_trim_conflict.json
│   │   │   │       └── source_assertion_set_4runner_2020.json
│   │   │   ├── test_acquisition_adapters.py
│   │   │   ├── test_adjudication_workflow.py
│   │   │   ├── test_candidate_construction.py
│   │   │   ├── test_canonical_import.py
│   │   │   ├── test_canonical_import_execution.py
│   │   │   ├── test_ingestion_serialization.py
│   │   │   ├── test_manufacturer_ingestion.py
│   │   │   ├── test_models.py
│   │   │   ├── test_normalization.py
│   │   │   ├── test_production_manufacturer_acquisition.py
│   │   │   ├── test_toyota_extractor.py
│   │   │   └── test_views.py
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
├── storage/
│   └── raw_source_artifacts/
├── templates/
│   └── urls.py
├── docs/
│   ├── architecture/
│   │   ├── ADR/
│   │   └── designs/
│   ├── development/
│   │   └── DATA_PRESERVATION.md
│   ├── handbook/
│   └── implementation/
│       ├── CURRENT_STATE.md
│       └── tasks/
│           ├── RA-003-core-foundation.md
│           ├── RA-005-application-shell-ux-foundation.md
│           ├── RA-007-observation-domain-foundation.md
│           ├── RA-009-development-data-preservation-implementation.md
│           ├── RA-012-intermediate-serialization-implementation.md
│           ├── RA-013-public-source-acquisition-implementation.md
│           ├── RA-015-source-assertion-normalization-implementation.md
│           ├── RA-017-candidate-configuration-construction-aggregation-implementation.md
│           ├── RA-019-canonical-reference-import-planning-create-only-execution-implementation.md
│           ├── RA-021-manufacturer-specification-evidence-acquisition-normalization-implementation.md
│           ├── RA-023-production-manufacturer-artifact-acquisition-dry-run-orchestration-implementation.md
│           ├── RA-024-canonical-reference-import-execution-execution-provenance-workflow-implementation.md
│           └── RA-026-deterministic-toyota-extraction-review-adjudication-implementation.md
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
- Milestone 11: Source Assertion Normalization Implementation & Fixture Validation (✅ Complete — RA-015)
- Milestone 12: Candidate Configuration Construction & Aggregation Architecture (✅ Approved Architecture — RA-016)
- Milestone 13: Candidate Configuration Construction & Aggregation Implementation (✅ Complete — RA-017)
- Milestone 14: Canonical Reference Matching & Import Architecture (✅ Approved Architecture — RA-018 / ADR-0004)
- Milestone 15: Canonical Reference Import Planning & Create-Only Execution Implementation (✅ Complete — RA-019)
- Milestone 16: Trim/Grade & Market Applicability Source & Normalization Architecture (✅ Approved Architecture — RA-020 / ADR-0005)
- Milestone 17: Manufacturer Specification Evidence Acquisition & Normalization Implementation (✅ Complete — RA-021)
- Milestone 18: Production Manufacturer Evidence Acquisition & Orchestration Architecture (✅ Approved Architecture — RA-022 / RA-022A / ADR-0006)
- Milestone 19: Production Manufacturer Artifact Acquisition & Dry-Run Orchestration Implementation (✅ Complete — RA-023)
- Milestone 20: Canonical Reference Import Execution & Execution Provenance Workflow Architecture & Implementation (✅ Complete — RA-024 / ADR-0007)
- Milestone 21: Production Manufacturer Extraction & Review-Adjudication Architecture (✅ Approved Architecture — RA-025 / ADR-0008)
- Milestone 22: Deterministic Toyota Extraction & Review-Adjudication Implementation (✅ Complete — RA-026 / ADR-0008)

The next proposed operational follow-up is Controlled Toyota 4Runner Canonical Population.


13. Current Repository Status
The repository currently contains:
- Functional Django project
- Passing test suite (185 tests passing)
- Shared core infrastructure (`core` app with `UUIDModel`, `TimestampedModel`, `BaseModel`)
- Reference Data Ingestion package (`reference/ingestion/` with contracts, serialization, validation, `acquisition/` adapters & PDF strategies, `normalization/` normalizers, `candidate/` builder, `importing/` importer & planner, `manifest/` review manifest, and `orchestration/` orchestrator)
- Development data preservation tooling (`snapshot_db`, `export_dev_data`, `verify_dev_data`)
- Accessible application shell and UX foundation (`templates/base.html`, `about.html`, `404.html`, `500.html`)
- Observation Domain foundation (`observation` app with `Observation` model)
- Public reference browser
- Admin interface with read-only audit log viewer (`ImportExecutionReceiptAdmin`)
- Stable migration history (0001_initial, 0002_importexecutionreceipt, 0003_importexecutionreceipt_adjudication_hash)
- Populated Architectural Decision Records (ADR-0001 through ADR-0008)
- Approved Architecture Design Documents (RA-006, RA-008, RA-010, RA-011, RA-014, RA-016, RA-018, RA-020, RA-022, RA-024, RA-025)
- Gemini CLI project instructions (GEMINI.md)
- Task-based implementation workflow (docs/implementation/tasks/)
- Completed implementation tasks: RA-003, RA-005, RA-007, RA-009, RA-012, RA-013, RA-015, RA-017, RA-019, RA-021, RA-023, RA-024, RA-026 — Deterministic Toyota Extraction & Review-Adjudication Implementation
- Approved Architecture/Research tasks: RA-010, RA-011, RA-014, RA-016, RA-018, RA-020, RA-022, RA-024, RA-025