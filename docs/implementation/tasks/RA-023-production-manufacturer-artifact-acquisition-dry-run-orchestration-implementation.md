# RA-023 — Production Manufacturer Artifact Acquisition & Dry-Run Orchestration Implementation

## Purpose

Implement the first production-oriented manufacturer artifact acquisition and dry-run orchestration pipeline. The pipeline acquires authoritative manufacturer raw HTML/PDF artifacts (via local file or live HTTPS request), stores immutable content-addressed snapshots with full SHA-256 digests in managed storage, links verified manually structured transcriptions via mechanical hash binding (`expected_raw_artifact_hash == actual_snapshot_hash`), produces Tier 1 `SourceAssertionSet` artifacts (schema `1.1.0`) carrying explicit `ExtractionProvenance`, normalizes assertions using `ManufacturerNormalizer`, constructs Tier 2 candidate configurations (`construct_candidate_configuration`), and executes downstream dry-run canonical import planning (`plan_candidate_import`) with verbatim operator report streaming. Operates in strict compliance with [RA-022 Production Manufacturer Evidence Acquisition & Orchestration Architecture](file:///Users/esse/dev/Rigarchive/docs/architecture/designs/RA-022-Production-Manufacturer-Evidence-Acquisition-Orchestration-Architecture.md) and [ADR-0006 Immutable Raw Acquisition Snapshots & Layered Manufacturer Profiles](file:///Users/esse/dev/Rigarchive/docs/architecture/ADR/ADR-0006-Immutable-Raw-Acquisition-Snapshots-Layered-Manufacturer-Profiles.md).

## Governing Architecture

Governed by [ADR-0006 Immutable Raw Acquisition Snapshots & Layered Manufacturer Profiles](file:///Users/esse/dev/Rigarchive/docs/architecture/ADR/ADR-0006-Immutable-Raw-Acquisition-Snapshots-Layered-Manufacturer-Profiles.md) and [RA-022 Production Manufacturer Evidence Acquisition & Orchestration Architecture](file:///Users/esse/dev/Rigarchive/docs/architecture/designs/RA-022-Production-Manufacturer-Evidence-Acquisition-Orchestration-Architecture.md). Operates within the established ingestion contract, candidate building, and canonical import planning boundaries of [RA-011](file:///Users/esse/dev/Rigarchive/docs/architecture/designs/RA-011-Ingestion-Schema-Intermediate-Serialization-Design.md), [RA-016](file:///Users/esse/dev/Rigarchive/docs/architecture/designs/RA-016-Candidate-Configuration-Construction-Aggregation-Architecture.md), [RA-019](file:///Users/esse/dev/Rigarchive/docs/implementation/tasks/RA-019-canonical-reference-import-planning-create-only-execution-implementation.md), [RA-020](file:///Users/esse/dev/Rigarchive/docs/architecture/designs/RA-020-Trim-Grade-Market-Applicability-Source-Normalization-Architecture.md), [ADR-0005](file:///Users/esse/dev/Rigarchive/docs/architecture/ADR/ADR-0005-Manufacturer-Grade-Taxonomy-Market-Applicability-Normalization.md), and [RA-021](file:///Users/esse/dev/Rigarchive/docs/implementation/tasks/RA-021-manufacturer-specification-evidence-acquisition-normalization-implementation.md).

## Architecture & Implementation Pipeline

The production manufacturer evidence acquisition and dry-run orchestration pipeline follows:

```text
operator-selected Toyota USA publication profile (--file / --url)
    ↓
authoritative Toyota raw HTML/PDF artifact
    ↓
RawSnapshotManager & storage/raw_source_artifacts/ (immutable raw snapshot)
    ↓
full SHA-256 content identity (sha256:<64_lowercase_hex>)
    ↓
verified derivative transcription (hash binding check)
    ↓
SourceAssertionSet (schema 1.1.0 + ExtractionProvenance)
    ↓
ManufacturerNormalizer & toyota_rules.py
    ↓
CandidateConfigurationDocument
    ↓
plan_candidate_import()
    ↓
dry-run CanonicalImportPlan report
    ↓
STOP
```

The milestone trust boundary ends at producing an in-memory `CanonicalImportPlan` and rendering a verbatim dry-run operator report (`plan_candidate_import`). Canonical execution (`execute_candidate_import`) is strictly prohibited and performing automatic database writes is zero-tolerance.

## Implementation Details & File Summary

### 1. ExtractionProvenance Dataclass & Contract (`reference/ingestion/contracts.py`)

* **Dataclass**:
  ```python
  @dataclass
  class ExtractionProvenance:
      raw_artifact_hash: str        # Format: "sha256:<64_lowercase_hex>"
      raw_artifact_reference: str   # Portable reference: "storage/raw_source_artifacts/toyota_usa/<hash>.html"
      extractor_id: str             # e.g., "toyota_pressroom_extractor"
      extractor_version: str        # e.g., "0.1.0"
      extraction_mode: str          # e.g., "manually_verified_transcription"
      unknown_fields: Dict[str, Any] = field(default_factory=dict)
  ```
* **`SourceMetadata` Field**: Added `extraction_provenance: Optional[ExtractionProvenance] = None`.
* **Field Separation**:
  - `SourceMetadata.source_locator` = original publisher URL (`https://pressroom.toyota.com/...`).
  - `SourceMetadata.acquisition_method` = acquisition transport (`local_file` or `live_http`).
  - `ExtractionProvenance.raw_artifact_reference` = RigArchive-managed portable snapshot reference (`storage/raw_source_artifacts/...`).
  - `ExtractionProvenance.raw_artifact_hash` = full SHA-256 digest (`sha256:<64_lowercase_hex>`).
  - `ExtractionProvenance.extraction_mode` = extraction mode (`manually_verified_transcription`).
  - `SourceAssertion.source_context` = human-readable source path (`configurations[].grade` or `table[1].row[4].col[2]`).

### 2. Serialization & Strict Validation (`reference/ingestion/serialization.py` & `reference/ingestion/validation.py`)

* Implemented `extraction_provenance_to_dict` and `extraction_provenance_from_dict`.
* Integrated into `source_metadata_to_dict` and `source_metadata_from_dict`, preserving `unknown_fields` and omitting `extraction_provenance` when `None`.
* Implemented `validate_extraction_provenance` in `validation.py`, validating:
  - `raw_artifact_hash` matching strict regex `^sha256:[0-9a-f]{64}$`.
  - Non-empty `raw_artifact_reference`, `extractor_id`, and `extractor_version`.
  - `extraction_mode` in `{"deterministic_structured_parser", "source_specific_parser", "manually_verified_transcription"}`.

### 3. Schema Version 1.1.0 & Version Compatibility

* **Schema Version Upgrade**: Newly emitted `SourceAssertionSet` artifacts carrying `ExtractionProvenance` set `envelope.schema_version = "1.1.0"`.
* **SemVer Policy (RA-011)**: Adding an optional `extraction_provenance` field with default `None` is a non-breaking minor schema version upgrade under major version 1 (`1.x.x`).
* **Major-Version Compatible Validation**: `validate_envelope` and `deserialize_artifact` validate `major_version == "1"`, cleanly reading both `"1.0.0"` and `"1.1.0"` artifacts. Legacy 1.0.0 artifacts deserialize with `extraction_provenance = None`. Existing historical NHTSA/EPA test fixtures remain `"1.0.0"`.

### 4. Raw Source Snapshot Retention & Portable References (`reference/ingestion/acquisition/snapshots.py`)

* **`RawSnapshotManager`**: Manages content-addressed storage of raw source payload snapshots and sidecar JSON metadata under `storage/raw_source_artifacts/<source_id>/<full_sha256>.<ext>`.
* **Portable Managed Storage References**:
  - `to_managed_storage_reference(path)` formats durable references as `storage/raw_source_artifacts/<source_id>/<hash>.<ext>`, completely omitting machine-specific absolute developer paths (`/Users/...`, `C:\...`).
  - `resolve_managed_storage_reference(ref, storage_root)` safely maps portable relative references back into internal filesystem `Path` objects, explicitly rejecting path traversal attempts (`..`).
* **Immutability & Idempotency**:
  - SHA-256 computed over exact acquired publisher bytes before decoding or transformation.
  - Re-acquiring identical bytes returns `("ALREADY_PRESENT", metadata)` without overwriting raw content or sidecar metadata (`acquired_at`, `publisher_locator`, `transport_metadata` remain untouched).
  - Atomic file creation via `tempfile.NamedTemporaryFile` and `os.replace` (content written first, sidecar written second).
* **Sidecar Metadata Isolation**: Sidecar JSON contains acquisition/storage metadata only. Extractor details (`extractor_id`, `extraction_mode`) belong strictly to `ExtractionProvenance`.

### 5. Toyota Publication Source Profile & Live Transport (`reference/ingestion/acquisition/profiles.py` & `base.py`)

* **`ToyotaUSAPressroomProfile`**: Concrete publication source profile for official Toyota USA Pressroom specifications (`source_id = "toyota_usa"`).
* **Transport Callable & Final-Host Redirect Safety**:
  - `default_http_transport` in `base.py` exposes `(status_code, body_bytes, resp_headers, final_url)`.
  - `acquire_from_url` validates scheme (`https`) and allowlisted host `pressroom.toyota.com` before request dispatch, AND re-validates `urlparse(final_url).hostname` after HTTP redirects.
  - If redirect final host is not allowlisted, raises `ProfileSecurityError` before writing snapshot files or attempting extraction.
* **Mechanical Transcription-to-Raw Hash Binding**:
  - `extract()` asserts `expected_raw_artifact_hash == snapshot_meta.content_hash`.
  - On hash mismatch or un-verified raw payload revision, raises `TranscriptionHashMismatchError`, aborting extraction immediately with zero emitted assertion sets or candidate configurations.

### 6. Authoritative Raw vs. Derivative Artifact Boundary

* **Authoritative Raw Source Artifact**: Original publisher HTML presskit page or PDF product kit bytes stored immutably in `storage/raw_source_artifacts/`.
* **Derivative Extraction Artifact**: RigArchive-produced structured transcription (`2020_4runner_specs.json`). Used as a controlled extraction fixture bound to the raw snapshot via `expected_raw_artifact_hash`. Derived transcriptions are NEVER stored or described as raw manufacturer snapshots.

### 7. Production Orchestration & Dry-Run Planning (`reference/ingestion/orchestration/manufacturer.py`)

* **`ProductionManufacturerOrchestrator`**:
  1. Acquires raw payload (`acquire_from_file` or `acquire_from_url`).
  2. Retains immutable raw snapshot (`store_snapshot`).
  3. Extracts Tier 1 assertion sets (`extract` with hash binding check).
  4. Normalizes assertions using `ManufacturerNormalizer`.
  5. Builds candidate configurations (`construct_candidate_configuration`).
  6. Plans candidate imports using `plan_candidate_import(candidate_doc)`.
  7. Returns `ProductionRunResult` aggregating snapshot metadata, total extracted sets, per-candidate plans, and verbatim reasons.
* **Strict Dry-Run Boundary**: NEVER calls `execute_candidate_import()`. Database count of `VehicleDefinition` remains 100% unchanged.

### 8. Django Management Command (`reference/management/commands/acquire_manufacturer_specs.py`)

* Operator CLI command `python manage.py acquire_manufacturer_specs`:
  - Arguments: `--file`, `--url`, `--profile`, `--transcription-file`, `--output-json`.
  - Outputs human-readable console report detailing source profile, publisher locator, acquisition status, snapshot hash, portable storage path, extracted configuration count, verbatim candidate plan statuses, and derived outcome counts evaluated against current database state.
  - Optional machine-readable dry-run JSON report output (`--output-json`).

### 9. CandidateIdentity Evidence Boundary & Regression Safety

* `CandidateIdentity` context (`make`, `model`, `year`, `market`, `trim`) is passed for candidate building context only.
* Tested in `test_candidate_identity_context_isolation`: Omitting mapped normalized evidence for trim or market causes `plan_candidate_import()` to return `REQUIRES_REVIEW` (`FLAG_REVIEW`), proving candidate context cannot bypass evidence requirements.

## Key Architectural Safety Guarantees

1. **Zero Automatic Canonical Writes**: Dry-run import planning stops automatically after `plan_candidate_import()`. Zero database writes (`execute_candidate_import`) are performed.
2. **Immutable Raw Snapshot Retention**: Acquired manufacturer raw HTML/PDF bytes are retained content-addressed by SHA-256 digest without overwriting.
3. **Mechanical Hash Binding**: Extraction requires `expected_raw_artifact_hash == actual_snapshot_hash`. Revised raw payloads require transcription re-verification before claiming lineage.
4. **Portable Managed References**: Durable provenance stores `storage/raw_source_artifacts/...` omitting developer machine paths.
5. **Redirect Final-Host Security**: Off-site HTTP redirects raise `ProfileSecurityError` before snapshot storage or extraction.
6. **Zero Network Dependencies in Standard Tests**: Test suite uses local file inputs and injected mock transports with zero live network calls.

## Scope Restrictions (Explicit Non-Goals)

* Zero automated updating, deleting, or inserting of canonical database records.
* Zero parent entity auto-creation.
* Zero live web scraping or unauthenticated arbitrary host requests.
* Zero cross-source fuzzy record joining.
* Zero background job / scheduler / browser automation infrastructure.
* Zero modification of established RA-011/RA-019/RA-021 contracts.

## Completion Record

Status: Completed / Verified

Completion date: 2026-08-15

Files created:
- `reference/ingestion/acquisition/snapshots.py`
- `reference/ingestion/acquisition/profiles.py`
- `reference/ingestion/orchestration/__init__.py`
- `reference/ingestion/orchestration/manufacturer.py`
- `reference/management/__init__.py`
- `reference/management/commands/__init__.py`
- `reference/management/commands/acquire_manufacturer_specs.py`
- `reference/tests/test_production_manufacturer_acquisition.py`
- `docs/implementation/tasks/RA-023-production-manufacturer-artifact-acquisition-dry-run-orchestration-implementation.md`

Files modified:
- `reference/ingestion/contracts.py`
- `reference/ingestion/serialization.py`
- `reference/ingestion/validation.py`
- `reference/ingestion/acquisition/base.py`
- `docs/implementation/CURRENT_STATE.md`
- `CHANGELOG.md`

Migrations created:
- None (0 ORM schema changes).

Verification results:
- `.venv/bin/python manage.py check`: Passed (`System check identified no issues (0 silenced)`).
- `.venv/bin/python manage.py makemigrations --check`: Passed (`No changes detected`).
- `.venv/bin/python manage.py test reference.tests.test_production_manufacturer_acquisition reference.tests.test_acquisition_adapters`: Passed (`Ran 34 tests in 0.058s — OK`).
- `.venv/bin/python manage.py test reference.tests.test_manufacturer_ingestion reference.tests.test_canonical_import`: Passed (`Ran 42 tests in 0.092s — OK`).
- `.venv/bin/python manage.py test`: Passed (`Ran 148 tests in 3.574s — OK`).
- `git diff --check`: Passed cleanly with exit code 0.
- `git status --short`: Verified unstaged/uncommitted state across all modified and newly created implementation and documentation files.
