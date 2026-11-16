# MY2021 snapshot archival and canonical revalidation — stopped for review

Created: 2026-11-16
Status: Archival verified; normal evaluation blocked; no cleanup authorized to proceed

## Outcome

Completed Stage A archival and row-level inspection. **73 EVALUATION_BLOCKED**;
zero exact/normalized normal-evaluation successes, zero eligible replacements.
All 73 current canonical identity tuples match the retained approved Matrix. This
is a static comparison of existing approved artifacts, **not** a new normal
Edmunds import evaluation and not retroactive authorization proof.

The required Stage B correction is not a narrowly isolated generation-overlap switch:

- `reference/ingestion/importing/planner.py:83–91` calls `assess_peer` even for
  structured exact-match checks. `powertrain_identity.py:149–171` and 174 onward
  use receipt-bound proofs for structured identity/no-op/create assessment.
- Accepted RA-044 independently specifies peer receipt/proof bindings, including
  nonidentity tuning/layout guards. These dependencies extend beyond exceptional
  ADR-0010 generation selection. Changing that sufficiency rule without a defined
  replacement would change the current identity-validation/approval policy.
- `reference/my2025_wrangler_import.py:55` and `reference/my2026_wrangler_import.py:101`
  are bounded previews pinned to approved year-specific inventories, registries,
  factory bodies and identity profiles. They are not a generic MY2021 evaluator.
- Retained `MY2021_JL/EDMUNDS_COMPARISON.md` explicitly describes manufacturer guides
  as primary and Edmunds as secondary corroboration. `edmunds_comparison.json`
  records `exact_structured_identity_confirmation: false`. No approved normal
  MY2021 Edmunds-profile matrix was located. Reusing the manufacturer-derived Matrix
  as though it had that different provenance would misstate its authority.

The current task makes ADR-0010 exceptional; this report accepts that direction and
does not construct a historical reconstruction reader or deploy an archive. It also
honors the explicit stop before a correction changes canonical identity semantics
or approval policy. No new evaluator, source interpretation, broad bypass or code
change was made to manufacture successful results.

## Baseline and archive

Selected by operation `vehicle_definition_import`, outcome `created`, target/current
MY2021, target/current Generation 32, canonical Jeep/Wrangler hierarchy and created
FK—not just IDs. Exactly PK **3076–3148**, 73 distinct targets. PK/UUID/slug mirrors
verified. Current identities: receipt 3094 Willys Sport; 3135 Unlimited Sahara VD936.

- Live DB size: **64,679,936 bytes** before and after.
- Live DB SHA-256: `sha256:b42fc13d6f3e24614e789a7d727e8ec1d179b1d5ee4749923b8b7439ba8fb899` (unchanged).
- Baseline: 1,150 VehicleDefinitions, ten Engines, 3,591 ImportExecutionReceipts,
  254 GenerationCorrespondenceRevisions, 16 Generations, six models, five manufacturers.
- SQLite integrity `ok`; zero FK violations. Verified consistent SQLite baseline copy
  matches **all 50 application tables** and passes integrity/FK checks.
- Original selected snapshot text: **32,170,852 bytes / 30.68 MiB**.
- ZIP: `backups/review/my2021_snapshot_archival_20261116T191303Z/original_snapshots.zip` — **2,690,523 bytes / 2.57 MiB**.
- Archive SHA-256: `sha256:7e59b872e589b18d36c3dff231963d9600422549dd19b9c052df7ee57d583b70`.
- Baseline copy: `backups/review/my2021_snapshot_archival_20261116T191303Z/baseline.sqlite3`.
- All **73** archived members match original SQL UTF-8 text byte-for-byte, raw hash,
  canonical hash, length and deterministic PK/UUID mapping. No original was removed.
- `archive_manifest.json` is the non-sensitive audit index. Complete selected receipt
  rows and working-file baseline are retained locally beside the ZIP, outside Git.
- Restore procedure: `RESTORE.md`. Archive/backup are ignored by Git and must remain
  outside deployment; no production reconstruction dependency is proposed.

The backup's physical SHA differs from the live DB because SQLite backup layout/header
bytes need not match; logical table content and SQLite integrity were verified.

## Per-record results and provenance

`revalidation_results.json` contains all 73 individual records: receipt PK,
VehicleDefinition PK/UUID/slug, Matrix row/digest, candidate hash, revision/time,
field-by-field retained-Matrix comparison, current registry/body FKs, artifact paths
and byte hashes, Edmunds secondary URL, normalization (none), and exact blockers.
All rows have `evaluator_invoked: false`. No normal outcome or target selection is
claimed from a static comparison. No additional or replacement VD was proposed.
A future evaluator must independently demonstrate same-record no-op semantics.

All 73 retained candidate hashes, execution-manifest identities and actual Matrix
approval are available. Matrix approval and all 73 execution manifest hashes were
validated using existing contract functions. Existing final approved Matrix digest:
`sha256:6926df6c06e4bd471bbda02c67257cf7a7e2999cf5cdfebfc8b06ead31a9996e`.
Current code revision: `a28a50815b331039c74840e72a528ab00e5c974b`.

## The 88 historical references

`proof_reference_classification.json` pins every source receipt, target receipt,
JSON pointer and original digest. All 88 digests match the archived original logical
snapshots. All edges are ordinary MY2021 JL, not 2018 JK/JL exceptional overlap.

Classification: **88 dependencies required by another independently authorized
workflow (the accepted RA-044 structured identity/Matrix verification path)**;
**zero legitimate generation-overlap dependencies**. Their overlap-adapter role is
obsolete under the new owner direction, but their live structured-identity role
cannot safely be retired yet. They are therefore blockers, not evidence that the
owner must retain ADR-0010 as the ordinary import architecture. No historical hashes
were rewritten. Existing offline material preserves them for historical audit.

## Compact record preparation

Inspected actual MY2026 receipt 3456 and `my2026_wrangler_import.execute` at line 239:
its compact registered-Engine/body profile is a different workflow. Reusing the
minimal separation between original metadata and new evaluation is appropriate;
pretending its existing year-specific contract evaluates MY2021 is not.

`compact_record_proposal.json` is a **blocked illustrative record**, not an approved
receipt version or a generated replacement. It separates original receipt identity,
outcome/candidate/manifest/Matrix references and archived original hash from a newly
timestamped revalidation result. Original execution timestamps/attribution remain
in existing columns. Successful later records would require the actual evaluator
version, same-existing-record result and full relevant field comparison. They must
not claim that a 2026 evaluation authorizes the original import retroactively.

No compact replacement for a successful evaluation was produced because there are
no eligible successes. Writing blocked review results over original creation snapshots
would not satisfy the task's acceptance criteria.

## Isolated experiment and storage

A consistent, integrity-checked baseline copy exists; **no cleanup transformation
or VACUUM was performed**, even on that copy, after the policy-review stop was reached.
All unresolved receipts remain unchanged. Before/after live DB size is identical;
actual reclaimed storage is **zero**. No fabricated compacted-size measurement is
reported. Original 30.68 MiB snapshot text and 2.57 MiB offline ZIP are measured;
possible future savings require actual successful compact records and a clone
experiment. Production storage/available quota was not inspected.

## Required owner decisions and next sequence

1. Approve the MY2021 normal evaluation input/profile: how retained Edmunds
   corroboration and approved manufacturer/adjudication evidence map to current
   registered Engines/body identities and the existing historical canonical identities.
   No new source fetch is needed or authorized here.
2. Specify whether exact canonical complete tuples plus authored registry mappings
   replace receipt-derived identity proof for ordinary imports, and define retained
   conflict, tuning/layout, duplicate, body and approval safeguards. This is the
   missing policy boundary; it is not just a file-access repair.
3. Authorize that bounded evaluator/correction with regressions, preserving the
   exceptional JK/JL overlap adapter. Then rerun all 73, isolating disagreements.
4. Only after successful rows and proof-retirement behavior are demonstrated, prepare
   real compact records and apply them to a separate copy; compare all tables/scalars,
   run ordinary and exceptional workflows, compact the disposable copy and measure.
5. Present exact eligible hashes/PKs, backup/restore and deployment plan for separate
   live cleanup approval. Do not deploy the historical archive or restore this old
   baseline over subsequent changes. Future ordinary writers still need a separately
   approved correction; this archival operation does not prevent oversized receipts.

Focused test results and final preservation verification are in `verification.json`.
No original DB writes, canonical edits, new/imported vehicles, source acquisition,
reconstruction infrastructure, staging, commit, push or deployment. Existing owner
working-tree changes are preserved. Stop for architectural/evaluation-scope review.
