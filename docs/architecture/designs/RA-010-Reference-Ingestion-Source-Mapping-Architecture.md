# RA-010 — Reference Data Ingestion Source & Mapping Architecture

> [!NOTE]
> **Status**: Architectural & Research Design Document  
> **Authority**: Governed by the Project Blueprint and Engineering Handbook. Positioned at Level 4 in the project authority hierarchy (below Current Task, ADRs, and `CURRENT_STATE.md`).  
> **Scope**: Conceptual, technical, and mapping specification for external source acquisition, non-lossy normalization, cross-source reconciliation, candidate configuration generation, and canonical `VehicleDefinition` mapping. Includes an empirical 4-year study of the Fifth-Generation Toyota 4Runner (US market, 2010–2024).

---

## Executive Summary

The RigArchive Reference Domain serves as the canonical factory configuration baseline for supported vehicles:
`Manufacturer → VehicleModel → Generation → VehicleDefinition`

Populating canonical Reference records manually via Django Admin is unsustainable at scale. However, importing external data directly into canonical Reference records creates severe risks: corrupting canonical identity, losing technical specificity, misinterpreting commercial presentation strings, or violating external source licensing constraints.

RA-010 establishes the architecture for a multi-stage reference ingestion pipeline that decouples **Source Acquisition** from **Canonical Reference Import**.

```text
External Sources
      ↓
Acquisition
      ↓
Preserved Source Assertions / Raw Source Material
      ↓
Normalization
      ↓
Candidate Configurations
      ↓
Cross-Source Reconciliation / Validation
      ↓
Human Review where required
      ↓
Approved Canonical Import
      ↓
Reference Domain
```

### Key Architectural Principles Established in RA-010
1. **Decoupled Acquisition & Import**: External source assertions represent statements about real-world vehicles; they are never canonical Reference records until normalized, reconciled, and validated.
2. **Manufacturer-Taxonomy Rule for Trim Identity**: RigArchive follows the manufacturer's own market-specific configuration taxonomy for trim/grade identity. When a manufacturer presents a configuration as a distinct trim/grade in official market material (including sub-grades like `SR5 Premium` or `Trail Premium`), RigArchive preserves that distinct trim identity. Packages and individual options that the manufacturer does not recognize as distinct trims/grades do not independently create separate `VehicleDefinition` records.
3. **Non-Lossy Specificity Preservation**: Technical specificity present in source material (e.g. full-time 4WD with Torsen center differential) MUST NOT be collapsed or destroyed during normalization, even if current public browsing or primary model choice fields expose a simpler classification (e.g. `4WD`).
4. **Multi-Level Drivetrain Normalization**: Drivetrain information is modeled across 7 conceptual technical dimensions: Drive System, Architecture, Components, Operating Modes, Mode-Specific States/Properties, System Capabilities, and Manufacturer Terminology.
5. **Attribute-Level Precedence & Specificity Rules**: Source reconciliation operates per-attribute rather than per-file. A generic source assertion (e.g., "4WD") cannot overwrite a reliable, higher-specificity assertion (e.g., "Full-time 4WD with Torsen center differential").
6. **Categorical Ambiguity Escalation**: Unresolved source conflicts or mapping uncertainties produce reviewable candidate records rather than invented certainty.

---

## 1. Purpose

This document defines the architecture, conceptual data structures, normalization pipelines, reconciliation logic, and provenance requirements for acquiring external vehicle specification data and mapping it into candidate configurations and canonical RigArchive Reference records.

It uses the **Fifth-Generation Toyota 4Runner (US Market, Model Years 2010–2024)**—focusing on representative model years **2010, 2015, 2020, and 2024**—as an empirical test case to expose configuration edge cases before designing a multi-manufacturer ingestion engine.

---

## 2. Governing Authority & Applicable Existing Architecture

This architectural proposal operates under the established project authority hierarchy:
1. Current approved implementation task
2. Architectural Decision Records ([ADR-0001](file:///Users/esse/dev/Rigarchive/docs/architecture/ADR/ADR-0001-Entity-Identity-Strategy.md), [ADR-0002](file:///Users/esse/dev/Rigarchive/docs/architecture/ADR/ADR-0002-Immutable-Automatic-Slugs.md), [ADR-0003](file:///Users/esse/dev/Rigarchive/docs/architecture/ADR/ADR-0003-Core-Infrastructure.md))
3. [`docs/implementation/CURRENT_STATE.md`](file:///Users/esse/dev/Rigarchive/docs/implementation/CURRENT_STATE.md)
4. **Applicable approved architecture/design documents** ([RA-006](file:///Users/esse/dev/Rigarchive/docs/architecture/designs/RA-006-Observation-Foundation-Architecture.md), [RA-008](file:///Users/esse/dev/Rigarchive/docs/architecture/designs/RA-008-Development-Data-Preservation-Architecture.md), and RA-010 once approved)
5. Engineering Handbook
6. Project Blueprint

`GEMINI.md` provides operational guidance for agent execution and is not architectural authority.

---

## 3. Current Reference Implementation Findings

Inspection of the repository implementation establishes:
* **Reference Hierarchy**: Implemented in [`reference/models.py`](file:///Users/esse/dev/Rigarchive/reference/models.py):
  * [`Manufacturer`](file:///Users/esse/dev/Rigarchive/reference/models.py#L9): `name`, `slug`, `country_code`, `is_active`.
  * [`VehicleModel`](file:///Users/esse/dev/Rigarchive/reference/models.py#L59): `manufacturer` (FK), `name`, `slug`, `is_active`.
  * [`Generation`](file:///Users/esse/dev/Rigarchive/reference/models.py#L115): `vehicle_model` (FK), `name`, `slug`, `generation_number`, `start_year`, `end_year`, `notes`, `is_active`.
  * [`VehicleDefinition`](file:///Users/esse/dev/Rigarchive/reference/models.py#L209): `generation` (FK), `model_year`, `trim_name`, `engine_name`, `drivetrain` (`2WD`, `4WD`, `AWD`, `UNK`), `market` (`US`, `CA`, `OT`), `slug`, `notes`, `is_active`.
* **Identity Mechanics**: All Reference entities inherit from [`core.models.BaseModel`](file:///Users/esse/dev/Rigarchive/core/models.py#L35), enforcing dual identity (internal integer PK `id` + immutable external UUID `uuid`) and creation/modification timestamps. Slugs are automatically generated on creation and are non-editable (`editable=False`).
* **Relational Protection**: All foreign key relationships use `on_delete=models.PROTECT`.
* **Current Schema Boundary**: `VehicleDefinition` currently represents drivetrain as a 3-character choice (`2WD`, `4WD`, `AWD`, `UNK`) and engine as free-form text (`"4.0L V6"`). The ingestion architecture MUST preserve rich nested technical attributes without forcing lossy truncation to fit today's 3-character database choice field.

---

## 4. Problem Statement & General Configuration Identity Conclusion

Building a comprehensive technical vehicle archive requires ingesting data across dozens of manufacturers and hundreds of model generations. Manual entry via Django Admin cannot support this scale.

However, external data sources expose multiple legitimate but distinct notions of vehicle configuration identity:
* **Commercial Presentation Categories**: Source strings often combine body styles, doors, and trim levels (e.g. J.D. Power's `"Utility 4D SR5 4WD V6"`).
* **Regulatory Powertrain Configurations**: EPA vehicle records focus on test weight, engine displacement, and emissions certification rather than marketing grades.
* **Coarse / Lossy Terminology**: Generic sources list `"Four Wheel Drive"` without distinguishing part-time 4WD from full-time 4WD with a locking Torsen center differential.
* **Missing Generation Boundaries**: Third-party databases rarely structure vehicles by manufacturer generation boundaries (e.g., 5th Gen 4Runner: 2010–2024).

### Central Research Conclusion
> **External sources expose multiple legitimate notions of vehicle configuration identity, including manufacturer marketing trim/grade identity, option/package configuration, mechanical configuration, regulatory powertrain configuration, and source-specific presentation categories. The ingestion layer must preserve these distinctions without prematurely treating them as interchangeable. Canonical Reference identity follows RigArchive's approved mapping semantics, with manufacturer-recognized trim taxonomy serving as the authority for trim identity.**

---

## 5. Initial Toyota 4Runner Proof-of-Concept Scope

To ensure the ingestion architecture is grounded in real engineering realities, RA-010 establishes an empirical test case:

> **Target Vehicle**: Toyota 4Runner — Fifth Generation (N280) — US Market — Model Years 2010–2024

### Focus Model Years for Ingestion Stress-Testing:
1. **2010 (Launch Year)**: Tests dual-engine availability (2.7L 2TR-FE I4 on 4x2 SR5 vs 4.0L 1GR-FE V6 on 4x2/4x4), introduction of Trail Edition with CRAWL Control/KDSS, and initial 5th Gen trim baseline.
2. **2015 (Mid-Cycle / TRD Pro Launch)**: Tests the introduction of the TRD Pro factory grade, retirement of the 2.7L I4, and preservation of sub-grades (`SR5 Premium`, `Trail Premium`).
3. **2020 (Late-Cycle Tech Update & Special Editions)**: Tests special edition trim enumeration (Venture Edition, Nightshade Edition), introduction of Toyota Safety Sense P (TSS-P), and updated infotainment specifications.
4. **2024 (Final 5th Gen Production Year)**: Tests final generation lineup maturity, TRD Sport (X-REAS suspension on SR5 body), and multi-year generation closure.

---

## 6. External Source Assessment

RA-010 evaluates four primary external source classes:

```
┌───────────────────────────────────────────────────────────────────────────┐
│                           External Source Suite                           │
├──────────────────────────────────────┬────────────────────────────────────┤
│ Source Class                         │ Primary Ingestion Utility          │
├──────────────────────────────────────┼────────────────────────────────────┤
│ A. NHTSA vPIC API                    │ Regulatory backbone, VIN structure,│
│                                      │ Make/Model/Year validation         │
│ B. EPA / FuelEconomy.gov             │ Powertrain combinations, engine    │
│                                      │ displacement, transmission, fuel   │
│ C. Toyota USA Manufacturer Material  │ Canonical generation boundaries,   │
│                                      │ exact drivetrain architecture, trim│
│ D. J.D. Power                        │ Commercial US trim enumeration,    │
│                                      │ option packages, market trim names │
└──────────────────────────────────────┴────────────────────────────────────┘
```

### A. NHTSA vPIC (Virtual Product Information Catalog)
* **Access Method**: Official Public REST API (`https://vpic.nhtsa.dot.gov/api/`) & Bulk CSV Downloads.
* **Strengths**: Authoritative US government regulatory source; free public domain data; structured JSON/XML endpoints; comprehensive VIN decoding tables.
* **Limitations**: Lacks generation awareness; trim names are inconsistent or unpopulated; drivetrain details are high-level.
* **Ingestion Role**: Regulatory backbone for validating Make, Model, Model Year, and basic VIN pattern structure.

### B. EPA / FuelEconomy.gov
* **Access Method**: Official Public REST API (`https://www.fueleconomy.gov/ws/rest/`) & Downloadable Data Files.
* **Strengths**: Complete listing of all EPA-certified US market powertrain configurations per model year; exact engine displacement, cylinders, transmission types, and drive descriptors (`4WD`, `2WD`, `AWD`).
* **Limitations**: Organized by EPA test configurations rather than consumer trim levels; does not map to marketing grades (e.g. TRD Pro vs SR5).
* **Ingestion Role**: Powertrain verification baseline (Engine + Transmission + Drivetrain combination authority).

### C. Toyota USA Manufacturer Material (Pressroom / FSM / Spec Sheets)
* **Access Method**: Technical specification sheets, pressroom archives, and Factory Service Manuals (FSM).
* **Strengths**: Highest factual authority for technical drivetrain architecture (e.g. Torsen Type-3 center diff), official generation naming, grade definitions, and mechanical option availability (KDSS, X-REAS, CRAWL Control).
* **Limitations**: Primarily HTML press releases or PDF spec sheets; requires structured extraction.
* **Ingestion Role**: Highest authority for Generation boundaries, official grade/trim names, and exact Drivetrain Architecture / Component details.

### D. J.D. Power (Commercial Specification Database)
* **Access Method**: Web product catalog pages / specification listings.
* **Strengths**: Comprehensive enumeration of consumer trim levels in the US market; captures special editions (Venture, Nightshade, TRD Pro).
* **Limitations**: Strings combine body style and trim (e.g. `"Utility 4D SR5 4WD V6"`); commercial terms of service require strict operational compliance; rate limits and scraping restrictions.
* **Ingestion Role**: Promising research and cross-corroboration source for US market trim enumeration.

---

## 7. Source Operational & Rights Suitability Assessment

Public accessibility on the web does not grant unrestricted rights to bulk-scrape or redistribute third-party compiled databases.

### Compliance & Operational Architecture
> **Prefer official structured APIs/downloads whose published access and reuse conditions support automated ingestion. Evaluate source-specific terms, access policies, automated-access restrictions, retention constraints, and redistribution considerations before enabling automated acquisition.**

1. **Public Domain Sources (NHTSA, EPA)**: Official government APIs/downloads suitable for automated pipeline integration and local assertion caching.
2. **Manufacturer Material (Toyota USA)**: Ingestion extracts normalized factual parameters (e.g. gear ratios, differential types, official grade names) rather than verbatim promotional copy.
3. **Commercial Data (J.D. Power)**: Useful as a research and cross-corroboration source for US trim enumeration. Suitability for automated production acquisition remains an unresolved research topic requiring legal/operational clearance.

---

## 8. Proposed Acquisition Architecture & Raw Retention Policy

The acquisition pipeline decouples network retrieval from domain processing.

### Raw Source Material Retention Policy
> **Preserve sufficient source material and metadata to make normalization auditable and reprocessable where source-use rights and operational constraints permit local retention.**

For structured government APIs (NHTSA, EPA), raw JSON payloads are preserved locally. For web or proprietary material where full document retention is restricted, acquisition preserves:
* Source identifier & source URL/reference;
* Retrieval timestamp;
* Source assertion or source-derived factual value (with raw source text/snippet retained where appropriate and permitted);
* Source-specific record IDs and checksums;
* Parser and normalization rule version metadata.

Raw ingestion artifacts MUST NOT be placed under `backups/` (which is reserved for RA-008/RA-009 development database preservation). Raw acquisition files belong in a dedicated, Git-ignored runtime data area (e.g., `ingestion/raw/`).

---

## 9. Normalization Architecture & Token-Based Parsing

Normalization converts raw, source-specific presentation strings into structured, canonical concepts.

### Token-Based Semantic Parsing (Avoiding Brittle Hacks)
Source presentation strings like J.D. Power's `"Utility 4D SR5 4WD V6"` or `"4D SUV Limited 4WD"` contain mixed presentation descriptors.
* **Body Descriptor Removal**: The parser isolates body prefixes (e.g. `Utility 4D`, `4D SUV`, `Sedan 4D`) using token pattern matching against a controlled vocabulary of vehicle body descriptors, rather than performing brittle literal string trimming like `remove("Utility 4D ")`.
* **Trim Extraction**: Grade tokens (SR5, Limited, TRD Pro, Trail) are identified against manufacturer-recognized trim lists for the target generation.

### Unclassified Attributes Principle
> **Unknown or not-yet-modeled factory attributes should remain preserved and explicitly unclassified rather than being forced into an incorrect existing category.**

For example, suspension features (Fox internal bypass shocks, KDSS, X-REAS) or exterior accessories (Yakima roof rack) MUST NOT be forced into drivetrain architecture fields merely to fit a compact table.

---

## 10. High-Fidelity Drivetrain Normalization Requirements

Drivetrain details MUST NOT be collapsed into a single choice field (e.g. `4WD`). The ingestion pipeline MUST capture drivetrain configuration across **7 conceptual technical dimensions**:

```
┌───────────────────────────────────────────────────────────────────────────┐
│                   7-Dimension Drivetrain Normalization                    │
├──────────────────────────┬────────────────────────────────────────────────┤
│ Dimension                │ Example Technical Values (Toyota 4Runner)      │
├──────────────────────────┼────────────────────────────────────────────────┤
│ 1. Generic Classification│ Four-Wheel Drive (4WD)                         │
│ 2. Drivetrain Arch.      │ Part-time 4WD  |  Full-time 4WD                │
│ 3. Physical Components   │ Transfer Case, Torsen Center Diff,             │
│                          │ Rear Locking Differential                      │
│ 4. Operating Modes       │ 2H, 4H, 4L (SR5)  |  H4F, H4L, L4L (Limited)   │
│ 5. Mode States/Props     │ 4H: Center locked (1:1)                        │
│                          │ H4F: Center open (40:60 torque split)          │
│                          │ H4L: Center locked (50:50 torque split)        │
│ 6. System Capabilities   │ Selectable 2WD, Low-Range, Center Lock,        │
│                          │ Rear Lock                                      │
│ 7. Manufacturer Term.    │ "Part-time 4WD with Active Traction Control"   │
│                          │ "Full-time 4WD with Torsen Limited-Slip"       │
└──────────────────────────┴────────────────────────────────────────────────┘
```

### Component vs Capability Distinction
A component is a physical assembly; a capability is a system behavior.
* `center_differential` is a **Component** (not a capability).
* `center_differential_lock` is a **Capability** (behavioral state).

### Distinguishing Drivetrain Capabilities from Vehicle-Control Systems
Drivetrain hardware/capabilities (low range, locking differential) MUST be distinguished from electronic/brake-based traction control features:
* **Drivetrain Hardware/Capability**: Part-time 4WD, Low-Range, Rear Locking Differential.
* **Vehicle-Control Feature**: Active Traction Control (A-TRAC), CRAWL Control, Multi-Terrain Select (MTS). These are preserved as `factory_technical_features` with unresolved model placement rather than forced into drivetrain components.

---

## 11. Empirical Drivetrain Architecture Findings (Toyota 4Runner)

Empirical investigation of Toyota manufacturer specification material establishes two primary 5th Gen 4Runner drivetrain architectures:

### A. SR5 / TRD Off-Road / TRD Pro / Trail / Venture Part-Time System
* **Generic Classification**: Four-Wheel Drive (`4WD`).
* **Drivetrain Architecture**: Part-Time 4WD.
* **Operating Modes**:
  * `2H`: Rear-wheel drive (100% rear).
  * `4H`: Part-time 4WD High range (50:50 rigid front/rear split, center coupling locked). Off-road / slippery surfaces only.
  * `4L`: Part-time 4WD Low range (2.566:1 reduction ratio, center coupling locked).
* **Capabilities**: Selectable 2WD, Selectable 4WD, Low-Range. (Rear Differential Lock added on TRD Off-Road / TRD Pro / Trail / Venture).

### B. Limited / Nightshade Full-Time System
* **Generic Classification**: Four-Wheel Drive (`4WD`).
* **Drivetrain Architecture**: Full-Time 4WD.
* **Components**: Torsen Type-3 Limited-Slip Center Differential.
* **Operating Modes**:
  * `H4F`: Full-time 4WD High range, center differential UNLOCKED (open Torsen operation; 40:60 torque split, auto-adjusting up to 30:70 or 50:50). Safe for all road surfaces.
  * `H4L`: Full-time 4WD High range, center differential LOCKED (50:50 rigid split).
  * `L4L`: Full-time 4WD Low range (2.566:1 reduction ratio), center differential LOCKED.
* **Capabilities**: Full-Time 4WD Operation, Center Differential Lock, Low-Range.

---

## 12. Multiple Future Presentation Levels

> **Normalized drivetrain data must support multiple presentation levels. Public-facing drivetrain descriptions may eventually be derived from generic drive-system classification, detailed architecture, or both. Ingestion must preserve sufficient structure so UI choices do not require source data to be reacquired.**

```text
Rich normalized drivetrain data
        │
        ├── compact browser/filter
        │       → "4WD"
        │
        ├── technical configuration label
        │       → "Full-time 4WD"
        │
        └── detailed technical presentation
                → architecture
                → components
                → modes
                → states
                → capabilities
```

---

## 13. Source Reconciliation & Precedence Strategy

Reconciliation merges assertions from multiple sources into a unified candidate configuration using attribute-level rules.

### Attribute-Specific Source Authority Principle
> **Source authority and precedence should be evaluated at the attribute level and may be source-, manufacturer-, model-, market-, and model-year-specific. Mapping rules must be empirically validated rather than assumed universal.**

### Illustrative Initial Source-Role Hypotheses
The following ordering is illustrative for initial research and does NOT establish universal hard-coded precedence:
* **Manufacturer Material**: Normally strong evidence for manufacturer-recognized trim/grade taxonomy, drivetrain architecture, and factory technical specifications.
* **EPA Data**: Potentially strong evidence for US regulatory powertrain/configuration existence.
* **NHTSA Data**: Potentially strong evidence for VIN/regulatory make/model structures.
* **J.D. Power Data**: Potentially useful for US-market trim/configuration enumeration and corroboration.

Exact authority relationships remain subject to empirical validation for the particular manufacturer, model, model year, market, source, and attribute.

### Reconciliation Rules
1. **Specificity Protection**: A higher-specificity assertion (e.g. `Full-time 4WD with Torsen center differential`) MUST NOT be overwritten by a lower-specificity assertion (e.g. `4WD`).
2. **No Silent Overwrite**: When two sources assert conflicting values at the same specificity level, the conflict is assigned a categorical status of `conflicting` or `requires_review` rather than allowing the last-processed source to win.

---

## 14. Candidate-Configuration & Categorical Status Concept

A **Candidate Configuration** is an intermediate normalized structure produced by reconciliation prior to canonical database import.

### Categorical Reconciliation States
Numeric confidence scoring (e.g. `0.85`) is excluded as an architectural requirement due to lack of empirical calibration. Ingestion utilizes categorical status states:
* `corroborated`: Asserted by multiple authoritative sources without conflict.
* `single_source`: Asserted by a single reliable source without contradiction.
* `conflicting`: Source assertions disagree at the same specificity level.
* `ambiguous`: Source text cannot be parsed deterministically.
* `incomplete`: Missing mandatory identification fields.
* `requires_review`: Flagged for human review.

---

## 15. `VehicleDefinition` Mapping Boundary & Manufacturer Taxonomy Rule

### The Manufacturer-Taxonomy Rule
> **RigArchive follows the manufacturer's own market-specific configuration taxonomy for trim/grade identity. When the manufacturer presents a configuration as a distinct trim or grade in official market-facing or specification material, RigArchive preserves that trim identity even when it incorporates equipment that could otherwise be described as an option package. When the manufacturer treats equipment only as an optional package or standalone option on an existing trim, that equipment does not create a separate trim or VehicleDefinition solely by its presence.**

### Approved `VehicleDefinition` Mapping Rules
1. **Distinct Model Year**: A different model year represents a distinct candidate `VehicleDefinition`.
2. **Distinct Manufacturer-Recognized Trim/Grade**: A different manufacturer-recognized US market grade (including sub-grades like `SR5 Premium` and `Trail Premium`) represents a distinct candidate `VehicleDefinition`. Sub-grades are NOT collapsed into base grades.
3. **Manufacturer Trim Incorporating a Package**: If the manufacturer markets a "trim + package" combination as a distinct trim identity (e.g. 2015 VW Touareg `Sport with Technology`), preserve it as a distinct trim identity.
4. **Ordinary Optional Package**: Packages and individual options that the manufacturer does not recognize as distinct trims/grades do not independently create `VehicleDefinition` records (e.g. KDSS option on Trail grade). The package is preserved in candidate package metadata.
5. **Individual Options**: Individual optional equipment does NOT independently create a separate `VehicleDefinition`.
6. **Mechanical Configuration Distinctions**: Within a manufacturer-recognized trim, materially distinct canonical factory configurations (e.g. 2WD vs 4WD, or 2.7L I4 vs 4.0L V6) represent distinct candidate `VehicleDefinition` records.
7. **Special Editions**: Follow manufacturer taxonomy. If presented as a distinct grade in manufacturer literature (e.g. TRD Pro, Venture, Nightshade), preserve it as a distinct trim identity. If presented as an optional accessory package on another trim, preserve it as a package.

### Future Options & Packages Capability
The ingestion pipeline MUST preserve package and option distinctions in candidate metadata so that future approved schemas can surface:
`VehicleDefinition → Trim Identity → Available Packages → Available Options`

---

## 16. Provenance Requirements

Every Candidate Configuration MUST preserve complete provenance linking normalized attributes back to original source assertions:
* Source identity (`nhtsa`, `epa`, `toyota_press`, `jd_power`);
* Source record/document identifier & URL reference;
* Retrieval timestamp;
* Source assertion or source-derived factual value (with raw source text/snippet retained where appropriate and permitted);
* Parser/normalization version & normalized interpretation.

---

## 17. Intermediate Representation Recommendation (JSON)

RA-010 recommends a structured **JSON Intermediate Representation** stored in a dedicated Git-ignored ingestion directory (e.g. `ingestion/candidates/`). Field names remain subject to refinement during implementation.

### Conceptual Intermediate Structure
> **Note**: `candidate_reference` below is an illustrative, transient property useful for identifying an intermediate candidate artifact. It is NOT a canonical Reference identifier, a finalized deduplication key, a `VehicleDefinition` identity key, or an approved import matching mechanism.

```json
{
  "candidate_reference": "cand_ref_2020_toyota_4runner_trd_off_road_premium_4wd",
  "provenance": {
    "retrieved_at": "2026-08-15T08:30:00Z",
    "sources_consulted": ["nhtsa", "epa", "toyota_press", "jd_power"]
  },
  "canonical_target": {
    "manufacturer_name": "Toyota",
    "vehicle_model_name": "4Runner",
    "generation_name": "Fifth Generation",
    "model_year": 2020,
    "trim_name": "TRD Off-Road Premium",
    "engine_name": "4.0L V6",
    "drivetrain": "4WD",
    "market": "US"
  },
  "normalized_technical_details": {
    "engine": {
      "displacement_l": 4.0,
      "cylinders": 6,
      "code": "1GR-FE"
    },
    "transmission": {
      "type": "Automatic",
      "speeds": 5
    },
    "drivetrain": {
      "generic_classification": "four-wheel drive",
      "architecture": "part-time 4WD",
      "operating_modes": ["2H", "4H", "4L"],
      "capabilities": ["selectable_2wd", "selectable_4wd", "low_range", "rear_differential_lock"]
    },
    "factory_technical_features": [
      {"name": "Active Traction Control (A-TRAC)", "status": "unclassified_feature"},
      {"name": "CRAWL Control", "status": "unclassified_feature"},
      {"name": "Multi-Terrain Select", "status": "unclassified_feature"}
    ]
  },
  "packages_and_options": [
    {"type": "package", "name": "KDSS (Kinetic Dynamic Suspension System)", "availability": "optional"}
  ],
  "reconciliation": {
    "status": "corroborated",
    "requires_review": false,
    "conflicts": []
  }
}
```

---

## 18. Representative Four-Year Source / Mapping Experiment

Applying the manufacturer-taxonomy mapping rules to representative 5th Gen 4Runner model years (**2010, 2015, 2020, 2024**) establishes candidate configuration mappings:

### A. Model Year 2010 (Launch Year)
* **Generation**: Fifth Generation (2010–2024).
* **Factual Powertrain Correction**: Official Toyota US specification material establishes that the `2.7L 2TR-FE I4` (4-Speed Auto) was available ONLY on the **4x2 SR5**. All 4x4 models used the `4.0L 1GR-FE V6` (5-Speed Auto). No `SR5 / 2.7L I4 / 4WD` configuration existed.
* **Candidate Trims & Variants**:
  1. `SR5` (2.7L I4, 2WD) → Candidate `VehicleDefinition`
  2. `SR5` (4.0L V6, 2WD) → Candidate `VehicleDefinition`
  3. `SR5` (4.0L V6, 4WD — Part-time) → Candidate `VehicleDefinition`
  4. `Trail` (4.0L V6, 4WD — Part-time with Rear Locker) → Candidate `VehicleDefinition`
  5. `Limited` (4.0L V6, 2WD) → Candidate `VehicleDefinition`
  6. `Limited` (4.0L V6, 4WD — Full-time Torsen) → Candidate `VehicleDefinition`
* **Package Distinctions**: KDSS available as an optional package on `Trail` (does not independently create a separate trim).

### B. Model Year 2015 (Mid-Cycle Update / TRD Pro Launch)
* **Powertrain Changes**: 2.7L I4 discontinued; 4.0L V6 standard across all models.
* **Manufacturer Trim Taxonomy Application**: Toyota officially lists `SR5 Premium` and `Trail Premium` as distinct grades in US sales literature. Per the Manufacturer-Taxonomy Rule, they are preserved as distinct trim identities rather than collapsed into `SR5` or `Trail`.
* **Candidate Trims & Variants**:
  1. `SR5` (2WD / 4WD) → 2 Candidate `VehicleDefinition` records
  2. `SR5 Premium` (2WD / 4WD) → 2 Candidate `VehicleDefinition` records
  3. `Trail` (4WD) → Candidate `VehicleDefinition`
  4. `Trail Premium` (4WD) → Candidate `VehicleDefinition`
  5. `TRD Pro` (4WD — Part-time) → Candidate `VehicleDefinition` (Distinct Grade)
  6. `Limited` (2WD / 4WD) → 2 Candidate `VehicleDefinition` records

### C. Model Year 2020 (Special Editions Update)
* **Manufacturer Trim Taxonomy Application**: Toyota markets `Venture Edition` and `Nightshade Edition` as distinct model grades.
* **Candidate Trims & Variants**:
  1. `SR5` / `SR5 Premium` (2WD / 4WD) → 4 Candidate `VehicleDefinition` records
  2. `TRD Off-Road` / `TRD Off-Road Premium` (4WD) → 2 Candidate `VehicleDefinition` records
  3. `Venture` (4WD — Part-time) → Candidate `VehicleDefinition`
  4. `TRD Pro` (4WD — Part-time, Fox shocks) → Candidate `VehicleDefinition`
  5. `Limited` (2WD / 4WD — Full-time on 4WD) → 2 Candidate `VehicleDefinition` records
  6. `Nightshade` (2WD / 4WD — Full-time on 4WD) → 2 Candidate `VehicleDefinition` records

### D. Model Year 2024 (Generation Closure)
* **Factual Lineup Correction**: Official Toyota material establishes that the `40th Anniversary Special Edition` was produced for the 2023 model year and was not part of the 2024 lineup.
* **Candidate Trims & Variants**:
  1. `SR5` / `SR5 Premium` (2WD / 4WD)
  2. `TRD Sport` (2WD / 4WD — X-REAS suspension on SR5 body)
  3. `TRD Off-Road` / `TRD Off-Road Premium` (4WD)
  4. `TRD Pro` (4WD — Fox internal bypass shocks)
  5. `Limited` (2WD / 4WD)

---

## 19. Human-Review Escalation Boundaries

Automated ingestion MUST NOT force canonical database writes when ambiguity exists. Candidates are assigned status `requires_review` under the following conditions:
1. **Unresolved Source Conflict**: Sources disagree on drivetrain architecture or engine parameters at the same confidence/specificity level.
2. **Unrecognized Trim / Grade**: Source lists a trim name not present in the target Generation trim dictionary.
3. **Missing Mandatory Attributes**: Candidate lacks required `model_year`, `trim_name`, or `drivetrain` classification.
4. **Generation Boundary Overlap**: Model year falls on a transition year where generation start/end dates overlap in source records.

---

## 20. Deterministic Import & Idempotency Requirements

Future import tools MUST satisfy the following architectural requirements:
* **Deterministic Execution**: Canonical import execution must be deterministic.
* **Duplicate-Safe & Idempotent**: Re-running the import against the same approved candidate set must produce zero additional database records.
* **Protection of Canonical Records**: Manually authored or previously validated canonical Reference records must be protected from unintended automated overwrite.
* **Matching Key Unresolved**: The exact canonical matching key/mechanism remains unresolved and must be established in a later design/implementation task after ingestion identity semantics have been validated.

---

## 21. Extensibility Beyond Toyota

To verify that the drivetrain and mapping abstractions are universal rather than Toyota-specific, RA-010 evaluates two non-Toyota systems:

### A. Mitsubishi Super Select 4WD (SS4-II)
* **Architecture**: Selectable Multi-Mode 4WD.
* **Operating Modes**: `2H` (RWD), `4H` (Full-time 4WD open viscous center diff, 33:67 split), `4HLc` (Part-time 4WD center locked, 50:50 split), `4LLc` (Part-time 4WD Low range, center locked).
* **Validation**: The 7-dimension model handles SS4-II cleanly, accurately distinguishing `4H` (full-time open) from `4HLc` (part-time locked).

### B. Volkswagen 4Motion (Electro-Hydraulic Haldex Coupling)
* **Architecture**: Automatic On-Demand All-Wheel Drive.
* **Validation**: Maps cleanly to `generic_classification: "all-wheel drive"`, `architecture: "automatic on-demand AWD"`, `components: ["multi-plate electro-hydraulic clutch"]`.

---

## 22. Explicit Non-Goals

RA-010 MUST NOT:
* Implement web scrapers, API client code, or source adapters.
* Execute database imports or create Reference records.
* Create or modify Django models or database migrations.
* Add models for Drivetrain, Engine, Transmission, Packages, or Options.
* Redesign User identity or redefine Observation/Evidence domains.
* Build public drivetrain UI or comparison views.
* Create a universal vehicle-specification ontology for all automotive systems.

---

## 23. Recommended Next Implementation & Research Milestones

1. **RA-011 — Ingestion Schema & Intermediate Serialization Design**: Define the formal JSON Schema for raw assertions and candidate configurations in a dedicated ingestion runtime directory.
2. **RA-012 — Public Source Acquisition Adapters (NHTSA & EPA)**: Implement read-only python acquisition adapters for public government APIs storing raw payloads.
3. **RA-013 — Toyota 4Runner Ingestion Normalizer & Candidate Generator**: Implement normalization logic producing 5th Gen 4Runner candidate JSON files.

---

## 24. Decisions, Findings, and Unresolved Questions

### Approved Architectural Principles
* Decoupled source acquisition and canonical import.
* Manufacturer taxonomy governs trim/grade identity (sub-grades like `SR5 Premium` preserved as distinct trims).
* Packages/options not recognized by the manufacturer as distinct trims/grades do not independently create VehicleDefinitions.
* Non-lossy normalization (specificity preservation).
* 7-dimension drivetrain normalization model.
* Attribute-level source authority and precedence.
* Unclassified attributes principle (unknown attributes preserved without being forced into incorrect categories).
* Multiple future presentation levels supported.
* Future import must be deterministic, duplicate-safe, and idempotent without fixing a premature matching mechanism.

### Empirical Source Findings
* 2010 Toyota 4Runner 2.7L I4 was available ONLY on 4x2 SR5 (not 4WD).
* 2024 Toyota 4Runner lineup does NOT include 40th Anniversary Special Edition (produced for 2023 model year only).
* J.D. Power presentation strings combine body descriptors (`Utility 4D`) requiring token-based parsing.

### Unresolved Items (Requiring Future Research/Task Specification)
* Final intermediate JSON schema structure and field names.
* Controlled technical vocabulary for drivetrain components and operating modes.
* Exact deterministic matching key/mechanism for canonical import.
* Persistent staging models vs file-based JSON candidate workflows.
* Final storage path for ingestion runtime artifacts (outside `backups/`).
* Operational/licensing suitability of J.D. Power for automated production acquisition.
* Domain placement and model structure for broader technical features (A-TRAC, CRAWL Control, KDSS, X-REAS).
* Eventual model and UI architecture for available packages and options.

---

## Summary Matrix

| Architectural Dimension | Specification |
| :--- | :--- |
| **Milestone** | RA-010 Architecture / Research |
| **Target Vehicle Scope** | Toyota 4Runner — 5th Gen (2010–2024 US Market) |
| **Focus Study Years** | 2010, 2015, 2020, 2024 |
| **Evaluated Sources** | NHTSA vPIC, EPA FuelEconomy.gov, Toyota USA Press/FSM, J.D. Power |
| **Trim Mapping Rule** | Manufacturer taxonomy governs (sub-grades like `SR5 Premium` preserved) |
| **Package/Option Mapping** | Packages/options not recognized by the manufacturer as distinct trims/grades do not independently create VehicleDefinitions |
| **Acquisition Boundary** | Decoupled from canonical DB; raw payloads stored in ingestion runtime area |
| **Normalization Boundary** | Non-lossy 7-dimension drivetrain model; token-based body prefix parsing |
| **Reconciliation Logic** | Attribute-level precedence; specificity protection; categorical status states |
| **Categorical States** | `corroborated`, `single_source`, `conflicting`, `ambiguous`, `incomplete`, `requires_review` |
| **Extensibility Validation** | Tested against Mitsubishi Super Select and VW 4Motion architectures |
| **Deferred Infrastructure** | Django staging models, automated scrapers, DB import execution, public UI components |
