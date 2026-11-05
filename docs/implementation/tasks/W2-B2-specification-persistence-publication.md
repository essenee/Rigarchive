# W2 B2 — Specification persistence and publication

Status: ready for review, 2026-11-04. Implementation only; no development migration, real catalogue publication or B3 work.

## Files

Created:

- reference/specifications/models.py
- reference/specifications/publication.py
- reference/migrations/0007_specification_persistence_publication.py
- reference/tests/test_specification_publication.py
- docs/implementation/tasks/W2-B2-specification-persistence-publication.md

Modified: reference/models.py (model registration imports only), docs/implementation/CURRENT_STATE.md, CHANGELOG.md. Pre-existing unrelated changes preserved; no staging, commits, pushes or branch changes.

## Persistence and services

Thirteen models: SpecificationUnitRegistry; EvidenceDocument; EvidenceAssertionReference; SpecificationDefinition; SpecificationDefinitionRevision; SpecificationDefinitionDependency; SpecificationAssertion; SpecificationCatalogue; SpecificationCatalogueRevision; SpecificationCatalogueMembership; SpecificationCatalogueCoverage; SpecificationEvidenceLink; SpecificationPublicationReceipt. Exact approved wire payloads/hashes are preserved; typed assertion JSON is validated by B1 against pinned definitions/units. Queryable protected relationships bind evidence, definitions, assertions and complete catalogue membership. Four separate coverage rows match each snapshot. Logical identities, revision numbers, one-successor relationships and database uniqueness/check constraints prevent competing valid branches. Ordinary model/queryset updates/deletes/bulk mutation are blocked; supported publication writes are insert-only. Privileged SQL/raw database replacement is not claimed to be prevented.

`plan_publication(draft, artifact_root, authorization_scope)` reads canonical state and retained bytes, validates B1 contracts and returns the exact new review manifest with no database writes. `publish` requires explicit affirmative authorization, exact authorized manifest hash and truthful operator label. It reconstructs no substitute plan. EvidenceStore is read-only under an explicit root and prevents path/symlink escapes. No downloads, source copying or fixture backfill.

Execution revalidates bytes, target UUID/PK/slug/identity, active parent relationships/ranges, catalogue head, exact dependency/member revisions and relevant generation correspondence bindings. Only definition/assertion members and applicable evidence/registry/correspondence dependencies are supported in B2. Unsupported B3/B5 inputs fail before canonical mutation. New/replayed revisions cannot hide superseded definitions/assertions. Exact-current replay requires original successful receipt binding and unchanged relevant state. Published catalogues retain complete exact membership, not patches; supersession preserves old snapshots.

Canonical publication, all newly required metadata/member/link/coverage rows and the successful receipt commit in one transaction. Receipt failure rolls back canonical changes. Domain rejection/stale outcomes roll back publication and retain an attempt receipt in a separate transaction where storage permits. Database/receipt infrastructure failures propagate without success; no durable receipt is promised when audit storage is unavailable. Concurrent SQLite write upgrades may abort one or both attempts, with no automatic retry. One-successor and unique-first-revision constraints prevent forks even where row locks are unavailable. Other backends may use the target row lock, but no deployment/backend change is introduced.

Separate specification receipts retain the full reviewed manifest/evidence/dependencies and actual operation/operator/time/outcome without changing historical ImportExecutionReceipt rows or inventing vehicle-creation fields. B1 pure state validation remains independent of Django; B2 obtains the live inputs. No existing canonical import executor was changed.

## Migration and verification

Migration 0007 depends on reference.0006. Operations create new specification tables and their protected relationships, indexes/constraints; fields added during the migration belong only to newly created specification tables. No RunPython, RunSQL, population, alteration of existing vehicle identity, or historical receipt rewrite. UNAPPLIED to the development database.

An isolated file database was migrated to 0006, seeded with synthetic canonical sentinels, then migrated to 0007. All pre-existing table contents matched afterward (excluding expected migration-ledger additions). The Django test runner independently applied the migration to temporary test databases.

Final verification:

- 20 B2 tests: publication, all-table zero-write planning, exact-current replay, catalogue/definition/assertion supersession, stale parallel plans/source/parents/shared definitions/correspondence bindings, withdrawal, exact authorization/tampering, receipt rollback, durable rejection attempts, append-only paths, protected relationships, pre-write B3 guards, evidence path safety and concurrent publication.
- 86 B1 tests plus 5 existing model and 16 canonical-execution regressions: 127 total, all passed.
- Django system check passed; migration-consistency dry-run found no changes; whitespace check passed. No full suite was run, as instructed.
- Development database and full 71-file retained-storage inventory matched pre/post verification fingerprints. Only the migration-ledger status for 0007 was read from development: unapplied. No persistent migration/write/publication was performed.

Representative commands (each Django operation used RIGARCHIVE_TEST_DB_PATH pointing to a temporary database and temporary media): `manage.py check`; `manage.py makemigrations --check --dry-run`; `manage.py test reference.tests.test_specification_publication reference.tests.test_specification_primitives reference.tests.test_specification_artifacts reference.tests.test_models reference.tests.test_canonical_import_execution`. Migration generation used the approved venv/py313/bin/python with an isolated database path; no dependencies were installed.

## Boundaries and outstanding work

No contract deviations or B2 blockers identified. The historical B1 development-database hash discrepancy remains unresolved and deferred; no investigation, repair or restoration was performed. B2 verification only attests its own pre/post preservation interval. B1's existing incidental fixture-copy artifacts were preserved, not cleaned up.

Deployment of migration 0007, publication of actual catalogues, transmission/equipment persistence, feature mappings, FactoryBodyConfiguration persistence, body-aware imports and UI remain separately authorized future work. B2 is ready for review; do not begin B3 or populate real data under this task.
