# RA-020 — Trim/Grade & Market Applicability Source and Normalization Architecture

- **Status**: Approved Architecture  
- **Date**: 2026-08-15  

## 1. Purpose & Executive Summary

This architecture design document establishes the authoritative source, normalization, and provenance architecture for acquiring and evaluating manufacturer grade/trim taxonomy and commercial market applicability within RigArchive's ingestion pipeline.

RA-011 through RA-019 established an end-to-end ingestion and promotion pipeline:

```text
External Source Acquisition
    ↓
SourceAssertionSet (Tier 1)
    ↓
Source Assertion Normalization (RA-015)
    ↓
CandidateConfigurationDocument (RA-017)
    ↓
Canonical Import Planning (RA-019)
    ↓
Create-Only VehicleDefinition Execution (RA-019)
```

RA-019 proved that this pipeline can safely promote eligible candidate configurations into canonical database records (`VehicleDefinition`). However, current production public sources (NHTSA vPIC, EPA FuelEconomy) omit mapped `trim` and `market` evidence. Under the Evidence Trust Boundary established in RA-016 and RA-018, real production candidates currently stop at `ImportEligibilityStatus.REQUIRES_REVIEW` and perform zero database writes.

RA-020 defines the architecture required to solve this production gap cleanly, introducing manufacturer specification evidence, formalizing trim and market semantics, enforcing the Source-Independence Test against context laundering, prohibiting unsupported Cartesian candidate joins, and establishing the implementation scope for `RA-021`.

## 2. Governing Authority & Related Artifacts

Governed by the RigArchive authority order:

1. Current task / architecture specification
2. Architectural Decision Records ([ADR-0001](file:///Users/esse/dev/Rigarchive/docs/architecture/ADR/ADR-0001-Entity-Identity-Strategy.md) through [ADR-0005](file:///Users/esse/dev/Rigarchive/docs/architecture/ADR/ADR-0005-Manufacturer-Grade-Taxonomy-Market-Applicability-Normalization.md))
3. Latest [`docs/implementation/CURRENT_STATE.md`](file:///Users/esse/dev/Rigarchive/docs/implementation/CURRENT_STATE.md)
4. Engineering Handbook
5. Project Blueprint

Operates directly over design documents [RA-010](file:///Users/esse/dev/Rigarchive/docs/architecture/designs/RA-010-Reference-Ingestion-Source-Mapping-Architecture.md), [RA-011](file:///Users/esse/dev/Rigarchive/docs/architecture/designs/RA-011-Ingestion-Schema-Intermediate-Serialization-Design.md), [RA-014](file:///Users/esse/dev/Rigarchive/docs/architecture/designs/RA-014-Source-Assertion-Normalization-Mapping-Architecture.md), [RA-016](file:///Users/esse/dev/Rigarchive/docs/architecture/designs/RA-016-Candidate-Configuration-Construction-Aggregation-Architecture.md), and [RA-018](file:///Users/esse/dev/Rigarchive/docs/architecture/designs/RA-018-Canonical-Reference-Matching-Import-Architecture.md).

## 3. Current Production Source Capability Audit

### 3.1 NHTSA vPIC Capability & Endpoints
* **Current Endpoint**: `/vehicles/GetModelsForMakeYear/make/{make}/modelyear/{year}`
  * *Returns*: `Make_ID`, `Make_Name`, `Model_ID`, `Model_Name`.
  * *Limitation*: Exposes zero trim, grade, series, or market information.
* **Alternative vPIC Endpoints Reassessed**:
  * `/vehicles/DecodeVinValuesBatch/` / `/vehicles/DecodeVin/{vin}`: Exposes `Series`, `Series2`, `Trim`, `BodyClass`, `DriveType`, `DisplacementL`, `EngineCylinders`. However, trim data is populated by manufacturers with varying consistency (often returning empty strings or internal series code strings like `BU4REV` or `GRN285L`). It represents NHTSA regulatory VIN taxonomy rather than first-party manufacturer grade hierarchy.
  * `/vehicles/GetCanadianVehicleSpecifications`: Exposes Canadian CMVSS specification data, explicitly scoped to Canadian regulatory jurisdiction (`CA`).

### 3.2 EPA FuelEconomy.gov Capability & Endpoints
* **Endpoints**: `/ws/rest/vehicle/menu/model?year={year}&make={make}` and `/ws/rest/vehicle/{id}`.
* **Empirical 2020 Toyota 4Runner Payloads**:
  * Models listed: `"4Runner 2WD"` and `"4Runner 4WD"`.
  * Vehicle option text:
    * ID `41939`: `Auto (S5), 6 cyl, 4.0 L, 2WD`
    * ID `41940`: `Auto (S5), 6 cyl, 4.0 L, Part-time 4WD`
    * ID `41942`: `Auto (S5), 6 cyl, 4.0 L, AWD`
* **Findings & Limitations**:
  * EPA records provide explicit powertrain, drive classification (`Part-time 4WD` vs `AWD` vs `2WD`), displacement (`4.0L`), cylinders (`6`), and fuel economy ratings.
  * EPA records provide **zero trim/grade labels** for 4Runner (`SR5`, `TRD Off-Road`, `Limited` do not exist in EPA 4Runner records).
  * Separate EPA vehicle IDs correlate to powertrain/drivetrain certification test groups, NOT factory grade/trim levels.

## 4. Manufacturer Evidence Architecture

First-party manufacturer evidence (official product press kits, e-brochures, specification sheets, model-year product guides, and ordering guides) is the primary authoritative source for factory configuration identity.

### 4.1 Direct Configuration Establishment
An authoritative manufacturer specification source may itself provide enough linked evidence to establish:

$$\text{Manufacturer Spec} \longrightarrow [\text{make}, \text{model}, \text{model\_year}, \text{grade/trim}, \text{drivetrain}, \text{engine}, \text{market}]$$

For example, an official Toyota specification artifact for Model Code `8666` establishes:
* Make: `Toyota`
* Model: `4Runner`
* Model Year: `2020`
* Trim / Grade: `SR5`
* Drivetrain: `Part-Time 4WD`
* Engine: `4.0L V6`
* Market: `US`

In such cases, RigArchive does **NOT** require EPA evidence to manufacture the configuration identity. EPA/NHTSA evidence provides independent corroboration for technical attributes where an evidence-backed correspondence exists.

## 5. Trim / Grade Semantics & Taxonomy Disambiguation

### 5.1 Concept Identifier
The normalized target attribute key **`trim`** is retained for contract stability across `CandidateConfigurationDocument`, `RA-019`, and `VehicleDefinition.trim_name`.

### 5.2 Canonical Ingestion Definition
`trim` is defined precisely as:
> **Manufacturer-Recognized Factory Grade/Trim Identity**  
> The high-level factory model line or grade identity recognized by the vehicle manufacturer in its official product catalog for that model year and market (e.g., `SR5`, `SR5 Premium`, `TRD Off-Road`, `Limited`).

### 5.3 Taxonomy Disambiguation Hierarchy
Ingestion must disambiguate source strings across eight distinct taxonomy levels:

```text
Raw Source String (e.g., "TRD OFF-ROAD PREMIUM")
    ↓
1. Raw Source Text                (Unnormalized string in assertion)
2. Manufacturer Factory Grade    (e.g., SR5, TRD Off-Road, Limited)
3. Sub-Grade                     (e.g., SR5 Premium, TRD Off-Road Premium)
4. Factory Special Edition       (e.g., Venture Special Edition, Nightshade Special Edition)
5. Option Package                (e.g., Premium Audio Package — NOT a trim)
6. Accessory / Dealer Package    (e.g., XP Predator Package — NOT a trim)
7. Individual Option             (e.g., Third-Row Seating — NOT a trim)
8. Unresolved Classification     (Ambiguous text requiring human review)
```

Raw string inequality never establishes canonical grade identity by itself. First-party manufacturer taxonomy evidence governs classification.

## 6. Market Applicability Semantics & Source-Independence Test

### 6.1 Canonical Market Definition
`VehicleDefinition.market` is defined precisely as:
> **Manufacturer Commercial Sales Market**  
> The intended geographic sales market (`US`, `CA`, `OT`) for which a factory vehicle configuration was engineered, cataloged, and offered to commercial buyers by the manufacturer.

Regulatory jurisdiction (e.g. EPA emissions certification or CMVSS safety compliance) provides supporting regulatory evidence, but regulatory jurisdiction is NOT semantically identical to commercial sales market:

$$\text{Regulatory Jurisdiction} \neq \text{Commercial Sales Market}$$

### 6.2 The Source-Independence Test
To prevent "context laundering" (where caller request context is copied into provenance and promoted into canonical evidence), RA-020 formalizes the **Source-Independence Test**:

> **Source-Independence Test**  
> A market value may become normalized evidence **ONLY** where the source artifact or acquisition definition independently establishes that applicability scope.  
> If the value merely repeats caller request parameters or adapter request settings (`target_context`), it **MUST REMAIN CONTEXT** and MUST NOT be laundered into normalized evidence.

The following context laundering path is strictly prohibited:

$$\text{Caller Market} \xrightarrow{\text{Request}} \text{target\_context} \xrightarrow{\text{Prohibited}} \text{NormalizedInterpretation} \xrightarrow{\text{Prohibited}} \text{Canonical VehicleDefinition.market}$$

### 6.3 Proposed Source Applicability Contract Extension
For future acquisition adapters, source applicability scope must be represented using explicit provenance metadata distinct from caller request context:

```python
@dataclass
class SourceApplicability:
    market: Optional[str] = None               # e.g., "US", "CA", "OT"
    applicability_basis: Optional[str] = None   # e.g., "first_party_publisher_scope", "regulatory_jurisdiction"
    publisher_jurisdiction: Optional[str] = None
```

Attached as an optional field `source_applicability` on `SourceMetadata`. Source applicability metadata remains provenance and must pass through assertion extraction and normalization mapping before canonical promotion.

## 7. Controlled 2020 Toyota 4Runner Empirical Study

Based on official Toyota Motor Sales, U.S.A., Inc. primary product press kits and technical specification matrices (`pressroom.toyota.com`):

* **Model Year**: 2020
* **Market**: United States (`US`)
* **Toyota Terminology**: Toyota officially classifies model lines as **"Grades"**.
* **Verified 8 U.S. Factory Grades & Order Model Codes**:

| Grade Name | Model Code (4x2) | Model Code (4x4) | Drivetrain Availability |
| :--- | :--- | :--- | :--- |
| **SR5** | 8664 | 8666 | 2WD / Part-Time 4WD |
| **SR5 Premium** | 8670 | 8672 | 2WD / Part-Time 4WD |
| **TRD Off-Road** | — | 8674 | Part-Time 4WD Only |
| **TRD Off-Road Premium** | — | 8676 | Part-Time 4WD Only |
| **Venture Special Edition** | — | 8682 | Part-Time 4WD Only |
| **Limited** | 8686 | 8688 | 2WD / Full-Time 4WD (AWD) |
| **Nightshade Special Edition** | 8690 | 8692 | 2WD / Full-Time 4WD (AWD) |
| **TRD Pro** | — | 8680 | Part-Time 4WD Only |

### 7.1 Source-Native Configuration Identity
Toyota's 4-digit order model codes (e.g. `8666`) provide strong source-native configuration identity evidence. They populate `SourceConfigurationIdentity` as source-native identity evidence:

$$\text{Toyota Model Code } 8666 \equiv \text{SourceConfigurationIdentity ("toyota\_usa", "8666")}$$

Source-native model codes MUST NOT be directly promoted to RigArchive canonical entity keys.

## 8. Cross-Source Grouping & Cartesian Product Prohibition

### 8.1 Attribute Equality Join Rule
RA-020 formalizes the cross-source join rule:

> **Attribute Equality Is Not a Join Key**  
> Matching field values across independent sources (e.g., EPA `4WD` == Toyota `4WD`) does NOT, by itself, prove that records represent the same factory configuration.

Cross-source assertions may be aggregated into a single `CandidateConfigurationDocument` ONLY when an evidence-backed correspondence exists (e.g. manufacturer configuration matrix, explicit source cross-reference, or VIN pattern applicability).

### 8.2 Cartesian Product Prohibition
RigArchive MUST NOT generate unsupported Cartesian combinations from independently observed dimensions:

$$8 \text{ Manufacturer Grades} \times 3 \text{ EPA Drivetrain Records} \neq 24 \text{ Candidate VehicleDefinitions}$$

Every candidate configuration must be supported by evidence that those attributes coexist in that factory configuration.

## 9. Preserved-Only Candidate Projection Decision

**Decision: Trim and market remain PRESERVED-ONLY normalized assertions.**

* **Rationale**: `plan_candidate_import` (RA-019) extracts mapped `trim` and `market` directly from `candidate.normalized_assertions` and verifies set-based consistency (`len(distinct) > 1` flags `FLAG_REVIEW`). Real canonical `CREATE` in RA-021 is 100% reachable with `trim` and `market` remaining preserved normalized assertions in `normalized_assertions`.
* **Deferred Action**: Promoting `trim` and `market` to Category A projected scalar fields in `CandidateConfigurationDocument` is deferred until review UX or adjudication tooling demands explicit `attribute_states` visualization.

## 10. Reusable Manufacturer Acquisition Abstraction

Rather than committing the architecture to a single hardcoded `ToyotaManufacturerAdapter`, define a reusable ingestion abstraction:

```text
reference/ingestion/acquisition/
├── base.py                   # BaseSourceAdapter
├── manufacturer.py           # ManufacturerSpecificationAdapter (Reusable dataset reader)
├── epa.py                    # EPAAdapter
└── nhtsa.py                  # NHTSAAdapter

reference/ingestion/normalization/rules/
├── epa_rules.py
├── nhtsa_rules.py
└── toyota_rules.py           # Toyota-specific mapping & grade taxonomy rules
```

This decouples generic acquisition and serialization mechanics from manufacturer-specific mapping and taxonomy rules.

## 11. Production Automation Gap Analysis

To enable real production candidate promotion without synthetic test fixtures, five specific links must be established:

1. **Source Applicability Contract**: Structured provenance semantics (`source_applicability`) for independently established commercial market applicability.
2. **Manufacturer Evidence Acquisition**: Structured acquisition of authoritative manufacturer grade and configuration evidence.
3. **Manufacturer Normalization Rules**: Mapped normalized interpretations for `trim` and `market` (plus applicable technical concepts).
4. **Configuration Relationship Preservation**: Preserving source-native model codes and grade-to-drivetrain relationships so candidate construction does not manufacture unsupported combinations.
5. **Aggregation Validation**: Verifying that candidate construction produces fully evidenced candidates carrying mapped `trim` and `market` assertions.

## 12. Proposed Next Milestone Scope (RA-021)

* **Title**: `RA-021 — Manufacturer Specification Evidence Acquisition & Normalization Implementation`
* **Proposed Scope**:
  1. Implement explicit `SourceApplicability` provenance metadata structure in `reference/ingestion/contracts.py`.
  2. Implement a controlled reusable `ManufacturerSpecificationAdapter` in `reference/ingestion/acquisition/`.
  3. Introduce a controlled authoritative 2020 Toyota 4Runner manufacturer specification fixture (`reference/tests/fixtures/acquisition/toyota/2020_4runner_specs.json`) derived from documented first-party evidence.
  4. Emit `SourceAssertionSet` artifacts preserving manufacturer source identity, model codes, factory grades, drivetrain applicability, and U.S. commercial market scope.
  5. Normalize manufacturer evidence through Tier 2 architecture, including mapped `trim` and `market` assertions in `reference/ingestion/normalization/rules/toyota_rules.py`.
  6. Verify deterministic serialization, provenance preservation, and `SourceConfigurationIdentity` behavior.
  7. Inspect resulting candidate configuration documents and verify downstream promotion through RA-019 `plan_candidate_import` and `execute_candidate_import`.
* **Explicit Exclusions**:
  * Zero Django model schema changes.
  * Zero migrations.
  * Zero automated updates or deletes of existing canonical database records.
  * Zero parent entity auto-creation (`Manufacturer`, `VehicleModel`, `Generation`).
  * Zero fuzzy or attribute-equality source joining.
  * Zero unsupported Cartesian candidate generation.

## 13. Explicit Non-Goals

* No broad multi-manufacturer web scraping infrastructure.
* No modification of existing `VehicleDefinition` database models or migrations.
* No automated creation of dealer or distributor accessory packages as canonical Reference entities.
* No context laundering of caller request parameters into canonical facts.
* No global source precedence or winner selection logic.
