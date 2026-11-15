# MY2026 Wrangler JL registry-backed local import

Created: 2026-11-14
Status: Accepted
Last Updated: 2026-11-14
Implementation disposition: Complete locally; owner human QA approved.
Completion date: 2026-11-14.

## Scope and source validation

The owner explicitly authorized local publication of the independently extracted
MY2026 inventory after a valid preview and passing focused tests. Verified both
source artifacts: 18 styles, 33 distinct configurations, ten two-door/23 four-door,
33 gasoline/zero PHEV. All style membership, marketed trims, body dimensions,
engine offerings, source links and counts agree. Inventory SHA-256:
`aafe8c3005c95937d6269fee4a1808cf16b453e156cc1c500beddf17237525d0`.
No MY2025 offering was carried forward without the MY2026 inventory association.

Existing authored Engines resolve exactly: ERC PK1 (15), EC1 PK2 (16), ESG PK3 (2).
Their UUIDs and complete properties match the inventory. No Engine creation/update,
aspiration inference, additional PHEV, parent creation or schema change.

## Minimal implementation

- `reference/my2026_wrangler_import.py`: bounded MY2026 adaptation, reusing MY2025
  digest/snapshot/unsaved-construction/local-target helpers, registry services,
  structured body/powertrain identity and complete-family slug qualification.
  Pins source bytes, exact registry references, parents, bodies, family and current
  MY2026 namespace. Validates 18 styles/33 rows and exact offered engine membership.
- `reference/management/commands/import_my2026_wrangler.py`: read-only preview by
  default; explicit execution requires the reviewed preview digest and local target.
- `reference/tests/test_my2026_wrangler_import.py`: 17 isolated behavioral tests
  cover counts, mappings, source ambiguity preservation, idempotency, prior years,
  audit failure rollback, stale state, missing/conflicting registry records, identity
  collisions, source/style validation, command authorization and public rendering.
- `reference/models.py`: extend the established body-derived Wrangler public names
  to MY2026. Existing generic configurator filtering/grouping is reused unchanged.

No generalized framework, MSRP import/ordering, Admin slug editing, new dependencies
or migration. MY2025 service/command/tests are unchanged. No governance file changed.

## Commands and exact execution

Preview:

```sh
.venv/bin/python manage.py import_my2026_wrangler
```

Execution uses `--execute --approved-plan-hash <exact-preview-hash>`. It independently
rebuilds the preview inside the same transaction as all creates/receipts; stale or
blocked input aborts the complete batch. Registry and body rows are reused, never
authored. Domain no-ops retain the existing audited outcome vocabulary. Source URLs,
extraction date, original configuration details (including unknown pairings/source
codes), registry snapshots and the exact plan digest remain in receipt provenance.

The initial read-only preview was 33 create/zero skip/block, with exact digest:
`sha256:14cc91a525060048b2e6aa37b7781b0e7f13b8c226b84d5f46225a47a209930a`.
A temporary pre-import physical backup passed SQLite integrity and FK checks.

One explicitly invoked local transaction created 33 VehicleDefinitions PK1131–1163
and 33 creation receipts PK3456–3488, zero skips/failures. A fresh preview then
reported zero create/33 skip/zero block. An actual second execution skipped all 33,
created no duplicate definitions and added 33 no-op receipts PK3489–3521. Every
VehicleDefinition field was identical before/after that second execution.

## Verification

Working interpreter discovered: `.venv/bin/python`, Python 3.13.1, Django 6.0.7.

```sh
RIGARCHIVE_TEST_DB_PATH=:memory: .venv/bin/python manage.py test reference.tests.test_my2026_wrangler_import reference.tests.test_my2025_wrangler_import reference.tests.test_configurator_body_groups reference.tests.test_engine_registry --noinput
.venv/bin/python manage.py check
RIGARCHIVE_TEST_DB_PATH=:memory: .venv/bin/python manage.py makemigrations --check --dry-run
git diff --check
```

All 67 focused tests pass; system check, migration drift and whitespace checks pass.
The initial new test fixture supplied an explicit PK to Engine.save(), which requires
an existing row for that branch. Corrected the isolated fixture to use normal authored
creation and assert its expected PK; final focused run passes. No domain guard or
test expectation was weakened. Tests use isolated databases and temporary resources.

All 33 active MY2026 records have exact Engine FKs and matching five-field snapshots;
15 ERC/16 EC1/two ESG, ten two-door/23 four-door, no ECX/4xe/PHEV. Read-only live view
verification checked all 18 trim/body groups and every exact member/Specs link; all
33 specification pages and 18 group pages render HTTP 200 with human-readable labels.
An unsaved per-request session was used; rendering caused no database writes.

Full-field fingerprints prove every preexisting row across all 49 tables unchanged,
including MY2018–2025, all Engines/bodies/parents and prior receipts. Only 33 definitions
and 66 audit receipts were added; schema unchanged. SQLite integrity/FK checks pass.
Operational totals: 1,148 VehicleDefinitions, 3,521 receipts and seven Engines.
The original inventory and extraction report remain byte-identical. Retained
`local_import_*.json` artifacts in the MY2026 research directory record preview,
execution, rerun and complete preservation/public-rendering verification.

The prior complete-suite result (25 pre-existing configuration-label failure entries,
with the owner-approved bounded MY2025 exception) remains a known limitation. The
complete suite was not rerun here; this milestone uses the explicitly requested
passing focused-importer and Django-check execution gate. No unrelated labels/tests
were changed. Human factual/visual website QA was pending at initial publication and
has since been completed/approved by the owner (see commit preparation below). The extraction's
unsupported transmission-pairing, cross-trim option-note and ancillary source gaps remain.
They are retained without invented mechanical details or extra identities.

CURRENT_STATE and CHANGELOG updated. No commit, staging, push, production operation
or deployment; unrelated working-tree changes preserved.

## America250 supplemental completion (2026-11-14)

The owner explicitly authorized two four-door America250 identities: ERC PK1 and
EC1 PK2. `america250_supplement.json` uses the existing inventory/configuration
structure, with `owner_confirmed` availability rather than an invented standard or
optional ranking. The original Edmunds `inventory.json` and extraction report remain
byte-identical, keeping previous raw-source references/hashes valid.

The supplied Jeep.com URL explicitly contains ERC. EC1 availability is the owner's
independent official-builder confirmation; it is not falsely claimed to be proved
by the ERC URL. This work does not claim automated inspection of Jeep.com. Original
URL option tokens are preserved without decoding a transmission pairing. No Edmunds
style ID or manufacturer style ID was fabricated. Both Engines and their complete
authored properties are reused without authoring/modification.

The bounded importer now combines the unchanged 33-row base and exactly two pinned
supplement rows under `my2026-registry/2`. Separate publisher/path/hash/native-identity
bindings are preserved per receipt. The unchanged base validator still enforces its
18 observed Edmunds styles; the supplement validator permits only America250,
four-door, ERC/EC1 and explicit owner provenance. Existing generation/body/Engine,
semantic identity, slug, exact digest, local-target and atomic audit safeguards remain.
Historical plans/receipts are not rewritten or relabeled.

The incremental preview was two create/33 skip/zero block, digest
`sha256:d8312f5bd6aab0cd2d0e95913fb39427b9781cfae7cd4c161c7dda0d85e28c72`.
A verified temporary pre-supplement backup passed integrity/FK checks. Explicit local
execution created America250 PK1164 (ERC; receipt3555) and PK1165 (EC1; receipt3556),
skipping the existing 33. An actual second execution created none and skipped all 35;
all VehicleDefinition fields remained unchanged. Those two invocations added two
creation and 68 no-op receipts, with no other operational additions or changes.

Final counts: 35 active MY2026 definitions, 19 exact trim/body groups, ERC16/EC1 17/
ESG2, ten two-door/25 four-door, zero PHEV. All 49 tables' preexisting rows are
field-identical, including all earlier years, the original 33 MY2026 definitions,
Engines, bodies, parents and prior receipts. Schema unchanged; integrity/FK checks
pass. All 19 public group pages and 35 Specs pages render HTTP200 through read-only
verification. Original Edmunds source bytes and Git index remain unchanged.

All 72 focused tests pass, including five new supplemental tests for 2-create/33-skip
behavior, exact preservation, truthful source attribution, late receipt rollback and
America250 public grouping. Existing tests now cover the combined 35-row family.
System/migration-drift/whitespace checks pass. The first focused run caught one stale
33-row command-preview expectation; updated it to the required 35-row cold preview
and reran the complete focused set successfully. No unrelated test was weakened.
Prior full-suite limitations remain as documented; no broad suite rerun.

Supplement, incremental preview, execution, rerun, idempotency, report and full
post-verification artifacts are retained under the MY2026 research directory with
the `america250_` prefix. CURRENT_STATE/CHANGELOG updated. No migration, MSRP,
price-based ordering, Admin slug editing, staging, commit, push or deployment.
Human website QA has since been completed/approved by the owner. Standard/optional ranking and transmission pairings
remain unasserted. No remaining publication blocker for these two confirmed rows.

## Final MY2026 commit preparation and owner QA approval (2026-11-14)

The owner reports completed human QA and approves the combined MY2026 inventory,
including America250, for focused commit preparation. This records the owner's
approval; no additional human inspection is claimed by the implementation agent.
Historical acquisition artifacts retain their original source bytes/wording and
receipt hashes; this completion record and CURRENT_STATE record the final approval.

Fresh read-only verification confirms 35 active JL definitions, 19 trim/body groups,
ERC PK1: 16, EC1 PK2: 17, ESG PK3: 2, ten two-door/25 four-door, zero PHEV,
and two America250 four-door identities with ERC/EC1. Preview is zero create,
35 skip, zero block. All registered snapshots and receipt source hashes validate.
Field-complete comparisons against the pre-MY2026 and pre-America250 fingerprints
confirm preservation of all 1,115 and 1,148 preexisting definitions respectively.
JL counts by year remain 2018:15, 2019:19, 2020:49, 2021:73, 2022:55, 2023:64,
2024:31, 2025:31 and 2026:35. Operational totals remain 1,150 definitions,
3,591 receipts and seven Engines. No operational writes/imports occurred in preparation.

All 72 focused MY2025/MY2026 import, body-group and Engine-registry tests pass
(8.652s) using `.venv/bin/python` (Python 3.13.1, Django 6.0.7). System check and
migration drift pass; the actual development migration plan is empty. SQLite
integrity/FK checks pass. The existing unrelated full-suite label-test limitations
were not repaired or rerun. No migration or deferred feature implementation.

Reviewed all four tracked modifications and all 946 untracked file paths. Stage
only 21 milestone files: service, management command, tests, model naming change,
this record, MY2026-only CURRENT_STATE/CHANGELOG hunks, and the 14 MY2026 research
source/report/verification artifacts. Other shared-document hunks remain unstaged.
MY2023/MY2024/RA050/RA051 handoffs, MY2025 blocked-preview diagnostic, unrelated
coverage register/test/helpers and scratch files remain unstaged. The database
contains mixed preexisting changes and is excluded from the source commit.

Proposed commit message: `Add registry-backed MY2026 Wrangler JL import`.
No remaining milestone blocker. No commit, push, deployment or production change;
the owner retains manual commit authorization/control.
