# Wrangler JL body-aware import follow-up proposal

Created: 2026-11-13
Last Updated: 2026-11-13
Status: Proposed

This is a separately reviewable proposal, not implementation approval or an import
plan. No slug, contract, source, canonical record or operational schema is changed.

## Finding and choice

Recommend **B: an explicit body-qualified Candidate v3 canonical identity path**,
including readable new-record slug generation within that path. A global slug-only
extension (A) cannot prevent semantic merging. No smaller supported path (C) exists:
manually supplying distinct slugs bypasses neither peer equality nor proof/authorization.

`VehicleDefinition.build_slug()` uses year, trim, engine label, drive and market;
`reference/powertrain.py:qualified_slug` adds engine aspiration/fuel/electrification
qualifiers. Neither uses the new body FK. The database's only vehicle locator uniqueness
is Generation/slug; it has no body-qualified vehicle identity constraint. For otherwise
identical Sport variants the common proposed slug is
`2024-sport-20l-i4-turbo-4wd-us-turbo`.

Fresh read-only/in-memory reproduction using all 31 active MY2024 rows, the retained
engine labels, owner-required trims and proposed engine tuples yielded **21 unique
slugs and ten collision pairs**: JL24-01/11, 02/12, 03/13, 04/14, 05/15, 06/16,
07/19, 08/20, 09/21 and 10/22. These are diagnostic proposed classifications, not
approved executable candidates. There are zero operational MY2024 JL records.

The semantic problem is independent of the locator: `powertrain_identity.peers_for`,
`identity_proof`, `plan_structured_identity` and `revalidate_identity` compare the
same trim/drive namespace and five engine fields without body. A two-door peer can
therefore appear equal to a four-door proposal even after a slug-only suffix. The
planner's `_fields_match_exact` and execution concurrent-insert matching likewise
lack body meaning. The current legacy planner only supports v1/v2, and legacy
serialization explicitly rejects v3. The RA-047 pure v3 reader is not a live importer.

## Smallest proposed implementation boundary

Limit the successor path to reviewed MY2024 JL consumer offerings, null FactorySeries,
the existing seven-dimension representation and the existing five-field powertrain.
Use the existing v3 reader, body/2 and baseline/2 primitives; do not change their wire
format or fabricate binding revisions. Resolve Generation through existing reviewed
correspondences and attributable source scope, not names/PK alone or a new registry.
Resolve exact supported body tuples in that Generation; sparse compatibility never
proves equality. No new models, FKs, approval systems or review rounds are proposed.

A body-aware plan must pin candidate hash, qualified reviewed evidence, resolved body
UUID/complete tuple, Generation, whole relevant peer set, proposed canonical fields
and complete slug family. Recheck the same state inside execution; changed shared body
attributes, peers, source support, authorization or slug occupancy stale the plan.
A null historical FK is neutral missingness, not proof of equality/difference. Actual
ambiguous overlap blocks a create rather than silently merging or automatically
requiring backfill. Reuse existing evidence for doors; resolve only material ambiguity.

Keep Sport as trim. Propose readable `-2-door` / `-4-door` qualifiers after the existing
structured base for the paired Sport family, e.g.
`2024-sport-20l-i4-turbo-4wd-us-turbo-2-door` and its `-4-door` counterpart.
Select qualifiers/order over the reviewed family, independent of import order; do not
add a suffix to every single-body vehicle. Preserve the 180-character limit and reject
unresolved collisions; no truncation/random repair. The full baseline, not slug text,
controls equivalence. Existing nonempty slugs are never regenerated, including after
an authorized body FK assignment. Manufacturer Unlimited labels remain evidence.

Keep legacy Candidate 2.1.0 dispatch, engine proofs, plans, matrices, receipts and old
imports frozen. Body meaning must not be smuggled into their metadata or shared
comparison functions. Version-dispatch new planning, proof, authorization and execution
rather than changing old closed schemas. Concurrent body-distinct creates must succeed;
concurrent exact duplicates must not. Retain atomic create-only VD/receipt execution,
exact human authorization and rollback. Any body-parent writes require explicit scope.
Existing Wrangler assignment corrections remain a separately authorized data operation.

## Contract decision needed before successor implementation

RA-046 §§5/5.1 and its approved decision 2 require immutable binding evidence for
ExistingBody and exact pending-parent reuse. RA-048 intentionally permits editable
body rows and supplies no binding-revision store. PendingBody is not a bypass: it
means unbound and still requires live evidence resolution. This is an explicitly
deferred downstream capability, not a defect in the approved minimal storage layer.

The next task should specify the minimal body-aware plan/proof/manifest/receipt
contract and readable-slug algorithm for owner review before implementation. Proposed
direction: pin exact body row state and reviewed source lineage in existing versioned
plan/receipt JSON with stale checks, without new binding tables or FKs. Whether that
satisfies the intended runtime binding boundary requires explicit architectural approval
and, if necessary, a narrowly authorized clarification of governing downstream
requirements. It must not be declared equivalent to an RA-046 immutable binding or
encoded as an invented wire revision UUID/hash. Do not silently edit RA-046 or an ADR.

The exact downstream proof and authorization schemas are not already approved by
RA-046. Specify their versioned shapes before coding. This decision can reuse accepted
door evidence; it does not create a second Wrangler classification review round.

## Proposed affected files and tests

| Path | Proposed responsibility |
| --- | --- |
| reference/ingestion/importing/body_identity.py (new, proposed) | Read-only exact body resolution, whole-set identity/peer snapshot and deterministic slug-family helper; reuse pure primitives |
| reference/ingestion/importing/planner.py; importing/__init__.py | Explicit v3 dispatch and body-qualified plan/create basis; preserve old branches |
| reference/ingestion/importing/importer.py; importing/workflow.py | Independently revalidate body/peer/slug state and exact authority; atomic create/receipt |
| reference/ingestion/importing/matrix_workflow.py | Version-dispatched model-year execution |
| reference/ingestion/manifest.py; matrix.py; matrix_approval.py | Separately approved successor closed shapes and exact body-qualified authorization |
| reference/models.py | Only if a new-record helper delegation is needed; keep legacy build_slug/nonempty slugs unchanged |
| reference/tests/test_body_aware_import.py (new, proposed) and existing import/manifest/matrix regressions | New path and preservation coverage |
| MY2024 handoff artifacts | Regenerated v3 candidates/plans only after downstream contract approval; preserve old artifacts as history |

No changes proposed to pure candidate_v3.py, candidate_v3_evidence.py, body_identity.py,
Candidate 2.1.0 schemas, existing fixtures, old migrations or accepted governance.
Existing powertrain_identity.py remains the legacy path; successor code reuses its
pure engine vocabulary without silently broadening proof 2.0.

Acceptance tests must cover both Sport doors and all ten collision pairs, same-body
repeat/no-op, cross-Generation rejection, sparse ambiguity/null legacy overlap,
import-order independence, existing inactive slug occupancy, 180-character failures,
shared-body edit stale plans, candidate/source/peer/approval drift, concurrent equal
and distinct creates, atomic rollback/receipts, unchanged Unlimited provenance,
immutable historical slugs, v3 A–H bytes/hashes and historical 2.1.0 regressions.
No operational migration, candidate publication or canonical import belongs in the
contract-specification task.

## Assignment preparation already available

[wrangler_body_assignment_proposals.csv](wrangler_body_assignment_proposals.csv)
contains all 355 existing Wrangler records: 260 JL proposals supported by prior
MY2019–MY2023 review, 15 MY2018 JL rows without an exact evidence join established
here, and 80 JK rows explicitly outside this JL task. For the 260, only the body FK
would change after separate authorization; preserve PK/UUID/trim/slug/receipt bytes.
Create or reuse two Generation-32 sparse body tuples, with only door_configuration
populated. No UUID/PK is fabricated for those not-yet-created parents.

| Model year | Two-door proposals | Four-door proposals | Unresolved JL rows |
| --- | ---: | ---: | ---: |
| 2018 | 0 | 0 | 15 |
| 2019 | 6 | 13 | 0 |
| 2020 | 15 | 34 | 0 |
| 2021 | 23 | 50 | 0 |
| 2022 | 15 | 40 | 0 |
| 2023 | 18 | 46 | 0 |
| Total | 77 | 183 | 15 |

Each proposal records the live PK/UUID, current trim/slug, creation receipt, reviewed
inventory path/hash/row and qualified model-code assertions. Body count is taken
from the reviewed row, not inferred from code suffix or trim. MY2019 uses the retained
director-accepted historical inventory representation, not a newly verified PDF;
its provisional powertrain flags are not promoted. Some historical source trim labels
differ from current reviewed canonical trims; both spellings are retained in the CSV.
The 2018 limitation is an unresolved join, not a finding that existing door evidence
is absent or a demand for a new review round. Inspect retained evidence for exact
applicability before proposing those remaining assignments.
