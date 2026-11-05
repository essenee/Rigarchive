# W2 B3 — Transmission implementation and verification record

Status: VERIFIED AND COMPLETE, READY FOR ARCHITECTURAL ACCEPTANCE (2026-11-04). All verification checks, migration tests, and regression runs passed in complete isolation. Development database and retained storage remain byte-identical to pre-verification baseline. Migrations 0007 and 0008 remain UNAPPLIED to the development database. No B4 work initiated.

## Objective, scope and authority

Implement approved transmission descriptions/revisions and exact VehicleDefinition-scoped offering revisions under existing B1/B2 contracts. Alternatives do not create VehicleDefinitions or change UUIDs/slugs/URLs. Presentation/UI, equipment/body persistence, acquisition, and real publication are excluded.

Governing: accepted [ADR-0010](../../architecture/ADR/ADR-0010-Generation-Correspondence-Selectable-Factory-Alternatives.md) and [ADR-0011](../../architecture/ADR/ADR-0011-Factory-Body-Configuration-Identity.md); W2 [domain](../../architecture/designs/W2-Full-Specifications-Domain-Architecture.md), [properties/applicability](../../architecture/designs/W2-Specification-Property-Applicability-Contract.md), [enrichment/publication](../../architecture/designs/W2-Enrichment-Publication-Contract.md), [implementation plan](../../architecture/designs/W2-Phase-A-Implementation-Plan.md); [protocol](../../development/INGESTION_PROTOCOL.md), [CURRENT_STATE](../CURRENT_STATE.md), [B2 record](W2-B2-specification-persistence-publication.md).

## Files and functionality

- `reference/specifications/models.py`: TransmissionDescription logical identity; immutable TransmissionDescriptionRevision; protected TransmissionEngineeringAssertion links; TransmissionOffering logical exact-baseline/hardware identity; immutable TransmissionOfferingRevision with standard/optional/unavailable/unknown availability. Unique revision numbers, single successors, and append-only guards reuse B2 patterns. SpecificationCatalogueMembership and SpecificationEvidenceLink extended with protected transmission revision FKs, exclusive-target checks, per-owner uniqueness, and exact hash/order validation.
- `reference/models.py`: re-exports new models within Reference without altering baseline models or canonical executors.
- `reference/specifications/publication.py`: supports transmission members and dependencies through exact input loading, current snapshot membership, current-leaf/replay/stale checks, logical-root continuity, revision persistence, and evidence/engineering links. Zero-write planning, explicit authorization, and atomic catalogue/receipt transactions preserved. Equipment/body persistence guarded.
- `reference/migrations/0008_transmission_domain.py`: depends on 0007; creates transmission tables, foreign keys, unique constraints, and check constraints; updates membership and evidence constraints. Tested against isolated temporary database; unapplied to development.
- `reference/tests/test_transmission_publication.py`: six focused synthetic tests verifying two alternatives on one baseline, offering supersession and history, invalid baseline rejection, receipt rollback, immutability, and availability versus selection/compatibility.
- `reference/tests/test_specification_publication.py`: B2 transmission exclusion test re-scoped to equipment; all 20 publication tests passing.

## Verification execution and results

All verification commands executed using `venv/py313/bin/python` with `RIGARCHIVE_TEST_DB_PATH` isolated from `db.sqlite3`.

### 1. Django system and migration checks
- `manage.py check`: Passed; 0 issues identified.
- `manage.py makemigrations --check --dry-run`: Passed; no uncommitted or missing model changes detected.

### 2. Isolated migration execution (0006 → 0007 → 0008)
Tested on dedicated isolated SQLite database (`/tmp/temp_mig_test.sqlite3`):
- `manage.py migrate reference 0006`: OK
- `manage.py migrate reference 0007`: OK
- `manage.py migrate reference 0008`: OK
- `manage.py migrate`: OK across all applications (accounts, admin, auth, contenttypes, measurements, observation, reference, sessions).
All table creation, foreign key bindings, and check constraints validated without error.

### 3. Targeted B3 tests
- `manage.py test reference.tests.test_transmission_publication`:
  - Initial run: 5 passed, 1 failed (`test_two_alternatives_preserve_one_baseline_and_exact_links`).
  - Defect identified: Type mismatch between unrefreshed model string `uuid` attribute from `create(uuid=uid(4))` and DB-loaded `uuid.UUID` instance after `refresh_from_db()`.
  - Fix: Normalized comparison in `test_transmission_publication.py` to `(str(self.vd.uuid), self.vd.slug, self.vd.generation_id)`.
  - Subsequent run: 6 of 6 passed.

### 4. Regression tests
- `manage.py test reference.tests.test_specification_publication`: 20 of 20 passed.
- `manage.py test reference.tests.test_specification_primitives reference.tests.test_specification_artifacts`: 86 of 86 passed.
- `manage.py test reference.tests.test_models reference.tests.test_canonical_import_execution`: 21 of 21 passed.
- Combined test run: 133 of 133 passed in 1.618s, 0 failed.

## Preservation verification

- `db.sqlite3` pre-verification SHA-256: `98a790345f683125c4d81029936e1af07f1d8a4da5bae0974e568dc530485458`
- `db.sqlite3` post-verification SHA-256: `98a790345f683125c4d81029936e1af07f1d8a4da5bae0974e568dc530485458`
- Retained `storage/` 71-file inventory pre-verification SHA-256: `118d838926f7d48dc6c7a028d806b3ce85ed7060347d7ac244f07020bfa61174`
- Retained `storage/` 71-file inventory post-verification SHA-256: `118d838926f7d48dc6c7a028d806b3ce85ed7060347d7ac244f07020bfa61174`
Zero development database modifications or storage mutations occurred.

## Boundaries and remaining limitations

- Migrations 0007 and 0008 remain unapplied to the development database per project policy.
- No real transmission records or catalogues have been published.
- Equipment/body persistence (B4/B5) and UI/presentation remain unstarted and guarded.
- The historical B1 database-hash discrepancy remains deferred and uninvestigated.
