# RA-011 — Ingestion Schema & Intermediate Serialization Design

> [!NOTE]
> **Status**: Architectural & Research Design Document  
> **Authority**: Governed by the Project Blueprint and Engineering Handbook. Positioned at Level 4 in the project authority hierarchy (below Current Task, ADRs, and `CURRENT_STATE.md`). Builds upon approved architecture [RA-010](file:///Users/esse/dev/Rigarchive/docs/architecture/designs/RA-010-Reference-Ingestion-Source-Mapping-Architecture.md).  
> **Scope**: Specification of versioned intermediate serialization formats, data representation contracts, provenance metadata schemas, high-fidelity drivetrain serialization, reconciliation states, and validation strategies for reference data ingestion.

---

## Executive Summary

RA-010 established the multi-stage architecture for acquiring external vehicle specification data and converting it into canonical RigArchive Reference records without corrupting domain identity or discarding technical specificity.

RA-011 defines the **intermediate data representation contracts and versioned logical schemas** that connect the stages of the ingestion pipeline:

```text
External Sources
      ↓
[Acquisition Engine]
      ↓
1. Source Assertion Set Schema  (<ingestion-runtime-root>/<source-artifacts>/)
      ↓
[Normalization Engine]
      ↓
2. Candidate Configuration Document Schema  (<ingestion-runtime-root>/<candidate-artifacts>/)
   (Contains: Source Assertions → Normalized Interpretations → Candidate Identity & Attributes)
      ↓
[Reconciliation & Human Review]
      ↓
Approved Candidate Configuration
      ↓
[Canonical Import Engine]
      ↓
Canonical Reference Domain (db.sqlite3)
```

### Key Serialization Principles Established in RA-011
1. **Two-Tier Artifact Architecture**: Ingestion is governed by two distinct logical artifact schemas:
   * `SourceAssertionSet` (Raw/extracted source assertions and acquisition envelope).
   * `CandidateConfigurationDocument` (Normalized configuration context, normalized assertions/interpretations, factory technical features, attribute-level provenance, and reconciliation/review states).
2. **Explicit Normalized-Assertion Layer**: The intermediate representation explicitly captures the normalization transformation (`source assertion → normalized interpretation → candidate attribute`), preserving raw values, normalized concepts, mapping notes, and provenance links.
3. **Explicit Schema Versioning Envelopes**: Every intermediate artifact carries mandatory envelope metadata (`artifact_type` and `schema_version` SemVer). Version metadata identifies the applicable logical serialization contract, enables readers and validators to determine how compatibility should be handled, and supports controlled schema evolution. It does NOT itself guarantee forward or backward compatibility. `$schema` URI is reserved as an optional future field.
4. **Decoupled Candidate Identity**: Candidates define real-world vehicle context (`candidate_identity`) and source-specific configuration IDs rather than mirroring Django `VehicleDefinition` database model columns.
5. **Non-Lossy Technical Contracts**: Rich technical details (7-dimension drivetrain structure, engine engineering attributes, transmission specifications) are preserved in structured JSON objects independently of today's primary `VehicleDefinition` model column bounds.
6. **Separated Reconciliation & Review States**: Attribute evidence states (`corroborated`, `single_source`, `conflicting`, `ambiguous`, `incomplete`) are logically separated from human-review workflow dispositions (`not_required`, `pending_review`, `under_review`, `resolved`, `rejected_excluded`). Attribute-level state remains primary.
7. **Transient Candidate References**: Candidate documents use a transient `candidate_reference` string for artifact identification and diff tracking. This is explicitly NOT a canonical Reference identifier, a `VehicleDefinition` identity key, or the canonical import matching key.

---

## 1. Purpose

This document specifies the concrete serialization contracts, logical schemas, JSON structures, field definitions, unit representations, missing-value semantics, and validation rules required to serialize intermediate data payloads throughout the RigArchive ingestion pipeline.

---

## 2. Governing Authority & Relationship to RA-010

This proposal operates under the established project authority hierarchy:
1. Current approved implementation task
2. Architectural Decision Records ([ADR-0001](file:///Users/esse/dev/Rigarchive/docs/architecture/ADR/ADR-0001-Entity-Identity-Strategy.md), [ADR-0002](file:///Users/esse/dev/Rigarchive/docs/architecture/ADR/ADR-0002-Immutable-Automatic-Slugs.md), [ADR-0003](file:///Users/esse/dev/Rigarchive/docs/architecture/ADR/ADR-0003-Core-Infrastructure.md))
3. [`docs/implementation/CURRENT_STATE.md`](file:///Users/esse/dev/Rigarchive/docs/implementation/CURRENT_STATE.md)
4. **Approved Architecture Documents** ([RA-006](file:///Users/esse/dev/Rigarchive/docs/architecture/designs/RA-006-Observation-Foundation-Architecture.md), [RA-008](file:///Users/esse/dev/Rigarchive/docs/architecture/designs/RA-008-Development-Data-Preservation-Architecture.md), [RA-010](file:///Users/esse/dev/Rigarchive/docs/architecture/designs/RA-010-Reference-Ingestion-Source-Mapping-Architecture.md), and RA-011)
5. Engineering Handbook
6. Project Blueprint

### RA-010 Baseline Preservation
RA-011 preserves all approved RA-010 principles:
* Source acquisition is strictly decoupled from canonical Reference import.
* Manufacturer-recognized market-specific taxonomy governs trim/grade identity. Sub-grades (`SR5 Premium`, `Trail Premium`) remain distinct.
* Packages and individual options not recognized by the manufacturer as distinct trims/grades do not independently create `VehicleDefinition` records.
* Technical specificity is preserved across 7 conceptual drivetrain dimensions.
* Source authority is attribute-specific.
* Ingestion runtime artifacts are isolated from development DB preservation (`backups/`).

---

## 3. Current Reference Implementation Findings

Inspection of the repository implementation establishes:
* **Reference Hierarchy**: Implemented in [`reference/models.py`](file:///Users/esse/dev/Rigarchive/reference/models.py):
  * [`Manufacturer`](file:///Users/esse/dev/Rigarchive/reference/models.py#L9): `name`, `slug`, `country_code`, `is_active`.
  * [`VehicleModel`](file:///Users/esse/dev/Rigarchive/reference/models.py#L59): `manufacturer` (FK), `name`, `slug`, `is_active`.
  * [`Generation`](file:///Users/esse/dev/Rigarchive/reference/models.py#L115): `vehicle_model` (FK), `name`, `slug`, `generation_number`, `start_year`, `end_year`, `notes`, `is_active`.
  * [`VehicleDefinition`](file:///Users/esse/dev/Rigarchive/reference/models.py#L209): `generation` (FK), `model_year`, `trim_name`, `engine_name`, `drivetrain` (`2WD`, `4WD`, `AWD`, `UNK` — 4 choice values), `market` (`US`, `CA`, `OT`), `slug`, `notes`, `is_active`.
* **Identity Mechanics**: All Reference entities inherit from [`core.models.BaseModel`](file:///Users/esse/dev/Rigarchive/core/models.py#L35), enforcing dual identity (internal integer PK `id` + immutable external UUID `uuid`). Slugs are non-editable (`editable=False`).
* **Current Schema Boundary**: `VehicleDefinition` currently represents drivetrain as a 4-choice field (`2WD`, `4WD`, `AWD`, `UNK`) and engine as free-form text. Intermediate serialization MUST preserve rich nested technical attributes without truncating data to fit current database column bounds.

---

## 4. Representation-Layer Architecture & Storage Boundaries

The serialization architecture distinguishes three logical information stages across two physical artifact tiers:

```
┌───────────────────────────────────────────────────────────────────────────┐
│                    Two-Tier Serialization Architecture                    │
├───────────────────────────────────────────────────────────────────────────┤
│ Tier 1: Source Assertion Set Schema                                       │
│ • Captures raw/extracted source assertions and retrieval metadata.         │
│ • Source-oriented structure reflecting what the source asserted.          │
├───────────────────────────────────────────────────────────────────────────┤
│ Tier 2: Candidate Configuration Document Schema                           │
│ • Contains embedded Normalized Interpretations layer.                     │
│ • Captures candidate configuration context, normalized attributes,        │
│   source-specific identities, factory technical features, provenance      │
│   links, and separated reconciliation & review workflow states.           │
└───────────────────────────────────────────────────────────────────────────┘
```

### Runtime Storage Isolation
* Ingestion runtime artifacts MUST remain strictly outside RA-009 `backups/`.
* The exact runtime root directory and filesystem hierarchy remain unresolved. Conceptual locations are designated using nonbinding placeholders (`<ingestion-runtime-root>/<source-artifacts>/` and `<ingestion-runtime-root>/<candidate-artifacts>/`). Logical artifact architecture does not require a physical path decision.

---

## 5. Serialization Format & Versioning Strategy

**JSON (JavaScript Object Notation)** is selected as the logical intermediate format.

### Envelope Metadata Standard
Every artifact MUST include an `envelope` object containing:
* `artifact_type`: Logical artifact identifier (`rigarchive.source_assertion_set.v1` or `rigarchive.candidate_configuration.v1`).
* `schema_version`: Semantic Versioning string (`MAJOR.MINOR.PATCH`, e.g., `"1.0.0"`).
* `$schema`: (Optional) Canonical schema URI reference reserved for future machine-readable schema publication.
* `created_at`: (Optional) ISO-8601 UTC timestamp.
* `generator`: (Optional) Producing software component name and version.

```json
{
  "envelope": {
    "artifact_type": "rigarchive.candidate_configuration.v1",
    "schema_version": "1.0.0",
    "created_at": "2026-08-15T09:00:00Z",
    "generator": "rigarchive-normalizer/0.1.0"
  }
}
```

### Version Compatibility Semantics
* **MAJOR**: Incompatible logical-contract change. Historical artifacts remain interpretable under declared major versions; active conversion is an operational decision.
* **MINOR**: Backward-compatible additive field addition.
* **PATCH**: Clarification or non-structural metadata correction.

---

## 6. Source Metadata & Assertion-Level Representation (Tier 1 Schema)

Source metadata records acquisition context without making blanket legal or source-role determinations.

### Source Metadata
* `source_id`: RigArchive-local stable source identifier (`nhtsa_vpic`, `epa_fueleconomy`, `toyota_usa_press`, `jd_power`).
* `source_type`: Descriptive category (`regulatory_api`, `powertrain_database`, `manufacturer_publication`, `commercial_catalog`).
* `source_locator`: Source URL, API endpoint, or document reference.
* `retrieved_at`: ISO-8601 UTC timestamp.
* `native_record_id`: Source's internal ID (e.g. EPA vehicle ID `42101`).
* `acquisition_method`: Mechanism (`rest_api_json`, `csv_download`, `html_extraction`).
* `source_use_notes`: Descriptive notes on retention or operational constraints.
* `review_status`: Rights review status (`unknown`, `not_reviewed`, `source_specific`).

### Source Assertion Model
Each assertion within a `SourceAssertionSet` payload contains:
* `assertion_id`: Local key within payload (e.g., `ast_epa_eng_01`).
* `attribute_key`: Target technical field (`engine_description`, `drive_descriptor`, `trim_string`).
* `raw_value`: Unmodified factual string or numeric value from the source.
* `source_context`: Payload location or JSON field path.
* `extracted_at`: ISO-8601 UTC timestamp.

---

## 7. Explicit Normalized-Assertion & Interpretation Layer

To make the normalization transformation auditable, candidate documents embed a structured `normalized_assertions` layer that connects raw assertions to normalized candidate attributes:

```
[Raw Source Assertion] (ast_epa_drive_01: "Part-time 4WD")
          ↓
[Normalized Interpretation] (drivetrain.architecture -> "part-time 4WD")
          ↓
[Candidate Attribute] (drivetrain_details -> 7-dimension structure)
```

### Normalized Interpretation Structure
```json
"normalized_assertions": [
  {
    "interpretation_id": "interp_drive_arch_01",
    "source_assertion_ref": "ast_epa_drive_01",
    "target_attribute_key": "drivetrain.architecture",
    "normalized_concept": "part-time 4WD",
    "raw_source_value": "Part-time 4WD",
    "manufacturer_term": "Part-time 4WD System",
    "mapping_status": "mapped",
    "normalization_notes": "Mapped directly from EPA drive descriptor to 7-dimension architecture concept"
  }
]
```

---

## 8. Candidate Configuration Representation (Tier 2 Schema)

A `CandidateConfigurationDocument` represents a normalized vehicle configuration ready for reconciliation and evaluation.

### Core Sections
1. `envelope`: Versioning metadata.
2. `candidate_reference`: Illustrative transient reference string (e.g. `cand_ref_2020_toyota_4runner_trd_off_road_premium_4wd`). Explicitly non-canonical.
3. `candidate_identity`: Real-world configuration context (`manufacturer_name`, `vehicle_model_name`, `generation_name`, `model_year`, `trim_name`, `market`).
4. `source_configuration_identities`: Native source identifiers (EPA ID, NHTSA VIN pattern, etc.).
5. `normalized_assertions`: Explicit normalization transformation layer.
6. `normalized_technical_details`: High-fidelity nested specifications (Engine, Transmission, 7-dimension Drivetrain).
7. `factory_technical_features`: Preserved unclassified technical features.
8. `packages_and_options`: Mapped packages and options.
9. `attribute_provenance`: Map linking attributes to interpretation IDs.
10. `reconciliation_and_review`: Separated evidence and workflow states.

---

## 9. Source-Specific Configuration Identity Representation

External sources expose distinct notions of configuration identity. The candidate document explicitly carries source-specific IDs without treating them as canonical identity:

```json
"source_configuration_identities": [
  {
    "source_id": "epa_fueleconomy",
    "identity_type": "epa_vehicle_id",
    "native_identifier": "42101",
    "source_description": "2020 Toyota 4Runner 4WD 6 cyl 4.0 L Automatic 5-spd"
  },
  {
    "source_id": "nhtsa_vpic",
    "identity_type": "vpic_pattern_id",
    "native_identifier": "11982",
    "source_description": "Toyota 4Runner Multi-Purpose Passenger Vehicle (MPV)"
  }
]
```

---

## 10. High-Fidelity Drivetrain Serialization Contract

The drivetrain contract preserves RA-010's **7 conceptual drivetrain dimensions**:

```json
"drivetrain_details": {
  "generic_classification": "four-wheel drive",
  "architecture": "full-time 4WD",
  "components": [
    {
      "component_type": "transfer_case",
      "name": "Two-speed transfer case",
      "low_range_ratio": 2.566
    },
    {
      "component_type": "center_differential",
      "name": "Torsen Type-3 Limited-Slip Center Differential",
      "has_locking_feature": true
    }
  ],
  "operating_modes": [
    {
      "mode_code": "H4F",
      "name": "Full-Time 4WD High Range (Open)",
      "center_differential_state": "open",
      "torque_split_default": "40:60"
    },
    {
      "mode_code": "H4L",
      "name": "Full-Time 4WD High Range (Locked)",
      "center_differential_state": "locked",
      "torque_split_default": "50:50"
    },
    {
      "mode_code": "L4L",
      "name": "Full-Time 4WD Low Range (Locked)",
      "center_differential_state": "locked",
      "low_range_engaged": true
    }
  ],
  "capabilities": [
    "full_time_4wd_operation",
    "center_differential_lock",
    "low_range"
  ],
  "manufacturer_terminology": "Full-time 4WD with Torsen limited-slip center differential with locking feature"
}
```

### Technical Disambiguation
* `component` (`center_differential`) != `capability` (`center_differential_lock`).
* `operating_mode` (`H4F`) != `architecture` (`full-time 4WD`).
* Empirical values (transfer case ratio `2.566`, torque split `40:60`) are illustrative content, not universal schema rules.

---

## 11. Broader Technical Features Representation

Technical features whose eventual canonical domain placement is unresolved (e.g. electronic traction systems, suspension mechanisms, exterior accessories) are preserved as `factory_technical_features`. KDSS carries both its source presentation and an unresolved classification status:

```json
"factory_technical_features": [
  {
    "feature_name": "Kinetic Dynamic Suspension System (KDSS)",
    "source_classification": "option_package",
    "normalized_classification_status": "unresolved",
    "source_assertion_ref": "ast_toyota_kdss_01"
  },
  {
    "feature_name": "Active Traction Control (A-TRAC)",
    "source_classification": "standard_feature",
    "normalized_classification_status": "unresolved",
    "source_assertion_ref": "ast_toyota_atrac_01"
  }
]
```

---

## 12. Trim, Package, and Option Classification

Implementing RA-010's **Manufacturer-Taxonomy Rule**, the schema distinguishes source presentation from normalized trim classification status:

```json
"trim_classification": {
  "trim_name": "TRD Off-Road Premium",
  "sub_grade_designation": "Premium",
  "classification_status": "manufacturer_sub_grade",
  "is_manufacturer_recognized_trim": true
},
"packages_and_options": [
  {
    "name": "Premium Audio with Dynamic Navigation",
    "source_classification": "option_package",
    "normalized_classification_status": "package",
    "is_distinct_trim_identity": false
  }
]
```

---

## 13. Separated Reconciliation & Review Workflow States

Evidence status is explicitly separated from human-review disposition:

### Evidence / Reconciliation States (Attribute-Level)
* `single_source`: Asserted by a single source without contradiction.
* `corroborated`: Asserted by multiple sources without conflict.
* `conflicting`: Source assertions disagree at the same specificity level.
* `ambiguous`: Source text cannot be parsed deterministically.
* `incomplete`: Missing mandatory attributes.

### Review Workflow Dispositions
* `not_required`: Corroborated or single-source data meeting auto-pass rules.
* `pending_review`: Requires human review.
* `under_review`: Currently assigned for review.
* `resolved`: Conflict resolved by human review.
* `rejected_excluded`: Candidate or assertion rejected during review.

### Primary Attribute-Level State & Summary Indicator
Attribute-level state is primary. The candidate root carries a workflow summary indicator (`requires_human_review: true/false`):

```json
"reconciliation_and_review": {
  "requires_human_review": true,
  "review_workflow_disposition": "pending_review",
  "attribute_states": {
    "drivetrain_architecture": {
      "reconciliation_state": "corroborated",
      "review_disposition": "not_required"
    },
    "engine_displacement": {
      "reconciliation_state": "corroborated",
      "review_disposition": "not_required"
    },
    "trim_name": {
      "conflict_details": "Source A asserts 'SR5', Source B asserts 'SR5 Premium'",
      "reconciliation_state": "conflicting",
      "review_disposition": "pending_review"
    }
  },
  "reconciliation_notes": "Trim conflict requires human review"
}
```

---

## 14. Missing, Unknown, and Semantic Value Representation

Bare `null` is prohibited when semantic distinction is required. The schema specifies three missing-value mechanisms:

1. **Field Omission**: Used when an optional scalar attribute was simply not asserted by any source.
2. **Explicit `null`**: Used when a value is known to be empty or null.
3. **Semantic Missing Value Object**: Used when the exact reason for missingness must be preserved:

```json
"center_differential": {
  "status": "not_applicable",
  "reason": "Part-time 4WD system does not utilize a center differential"
},
"transmission_code": {
  "status": "not_supplied_by_source",
  "reason": "Source API payload omitted transmission factory code"
}
```

---

## 15. Technical Value & Unit Representation

Technical measurements store raw source text alongside ONE normalized numeric value & standard unit:

```json
"engine_displacement": {
  "normalized_value": 4.0,
  "normalized_unit": "L",
  "raw_source_string": "3,956 cc / 4.0L"
},
"horsepower": {
  "normalized_value": 270,
  "normalized_unit": "hp",
  "rpm_normalized": 5600,
  "raw_source_string": "270 hp @ 5600 rpm"
}
```

---

## 16. Serialization Determinism Rules

Intermediate JSON artifacts MUST support reproducible formatting for test assertion and Git diffing:
* **Object Keys**: Sorted alphabetically.
* **Unordered Collections**: Sorted deterministically by explicit stable key (e.g. `interpretation_id`, `feature_name`).
* **Ordered Collections**: Source-ordered or semantically-ordered lists preserve their order.
* **Indentation & Encoding**: 2 spaces per indentation level; UTF-8 without BOM.
* **Timestamps**: ISO-8601 UTC format (`YYYY-MM-DDTHH:MM:SSZ`).

---

## 17. Security & Input Safe Handling

* **Untrusted Input**: Source strings are treated as untrusted data, safely UTF-8 encoded, and escaped at interpretation/presentation boundaries. Source strings are not mutated during acquisition.
* **Credential Protection**: Artifacts MUST NEVER contain API keys, passcodes, or internal filesystem credentials.
* **Copyright Compliance**: Acquisition complies with source-specific operational constraints; proprietary material is not retained wholesale.

---

## 18. Representative JSON Examples (Design Illustrations — Non-Canonical Data)

### Example 1: `SourceAssertionSet` Payload (Tier 1 Schema Illustration)
```json
{
  "envelope": {
    "artifact_type": "rigarchive.source_assertion_set.v1",
    "created_at": "2026-08-15T09:15:00Z",
    "generator": "rigarchive-acquisition-epa/0.1.0",
    "schema_version": "1.0.0"
  },
  "provenance": {
    "acquisition_method": "rest_api_json",
    "native_record_id": "42101",
    "retrieved_at": "2026-08-15T09:15:00Z",
    "review_status": "not_reviewed",
    "source_id": "epa_fueleconomy",
    "source_locator": "https://www.fueleconomy.gov/ws/rest/ympg/shared/ympgVehicle/42101",
    "source_type": "powertrain_database",
    "source_use_notes": "Source-use review pending",
    "target_context": {"make": "Toyota", "market": "US", "model": "4Runner", "model_year": 2020}
  },
  "source_assertions": [
    {
      "assertion_id": "ast_epa_eng_01",
      "attribute_key": "engine_description",
      "extracted_at": "2026-08-15T09:15:00Z",
      "raw_value": "4.0 L, 6 cyl, Automatic 5-spd",
      "source_context": "payload.engine"
    },
    {
      "assertion_id": "ast_epa_drive_01",
      "attribute_key": "drive_descriptor",
      "extracted_at": "2026-08-15T09:15:00Z",
      "raw_value": "Part-time 4WD",
      "source_context": "payload.drive"
    }
  ]
}
```

### Example 2: `CandidateConfigurationDocument` (Tier 2 Schema Illustration)
```json
{
  "attribute_provenance": {
    "drivetrain_architecture": ["interp_drive_arch_01"],
    "engine_displacement": ["interp_eng_disp_01"],
    "trim_name": ["interp_trim_01"]
  },
  "candidate_identity": {
    "generation_name": "Fifth Generation",
    "manufacturer_name": "Toyota",
    "market": "US",
    "model_year": 2020,
    "trim_name": "TRD Off-Road Premium",
    "vehicle_model_name": "4Runner"
  },
  "candidate_reference": "cand_ref_2020_toyota_4runner_trd_off_road_premium_4wd",
  "envelope": {
    "artifact_type": "rigarchive.candidate_configuration.v1",
    "created_at": "2026-08-15T09:20:00Z",
    "generator": "rigarchive-normalizer/0.1.0",
    "schema_version": "1.0.0"
  },
  "factory_technical_features": [
    {
      "category_status": "unclassified_feature",
      "feature_name": "Active Traction Control (A-TRAC)",
      "normalized_classification_status": "unresolved",
      "source_assertion_ref": "ast_toyota_atrac_01",
      "source_classification": "standard_feature"
    },
    {
      "category_status": "unclassified_feature",
      "feature_name": "Kinetic Dynamic Suspension System (KDSS)",
      "normalized_classification_status": "unresolved",
      "source_assertion_ref": "ast_toyota_kdss_01",
      "source_classification": "option_package"
    }
  ],
  "normalized_assertions": [
    {
      "interpretation_id": "interp_drive_arch_01",
      "manufacturer_term": "Part-time 4WD System",
      "mapping_status": "mapped",
      "normalization_notes": "Mapped directly from EPA drive descriptor",
      "normalized_concept": "part-time 4WD",
      "raw_source_value": "Part-time 4WD",
      "source_assertion_ref": "ast_epa_drive_01",
      "target_attribute_key": "drivetrain.architecture"
    },
    {
      "interpretation_id": "interp_eng_disp_01",
      "manufacturer_term": "4.0L DOHC V6",
      "mapping_status": "mapped",
      "normalization_notes": "Extracted displacement from EPA engine string",
      "normalized_concept": "4.0L",
      "raw_source_value": "4.0 L, 6 cyl",
      "source_assertion_ref": "ast_epa_eng_01",
      "target_attribute_key": "engine.displacement"
    }
  ],
  "normalized_technical_details": {
    "drivetrain_details": {
      "architecture": "part-time 4WD",
      "capabilities": [
        "selectable_2wd",
        "selectable_4wd",
        "low_range",
        "rear_differential_lock"
      ],
      "components": [
        {
          "component_type": "transfer_case",
          "low_range_ratio": 2.566,
          "name": "VF2A Manual Lever Transfer Case"
        },
        {
          "component_type": "rear_differential",
          "has_locking_feature": true,
          "name": "Electronic Locking Rear Differential"
        }
      ],
      "generic_classification": "four-wheel drive",
      "manufacturer_terminology": "Part-time 4WD with Active Traction Control and Rear Differential Lock",
      "operating_modes": [
        {"center_coupling": "unlocked", "mode_code": "2H", "name": "2WD High"},
        {"center_coupling": "locked", "mode_code": "4H", "name": "4WD High"},
        {"center_coupling": "locked", "low_range": true, "mode_code": "4L", "name": "4WD Low"}
      ]
    },
    "engine": {
      "code": "1GR-FE",
      "cylinders": 6,
      "displacement": {"normalized_unit": "L", "normalized_value": 4.0, "raw_source_string": "4.0 L"},
      "horsepower": {"normalized_unit": "hp", "normalized_value": 270, "raw_source_string": "270 hp @ 5600 rpm", "rpm_normalized": 5600}
    },
    "transmission": {
      "code": "A750F",
      "speeds": 5,
      "type": "Automatic"
    }
  },
  "packages_and_options": [
    {
      "is_distinct_trim_identity": false,
      "name": "Premium Audio with Dynamic Navigation",
      "normalized_classification_status": "package",
      "source_classification": "option_package"
    }
  ],
  "reconciliation_and_review": {
    "attribute_states": {
      "drivetrain_architecture": {
        "reconciliation_state": "corroborated",
        "review_disposition": "not_required"
      },
      "engine_displacement": {
        "reconciliation_state": "corroborated",
        "review_disposition": "not_required"
      },
      "trim_name": {
        "conflict_details": "Source A asserts 'SR5', Source B asserts 'SR5 Premium'",
        "reconciliation_state": "conflicting",
        "review_disposition": "pending_review"
      }
    },
    "reconciliation_notes": "Trim conflict requires human review",
    "requires_human_review": true,
    "review_workflow_disposition": "pending_review"
  },
  "source_configuration_identities": [
    {
      "identity_type": "epa_vehicle_id",
      "native_identifier": "42101",
      "source_description": "2020 Toyota 4Runner 4WD 6 cyl 4.0 L Automatic 5-spd",
      "source_id": "epa_fueleconomy"
    }
  ]
}
```

---

## 19. Empirical 4Runner Schema Stress Test

Validating the proposed schema against the approved 5th Gen Toyota 4Runner empirical study:

1. **2010 Launch Year**: Schema handles `SR5 2.7L I4 2WD` (4-speed auto) alongside `4.0L V6` (5-speed auto 2WD/4WD) without forcing an invalid `SR5 I4 4WD` combination.
2. **2015 Mid-Cycle Update**: Schema preserves sub-grades `SR5 Premium` and `Trail Premium` as distinct candidate configuration records while tracking KDSS as a `factory_technical_feature` carrying both `source_classification: "option_package"` and `normalized_classification_status: "unresolved"`.
3. **2020 Special Editions Update**: Schema preserves `Venture` and `Nightshade` as distinct trim identities while isolating full-time 4WD Torsen details on Limited/Nightshade vs part-time 4WD on Venture/TRD Off-Road.
4. **2024 Final Year**: Schema represents final lineup without including the 2023-only `40th Anniversary Special Edition`.

---

## 20. Explicit Unresolved / Deferred Decisions

The following 14 decisions remain intentionally unresolved in RA-011:
1. **Canonical Import Matching Key / Mechanism**: The exact matching key or deduplication algorithm for candidate-to-canonical matching during import.
2. **Final Runtime Ingestion Storage Root / Path / Hierarchy**: The exact filesystem/storage location for ingestion artifacts.
3. **Persistent Django Staging Models**: Whether permanent staging/review database tables are eventually needed.
4. **Permanent Package / Option Persistence Architecture**: Final Django domain representation of packages and options.
5. **Final Technical-Domain Placement of Broader Factory Features**: Domain ownership for A-TRAC, CRAWL Control, MTS, KDSS, X-REAS, suspension systems, factory accessories, etc.
6. **J.D. Power / Commercial-Source Automated Production Suitability**: Source-specific legal, contractual, operational, and technical suitability for automated production acquisition.
7. **Manufacturer/Attribute-Specific Source Precedence Rules**: Exact source authority/preference rules require empirical validation; RA-010's source-role examples remain hypotheses rather than universal hierarchy.
8. **Final Controlled Drivetrain Vocabulary**: Controlled vocabulary enumerations for drivetrain components and operating modes requiring broader multi-manufacturer validation.
9. **Final Canonical Drivetrain Domain / Django Model Architecture**: The seven conceptual serialization dimensions do not prescribe seven models or final database persistence structure.
10. **Public Presentation / UI**: Generic, technical, and detailed drivetrain presentation remains a future concern.
11. **Production Ingestion Scheduling / Orchestration**: Batch scheduling, queues, retries, and job orchestration remain outside RA-011.
12. **Acquisition Adapter Implementation Details**: Source-specific acquisition mechanics not required to establish serialization remain deferred.
13. **Historical Artifact Conversion / Migration Policy**: Whether old serialization artifacts ever need active conversion rather than interpretation by version-aware tooling.
14. **Formal Machine-Readable JSON Schema Publication**: Logical validation is approved conceptually; exact formal schema artifacts/tooling belong to implementation work.

---

## 21. Recommended Next Milestone

# RA-012 — Intermediate Serialization Contract Implementation & Fixture Validation

### Proposed Scope
* Implement Python serialization/validation structures and contracts corresponding to the approved RA-011 design.
* Implement structural and semantic validation in Python.
* Create small controlled fixture files derived from the approved RA-010 4Runner study.
* Test round-trip serialization/deserialization, provenance traceability, normalized assertion links, and deterministic formatting.
* Verify that rich candidate data survives serialization without being truncated to current `VehicleDefinition` fields.
* **Do NOT acquire live external data, import canonical Reference records, or modify Django database models.** (Live acquisition adapters deferred to RA-013).
