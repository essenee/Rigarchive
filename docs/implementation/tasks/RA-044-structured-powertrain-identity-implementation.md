# RA-044 — Structured powertrain identity implementation record

**Created:** 2026-11-07
**Status:** Accepted
**Implementation date:** 2026-11-07
**Authority:** [Accepted RA-044](../../architecture/designs/RA-044-Structured-Powertrain-Identity-Implementation-Architecture.md), [ADR-0012](../../architecture/ADR/ADR-0012-Structured-Powertrain-Identity-And-Hybrid-Terminology.md), and the director's explicit implementation authorization.

Implementation acceptance and completed development migrations 0007–0010 were explicitly confirmed by the director on 2026-11-07. Read-only live inspection confirms applied migration records; historical assignments and canonical imports require separate authorization. The completed RA-043 Measurements milestone remains unchanged.

## Delivered scope

- Five nullable VehicleDefinition fields: `engine_displacement_liters` (Decimal(5,2)), `engine_cylinders` (positive small integer), `engine_aspiration`, `fuel_type`, and `electrification_type`. No semantic defaults or historical backfill. Migration `0010_vehicledefinition_electrification_type_and_more` adds the columns and positive/controlled-token-or-null constraints without data operations.
- Central vocabulary in `reference/powertrain.py`: aspiration `naturally_aspirated`, `turbocharged`, `supercharged`, `twincharged`, `other`; fuel `gasoline`, `diesel`; electrification `none`, `mild_hybrid`, `hybrid`, `plug_in_hybrid`. Unsupported noncombustion categories remain outside this bounded implementation. Unknown stays null. Other aspiration requires review before new canonical creation.
- Explicit Candidate schema 2.1.0 with exact five-key `canonical_powertrain`, canonical decimal strings and document-qualified normalized evidence. The versioned normalization helper preserves raw lexemes and maps no missing classifications. One assertion may support multiple attributes; multiple applicable sources may support a complete tuple. Incomplete preparation remains possible, but creation requires all five facts.
- Manifest 2.1, generation resolution 1.1, engine proof 2.0 and Matrix 2.1 bind the ten target fields and existing evidence/authorization mechanisms. Approval v1 is unchanged. Old candidate, manifest, resolution, proof and matrix versions retain their serializers and execution paths. Mixed executable manifest versions are rejected rather than dropping semantics.
- Structured semantic assessment precedes slug matching. Complete equality reconciles an existing identity even if its display label or immutable slug differs. Complete inequalities support mechanical creation. Unique creation receipts and retained source bytes establish peer premises; explicit retained five-field facts can assess nullable legacy peers without persisting assignments. Insufficient, conflicting or unavailable peer evidence requires review. Manufacturer/emissions codes and transmission differences do not independently split records. Layout-only and evidenced tuning/output differences require review.
- The `engine-fields/1` locator recipe appends fixed aspiration/fuel/electrification qualifiers independently of occupancy. Evidenced naturally aspirated gasoline nonhybrid configurations omit them. Conflicting active/historical slugs block. Existing UUIDs and slugs remain immutable.
- Transaction-time proof reconstruction binds source documents, canonical peer state, receipt identities and projections. The existing single-plan authorization and model-year atomic Matrix execution remain in place. Retries of completed Matrix rows create no further records or receipts.
- Central long hybrid labels feed VehicleDefinition descriptions and the detail page. Central short labels feed configurator choices; known none and unknown have no inferred hybrid abbreviation. Manufacturer terms stay in descriptive/source evidence.

## Files delivered or updated

- Domain/presentation: `reference/powertrain.py`, `reference/models.py`, `reference/services.py`, `templates/reference/vehicle_definition_detail.html`.
- Additive schema: `reference/migrations/0010_vehicledefinition_electrification_type_and_more.py`.
- Candidate contracts: `reference/ingestion/contracts.py`, `reference/ingestion/serialization.py`, `reference/ingestion/validation.py`, `reference/ingestion/candidate/builder.py`, `reference/ingestion/normalization/powertrain.py`.
- Planning/execution: `reference/ingestion/importing/powertrain_identity.py`, `reference/ingestion/importing/engine_distinction.py`, `reference/ingestion/importing/planner.py`, `reference/ingestion/importing/importer.py`, `reference/ingestion/generation_correspondence.py`.
- Review/authorization dispatch: `reference/ingestion/manifest.py`, `reference/ingestion/matrix.py`, `reference/ingestion/importing/matrix_workflow.py`, `reference/management/commands/plan_canonical_import.py`, `reference/management/commands/review_generation_trim_matrix.py`.
- Tests: `reference/tests/test_structured_powertrain.py`.
- Documentation: this record, `docs/implementation/CURRENT_STATE.md`, `docs/development/INGESTION_PROTOCOL.md`, and the RA-044 implementation-status cross-reference in `docs/architecture/designs/RA-018-Canonical-Reference-Matching-Import-Architecture.md`.

Pre-existing modified/untracked architecture documents and the modified development database were preserved. No accepted ADR was edited by this implementation.

## Verification

Focused tests cover field and database validation, nullable historical rows, all supported electrification classifications, aspiration/fuel distinctions, canonical decimal precision, missing/conflicting evidence, source sharing, legacy compatibility, semantic equality, code/transmission nonidentity, collisions, stale sources/receipts/peers, reversed Matrix order, idempotence and rollback. An isolated migration test compares all pre-existing application-table columns before and after migration and verifies that historical powertrain fields remain null.

Actual results:

- Focused ingestion regression selection: 129 tests passed. Final new RA-044 coverage totals 39 tests, all passing in the complete suite.
- Complete Django suite: 691 tests executed and passed, zero failures, errors or skips.
- Django system checks: zero issues. Migration consistency (`makemigrations --check --dry-run`): no changes detected. `git diff --check`: passed.
- Development database SHA-256: identical before and after verification. No development schema or data operation occurred.

The documented `venv/py313/bin/python` does not exist in this checkout. Verification used the previously approved Homebrew Python 3.13.2 / Django 6.1.3 workaround, without rebuilding environments or changing dependencies:

```bash
PYTHONDONTWRITEBYTECODE=1 \
PYTHONPATH="$PWD/venv/lib/python3.13/site-packages" \
RIGARCHIVE_TEST_DB_PATH=:memory: \
/opt/homebrew/bin/python3.13 manage.py test --noinput
```

The same isolated environment was used for `manage.py check` and `manage.py makemigrations --check --dry-run`. Tests use a disposable Django test database; the migration preservation test migrates only that connection.

## Acceptance and operational boundary

No development migration application, historical backfill, Wrangler JL import, live receipt creation, correspondence publication or W2 implementation is part of this milestone. Existing historical artifact content and hashes are not rewritten. Implementation acceptance and later operational authorization remain separate.

## Director acceptance and post-migration inspection — 2026-11-07

The director accepts RA-044 and reports successful application of development migrations 0007–0010 and a pre/post-backup comparison: 793 historical VehicleDefinition PKs/UUIDs/slugs and 2,856 receipts unchanged. This comparison is director-reported, not independently repeated here. Current SQLite inspection using `mode=ro` confirms those migrations and counts, all five structured fields null on all definitions, integrity `ok`, and no foreign-key violations. Database hash before and after this inspection: `b045601a33811b44a443b7c0cc78ce916e9af476cb3c5f4c5b94dc2fdf18e26f`.

The earlier verification and unapplied-migration statements above describe the original implementation checkpoint. No migration, backfill, canonical import or database write occurred during this follow-up. The required `venv/py313/bin/python` is still absent; `venv/bin/python` fails to load its Python framework, and Homebrew Python 3.13 has no directly importable Django. The prior test results were not rerun. MY2019 preparation remains blocked on authentic source acquisition; see the handoff director-review report.
