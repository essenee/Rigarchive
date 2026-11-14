# RA-045 phase one — pure identity foundations

Created: 2026-11-13
Status: Completed within bounded scope; full Candidate v3 contract portion stopped

The Project Owner accepted [ADR-0013](../../../architecture/ADR/ADR-0013-Unified-Factory-Body-Identity.md)
and approved [RA-045](../../../architecture/designs/RA-045-Unified-Factory-Body-Identity-Architecture.md).
Architecture-only commit: `b98f078` (`Accept ADR-0013 unified factory body identity architecture`).
Narrow amendment notes were appended to ADR-0010, ADR-0011 and ADR-0012, preserving
their historical decision text. Acceptance-only governance additions were staged
separately from pre-existing CURRENT_STATE/CHANGELOG work. Nothing was pushed.

## Implemented

- `reference/body_identity.py`: seven explicit nullable dimensions; canonical scoped
  token validation and caller-supplied reviewed aliases; namespaced identity-bearing
  body codes; nonempty sparse `factory-body-semantic/2`; exact
  `vehicle-definition-body/2` with complete existing five-field powertrain and optional
  body/series digests; deterministic canonical UTF-8 JSON/SHA-256.
- Pair comparison returns equal, compatible, distinct or same-configuration conflict.
  Whole-set observation resolution reports actual ambiguity without first-match or
  transitive compatibility merging. A unique compatible result does not prove semantic
  equality, source equivalence, applicability or authorization to bind a parent.
- `reference/ingestion/candidate/v3_foundations.py`: explicit 3.0.0 dispatch for a
  closed optional identity-field projection; validation, canonical serialization,
  duplicate-key/nonfinite JSON rejection, projection checksum and existing retained
  document-qualified lineage validation without byte or database access.
- `reference/tests/test_body_identity.py` and two bounded read-only fixtures:
  `my2024_body_identity_projection.json` retains 31 provisional inventory rows and
  source-file hashes; `historical_jl24_candidate_2_1_0.json` is a byte-identical copy
  of retained `JL24-01.provisional-r1.candidate.2.1.0.json`, SHA-256
  `2f341d71c8cc7aee323ad5fadedbdf6422b409c87f06f068986f6f15716d7c6a`.

These pure functions consume reviewed scope/designation inputs; they do not perform
source review, publish registry keys, decide whether an equipment option is structural,
approve powertrain classifications, create parents, or change canonical rows. Empty
fields are omitted; an empty parent is rejected while the no-body path remains valid.
New supported identity-bearing facts do not mutate an existing frozen preimage.

## Explicit contract boundary and remaining decisions

RA-045 §7 reserves Candidate 3.0.0 but expressly leaves exact wire schemas and fixtures
for later approval. The following portions were stopped rather than invented:

1. Full v3 envelope/required fields and schema identifier, recursive closed shapes,
   whole-candidate canonical serialization/hash and validation dispatch.
2. Exact existing-parent versus pending-parent body/series payloads, qualified
   assertion/interpretation references, immutable binding revisions and applicability
   fields. Non-null parent projections raise `UnresolvedV3Contract`.
3. Exact relationship between semantic projection, qualified raw support and human
   findings, including series/trim separation and historical evidence reuse in v3.

The implemented projection checksum is **not a Candidate artifact hash**. Projection
validation is not evidence support or import eligibility. The separate qualified-lineage
primitive checks document references only; it cannot certify that raw assertions support
a designation or five-field classification. No complete v3 payload is admitted to
existing deserialization, adjudication, planning, Matrix or import execution. Existing
Candidate 1/2/2.1 and historical /1 preimages retain their original meanings.

Next bounded phase should specify/approve these wire details, then complete the pure
full-contract and evidence fixtures. Persistence models/migrations, body-parent lifecycle,
proof/resolution/manifest/Matrix/receipt integration, slug generation, UI integration
and MY2024 artifact regeneration remain later separately authorized phases.

## Verification

Used the existing authorized `.venv/bin/python` (Python 3.13.1, Django 6.0.7), because
`venv/py313/bin/python` is absent. No environment or dependency changes.

Commands used `RIGARCHIVE_TEST_DB_PATH=/private/tmp/rigarchive-body-foundations-isolated.sqlite3`
for tests; checks used a separate `/private/tmp/rigarchive-body-foundations-check.sqlite3`.
The Django runner created/destroyed its isolated test database. Pure tests use
`SimpleTestCase`, which disallows database queries.

| Verification | Final result |
| --- | --- |
| `manage.py test reference.tests.test_body_identity` | 35 passed |
| Targeted existing tests: `test_structured_powertrain`, `test_ingestion_serialization`, `test_candidate_construction`, `test_engine_distinction`, `test_classification_adjudication` | 98 passed |
| `manage.py check` | No issues |
| `manage.py makemigrations --check --dry-run` | No changes detected; no migration created/applied |
| MY2024 fixture projection | 31 active: 10 two-door / 21 four-door; 21 keys without doors; 31 with doors; 10 old collision pairs |
| Candidate 2.1.0 pinned fixture | Exact bytes/hash and serialization round-trip preserved; legacy reader rejects schema 3.0.0 |
| Documentation and preservation checks | Local links/fences/JSON and Git whitespace checks pass; all 6,138 baseline files accounted for; only seven authorized architecture/governance files changed; index empty |

One intermediate test expected Django's ValidationError from a legacy reader; that
reader correctly raises its established IngestionValidationError. The assertion was
corrected to expect that existing exception; application behavior was not changed.
The final combined run passed all 133 tests in 2.933 seconds. Final runs have zero
failures. No full Django suite was run. No total processing-time or token savings
claim is made.

## Preservation and authorization

The fresh task baseline fingerprints 6,138 existing files. Only the seven authorized
architecture/governance files were changed from that baseline; implementation files
and test fixtures are new. All prior handoffs, candidate artifacts, receipt and
correspondence data, persisted slugs and the operational database are preserved.
Pre-existing CURRENT_STATE/CHANGELOG changes remain in the working tree and were
excluded from the documentation commit. Database SHA-256 at task start/end:
`be3b1cfe8f03feda457f2aa7ef397b96f2cd673971aaf6a999c171c5523b32a6`.

No operational migrations, body/series creation, canonical writes, historical
backfills, candidate regeneration, approvals, correspondence publication, canonical
imports or UI/importer integration occurred. Implementation and its completion
documentation remain unstaged/uncommitted. Stop at this phase boundary.
