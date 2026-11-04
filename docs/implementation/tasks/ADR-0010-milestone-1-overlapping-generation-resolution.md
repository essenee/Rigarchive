# ADR-0010 Milestone 1 — Overlapping-generation resolution

## Status and scope

- Status: PASS WITH QUALIFICATIONS after targeted generation-evidence completeness correction; 133 focused and 402 full Django tests pass. The unrelated PNG failure, historical database-hash discrepancy and documented legacy limitations remain.
- Final verification date: 2026-11-04.
- Authority: accepted [ADR-0010](../../architecture/ADR/ADR-0010-Generation-Correspondence-Selectable-Factory-Alternatives.md) and the explicit Milestone 1 implementation authorization.
- Scope: reviewed append-only generation correspondence, deterministic overlap resolution, candidate v2, import manifest 2.0, authorization/receipts, bounded legacy guards and ingestion documentation.
- Exclusions preserved: transmission/package/UI implementation, Jeep acquisition or development population, existing identity/range changes, historical ADR edits and Git publication.
- No application code was changed during the earlier final-verification continuation. The separately authorized blocker correction is documented below.

## Implemented behavior

GenerationCorrespondenceRevision has a logical correspondence UUID, immutable revision UUID, source selector/namespace, model/market/year scope, protected target, retained evidence, reviewer finding/time, content hash, and supersession/withdrawal history. Unique chain/revision and one-successor constraints prevent competing successor commits. Supported model/queryset/admin paths are append-only; privileged direct SQL is not claimed to be prevented.

The resolver preserves unique_year_range for legacy unambiguous cases. Explicit identities require all applicable current reviewed correspondences to establish one valid target. Failure never silently falls back. Missing, contradictory, withdrawn, stale or mismatched correspondence blocks import. Resolution is checked before creation and exact no-op handling.

Candidate 2.0.0 retains original document assertions, qualified interpretation references, source revision/hash inventories and generation normalizer identity/version. Import manifest 2.0 binds candidate content, actual extraction provenance, target identity, parent snapshots and mapping revisions. Legacy inspection remains available; only the original provably unambiguous execution path remains supported.

Correspondence publication and VehicleDefinition import are distinct receipt operation types and authorizations. Successful writes and receipts share a transaction. Stale/rejected outcomes produce no canonical creation and retain attempt receipts where audit storage permits. Receipt infrastructure failures roll back and are never reported as success. SQLite contention can abort both publication contenders; fresh review/authorization is then required.

Parent creation was removed from population planning. Batch/bootstrap/correction guards inspect unsupported scopes before mutation, including proposed taxonomy ranges and late fixture inputs. These are bounded guards, not a repair of legacy batch re-planning, slug authorization, no-op receipt suppression or ordinary correction semantics.

## Initial implementation verification (before blocker correction)

Final verification used the repository Python 3.13 environment. The following management operations ran under PYTHONDONTWRITEBYTECODE=1 and RIGARCHIVE_TEST_DB_PATH=:memory:, with temporary MEDIA_ROOT/raw-source storage and a connection_created guard refusing any ORM connection except :memory: or Django's mode=memory test URI:

```python
call_command("check")
call_command("makemigrations", check=True, dry_run=True)
call_command(
    "test",
    "reference.tests.test_generation_correspondence",
    "reference.tests.test_canonical_import",
    "reference.tests.test_canonical_import_execution",
    "reference.tests.test_adjudication_workflow",
    "reference.tests.test_operator_workflow",
    "reference.tests.test_generation_bootstrap",
    "reference.tests.test_ingestion_serialization",
    interactive=False, verbosity=1,
)
call_command("test", interactive=False, verbosity=1)
```

- Django system check: passed.
- Migration consistency: no changes detected.
- Focused tests: 145 passed.
- Complete Django suite: 387 passed, including 29 new Milestone 1 tests.
- node --test reference/tests/js/*.test.cjs: 33 passed, 1 failed.
- The failing unchanged test is “length correction is localized and aligns its short witness with the rear bumper.” The unchanged corrected homepage PNG is 1239×1269; the unchanged original is 502×514. All relevant test/helper/image hashes match the implementation-start baseline. No unrelated UI repair or test weakening was performed.
- git diff --check: passed. Relative documentation links resolved; final verification confirmed all six reference-table fingerprints and the complete database file remained unchanged. No SQLite WAL/SHM/journal sidecars were present. Application code was unchanged during this final-verification continuation.
- No new TODO/FIXME/NotImplemented placeholders were found in the new implementation modules/commands.

The new tests cover synthetic JK/JL routes, unidentified/conflicting evidence, scope/withdrawal, document lineage, tampering, stale correspondence/source revisions, parent changes, create/no-op authorization, publication/import receipt rollback, concurrent successors, zero-write planning, pre-write legacy guards and Toyota/Volkswagen compatibility. The synthetic Wrangler fixtures are not manufacturer evidence.

Earlier failures were corrected by explicit test parent curation instead of planner seeding, preserving the new zero-write invariant; an invalid legacy resolution is now stale before creation rather than failing only at model validation. Tests were not weakened to hide defects.

## Migration and development data

Created reference/0006_generationcorrespondencerevision_and_receipt_resolution.py. It is additive and contains no data backfill or Generation/VehicleDefinition identity alterations. Tests exercised it only on isolated databases.

Read-only development inspection confirms the reference migration ledger ends at 0005 and the correspondence table does not exist. Development has zero Jeep manufacturers and zero Wrangler models. Active configuration counts are 326 4Runner, 276 Tacoma and 65 Touareg; inspected Generation UUIDs/slugs/ranges match the earlier inventory. No development migration, acquisition or import was issued.

Preservation limitation: the implementation-start database SHA-256 was cfa9f2736c7c078e5edc5dc57657d15d317659c1655280f39f3f89e31fd2e78d; final-verification-start SHA-256 was 402cc222c0acb14a140d9b48c0daf8cc287b8328e907f1f1a6b1739c6fd8df35. The cause of that earlier change is unestablished. The database was not restored or overwritten. Aggregate reference observations do not prove every individual VehicleDefinition identity remained unchanged across the earlier interval. Final verification independently fingerprints all six existing reference tables and the database file to detect changes during this continuation.

Public UI files, settings and historical ADRs match implementation-start hashes. Pre-existing working-tree work remains preserved. No staging, commit, push or branch change occurred.

## Documentation

Created the [permanent ingestion protocol](../../development/INGESTION_PROTOCOL.md); amended RA-010/011/014/016/018/022/024/025 under ADR-0010; updated CURRENT_STATE.md and CHANGELOG.md with verified status and limitations. Historical ADRs and completed task records remain unchanged.

## Files modified by Milestone 1

- CHANGELOG.md
- docs/architecture/designs/RA-010-Reference-Ingestion-Source-Mapping-Architecture.md
- docs/architecture/designs/RA-011-Ingestion-Schema-Intermediate-Serialization-Design.md
- docs/architecture/designs/RA-014-Source-Assertion-Normalization-Mapping-Architecture.md
- docs/architecture/designs/RA-016-Candidate-Configuration-Construction-Aggregation-Architecture.md
- docs/architecture/designs/RA-018-Canonical-Reference-Matching-Import-Architecture.md
- docs/architecture/designs/RA-022-Production-Manufacturer-Evidence-Acquisition-Orchestration-Architecture.md
- docs/architecture/designs/RA-024-Canonical-Reference-Import-Execution-Execution-Provenance-Workflow-Architecture.md
- docs/architecture/designs/RA-025-Production-Manufacturer-Extraction-Review-Adjudication-Architecture.md
- docs/implementation/CURRENT_STATE.md
- reference/admin.py
- reference/ingestion/candidate/builder.py
- reference/ingestion/contracts.py
- reference/ingestion/importing/__init__.py
- reference/ingestion/importing/correction.py
- reference/ingestion/importing/importer.py
- reference/ingestion/importing/planner.py
- reference/ingestion/importing/workflow.py
- reference/ingestion/manifest.py
- reference/ingestion/orchestration/generation_bootstrap.py
- reference/ingestion/orchestration/manufacturer.py
- reference/ingestion/serialization.py
- reference/ingestion/validation.py
- reference/management/commands/acquire_manufacturer_specs.py
- reference/management/commands/execute_canonical_import.py
- reference/models.py
- reference/tests/test_canonical_import_execution.py
- reference/tests/test_generation_bootstrap.py

## Files created by Milestone 1

- docs/development/INGESTION_PROTOCOL.md
- reference/ingestion/generation_correspondence.py
- reference/ingestion/normalization/generation.py
- reference/management/commands/plan_canonical_import.py
- reference/management/commands/publish_generation_correspondence.py
- reference/migrations/0006_generationcorrespondencerevision_and_receipt_resolution.py
- reference/tests/fixtures/ingestion/generation_overlap/correspondence_revision_chain.json
- reference/tests/fixtures/ingestion/generation_overlap/wrangler_2018_contradictory.json
- reference/tests/fixtures/ingestion/generation_overlap/wrangler_2018_invalid_scope.json
- reference/tests/fixtures/ingestion/generation_overlap/wrangler_2018_jk.json
- reference/tests/fixtures/ingestion/generation_overlap/wrangler_2018_jl.json
- reference/tests/fixtures/ingestion/generation_overlap/wrangler_2018_unidentified.json
- reference/tests/test_generation_correspondence.py
- reference/tests/test_generation_projection_completeness.py
- docs/implementation/tasks/ADR-0010-milestone-1-overlapping-generation-resolution.md

The pre-existing modified db.sqlite3/settings, ADR-0010 and homepage work are not new Milestone 1 implementation files. The database hash discrepancy above is not attributed to a known operation.

## Remaining work and limitations

- The initial closeout blocker was corrected and regression-tested under separate authorization, as documented below. No application fix was made during the restricted closeout itself.
- Separate authorization is required before applying migration 0006 to development or any deployed database.
- No real Jeep source correspondence or vehicle population is established.
- Transmission and factory-package milestones remain unimplemented.
- Legacy authorization weaknesses remain outside the guarded Milestone 1 path.
- Overall project verification remains non-clean because of the unrelated existing JavaScript asset failure.
- Whole-implementation database preservation remains unconfirmed; no speculative repair was attempted.

## Initial closeout review (2026-11-04; superseded by correction below)

**Acceptance recommendation at that review: BLOCKED.**

The candidate-v2 validator checks submitted `generation_evidence` entries against retained document assertions but does not require that every explicit generation assertion has a corresponding projected identity. An empty list passes even when `evidence_documents` contains `generation_designation = JK`. The v2 parser also defaults an omitted `generation_evidence` field to an empty list. `resolve_generation()` branches on that list alone and permits `unique_year_range` when it is empty, without checking the retained explicit assertions. Consequently, a missing or dropped projection can bypass reviewed correspondence and the requirement that failed explicit evidence never falls back.

Affected locations: `reference/ingestion/validation.py::validate_candidate_configuration`, `reference/ingestion/generation_correspondence.py::validate_generation_evidence` and `resolve_generation`, and `reference/ingestion/serialization.py::candidate_config_doc_from_dict`.

Two pure in-memory acceptance probes confirmed the gap: (1) a v2 candidate with an explicit retained generation assertion and empty projection passed validation; (2) a resolver supplied that retained assertion and an empty projection returned `unique_year_range` with one mocked generation. A connection-created guard prohibited database connections. No files, records, acquisition or application changes were involved in those probes. No live import was attempted. These are additional targeted review findings, not replacements for the earlier 145/387 passing test results.

Required follow-up, subject to separate authorization: validate completeness and consistency of the generation projection against all recognized retained generation assertions; reject omitted/dropped/contradictory identities before planning and execution; ensure the resolver cannot enter year fallback when explicit retained evidence exists; add regression cases for empty/missing projection and partial omission of conflicting identities, including recomputed candidate/manifest hashes. Do not weaken retained evidence or silently manufacture an authorized correspondence.

Other closeout findings:

- The JavaScript failure is unrelated and pre-existing: its test, decoder helper and both PNG hashes match implementation-start fingerprints. The 1239×1269 corrected image differs from the 502×514 original expected by the existing test. None were modified for closeout.
- Migration 0006 contains only creation of the correspondence model, additive receipt fields and correspondence constraints. It has no RunPython/RunSQL operations or existing Generation/VehicleDefinition alterations/population. Its receipt defaults do not populate vehicle records.
- Revision integrity constraints, exact single-plan authorization, stale-state checks and zero-write planning have implementation and passing-test evidence, but the generation-evidence omission defect prevents overall Milestone 1 acceptance.
- The database hash discrepancy documented above remains unresolved and is preserved; no restore or overwrite was performed. Development migration 0006 remains unapplied.
- At initial closeout, the exact Milestone 1 inventory was 28 modified files and 14 created files. The correction adds one regression-test file, now included above. Pre-existing settings/database/ADR/homepage/probe changes remain outside that inventory. Only this verification record was edited during closeout.
- Suggested future implementation commit message, after the blocker is resolved: `Implement ADR-0010 Milestone 1 generation correspondence and exact import authorization`.

## Blocker correction and verification (2026-11-04)

**Revised acceptance recommendation: PASS WITH QUALIFICATIONS.** The generation-projection blocker is resolved. This recommendation does not claim a clean unrelated JavaScript suite or establish whole-implementation database preservation.

### Root cause

`validate_generation_evidence()` checked each submitted identity against retained assertions, but never checked the reverse direction. An empty/subset projection therefore passed. `resolve_generation()` validated only a nonempty projection and treated an empty list as absence of explicit source evidence. Candidate deserialization supplied an empty-list default without validating completeness. Manifest reconstruction and legacy serialization also needed explicit guards against discarding generation-aware authorization fields.

### Exact correction

- Reuse one deterministic projection function for construction and validation. Its qualified key is `(source_id, document_hash, assertion_set_id, assertion_id)`; values preserve source namespace, raw-derived native identifier and normalizer provenance.
- Compare the complete expected identity map from retained generation-identifying assertions with the submitted map. Reject missing, duplicate, extra or contradictory entries. Unknown values and conflicting assertions remain separate evidence. Validation never repairs a submitted projection or creates a correspondence.
- Require retained assertion information even to validate an empty projection. Empty/missing assertion inventories fail closed. No completeness flag or caller Generation identifier is accepted as proof.
- Validate before either public resolver branch. `unique_year_range` is allowed on the v2 path only after retained assertions establish no explicit generation identity.
- Keep original v1 unique-year compatibility in a separate internal helper. Reject v1 candidates still carrying v2 documents or generation hints; never interpret legacy compatibility as a v2 completeness finding.
- Validate v2 serialization/deserialization and direct manifest reconstruction. Reject legacy manifest serialization that would drop v2 authorization data, or execution with a missing resolution but remaining candidate snapshot/hash. Existing exact membership, hash and stale-state checks remain in force.
- Candidate v2 fields, artifact types, schema version 2.0.0 and manifest version 2.0 are unchanged. This enforces an existing invariant, not a material contract redesign. No models or migrations were changed.

### Files changed by this correction

- `reference/ingestion/normalization/generation.py`
- `reference/ingestion/generation_correspondence.py`
- `reference/ingestion/importing/planner.py`
- `reference/ingestion/serialization.py`
- `reference/ingestion/manifest.py`
- `reference/tests/test_generation_correspondence.py` (retain the original unique-year assertions while supplying verifiable v2 absence evidence)
- `reference/tests/test_generation_projection_completeness.py` (new)
- `docs/implementation/CURRENT_STATE.md`
- `CHANGELOG.md`
- This verification record

The complete Milestone 1 inventory is now 28 modified files and 15 created files; all pre-existing unrelated changes remain preserved.

### Regression tests and results

Added 15 tests covering empty/subset omission, omitted unknown terms, partially omitted contradictory assertions, independently qualified duplicate local IDs across documents, duplicate projections, valid absence and reviewed explicit correspondence, direct resolver/planner/adjudicated calls, missing retained assertions, serialization/deserialization tampering, recomputed candidate/manifest hashes, direct reconstruction and execution, legacy downgrade attempts, and existing Toyota/Volkswagen fixture candidates.

Original tests and safety assertions remain; the existing public-resolver unique-year test now supplies retained assertions proving absence rather than an unverifiable empty document list.

Verification used `venv/py313/bin/python -B`, `PYTHONDONTWRITEBYTECODE=1`, `RIGARCHIVE_TEST_DB_PATH=:memory:`, temporary media/raw storage, and a `connection_created` guard rejecting non-isolated ORM connections. Commands were:

```python
call_command("check")
call_command("makemigrations", check=True, dry_run=True)
call_command(
    "test",
    "reference.tests.test_generation_projection_completeness",
    "reference.tests.test_generation_correspondence",
    "reference.tests.test_candidate_construction",
    "reference.tests.test_ingestion_serialization",
    "reference.tests.test_canonical_import",
    "reference.tests.test_canonical_import_execution",
    "reference.tests.test_adjudication_workflow",
    interactive=False, verbosity=1,
)
call_command("test", interactive=False, verbosity=1)
```

- System check: passed.
- Migration consistency: no changes detected.
- Focused tests: 133 passed.
- Complete Django suite: 402 passed.
- Final correction preservation check: exactly the ten files listed above changed; no files were removed. The development database SHA-256 remained `402cc222c0acb14a140d9b48c0daf8cc287b8328e907f1f1a6b1739c6fd8df35`. Read-only inspection confirmed reference migrations stop at 0005 and no correspondence table exists. Models, migrations, UI assets, accepted ADRs and other pre-existing changes were unchanged during this correction. Git diff whitespace and the new test file whitespace checks passed.
- The unrelated homepage PNG failure and its unchanged assets/test remain as documented above; it was not repaired or rerun for this targeted correction.
- No development migration, data backfill, Jeep acquisition/population, UI change, identity/range change or Git publication was performed. Migration 0006 remains separately authorized deployment work.

