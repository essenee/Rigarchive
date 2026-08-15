# ADR-0004: Canonical Reference Matching & Import Promotion Strategy

- **Status**: Accepted  
- **Date**: 2026-08-15  

## Context

RigArchive's ingestion pipeline acquires external data from public sources (NHTSA, EPA), normalizes assertions into structured interpretations, and constructs transient candidate configuration documents (`CandidateConfigurationDocument`). The final phase of ingestion is promoting eligible candidate artifacts into persistent canonical Reference domain records (`VehicleDefinition`).

Without explicit promotion rules, automated ingestion risks corrupting canonical Reference identity, promoting uncorroborated caller context into canonical facts, overwriting manually curated database records, or collapsing distinct real-world factory configurations into underspecified placeholder rows.

## Decision

Adopt the following durable architecture for candidate-to-canonical matching and import promotion:

1. **Two-Tier Semantic Tier Separation**:
   Candidate configuration documents (`CandidateConfigurationDocument`) are transient, non-canonical, JSON-serializable hypotheses existing outside the database. Canonical vehicle definitions (`VehicleDefinition`) are persistent, authoritative, database-backed Django ORM records. Candidate construction success does NOT equal canonical import eligibility.

2. **Strict Evidence Trust Boundary**:
   Canonical Reference data must be supported by normalized source evidence. Caller workflow context (`CandidateIdentity`) declares search/aggregation intent but is NOT source evidence. Context-only fields (e.g. `CandidateIdentity.trim_name = "SR5"`) must NEVER be silently written into a new canonical `VehicleDefinition` record as source evidence. Candidates lacking evidence-backed attributes on multi-trim vehicle models require human review.

3. **Initial Create-Only & No-Op Import Policy**:
   Automated ingestion is strictly CREATE-ONLY for proven-distinct new configurations and NO-OP for exact existing representations. The automated importer will NEVER update, overwrite, or delete existing canonical `VehicleDefinition` records, and will NEVER automatically create parent `Manufacturer`, `VehicleModel`, or `Generation` entities.

4. **Database Representation Key vs. Canonical Identity**:
   The unique constraint `(generation_id, slug)` is the current database uniqueness key and deterministic storage representation key. It is NOT a universal real-world semantic identity. Slug matching guarantees storage deduplication; it does not replace semantic matching logic.

5. **Plan-First Execution Model**:
   Canonical import operates in two decoupled phases: read-only planning (`plan_candidate_import`) producing a transient `CanonicalImportPlan`, followed by transactional write execution (`execute_candidate_import`) inside `transaction.atomic()`.

6. **Review Flagging under Ambiguity**:
   Any candidate exhibiting attribute conflicts, context contradictions, missing trim evidence on multi-trim models, or ambiguous parent entity matching produces a plan flagging human review with zero database writes.

## Rationale

- **Canonical Integrity**: Enforces that canonical database records represent verified domain truth rather than speculative context or unmapped source noise.
- **Safety Against Data Loss**: A create-only policy ensures that pre-existing manually curated Reference records can never be degraded or corrupted by automated ingestion processes.
- **Inspectability**: Two-phase planning enables CLI dry-run inspection, automated testing, and administrative review prior to database mutations.

## Consequences

### Positive
- Canonical Reference records maintain total domain authority and evidence traceability.
- Erroneous or underspecified external data cannot corrupt database tables.
- Importer execution is completely deterministic and idempotent.

### Negative
- Candidates lacking evidence-backed trim (such as raw EPA payloads) will flag human review rather than automatically creating canonical records until dedicated trim acquisition/normalization rules are introduced.
- Parent entity seeding (`Manufacturer`, `VehicleModel`, `Generation`) must precede automated candidate import.

## Alternatives Considered

- **Direct Ingestion to Database**: Writing acquired data directly into Django models. Rejected because it corrupts canonical identity and destroys evidence provenance.
- **Context-Only Promotion**: Using `CandidateIdentity.trim_name` to populate canonical fields without source evidence. Rejected because it violates the Evidence Trust Boundary.
- **Automated Ingestion Updates**: Allowing the importer to update existing `VehicleDefinition` fields. Rejected to prevent automated degradation of manually curated canonical records.
