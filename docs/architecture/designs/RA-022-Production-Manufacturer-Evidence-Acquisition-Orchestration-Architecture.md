# RA-022 — Production Manufacturer Evidence Acquisition & Orchestration Architecture

## 1. Purpose & Overview

This architecture document defines the production acquisition, raw snapshot retention, extraction provenance, and orchestration pipeline for ingesting real manufacturer-origin specification evidence into RigArchive. Building upon the contracts established in [RA-011](file:///Users/esse/dev/Rigarchive/docs/architecture/designs/RA-011-Ingestion-Schema-Intermediate-Serialization-Design.md)–[RA-021](file:///Users/esse/dev/Rigarchive/docs/implementation/tasks/RA-021-manufacturer-specification-evidence-acquisition-normalization-implementation.md), [ADR-0005](file:///Users/esse/dev/Rigarchive/docs/architecture/ADR/ADR-0005-Manufacturer-Grade-Taxonomy-Market-Applicability-Normalization.md), and [ADR-0006](file:///Users/esse/dev/Rigarchive/docs/architecture/ADR/ADR-0006-Immutable-Raw-Acquisition-Snapshots-Layered-Manufacturer-Profiles.md), this document establishes how heterogeneous first-party manufacturer publications (JSON datasets, static HTML tables, PDF ordering guides) are acquired immutably, extracted traceably into Tier 1 `SourceAssertionSet` artifacts, normalized into Tier 2 `NormalizedInterpretation` objects, aggregated into `CandidateConfigurationDocument` candidates, and planned against canonical database records via dry-run `plan_candidate_import()` execution.

## 2. Integration with Existing Ingestion Pipeline

The production acquisition pipeline integrates seamlessly with the established RA-011–RA-021 contracts:

```text
Authoritative Manufacturer Publication (JSON / HTML / PDF)
    ↓
Publication Source Profile (Locators, Transport, Extraction Rules)
    ↓
Raw Source Artifact Storage (storage/raw_source_artifacts/ + SHA-256 Hash)
    ↓
Source-Specific Extraction (1 SourceAssertionSet per configuration row)
    ↓
Manufacturer Normalization (ManufacturerNormalizer & ManufacturerProfile)
    ↓
Candidate Construction Engine (construct_candidate_configuration)
    ↓
Canonical Import Planning Engine (plan_candidate_import)
    ↓
CanonicalImportPlan Report (ELIGIBLE / CREATE, REQUIRES_REVIEW, INELIGIBLE)
    ↓
STOP (Zero automatic database writes)
```

## 3. Empirical Cross-Manufacturer Validation (RA-022A Findings)

The architecture was empirically validated across four distinct manufacturer publication ecosystems in the RA-022A research study:

* **Toyota USA (Control)**: 2020 4Runner product press kit matrix (`pressroom.toyota.com`). Structured JSON/HTML tables, official term `"Grade"`, explicit 4-digit order model codes (`8666`).
* **Ford Motor Company**: 2021 Bronco press kit specs & dealer order guides (`media.ford.com`). PDF order guides, official term `"Series"`, style/body codes (`E5A`/`E5B`) + equipment group codes (`312A`).
* **Jeep / Stellantis North America**: 2021 Wrangler press release & order guides (`media.stellantisnorthamerica.com`). PDF order guides, terms `"Model"`/`"Edition"`, package codes (`24G` Sahara), model codes (`JLJL74`).
* **Mercedes-Benz USA**: 2021 E-Class newsroom releases (`media.mbusa.com`). Static HTML press releases, term `"Model Variant"`, zero published model codes (`structural_row` identity).

Key empirical conclusions:
1. Manufacturer terminology and publication formats vary substantially.
2. All studied manufacturers present complete coexisting configurations in row-structured tables.
3. Structurally grouped rows without native order codes are represented cleanly via `structural_row` identity.
4. Synthetic attribute-derived composite identity is unnecessary and rejected.

## 4. Layered Profile Architecture

To handle manufacturer and publication variation without monolithic code duplication, RA-022 establishes a layered profile model:

```text
Manufacturer Profile (Taxonomy & Identity Semantics)
    ├── toyota_rules.py (Toyota Grade taxonomy, model_code rules)
    ├── ford_rules.py (Ford Series taxonomy, style_code rules)
    └── jeep_rules.py (Jeep Edition taxonomy, package_code rules)

Publication Source Profile (Acquisition, Snapshot & Extraction)
    ├── toyota_usa_pressroom_json (Fetch locator, JSON extractor, Scope="US")
    ├── ford_us_media_html (Fetch locator, HTML table extractor, Scope="US")
    └── jeep_us_order_guide_pdf (Fetch locator, PDF table extractor, Scope="US")
```

* **`ManufacturerProfile`**: Owns manufacturer grade/series taxonomy mappings into normalized `trim`, package classification, and native configuration identity strategies.
* **`PublicationSourceProfile`**: Owns URL locators, HTTP transport options, raw snapshot capture, `SourceApplicability` scope, and source-specific raw-to-structured extractor logic.

A monolithic per-manufacturer adapter model is rejected because single manufacturers (e.g. Ford) publish across pressroom HTML, PDF order guides, and media matrices requiring distinct fetch and extraction mechanics.

## 5. Raw Source Artifact Retention & Content Hashing

* **Immutable Retention**: Every production acquisition operation MUST retain the acquired raw source payload (HTML, JSON, PDF, CSV, XLS) as an immutable evidence snapshot before structured extraction occurs.
* **Storage Location**: Saved to raw source artifact storage (`storage/raw_source_artifacts/<source_id>/<year>/<hash>.<ext>`). Raw snapshots are primary ingestion evidence, not temporary backups.
* **Durable Metadata Envelope**: An in-memory acquisition result carries raw bytes temporarily during acquisition. The durable metadata envelope references stored content paths (`storage_locator`) rather than embedding large byte arrays inside JSON envelopes.
* **Full SHA-256 Hashing**: Revision detection and byte-content identity use the full 64-character SHA-256 hex digest computed over raw body bytes. Shortened hash strings are used for display/logging only.
* **Revision Model**:
  * Same locator + same SHA-256 $\rightarrow$ Unchanged content snapshot.
  * Same locator + different SHA-256 $\rightarrow$ New content snapshot (retained alongside historical snapshots).

## 6. Extraction Provenance Requirements

Structured assertions derived from raw snapshots MUST preserve complete provenance traceability to reproduce and audit extraction:

* **Required Provenance Fields**: Raw artifact hash, original source locator, source-local element/table/row path, extractor identity/version, and extraction mode (`deterministic_structured_parser`, `source_specific_parser`, `manually_verified_transcription`).
* **Contract Boundary**: Existing `SourceAssertion.source_context` string MUST NOT be overloaded with hidden JSON schemas. Structured extraction provenance is required conceptually, while its exact contract representation is deferred to RA-023 implementation planning.

## 7. Native vs. Structural Configuration Identity

Configuration identity strength is categorized into two safe, evidence-backed classes:

1. **Explicit Source-Native Identity**: Official manufacturer order/model/style code (Toyota `8666`, Ford `E5B`, Jeep `JLJL74`). Preserved as `SourceConfigurationIdentity` evidence (`identity_type = "model_code"`).
2. **Source-Local Structural Identity**: Sources lacking published order codes (Mercedes-Benz `media.mbusa.com`) use a structural identifier combining raw artifact hash + table/row path (`identity_type = "structural_row"`). This identifies that exact source-local structure and is not promoted as a global manufacturer identity.

## 8. Rejection of Synthetic Composite Attribute Identity

The earlier proposed `composite_row` identity (synthesizing identifiers from attribute tuples like `Limited+4WD+V6`) is **STRICTLY REJECTED**. Synthesizing configuration identity from attribute values risks context laundering and violates [ADR-0005](file:///Users/esse/dev/Rigarchive/docs/architecture/ADR/ADR-0005-Manufacturer-Grade-Taxonomy-Market-Applicability-Normalization.md) (attribute equality is not a join key). All uncoded sources MUST use source-local `structural_row` identity when structurally grouped by the source.

## 9. Configuration Coexistence & Cartesian Protection

* **Coexistence Rule**: Extractors create **one `SourceAssertionSet` per coexisting configuration row** from an authoritative publication table.
* **Cartesian Product Protection**: Unsupported Cartesian expansion (8 trims $\times$ 3 engines != 24 candidates) is strictly prohibited. Every candidate represents a real-world coexisting configuration.

## 10. Multi-Document Linking Rules

Multiple manufacturer documents MAY be linked into a single configuration evidence set ONLY when an explicit, evidence-backed relationship key (e.g. shared `model_code` `"8666"` or explicit order cross-reference) establishes their correspondence. Joining unlinked documents based on string equality (`trim = "SR5"`) is STRICTLY PROHIBITED. Unlinked multi-document attributes remain unjoined `REQUIRES_REVIEW` evidence.

## 11. Taxonomy & Option Package Boundaries

* **`trim` Semantics**: Normalized `trim` means manufacturer-recognized factory grade/trim identity. Source terms (`Grade`, `Series`, `Model Variant`, `Edition`) map to `trim` only when recognized by manufacturer taxonomy rules.
* **Package Boundary**: Option packages (Ford Equipment Groups, Jeep Customer Preferred Packages, Toyota accessory packages) remain distinct from `trim` and are preserved separately in raw assertions or unmapped interpretations.

## 12. SourceApplicability & Market Semantics

`PublicationSourceProfile` defines how independently established commercial market applicability is obtained (`SourceApplicability.market = "US"`, `applicability_basis = "first_party_publisher_scope"`). Publisher jurisdiction alone is not automatically commercial market. `target_context` remains caller/request context and is NEVER laundered into canonical facts.

## 13. Source-Format Strategies & PDF / Dynamic Boundaries

* **Structured Sources (JSON/CSV)**: Extracted via deterministic structured parsers.
* **Static HTML Tables**: Extracted via source-specific table parsers.
* **Authoritative PDFs**: Raw PDF payload is retained immutably. Extraction uses source-specific PDF parsers or manually verified transcriptions. Universal PDF table parsing is NOT promised.
* **Dynamic Sources**: Browser automation (Puppeteer/Playwright) is deferred. Configurator APIs are accessed directly as static data endpoints where available.

## 14. Manual Transcription Role

Manually verified transcriptions (such as RA-021's Toyota fixture) are first-class extraction operations (`extraction_mode = "manually_verified_transcription"`). They preserve authoritative raw source locators, source-local paths, and standard `SourceAssertionSet` outputs.

## 15. Security & Operational Boundaries

* **Transport Isolation**: `default_http_transport` using `urllib.request` with strict TLS certificate verification (`ssl.create_default_context()`), finite timeouts (10s), and explicit User-Agent.
* **Safeguards**: Configurable size limits per profile/content-type, MIME-type allowlists, fixed source locators (no recursive crawling).

## 16. Idempotency & Reprocessing Strategy

* **Acquisition Idempotency**: Content hashing prevents duplicate raw snapshot storage when payload is unchanged.
* **Reprocessing**: Retained raw snapshots allow extractors and normalizers to be upgraded and re-executed offline without re-downloading source payloads.

## 17. Production Orchestration Boundary & Initial Operating Mode

Production acquisition orchestration is operator-invoked via CLI command and MUST stop automatically at `plan_candidate_import()`, outputting a dry-run execution report:

```text
Operator Command -> Acquire Raw Snapshot -> SHA-256 Hash -> Store Raw Snapshot -> Extract AssertionSets -> Normalize -> Build Candidates -> Plan Import (plan_candidate_import) -> Dry-Run Report -> STOP
```

Zero automatic canonical database writes (`execute_candidate_import`) are performed. Automated schedulers and recurring crawlers are excluded from initial production scope.

## 18. Persistence Boundary

No new Django ORM models are required for initial production acquisition. Raw snapshots are stored in file-backed raw artifact storage (`storage/raw_source_artifacts/`). Staging ORM models are not created.

## 19. Next Implementation Milestone (RA-023 Scope)

**RA-023 — Production Manufacturer Artifact Acquisition & Dry-Run Orchestration Implementation**

* **Narrow Initial Scope**:
  1. Read-only implementation planning pass.
  2. Operator-invoked CLI command (`acquire_manufacturer_specs`).
  3. Single approved source profile initially (Toyota USA Pressroom control).
  4. Immutable raw snapshot retention (`storage/raw_source_artifacts/`) with full SHA-256 content hashing.
  5. Deterministic extraction into Tier 1 `SourceAssertionSet` artifacts.
  6. `ManufacturerNormalizer` transformation.
  7. Candidate building (`construct_candidate_configuration`).
  8. Downstream dry-run import planning (`plan_candidate_import`).
  9. Operator dry-run execution summary report.
  10. Zero automatic canonical writes.

## 20. Explicit Deferred Items

* Browser automation / Headless browser crawlers.
* Automated recurring crawlers / background acquisition schedulers.
* Automatic canonical write execution.
* Cross-source fuzzy joins.
* Automatic updates/deletes of existing canonical Reference records.
* Ingestion ORM staging models.
