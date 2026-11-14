# RA-048 — Minimal factory body persistence handoff

Created: 2026-11-13
Last Updated: 2026-11-13
Status: Accepted
Disposition: **ACCEPTED** by explicit Project Owner decision on 2026-11-13.

The Project Owner's revised task supersedes the previous stop-before-schema review
and its unapproved D1–D3 recommendations. The simplified architecture direction is
approved; the implementation and final corrections are now owner-accepted. Baseline main/HEAD:
`ff106af` following `de62f29` and `f712353`; these commits remain unchanged.

## Delivered architecture

One new canonical model, `FactoryBodyConfiguration`, inherits the existing integer PK,
unique UUID and created/updated timestamps. Required `generation` uses PROTECT,
reverse name `factory_body_configurations`.

| Nullable field (CharField, max_length=128, blank=True) | Meaning |
| --- | --- |
| body_style | Reviewed body style designation |
| wheelbase_designation | Manufacturer wheelbase designation, not a measurement |
| body_length_designation | Manufacturer length designation |
| roof_height_designation | Manufacturer roof designation |
| door_configuration | Includes verified canonical tokens two-door / four-door |
| side_door_arrangement | Reviewed side door designation |
| body_code | Reviewed manufacturer code |
| body_code_namespace | Required exactly when body_code is populated |

The code pair is one logical dimension: seven dimension groups, eight scalar columns.
`VehicleDefinition.factory_body_configuration` uses PROTECT, null=True, blank=True,
related_name=`vehicle_definitions`. No other canonical model or FK was added.

Blank strings normalize to null. Non-string measurements and noncanonical populated
tokens are rejected using the existing pure token grammar. At least one dimension
is required; namespace alone never qualifies. Database checks enforce presence,
nonempty strings and code pairing. Full model validation and a database expression
unique constraint enforce Generation plus the complete normalized tuple, including
nulls. A sparse tuple is never automatically merged with a richer compatible tuple.
No semantic digest, placeholder or evidence metadata is invented.

Vehicle clean and save enforce matching Generation, including partial saves against
the actual persisted pair. A shared body's Generation cannot change incompatibly.
Writes use transactions and body row locks where supported. Body partial/bulk writes
and Vehicle bulk body assignments/creation are rejected in favor of validated saves;
bulk Generation edits involving body-associated vehicles are also rejected. Legacy
null-body bulk workflows are preserved. Raw SQL/private ORM bypasses are outside the
supported correction interface; cross-table scope is application validation.

Ordinary Django Admin supports create/edit, displays dimensions and Generation, and
exposes the vehicle FK through autocomplete. Shared-body change views warn that all
referencing vehicles are affected and recommend FK correction or a distinct record.
Standard permissions and LogEntry auditing apply; referenced deletion is protected.
No new approval workflow, immutable bindings or audit model was introduced.

## Complete implementation file inventory

| File | Change |
| --- | --- |
| reference/models.py | Body model, constraints, validation/write guards, nullable vehicle FK and scope validation |
| reference/admin.py | Body Admin, shared-edit warning, vehicle FK display/edit |
| reference/migrations/0011_factory_body_configuration.py | Additive schema migration depending on 0010; no data operation |
| reference/tests/test_factory_body_configuration.py | 34 isolated model, Admin and migration tests after final review |
| docs/architecture/designs/RA-048-Factory-Body-Series-Persistence-And-Immutable-Binding.md | Revised in place for owner-approved simplification; original D1–D3 explicitly deferred |
| docs/implementation/handoffs/RA048_body_series_persistence_20261113/README.md | This implementation/verification handoff replaces the blocked reconciliation |
| docs/implementation/CURRENT_STATE.md | Only RA-048 milestone section replaced |
| CHANGELOG.md | Only RA-048 milestone entry replaced |

The design and handoff were already untracked before this implementation. All other
pre-existing changes, including db.sqlite3, MY2023/MY2024, research and scratch, remain
preserved. No governance document, accepted ADR or historical migration was modified.

## Historical implementation verification (not rerun results)

The required `venv/py313/bin/python` was absent. The user's existing authorization to
use suitable `.venv/bin/python` was reused: Python 3.13.1, Django 6.0.7. No installation,
PYTHONPATH workaround or environment change was performed.

All commands below used
`RIGARCHIVE_TEST_DB_PATH=/private/tmp/ra048-check.sqlite3` before `.venv/bin/python`.
Django test databases and temporary test media/artifacts remained isolated.

| Command/check | Actual result |
| --- | --- |
| manage.py makemigrations reference --name factory_body_configuration | Generated 0011 only; no operational migration application |
| manage.py test reference.tests.test_factory_body_configuration --noinput | 29 tests passed in 1.501 s |
| manage.py test reference.tests.test_factory_body_configuration reference.tests.test_body_identity reference.tests.test_candidate_v3_wire reference.tests.test_candidate_construction reference.tests.test_models reference.tests.test_structured_powertrain --noinput | 182 tests passed in 3.744 s |
| manage.py test --noinput | 866 tests passed in 42.103 s; zero failures, errors or skips |
| manage.py check | No issues |
| manage.py makemigrations --check | No changes detected |
| git diff --check | Passed |

The new migration test rolls an isolated database back to 0010, creates a historical
vehicle, snapshots every pre-existing table's columns/values (excluding migration
bookkeeping), migrates forward and compares all original values. The new FK is null;
the body table is empty. It restores latest schema in finally. Existing migration and
receipt tests also pass in the full suite. New model/Admin tests cover door variants,
reuse, null associations, exact and sparse identities, DB null-tuple duplicate rejection,
generation scope, protected deletion, shared corrections, ordinary permissions and
Admin auditing. Sport door variants use explicit distinct test slugs: the test does
not pretend the unchanged legacy slug builder is body-aware.

## Preservation and remaining work

Operational database SHA-256 before and after:
`be3b1cfe8f03feda457f2aa7ef397b96f2cd673971aaf6a999c171c5523b32a6`.
It was not migrated or written. No Wrangler records were created/corrected; no backfill
or identity, trim, UUID, slug, receipt, source, candidate or evidence rewrite occurred.
Baseline file hashes confirmed that only the eight inventory paths changed or were
created. Candidate v3 wire code, semantic hashing, A–H fixtures and Candidate 2.1.0
remain byte-identical, with their regression tests passing. The index remains empty.
No staging, commits, pushes, resets or cleanup were performed.

Before assigning bodies to existing Wrangler records: obtain review acceptance and
separate authorization to apply 0011 to the operational database, identify the exact
reviewed Generation/body tuples and target records, and obtain authorization for those
specific data writes with preservation checks. Reuse existing reviewed evidence; no
new Wrangler adjudication round is required solely for this population. Existing
Unlimited labels and historical provenance remain intact.

FactorySeries, registry fields, evidence snapshots/binding revisions and revision FKs
remain deferred. Body-aware canonical matching/slugs, dependency resolution,
authorization/certification and Candidate v3 import execution remain separate. Two
otherwise identical Sport definitions still collide through the old generated slug
path; this milestone stores body associations but does not claim import readiness or
change that policy. No next milestone has begun.


## Final source review and acceptance preparation — 2026-11-13

**PASS WITH CORRECTIONS; formally accepted by the Project Owner on 2026-11-13.** Two reproduced defects were
corrected without changing schema or contracts: bulk conflict updates could change
an existing body-associated vehicle's Generation behind an incoming null body, and
save consumed iterator-valued update_fields. Conflict writes of generation/body fields
now require individual validated saves. Iterables are materialized once. Safe unrelated
upserts remain supported. Five regression tests bring RA-048 coverage to 34 tests.
The migration and Admin implementation required no correction.

Fresh verification: **34 focused tests passed in 1.515 s; 187 targeted tests passed
in 3.794 s; 871 full-suite tests passed in 43.409 s** (no failures/errors/skips).
System checks, migration drift and whitespace checks passed. The preceding 29/182/866
results above remain historical evidence. All new runs used the same authorized .venv
and isolated test database configuration with /private/tmp/ra048-review.sqlite3.

The [final review](FINAL_REVIEW.md) contains the full verdict, exact commit boundary,
read-only access method and preservation results. The separately proposed
[Wrangler follow-up](WRANGLER_READINESS_PROPOSAL.md) recommends a versioned body-aware
v3 identity path, not a slug-only repair. Its downstream binding/snapshot and execution
contracts require approval; no new binding subsystem is proposed. The
[assignment inventory](wrangler_body_assignment_proposals.csv) has 260 reviewed JL
proposals, 15 JL rows needing an exact existing-evidence join and 80 out-of-scope JK
rows. No migration application or canonical writes occurred. Architecture approval
and implementation acceptance are now recorded. Successor functionality remains deferred.


## Acceptance and local commit authorization — 2026-11-13

The Project Owner accepts only minimal RA-048, including migration 0011 and the
reviewed corrections, and authorizes one local commit with the FINAL_REVIEW inventory
and RA-048-only shared-document hunks. FactorySeries, binding revisions, registries,
v3 execution, operational migration and Wrangler assignments remain unauthorized.
Fresh acceptance checks pass: **187 targeted tests in 3.840 seconds**, system
checks, migration drift and whitespace checks. Exact boundary is in FINAL_REVIEW.
The historical no-staging/no-commit statements above describe earlier checkpoints.
No push is authorized. The assignment inventory remains unchanged.
