# RA-048 final source review and acceptance preparation

Created: 2026-11-13
Last Updated: 2026-11-13
Status: Accepted

**Source verdict: PASS WITH CORRECTIONS. Implementation: ACCEPTED** by explicit
Project Owner decision on 2026-11-13, including the final reviewed corrections.
Acceptance excludes deferred downstream functionality and operational data writes.
No material conflict blocks minimal RA-048.

## Source findings and corrections

1. **Bulk upsert scope bypass.** An incoming vehicle with a null body could conflict
   with a persisted body-associated vehicle. bulk_create(update_conflicts=True,
   update_fields=[generation], unique_fields=[id]) changed the existing Generation
   while preserving its existing body FK. The original incoming-object guard missed
   this. Reproduced by a failing isolated regression before correction. Generation
   and body fields in conflict updates are now rejected; use validated instance saves.
   Unrelated upserts remain supported, including iterator-valued field lists.
2. **Partial-save iterator consumption.** Repeated set(update_fields) consumed a
   caller's iterator before Django save, producing an AssertionError. Reproduced
   before correction. Save now freezes update_fields once and reuses it for scope
   validation and the parent save. Five new regressions also cover safe unrelated
   upserts and bulk_update rejection of body/generation changes.

Only models.py and its focused tests needed executable changes in this review.
No new model, FK, schema, dependency, registry, binding subsystem or audit model.

| Reviewed requirement | Result |
| --- | --- |
| Integer PK / stable UUID / timestamps | Existing BaseModel conventions; no custom identity strategy |
| Required protected Generation / seven dimension groups | Correct; code and namespace are two columns in one paired group |
| Sparse nullable tokens / blank normalization / presence | Correct; token grammar reused, blanks to null, no dimensions fabricated |
| Exact duplicate prevention | Application constraint validation plus DB Generation/COALESCE tuple uniqueness; empty-string sentinel excluded by checks |
| Sparse non-merging and cross-year/trim reuse | Correct; separate exact tuples, many vehicles can reference one body |
| Nullable protected vehicle association / scope | Correct on clean/save, persisted partial-save pair and supported bulk paths after corrections |
| Existing identities and receipts | No rewrite/backfill; slug builder unchanged |
| Admin maintenance | Ordinary permissions, editable FK, shared-use warning, standard LogEntry, protected deletion; no correction required |

Direct SQL/private ORM bypasses are outside supported maintenance; scope consistency
is application-enforced rather than a composite DB FK. SQLite has transaction locking,
not effective SELECT FOR UPDATE row locks. No broader database/concurrency architecture
is claimed by this minimal implementation.

## Migration review

0011 depends on reference.0010_vehicledefinition_electrification_type_and_more.
Operations are one CreateModel, one nullable AddField and body-only constraints.
UUID uniqueness and FK indexes follow Django conventions; the expression unique
index covers null tuples. Presence, pairing and nonempty checks are necessary for
that identity rule. No unrelated model/schema change, RunPython, backfill or historical
migration edit exists. Model and migration state agree.

The isolated migration test snapshots all pre-existing table columns/values except
migration bookkeeping, migrates 0010 forward and verifies preservation, a null body
FK on the historical vehicle and an empty new table. The existing migration/receipt
suite also passes. This verifies populated old tables and the new nullable association;
it does not claim that an operational migration has run. The live database still ends
at reference migration 0010.

## Final-review verification (historical checkpoint)

Authorized fallback interpreter: .venv/bin/python (Python 3.13.1, Django 6.0.7;
venv/py313/bin/python remains absent). All Django commands used
RIGARCHIVE_TEST_DB_PATH=/private/tmp/ra048-review.sqlite3. Tests used Django-isolated
test databases; no management command was pointed at the operational database.

| Check | Fresh result |
| --- | --- |
| Two defect regressions before correction | Both failed as expected; preserved in /tmp/ra048-review-reproduction.log |
| RA-048 focused module | 34 tests, 1.515 s, passed |
| RA-048 + body identity + v3 wire + legacy construction + models + structured powertrain | 187 tests, 3.794 s, passed |
| Full Django suite after executable corrections | 871 tests, 43.409 s, passed; zero failures/errors/skips |
| manage.py check | No issues |
| manage.py makemigrations --check | No changes detected |
| git diff --check | Passed |

The earlier 29/182/866 results are historical, not these runs. The intermediate
184-test run also passed before adding three bulk-path regressions; the final 187
and 871 runs cover the final executable bytes. Logs: /tmp/ra048-review-focused.log,
/tmp/ra048-review-targeted-final.log and /tmp/ra048-review-full.log.

## Wrangler readiness

The [proposal](WRANGLER_READINESS_PROPOSAL.md) explains why both slug generation
and semantic peer assessment omit body, and recommends B: an explicit v3 identity
path with readable new-record qualifiers. Fresh in-memory reproduction confirms
31 active MY2024 offerings collapse to 21 slugs in ten pairs. No slug code changed.

Read-only SQLite URI mode=ro plus PRAGMA query_only=ON was used, without Django ORM
or migration application. No SQLite journal/WAL/SHM sidecars existed. Queries joined
VehicleDefinition → Generation → VehicleModel and successful creation receipts; JSON
receipt snapshots were decoded as data. Totals remain 1,053 VehicleDefinitions and
3,350 receipts; zero MY2024 JL rows. Generation 32 is JL, UUID
38d3c3ac-f825-4406-abb5-c2d12b9129a4.

The [355-row inventory](wrangler_body_assignment_proposals.csv) identifies all current
Wranglers with explicit scope/disposition. **260 MY2019–MY2023 JL rows** have reviewed
door proposals (77 two-door, 183 four-door). Their receipt PK/UUID/slug snapshots and
canonical field projections matched live records; exact candidate references join
the retained body rows and qualified model-code assertions. MY2021 and MY2023 execution
inventories additionally match live PK/UUID/slug. Inventory source paths/hashes and
original evidence trim labels are retained, including historical label corrections.
The MY2019 source is director-accepted research, not newly verified manufacturer PDFs.

**15 MY2018 JL rows** lack an exact per-record door join established in this review;
no inference from Unlimited/shared prose was made. This is not a demand to re-review
already established evidence: locate its exact applicable existing join first.
**80 JK rows** are identified but outside this JL assessment; no assignment proposed.
For the 260, a separately authorized FK-only assignment can preserve existing
PKs/UUIDs/trims/slugs/receipts; it must not reinterpret historical import identities.
The table/FK does not exist operationally yet. Separate migration and data-write
authorization plus stale-row verification are prerequisites to any assignment.

The successor import path remains deferred. In particular, RA-046 immutable binding
requirements cannot be declared fulfilled by editable body rows. A narrow downstream
contract decision is needed; no new binding subsystem or fabricated revision is
proposed. This does not block acceptance of the explicitly minimal storage milestone.

## Owner-authorized commit boundary

Full-file inclusion:

- reference/models.py
- reference/admin.py
- reference/migrations/0011_factory_body_configuration.py
- reference/tests/test_factory_body_configuration.py
- docs/architecture/designs/RA-048-Factory-Body-Series-Persistence-And-Immutable-Binding.md
- docs/implementation/handoffs/RA048_body_series_persistence_20261113/README.md
- docs/implementation/handoffs/RA048_body_series_persistence_20261113/FINAL_REVIEW.md
- docs/implementation/handoffs/RA048_body_series_persistence_20261113/WRANGLER_READINESS_PROPOSAL.md
- docs/implementation/handoffs/RA048_body_series_persistence_20261113/wrangler_body_assignment_proposals.csv

Shared-document inclusion only:

- docs/implementation/CURRENT_STATE.md: the complete RA-048 minimal-body-persistence
  section, ending before the existing RA-046/RA-047 section. Exclude the pre-existing
  Version 1.6 → 1.9 change and all unrelated sections.
- CHANGELOG.md: the single RA-048 milestone bullet under Unreleased → Changed.
  Exclude MY2023/MY2024 and all unrelated entries/hunks.

The exact shared-only HEAD-relative patch is prepared outside the repository at
/private/tmp/ra048-final-review-shared-documents.patch. It adds just that section and
bullet; an index-only git apply --check verifies applicability without staging.
The Project Owner explicitly authorized this inventory for one local RA-048 commit.
Do not stage entire shared documents from their mixed working-tree state.

Exclude db.sqlite3, MY2023_JL/, MY2024_JL/, docs/research/, run_readonly_plans.py,
scratch/, and every path outside the inventory. No accepted ADR or RA-045/046/047
artifact is included or changed.

## Review-checkpoint preservation and next action

Operational database SHA-256 before/after:
be3b1cfe8f03feda457f2aa7ef397b96f2cd673971aaf6a999c171c5523b32a6.
Main/HEAD remains ff106af6e5c1a18ae796a61df88d38fe8b26ec68, following de62f29/f712353.
Index remains empty. The pre-existing modified database status is preserved, not a
new write. Whole-file baseline hashes preserve unrelated evidence/research/ingestion
work, v3 code and A–H fixtures, historical 2.1.0 contracts, receipts and old migrations.
Only the scoped model/tests and milestone documentation changed in this review;
new readiness artifacts are listed above. No stage, commit, push, reset or cleanup.

Next narrowly scoped task: specify and obtain approval for the minimal Candidate v3
body-aware plan/proof/authorization/receipt and deterministic readable-slug contract,
using the reviewed Wrangler doors and existing persistence, before implementing the
successor import path. Keep operational migration and FK assignments separately
authorized. No next milestone implementation has begun.


## Formal acceptance verification — 2026-11-13

Architecture and implementation are Accepted by the Project Owner. The historical
review checkpoint above remains accurate for its time; this acceptance authorizes
staging only the listed inventory and one local commit, without a push. Fresh acceptance verification: **187 targeted tests passed in 3.840 seconds**,
with system checks, migration drift and working/staged whitespace checks passing.
The exact eleven-path inventory was verified before committing. No executable
implementation changes are part of this acceptance step; the full 871-pass result
remains historical. Operational migration and canonical data writes are not authorized.

The staged whitespace check exposed CRLF line endings in the previously untracked
assignment CSV. Acceptance finalization uses LF and quotes CSV fields to preserve trailing spaces
inside field values without Git whitespace errors; parsed headers
and all 355 data rows are identical. No assignment or evidence value changed.
