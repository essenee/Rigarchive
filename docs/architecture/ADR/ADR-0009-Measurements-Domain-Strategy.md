# ADR-0009: Physical Vehicle Measurements & Feature Applicability Domain Strategy

- **Status**: Accepted
- **Date**: 2026-08-17

## Context

RigArchive is an evidence-oriented technical archive for vehicles. The Reference domain ([ADR-0001](file:///Users/esse/dev/Rigarchive/docs/architecture/ADR/ADR-0001-Entity-Identity-Strategy.md), [ADR-0003](file:///Users/esse/dev/Rigarchive/docs/architecture/ADR/ADR-0003-Core-Infrastructure.md)) models canonical factory vehicle taxonomy (`Manufacturer`, `VehicleModel`, `Generation`, `VehicleDefinition`), answering *"What configuration did the manufacturer sell?"*.

Physical vehicle measurements useful for vehicle modification, travel, camping, overlanding, storage, and sleeping-platform design (e.g., cargo opening dimensions, cargo interior height behind seating, maximum interior height) extend beyond standard manufacturer sales specifications. 

To support physical vehicle measurements without polluting canonical reference configurations, creating unmanageable schema expansions for every physical option, or assuming individual measurement entries constitute absolute canonical truth, RigArchive requires formal architectural decisions governing domain boundaries, vehicle scope anchors, measurement definitions vs. results, unit ownership, protocol boundaries, evidence preservation, and feature applicability.

## Decision

Adopt the following durable architectural decisions for the Measurements domain foundation:

1. **Top-Level Domain Isolation (`measurements/`)**:
   Measurements IS a distinct domain and SHALL be implemented as a top-level Django application (`measurements/`). Measurement models MUST NOT be placed inside the `reference` application.

2. **Generation Vehicle Scope Anchor**:
   Physical body geometry applies at the vehicle generation level. `MeasurementResult` SHALL associate directly with `reference.Generation` via protected deletion (`on_delete=models.PROTECT`). `MeasurementResult` MUST NOT require a `VehicleDefinition` association.

3. **Separation of Definition and Result**:
   `MeasurementDefinition` represents WHAT is being measured as a reusable concept across vehicle generations (e.g., "Cargo Opening Height"). `MeasurementResult` represents an individual reported/measured value for a `MeasurementDefinition` within a `Generation` context.

4. **Result Unit Ownership**:
   `MeasurementResult` owns its numeric `value` and `unit`. `MeasurementDefinition` represents a dimensional concept and SHALL NOT specify a canonical or default unit. This prevents double-source-of-truth conflicts.

5. **Deferred Protocol Versioning Boundary**:
   Standardized measurement protocol storage, versioning, and execution procedures ARE DEFERRED. `MeasurementDefinition.description` explains what a measurement concept means, but SHALL NOT be treated as versioned protocol storage.

6. **Multiple Results Coexistence & Evidence Preservation**:
   A `Generation + MeasurementDefinition + applicability` combination SHALL NOT be constrained as database-unique. Multiple `MeasurementResult` records for the identical vehicle, definition, and applicability combination MUST remain architecturally permitted to accommodate independent measurements, manufacturer specifications, or reviewed interpretations. A `MeasurementResult` is NOT automatically canonical truth. Evidence reconciliation and canonical result selection ARE DEFERRED.

7. **Controlled Feature Applicability (`ApplicabilityFeature` & `ApplicabilityState`)**:
   Physical configuration factors affecting measurements (e.g., Sunroof Present/Absent, Cargo Floor Position Upper/Lower) SHALL be modeled using controlled `ApplicabilityFeature` and `ApplicabilityState` domain vocabulary. Measurements SHALL NOT duplicate factory sales trim/package hierarchies (`VehicleDefinition`) and SHALL NOT use dedicated nullable Boolean columns per feature.

8. **Generation-Wide Applicability (Zero Conditions)**:
   A `MeasurementResult` with zero associated `MeasurementResultCondition` records represents **Generation-wide** applicability. In public user interfaces, this SHALL be labeled "Generation-wide" or "All configurations" (the phrase "Generation Standard" is prohibited due to false canonical implications).

9. **Conjunctive Condition Semantics**:
   Multiple conditions attached to a single `MeasurementResult` are conjunctive (**AND**). A `MeasurementResult` MUST NOT attach multiple mutually exclusive states of the same `ApplicabilityFeature` (e.g., `Sunroof = Present AND Sunroof = Absent` is invalid and MUST be rejected by model validation).

10. **Provisional Cargo-Height Taxonomy**:
    The provisional v1 cargo-height taxonomy consists of three definitions:
    - *Cargo Opening Height*
    - *Cargo Height Behind Second Row*
    - *Maximum Cargo Interior Height* (which SHALL NOT be defined as necessarily occurring on the vehicle centerline).

11. **Decoupled Manufacturer Dimensions Integration**:
    Manufacturer-published specifications and empirical `MeasurementResult` records MAY eventually be presented in a unified public user experience, but their underlying domain models and provenance remain distinct. Manufacturer dimension ingestion IS OUT OF SCOPE for RA-042/RA-043.

12. **Vehicle-First & Future Measurement-First Discovery**:
    The primary public presentation route for initial implementation is vehicle-first (`Home -> Vehicles -> Manufacturer -> Model -> Generation -> Measurements`) via a dedicated `GenerationMeasurementsView`. Top-level homepage-first discovery (`Home -> Measurements`) is preserved as future product direction.

## Rationale

- **Domain Integrity**: Separating `reference` (factory configurations) from `measurements` (physical vehicle geometry) protects both domains from architectural pollution and enforces strict separation of concerns.
- **Physical Reality vs. Sales Hierarchy**: Physical measurements care about physical feature states (e.g., whether a sunroof housing lowers the interior headliner) regardless of whether the manufacturer sold the sunroof as a standard trim item, an option package, or a standalone factory option.
- **Extensibility**: Using `ApplicabilityFeature` and `ApplicabilityState` avoids schema migrations whenever a new physical feature factor (e.g., seating configuration, cargo floor position) is discovered.
- **Evidence-Oriented Truth**: Allowing multiple `MeasurementResult` records for the same vehicle/definition/applicability preserves raw empirical measurement reporting and prevents premature data destruction before reconciliation logic is established.

## Consequences

- The `measurements` application will inherit `core.models.BaseModel` for dual identity (Integer PK + UUID) and timestamps.
- `MeasurementResult` records will reference `reference.Generation` via `on_delete=models.PROTECT`.
- No database uniqueness constraints will be placed across `(generation, definition, applicability)` on `MeasurementResult`.
- Public presentation will label unconditioned results as "Generation-wide" or "All configurations".
- Standardized measurement protocols, evidence upload workflows, and result reconciliation remain explicitly deferred.
