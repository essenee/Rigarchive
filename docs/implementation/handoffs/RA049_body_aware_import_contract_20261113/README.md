# RA-049 — Body-aware v3 import implementation handoff

Created: 2026-11-13
Last Updated: 2026-11-13
Status: Accepted
Disposition: **ACCEPTED** by the Project Owner on 2026-11-13; source verdict PASS WITH CORRECTIONS.

The Project Owner approved the exact RA-049 contract and §11 runtime clarification,
and authorized implementation/isolated verification on 2026-11-13. The Project Owner has now formally accepted the reviewed implementation. Baseline main/HEAD:
`29ff1b4a42c99c8ecf9c75b77cd5b2c0dfce706f` (Accepted RA-048). One exact 21-path local RA-049 commit is authorized; no push.

## Authority and compatibility

[RA-049](../../../architecture/designs/RA-049-Body-Aware-Candidate-v3-Import-Contract.md)
is Approved. Its PendingBody reuse exception is recorded verbatim in RA-046 §15;
no accepted ADR or historical clause was rewritten. Pinned plan/evidence/authorization/
receipt state is expressly **not** an immutable binding revision. ExistingBody wire
semantics are unchanged and unsupported for execution. No FactorySeries, parent writes,
Scope registry, evidence-binding model, new approval system, FK or migration.

The initial profile is exactly `my2024-wrangler-jl-consumer/1`: the 31 active US
MY2024 JL offerings, complete five-field engines and null series. The source inventory
and trim audit are independently SHA-256-pinned; missing/replaced/quarantined release
members cannot shrink the family. Published reviewed correspondence resolves actual
Generation; only exact supported pre-existing body tuples are reused. No UUID is
minted by planning. Missing body parents/evidence return closed non-executable reports.

## Exact implementation file inventory

| File | Delivered change |
| --- | --- |
| reference/ingestion/body_import_contracts.py | Closed recursive states and 3.0.0 contracts; validation, ordering, parse/serialize/hash checks using existing canonical_json |
| reference/ingestion/importing/body_identity.py | Safe retained-byte reads, independently pinned release, qualified evidence, reviewed Generation/exact body resolution, peer assessment and complete-family slug planning |
| reference/ingestion/importing/body_import.py | Matrix/manifest construction, independent revalidation, atomic batch executor and existing-model receipt persistence |
| reference/ingestion/importing/__init__.py | Explicit versioned batch entry point |
| reference/ingestion/importing/planner.py | Candidate v3 dispatch requiring a complete retained release; legacy branches unchanged |
| reference/ingestion/importing/importer.py | Reject v3 dictionary plans in legacy single-plan executor |
| reference/ingestion/importing/workflow.py | Reject Manifest3 in legacy single-plan workflow |
| reference/ingestion/importing/matrix_workflow.py | Explicit execute_body_matrix entry point; reject Matrix3 in legacy MatrixYear |
| reference/ingestion/importing/powertrain_identity.py | Explicit rejection of body receipt 3.0.0 by Engine Proof 2.0 reader; no equality change |
| reference/ingestion/manifest.py | Strict Manifest3 reader/writer dispatch; legacy readers unchanged |
| reference/ingestion/matrix.py | Strict Matrix3 validation/canonical payload/digest dispatch for existing approval1 integration |
| reference/tests/body_import_support.py | Synthetic positive source evidence and correspondences in temporary roots/isolated databases; no operational classifications |
| reference/tests/test_body_import_contracts.py | 20 contract/graph, complete-family, vectors, authority, drift and compatibility tests |
| reference/tests/test_body_aware_import.py | 39 live-resolution, evidence, execution, receipt, rollback and concurrency tests |
| reference/tests/test_body_import_final_review.py | 27 final-review adversarial, reader-integration and real commit-boundary regressions |
| docs/implementation/handoffs/RA049_body_aware_import_contract_20261113/FINAL_REVIEW.md | Source findings, corrections, reader matrix, fresh checks and exact proposed acceptance boundary |
| docs/architecture/designs/RA-046-Candidate-v3-Exact-Wire-Contract-Specification.md | Only labeled owner-approved scoped clarification appended as §15 |
| docs/architecture/designs/RA-049-Body-Aware-Candidate-v3-Import-Contract.md | Approved status, exact owner decision and verified implementation record |
| docs/implementation/CURRENT_STATE.md | New RA-049 milestone section only |
| CHANGELOG.md | New RA-049 milestone entry only |
| docs/implementation/handoffs/RA049_body_aware_import_contract_20261113/README.md | This updated implementation handoff |

New code is limited to three scoped application/contract modules and four test files.
No model, migration, legacy slug builder, pure Candidate v3 module or fixture changed.

## Public workflow and closed versions

- `body_import_contracts.validate(kind, value)`, `parse(kind, text)` and
  `serialize(kind, value)` implement all approved common state types plus Proof3,
  Plan3, Assessment3, Matrix3, Manifest3, Revalidation3 and Receipt3. These are exact
  3.0.0 discriminators; Approval1 retains version 1.0. Unknown keys, duplicate JSON
  keys/IDs, noncanonical arrays/timestamps, invalid tokens/nulls, bool-as-int,
  nonfinite numbers, nested hash mismatches and unsupported review readers reject.
  Builders explicitly seal newly constructed values; parsing never repairs inputs.
- `Release(candidate_paths, root=authorized_root)` reloads all 31 retained v3 files,
  independent inventory, source bytes and current parents. `release.plan(reference)`
  returns an exact Plan3, blocked Plan3 or Assessment3, never an eligible fiction.
- `plan_candidate_import(candidate_v3, body_release=release)` is explicit dispatch;
  it checks that the supplied document equals the retained release member.
- `build_matrix(plans)` enumerates only executable selected plans against the same
  pre-batch state/family. `build_matrix_approval(..., confirmed=True)` reuses the
  existing actual human-confirmation boundary; a JSON approval/hash alone grants
  no authority. `build_manifest(matrix, approval)` binds the exact Matrix and approval.
- `execute_body_matrix(...)` / `execute_body_import_batch(...)` require exact operator,
  execution-agent attribution, affirmative confirmation and non-review-only mode.
  These interfaces do not themselves impersonate the approver. Production use still
  requires actual explicit owner authorization for the exact enumerated Matrix.

## Identity, slugs and evidence

Identity is baseline/2: exact Scope/year/market/trim/drive, five powertrain fields,
body semantic digest and null series. Descriptors and slugs are not equality keys.
Supported exact active equality produces no-op; proven different bodies/powertrains
remain distinct. Compatible sparse tuples, unresolved overlapping null-body peers,
inactive equal peers and duplicates block unsafe creation. Nulls are not universal
bodies. A supported no-op on a null FK preserves that null; it does not backfill.
Existing descriptive engine aliases remain unchanged when their evidenced tuple and
displacement/cylinder expression agree. Creation receipts and source support bind peers.

The existing legacy slug builder is reused without changing its behavior or minting
UUIDs on temporary slug objects. The complete 31-member family fixes readable door
qualification independently of input order, selected Matrix subset or insertion order.
All ten known paired bases receive -2-door/-4-door; the other 11 keep structured bases.
All 31 are unique in isolated acceptance tests. Residual collisions, inactive occupancy
and >180 characters reject without truncation, UUID suffixes or random repair.

Evidence is checked through original retained bytes and qualified positive grouping,
not file presence/hash alone or the negation of has_evidence_errors. Scope and pending
parent diagnostics are discharged only by actual reviewed live resolution. Direct native
JSON assertion projections must match retained source assertions. The pinned CSV reader
supports exact model-code/heading/row joins; unsupported extracted claims are dependency
failures. It does not turn provisional/proposed powertrain columns into accepted facts.
The reviewed trim mapping is the exact retained audit, not unrestricted prefix removal.
Required pending/conflicting material classifications block the entire family.

Original review readers are intentionally version-specific. Contract payload readers
recognize Generation correspondence 1.0 and body-import receipt 3.0.0; unsupported
findings/readers are explicitly unavailable. Historical candidate-bound adjudication
cannot be rebound to a v3 candidate. Required unknown source/review decoders remain
real dependencies, not implicit approval or a reason to fabricate a new review record.
Retained paths cannot escape the authorized root or traverse symlinks. No source
acquisition, instruction execution from source material or network operation occurs.

## Transactions and receipts

The executor validates exact plans/Matrix/approval, then independently reconstructs
all selected plans against one common pre-batch state inside transaction.atomic.
Candidate, source/finding, correspondence chain, Generation, body attributes/timestamp,
body namespace, peers/active state, full family or slug namespace drift yields stale
revalidation and zero writes. Only after every selected row revalidates are enumerated
vehicles and receipts inserted. Own earlier batch inserts do not stale later rows.

No-op writes receipt only. No parent write or existing vehicle update/delete occurs.
Any vehicle/receipt failure rolls back the complete selected batch. SQLite conflicts
are not caught-and-continued or automatically retried against old approval. Concurrent
equal requests cannot both create; distinct-body requests never merge. A loser may
need a fresh plan and affirmative approval; a joint two-body batch commits both.
Threaded isolated tests exercise real SQLite transactions, plus fresh approved retry.

Each existing ImportExecutionReceipt stores exactly
`resolution_snapshot_json = {"body_import": ReceiptSnapshot3}`. The snapshot embeds
complete Manifest3, Plan3 and Revalidation3, actual persisted identity/fields, result,
execution agent/time and snapshot hash. Scalar mirrors and human approver remain
separate from execution-agent attribution. The complete original decision remains
reconstructible after a later authorized shared-body Admin edit. No historical receipt
is rewritten; legacy Engine Proof 2.0 readers reject the new version explicitly.

## Historical implementation verification — before final source review

The previously authorized `.venv/bin/python` fallback remains in use (Python 3.13.1,
Django 6.0.7); required venv/py313/bin/python was not installed or substituted through
PYTHONPATH. All Django commands used
`RIGARCHIVE_TEST_DB_PATH=/private/tmp/ra049-check.sqlite3`. Tests used isolated Django
databases and temporary source/media roots, never operational db.sqlite3.

| Executed check | Actual result |
| --- | --- |
| Focused contract/import modules | **59 tests passed, 29.591 seconds** |
| RA-049 + RA-048 + body foundations + Candidate v3 + legacy candidate/powertrain/import/execution/Matrix/approval/serialization | **335 tests passed, 33.532 seconds** |
| Full Django suite | **930 tests passed, 70.746 seconds**, zero failures/errors/skips |
| manage.py check | No issues |
| manage.py makemigrations --check | No changes detected |
| git diff --check plus untracked-code/doc whitespace checks | Passed |

Coverage includes exact closed graphs, all 31/ten-pair vectors, 180/181 boundaries,
ordering/subset independence, sparse/null/inactive/cross-Generation behavior, descriptor
aliases, body/Generation/correspondence/candidate/source/peer/slug/family/authorization
drift, pending classification rejection, review-only rejection, atomic 31-row create,
no-op immutability, second-receipt failure rollback, concurrent equal/distinct bodies,
receipt fidelity, later shared-body correction and frozen v3/2.1.0 regressions.
Synthetic sources make test classifications explicit; they do not approve actual
provisional research. Earlier RA-048 871-test results remain historical evidence.

An integration test initially found a misplaced Manifest3 writer dispatch; it was
corrected before the final successful targeted/full runs. No failed check remains.

## Preservation and remaining operational prerequisites

Operational SHA-256 before and after:
`be3b1cfe8f03feda457f2aa7ef397b96f2cd673971aaf6a999c171c5523b32a6`.
The database was not migrated, opened for writes or used for executable imports.
No canonical Wrangler/body/receipt rows changed. Existing RA-048 model/migration,
Candidate v3 wire/semantic hash code, A–H fixtures, legacy 2.1.0 artifacts and the
355-row historical assignment inventory remain byte-identical to the task baseline.
The index is empty and HEAD remains 29ff1b4; no stage, commit or push.

Unrelated shared-document hunks, database modification, MY2023/MY2024 directories,
research, scratch and run_readonly_plans.py are preserved. New implementation files
are left untracked for review; modified shared documents retain unrelated content.

Before MY2024 publication, separately authorize/apply migration 0011 and populate or
reuse the two reviewed operational body parents; prepare the complete real v3 release
with supported retained bytes, applicable original powertrain findings and published
exact Generation correspondences; verify all runtime dependencies/readers; obtain
actual affirmative approval for the exact production Matrix after fresh planning.
The code/test results do not establish those prerequisites or authorize their writes.

Historical FK assignments remain a separate owner-authorized operation: 260 reviewed
MY2019–MY2023 proposals, 15 unresolved MY2018 joins, 80 JK rows outside scope. No new
classification review is required merely to restate established doors. FactorySeries,
ExistingBody execution and binding tables remain unsupported/deferred. No actual
architectural blocker or new owner design decision was encountered. Stop here for
implementation review; no operational follow-up has begun.


## Final source review — 2026-11-13

The [final review](FINAL_REVIEW.md) records actual source-level findings and narrow
corrections, including ordered execution inputs, strict native source projection,
known body discrimination without mandatory blank fields, supported original Generation
review/restriction integration, one Generation chain across the complete family,
nested proof/receipt consistency, receipt scalar/outcome mirrors and explicit invalid
v3 dispatch rejection. No schema, model, migration, pure Candidate wire/hash or fixture
change. Implementation acceptance is now explicitly authorized and recorded; operational
deployment/publication remain separate.

Unknown legacy receipt body annotations are no longer promoted through Engine Proof
2.0. Material legacy overlaps without a recognized body-aware original receipt reader
return an explicit dependency assessment. This is not a new classification review:
unrelated nulls remain neutral and evidenced v3-backed null-FK no-ops still preserve
their null. The supported Generation review 1.0 decoder now loads original bytes,
checks the applied published payload/coverage/selector/locator and pins its snapshot.
It cannot approve body or powertrain interpretations; unknown versions and old
candidate-bound approvals remain rejected. Source/source-reader dependencies remain
distinct, as detailed in the final review support matrix.

Fresh final verification passes: **86 focused tests in 46.501 seconds, 362 targeted
regressions in 52.113 seconds, and 957 full-suite tests in 90.054 seconds**, no failures,
errors or skips. System, migration-drift and whitespace checks pass. The 59/335/930
results above are historical, not these runs. Twenty-seven additional regressions
cover actual reproduced defects, unchanged authority boundaries and real commit timing.
The [final review](FINAL_REVIEW.md) contains the reader-support matrix, preservation
checks and exact 21-path proposed acceptance inventory with RA-049-only shared hunks.
Owner acceptance and one local acceptance commit are now authorized. No push or
operational work is authorized. Earlier no-staging/no-commit statements describe
historical implementation/review checkpoints.


## Formal owner acceptance and local commit — 2026-11-13

The Project Owner accepts the exact implementation, including final corrections and
27 regressions, and authorizes only the 21-path FINAL_REVIEW inventory and milestone-only
shared-document hunks for one local commit. Approval1 remains a trusted-caller
confirmation boundary, not cryptographic actor authentication. Fresh acceptance
verification is recorded below before committing; the prior review results above
remain historical evidence. No operational migration, body creation, historical
assignment, publication or push is authorized.


Fresh acceptance verification: **86 focused tests passed in 44.699 seconds; 362 targeted tests in 50.513 seconds; 957 full-suite tests in 88.227 seconds**, with zero failures/errors/skips. System checks, migration drift and staged whitespace passed. All tests used isolated databases; reviewed executable bytes and historical artifacts remained unchanged.

Exact staged inventory and shared-only hunks are verified before the authorized local
commit. No operational data is included; no push is authorized.
