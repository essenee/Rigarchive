# RA-055 — MY2024 Wrangler JL complete-family planning

Created: 2026-11-14
Status: Proposed

**31/31 valid Candidate 3.1.0 envelopes; 31/31 valid read-only Plan 3.1.0 artifacts.
Actions: 31 create, zero no-op, zero blocked. No remaining evidence or identity
blocker was detected. Execution still requires exact human authorization.**

## Root cause and implementation corrections

The legacy CSV reader compared a shared model-code-family heading to an individual
trim/QOP heading. Those are different scopes. The exact shared selector documents
were already published under RA-053, with retained source hashes and applicability.

Two directly related corrections were made, without changing retained evidence:

1. Registry 3.1.0 now validates shared CSV documents by exact equality with an applied
   published Generation revision's evidence. It also checks the source ID, actual
   retained offering row, model code, trim, door style, engine code and QOP membership.
   Shared family headings are not compared to individual trim/QOP headings. Changed
   or unrecognized shared headings fail exact published-document membership and are
   still rejected; individual headings retain exact trim/model-code/QOP checks.
2. The same bounded projection path handles the existing factory-reconciliation CSV
   for JL24-18 and JL24-27. The previous reader handled only the inventory CSV even
   though those two approved factory-only offerings retain a distinct guide source.
   The factory rows must match the reviewed inventory's exact identity and full QOP
   set; individual assertions and source identifiers remain checked. No guide source
   was relabeled as Edmunds, and no unsupported claim was accepted by a catch-all.

`read_retained` still verifies the document hash before this path runs. Published
revision hashes/parent state are independently verified during resolution. Unknown
source paths and claims still fail. No heading checks were disabled or made fuzzy.

Changed application/test files in this task:

- `reference/ingestion/importing/body_identity.py`: one projection hook; its default
  returns false, preserving historical 3.0.0 reader behavior.
- `reference/ingestion/importing/registry_body_import.py`: the bounded MY2024 CSV
  projection implementation. All existing RA-054 corrections remain intact.
- `reference/tests/test_registry_body_import.py`: regressions covering all 31 current
  offering/shared projections, both factory-only offerings, unchanged 3.0.0 dispatch,
  and rejection of wrong headings, sources, model codes, trim, QOPs and engine codes.

No contracts, schema, serializers, source bytes, classifications or candidate values
changed. Engine Registry authority, published Generation assignments, body semantics,
slug generation, human authorization, stale-plan checks and atomic execution remain
unchanged. No additional unrelated defects required correction.

## Actual complete-family result

Reused the exact 31 regenerated RA-054 Candidate 3.1.0 envelopes at
`../RA054_wrangler_jl_my2024_ingestion_unblock/data/candidates/` without rewriting them.
All still serialize/parse successfully. Original Candidate 2.1.0 lineage and source
hashes are unchanged. The complete-family production workflow, not an alternate
importer, resolved the published correspondences, existing Engines and exact
Generation-32 two-/four-door body parents for every candidate.

Every call to `plan_candidate_import` used `RegistryRelease` with all 31 retained
locations. All source projections and downstream evidence checks passed. Every plan
passed the existing Plan 3.1.0 validator, including nested Plan/Proof3 checks. All
plans share the same complete verified 31-member family. Canonical peer and active/
inactive slug-occupancy checks found no blocking collision. No canonical UUIDs were
allocated during planning.

**Production slug verification passed:** 31 unique slugs within the 180-character
limit, and all ten exact two-door/four-door vectors in RA-049 §12 matched. The
established readable naming algorithm was not changed.

Ready for exact publication authorization: **31**. Genuinely blocked: **0**.
These plans are not a Matrix, Manifest, Approval1 or permission to execute.

## Focused verification

One consolidated isolated test run: **128 passed in 30.803 seconds**:
`test_registry_body_import`, `test_body_import_final_review`,
`test_candidate_v3_wire`, and `test_body_import_contracts`.
This includes the pre-existing RA-054 regressions, registry/atomic/stale-state
regressions, unchanged historical 3.0.0/wire behavior, all-31/two-body slug cases,
and new strict source-projection mismatch cases. No full Django suite was run.

New operational checks: 31 candidate contracts, 31 parent resolutions, 31 complete-
family planning calls/plan validations, and ten exact slug-vector comparisons.
`manage.py check` passed; `makemigrations --check` reported no changes; Git whitespace
checks passed. Tests used isolated resources via `RIGARCHIVE_TEST_DB_PATH` and the
previously authorized `.venv/bin/python` fallback; `venv/py313/bin/python` is absent.

## Artifacts

- [data/readiness.csv](data/readiness.csv): the exact 31-row planning inventory,
  actions, target slugs, Plan3.1 hashes, baseline digests, original candidate/source
  pins, trim/door/engine and transmission/QOP distinctions.
- [data/planning_results.json](data/planning_results.json): 31 full validated plans,
  including complete-family proofs, evidence pins, parent and peer/slug snapshots.
- [data/slug_verification.json](data/slug_verification.json): 31 slugs, exact pair
  verification, common-family and action counts.
- [data/parent_resolutions.json](data/parent_resolutions.json): Generation, Engine and
  exact body snapshots for all 31 offerings.
- [data/summary.json](data/summary.json): planning and preservation counts/hashes.

## Preservation and next step

Operational DB SHA-256 before and after is identical:
`46aafa64d6b34f880a441a000675becedb890ff6a225a745208dd00bcb75e5ef`.
All database table row fingerprints match. Counts remain **1,053 VehicleDefinitions,
254 correspondence revisions, 3,362 receipts, seven Engines and two bodies**.
Historical Engine/body FKs remain null; zero MY2024 JL canonical records. SQLite
integrity is `ok`; foreign-key violations are zero. Planning used `mode=ro` and
`PRAGMA query_only=ON`; no operational writes occurred.

HEAD remains `a99187227e862a5c97fcdb12491a5bac2e2f1ffb`. Unrelated work, RA-054's
uncommitted implementation and all prior candidate/evidence artifacts were preserved.
No staging, commit, push, correspondence publication, Matrix/Approval1 creation,
canonical import or historical assignment occurred.

**Smallest next step:** owner review/acceptance of the RA-054/055 corrections, then
prepare the exact 31-plan Matrix through the existing 3.1.0 workflow for explicit
human approval. Execution must independently revalidate the approved plans and
current state; material drift requires fresh planning/approval. No new configuration,
Engine, drivetrain or architecture review is needed.
