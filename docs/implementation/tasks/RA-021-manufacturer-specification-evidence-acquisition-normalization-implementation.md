# RA-021 — Manufacturer Specification Evidence Acquisition & Normalization Implementation

## Purpose

Implement the first manufacturer-origin evidence acquisition and normalization pipeline for factory grade/trim and commercial market applicability, converting authoritative manufacturer specification datasets into Tier 1 `SourceAssertionSet` artifacts with explicit `SourceApplicability` provenance metadata and normalizing them into Tier 2 `NormalizedInterpretation` arrays. This provides candidate configurations with the complete set of eight evidence-backed mapped attributes required for downstream [RA-019](file:///Users/esse/dev/Rigarchive/docs/implementation/tasks/RA-019-canonical-reference-import-planning-create-only-execution-implementation.md) canonical promotion planning (`plan_candidate_import`), in strict compliance with [RA-020](file:///Users/esse/dev/Rigarchive/docs/architecture/designs/RA-020-Trim-Grade-Market-Applicability-Source-Normalization-Architecture.md) and [ADR-0005](file:///Users/esse/dev/Rigarchive/docs/architecture/ADR/ADR-0005-Manufacturer-Grade-Taxonomy-Market-Applicability-Normalization.md).

## Governing Architecture

Governed by [ADR-0005 Manufacturer Grade Taxonomy & Market Applicability Normalization Strategy](file:///Users/esse/dev/Rigarchive/docs/architecture/ADR/ADR-0005-Manufacturer-Grade-Taxonomy-Market-Applicability-Normalization.md) and [RA-020 Trim/Grade & Market Applicability Source & Normalization Architecture](file:///Users/esse/dev/Rigarchive/docs/architecture/designs/RA-020-Trim-Grade-Market-Applicability-Source-Normalization-Architecture.md). Operates within the established ingestion contract and candidate building boundaries of [RA-016](file:///Users/esse/dev/Rigarchive/docs/architecture/designs/RA-016-Candidate-Configuration-Construction-Aggregation-Architecture.md), [RA-017](file:///Users/esse/dev/Rigarchive/docs/implementation/tasks/RA-017-candidate-configuration-construction-aggregation-implementation.md), [RA-018](file:///Users/esse/dev/Rigarchive/docs/architecture/designs/RA-018-Canonical-Reference-Matching-Import-Architecture.md), and [RA-019](file:///Users/esse/dev/Rigarchive/docs/implementation/tasks/RA-019-canonical-reference-import-planning-create-only-execution-implementation.md).

## Architecture & Implementation Pipeline

The manufacturer specification evidence acquisition and normalization pipeline follows:

```text
Authoritative Manufacturer Specification Evidence
    ↓
ManufacturerSpecificationAdapter
    ↓
SourceAssertionSet (1 set per native model code) + SourceApplicability
    ↓
ManufacturerNormalizer & toyota_rules.py
    ↓
NormalizedInterpretation (mapped trim & market)
    ↓
construct_candidate_configuration()
    ↓
CandidateConfigurationDocument (preserved-only trim & market)
    ↓
plan_candidate_import()
    ↓
ELIGIBLE / CREATE Canonical Import Plan
```

The milestone trust boundary ends at producing a valid canonical import plan (`plan_candidate_import`). Canonical execution (`execute_candidate_import`) is not required or performed.

## Implementation Details & File Summary

### 1. Ingestion Contracts & Provenance Metadata (`reference/ingestion/contracts.py`)

* **`SourceApplicability` Dataclass**:
  ```python
  @dataclass
  class SourceApplicability:
      market: Optional[str] = None
      applicability_basis: Optional[str] = None
      publisher_jurisdiction: Optional[str] = None
      unknown_fields: Dict[str, Any] = field(default_factory=dict)
  ```
* **`SourceMetadata` Field**: Added `source_applicability: Optional[SourceApplicability] = None`.
* **Semantic Boundary**: `target_context` represents caller/request acquisition context. `source_applicability` represents independently established applicability of the source artifact. They are strictly separate semantic concepts with no automatic defaulting or fallback between them.
* **Schema Backward Compatibility**: Schema version remains `"1.0.0"`. Under RA-011 SemVer rules, adding an optional metadata field to `SourceMetadata` is 100% backward-compatible. Existing payloads lacking the field deserialize cleanly as `source_applicability = None`. Existing `SourceMetadata` constructor calls use explicit keyword arguments and remain unaffected.

### 2. Serialization & Validation (`reference/ingestion/serialization.py` & `reference/ingestion/validation.py`)

* Implemented `source_applicability_to_dict` and `source_applicability_from_dict`.
* Updated `source_metadata_to_dict` and `source_metadata_from_dict` to serialize `source_applicability` deterministically.
* Implemented `validate_source_applicability` in `validation.py`, validating `market in {"US", "CA", "OT"}` and calling it inside `validate_source_assertion_set`.

### 3. Manufacturer Acquisition Adapter (`reference/ingestion/acquisition/manufacturer.py`)

* **`ManufacturerSpecificationAdapter(BaseSourceAdapter)`**: Generic acquisition adapter for structured manufacturer specification payloads.
* Accepts `source_id` as a parameter (default `"toyota_usa"`).
* Generates **one `SourceAssertionSet` per source-native configuration item** (`model_code`), attaching `provenance.native_record_id = model_code` and `source_applicability`.
* Emits raw assertions for `make_name`, `model_name`, `model_year`, `manufacturer_grade`, `model_code`, `drive_descriptor`, `engine_displacement_liters`, `engine_cylinders`, `transmission_descriptor`, and provenance-derived `market`.

### 4. Controlled Toyota Fixture (`reference/tests/fixtures/acquisition/toyota/2020_4runner_specs.json`)

* Manually structured derivative transcription of official first-party Toyota USA 2020 4Runner product press kit and technical specification matrix (`pressroom.toyota.com`).
* Contains 12 official Toyota US order model codes (`8664`, `8666`, `8670`, `8672`, `8674`, `8676`, `8682`, `8686`, `8688`, `8690`, `8692`, `8680`).
* Preserves complete publication provenance metadata in `_provenance`.

### 5. Toyota Rules & Manufacturer Normalizer (`reference/ingestion/normalization/`)

* **`toyota_rules.py`**: Provides exact uppercase dictionary lookup for Toyota factory grades (`SR5`, `SR5 Premium`, `TRD Off-Road`, `TRD Off-Road Premium`, `Venture Special Edition`, `Limited`, `Nightshade Special Edition`, `TRD Pro`).
* **Package Rejection**: Non-grade option/accessory packages (`XP PREDATOR`, `PREMIUM AUDIO`, `THIRD-ROW SEATING`) default safely to `mapping_status = "unmapped"`. Zero fuzzy or substring rules exist that could misclassify packages as grade/trim.
* **`ManufacturerNormalizer`**: Generic source normalizer (`source_id = "toyota_usa"`).
* **Source-Independence Test Enforcement**: Mapped `market` normalized interpretation (`"US"`) is emitted **ONLY** when `assertion_set.provenance.source_applicability.market` matches the market assertion. If `source_applicability` is missing (`None`), `market` remains unmapped.
* **Drivetrain Normalization**: `2WD` $\rightarrow$ `2WD`, `Part-Time 4WD` $\rightarrow$ `4WD` / `Part-time 4WD`, `Full-Time 4WD` $\rightarrow$ `AWD` / `Full-time 4WD` (following RA-014/RA-015 7-dimension drivetrain normalization).
* **Engine & Transmission**: Displacement (`4.0`) maps to `TechnicalValue(4.0, "L")`, cylinders map to `6`, transmission descriptor remains raw and unmapped.

### 6. Candidate Building & Preserved-Only Attributes

* Mapped `trim` and `market` normalized assertions are aggregated by `construct_candidate_configuration()` into `CandidateConfigurationDocument.normalized_assertions` as Category B preserved-only mapped concepts.
* `reference/ingestion/candidate/builder.py` required zero modifications.

### 7. Downstream Planning & Context Contradiction Correction (`reference/ingestion/importing/planner.py`)

* **Full Evidence Reachability**: Candidate configurations carrying mapped manufacturer evidence supply all eight required concepts (`make`, `model`, `model_year`, `generic_drive_classification`, `engine_displacement_liters`, `engine_cylinders`, `trim`, `market`), enabling `plan_candidate_import` to reach `ImportEligibilityStatus.ELIGIBLE` / `ImportPlannedAction.CREATE` / `ImportCreateBasis.FIRST_REPRESENTATION`.
* **Context Contradiction Protection**: Extended `planner.py` context verification to check `CandidateIdentity.trim_name` and `CandidateIdentity.market` against mapped evidence. Contradictions (e.g. `CandidateIdentity.trim_name = "Limited"` vs evidence `SR5`, or `CandidateIdentity.market = "CA"` vs evidence `US`) trigger `ImportEligibilityStatus.REQUIRES_REVIEW` / `ImportPlannedAction.FLAG_REVIEW`.

## Key Architectural Safety Guarantees

1. **Zero Cross-Source Joins**: Manufacturer evidence stands alone. Zero automated joins across Toyota, EPA, and NHTSA records.
2. **Cartesian Product Protection**: 12 model-code configuration rows generate exactly 12 candidate documents, preventing invalid Cartesian combinations.
3. **Zero Network Dependencies**: 100% offline execution utilizing local structured specification datasets.
4. **Zero Automated Writes**: Canonical promotion planning stops at producing an in-memory `CanonicalImportPlan`. Zero database writes are performed.

## Scope Restrictions (Explicit Non-Goals)

* Zero automated updating or deleting of canonical database records.
* Zero parent entity auto-creation.
* Zero live web scraping or unauthenticated HTTP requests.
* Zero cross-source fuzzy record matching.
* Zero modification of RA-011 schema version major contract (`schema_version` remains `"1.0.0"`).

## Completion Record

Status: Completed / Verified

Completion date: 2026-08-15

Files created:
- `reference/ingestion/acquisition/manufacturer.py`
- `reference/ingestion/normalization/manufacturer.py`
- `reference/ingestion/normalization/rules/toyota_rules.py`
- `reference/tests/fixtures/acquisition/toyota/2020_4runner_specs.json`
- `reference/tests/test_manufacturer_ingestion.py`
- `docs/implementation/tasks/RA-021-manufacturer-specification-evidence-acquisition-normalization-implementation.md`

Files modified:
- `reference/ingestion/contracts.py`
- `reference/ingestion/serialization.py`
- `reference/ingestion/validation.py`
- `reference/ingestion/acquisition/__init__.py`
- `reference/ingestion/normalization/__init__.py`
- `reference/ingestion/__init__.py`
- `reference/ingestion/importing/planner.py`
- `docs/implementation/CURRENT_STATE.md`
- `CHANGELOG.md`

Migrations created:
- None (0 ORM schema changes).

Verification results:
- `.venv/bin/python manage.py check`: Passed (`System check identified no issues (0 silenced)`).
- `.venv/bin/python manage.py makemigrations --check`: Passed (`No changes detected`).
- `.venv/bin/python manage.py test reference.tests.test_manufacturer_ingestion reference.tests.test_canonical_import`: Passed (`Ran 42 tests in 0.088s — OK`).
- `.venv/bin/python manage.py test`: Passed (`Ran 122 tests in 3.499s — OK`).
- `git diff --check`: Passed cleanly with exit code 0.
- `git status --short`: Verified clean state across all modified and newly created files.
