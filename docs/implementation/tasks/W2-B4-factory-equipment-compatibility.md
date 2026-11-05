# W2 B4 — Factory equipment and compatibility implementation record

Status: F1–F3 CORRECTIONS VERIFIED, PENDING INDEPENDENT ARCHITECTURAL ACCEPTANCE (2026-11-04). The original B4 implementation and verification history is retained below. The corrective verification section records the current results; no architectural acceptance or B5 work is claimed.

## Objective, scope and authority

Implement approved factory equipment models (`EquipmentItem`, `EquipmentItemRevision`, `EquipmentOffering`, `EquipmentOfferingRevision`, `CompatibilityRule`, `CompatibilityRuleRevision`), catalogue membership, evidence links, and publication/replay integration under existing Phase A contracts.

Canonical VehicleDefinition identities remain stable. Equipment offerings are subordinate to VehicleDefinitions. No presentation/UI, manufacturer acquisition, or B5 work.

Governing: accepted [ADR-0010](../../architecture/ADR/ADR-0010-Generation-Correspondence-Selectable-Factory-Alternatives.md) and [ADR-0011](../../architecture/ADR/ADR-0011-Factory-Body-Configuration-Identity.md); W2 [domain architecture](../../architecture/designs/W2-Full-Specifications-Domain-Architecture.md), [properties/applicability contract](../../architecture/designs/W2-Specification-Property-Applicability-Contract.md), [enrichment/publication contract](../../architecture/designs/W2-Enrichment-Publication-Contract.md); [INGESTION_PROTOCOL.md](../../development/INGESTION_PROTOCOL.md), [CURRENT_STATE.md](../CURRENT_STATE.md), and [B3 verification record](W2-B3-transmission-implementation.md).

## Files and functionality completed

- `reference/specifications/models.py`:
  - `EquipmentItem`: Logical equipment/package/accessory identity tied to manufacturer, namespace, and source native identity.
  - `EquipmentItemRevision`: Immutable revision chain for equipment items with kind (`equipment_item`, `factory_package`, `factory_option`, `accessory`), installation channel (`factory`, `manufacturer_accessory`, `unresolved`), name, code, contents (for packages), and qualified evidence links. Constraints enforce revision number sequence, predecessor matching, and append-only guards.
  - `EquipmentOffering`: Logical offering chain tied to exact `VehicleDefinition` and `EquipmentItem`.
  - `EquipmentOfferingRevision`: Immutable revision chain with assignment (`standard`, `optional`, `unavailable`, `unknown`, `accessory_catalogue_only`), equipment policy validation (brochure listed, package identification, exception authorization), and qualified evidence links.
  - `CompatibilityRule`: Logical compatibility rule tied to exact `VehicleDefinition`.
  - `CompatibilityRuleRevision`: Immutable revision chain for compatibility rules with rule kind (`requires_all`, `requires_any`, `excludes`, `includes`, `replaces`, `cardinality`, `supports_combination`) and qualified evidence links.
  - `SpecificationCatalogueMembership`: Extended with foreign keys `equipment_item_revision`, `equipment_offering_revision`, and `compatibility_rule_revision`; updated exclusive target check constraint and per-owner unique constraints.
  - `SpecificationEvidenceLink`: Extended with foreign keys `equipment_item_revision`, `equipment_offering_revision`, and `compatibility_rule_revision`; updated exclusive owner check constraint, per-owner unique constraints, and validation logic.
- `reference/models.py`:
  - Re-exports `EquipmentItem`, `EquipmentItemRevision`, `EquipmentOffering`, `EquipmentOfferingRevision`, `CompatibilityRule`, `CompatibilityRuleRevision` within the Reference application.
- `reference/specifications/publication.py`:
  - `MEMBER_MODELS`: Registered `equipment_item`, `equipment_offering`, `compatibility_rule`.
  - `_scope()`: Updated scope check to permit equipment and compatibility rule members and dependencies, guarding feature mapping (B5).
  - `_revision_root()`: Implemented logical root resolution and validation for `equipment_item`, `equipment_offering`, and `compatibility_rule`.
  - `_chain()`: Mapped `equipment_item -> item`, `equipment_offering -> offering`, `compatibility_rule -> rule`.
  - `_state()`: Registered equipment and rule member kinds for dependency leaf checks.
  - `_persist()`: Integrated persistence and evidence linking for `equipment_item`, `equipment_offering`, and `compatibility_rule`.
- `reference/migrations/0009_factory_equipment_compatibility.py`:
  - Additive migration depending on `0008_transmission_domain`.
  - Creates tables for `EquipmentItem`, `EquipmentItemRevision`, `EquipmentOffering`, `EquipmentOfferingRevision`, `CompatibilityRule`, `CompatibilityRuleRevision`.
  - Updates `SpecificationCatalogueMembership` and `SpecificationEvidenceLink` constraints and foreign keys.
  - Adds unique and predecessor check constraints.
  - UNAPPLIED to the development database.
- `reference/tests/test_equipment_publication.py`:
  - Eight focused synthetic tests covering:
    - Equipment classifications (standard, optional, package, accessory) and exact membership/evidence publication.
    - Brochure-controlled equipment scope and unlisted accessory exclusion.
    - Compatibility rules evaluation (`requires_all`, `excludes`, `cardinality`, `supports_combination`) and rule persistence.
    - Higher-order selection uncertainty and unknown vs. unselected equipment.
    - Foreign/wrong baseline rejection during zero-write planning.
    - Equipment offering supersession and historical preservation.
    - Atomic rollback on receipt failure.
    - Immutability of equipment and compatibility rule records.
- `reference/tests/test_specification_publication.py`:
  - Re-scoped `test_b4_members_guarded_before_any_publication` to `test_b5_members_guarded_before_any_publication` (guarding `physical_feature_mapping` before B5).

## Verification and preservation boundary

- `db.sqlite3` SHA-256 at start of verification session: `cee1c51459f8dc8e3f4abd267bc7f5a72305767ce5c45e89e32048fe0398e0a3` (pre-existing discrepancy from B1/W1 session documented in CURRENT_STATE.md; cause unestablished; unrelated to B4 work).
- `db.sqlite3` SHA-256 after B4 verification: `4e1dff5fcdcfceef1099eb7e88b6ed6bf60665ce0fab5e1a50a42af66a7d0f49` (historically reported value; it differs from the recorded starting hash above, so those two values do not establish byte preservation. The cause is unestablished; a SQLite/WAL explanation has not been verified).
- Retained `storage/` 71-file inventory aggregate SHA-256: `118d838926f7d48dc6c7a028d806b3ce85ed7060347d7ac244f07020bfa61174` — **matches baseline exactly**.
- Zero development database migrations or mutations were executed during verification.

## Defects corrected during verification

### 1. Migration 0009 check-constraint field ordering

`makemigrations --check --dry-run` detected a discrepancy: migration 0009's two `CheckConstraint` conditions (for `SpecificationCatalogueMembership.reference_spec_membership_one_target` and `SpecificationEvidenceLink.reference_spec_evidence_one_owner`) used declaration-order field ordering within each Q clause. Django's `_exclusive_target()` function generates alphabetical field order. These are functionally equivalent SQL constraints but Django's migration state comparison is order-sensitive.

Fix: Rewrote both check constraints in `0009_factory_equipment_compatibility.py` using alphabetically sorted field order matching Django's generation. Migration consistency check then passed with "No changes detected".

### 2. Test operand ordering in `test_compatibility_rules_evaluation_and_publication`

The `operands` validator (via `array(..., ordered=True)`) requires arrays to be sorted by `member_key = (kind, revision_uuid)`. In the `r_combo` rule fixture, the `offerings` and `universe` arrays listed `transmission_offering` before `equipment_offering`, but `'equipment_offering' < 'transmission_offering'` alphabetically.

Fix: Swapped operand order to `[operand(opt_a[1]), operand(tx[1])]` for both `offerings` and `universe` in `test_equipment_publication.py` lines 138–140.

## Verification commands and results (2026-11-04)

```
RIGARCHIVE_TEST_DB_PATH=/tmp/b4_check.sqlite3 venv/py313/bin/python manage.py check
# → System check identified no issues (0 silenced). ✓

RIGARCHIVE_TEST_DB_PATH=/tmp/b4_check.sqlite3 venv/py313/bin/python manage.py makemigrations --check --dry-run
# → No changes detected. ✓

# Isolated migration test (0006→0007→0008→0009→all):
RIGARCHIVE_TEST_DB_PATH=/tmp/b4_mig_test.sqlite3 venv/py313/bin/python manage.py migrate
# → All migrations applied cleanly. ✓

# Full test suite (141 tests):
RIGARCHIVE_TEST_DB_PATH=/tmp/b4_runner2.sqlite3 venv/py313/bin/python manage.py test \
  reference.tests.test_equipment_publication \
  reference.tests.test_transmission_publication \
  reference.tests.test_specification_publication \
  reference.tests.test_specification_primitives \
  reference.tests.test_specification_artifacts \
  reference.tests.test_models \
  reference.tests.test_canonical_import_execution
# → Ran 141 tests in 2.456s — OK ✓
#   (8 B4 + 6 B3 + 20 B2 + 86 B1 + 21 reference regressions)

git diff --check
# → No trailing whitespace issues. ✓
```

## Outstanding work and next steps

1. Architectural review and acceptance of B4 by the project director.
2. Begin B5 (Factory Body Identity & Physical Feature Mappings) only after explicit B4 acceptance.


## F1–F3 corrective implementation and verification (2026-11-04)

Status: corrections implemented and verified; B4 remains pending independent architectural acceptance. No B5 work, commit or push.

### Corrections and semantic resolution

- `reference/specifications/evaluation.py`: collect package/rule effects with fixed reviewed applicability, effective-date and trigger premises. Resolve standard-equipment dependencies synchronously from the complete effect set, beginning with unknown dependent effects. Knowledge refinement is bounded by the effect count; unresolved dependency cycles remain unknown. Definitive removals disable dependent standard effects; conflicting/possible additions and removals remain conservative. Inactive premises dominate unknown findings through three-valued conjunction. Every predicate invocation uses the existing shared budget; the resolution loop performs only truth/set operations. Offering selections and the independent coexistence proof mechanism remain separate.
- `reference/specifications/catalogue.py`: exact-resolve every package constituent/replacement target and reject accessory kinds. Validation visits all package records, so nested packages without standalone offerings cannot bypass the prohibition. Accessory catalogue-only representation is preserved.
- `reference/tests/test_specification_artifacts.py`: 18 new regressions covering all rule permutations for established replacement plus standard inclusion, absence of a coexistence proof, false/unknown applicability, expired/unknown dates, inactive/unknown triggers, unresolved findings, conflicting additions/removals, dependent replacement chains/cycles, package conflicts, direct/nested accessory edges and valid direct/nested nonaccessory packages. Permutation checks also assert unchanged selections and equal predicate-budget charges.
- `reference/tests/test_equipment_publication.py`: one new regression with four planning subcases (constituent/replacement, direct/nested), asserting rejection before any publication writes. Existing publication tests continue to verify legitimate accessory catalogue-only offerings.
- Updated this record, `docs/implementation/CURRENT_STATE.md`, and the existing Unreleased B4 changelog entry. No models, migrations, schemas, governance or approved contracts changed.

The F1 example resolves to SUPPORTED in every permutation because the established replacement removes S and disables S's inclusion; the exact coexistence proof independently establishes the unchanged selection. Without that proof the result remains UNVERIFIED. Unknown replacement premises remain UNVERIFIED; conflicts are not resolved by rule priority.

### Verification

All Django invocations used `venv/py313/bin/python -B` (Python 3.13) with `RIGARCHIVE_TEST_DB_PATH` pointing to temporary verification resources. The final combined run used a directory created with `mktemp -d "${TMPDIR:-/tmp/}rigarchive-b4-fix.XXXXXX"`; no command targeted the persistent database for writes.

- Focused corrective classes plus the new zero-write planning method: 19 tests passed, zero failures. An earlier 16-test focused run also passed before the three trigger/dependency boundary tests were added.
- Existing specification selection (equipment/transmission/specification publication, primitives and artifacts): 136 tests passed, zero failures before those three additional tests; all final tests were included in the combined run below.
- Final combined command: `python -B manage.py test reference.tests.test_equipment_publication reference.tests.test_transmission_publication reference.tests.test_specification_publication reference.tests.test_specification_primitives reference.tests.test_specification_artifacts reference.tests.test_models reference.tests.test_canonical_import_execution reference.tests.test_equipment_ingestion_policy reference.tests.test_multi_source_population reference.tests.test_production_manufacturer_acquisition reference.tests.test_acquisition_adapters reference.tests.test_manufacturer_ingestion --noinput`: 227 tests passed, zero failures. Earlier combined run: 224 passed before the three boundary additions.
- `python -B manage.py check`: passed, zero issues.
- `python -B manage.py makemigrations --check --dry-run`: passed, no changes detected.
- `git diff --check`: passed.

### Preservation and remaining boundary

The director authorized `09754fa3a988df19c984e5a492d4e869ae3f0921ee44517fe7f1113df417e873` as this task's preservation baseline only. It matched before editing and after testing. Its historical difference from `4e1dff5fcdcfceef1099eb7e88b6ed6bf60665ce0fab5e1a50a42af66a7d0f49` is an unexplained observation, not evidence of a confirmed SQLite/WAL mechanism. No restore, migration or mutation of development data was attempted.

All 71 retained storage files have identical paths and SHA-256 hashes before/after; storage was not modified. Existing staged, modified and untracked work was preserved. No dependencies installed, no migrations created, no architectural decision changed, no commit/push performed. No known failing corrective checks remain. Independent architectural re-review and director acceptance are outstanding.
