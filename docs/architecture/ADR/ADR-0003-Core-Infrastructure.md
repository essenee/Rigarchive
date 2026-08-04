# ADR-0003: Core Infrastructure Application

- **Status**: Accepted
- **Date**: 2026-08-04

## Context

As RigArchive expands across multiple business domains (such as Reference, Knowledge, Evidence, Media, and Projects), multiple models require identical foundational infrastructure, specifically stable external UUID identifiers and automatic creation/modification timestamps. Without a shared infrastructure application, each domain application would duplicate field definitions, leading to inconsistent implementations and maintenance friction.

However, introducing a shared `core` package carries the risk of it becoming a bloat-prone "utility sink" if domain logic or unrelated helpers are prematurely added.

## Decision

Introduce a dedicated `core` Django application that provides shared, abstract model infrastructure across all RigArchive domains:

1. **Scope of `core`**: `core` contains only foundational, domain-agnostic abstract base classes (`UUIDModel`, `TimestampedModel`, and `BaseModel`).
2. **Abstract Inheritance**: All shared model classes in `core` MUST define `Meta.abstract = True`. No concrete database tables belong to `core`.
3. **Domain Ownership**: Domain-specific models, services, business workflows, and validation rules remain strictly inside their respective domain applications (e.g., `reference`, `accounts`).
4. **Exclusion of Soft Deletion**: Soft deletion behavior is deliberately excluded from RA-003 to keep the core infrastructure minimal and focused. Soft deletion will be evaluated in a separate future ADR when an immediate business workflow requires it.

## Rationale

- **DRY Infrastructure**: Centralizes UUID identity and timestamp management without duplicating field attributes across domain applications.
- **Schema Safety**: Abstract inheritance ensures domain models own their concrete database tables while inheriting unified field definitions.
- **Architectural Boundary**: Restricting `core` to abstract base infrastructure prevents `core` from accumulating unrelated helper functions, miscellaneous utilities, or domain leaks.

## Consequences

### Positive
- Domain models across RigArchive share identical UUID identity and timestamp mechanics.
- Abstract base classes create zero database overhead or extra table joins.
- Maintenance is centralized: changes to common field behavior can be managed in one location.

### Negative
- Requires strict code review discipline to prevent developers from adding domain models or generic utility functions into `core`.

## Alternatives Considered

- **Domain-Local Duplication**: Keep UUID and timestamp fields declared separately in each domain model. Rejected due to code duplication and risk of divergent field parameters.
- **Concrete Parent Models (Multi-table Inheritance)**: Have models inherit from concrete parent tables. Rejected due to severe performance penalties caused by implicit SQL JOIN operations on every query.
- **Broad Utility App**: Create a generic `utils` or `common` package containing helpers, services, and mixins. Rejected because unstructured utility apps degrade architectural boundaries.
