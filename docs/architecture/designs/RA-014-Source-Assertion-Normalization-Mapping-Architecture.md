# RA-014 — Source Assertion Normalization & Mapping Architecture

**Status**: Accepted  
**Date**: 2026-08-15  
**Domain**: Reference Domain — Data Ingestion Pipeline  

---

## 1. Executive Summary

RA-014 establishes the architectural design for transforming raw, source-specific Tier 1 assertions (`SourceAssertionSet`) into explicit normalized interpretations (`NormalizedInterpretation`). 

This architecture bridges raw acquired source payloads (RA-013) with normalized technical concepts (RA-011) without prematurely declaring source mappings as canonical database facts, manufacturing unsupported technical detail, or collapsing source-specific nuances into rigid ORM structures.

## 2. Purpose

The purpose of RA-014 is to define how RigArchive safely, deterministically, and reproducibly transforms source-native assertions into explicit normalized interpretations while:
* preserving source meaning, provenance, ambiguity, specificity, and unresolved terminology;
* adhering strictly to evidence-bounded normalization (preventing the fabrication of unsupported drivetrain modes, ratios, lock states, or capabilities);
* maintaining source-specific normalization boundaries so that NHTSA and EPA logic remain isolated;
* preparing normalized assertions for downstream candidate construction (RA-015+) and cross-source reconciliation without making early canonical database commitments.

## 3. Scope

### Included in RA-014 Architectural Design
* Partitioning normalization logic by source behind a common normalization contract.
* Defining the normalized concept identity strategy and normalized value representations.
* Taxonomizing transformation methods (`direct_copy`, `exact_mapping`, `parsed`, `converted`, `interpreted`, `unmapped`).
* Establishing mapping-rule identity, rule representation, and provenance boundaries.
* Preserving normalization provenance, source assertion traceability, and applicability context.
* Handling unknown source values, unmapped concepts, and controlled vocabulary evolution safely.
* Mapping source assertions into the 7-dimension drivetrain contract and `factory_technical_features`.
* Preserving manufacturer taxonomy rules for trim, grade, sub-grade, package, and option normalization.
* Defining human-review, cross-source reconciliation, and candidate-construction boundaries.
* Repository-versioned mapping storage direction and contract validation integration.
* Defining the Category C mappings authorized for RA-015 implementation.

### Excluded from RA-014 (Non-Goals)
* Implementing normalization Python modules or mapping rule files.
* Modifying RA-012 contracts or RA-013 acquisition adapters.
* Constructing `CandidateConfigurationDocument` artifacts or grouping candidate attributes.
* Cross-source reconciliation, conflict resolution, or source precedence logic.
* Canonical Reference matching, deduplication, or `VehicleDefinition` writes.
* Django ORM staging models, migrations, or database schema changes.
* Production ingestion persistence directory decisions or background job scheduling.

## 4. Governing Architecture

Governed by the approved [RA-010 Source Mapping Architecture](file:///Users/esse/dev/Rigarchive/docs/architecture/designs/RA-010-Reference-Ingestion-Source-Mapping-Architecture.md) and [RA-011 Ingestion Serialization Architecture](file:///Users/esse/dev/Rigarchive/docs/architecture/designs/RA-011-Ingestion-Schema-Intermediate-Serialization-Design.md), and operating over the executable [RA-012 Intermediate Serialization Implementation](file:///Users/esse/dev/Rigarchive/docs/implementation/tasks/RA-012-intermediate-serialization-implementation.md) and [RA-013 Public Source Acquisition Adapters](file:///Users/esse/dev/Rigarchive/docs/implementation/tasks/RA-013-public-source-acquisition-implementation.md).

## 5. Relationship to Prior Milestones (RA-010 through RA-013)

* **RA-010 (Source Mapping Architecture)**: Established foundational principles (7 drivetrain dimensions, manufacturer-taxonomy trim rules, non-lossy normalization).
* **RA-011 (Ingestion Serialization Design)**: Defined the logical contract for `NormalizedInterpretation` (`interpretation_id`, `source_assertion_ref`, `target_attribute_key`, `normalized_concept`, `raw_source_value`, `manufacturer_term`, `mapping_status`, `normalization_notes`).
* **RA-012 (Intermediate Serialization Implementation)**: Provided pure Python dataclasses and contract validators (`validate_artifact`) in `reference/ingestion/`.
* **RA-013 (Public Source Acquisition Adapters)**: Implemented acquisition adapters (`NHTSAAdapter`, `EPAAdapter`) emitting real Tier 1 `SourceAssertionSet` objects.

## 6. Repository & Current Implementation Findings

* **Executable Code Base**: RA-012 serialization contracts (`reference/ingestion/contracts.py`) and RA-013 acquisition adapters (`reference/ingestion/acquisition/`) are clean, fully tested, and passing all unit tests offline.
* **Currently Emitted RA-013 Assertion Keys (15 total keys)**:
  * **NHTSA vPIC (`nhtsa_vpic`)**: `make_id`, `make_name`, `model_id`, `model_name`.
  * **EPA FuelEconomy.gov (`epa_fueleconomy`)**: `model_year`, `make`, `model`, `drive_descriptor`, `engine_displacement_liters`, `engine_cylinders`, `transmission_descriptor`, `vehicle_class`, `engine_description`, `city_mpg_epa_rating`, `highway_mpg_epa_rating`.
* **EPA MPG Semantic Labels**: `city08` and `highway08` emit Tier 1 keys `city_mpg_epa_rating` and `highway_mpg_epa_rating` respectively. The qualifier `_epa_rating` explicitly preserves source metric meaning rather than broadening it into generic `city_mpg` / `highway_mpg`.
* **NHTSA Model ID Finding**: The controlled offline test fixture `get_models_toyota_2020.json` contains `"Model_ID": 11982`, whereas the recorded live smoke test returned `"Model_ID": 2216`. RA-014 does not establish the cause of this discrepancy; the controlled fixture value (`11982`) governs deterministic offline testing.

## 7. Normalization Principles

1. **Normalize Only What Evidence Supports**: Preserve what the source actually asserted.
2. **Provenance Over Convenience**: Every normalized interpretation must maintain explicit traceability back to its originating `source_assertion_ref` (`assertion_id`).
3. **Explicit Interpretation Over Hidden Inference**: Mappings explicitly record how a normalized value was derived (`transformation_method`) rather than silently mutating strings.
4. **Source-Specific Normalization**: Mapping rules are partitioned by source. NHTSA logic does not bleed into EPA logic or generic system code.
5. **Partial Knowledge Is Valid**: A source assertion providing generic 4WD classification does NOT require populating transfer case gear ratios or locking differential states.
6. **Preserve Unknowns Without Pseudonormalization**: Unrecognized source terms produce explicit `mapping_status: "unmapped"` interpretations without fabricating normalized values or treating raw source keys as normalized concept keys.
7. **No Overwriting**: Normalization does NOT overwrite other assertions. Each interpretation survives independently with its own applicability metadata. Downstream reconciliation evaluates competing assertions.
8. **Normalization Is Not Canonical Import**: A normalized assertion reflects RigArchive's interpretation of a specific source assertion, NOT a finalized database fact.

## 8. Evidence-Bounded Normalization Rule

> **Evidence-Bounded Normalization Rule**: Normalization may ONLY add semantic specificity that is supported by the source assertion plus an explicitly justified mapping rule. It must NOT manufacture drivetrain operating modes, transfer-case gear ratios, differential lock states, system capabilities, taxonomy, units, or ratings merely because those details are commonly associated with the source term.

## 9. Normalization Pipeline Boundary

RA-014 governs strictly the **Normalization / Interpretation** phase of the ingestion pipeline:

```text
External Source
    ↓
Acquisition Adapters (RA-013)
    ↓
Tier 1 SourceAssertionSet
    ↓
[RA-014 NORMALIZATION BOUNDARY]
    Source-Specific Normalizers (NHTSA / EPA)
        ↓
    Mapping Rules & Parsers
        ↓
    Array of NormalizedInterpretation Objects
[STOP FOR RA-014]
    ↓
Candidate Configuration Construction (RA-015+)
    ↓
Cross-Source Reconciliation & Human Review
    ↓
Canonical Reference Import
```

Normalization operates strictly on a single `SourceAssertionSet` at a time. It does NOT merge multiple source assertion sets, evaluate cross-source authority, or persist records into `db.sqlite3`.

## 10. Source-Specific Normalization Ownership

Normalization logic is partitioned by source behind a shared normalization contract. Each source owns its source-specific interpretation and mapping behavior.

For illustrative future implementation purposes, package organization may be placed under `reference/ingestion/normalization/`:
```text
reference/ingestion/normalization/   (Recommended RA-015 Package Structure)
├── __init__.py
├── base.py             # Common normalizer interface/protocol
├── nhtsa.py            # NHTSA normalizer implementation
├── epa.py              # EPA normalizer implementation
└── rules/              # Repository-versioned mapping declarations
    ├── __init__.py
    ├── nhtsa_rules.py  # NHTSA mapping declarations
    └── epa_rules.py    # EPA mapping declarations
```
The exact Python abstraction (ABC, Protocol, composition, functional interface) is an RA-015 implementation decision.

## 11. Shared Normalization Contract

All source normalizers accept a validated `SourceAssertionSet` and return a list of `NormalizedInterpretation` objects conforming to the RA-012 contract.

## 12. Initial / Provisional Normalized Concept-Key Strategy

### Concept Naming & Identity Strategy
* Attribute keys (`target_attribute_key`) use stable, lower_snake_case strings representing domain concepts.
* Concept keys are domain-oriented and decoupled from Django ORM field names.
* Vocabulary expansion is organic and provisional. RA-014 approves the naming strategy, not an exhaustive frozen ontology.

### Current Proposed Normalization Concept Set
* **Identity & Context**: `make`, `model`, `model_year`, `market`, `trim_grade`, `sub_grade`, `vehicle_class`
* **Powertrain — Engine**: `engine_displacement_liters`, `engine_cylinders`, `engine_configuration`, `fuel_type`, `fuel_induction`
* **Powertrain — Transmission**: `transmission_type`, `transmission_speeds`, `transmission_descriptor`
* **Powertrain — Performance**: `city_mpg_epa_rating`, `highway_mpg_epa_rating`
* **Drivetrain — 7 Dimensions**: `generic_drive_classification`, `drivetrain_architecture`, `drivetrain_components`, `drivetrain_operating_modes`, `drivetrain_mode_states`, `drivetrain_capabilities`, `manufacturer_drivetrain_term`
* **Unclassified Features**: `factory_technical_feature`, `unclassified_source_attribute`, `nhtsa_make_id`, `nhtsa_model_id`

## 13. Normalized Value Representation

Normalized values (`normalized_concept`) support structured representations appropriate for the concept type:

1. **Scalar Concepts**: Primitive strings, integers, or floats (e.g. `2020`, `4.0`, `"Toyota"`).
2. **Controlled Vocabulary Concepts**: Standardized system tokens (e.g. `generic_drive_classification: "4WD"`).
3. **Structured Technical Values**: `TechnicalValue` objects containing `normalized_value`, `normalized_unit`, and `raw_source_string` (e.g. `normalized_value: 4.0`, `normalized_unit: "L"`, `raw_source_string: "4.0"`).
4. **Complex Drivetrain Details**: Structured dicts matching RA-011 7-dimension drivetrain sub-contracts.
5. **Semantic Missing Values**: `SemanticMissingValue` objects (`"not_supplied_by_source"`, `"unresolved_conflict"`).

## 14. Transformation Methods Taxonomy

Every `NormalizedInterpretation` indicates how the source value was derived:

| Transformation Method | Description | Example |
| :--- | :--- | :--- |
| `direct_copy` | Literal scalar transfer from source assertion without alteration. | `model_year: "2020"` → `2020` |
| `exact_mapping` | Controlled vocabulary lookup from source term to system concept. | EPA `"Part-time 4WD"` → `generic_drive_classification: "4WD"` |
| `parsed` | Structural string decomposition into typed value and unit. | `"4.0"` → `value: 4.0, unit: "L"` |
| `converted` | Deterministic unit conversion (retaining raw string provenance). | `"244 cu in"` → `value: 4.0, unit: "L"` |
| `interpreted` | Domain inference supported by empirical research and source evidence. | EPA `"Part-time 4WD"` → `drivetrain_architecture: "part_time_4wd"` |
| `unmapped` | Source value unknown to current mapping rules; raw value preserved. | Unrecognized drive term → `mapping_status: "unmapped"` |

## 15. Mapping-Rule Architecture & Identity

Mapping rules are expressed as pure Python data structures in repository-versioned rule files. Each rule specifies:
* `rule_id`: Stable human-readable string identifier (e.g. `"epa.drive.part_time_4wd"`).
* `source_id`: Source identifier (`"nhtsa_vpic"`, `"epa_fueleconomy"`).
* `source_attribute_key`: Originating raw attribute key.
* `raw_value_pattern`: Value match pattern.
* `target_attribute_key`: Target normalized concept key.
* `normalized_concept`: Derived normalized value or structure.
* `transformation_method`: Taxonomy classification.

Rule evolution is tracked via Git repository history without requiring redundant internal SemVer fields (`rule_version`).

## 16. Mapping-Rule Identity and Evolution

Rule IDs are recorded in `normalization_notes` or rule metadata for auditability, debugging, and fixture testing. They do NOT serve as canonical vehicle identities.

## 17. Normalization Provenance

Every normalized interpretation maintains explicit traceability to its source assertion via `source_assertion_ref`.
* **One Source Assertion → Multiple Interpretations**: Supported by RA-012. A single source assertion (e.g. EPA `trany: "Automatic 5-spd"`) generates two distinct `NormalizedInterpretation` objects sharing `source_assertion_ref: "ast_epa_trans_01"`.
* **Multiple Source Assertions → Single Interpretation**: Deferred until a validated use case requires extending `source_assertion_ref` into an array or adding `supporting_assertion_refs`.

## 18. Applicability and Specificity

Normalized interpretations record their applicability context (`market`, `model_year`, `trim_grade`). Specificity metadata allows downstream candidate construction and reconciliation to distinguish broad model assertions from configuration-specific assertions. Normalization does NOT overwrite broader or narrower interpretations.

## 19. Redesigned Unmapped / Unknown Values Handling

The architecture distinguishes two explicit cases for unmapped data:

### Case A — Target Concept Known, Value Unmapped
The system recognizes that the source attribute represents a known concept (e.g. `generic_drive_classification`), but encounters an unrecognized value (e.g. `"Quad-Drive"`).
* `target_attribute_key`: `"generic_drive_classification"`
* `normalized_concept`: `None`
* `raw_source_value`: `"Quad-Drive"`
* `mapping_status`: `"unmapped"`
* `normalization_notes`: `"Unmapped value for generic_drive_classification"`

### Case B — Target Concept Itself Unknown
The system encounters a source attribute key not recognized by the normalizer.
* Tier 1 assertion is fully preserved in `SourceAssertionSet`.
* Normalizer emits `target_attribute_key: "unclassified_source_attribute"`, `mapping_status: "unmapped"`, `raw_source_value: <raw_value>`. It does NOT pretend the raw source attribute key is a normalized concept key.

## 20. Ambiguous Interpretations

When a source value supports multiple plausible normalized concepts or cannot be mapped deterministically, the normalizer sets `mapping_status: "requires_review"` with explanatory `normalization_notes`.

## 21. Controlled Vocabulary Evolution

Controlled vocabularies expand organically. Unknown values produce explicit `mapping_status: "unmapped"` assertions, allowing new source terms to be reviewed and mapped in future repository updates without pipeline failure.

## 22. Semantic Qualifier Preservation Rule

> **Semantic Qualifier Preservation Rule**: Normalization must NOT remove a technically meaningful source qualifier unless the target concept is explicitly defined as equivalent.

For FuelEconomy.gov `city08` and `highway08`:
* `city08` → Tier 1 `city_mpg_epa_rating` → Normalized `city_mpg_epa_rating`
* `highway08` → Tier 1 `highway_mpg_epa_rating` → Normalized `highway_mpg_epa_rating`

The qualifier `epa_rating` is preserved to retain exact metric meaning rather than broadening it into generic `city_mpg` / `highway_mpg`.

## 23. Drivetrain Normalization Boundary (7 Dimensions)

Normalization maps source drive descriptions against the 7 RA-010/RA-011 drivetrain dimensions strictly according to evidence:

1. **Generic Classification**: EPA `"Part-time 4WD"` → `generic_drive_classification: "4WD"` (Category C: Empirically Validated).
2. **Architecture**: EPA `"Part-time 4WD"` → `drivetrain_architecture: "part_time_4wd"` (Category C: Empirically Validated).
3. **Physical Components**: Unpopulated unless explicitly asserted (transfer case model, locking differential).
4. **Operating Modes**: Unpopulated (`None` / missing) for `"Part-time 4WD"` alone. Specific operating modes (`2H`, `4H`, `4L`) require separate OEM/empirical evidence.
5. **Mode-Specific States**: Internal mechanical states (e.g. `center_diff_locked`, `low_range_engaged`). Actuation controls (manual floor lever vs electronic dash dial) are interface/actuation details, not mode states.
6. **Capabilities**: System capabilities (e.g. low-range capability, center-differential locking capability, rear-differential locking capability, selectable two-wheel-drive capability) populated only where separately supported by evidence.
7. **Manufacturer Terminology**: Preserves original OEM marketing names (e.g. `"Multi-Mode 4WD"`).

## 24. Manufacturer Terminology

Original OEM marketing terms (e.g. `"Multi-Mode 4WD"`, `"Full-Time 4WD"`) are preserved in `manufacturer_term` alongside normalized concepts.

## 25. Factory Technical Features

A-TRAC, CRAWL Control, MTS, KDSS, X-REAS, active suspension systems, and similar source-identified technical features map to `target_attribute_key: "factory_technical_feature"` with `normalized_classification_status: "unresolved"`. They are NOT used as resolved examples of drivetrain capabilities, option packages, or suspension ORM models without validated evidence.

## 26. Trim / Grade / Package / Option Handling

Enforces the RA-010 **Manufacturer-Taxonomy Rule**:
* Composite source strings (e.g. EPA `model: "4Runner 4WD"`) are processed in multiple stages:
  1. Decompose string into `model_component = "4Runner"` and `suffix_component = "4WD"`.
  2. Map `model_component` → `model: "4Runner"`.
  3. Map `suffix_component` → `generic_drive_classification: "4WD"`.
* Source strings do NOT automatically establish manufacturer trim identities. Trim/grade classification remains `unresolved` until manufacturer taxonomy rules match the string.
* Sub-grades (e.g. "TRD Off-Road Premium") are preserved as distinct grade identities and are not collapsed into base "TRD Off-Road".

## 27. Technical Numeric Values and Units

Numeric technical values (displacement, fuel economy) map to structured `TechnicalValue` objects (`normalized_value`, `normalized_unit`, `raw_source_string`). Parsing retains unit precision (`"4.0"` → `4.0`, `"L"`).

## 28. Human Review Boundary

Normalization sets `mapping_status: "requires_review"` for ambiguous source values or unrecognized terms. Normalization review is strictly separated from cross-source reconciliation review.

## 29. Cross-Source Reconciliation Boundary

Normalizers operate strictly per-source. The EPA normalizer does NOT inspect NHTSA assertions, resolve conflicts between sources, or enforce cross-source precedence rules. Cross-source conflict resolution is deferred entirely to reconciliation.

## 30. Candidate Construction Boundary

Normalization outputs `NormalizedInterpretation` arrays. Grouping normalized assertions into candidate real-world configurations (`CandidateConfigurationDocument`) belongs to candidate construction (RA-015+), not normalization.

## 31. Current NHTSA Assertion Analysis

NHTSA vPIC emits 4 assertion keys (`make_id`, `make_name`, `model_id`, `model_name`). `make_name` and `model_name` map directly to normalized `make` and `model`. `make_id` and `model_id` are preserved source-native identifiers.

## 32. Current EPA Assertion Analysis

EPA FuelEconomy.gov emits 11 assertion keys (`model_year`, `make`, `model`, `drive_descriptor`, `engine_displacement_liters`, `engine_cylinders`, `transmission_descriptor`, `vehicle_class`, `engine_description`, `city_mpg_epa_rating`, `highway_mpg_epa_rating`).

## 33. Fifth-Generation 4Runner Stress Test

Validates mapping rules against 2010, 2015, 2020, and 2024 4Runner research:
* 2010 2.7L I4 belongs to 4x2 SR5 ONLY (not an I4/4WD configuration).
* Manufacturer-recognized TRD Off-Road Premium sub-grade is preserved as a distinct grade identity.
* 40th Anniversary Special Edition belongs to 2023, not 2024.

## 34. Current-Source Mapping Matrix

| Source | Raw Assertion Key | Sample Raw Value | Proposed Target Concept | Transformation Method | Proposed Normalized Value | Evidentiary Basis | Approval Category |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **NHTSA** | `make_id` | `448` | `nhtsa_make_id` | `direct_copy` | `448` | Direct preservation of source-native integer ID for source context. | **Category C — Empirically Validated** |
| **NHTSA** | `make_name` | `"Toyota"` | `make` | `direct_copy` | `"Toyota"` | Direct preservation of explicit source text matching approved manufacturer name. | **Category C — Empirically Validated** |
| **NHTSA** | `model_id` | `11982` | `nhtsa_model_id` | `direct_copy` | `11982` | Direct preservation of source-native integer ID for source context. | **Category C — Empirically Validated** |
| **NHTSA** | `model_name` | `"4Runner"` | `model` | `direct_copy` | `"4Runner"` | Direct preservation of explicit source text matching approved model name. | **Category C — Empirically Validated** |
| **EPA** | `model_year` | `"2020"` | `model_year` | `parsed` | `2020` (integer) | Type-safe integer parsing of explicitly designated model year source string (`year`). | **Category C — Empirically Validated** |
| **EPA** | `make` | `"Toyota"` | `make` | `direct_copy` | `"Toyota"` | Direct preservation of explicit source text matching approved manufacturer name. | **Category C — Empirically Validated** |
| **EPA** | `model` | `"4Runner 4WD"` | `model` | `parsed / exact` | `model: "4Runner"`, `generic_drive: "4WD"` | Multi-stage composite string decomposition (`"4Runner 4WD"` → model + drive suffix). | **Category B — Illustrative / Requires Validation** |
| **EPA** | `drive_descriptor` | `"Part-time 4WD"` | `generic_drive_classification` | `exact_mapping` | `"4WD"` | Controlled vocabulary mapping of explicit source term `"Part-time 4WD"` to generic drive class, supported by approved RA-010 research. | **Category C — Empirically Validated** |
| **EPA** | `drive_descriptor` | `"Part-time 4WD"` | `drivetrain_architecture` | `interpreted` | `"part_time_4wd"` | Architectural interpretation of explicit source term `"Part-time 4WD"`, supported by approved RA-010 research. | **Category C — Empirically Validated** |
| **EPA** | `engine_displacement_liters` | `"4.0"` | `engine_displacement_liters` | `parsed` | `TechnicalValue(4.0, "L", "4.0")` | Type-safe numeric parsing of explicitly designated displacement source field (`displ`), supported by approved RA-010 research. | **Category C — Empirically Validated** |
| **EPA** | `engine_cylinders` | `"6"` | `engine_cylinders` | `parsed` | `6` (integer) | Type-safe integer parsing of explicitly designated cylinder count source field (`cyl`). | **Category C — Empirically Validated** |
| **EPA** | `transmission_descriptor` | `"Automatic 5-spd"` | `transmission_type` | `parsed` | `"automatic"` | String parsing of explicit source descriptor `"Automatic 5-spd"`. | **Category B — Illustrative / Requires Validation** |
| **EPA** | `transmission_descriptor` | `"Automatic 5-spd"` | `transmission_speeds` | `parsed` | `5` (integer) | String parsing of explicit source descriptor `"Automatic 5-spd"`. | **Category B — Illustrative / Requires Validation** |
| **EPA** | `vehicle_class` | `"Small Sport Utility Vehicle 4WD"`| `vehicle_class` | `exact_mapping` | `"Small Sport Utility Vehicle 4WD"` | Full preservation of EPA regulatory vehicle class string without premature collapsing. | **Category B — Illustrative / Requires Validation** |
| **EPA** | `engine_description` | `"SFI"` | `fuel_induction` | `exact_mapping` | `"SFI"` | Direct preservation of raw source abbreviation string without unvalidated expansion. | **Category B — Illustrative / Requires Validation** |
| **EPA** | `city_mpg_epa_rating` | `"16"` | `city_mpg_epa_rating` | `parsed` | `16` (integer) | Type-safe integer parsing of explicitly designated EPA city rating source field (`city08`), retaining semantic qualifier `epa_rating`. | **Category C — Empirically Validated** |
| **EPA** | `highway_mpg_epa_rating` | `"19"` | `highway_mpg_epa_rating` | `parsed` | `19` (integer) | Type-safe integer parsing of explicitly designated EPA highway rating source field (`highway08`), retaining semantic qualifier `epa_rating`. | **Category C — Empirically Validated** |

## 35. Mapping Definition Storage Direction

Initial mapping definitions will be repository-versioned, source-owned, Git-diffable, code-reviewable, and non-database-backed. Ordinary Python data structures are the preferred initial implementation direction. Exact module layout and Python representations remain RA-015 implementation decisions.

## 36. Validation Strategy

Normalization output is validated against the RA-012 `validate_artifact` contract validator, ensuring structural and semantic compliance before candidate construction.

## 37. Failure Behavior

Parsing or mapping errors for an individual assertion produce `mapping_status: "unmapped"` or `"requires_review"` without crashing the ingestion process or dropping raw Tier 1 assertions.

## 38. Determinism

Identical input `SourceAssertionSet` + identical mapping rules → identical `NormalizedInterpretation` output.

## 39. Security

Source strings are processed strictly as untrusted data. Zero dynamic code evaluation (`eval`, `exec`, template rendering).

## 40. Reviewability / Observability

Normalization generates structured logs detailing count of mapped, parsed, interpreted, and unmapped assertions.

## 41. Risks and Safeguards

* **Risk**: Manufacturing unsupported technical detail.
  * **Safeguard**: Enforce the Evidence-Bounded Normalization Rule.
* **Risk**: Dropping source qualifiers.
  * **Safeguard**: Enforce the Semantic Qualifier Preservation Rule.

## 42. RA-012 Contract Compatibility

RA-014 is 100% compatible with the existing RA-012 `NormalizedInterpretation` contract in `reference/ingestion/contracts.py`. Zero contract modifications are required for RA-015 implementation.

## 43. Explicit Non-Goals

RA-014 does NOT implement acquisition adapters, normalization code, mapping rule files, candidate construction, reconciliation, or database models.

## 44. Deferred Decisions

1. Final complete normalized concept key vocabulary.
2. Final complete drivetrain concept vocabulary.
3. Manufacturer-specific terminology mappings beyond empirically validated cases.
4. Final vehicle-class taxonomy.
5. Final fuel-economy metric taxonomy beyond unadjusted values.
6. Canonical source precedence rules.
7. Cross-source conflict resolution & reconciliation architecture.
8. Candidate configuration grouping/construction logic.
9. Canonical `VehicleDefinition` import and matching logic.
10. Permanent database-backed mapping persistence architecture.
11. Final canonical drivetrain/domain ORM architecture.
12. Package/option ORM persistence architecture.
13. Factory technical-feature final domain placement (KDSS, A-TRAC).
14. Human-review UI/workflow implementation.
15. Production ingestion scheduling, background jobs, and orchestration.
16. Historical remapping strategy if normalization rules evolve.
17. Explicit per-rule version metadata beyond Git history.
18. Many-to-one source assertion provenance arrays.
19. Placement of source-native identifiers (`make_id`, `model_id`) in canonical Reference domain.

## 45. Architectural Decisions Proposed for Approval

### Previously Approved Principles (Preserved from RA-010 & RA-011)
1. Intermediate normalized interpretations are non-canonical, traceable objects distinct from database records.
2. 7-dimension drivetrain normalization model and preservation of partial drivetrain knowledge.
3. Manufacturer-taxonomy trim rule (source strings do not automatically create manufacturer trims).
4. `factory_technical_features` preservation for unclassified features like KDSS and A-TRAC.
5. Separated evidence state (`single_source`, `corroborated`, `conflicting`) from workflow review disposition (`pending_review`, `resolved`).

### New RA-014 Architectural Decisions
1. **Source-Specific Normalization Ownership**: Partitioning normalization logic by source behind a shared normalization contract. Each source owns its source-specific interpretation and mapping behavior.
2. **Evidence-Bounded Normalization Rule**: Normalization may only add semantic specificity supported by the source assertion plus an explicitly justified mapping rule. Manufacturing unsupported drivetrain modes, transfer-case ratios, lock states, or capabilities is strictly prohibited.
3. **Explicit Transformation Taxonomy**: Standardizing 6 transformation methods (`direct_copy`, `exact_mapping`, `parsed`, `converted`, `interpreted`, `unmapped`).
4. **Decoupled Concept Key Strategy**: Using stable, lower_snake_case concept keys decoupled from Django ORM field names, treating the concept set as provisional and extensible.
5. **Redesigned Unmapped/Unknown Handling**: Preserving Case A (known concept, unmapped value) and Case B (unknown concept) without fabricating normalized values or treating raw source keys as normalized concept keys.
6. **Preservation of Semantic Qualifiers**: Mandating that technical qualifiers (`epa_rating`, `unadjusted`, `measured`, `estimated`, `front`, `rear`) must not be stripped during normalization.
7. **Repository-Versioned Mapping Definitions**: Approving repository-versioned, Git-reviewable mapping definitions as the preferred initial non-database storage direction.
8. **Streamlined Mapping Rule Identity**: Using stable human-readable rule IDs (`rule_id`) tracked via repository Git history rather than maintaining redundant internal version numbers.
9. **Deterministic Normalization**: Guaranteeing identical outputs for identical inputs and mapping rules.
10. **Separation of Normalization Review from Reconciliation**: Distinguishing normalization review (`unmapped`/`ambiguous`) from cross-source reconciliation.

## 46. Recommended Next Milestone

**RA-015 — Source Assertion Normalization Implementation & Fixture Validation**

### Scoped Scope for RA-015
Implement pure Python normalization engine and validate offline using controlled RA-013 fixtures (`nhtsa/get_models_toyota_2020.json`, `epa/vehicle_42101.json`).

* **Authorized Category C Mappings for RA-015**:
  * `make_id` → `nhtsa_make_id` (`direct_copy`)
  * `make_name` → `make` (`direct_copy`)
  * `model_id` → `nhtsa_model_id` (`direct_copy`)
  * `model_name` → `model` (`direct_copy`)
  * `model_year` → `model_year` (`parsed`)
  * `make` → `make` (`direct_copy`)
  * `drive_descriptor` → `generic_drive_classification: "4WD"` (`exact_mapping`)
  * `drive_descriptor` → `drivetrain_architecture: "part_time_4wd"` (`interpreted`)
  * `engine_displacement_liters` → `engine_displacement_liters` (`parsed`)
  * `engine_cylinders` → `engine_cylinders` (`parsed`)
  * `city_mpg_epa_rating` → `city_mpg_epa_rating` (`parsed`)
  * `highway_mpg_epa_rating` → `highway_mpg_epa_rating` (`parsed`)
* **Strict Exclusions for RA-015**:
  * Do NOT implement CandidateConfigurationDocument generation or candidate aggregation.
  * Do NOT implement cross-source reconciliation.
  * Do NOT perform live network requests or database writes.
