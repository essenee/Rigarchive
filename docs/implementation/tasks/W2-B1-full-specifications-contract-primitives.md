# W2 B1 — Full Specifications serializers and validators

Status: IMPLEMENTED / PASS WITH QUALIFICATIONS, 2026-11-04. B2 is not started. No production/development persistence or canonical-write authorization.

## Delivered contracts and API boundaries

Pure-Python package `reference/specifications/` supplies closed specification value/assertion/evidence schemas, canonical JSON/SHA-256, canonical decimal producer normalization, exact rational unit conversion validation, predicate language 1.0, independent transmission/equipment selections, three-valued evaluation and shared budgets. Catalogue validation checks exact members, definitions/qualifiers/units, relationships, cycles, scoped equipment policy, predecessor lineage, full carry-forward state and explicitly accounted removals. Whole-selection evaluation supports prerequisites, exclusions, cardinality, contents/replacements and evidence-reviewed exact/complete-scope coexistence; pairwise support does not prove higher-order support. Unresolved restrictions/contexts remain unverified. Manufacturer capacities are not calculated.

Enrichment `rigarchive.full_specifications_enrichment.v1` schema 1.0.0 and publication `rigarchive.full_specifications_publication_manifest.v1` schema 1.0.0 are separately parsed and validated; operation type is specification_catalogue_publication. Specification assertion v1/schema 1.0.0 is also supported. Candidate v2/manifest 2.0 behavior, UUIDs, slugs, URLs and existing executors are unchanged. Candidate v3, body/series curation, catalogue persistence, publication execution and receipts remain unimplemented and unauthorized.

`serialize_artifact`/`deserialize_artifact` and catalogue serialization return validated canonical-byte snapshots; detached dictionaries cannot mutate retained bytes. Validation requires explicitly provided immutable byte artifacts, exact existing member records/predecessor, registry and controlled feature/state bindings; no filesystem I/O or ORM is performed. New quantities use Decimal strings; original wording/units/formatting and historical raw hashes are retained. Retained SourceAssertionSet v1 schema 1.0.0/1.1.0 bindings are read without rewriting; unknown formats fail closed. This is not a general PDF/HTML extraction bridge.

`publication_disposition` is a pure decision against caller-supplied target, parents, dependencies, current catalogue and successful-manifest snapshots. Exact-current authorized replay returns no-op; changed/superseded/withdrawn or unproven state raises ContractError. It does not authenticate users, obtain trustworthy live state, perform transactions or persist receipts. Those are B2 responsibilities; hashes are not authentication.

The package lives directly under Reference because the existing `reference.ingestion` package eagerly imports ORM modules. No existing import semantics were changed to make new primitives independently testable.

## Resolved contract blocker

Initial work stopped because QualifierRule permitted category values without a qualifier-specific vocabulary. The director selected an exact categorical definition revision reference. Approved W2 Publication §9 and Properties §7 now require `categorical_definition:Ref|null`: category requires an exact pinned category-definition revision/hash; noncategory requires null. Validators use that definition's controlled terms, reject absent/mismatched/noncategory bindings and cycles, and never reuse parent-property terms by assumption. No historical schema/artifact hash was rewritten; no accepted ADR was modified.

## Verification

- Standalone: `venv/py313/bin/python -B -m unittest reference.tests.test_specification_primitives reference.tests.test_specification_artifacts -q`: 86 passed, no Django setup.
- Final guarded focused Django run: 161 passed, including new tests and existing serialization, candidate/projection, drivetrain, multi-source and canonical-execution regressions.
- Final guarded full Django suite: 518 passed. System check passed; migration-consistency dry-run reported no changes. No migration files generated or development migrations applied.
- Python AST/syntax, local documentation links and `git diff --check` passed. No JavaScript suite rerun; the previously recorded unrelated homepage PNG qualification remains untouched.
- Test resources: isolated in-memory SQLite, temporary media/acquisition roots, connection guard rejecting non-isolated ORM connections, persistent-storage write/mkdir/delete guards, and full pre/post file inventory/hash comparison. The final run preserved all 71 storage files and its development database hash.

## Preservation qualifications and deviations

B1-start database hash: `ace233ac349ba867572cba2ec07c96c575b96371601f911c7c31ef94abd6aa6b`. The first full run preserved that hash. A later pre-run hash was `c87454dcdc140fd5c96896d4b3928cc73a6088e9273fb8ab4f1f44de8cd79f3b`; cause of the intervening change is unestablished. Final guarded runs preserved the latter hash. No development database write/migration/import command or restore was issued. Do not claim byte-for-byte preservation over the whole B1 interval.

Read-only checks: integrity OK, foreign-key violations none, no SQLite sidecars; 700 VehicleDefinitions, 14 Generations, 2,758 receipts, three correspondences, 31 corrections. Jeep714/715 UUIDs, slugs, identity dimensions and Generation relationships match W1. A typed-content comparison against the verified pre-0006 physical snapshot found zero missing/modified historical rows in all eleven Reference/Measurements tables. Additions match previously authorized Jeep/W1 operations: one Manufacturer, one VehicleModel, two Generations, two VehicleDefinitions and five receipts. Corrections and all measurement/applicability tables match completely. This supports canonical preservation but is not a substitute for a missing B1-start logical snapshot or an explanation of the database byte change.

The first full-suite run exposed an existing storage-isolation gap: MultiSourceAggregationTests used RawSnapshotManager's persistent default. It created four fixture-copy artifacts at 2026-11-04T20:20:12Z. No pre-existing evidence file changed or was deleted. Temporary-root patches were added in that class and CanonicalImportExecutionTestCase; stricter guards exposed four attempted persistent mkdir operations in the latter, which were corrected before the final successful run. No assertion was weakened and no application/executor behavior changed. Initial guards checked existing bytes but not new file inventory; final guards/checks cover both.

The following incidental files remain untouched, not authorized acquisition evidence and not promoted into any candidate/catalogue:

- storage/raw_source_artifacts/jd_power/b3506db54dcd327be5691515fbea1b3a09409f2e6c51f4eeef9a8ea6caa4d1cf.json
- storage/raw_source_artifacts/jd_power/b3506db54dcd327be5691515fbea1b3a09409f2e6c51f4eeef9a8ea6caa4d1cf.meta.json
- storage/raw_source_artifacts/toyota_usa/e7ef451a81298e8319f7a6e04559264c0e372ac06b8c17c4ca7878ca777c2a57.json
- storage/raw_source_artifacts/toyota_usa/e7ef451a81298e8319f7a6e04559264c0e372ac06b8c17c4ca7878ca777c2a57.meta.json

An ignored IDE workspace metadata file also changed during the interval; this task did not edit it or inspect its contents. No automatic cleanup, restoration, overwrite or retrospective authenticity claim. All original 67 evidence/storage files remain byte-identical to the B1-start fingerprint. Four incidental additions and the database hash difference prevent an unqualified task-wide preservation claim.

## Complete authored file inventory

New package: reference/specifications/__init__.py, canonical.py, values.py, predicates.py, schemas.py, catalogue.py, artifacts.py, evaluation.py, serialization.py.

New tests/fixtures: reference/tests/test_specification_primitives.py, test_specification_artifacts.py, specification_fixtures.py. These contain synthetic fixtures only and write no persistent evidence.

Existing tests changed only for temporary acquisition-root isolation: reference/tests/test_multi_source_population.py and reference/tests/test_canonical_import_execution.py.

Documentation updated: docs/architecture/designs/W2-Specification-Property-Applicability-Contract.md, W2-Enrichment-Publication-Contract.md, W2-Phase-A-Implementation-Plan.md; docs/development/INGESTION_PROTOCOL.md; docs/implementation/CURRENT_STATE.md; CHANGELOG.md; this task record. Incidental artifacts are separately listed above.

Existing unrelated working-tree changes remain preserved. Nothing staged, committed, pushed or switched. No models, migrations, services/executors, UI or canonical records were authored/modified by B1.

## Next boundary

B1 is ready for review with the preservation qualifications above. B2 persistence/publication needs separate authorization, trustworthy live-state resolution, atomic receipt handling and data-preservation/migration gates. Body/series publication remains B5. No B2 work was started.
