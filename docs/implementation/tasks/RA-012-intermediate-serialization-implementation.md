# RA-012 — Intermediate Serialization Contract Implementation & Fixture Validation

## Purpose

Implement the executable Python intermediate serialization contracts, validation logic, deterministic JSON round-trip utilities, and controlled test fixtures for the approved RA-011 architecture without creating persistent Django database models, database migrations, or live acquisition network clients.

## Governing Architecture

Governed by the approved [RA-011 Architecture Document](file:///Users/esse/dev/Rigarchive/docs/architecture/designs/RA-011-Ingestion-Schema-Intermediate-Serialization-Design.md) and [RA-010 Source Mapping Architecture](file:///Users/esse/dev/Rigarchive/docs/architecture/designs/RA-010-Reference-Ingestion-Source-Mapping-Architecture.md).

## Implementation Design & Module Placement

The Python implementation is organized as a pure Python package under `reference/ingestion/` associated with the Reference domain:

```text
reference/ingestion/
├── __init__.py         # Package public API exports
├── contracts.py        # Pure Python dataclasses for Tier 1 & Tier 2 payloads
├── serialization.py    # Deterministic JSON round-trip serializer/deserializer & unknown-field preservation
└── validation.py       # Structural, envelope, assertion reference, and reconciliation contract validator
```

* **Module Ownership Rationale**: Placed in `reference/ingestion/` as domain application infrastructure associated with Reference Data Ingestion. No Django ORM models, persistent staging database tables, or migrations are created.
* **Dependencies**: Uses strictly the Python standard library (`dataclasses`, `enum`, `typing`, `json`, `re`, `datetime`, `pathlib`). Zero third-party dependencies added.
* **Test Fixture Location**: Controlled test fixtures live in `reference/tests/fixtures/ingestion/` as test-owned fixture data.

## Scope

### Included
* Implement dataclass contracts (`Envelope`, `SourceMetadata`, `SourceAssertion`, `SourceAssertionSet`, `NormalizedInterpretation`, `CandidateIdentity`, `SourceConfigurationIdentity`, `TechnicalValue`, `EngineDetails`, `TransmissionDetails`, `DrivetrainComponent`, `DrivetrainMode`, `DrivetrainDetails`, `NormalizedTechnicalDetails`, `FactoryTechnicalFeature`, `PackageOrOption`, `AttributeReconciliationState`, `ReconciliationAndReview`, `SemanticMissingValue`, `CandidateConfigurationDocument`).
* Implement deterministic JSON serialization and deserialization with UTF-8 encoding, 2-space indentation, ISO-8601 UTC timestamps, and deterministic key sorting (`serialize_artifact`, `deserialize_artifact`).
* Implement unknown-field preservation during parsing so unmodeled JSON fields in minor additive schema versions are retained in `unknown_fields` containers and preserved losslessly during round-trip serialization.
* Implement contract validation (`validate_artifact`, `validate_envelope`, `validate_source_assertion_set`, `validate_candidate_configuration`, `validate_semantic_missing_value`, `IngestionValidationError`).
* Create 4 controlled test fixture files in `reference/tests/fixtures/ingestion/`:
  1. `source_assertion_set_4runner_2020.json`
  2. `candidate_configuration_4runner_2020_trd_offroad.json`
  3. `candidate_configuration_4runner_2020_trim_conflict.json`
  4. `candidate_configuration_4runner_2010_i4_2wd.json`
* Implement 16 automated test methods in `reference/tests/test_ingestion_serialization.py` covering envelope validation, Tier 1 payload serialization, assertion uniqueness, broken reference detection, 7-dimension drivetrain representation, unresolved KDSS feature preservation, separated reconciliation/review states, semantic missing values, technical value units, forward-compatible unknown field round-trips, and fixture contract validation.
* Update `docs/implementation/CURRENT_STATE.md` and `CHANGELOG.md`.

### Not Included
* Live external data acquisition, scrapers, HTTP clients, or REST API calls (NHTSA, EPA, Toyota USA, J.D. Power).
* Importing candidate configurations into canonical `VehicleDefinition` records.
* Modifying existing Django Reference models or database tables.
* Creating Django ORM staging models or migrations.
* Establishing the canonical import matching key or deduplication algorithm.
* Establishing production ingestion storage directories on disk.

## Completion Record

Status: Completed

Completion date: 2026-08-15

Files created:
- `reference/ingestion/__init__.py`
- `reference/ingestion/contracts.py`
- `reference/ingestion/serialization.py`
- `reference/ingestion/validation.py`
- `reference/tests/fixtures/ingestion/source_assertion_set_4runner_2020.json`
- `reference/tests/fixtures/ingestion/candidate_configuration_4runner_2020_trd_offroad.json`
- `reference/tests/fixtures/ingestion/candidate_configuration_4runner_2020_trim_conflict.json`
- `reference/tests/fixtures/ingestion/candidate_configuration_4runner_2010_i4_2wd.json`
- `reference/tests/test_ingestion_serialization.py`
- `docs/implementation/tasks/RA-012-intermediate-serialization-implementation.md`

Files modified:
- `docs/implementation/CURRENT_STATE.md`
- `CHANGELOG.md`

Migrations created:
- None (ingestion contract implementation uses pure Python data structures without Django ORM models).

Verification results:
- `.venv/bin/python manage.py check`: Passed (`System check identified no issues (0 silenced)`).
- `.venv/bin/python manage.py makemigrations --check`: Passed (`No changes detected`).
- `.venv/bin/python manage.py test`: Passed (`Ran 50 tests in 3.386s — OK`).
- `git diff --check`: Passed cleanly with exit code 0.
- `git status --short`: Verified clean status on pre-existing tracked files.
