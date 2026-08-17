# RA-042 — Measurements Domain Foundation Architecture

> **Status**: Approved Architectural Design Document  
> **Authority**: Higher than `CURRENT_STATE.md` and Handbook for RA-042 decisions.  
> **Scope**: Conceptual and architectural specification for the Measurements domain foundation before implementation in RA-043.  
> **Restrictions**: Documentation only. Zero application code, zero models, zero migrations, zero template/view changes.  

---

## 1. Executive Summary

RigArchive is an evidence-oriented technical archive for vehicles. The Reference domain ([RA-003](file:///Users/esse/dev/Rigarchive/docs/implementation/tasks/RA-003-core-foundation.md), [RA-030](file:///Users/esse/dev/Rigarchive/docs/implementation/tasks/RA-030-public-vehicle-navigation-hierarchy.md), [ADR-0001](file:///Users/esse/dev/Rigarchive/docs/architecture/ADR/ADR-0001-Entity-Identity-Strategy.md)) models canonical factory vehicle taxonomy (`Manufacturer`, `VehicleModel`, `Generation`, `VehicleDefinition`), answering *"What configuration did the manufacturer sell?"*.

The **Measurements** domain is a first-class RigArchive product capability designed to provide physical vehicle measurements useful beyond standard manufacturer sales specifications. Examples include cargo opening dimensions, cargo interior height at critical boundaries, cargo floor dimensions, and equipment-influenced interior clearances essential for vehicle modification, travel, camping, overlanding, storage, and sleeping-platform design.

This document establishes the approved foundation architecture for the Measurements domain ([ADR-0009](file:///Users/esse/dev/Rigarchive/docs/architecture/ADR/ADR-0009-Measurements-Domain-Strategy.md)), specifying domain boundaries, vehicle scope anchors, measurement definitions vs. results, unit ownership, protocol boundaries, feature applicability models, condition semantics, multi-result evidence preservation, public presentation paths, and testing requirements prior to implementation in RA-043.

---

## 2. Scope & Non-Goals

### Approved Scope
- Architectural specification for the `measurements` Django application.
- Conceptual data model (`MeasurementDefinition`, `MeasurementResult`, `ApplicabilityFeature`, `ApplicabilityState`, `MeasurementResultCondition`).
- Vehicle scope anchor specification binding measurements to `reference.Generation`.
- Controlled feature applicability architecture decoupling physical feature states from factory sales trims/packages.
- Definition of provisional v1 cargo-height taxonomy concepts.
- Specification for `GenerationMeasurementsView` vehicle-first public browser integration.
- Semantic test invariants for RA-043 implementation.
- Architectural decision record ([ADR-0009](file:///Users/esse/dev/Rigarchive/docs/architecture/ADR/ADR-0009-Measurements-Domain-Strategy.md)).

### Explicit Non-Goals (Deferred Capabilities)
- Implementation of Django models, migrations, views, URLs, templates, or admin classes (reserved for RA-043).
- User contribution submission forms, evidence uploads, photo/image evidence attachment.
- Contributor reputation, attribution, or moderation workflows.
- Automatic manufacturer specification ingestion or Reference-to-Measurement mapping.
- Arbitrary Boolean expression engines or complex rules languages.
- Broad measurement taxonomy expansion (cargo length/width, seat-position protocols, ground clearance).
- Measurement comparison tools, interactive CAD/diagram visualizations, search filters, or REST APIs.
- Versioned measurement protocol storage models.
- Database uniqueness constraints across `(generation, definition, applicability)`.
- Real data insertion or seed fixture population during RA-042.

---

## 3. Approved Domain Boundary

Measurements IS approved as a distinct RigArchive domain and SHALL be implemented in RA-043 as a top-level Django application:

```text
measurements/
├── __init__.py
├── apps.py
├── models.py
├── admin.py
├── views.py
├── urls.py
├── migrations/
└── tests/
```

### Domain Distinction
- **Reference Domain (`reference`)**: Answers *"What factory configurations did the manufacturer produce and sell?"* (Manufacturer, Model, Generation, VehicleDefinition).
- **Measurements Domain (`measurements`)**: Answers *"What are the physical dimensional characteristics of a vehicle body geometry under defined feature conditions?"*.

Measurement models MUST NOT be placed inside `reference`. The domains interact via protected foreign key relationships (`reference.Generation`), but maintain strict architectural decoupling.

---

## 4. Approved Core Conceptual Model

```text
reference.Generation
        │
        ▼
MeasurementResult
        │
        ├──── MeasurementDefinition
        │
        └──── zero or more MeasurementResultCondition
                           │
                           ▼
                  ApplicabilityState
                           │
                           ▼
                  ApplicabilityFeature
```

1. **`reference.Generation`**: The physical vehicle body geometry anchor.
2. **`MeasurementDefinition`**: Reusable measurement concept (WHAT is measured).
3. **`MeasurementResult`**: Reported numeric value and unit for a definition in a generation context.
4. **`ApplicabilityFeature`**: Measurement-relevant physical feature type (e.g., Sunroof).
5. **`ApplicabilityState`**: Allowed state for a feature (e.g., Present, Absent).
6. **`MeasurementResultCondition`**: Required feature state condition attached to a result.

---

## 5. Measurement Definition Architecture

`MeasurementDefinition` represents WHAT is being measured as a reusable concept across vehicle generations.

### Conceptual Specifications
- **Identity**: Inherits `core.models.BaseModel` (Integer PK + UUID).
- **Name**: `CharField(max_length=100, unique=True)` (e.g., "Cargo Opening Height").
- **Slug**: `SlugField(max_length=120, unique=True, editable=False)` (auto-generated from `name`, immutable per ADR-0002).
- **Category**: `CharField(max_length=50, choices=MeasurementCategory.choices, default="cargo")`.
- **Description**: `TextField(blank=True)` (human-readable explanation of what the measurement conceptualizes).
- **Lifecycle**: `is_active = models.BooleanField(default=True)`.

### Unit Ownership Policy
`MeasurementDefinition` SHALL NOT specify a canonical or default unit. A dimensional concept (e.g., "Cargo Opening Height") is unit-agnostic. Units belong exclusively to `MeasurementResult`.

---

## 6. Measurement Protocols — Deferred Architecture Boundary

Standardized measurement protocol storage, versioning, and execution procedure models ARE DEFERRED.

A future protocol architecture may specify:
- Reference measurement planes and landmarks;
- Instrument tolerances and measurement techniques;
- Equipment states (e.g., cargo floor position, seat position);
- Versioned protocol revisions.

`MeasurementDefinition.description` explains what a measurement concept means in prose, but MUST NOT be treated as versioned protocol storage. Historical `MeasurementResult` records must eventually bind to versioned protocol records so their meaning is not altered when protocol descriptions change.

---

## 7. Measurement Result Architecture

`MeasurementResult` represents an individual reported value for a `MeasurementDefinition` within a `Generation` context.

### Conceptual Specifications
- **Generation Anchor**: `ForeignKey("reference.Generation", on_delete=models.PROTECT, related_name="measurement_results")`.
- **Definition Anchor**: `ForeignKey("measurements.MeasurementDefinition", on_delete=models.PROTECT, related_name="results")`.
- **Numeric Value**: `DecimalField(max_digits=7, decimal_places=2, validators=[MinValueValidator(Decimal("0.01"))])` (e.g., `37.25`).
- **Unit**: `CharField(max_length=20, default="in")` (stores unit string, e.g., `"in"` for Inches).
- **Notes**: `TextField(blank=True)`.
- **Lifecycle**: `is_active = models.BooleanField(default=True)`.

`MeasurementResult` associates directly with `reference.Generation`. It MUST NOT require a `VehicleDefinition` association. Physical body geometry is established at the `Generation` level; factory sales trims/packages (`VehicleDefinition`) are orthogonal.

---

## 8. Result Identity & Multi-Result Evidence Rule

A `Generation + MeasurementDefinition + applicability` combination SHALL NOT be constrained as database-unique.

RigArchive is an evidence-oriented technical archive. Multiple `MeasurementResult` records for the identical vehicle, definition, and applicability MUST remain architecturally permitted to accommodate:
- Independent empirical measurements from different contributors/sources;
- Manufacturer-published specifications;
- Re-measured or verified interpretations;
- Historical measurement comparisons.

A `MeasurementResult` is NOT automatically canonical truth merely because it exists. Result selection, preference, statistical aggregation, and evidence reconciliation ARE EXPLICITLY DEFERRED.

---

## 9. Unit Representation Policy

- Initial implementation (RA-043) stores units on `MeasurementResult.unit` defaulting to `"in"` (Inches).
- Inches is the primary unit used in North American vehicle modification and overlanding contexts.
- Generalized unit-conversion frameworks (e.g., Inches to Centimeters/Millimeters) ARE DEFERRED to presentation/service layers.
- Storing `"in"` on a result does not make `MeasurementDefinition` inherently inch-based.

---

## 10. Measurement Applicability Architecture

Measurement applicability describes physical/configurational feature states that materially affect physical geometry.

### Physical Applicability vs. Sales Hierarchy
- **Factory Sales Hierarchy (`reference`)**: Answers *"Did Toyota sell a 2019 4Runner TRD Off-Road Premium with a Sunroof Package?"*.
- **Measurement Applicability (`measurements`)**: Answers *"Does this vehicle have a sunroof installed that lowers interior headliner clearance?"*.

Measurement applicability asks *"What physical feature state materially affects this measurement?"*. It MUST NOT duplicate manufacturer trim, model year, or option package hierarchies.

---

## 11. Applicability Feature & State Models

### `ApplicabilityFeature`
Represents a measurement-relevant physical feature type.
- **Fields**: `name` (unique), `slug` (unique), `description`.
- **Approved Examples**:
  - *Sunroof* (`sunroof`)
  - *Cargo Floor Position* (`cargo-floor-position`)
  - *Second Row Configuration* (`second-row-seating`)

### `ApplicabilityState`
Represents an allowed option/state for a feature.
- **Fields**: `feature` (FK `ApplicabilityFeature`), `name`, `slug`.
- **Approved Examples**:
  - Sunroof: `Present`, `Absent`
  - Cargo Floor Position: `Upper Position`, `Lower Position`
  - Second Row Configuration: `Bench Seat`, `Captain's Chairs`

This controlled vocabulary architecture avoids adding dedicated nullable Boolean columns (e.g., `has_sunroof`, `has_third_row`) to models, enabling new applicability factors to be added without database schema migrations.

---

## 12. Measurement Result Condition Semantics

`MeasurementResultCondition` joins a `MeasurementResult` to an `ApplicabilityState`.

### Zero Conditions: Generation-Wide Applicability
Zero associated conditions (`result.conditions.count() == 0`) means **Generation-wide applicability**. The measurement applies to all vehicles in the Generation regardless of optional feature states.
- **Public Labeling**: In public interfaces, zero-condition results MUST be labeled **"Generation-wide"** or **"All configurations"**.
- **Prohibited Labeling**: The phrase "Generation Standard" is PROHIBITED due to false canonical/authoritative implications.

### One or More Conditions: Conjunctive AND Semantics
Multiple conditions attached to a single `MeasurementResult` are evaluated conjunctively (**AND**).
- Example: `{Sunroof: Present, Cargo Floor Position: Lower Position}` applies ONLY when `Sunroof = Present AND Cargo Floor Position = Lower Position`.
- **Domain Validation**: Model validation (`clean()`) MUST enforce that a single `MeasurementResult` cannot attach multiple states belonging to the same `ApplicabilityFeature` (e.g., `Sunroof = Present AND Sunroof = Absent` is invalid).

---

## 13. Initial Cargo-Height Taxonomy (Provisional v1)

The provisional v1 cargo-height taxonomy comprises three approved definitions:

1. **Cargo Opening Height**: Usable vertical height of the rear cargo opening.
2. **Cargo Height Behind Second Row**: Vertical interior height measured immediately behind the second-row seating/cargo boundary (capturing sunroof headliner variations).
3. **Maximum Cargo Interior Height**: The greatest usable vertical interior dimension within the defined cargo area.
   - *Centerline Policy*: The architecture SHALL NOT define maximum height as necessarily occurring on the vehicle centerline. Equipment or roof geometry may cause the true maximum to occur off-center.

---

## 14. Manufacturer Dimensions Integration Boundary

Manufacturer-supplied dimensions and empirical `MeasurementResult` records MAY eventually be presented in a unified public user experience, but their underlying provenance and domain models remain distinct. Manufacturer-dimension ingestion IS OUT OF SCOPE for RA-042/RA-043.

---

## 15. Provenance & Evidence Boundary (Deferred)

Future architecture may capture contributor identity, measurement date, instrument type, photographic evidence, statistical confidence, and verification state. RA-042 explicitly preserves architectural room for these concepts without implementing them.

---

## 16. Initial Public Presentation Plan

### Navigation Path (Vehicle-First)
```text
Home ──> Vehicles ──> Manufacturer ──> Model ──> Generation ──> Measurements
```

### Presentation Components (RA-043)
1. **`GenerationDetailView` Integration**:
   - Add a "Physical Measurements" link/button in the right-hand Overview infobox or secondary nav on `templates/reference/generation_detail.html`.
2. **Dedicated Generation Measurements Page**:
   - Route: `/vehicles/<manufacturer_slug>/<vehicle_model_slug>/<generation_slug>/measurements/` (`GenerationMeasurementsView`).
   - Renders provisional v1 cargo-height definitions, values, units, and applicability tags.
   - Unconditioned results display "Generation-wide" / "All configurations".
   - Conditioned results display feature state tags (e.g., `Sunroof: Present`).

---

## 17. Future Homepage Discovery Direction

Measurements is a core product capability. Future navigation (`base.html`) will support homepage-first discovery:
```text
Home ──> Measurements ──> Vehicle Selection ──> Generation Measurements
```
Top-level `/measurements/` routes and cross-vehicle measurement comparison ARE DEFERRED.

---

## 18. Data Population & Seed Fixture Boundary

- The persistence and population mechanism for controlled `MeasurementDefinition` vocabulary (fixtures vs. data migrations vs. admin management) IS DEFERRED to RA-043.
- **Zero Real Data Insertion**: Illustrative measurement values (e.g., 37.25", 34.50") used in planning discussions MUST NOT be inserted into development or production databases.
- Unit tests in RA-043 SHALL use isolated test database fixtures only.

---

## 19. Admin Interface Direction

RA-043 will register Django Admin interfaces in `measurements/admin.py`:
- `MeasurementDefinitionAdmin`: List display (`name`, `category`, `unit`, `is_active`), search, filters.
- `ApplicabilityFeatureAdmin`: List display, with inline `ApplicabilityStateInline`.
- `MeasurementResultAdmin`: List display (`generation`, `definition`, `value`, `unit`, `is_active`), filters, with inline `MeasurementResultConditionInline`. Enforces domain validation against invalid condition combinations.

---

## 20. Semantic Testing Invariants for RA-043

RA-043 implementation tests (`measurements/tests/`) MUST protect the following semantic invariants:

1. `MeasurementDefinition` generates a stable UUID and immutable slug per ADR-0001/ADR-0002.
2. `MeasurementResult` associates directly with `reference.Generation` via `on_delete=models.PROTECT`.
3. `MeasurementResult` does NOT require a `VehicleDefinition` association.
4. Units belong to `MeasurementResult`, NOT `MeasurementDefinition`.
5. Zero conditions on a result represents Generation-wide applicability (`is_generation_wide == True`).
6. One condition correctly scopes a result to an `ApplicabilityState`.
7. Multiple conditions evaluate conjunctively (AND).
8. Model validation rejects assigning multiple states of the same `ApplicabilityFeature` to a single result.
9. Binary features (Sunroof: Present/Absent) function cleanly.
10. Multi-state features (Cargo Floor Position: Upper/Lower) function cleanly.
11. Multiple `MeasurementResult` records can coexist for identical `(generation, definition, applicability)` combinations.
12. Canonical `reference` database records remain untouched during measurement creation.
13. `GenerationMeasurementsView` returns 200 OK and renders definitions, values, units, and applicability tags correctly.
14. Complete regression suite remains 100% clean (273+ tests passing).

---

## 21. ADR-0009 Alignment

This architecture document aligns with and incorporates all durable architectural decisions recorded in [ADR-0009: Physical Vehicle Measurements & Feature Applicability Domain Strategy](file:///Users/esse/dev/Rigarchive/docs/architecture/ADR/ADR-0009-Measurements-Domain-Strategy.md).

---

## 22. Explicit Deferred Decisions Summary

1. Measurement protocol versioning and execution procedure models.
2. Contributor attribution, source tracking, and evidence upload models.
3. Measurement verification, moderation, and result reconciliation.
4. Statistical aggregation / preferred result selection algorithms.
5. Manufacturer dimension specification ingestion.
6. Reference-to-Measurement sales hierarchy mapping.
7. Broad measurement taxonomy expansion beyond cargo-height v1.
8. Seat-position measurement protocols.
9. Generalized unit conversion and user display preferences.
10. Definition population persistence mechanism (fixtures vs. migrations).
11. Top-level homepage-first `/measurements/` discovery routes and comparison tools.

---

## 23. RA-043 Implementation Boundary

The anticipated next milestone is:  
**RA-043 — Measurements Domain Foundation Implementation**

### Expected RA-043 Scope
- Create `measurements` Django app (`apps.py`, `models.py`, `admin.py`, `views.py`, `urls.py`).
- Create initial migration (`measurements/migrations/0001_initial.py`).
- Register `measurements` in `config/settings.py` (`INSTALLED_APPS`).
- Register Admin interfaces.
- Add `GenerationMeasurementsView` and `templates/measurements/generation_measurements.html`.
- Add link on `templates/reference/generation_detail.html`.
- Implement semantic test suite in `measurements/tests/`.
- Verify full test suite.

---

## 24. STOP Boundary

RA-042 is complete upon human review of documentation artifacts.  
**DO NOT BEGIN RA-043 IMPLEMENTATION. DO NOT CREATE CODE OR MIGRATIONS. DO NOT STAGE OR COMMIT.**
