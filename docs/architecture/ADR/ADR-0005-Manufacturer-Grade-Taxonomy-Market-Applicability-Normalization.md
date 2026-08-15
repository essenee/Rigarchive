# ADR-0005: Manufacturer Grade Taxonomy & Market Applicability Normalization Strategy

- **Status**: Accepted  
- **Date**: 2026-08-15  

## Context

RigArchive's canonical promotion pipeline ([ADR-0004](file:///Users/esse/dev/Rigarchive/docs/architecture/ADR/ADR-0004-Canonical-Reference-Matching-Import-Promotion-Strategy.md), [RA-018](file:///Users/esse/dev/Rigarchive/docs/architecture/designs/RA-018-Canonical-Reference-Matching-Import-Architecture.md), [RA-019](file:///Users/esse/dev/Rigarchive/docs/implementation/tasks/RA-019-canonical-reference-import-planning-create-only-execution-implementation.md)) converts validated `CandidateConfigurationDocument` artifacts into canonical `VehicleDefinition` records when evidence exists for 8 core concepts (`make`, `model`, `model_year`, `generic_drive_classification`, `engine_displacement_liters`, `engine_cylinders`, `trim`, `market`).

However, current production public sources (NHTSA vPIC, EPA FuelEconomy) omit mapped `trim` and `market` assertions, leaving real production candidates at `REQUIRES_REVIEW` with zero database writes. To achieve safe automated canonical promotion, RigArchive requires a trusted source and normalization architecture for factory grade taxonomy and market applicability.

Without explicit rules, automated ingestion risks introducing arbitrary source text as canonical grades, laundering caller request context into canonical market facts, manufacturing invalid Cartesian combinations, or conflating regulatory certification with commercial sales identity.

## Decision

Adopt the following durable architecture for manufacturer grade taxonomy, market applicability normalization, and cross-source configuration grouping:

1. **Manufacturer Grade Taxonomy Governs `trim`**:
   The normalized attribute key `trim` is defined precisely as **manufacturer-recognized factory grade/trim identity** (e.g., `SR5`, `SR5 Premium`, `TRD Off-Road`, `Limited`). Arbitrary source trim text or raw string inequality MUST NOT be treated as proof of canonical grade identity without first-party manufacturer taxonomy evidence.

2. **Factory Grade vs. Option Package Boundary**:
   Factory grade taxonomy disambiguates factory model lines from option packages, distributor/dealer accessory packages (e.g., `XP Predator Package`), and individual options. Option packages and dealer accessories belong exclusively in Observation or Knowledge domains; the Reference domain models factory engineering configurations.

3. **Commercial Sales Market Definition**:
   `VehicleDefinition.market` is defined as the **manufacturer commercial sales/applicability market** (`US`, `CA`, `OT`) for which a factory vehicle configuration was cataloged and offered to commercial buyers. Regulatory jurisdiction (e.g., EPA emissions certification or CMVSS safety compliance) provides supporting regulatory evidence, but regulatory jurisdiction is NOT semantically identical to commercial sales market.

4. **Source-Independence Test for Market Evidence**:
   A market value may become normalized evidence ONLY when the source artifact or acquisition definition independently establishes that applicability scope. If a value merely repeats caller request parameters or adapter request settings (`target_context`), it MUST REMAIN CONTEXT and MUST NOT be laundered into canonical market evidence.

5. **Explicit Source Applicability Provenance**:
   Independently established source applicability metadata must be represented with explicit provenance semantics (`source_applicability`), remaining distinct from request context (`target_context`) and caller intent (`CandidateIdentity`). Source applicability metadata remains provenance and must pass through assertion extraction and normalization before canonical promotion.

6. **Prohibition on Unsupported Cartesian Candidate Generation**:
   Candidate construction MUST NOT generate unsupported Cartesian combinations from independently observed dimensions (e.g., 8 manufacturer grades $\times$ 3 EPA records MUST NOT automatically produce 24 candidate configurations). Every candidate combination must be supported by evidence that those attributes coexist in that factory configuration.

7. **Attribute Equality is NOT a Cross-Source Join Key**:
   Matching field values across independent sources (e.g., EPA `4WD` == Toyota `4WD`) does not, by itself, prove that records represent the same factory configuration. Cross-source aggregation into a single candidate requires an evidence-backed correspondence (e.g., direct manufacturer configuration matrix, explicit source cross-reference, or VIN pattern applicability).

8. **Source-Native Configuration Identifiers**:
   Manufacturer model/order codes (e.g., Toyota model code `8666`) populate `SourceConfigurationIdentity` as source-native identity evidence. They MUST NOT be directly promoted to RigArchive canonical entity keys.

## Rationale

- **Canonical Truth**: Ensures that `VehicleDefinition` records represent genuine, evidence-backed factory configurations as defined by the manufacturer.
- **Context Integrity**: Prevents caller assumptions or adapter request parameters from improperly mutating database records without source evidence.
- **Safety Against Combinatorial Explosion**: Enforces that candidate construction reflects real-world factory offerings rather than invalid Cartesian combinations of unlinked source records.

## Consequences

### Positive
- Production pipeline can reach canonical `CREATE` safely when manufacturer specification evidence is acquired.
- Canonical Reference records maintain total evidence traceability and domain authority.
- Clear boundary between factory grades and dealer/distributor accessory packages.

### Negative
- Automated promotion requires acquiring authoritative manufacturer specification artifacts or dataset fixtures before production candidate creation occurs.
- Cross-source grouping between EPA and manufacturer records requires explicit evidence correspondence rather than simple field matching.

## Alternatives Considered

- **Global Source Precedence**: Declaring manufacturer sources to always override EPA/NHTSA across all fields. Rejected because authority varies by concept and evidence should corroborate rather than unilaterally overwrite.
- **Context Laundering**: Allowing `target_context["market"] = "US"` to become canonical evidence without source scoping proof. Rejected because it violates the Evidence Trust Boundary.
- **Cartesian Product Generation**: Pairing all EPA records with all manufacturer grades. Rejected because it creates non-existent factory vehicle definitions.
