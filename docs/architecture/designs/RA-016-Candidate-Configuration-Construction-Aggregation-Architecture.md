# RA-016 — Candidate Configuration Construction & Aggregation Architecture

**Status**: Accepted  
**Date**: 2026-08-15  
**Domain**: Reference Domain — Data Ingestion Pipeline  

---

## 1. Executive Summary

RA-016 establishes the architectural design for transforming normalized source interpretations (`NormalizedInterpretation`) derived from one or more acquisition sources into transient candidate configuration documents (`CandidateConfigurationDocument`).

This architecture bridges source-assertion normalization (RA-014/RA-015) with downstream cross-source reconciliation and canonical Reference import, defining how RigArchive aggregates multi-source technical evidence into a candidate factory configuration without silently converting aggregation into reconciliation or canonical truth assignment.

## 2. Purpose

The purpose of RA-016 is to define how RigArchive safely, deterministically, and reproducibly constructs candidate configuration documents while:
* preserving source evidence, raw assertions, multi-source provenance, ambiguity, and unresolved technical features;
* enforcing a **Hybrid Context/Evidence Grouping Model** where caller-supplied `CandidateIdentity` defines the intended aggregation boundary without acting as source evidence or canonical truth;
* explicitly separating **Evidence Reconciliation** (evaluating independent source evidence lineages against each other) from **Candidate-Context Verification** (evaluating normalized source evidence against caller context);
* preventing the premature resolution of conflicts, source precedence assumptions, or automatic entity matching;
* adhering strictly to the **No Semantic Recovery** rule (candidate attributes and factory technical features are projected ONLY from approved normalized interpretations emitted by RA-015);
* operating strictly over the existing [RA-011](file:///Users/esse/dev/Rigarchive/docs/architecture/designs/RA-011-Ingestion-Schema-Intermediate-Serialization-Design.md)/[RA-012](file:///Users/esse/dev/Rigarchive/docs/implementation/tasks/RA-012-intermediate-serialization-implementation.md) serialization contracts (**Outcome B**) using implementation conventions without requiring contract extensions.

## 3. Scope

### Included in RA-016 Architectural Design
* Defining the transient candidate configuration concept and its boundary against canonical database entities (`VehicleDefinition`).
* Establishing the Hybrid Context/Evidence Grouping Model and candidate identity rules.
* Separating evidence reconciliation states from candidate-context verification states.
* Formulating candidate-context verification concepts (`supported`, `partially_supported`, `contradicted`, `unverified`).
* Formulating evidence lineage, duplicate detection, and independent corroboration rules.
* Defining attribute projection and conflict representation rules for candidate technical fields.
* Constructing a 15-scenario evidence-state matrix mapping inputs to projected values, provenance, evidence states, review dispositions, and review flags.
* Establishing applicability evaluation prior to evidence-state classification.
* Defining the provenance model for 1-to-many normalization and multi-source attribute support.
* Establishing non-semantic transient `candidate_reference` semantics and semantic determinism.
* Stress testing the architecture against 5th-Generation Toyota 4Runner NHTSA/EPA controlled evidence across 3 distinct scenarios.
* Defining factory technical feature and option package aggregation boundaries.
* Performing a comprehensive contract gap analysis demonstrating Outcome B adequacy.
* Recommending the implementation boundary for RA-017.

### Excluded from RA-016 (Non-Goals)
* Implementing candidate construction Python modules or runtime aggregation logic.
* Modifying `reference/ingestion/contracts.py` or intermediate serialization validators.
* Modifying RA-013 acquisition adapters or RA-015 normalizers.
* Creating CandidateConfigurationDocument test fixtures or unit tests.
* Canonical Reference entity matching, deduplication, or `VehicleDefinition` writes.
* Canonical source precedence hierarchy or final conflict resolution UI/workflows.
* Persistent ORM staging models, migrations, or database schema changes.
* Production storage directory structures or background job scheduling.

## 4. Governing Architecture & Authority

Governed by the approved [RA-010 Source Mapping Architecture](file:///Users/esse/dev/Rigarchive/docs/architecture/designs/RA-010-Reference-Ingestion-Source-Mapping-Architecture.md), [RA-011 Ingestion Serialization Architecture](file:///Users/esse/dev/Rigarchive/docs/architecture/designs/RA-011-Ingestion-Schema-Intermediate-Serialization-Design.md), and [RA-014 Source Assertion Normalization Architecture](file:///Users/esse/dev/Rigarchive/docs/architecture/designs/RA-014-Source-Assertion-Normalization-Mapping-Architecture.md), and operating over the executable implementation delivered in [RA-012 Intermediate Serialization](file:///Users/esse/dev/Rigarchive/docs/implementation/tasks/RA-012-intermediate-serialization-implementation.md), [RA-013 Acquisition Adapters](file:///Users/esse/dev/Rigarchive/docs/implementation/tasks/RA-013-public-source-acquisition-implementation.md), and [RA-015 Source Assertion Normalization](file:///Users/esse/dev/Rigarchive/docs/implementation/tasks/RA-015-source-assertion-normalization-implementation.md).

## 5. Candidate Configuration Definition & Canonical Boundary

* **Candidate Configuration**: A transient, evidence-backed structured hypothesis assembling normalized interpretations from one or more sources that describe the same real-world factory configuration context.
* **Candidate Identity / Context**: A structural header (`CandidateIdentity`) declaring the target vehicle context (`manufacturer_name: "Toyota"`, `vehicle_model_name: "4Runner"`, `model_year: 2020`, `market: "US"`) that defines the candidate's aggregation boundary.
* **Candidate Attribute**: A projected technical attribute (e.g. `engine_displacement_liters = TechnicalValue(4.0, "L", "4.0")`) derived from one or more `NormalizedInterpretation` objects.
* **Evidence Set**: The underlying set of `NormalizedInterpretation` and `SourceAssertion` objects that support, corroborate, or conflict upon projected candidate attributes.
* **Distinction from Canonical `VehicleDefinition`**:
  * `CandidateConfigurationDocument` is transient, non-canonical, JSON-serializable, and lives outside the database.
  * `VehicleDefinition` is persistent, authoritative, database-backed (Django ORM), assigned an internal integer PK + permanent UUID + slug, and represents verified domain truth.
  * A candidate configuration does NOT equal a database row, does NOT claim canonical authority, and does NOT alter `db.sqlite3`.

```text
SourceAssertionSet(s) [RA-013]
    ↓
NormalizedInterpretation(s) [RA-015]
    ↓
[RA-016 CANDIDATE CONSTRUCTION BOUNDARY]
    Caller-Supplied Candidate Context (CandidateIdentity)
        ↓
    Candidate Aggregation & Attribute Projection (From Mapped Interpretations Only)
        ↓
    Mechanical Evidence State Assignment (single_source, corroborated, conflicting)
    & Candidate-Context Verification (supported, partially_supported, contradicted, unverified)
        ↓
    CandidateConfigurationDocument
[STOP FOR RA-016]
    ↓
Later Reconciliation Milestone
    ↓
Later Canonical Import Milestone
```

## 6. Candidate Grouping Architecture (Hybrid Model)

RA-016 adopts a **Hybrid Context/Evidence Grouping Model**:
1. **Caller-Supplied Candidate Context**: The orchestrating workflow provides an explicit `CandidateIdentity` (e.g. `Toyota 4Runner 2020 US`) that defines the target aggregation container.
2. **Workflow Routing Context**: Caller context provides routing context for ingestion tasks, but is NOT source evidence and is NOT canonical truth.
3. **Evidence Validation**: Source evidence aggregated into the container may support, contradict, or leave caller context unverified.
4. **Routing Error vs. Evidentiary Contradiction**:
   * *Routing Error*: An input payload clearly belongs to a different ingestion task (e.g. Ford payload passed to Toyota task) → Rejected at the boundary before candidate construction.
   * *Evidentiary Contradiction*: A valid normalized assertion conflicts with caller context (e.g. Context says 2020; normalized evidence says 2019) → Accepted into candidate construction, preserved in `normalized_assertions`, assigned evidence state `single_source`, flagged as context `contradicted`, and triggers top-level human review (`requires_human_review = True`).

## 7. Candidate Context vs. Source Evidence Rules

* `CandidateIdentity.model_year = 2020` does NOT produce a synthetic source assertion or normalized interpretation for 2020.
* Caller context does NOT count as an evidentiary lineage and CANNOT corroborate source evidence.
* If caller context says 2020 and a single source assertion says 2019:
  * `candidate_identity.model_year` remains `2020` as workflow context.
  * `normalized_assertions` retains the 2019 interpretation.
  * `attribute_provenance["model_year"]` references the 2019 interpretation.
  * Evidence `reconciliation_state` for `model_year` is `single_source`.
  * Candidate-context verification state is `contradicted`.

## 8. Evidence Reconciliation vs. Candidate-Context Verification

RA-016 strictly separates evidence reconciliation from candidate-context verification:

```text
                                 ┌──────────────────────────────────────────────────────────┐
                                 │                Candidate Construction                    │
                                 └────────────────────────────┬─────────────────────────────┘
                                                              │
                     ┌────────────────────────────────────────┴────────────────────────────────────────┐
                     ▼                                                                                 ▼
   ┌───────────────────────────────────┐                                             ┌───────────────────────────────────┐
   │    Evidence Reconciliation State  │                                             │    Candidate-Context Verification │
   │    (Evidence vs. Evidence)        │                                             │    (Context vs. Evidence)         │
   ├───────────────────────────────────┤                                             ├───────────────────────────────────┤
   │ Evaluates independent source      │                                             │ Evaluates whether source evidence │
   │ lineages against each other.      │                                             │ supports caller CandidateIdentity.│
   │                                   │                                             │                                   │
   │ States:                           │                                             │ Conceptual States:                │
   │ - single_source                   │                                             │ - supported                       │
   │ - corroborated                    │                                             │ - partially_supported             │
   │ - conflicting                     │                                             │ - contradicted                    │
   │ - ambiguous                       │                                             │ - unverified                      │
   │ - incomplete                      │                                             │                                   │
   └───────────────────────────────────┘                                             └───────────────────────────────────┘
```

* **Separation Rule**: `reconciliation_state = "conflicting"` is reserved exclusively for evidence-to-evidence conflicts where two or more independent evidence lineages disagree. Candidate-context contradiction does not alter or manufacture an evidence reconciliation state; evidence state is determined independently from applicable evidence lineages, while context contradiction triggers top-level human review.

## 9. Candidate-Context Verification States & Review Workflow

### Context Verification States
* **`supported`**: Mapped normalized evidence agrees with the relevant caller `CandidateIdentity` dimension.
* **`partially_supported`**: Some caller identity dimensions are supported by evidence; others remain unverified.
* **`contradicted`**: Applicable mapped normalized evidence explicitly disagrees with a caller identity dimension.
* **`unverified`**: No normalized evidence currently asserts a value for a caller identity dimension.

### Review Workflow Policy
* **Triggers for `requires_human_review = True` and `review_workflow_disposition = "pending_review"`**:
  1. Evidence-to-evidence conflict (`reconciliation_state = "conflicting"`).
  2. Evidence ambiguity (`reconciliation_state = "ambiguous"`).
  3. Candidate-context contradiction (context verification state = `contradicted`).
* **Triggers for `requires_human_review = False` and `review_workflow_disposition = "not_required"`**:
  1. Single source evidence (`single_source`).
  2. Corroborated evidence (`corroborated`).
  3. Incomplete evidence (`incomplete` alone does NOT trigger human review).

## 10. Evidence Lineage, Independence & Corroboration Rules

1. **Lineage-Based Corroboration**: A projected candidate value is `corroborated` ONLY when two or more independent evidence lineages support the same normalized semantic value.
2. **Independence Standard**: Different `source_id` values (e.g. `nhtsa_vpic` vs `epa_fueleconomy`) represent independent evidence lineages for initial implementation.
3. **Repeated Retrieval Rule**: Repeated acquisition of the same source record (`same source_id + same native_record_id`), regardless of `retrieved_at` timestamp, represents the **same evidence lineage** and yields `single_source`.
4. **One-to-Many Normalization**: Multiple interpretations derived from a single `SourceAssertion` (e.g. EPA `drive_descriptor` → `generic_drive_classification` & `drivetrain_architecture`) represent **one evidence lineage**.
5. **Deduplication vs. Preservation**: Artifact-level deduplication by evidence lineage is performed for evidence-state calculation, but all underlying `NormalizedInterpretation` objects are retained in `normalized_assertions`.

## 11. Candidate Projection & Conflict Rules

1. **Projection Authority**: Candidate attributes and `factory_technical_features` are projected ONLY from approved mapped `NormalizedInterpretation` objects.
2. **No Tier 1 Normalization Bypass**: Raw `SourceAssertion` strings are never scanned or parsed during candidate construction.
3. **No Winner Selection Under Conflict**: When independent evidence lineages conflict on a scalar technical field (e.g. cylinders `6` vs `4`):
   * The scalar field in `normalized_technical_details` (e.g. `engine.cylinders`) is left **UNSET (`None`)**.
   * ALL conflicting `NormalizedInterpretation` objects are retained in `normalized_assertions`.
   * ALL interpretation IDs are retained in `attribute_provenance["engine_cylinders"]`.
   * `reconciliation_state` in `attribute_states["engine_cylinders"]` is set to `"conflicting"`.
   * `review_workflow_disposition = "pending_review"`, `requires_human_review = True`.

## 12. Comprehensive Evidence-State Matrix

| Scenario | Input Interpretations & Lineages | Projected Value | `attribute_provenance` | Evidence `reconciliation_state` | Context Verification State | `review_disposition` | `requires_human_review` |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **1. Single Mapped Interpretation** | 1 mapped (NHTSA `make: "Toyota"`) | `"Toyota"` | `["interp_nhtsa_make_01"]` | `single_source` | `supported` | `not_required` | `False` |
| **2. Independent Corroboration** | 2 mapped (NHTSA + EPA `make: "Toyota"`) | `"Toyota"` | `["interp_nhtsa_01", "interp_epa_01"]` | `corroborated` | `supported` | `not_required` | `False` |
| **3. Repeated Acquisition / Same Lineage** | 2 identical (Same EPA record twice) | `"Toyota"` | `["interp_epa1_01", "interp_epa2_01"]` | `single_source` | `supported` | `not_required` | `False` |
| **4. Independent Evidence Conflict** | 2 mapped (Source A `cyl: 6` vs Source B `cyl: 4`) | `None` (Unset) | `["interp_srcA_cyl", "interp_srcB_cyl"]` | `conflicting` | `supported` | `pending_review` | `True` |
| **5. Specificity: Independent / Same Value** | Model-wide `4WD` (Src A) + Trim `4WD` (Src B) | `"4WD"` | `["interp_srcA_drive", "interp_srcB_drive"]` | `corroborated` | `supported` | `not_required` | `False` |
| **6. Specificity: Same Lineage / Same Value** | Model-wide `4WD` + Trim `4WD` (Same Src A) | `"4WD"` | `["interp_srcA1_drive", "interp_srcA2_drive"]` | `single_source` | `supported` | `not_required` | `False` |
| **7. Specificity: Independent / Conflict** | Model-wide `4WD` (Src A) vs Trim `2WD` (Src B) | `None` (Unset) | `["interp_srcA_drive", "interp_srcB_drive"]` | `conflicting` | `supported` | `pending_review` | `True` |
| **8. Clearly Non-Applicable Evidence** | Assertion for 2010 model year | *(Excluded)* | *(Not in provenance)* | *(N/A)* | *(N/A)* | *(N/A)* | `False` |
| **9. Unresolved Applicability** | Trim assertion with unverified grade match | `None` (Unset) | `["interp_trim_drive"]` | `ambiguous` | `unverified` | `pending_review` | `True` |
| **10. Unmapped Case A (Known Concept)** | `drive_descriptor: "Quad-Drive"` (`unmapped`) | `None` (Unset) | `["interp_unmapped_drive"]` | `incomplete` | `unverified` | `not_required` | `False` |
| **11. Case B (Unknown Concept)** | *(No interpretation emitted by RA-015)* | *(Unset)* | *(Not in provenance)* | *(N/A)* | *(N/A)* | `not_required` | `False` |
| **12. Parsing Failure** | `model_year: "invalid"` (`unmapped`) | `None` (Unset) | `["interp_unmapped_year"]` | `incomplete` | `unverified` | `not_required` | `False` |
| **13. No Evidence for Optional Field** | No assertion for `horsepower` | `None` (Unset) | *(Not in provenance)* | *(N/A)* | *(N/A)* | `not_required` | `False` |
| **14. Context Contradiction (1 Lineage)** | Context `2020`; Evidence `2019` (Src A) | `2019` | `["interp_srcA_year"]` | `single_source` | **`contradicted`** | `pending_review` | `True` |
| **15. Context Contradiction + Conflict** | Context `2020`; Src A `2020`; Src B `2019` | `None` (Unset) | `["interp_srcA_yr", "interp_srcB_yr"]` | **`conflicting`** | **`contradicted`** | `pending_review` | `True` |

## 13. Applicability & Specificity Rules

1. Applicability is evaluated against caller candidate context prior to evidence-state assignment.
2. Non-applicable evidence is excluded from candidate projection.
3. Specificity does NOT dictate precedence. Applicable disagreeing evidence from independent lineages yields `reconciliation_state = "conflicting"`.

## 14. Provenance Model & Transitive Traceability

`Candidate Attribute Key` → `attribute_provenance[key]` → `NormalizedInterpretation.interpretation_id` → `source_assertion_ref` → `SourceAssertion.assertion_id` → `SourceMetadata`.

Interpretation count does NOT equal evidence lineage count. Multiple interpretations derived from one source assertion represent one lineage (`single_source`).

## 15. Candidate Reference & Determinism

1. **Candidate Reference Semantics**: `candidate_reference` is a transient, opaque workflow identifier (e.g. `"cand_toyota_4runner_2020_us_001"`). It MUST NOT be derived semantically from vehicle identity fields.
2. **Semantic Determinism**: Identical semantic inputs produce identical projected semantic content, evidence states, provenance maps, and deterministic ordering. Artifact-generation metadata such as `created_at` may vary unless explicitly injected or fixed for testing.

## 16. Fifth-Generation Toyota 4Runner Stress Test

### Scenario 1: Standard 2020 4Runner Aggregation
* **Input 1 (NHTSA 2020 Toyota 4Runner)**: Emits `make: "Toyota"`, `model: "4Runner"`, `nhtsa_make_id: 448`, `nhtsa_model_id: 11982`.
* **Input 2 (EPA 2020 Toyota 4Runner 4WD)**: Emits `model_year: 2020`, `make: "Toyota"`, `generic_drive_classification: "4WD"`, `drivetrain_architecture: "part_time_4wd"`, `engine_displacement_liters: 4.0L`, `engine_cylinders: 6`, `city_mpg_epa_rating: 16`, `highway_mpg_epa_rating: 19`, and unmapped Case A interpretations for composite `model` (`"4Runner 4WD"`), `transmission_descriptor`, `vehicle_class`, and `engine_description`.
* **Caller Context**: `CandidateIdentity(manufacturer_name="Toyota", vehicle_model_name="4Runner", model_year=2020, market="US")`.
* **Result**: `make` is `corroborated`; `model` is `single_source` (from NHTSA); EPA composite `"4Runner 4WD"` is unmapped Case A; `normalized_technical_details.transmission` is `None`; `factory_technical_features` is `[]`; `requires_human_review = False`.

### Scenario 2: Candidate-Context Contradiction (Single Evidence Lineage)
* **Caller Context**: `CandidateIdentity(manufacturer_name="Toyota", vehicle_model_name="4Runner", model_year=2020, market="US")`.
* **Single Source Evidence Lineage**: Emits `model_year: 2019`.
* **Result**: `model_year` evidence state is **`single_source`** (for 2019); candidate context is **`contradicted`**; `reconciliation_notes` records `"Context contradiction detected: model_year context 2020 vs evidence 2019"`; `requires_human_review = True`, `review_workflow_disposition = "pending_review"`.

### Scenario 3: True Evidence-to-Evidence Conflict + Context Contradiction
* **Caller Context**: `CandidateIdentity(manufacturer_name="Toyota", vehicle_model_name="4Runner", model_year=2020, market="US")`.
* **Source A Evidence Lineage**: Emits `model_year: 2020`.
* **Source B Evidence Lineage**: Emits `model_year: 2019`.
* **Result**: `model_year` evidence state is **`conflicting`**; projected scalar field is `None`; context is **`contradicted`** by Source B; `requires_human_review = True`, `review_workflow_disposition = "pending_review"`.

## 17. Factory Technical Features & Package Boundary

Populated ONLY from mapped feature `NormalizedInterpretation` objects. Raw Tier 1 string scanning is strictly prohibited. In RA-017, `factory_technical_features` will be `[]` because RA-015 normalization left feature strings unmapped.

## 18. Contract Gap Analysis & Outcome B Conclusion

| Requirement | Contract Support Status | Implementation Convention / Notes |
| :--- | :--- | :--- |
| **Candidate Envelope & Versioning** | **Supported as-is** | `rigarchive.candidate_configuration.v1` |
| **Candidate Identity Header** | **Supported as-is** | `CandidateIdentity` struct |
| **Source Native Identifiers** | **Supported as-is** | `source_configuration_identities: List[SourceConfigurationIdentity]` |
| **Normalized Assertions Preservation** | **Supported as-is** | `normalized_assertions: List[NormalizedInterpretation]` |
| **Multi-Source Attribute Provenance** | **Supported as-is** | `attribute_provenance: Dict[str, List[str]]` |
| **Conflicting Scalar Technical Fields** | **Supported with convention** | Field left `None`; all conflicting interpretations retained in `normalized_assertions` and `attribute_provenance` |
| **Evidence Reconciliation States** | **Supported as-is** | `reconciliation_and_review.attribute_states` |
| **Context Contradiction Review Signal** | **Supported with convention** | `requires_human_review = True`, `review_workflow_disposition = "pending_review"`, notes in `reconciliation_notes` |
| **Formal Context-Verification Persistence** | **Deferred** | Operating as runtime construction validation; formal enum serialization deferred |

**Conclusion (Outcome B)**: Supported with implementation conventions. **Zero contract modifications required** for RA-017.

## 19. Approved Architectural Decisions

1. **Hybrid Caller-Context + Evidence Grouping Model**: Caller `CandidateIdentity` defines workflow context; source evidence supports, contradicts, or unverifies context.
2. **Separation of Evidence Reconciliation from Context Verification**: `reconciliation_state = "conflicting"` is reserved for evidence-to-evidence conflicts. Candidate-context contradiction does not alter or manufacture an evidence reconciliation state; the evidence state is determined independently from the applicable evidence lineages, while context contradiction triggers top-level human review.
3. **Lineage-Based Evidence Independence**: Corroboration requires 2+ independent evidence lineages. Repeated retrieval of the same source record yields `single_source`.
4. **Consistency of `incomplete` Review Policy**: `incomplete` alone does NOT trigger human review (`requires_human_review = False`). Automatic review is reserved for `conflicting`, `ambiguous`, and `contradicted` states.
5. **Evidence-Aware Projection Without Winner Selection**: Under evidence conflict, scalar fields are left unset while all conflicting interpretations are preserved.
6. **No Tier 1 Normalization Bypass**: Candidate attributes projected strictly from mapped `NormalizedInterpretation` objects.
7. **Applicability Prior to Conflict Detection**: Non-applicable evidence excluded from candidate projection. Specificity does NOT dictate precedence.
8. **Transient Non-Semantic `candidate_reference`**: Opaque, non-semantic workflow identifier.
9. **Semantic Determinism**: Identical semantic inputs produce identical projected semantic content, evidence states, provenance maps, and deterministic ordering. Artifact-generation metadata such as `created_at` may vary unless explicitly injected or fixed for testing.
10. **Separation of Construction from Matching & Import**: Transient candidate construction occurs without canonical matching or database writes.

## 20. Complete Deferred Decision Boundary

1. Formal serialized candidate-context verification enum/field model.
2. Same-source multiple-record evidence independence criteria.
3. Attribute-criticality / mandatory-field human review policy.
4. Canonical Reference matching algorithms and key strategies.
5. Canonical source precedence hierarchy.
6. Final cross-source conflict resolution & human adjudication UI/workflows.
7. Persistent database staging models and migration schemas.
8. Permanent DB ORM schemas for packages, options, and suspension features.
9. Automated candidate splitting for multi-configuration payloads.
10. Historical candidate document conversion and remapping strategies.
11. Production candidate persistence directory tree on disk.
12. Background job scheduling and ingestion orchestration.

## 21. Recommended Next Milestone

**RA-017 — Candidate Configuration Construction & Aggregation Implementation**

* **Status**: **Implementation-Ready**.
* **Scope**: Implement pure Python candidate construction engine in `reference/ingestion/candidate/` (or `construction.py`), implementing the hybrid grouping model, candidate attribute projection, independent evidence lineage deduplication, evidence vs. context state separation, and deterministic serialization. Validate offline against controlled NHTSA/EPA fixtures and synthetic contradiction tests. Zero ORM changes, zero live acquisition, zero canonical matching, zero contract modifications.
