# ADR-0006: Immutable Raw Acquisition Snapshots & Layered Manufacturer Profile Architecture

- **Status**: Accepted  
- **Date**: 2026-08-15  

## Context

RigArchive's canonical promotion pipeline ([ADR-0004](file:///Users/esse/dev/Rigarchive/docs/architecture/ADR/ADR-0004-Canonical-Reference-Matching-Import-Promotion-Strategy.md), [ADR-0005](file:///Users/esse/dev/Rigarchive/docs/architecture/ADR/ADR-0005-Manufacturer-Grade-Taxonomy-Market-Applicability-Normalization.md), [RA-019](file:///Users/esse/dev/Rigarchive/docs/implementation/tasks/RA-019-canonical-reference-import-planning-create-only-execution-implementation.md), [RA-021](file:///Users/esse/dev/Rigarchive/docs/implementation/tasks/RA-021-manufacturer-specification-evidence-acquisition-normalization-implementation.md)) converts validated `CandidateConfigurationDocument` artifacts into canonical `VehicleDefinition` records when evidence exists for 8 required concepts (`make`, `model`, `model_year`, `generic_drive_classification`, `engine_displacement_liters`, `engine_cylinders`, `trim`, `market`).

Empirical cross-manufacturer research ([RA-022A](file:///Users/esse/dev/Rigarchive/docs/architecture/designs/RA-022-Production-Manufacturer-Evidence-Acquisition-Orchestration-Architecture.md)) across Toyota, Ford, Jeep/Stellantis, and Mercedes-Benz demonstrated that real-world manufacturer publication ecosystems exhibit material variation across publication formats (JSON, static HTML, multipage PDF ordering guides), taxonomy vocabulary (`Grade`, `Series`, `Model`, `Model Variant`), configuration identifiers, package models, and multi-document relationships.

To ingest real manufacturer evidence reproducibly at scale without compromising provenance auditing, Cartesian safety, or canonical promotion integrity, RigArchive requires a durable architecture for production source acquisition, raw artifact retention, and profile layering.

## Decision

Adopt the following durable architectural principles for production manufacturer evidence acquisition, raw artifact retention, configuration identity, and orchestration:

1. **Immutable Raw Source Artifact Retention**:
   Every production acquisition operation MUST retain the acquired raw source payload (HTML, JSON, PDF, CSV, XLS) as an immutable evidence snapshot before structured extraction occurs. Re-acquiring a source locator that yields modified content MUST store a new immutable snapshot with a new revision provenance record. Historical snapshots MUST NEVER be overwritten or silently deleted.

2. **Full SHA-256 Byte-Content Hashing & Revision Identity**:
   Durable byte-content identity and revision detection MUST be computed using the full 64-character SHA-256 hex digest over uncompressed raw payload bytes. A shortened hash string MAY be used ONLY for display or logging. Content-hash equality establishes byte-identical snapshot content; a changed content hash establishes a content revision but does NOT automatically imply a canonical vehicle configuration revision.

3. **Architectural Layering of Manufacturer & Publication Profiles**:
   Manufacturer domain concerns and publication acquisition concerns MUST be architecturally separated:
   * **Manufacturer Profile**: Owns manufacturer-recognized taxonomy mappings (`trim` definitions), option package classification, configuration identity strategies, and manufacturer interpretation rules.
   * **Publication Source Profile**: Owns source locators, fetch transport options, content-type expectations, `SourceApplicability` scope, raw snapshot capture, and source-specific extraction logic.
   A monolithic per-manufacturer adapter model is explicitly rejected because publication structures vary within a single manufacturer's ecosystem.

4. **Preservation of Source-Native Configuration Identifiers**:
   Authoritative sources that publish explicit manufacturer configuration identifiers (e.g., Toyota order model codes, Ford style/body codes, Jeep package codes) MUST preserve those codes as `SourceConfigurationIdentity` evidence (`identity_type = "model_code"`). Source-native codes MUST NOT be directly promoted to RigArchive canonical entity primary keys.

5. **Source-Local Structural Identity for Uncoded Sources**:
   Authoritative sources that explicitly present complete configuration rows or sections but publish no stable manufacturer configuration code (e.g., Mercedes-Benz media specification releases) MUST be assigned a source-local structural row identity (`identity_type = "structural_row"`, combining raw artifact hash + table/row path). This identity represents that exact source-local structure and MUST NOT be promoted as a global manufacturer identity.

6. **Prohibition of Synthetic Attribute-Derived Composite Identity**:
   Synthesizing configuration identity from attribute tuples (e.g. `Limited+4WD+V6`) is STRICTLY PROHIBITED. Attribute values MUST NOT be combined to fabricate artificial configuration codes (`composite_row` identity is rejected). Legitimate uncoded configurations MUST use source-local structural identity when structurally grouped by the source.

7. **Explicit Evidence-Backed Multi-Document Linking**:
   Multiple manufacturer documents MAY be linked into a single configuration evidence set ONLY when an explicit, evidence-backed relationship key (e.g. shared model/style code or manufacturer order cross-reference) establishes their correspondence. Linking unlinked documents based on string equality (`trim = "SR5"`) is STRICTLY PROHIBITED. Unlinked multi-document attributes remain unjoined `REQUIRES_REVIEW` evidence.

8. **Plan-First Production Orchestration Boundary**:
   Initial production acquisition orchestration MUST be manually invoked by an operator and MUST stop automatically at `plan_candidate_import()`, producing an in-memory `CanonicalImportPlan` and dry-run execution report (`ELIGIBLE` / `CREATE`, `REQUIRES_REVIEW`, `INELIGIBLE`). Production acquisition orchestration MUST NOT automatically execute canonical database writes (`execute_candidate_import`).

9. **Structured Extraction Provenance Requirement**:
   Structured assertions derived from raw snapshots MUST preserve enough provenance information to reproduce and audit extraction (including raw artifact reference, source locator, element/table path, extractor identity/version, and extraction mode). The exact contract representation is deferred to implementation inspection during development planning.

## Rationale

- **Auditability & Link-Rot Resilience**: Retaining raw source snapshots immutably ensures that RigArchive's evidence base remains fully auditable and reproducible even if manufacturer websites alter URL structures or remove historical press releases.
- **Protection Against Context Laundering & False Joins**: Rejecting synthetic composite IDs and prohibiting unlinked multi-document joins protects the canonical Reference database against false candidate aggregation.
- **Operational Safety**: Stopping production acquisition at dry-run planning prevents external web scraping from unexpectedly mutating canonical database records without explicit operator review.

## Consequences

### Positive
- Ingestion pipeline can ingest heterogeneous primary manufacturer sources (JSON, HTML, PDF) reproducibly.
- Raw evidence can be reprocessed offline when extractors or normalizers are upgraded.
- Clear separation between manufacturer taxonomy vocabulary and publication fetch mechanics.

### Negative
- Production acquisition requires maintaining raw source artifact storage.
- Sources lacking explicit cross-reference keys cannot automatically join attributes across separate documents.

## Alternatives Considered

- **Monolithic Adapter per Manufacturer**: Rejected because single manufacturers (e.g. Ford) publish across pressroom HTML, PDF order guides, and media matrices requiring different fetch/extraction mechanics.
- **Synthetic Attribute Identity (`composite_row`)**: Rejected because generating identifiers from attribute values risks context laundering and violates the rule that attribute equality is not a join key.
- **Automated Canonical Write Execution**: Rejected because automated web acquisition must not bypass human dry-run planning review.
