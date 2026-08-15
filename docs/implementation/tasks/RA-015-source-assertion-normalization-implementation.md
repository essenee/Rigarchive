# RA-015 — Source Assertion Normalization Implementation & Fixture Validation

## Purpose

Implement the initial controlled pure Python source assertion normalization layer for NHTSA vPIC and EPA FuelEconomy.gov assertions, converting Tier 1 `SourceAssertionSet` artifacts into valid `NormalizedInterpretation` objects strictly adhering to the 12 Category C mappings authorized by RA-014 while preserving provenance, semantic qualifiers, unmapped handling, and 100% offline deterministic verification.

## Governing Architecture

Governed by the approved [RA-014 Source Assertion Normalization & Mapping Architecture](file:///Users/esse/dev/Rigarchive/docs/architecture/designs/RA-014-Source-Assertion-Normalization-Mapping-Architecture.md) and operating over [RA-012 Intermediate Serialization Contracts](file:///Users/esse/dev/Rigarchive/docs/implementation/tasks/RA-012-intermediate-serialization-implementation.md) and [RA-013 Public Source Acquisition Adapters](file:///Users/esse/dev/Rigarchive/docs/implementation/tasks/RA-013-public-source-acquisition-implementation.md).

## Implementation Design & Module Placement

The Python normalization package is organized under `reference/ingestion/normalization/`:

```text
reference/ingestion/normalization/
├── __init__.py         # Package exports (normalize_source_assertions, BaseSourceNormalizer, etc.)
├── base.py             # BaseSourceNormalizer ABC, exception hierarchy, registry, and top-level dispatch
├── nhtsa.py            # NHTSANormalizer implementation for source_id "nhtsa_vpic"
├── epa.py              # EPANormalizer implementation for source_id "epa_fueleconomy"
└── rules/              # Declarative repository-versioned mapping definitions
    ├── __init__.py
    ├── nhtsa_rules.py  # Declarative Category C mapping rules for NHTSA
    └── epa_rules.py    # Declarative Category C mapping rules for EPA
```

* **Shared Normalization Abstraction**: `BaseSourceNormalizer` abstract base class defining `source_id` property and `normalize(assertion_set)` method. Registered normalizers are dispatched dynamically by `source_id` via top-level function `normalize_source_assertions(assertion_set)`. Unregistered sources raise `UnsupportedSourceError`.
* **Zero Custom DSL / Zero Dynamic Code Execution**: Mapping rules are expressed as clean, declarative Python data structures (`MappingRule`). Zero dynamic code evaluation (`eval`, `exec`), dynamic imports, or external rules engines used.
* **RA-012 Contract Invariance**: Consumes `SourceAssertionSet` and emits `NormalizedInterpretation` arrays. Uses existing RA-012 contract fields without modifying `contracts.py`, `serialization.py`, or `validation.py`. Rule IDs and transformation methods are cleanly preserved in `normalization_notes` and `unknown_fields`.

## Implemented Category C Mapping Matrix (12 Mappings)

### NHTSA Mappings (4 Mappings)
1. `make_id` → `target_attribute_key: "nhtsa_make_id"` (`direct_copy`, `rule_id: "nhtsa.make_id.direct"`). Preserved source-native identifier context.
2. `make_name` → `target_attribute_key: "make"` (`direct_copy`, `rule_id: "nhtsa.make_name.direct"`). Direct copy of raw text `"Toyota"`.
3. `model_id` → `target_attribute_key: "nhtsa_model_id"` (`direct_copy`, `rule_id: "nhtsa.model_id.direct"`). Preserved source-native identifier context.
4. `model_name` → `target_attribute_key: "model"` (`direct_copy`, `rule_id: "nhtsa.model_name.direct"`). Direct copy of raw text `"4Runner"`.

### EPA Mappings (8 Category C Mappings across 7 Assertion Keys)
5. `model_year` → `target_attribute_key: "model_year"` (`parsed`, `rule_id: "epa.model_year.parse_integer"`). Type-safe integer parsing (`"2020"` → `2020`).
6. `make` → `target_attribute_key: "make"` (`direct_copy`, `rule_id: "epa.make.direct"`). Direct copy of raw text `"Toyota"`.
7. `drive_descriptor` (`"Part-time 4WD"`) → `target_attribute_key: "generic_drive_classification"` (`exact_mapping`, `rule_id: "epa.drive.part_time_4wd.classification"`). Normalized value `"4WD"`.
8. `drive_descriptor` (`"Part-time 4WD"`) → `target_attribute_key: "drivetrain_architecture"` (`interpreted`, `rule_id: "epa.drive.part_time_4wd.architecture"`). Normalized value `"part_time_4wd"`. Demonstrates 1 source assertion → 2 normalized interpretations sharing `source_assertion_ref`.
9. `engine_displacement_liters` → `target_attribute_key: "engine_displacement_liters"` (`parsed`, `rule_id: "epa.displ.parse_technical_value"`). Parsed structured `TechnicalValue(normalized_value=4.0, normalized_unit="L", raw_source_string="4.0")`.
10. `engine_cylinders` → `target_attribute_key: "engine_cylinders"` (`parsed`, `rule_id: "epa.cyl.parse_integer"`). Type-safe integer parsing (`"6"` → `6`).
11. `city_mpg_epa_rating` → `target_attribute_key: "city_mpg_epa_rating"` (`parsed`, `rule_id: "epa.city_mpg.parse_integer"`). Type-safe integer parsing (`"16"` → `16`). Retains `_epa_rating` semantic qualifier.
12. `highway_mpg_epa_rating` → `target_attribute_key: "highway_mpg_epa_rating"` (`parsed`, `rule_id: "epa.hwy_mpg.parse_integer"`). Type-safe integer parsing (`"19"` → `19`). Retains `_epa_rating` semantic qualifier.

## Unmapped & Error Handling

* **Case A (Target Concept Known, Mapping Deferred or Unmapped Value)**:
  * Category B EPA assertions emitted by RA-013 (`model`, `transmission_descriptor`, `vehicle_class`, `engine_description`) or unknown drive terms (e.g. `"Quad-Drive"`) emit `NormalizedInterpretation` objects preserving `target_attribute_key`, `mapping_status: "unmapped"`, `normalized_concept: None`, and `raw_source_value`, with explanatory `normalization_notes`.
* **Case B (Target Concept Unknown)**:
  * When the normalized target concept is unknown, no `NormalizedInterpretation` is emitted. The original Tier 1 `SourceAssertion` remains preserved in the `SourceAssertionSet` until a future approved mapping establishes normalized meaning. Zero synthetic target keys (such as `unclassified_source_attribute`) are manufactured.

* **Parsing Failures**:
  * Invalid integer/float representations (e.g. `model_year: "invalid"`) result in `mapping_status: "unmapped"` and `normalized_concept: None` without crashing or inventing numbers.
* **Unsupported Sources**:
  * Input assertion sets with unrecognized `source_id` raise `UnsupportedSourceError`.

## Scope Restrictions (Explicit Non-Goals)

* Zero Category B production mappings implemented.
* Zero CandidateConfigurationDocument objects generated.
* Zero candidate aggregation, grouping, or cross-source reconciliation.
* Zero source precedence rules or canonical matching/import.
* Zero Django ORM models modified or migrations created.
* Zero live network requests or acquisition adapter modifications.

## Completion Record

Status: Completed

Completion date: 2026-08-15

Files created:
- `reference/ingestion/normalization/__init__.py`
- `reference/ingestion/normalization/base.py`
- `reference/ingestion/normalization/nhtsa.py`
- `reference/ingestion/normalization/epa.py`
- `reference/ingestion/normalization/rules/__init__.py`
- `reference/ingestion/normalization/rules/nhtsa_rules.py`
- `reference/ingestion/normalization/rules/epa_rules.py`
- `reference/tests/test_normalization.py`
- `docs/implementation/tasks/RA-015-source-assertion-normalization-implementation.md`

Files modified:
- `reference/ingestion/__init__.py`
- `docs/implementation/CURRENT_STATE.md`
- `CHANGELOG.md`

Migrations created:
- None (0 ORM changes).

Verification results:
- `.venv/bin/python manage.py check`: Passed (`System check identified no issues (0 silenced)`).
- `.venv/bin/python manage.py makemigrations --check`: Passed (`No changes detected`).
- `.venv/bin/python manage.py test`: Passed (`Ran 67 tests in 3.374s — OK`).
- `git diff --check`: Passed cleanly with exit code 0.
- `git status --short`: Verified clean state across all modified and newly created files.
