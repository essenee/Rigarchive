# RA-018 — Canonical Reference Matching & Import Architecture

**Status**: Accepted  
**Date**: 2026-08-15  
**Domain**: Reference Domain — Data Ingestion Pipeline  

---

## 1. Executive Summary

RA-018 establishes the architectural design for evaluating transient candidate configuration documents (`CandidateConfigurationDocument`) produced by RA-016/RA-017 and determining their eligibility, parent entity resolution, semantic matching, and promotion into canonical Reference-domain database records (`VehicleDefinition`).

This architecture bridges candidate configuration construction (RA-016/RA-017) with canonical Reference database persistence (RA-019), defining how RigArchive promotes evidence-backed candidate artifacts into canonical entities without compromising the strict Evidence Trust Boundary, degrading manually curated Reference domain records, or promoting uncorroborated context data into canonical truth.

---

## 2. Purpose

The purpose of RA-018 is to define how RigArchive safely, deterministically, and reproducibly resolves, matches, and imports eligible candidate configuration documents while:
* enforcing the strict **Evidence Trust Boundary** (`Source Evidence → Candidate → Canonical Promotion`), prohibiting caller workflow context (`CandidateIdentity`) from being silently written into canonical fields as source evidence;
* distinguishing **real-world canonical factory-configuration identity** from the current **database uniqueness/representation key** (`generation_id`, `slug`);
* establishing that `trim_name = ""` represents missing trim evidence (not a canonical trim named "blank") and requiring explicit evidence-backed trim for automatic promotion on multi-trim vehicle model years;
* establishing an **Initial Create-Only & No-Op Policy** for automated import, prohibiting automated updates to existing `VehicleDefinition` records, deletion of canonical data, or automatic creation of parent `Manufacturer`, `VehicleModel`, or `Generation` entities;
* defining a **Two-Phase Plan-First Execution Architecture** (`plan_candidate_import` → `execute_candidate_import`) that performs read-only eligibility analysis and parent resolution prior to transactional write execution;
* enforcing deterministic storage idempotency and transaction concurrency safeguards.

---

## 3. Scope

### Included in RA-018 Architectural Design
* Defining the promotion boundary separating transient candidate artifacts from persistent canonical `VehicleDefinition` database records.
* Establishing the semantic identity of `VehicleDefinition` and clarifying the distinction between real-world identity and the current `(generation_id, slug)` database representation key.
* Establishing the strict Evidence Trust Boundary prohibiting context-only field promotion.
* Defining trim/grade sufficiency, missing trim rules, engine presentation semantics, and market provenance requirements.
* Establishing deterministic parent entity resolution (`Manufacturer`, `VehicleModel`, `Generation`).
* Formulating the import eligibility model (`ELIGIBLE`, `REQUIRES_REVIEW`, `INELIGIBLE`) and semantic matching categories (`EXACT_EXISTING_MATCH`, `PROVEN_DISTINCT_NEW_RECORD`, `UNDERSPECIFIED_CANDIDATE`, `CONFLICT_WITH_EXISTING_CANONICAL`, `AMBIGUOUS_MATCH`, `INELIGIBLE`).
* Establishing the Create-Only & Manual Data Protection policy for automated ingestion.
* Defining storage idempotency, database representation keys, and concurrency safeguards (`transaction.atomic()` + pre-check + `IntegrityError` catch).
* Defining the transient, in-process `CanonicalImportPlan` dataclass and two-phase execution boundary.
* Reassessing the controlled 5th-Generation Toyota 4Runner NHTSA/EPA case study under strict promotion rules.
* Recommending the implementation boundary for RA-019 and identifying future source/normalization dependencies.

### Excluded from RA-016/RA-018 (Non-Goals)
* Implementing Python importer logic or service modules (deferred to RA-019).
* Modifying Django models (`reference/models.py`) or creating DB migrations.
* Modifying candidate contracts (`reference/ingestion/contracts.py`) or serializers.
* Automated updating or merging of existing canonical Reference records.
* Automated creation of parent `Manufacturer`, `VehicleModel`, or `Generation` records.
* Web-based human adjudication UI or persistent staging tables.
* Production background job scheduling or automated acquisition orchestration.

---

## 4. Governing Architecture & Authority

Governed by the approved [RA-010 Source Mapping Architecture](file:///Users/esse/dev/Rigarchive/docs/architecture/designs/RA-010-Reference-Ingestion-Source-Mapping-Architecture.md), [RA-011 Ingestion Serialization Architecture](file:///Users/esse/dev/Rigarchive/docs/architecture/designs/RA-011-Ingestion-Schema-Intermediate-Serialization-Design.md), [RA-014 Source Assertion Normalization Architecture](file:///Users/esse/dev/Rigarchive/docs/architecture/designs/RA-014-Source-Assertion-Normalization-Mapping-Architecture.md), and [RA-016 Candidate Construction Architecture](file:///Users/esse/dev/Rigarchive/docs/architecture/designs/RA-016-Candidate-Configuration-Construction-Aggregation-Architecture.md), and operating over executable implementations in [RA-012](file:///Users/esse/dev/Rigarchive/docs/implementation/tasks/RA-012-intermediate-serialization-implementation.md), [RA-013](file:///Users/esse/dev/Rigarchive/docs/implementation/tasks/RA-013-public-source-acquisition-implementation.md), [RA-015](file:///Users/esse/dev/Rigarchive/docs/implementation/tasks/RA-015-source-assertion-normalization-implementation.md), and [RA-017](file:///Users/esse/dev/Rigarchive/docs/implementation/tasks/RA-017-candidate-configuration-construction-aggregation-implementation.md).

```text
SourceAssertionSet(s) [RA-013]
    ↓
NormalizedInterpretation(s) [RA-015]
    ↓
CandidateConfigurationDocument [RA-016 / RA-017]
    ↓
[RA-018 CANONICAL PROMOTION BOUNDARY]
    1. Read-Only Eligibility & Context Check
    2. Parent Entity Resolution (Manufacturer → VehicleModel → Generation)
    3. Trim & Technical Evidence Sufficiency Check
    4. Canonical Matching & Representation Key Building (target_slug)
    5. Plan Generation (CanonicalImportPlan: ELIGIBLE / REQUIRES_REVIEW / INELIGIBLE)
        ↓
    Transactional Execution [RA-019]
        ├── EXACT_EXISTING_MATCH ──► Idempotent No-Op (0 Writes)
        ├── PROVEN_DISTINCT_NEW_RECORD ──► Create VehicleDefinition
        └── UNDERSPECIFIED / CONFLICT ──► Flag Human Review (0 Writes)
```

---

## 5. Candidate-to-Canonical Promotion Boundary

The candidate tier and canonical tier represent fundamentally distinct semantic layers in RigArchive:

1. **Candidate Configuration (`CandidateConfigurationDocument`)**:
   * Transient, non-canonical, JSON-serializable artifact existing outside the database.
   * Evidence-backed aggregation describing a potential vehicle configuration hypothesis.
   * May be incomplete, ambiguous, or contain unverified caller context.
2. **Canonical Reference Record (`VehicleDefinition`)**:
   * Persistent, authoritative, database-backed Django ORM entity.
   * Assigned permanent integer PK, immutable UUID, and non-editable slug.
   * Represents verified, canonical domain truth governing the Reference domain.

**Promotion Rule**: A `CandidateConfigurationDocument` is NEVER automatically equivalent to a canonical record. Promotion requires passing structural validation, evidence sufficiency, parent entity resolution, and explicit matching classification.

---

## 6. VehicleDefinition Semantic Meaning vs. Database Representation Key

### Real-World Domain Identity vs. Model Fields
A canonical `VehicleDefinition` represents a recognized, distinct factory-produced vehicle configuration within a market, adhering to the manufacturer's trim taxonomy and powertrain specification.

The current Django `VehicleDefinition` model (`generation`, `model_year`, `trim_name`, `engine_name`, `drivetrain`, `market`, `slug`) is an **intentionally simplified first-version representation** of this domain concept (as documented in RA-010).

### Database Representation Key (`generation_id`, `slug`)
* **Role**: `(generation_id, slug)` is the **current database uniqueness key** and **deterministic representation key** enforcing deduplication under the current schema.
* **Non-Equivalence**: `(generation_id, slug)` is **NOT** a universal real-world semantic identity.
  * *Collapse Hazard*: Two distinct factory configurations (e.g. 2 different engine options with same 4.0L V6 displacement, or 2 distinct trims when trim is unmapped/blank) can generate identical slugs.
  * *Synonym Hazard*: Two different string representations of the same physical engine or trim can generate different slugs.
* **Storage Determinism**: `build_slug()` derives deterministically from `[model_year, trim_name, engine_name, drivetrain, market]`, providing current database representation deduplication rather than a permanent ontology.

---

## 7. Strict Evidence Trust Boundary

RigArchive enforces a strict **Evidence Trust Boundary**:

$$\text{Source Evidence} \longrightarrow \text{Candidate Aggregation} \longrightarrow \text{Canonical Promotion}$$

### Caller Context (`CandidateIdentity`) Rules
* `CandidateIdentity` is caller workflow request context. It defines the search/aggregation boundary.
* Context may assist consistency checks, surface contradictions, and route candidates.
* **Context Promotion Prohibition**: Context-only values **MUST NOT** be silently written into a new canonical `VehicleDefinition` field as if they were normalized source evidence.
* Example: `CandidateIdentity.trim_name = "SR5"` without normalized source evidence supporting `"SR5"` **MUST NOT** result in automatic creation of a canonical `VehicleDefinition` with `trim_name = "SR5"`. Such a candidate MUST be flagged as `REQUIRES_HUMAN_REVIEW` or classified as `INELIGIBLE_UNCORROBORATED_CONTEXT`.

---

## 8. Trim / Grade Sufficiency & Missing Evidence Rules

1. **Meaning of Blank Trim (`trim_name = ""`)**:
   `trim_name = ""` indicates **missing or unmapped trim evidence** under the current model. It is NOT a canonical manufacturer trim level named "blank".
2. **Multi-Trim Ineligibility Rule**:
   In any vehicle model year/generation where the manufacturer produced multiple distinct trims/grades, a candidate lacking normalized trim evidence **MUST NOT** be automatically promoted. Generating a slug like `2020-40l-v6-4wd-us` for a trim-unknown candidate creates an underspecified canonical record that collapses multiple distinct factory configurations into a single row.
3. **Single-Trim Base Model Exception (Conservative Formulation)**:
   Automatic creation of a `VehicleDefinition` with blank trim is permissible ONLY when independent evidence confirms that the manufacturer defined zero trim/grade distinctions for that model year and market (a monolithic base vehicle model). Current RA-018 does not implement automated proof of zero-trim distinction; therefore, blank-trim candidates on multi-trim models are classified as `REQUIRES_HUMAN_REVIEW`.

---

## 9. Engine Name Presentation Semantics

1. **Free-Text Presentation Role**: `VehicleDefinition.engine_name` is an intentionally simple free-text display field (e.g. `"4.0L V6"`).
2. **Deterministic Synthesis**: Synthesizing `"4.0L V6"` from mapped `engine_displacement_liters = 4.0L` and `engine_cylinders = 6` provides a standard display label. However:
   * It is NOT a manufacturer engine family code (e.g. `1GR-FE`).
   * Displacement and cylinder count alone do not distinguish every engine option (e.g., naturally aspirated vs turbocharged variants).
   * Synthesized `engine_name` alone does not establish complete real-world engine identity.
3. **Evidence Integration**: If an explicit mapped engine designation is emitted by normalization, it will integrate according to approved mapping/reconciliation rules without introducing undocumented canonical-import precedence shortcuts.

---

## 10. Market Provenance & Source Authority

1. **Workflow Scope**: The current controlled 4Runner study is US-market scoped.
2. **Source Authority Provenance**:
   * Acquisition target context and source authority metadata (`source_id = epa_fueleconomy` or `nhtsa_vpic`) establish US market applicability because EPA and NHTSA are US federal regulatory agencies whose scope is legally restricted to the US market.
   * Market assignment must be justified from explicit source/acquisition/candidate context approved for the artifact. Source identity alone must not become an implicit market inference for all future adapters.

---

## 11. Parent Entity Resolution (Manufacturer, VehicleModel, Generation)

Canonical promotion requires deterministic resolution of parent database entities prior to `VehicleDefinition` creation:

```text
Candidate Document Evidence
   │
   ├── 1. Manufacturer Resolution: Query Manufacturer where name__iexact == evidence_make
   │      ├── Found (Active) ──► Resolved Manufacturer
   │      └── Missing ─────────► INELIGIBLE_UNRESOLVED_MANUFACTURER (No auto-create)
   │
   ├── 2. VehicleModel Resolution: Query VehicleModel where manufacturer == resolved_mfr AND name__iexact == evidence_model
   │      ├── Found (Active) ──► Resolved VehicleModel
   │      └── Missing ─────────► INELIGIBLE_UNRESOLVED_VEHICLE_MODEL (No auto-create)
   │
   └── 3. Generation Resolution: Query Generation where vehicle_model == resolved_model AND start_year <= model_year <= (end_year or inf)
          ├── Exactly 1 Match ─► Resolved Generation
          ├── 0 Matches ───────► INELIGIBLE_UNRESOLVED_GENERATION (No auto-create)
          └── >1 Matches ──────► REQUIRES_HUMAN_REVIEW (Ambiguous year ranges)
```

**Rule**: The automated importer **NEVER** automatically creates `Manufacturer`, `VehicleModel`, or `Generation` records. Parent entity creation requires explicit administrative curation or seeding.

---

## 12. Refined Import Eligibility Model

An automated `VehicleDefinition` CREATE requires ALL of the following criteria:

1. **Schema Support**: `envelope.schema_version == "1.0.0"`.
2. **Review Clearance**: Top-level `reconciliation_and_review.requires_human_review == False`.
3. **No Evidence Conflicts**: No attribute state in `attribute_states` is `"conflicting"`.
4. **Parent Resolution**: `Manufacturer`, `VehicleModel`, and `Generation` deterministically resolved to existing active DB rows.
5. **Core Attribute Evidence**: `model_year`, `drivetrain`, `engine`, and `market` backed by normalized evidence or source authority provenance.
6. **Trim Sufficiency**: `trim_name` is explicitly supported by normalized source evidence, OR the model year is proven to have zero trim distinctions.
7. **No Uncorroborated Context Promotion**: No field relying solely on `CandidateIdentity` context is written into canonical data.
8. **Resolution Unambiguity**: Zero partial-match ambiguity with existing canonical records.

---

## 13. Existing / Partial / New Match Semantics

```text
┌──────────────────────────────────────────────────────────────────────────────────────────┐
│ 1. EXACT_EXISTING_MATCH                                                                  │
│    Candidate matches an existing DB row by (generation, slug) with identical technical   │
│    attributes. -> Action: IDEMPOTENT NO-OP. Return existing record. Zero DB writes.        │
├──────────────────────────────────────────────────────────────────────────────────────────┤
│ 2. PROVEN_DISTINCT_NEW_RECORD                                                            │
│    Candidate has complete, evidence-backed attributes defining a distinct factory        │
│    configuration not present in DB. -> Action: CREATE new VehicleDefinition.             │
├──────────────────────────────────────────────────────────────────────────────────────────┤
│ 3. UNDERSPECIFIED_CANDIDATE                                                              │
│    Candidate lacks required attributes (e.g. trim unknown on a multi-trim model year).   │
│    -> Action: DO NOT CREATE. Flag REQUIRES_HUMAN_REVIEW.                                 │
├──────────────────────────────────────────────────────────────────────────────────────────┤
│ 4. CONFLICT_WITH_EXISTING_CANONICAL                                                      │
│    Candidate matches an existing row's slug/identity but asserts conflicting technical   │
│    data. -> Action: DO NOT OVERWRITE. Flag REQUIRES_HUMAN_REVIEW.                        │
├──────────────────────────────────────────────────────────────────────────────────────────┤
│ 5. AMBIGUOUS_MATCH                                                                       │
│    Candidate matches multiple existing canonical records or overlaps multiple trims.       │
│    -> Action: DO NOT WRITE. Flag REQUIRES_HUMAN_REVIEW.                                       │
└──────────────────────────────────────────────────────────────────────────────────────────┘
```

**Key Distinction**: A different current slug (`build_slug()`) does **NOT** automatically prove a distinct real-world configuration. An underspecified candidate (missing trim) must not create a new row merely because its slug differs from existing trim-specified rows.

---

## 14. Create-Only & Manual Data Protection Policy

To preserve the absolute integrity of canonical Reference domain records, the automated importer operates under a strict **Initial Create-Only Policy**:

* **CREATE**: Permitted ONLY for `PROVEN_DISTINCT_NEW_RECORD` candidates.
* **NO-OP**: Executed for `EXACT_EXISTING_MATCH` candidates (zero writes).
* **NEVER UPDATE**: The automated importer will **NEVER** update, modify, or overwrite an existing `VehicleDefinition` record.
* **NEVER DELETE**: The automated importer will **NEVER** delete canonical records.
* **NEVER AUTO-CREATE PARENTS**: Missing `Manufacturer`, `VehicleModel`, or `Generation` entities stop import and require administrative curation.
* **PROTECT MANUALLY CURATED DATA**: Pre-existing manually created Reference domain records are immutable to automated ingestion. Disagreements with existing canonical data trigger human review.

---

## 15. Idempotency vs. Canonical Entity Resolution

* **Storage Idempotency**: Prevents duplicate database rows when re-running identical candidate inputs. Enforced by database unique constraint `UniqueConstraint(generation, slug)`.
* **Canonical Entity Resolution**: Evaluates whether a candidate describes a real-world vehicle configuration distinct from existing database entities.
* **Exclusion**: `candidate_reference` and `source_configuration_identities` (e.g. `epa_vehicle_id`, `nhtsa_make_id`) are transient/source-scoped identifiers and **MUST NEVER** be used as canonical matching or deduplication keys.

---

## 16. Transaction & Concurrency Strategy

Because a non-existent row cannot be locked with `select_for_update()`, the create-only concurrency strategy relies on atomic database representation checks and unique constraints:

1. Perform read-only resolution & import planning outside the transaction.
2. Enter `transaction.atomic()`.
3. Re-query `VehicleDefinition.objects.filter(generation=resolved_gen, slug=target_slug).first()`.
4. If row exists: Return `EXACT_EXISTING_MATCH` (Idempotent No-Op).
5. If row does not exist: Instantiate `VehicleDefinition(...)`, run `full_clean()`, and execute `save()`.
6. Wrap save block in `try...except IntegrityError:` to catch concurrent insert race conditions, gracefully falling back to `EXACT_EXISTING_MATCH`.

---

## 17. Transient `CanonicalImportPlan` Architecture

RA-018 approves a two-phase decoupled import architecture:

```python
# Phase 1: Pure Read-Only Planning (In-process, transient, non-persisted, 0 DB writes)
plan = plan_candidate_import(candidate_doc) -> CanonicalImportPlan

# Phase 2: Transactional Execution (Only if plan.is_eligible and plan.action == "create")
result = execute_candidate_import(plan) -> CanonicalImportResult
```

### `CanonicalImportPlan` Specification
A pure Python dataclass carrying:
* `candidate_reference`: str
* `eligibility_status`: `ELIGIBLE` | `REQUIRES_REVIEW` | `INELIGIBLE`
* `action`: `CREATE` | `NO_OP_EXACT_MATCH` | `FLAG_REVIEW` | `REJECT`
* `resolved_manufacturer_id`: Optional[int]
* `resolved_vehicle_model_id`: Optional[int]
* `resolved_generation_id`: Optional[int]
* `target_vehicle_definition_fields`: Dict[str, Any]
* `target_slug`: str
* `reasons`: List[str]

**Constraints**:
* `CanonicalImportPlan` is transient, in-process, and non-persisted. It is **NOT** an ORM staging model, a database table, or a durable review queue.
* Resolved primary keys carried in the plan are execution references; Phase 2 execution re-verifies DB state inside `transaction.atomic()` to ensure safety against stale plans.

---

## 18. Controlled 2020 Toyota 4Runner Empirical Study Reassessment

Evaluating current NHTSA + EPA normalized evidence for the 2020 Toyota 4Runner:

1. **Evidence-Supported Attributes**:
   * `make`: `"Toyota"` (NHTSA + EPA mapped assertions)
   * `model`: `"4Runner"` (NHTSA mapped assertion)
   * `model_year`: `2020` (EPA mapped assertion)
   * `drivetrain`: `"4WD"` (EPA mapped assertion `generic_drive_classification`)
   * `engine`: `"4.0L V6"` (EPA mapped displacement `4.0L` + cylinders `6`)
   * `market`: `"US"` (EPA/NHTSA source authority provenance)
2. **Missing Evidence**:
   * `trim_name`: **UNMAPPED in RA-015** (EPA raw descriptors remain unmapped Case A).
3. **Context Evaluation**:
   * `CandidateIdentity.trim_name = "SR5"` is caller workflow context. Under the strict Evidence Trust Boundary, `"SR5"` **CANNOT** be promoted into a canonical field without source evidence.
4. **Final Controlled Result**:
   * Because current evidence lacks normalized trim for a multi-trim model year, the 2020 4Runner candidate is classified as **underspecified**:
     `plan.eligibility_status = REQUIRES_REVIEW`  
     `plan.action = FLAG_REVIEW`  
   * The candidate produces a **dry-run plan flagging human review** and **ZERO database writes**.

---

## 19. Current Source Coverage & Data Gap Analysis

* **Primary Ingestion Data Gap**: Normalized manufacturer trim/grade identity.
* **Resolution Path**: As identified in RA-010, manufacturer-published market material (brochures, spec sheets, official press assets) represents the authoritative source for generation boundaries, trim taxonomies, and manufacturer feature terminology. Future acquisition adapters targeting manufacturer source material will supply normalized trim evidence, enabling automatic promotion without modifying the RA-018 promotion architecture.

---

## 20. Recommended Implementation Boundary for RA-019

The proposed implementation milestone following RA-018 is:  
**RA-019 — Canonical Reference Import Planning & Create-Only Execution Implementation**

### RA-019 Responsibilities
1. Implement pure Python package `reference/ingestion/importing/` (`planner.py`, `importer.py`).
2. Implement `plan_candidate_import(candidate_doc) -> CanonicalImportPlan`.
3. Implement `execute_candidate_import(plan) -> CanonicalImportResult` with `transaction.atomic()`, create-only policy, and `IntegrityError` safety.
4. Deliver comprehensive automated unit tests covering eligibility evaluation, parent resolution, dry-run planning, exact-match no-op, safe creation, and review flagging.

Current NHTSA/EPA candidates will plan cleanly into `FLAG_REVIEW` (no-write) due to missing trim evidence, establishing complete end-to-end pipeline machinery safely.

---

## 21. Relationship to ADR-0004

RA-018 is accompanied by **ADR-0004: Canonical Reference Matching & Import Promotion Strategy**, which formalizes durable architectural decisions:
1. Two-tier Candidate-to-Canonical promotion boundary.
2. Strict Evidence Trust Boundary (prohibiting uncorroborated context promotion).
3. Initial Create-Only & No-Op automated import policy.
4. `(generation, slug)` as database representation key, not universal identity.
5. Plan-First transactional execution model.

---

## 22. Summary of Architectural Decisions Approved by RA-018

1. **Promotion Boundary**: `CandidateConfigurationDocument` and `VehicleDefinition` are distinct semantic tiers.
2. **Evidence Trust Boundary**: Context-only fields (`CandidateIdentity`) cannot be silently written into canonical `VehicleDefinition` records without source evidence.
3. **Representation Key Distinction**: `(generation_id, slug)` is current storage uniqueness key, not real-world identity.
4. **Trim Sufficiency Rule**: `trim_name = ""` means missing trim; candidates lacking normalized trim on multi-trim model years require human review.
5. **Create-Only Policy**: Initial importer creates proven distinct records, executes no-ops on exact matches, and NEVER updates or deletes existing canonical data.
6. **Parent Protection**: Automated importer NEVER creates `Manufacturer`, `VehicleModel`, or `Generation` records.
7. **Plan-First Architecture**: Decoupled `CanonicalImportPlan` (read-only) + `execute_candidate_import` (transactional).
8. **Controlled Result**: Controlled 2020 4Runner candidate correctly flags `REQUIRES_REVIEW` due to unmapped trim evidence.
