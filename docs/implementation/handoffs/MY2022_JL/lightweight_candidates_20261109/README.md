# MY2022 JL — lightweight provisional candidates

Created: 2026-11-09
Status: Proposed
Construction completed: 2026-11-09

**Constructed and validated 55 provisional Candidate 2.1.0 artifacts: 15 two-door
and 40 four-door. All are incomplete and blocked; none is import-eligible.** The
single Sport RHD offering remains excluded and preserved separately.

This checkpoint implements the owner-authorized construction experiment, not
classification approval, correspondence publication, Matrix certification or import.
See the [workflow decision/comparison](../WORKFLOW_EXPERIMENT_20261109.md).

## Results

| Check/result | Actual count |
| --- | ---: |
| Schema-valid candidates / deterministic references | 55 / 55 |
| Complete five-field identities | 0 |
| Incomplete five-field identities | 55 |
| Blocked / eligible | 55 / 0 |
| Engine Proof 2.0 artifacts supported/created | 0 |
| Consumer Edmunds same-name / equivalent-name mappings | 44 / 11 |
| Original full comparison, including deferred RHD | 45 / 11 = 56 |
| Deferred RHD candidates constructed | 0 |
| Manufacturer-supported transmission/QOP review items | 8 |
| Unresolved field instances / engine-field review groups | 112 / 12 |
| Confirmed duplicate complete identities | 0 (no complete tuples available) |
| Uncertain ERC/eTorque peer pairs | 13 |
| Missing applicable source/model generation keys | 72 |

Complete/incomplete partition the 55 candidates. Blocked overlaps that partition;
it is not an additional set. Candidate references retain the discovery IDs
`JL22-01`–`JL22-56`, with the RHD ID omitted; no renumbering or random IDs.

All six families remain: **EC1 14, ERC 13, ERG 15, EXJ 9, ECX 3, ESG 1**.
Unsupported fields remain null: **29 aspiration, 46 fuel, 37 electrification**.
The three ECX research counterparts describe gasoline/electric PHEVs, but their
retained Edmunds evidence is a local research transcription and the unchanged
literal support predicate does not accept that wording as a directly qualified
`gasoline` assertion. Consequently ECX fuel remains null here too. No inference
was relabeled as a manufacturer claim, and no predicate/schema was changed.

Read-only evaluation through the actual existing planner returns
`requires_review / generation_correspondence` for all 55. Generation PK 32 and
UUID `38d3c3ac-f825-4406-abb5-c2d12b9129a4` exist and remain the intended target;
no MY2022 source binding is published. This first planner gate masks the later
powertrain gate, so completeness is checked independently. The MY2022 Generation
32 namespace contains zero canonical rows; totals remain 934 definitions,
3,148 receipts and 159 correspondence revisions. No executable manifest was emitted.

## Lineage and implementation choices

Reused the 56-row discovery and 56-row Edmunds CSV without PDF reconstruction,
new acquisition or historical revision research. Each candidate binds original
manufacturer PDF hashes, model codes, exact positive QOP/engine/transmission
observations, guide revisions/pages, the immutable discovery row and the exact
Edmunds comparison row/style ID. All eight uncorroborated automatic/QOP alternatives
remain in the candidate lineage and review register; none creates a separate row.

The existing builder, serializers, qualified-evidence validators, five-field
predicate, generation resolver and read-only planner are unchanged. 128 ordinary
SourceAssertionSet 1.1.0 files reuse 72 guide/model sections, one retained technical
layout section and 55 explicitly labeled Edmunds research-row transcriptions.
The original research CSV is the raw local artifact for those transcriptions,
not falsely claimed original Edmunds HTML. No five-field value is projected from
that derivative source. Manufacturer technical p1 explicitly establishes
four-wheel drive; only that already-retained section is mapped to `4WD`.

Body-aware names follow established Wrangler conventions. The Altitude model
sections and separate 4xe model are preserved rather than merged. High Tide's
candidate name is provisional; the High Tide/Jeep Beach grade-versus-equipment
finding remains for owner review. No Jeep Beach or RHD candidate was added.
Factory package pages remain raw retained references, not an optional-equipment
catalogue or compatibility evaluator.

Thirteen same-trim ERC/eTorque pairs share displacement/cylinders but have missing
classifications that prevent an established unequal tuple. They are neither merged
nor certified distinct merely because their engine codes differ. No engine proof
is emitted with invented values or an unverified empty peer list.

## Files

- `candidate_inventory.json` / `.csv`, `candidates/`: 55 hashes, stable IDs, mappings, fields and artifacts.
- `assertion_sets/`: existing SourceAssertionSet 1.1.0 envelopes with exact raw/local provenance.
- `offering_correspondence_inventory.json`, `deferred_RHD.json`: full 56-row reconciliation and exclusion.
- `unresolved_classification_register.json`, `next_owner_decisions.json`: 112 null instances grouped into 12 review topics.
- `transmission_QOP_review_items.json`: eight supported alternatives and exact positive observations.
- `engine_proof_assessment.json`, `engine_proofs_index.json`: 55 explicit proof rejections and zero fabricated proofs.
- `duplicate_identity_review.json`, `generation_readiness.json`: uncertain pairs and missing source bindings.
- `eligibility_assessment.json`, `eligibility_summary.json`: actual planner outcomes and separate completeness findings.
- `build_candidates.py`, `validate_candidates.py`: bounded handoff drivers using current contracts; no production framework.
- `authorization.json`, `preservation_baseline.json`, `processing_measurements.json`, logs, `validation_results.json`, `artifact_hashes.json`: authority, preservation, measurements and verification.

## Verification and measured overhead

Construction and independent same-input rebuild produce identical candidate bytes.
A separate validation pass checks all 55 schemas, round trips, semantic/file hashes,
qualified source bytes, manufacturer-to-Edmunds correspondence, 128 assertion sets,
null preservation, RHD exclusion, eight review items and exact generation evidence.
It rejects two unsupported null-fill controls and a changed generation projection;
all 55 incomplete engine-proof attempts fail closed. The repeated planner assessment
agrees for every row. SQLite guards reject writable/non-target connections;
validation observes one `mode=ro` connection with `PRAGMA query_only=1`, and zero
construction-phase connections. Prior evidence, application ingestion contracts,
governance, database and SQLite sidecar inventory remain unchanged.

Commands: `.venv/bin/python -B .../build_candidates.py` (initial and deterministic
repeat), then `.venv/bin/python -B .../validate_candidates.py`. Actual environment:
owner-authorized Python 3.13.1 / Django 6.0.7 / pypdf 6.16.1. No full Django suite
was run because no application code/regression changed. System and migration dry-run
checks passed (`system_check.txt`, `migration_check.txt`). No migrations were applied.

Measured initial script phases: **1.257802 s** construction/rebuild/contract checking,
**0.143702 s** read-only planning, **1.875675 s** instrumented script elapsed.
Candidate files total **8,111,439 bytes**, assertion sets **824,644 bytes**.
Independent validation measured **0.891836 s**. Initial connection-counter coverage
was corrected to intercept Django's `sqlite3.dbapi2.connect` as well as
`sqlite3.connect`; the initial database URI already enforced read-only access.
The independent guard validation confirms one read-only connection. These timings
exclude model processing, research, documentation and total chat wall time; no
quantitative time/token savings are claimed.

## Next owner decisions and stop boundary

Review the 12 grouped classification findings (candidate-bound application still
required), particularly aspiration/nonhybrid conclusions and gasoline terminology.
Confirm the provisional High Tide/Jeep Beach identity treatment. Then review the
72 MY2022 source/model generation bindings to existing Generation 32 and separately
authorize publication. RHD can remain deferred; the eight transmission gaps do not
need to be resolved by inventing or discarding baseline candidates.

No architectural decision, schema change or deviation from the authorized scope.
Workflow documentation updated: CURRENT_STATE, CHANGELOG, the existing ingestion
protocol and the MY2022 workflow experiment record. MY2019–MY2021 procedures,
Handbook, Blueprint and accepted ADRs were not changed. Existing working-tree work
was preserved. No operational writes, correspondence publication, Matrix certification,
canonical imports, commits or pushes. Stop here; further work requires owner direction.
