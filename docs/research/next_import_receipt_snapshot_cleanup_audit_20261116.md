# Next import-receipt snapshot cleanup candidate

Created: 2026-11-16
Status: Read-only audit; recommendation only, no cleanup authorized or performed

## Executive recommendation

Select **US-market MY2022 Jeep Wrangler JL, Generation PK32 / UUID
38d3c3ac-f825-4406-abb5-c2d12b9129a4**, for the next **bounded preparation and isolated
simulation**. It has **55** successful canonical creation receipts, PK **3221–3275**,
containing **7,021,733 bytes / 6.70 MiB** of snapshot JSON—the largest remaining
model-year group. These represent ordinary MY2022 configurations, not a JK/JL overlap.
No receipt is yet approved for live replacement by this audit.

Its original document arrays occupy **6,516,504 original UTF-8 bytes / 6.21 MiB**.
That is measured removable *bulk payload opportunity*, not a promise of equal file
shrinkage or permission to discard evidence. New metadata, approvals, archive and
compatibility handling must be designed/tested before net savings can be measured.
Use MY2021 as the procedural precedent; do not broaden its hard-pinned profile.

## Current baseline and committed implementation

- Database: **32,571,392 bytes / 31.06 MiB**; SHA-256
  `sha256:e8c07d3da417736ca6e1ae9ae91bb3e830bd4ac4853fda1406ac24ae62e0f126`. Matches the completed MY2021 maintenance result.
- **3,591 receipts**; total actual stored snapshot text **24,493,284 UTF-8 bytes /
  23.36 MiB**. Measured from the SQL JSON text encoded to UTF-8,
  not Python object estimates or character counts.
- Read-only SQLite integrity `ok`; zero foreign-key violations; 4,096-byte pages,
  zero free pages. The receipt table occupies **28,536,832 bytes / 27.21 MiB** including
  row/overflow storage; its indexes are additional. Correspondence table 2,199,552
  bytes, VehicleDefinition table 233,472 bytes. Physical pages differ from JSON bytes.
- All **73** MY2021 compact records remain present and pass actual `validate_compact`
  against their approved Matrix and unchanged canonical records.
- Current committed HEAD **`fc5a28e2bf93080b1e5eb7a897a8124b39f603af`**,
  `Revalidate MY2021 JL imports and compact receipt evidence`. The committed service
  bytes equal working implementation; it supports exactly
  `my2021-approved-matrix-revalidation/1`. No PYTHONPATH/environment workaround.
- Working tree clean at audit start. No code, DB, staging or deployment changes.

## Storage ranking

Grouped by manufacturer/model, explicit receipt target model year and canonical
Generation. Generation/model/manufacturer use resolved parent or preserved target FK,
with correspondence parent only for publication rows; do not assign publication
payloads arbitrarily to a year within their applicability range. JSON sizes below
include the entire stored snapshot, not only its evidence array. MiB = 1,048,576 bytes.
All twelve ranked groups are Jeep/Wrangler; the manufacturer/model totals below explain why.

| Rank | Manufacturer / model | MY / Generation (PK) | Receipts | JSON bytes / MiB | Average bytes | Largest bytes | Format | Large content |
|---|---|---|---:|---:|---:|---:|---|---|
| 1 | Jeep / Wrangler | 2022 / JL (32) | 55 | 7,021,733 / 6.6964 | 127,667.9 | 141,527 | G1.1 | Documents |
| 2 | Jeep / Wrangler | 2024 / JL (32) | 31 | 5,403,815 / 5.1535 | 174,316.6 | 174,649 | Body3.1 | Body plan/manifest |
| 3 | Jeep / Wrangler | 2020 / JL (32) | 49 | 3,442,863 / 3.2834 | 70,262.5 | 92,552 | G1.1 | Documents |
| 4 | Jeep / Wrangler | 2023 / JL (32) | 64 | 2,157,261 / 2.0573 | 33,707.2 | 37,347 | G1.1 | Documents |
| 5 | Jeep / Wrangler | 2018 / JK (31) | 6 | 1,596,224 / 1.5223 | 266,037.3 | 266,703 | G1.0 | Documents |
| 6 | Jeep / Wrangler | 2026 / JL (32) | 136 | 1,111,416 / 1.0599 | 8,172.2 | 8,957 | M26v1 (66), M26v2 (70) | Compact; no document corpus |
| 7 | Jeep / Wrangler | 2021 / JL (32) | 73 | 488,147 / 0.4655 | 6,686.9 | 7,294 | M21compact | Compact; no document corpus |
| 8 | Jeep / Wrangler | 2025 / JL (32) | 62 | 427,284 / 0.4075 | 6,891.7 | 6,989 | M25v1 | Compact; no document corpus |
| 9 | Jeep / Wrangler | 2019 / JL (32) | 19 | 380,998 / 0.3633 | 20,052.5 | 25,380 | G1.1 | Documents |
| 10 | Jeep / Wrangler | 2018 / JL (32) | 15 | 147,965 / 0.1411 | 9,864.3 | 44,302 | G1.0 | Documents |
| 11 | Jeep / Wrangler | 2007 / JK (31) | 8 | 30,915 / 0.0295 | 3,864.4 | 4,109 | G1.0 | Documents |
| 12 | Jeep / Wrangler | 2010 / JK (31) | 8 | 29,061 / 0.0277 | 3,632.6 | 3,651 | G1.0 | Documents |

G1.0/G1.1 mean `generation_resolution.resolution_version` 1.0/1.1;
Body3.1 means `body_import.receipt_version=3.1.0`.
M26v1 = `my2026-edmunds-registry/1`, M26v2 = `my2026-registry/2`;
M21compact = `my2021-approved-matrix-revalidation/1`;
M25v1 = `my2025-edmunds-registry/1`.

The ranking includes completed MY2021's remaining compact storage for completeness;
it is **not** a further cleanup candidate. All listed groups except MY2025/MY2026
are successful creation receipts. MY2025 has 31 creates +31 no-ops; MY2026 has
35 creates +101 no-ops. These audit attempts must not be deleted just because they
share canonical targets. MY2026 splits into 66 v1 receipts /527,308 bytes and 70 v2
receipts /584,108 bytes; average/largest are respectively 7,989.5/8,103 and
8,344.4/8,957 bytes. No large document corpus is embedded in these compact profiles.

**MY2024 needs separate handling:** all 31 are registered-Engine/body-aware 3.1.0
receipts, not old ordinary G1.1 imports. A representative compactly serialized body
snapshot contains a 138,074-byte plan and 23,696-byte manifest, including nested
review/baseline dependencies. Absence of the top-level `documents` array does not
mean absence of substantial embedded evidence. Do not apply MY2021 semantics to it.

**MY2018 JK and JL are genuinely overlapping:** current Generation ranges are
JK 2007–2018 and JL 2018 onward. Preserve their exceptional selection evidence;
they are excluded from the recommended ordinary cleanup. MY2022 only falls in JL.

### Available authority and source evidence for ranked groups

- **2022**: Authenticated Matrix/approval + exact candidates/manifests; sources verified.
- **2024**: Embedded approved body Matrix/manifest; source anchors verified; separate profile.
- **2020**: Execution Matrix/approval retained; sources verified; not fully authenticated here.
- **2023**: Execution Matrix/approval retained; sources verified; not fully authenticated here.
- **2026**: Pinned inventory/supplement retained; source anchors verified.
- **2021**: Committed compact profile; approved basis + all 73 records validated.
- **2025**: Pinned inventory retained; source anchor verified.
- **2019**: Execution Matrix/approval retained; sources verified; not fully authenticated here.
- **2018**: Exceptional overlap source evidence retained/verified; approval coverage not audited.
- **2007**: Source anchors verified; external Matrix approval not audited.
- **2010**: Source anchors verified; external Matrix approval not audited.

For all twelve groups, the inspected receipt document source references (or primary
source anchors for compact/body formats) exist and match their recorded byte hashes.
This is **not** an assertion of complete source dependency closure for every group.
Only MY2022 received the full candidate/execution Matrix assessment below. Body3.1
approval/Matrix data is embedded in the retained receipts; its separate release
approval/dependency closure was not authenticated in this nonselected audit.

### Manufacturer/model totals (including year-unspecified receipts)

| Manufacturer | Model | Receipts | Snapshot bytes | MiB |
|---|---|---:|---:|---:|
| Jeep | Wrangler | 838 | 24,487,778 | 23.3534 |
| Toyota | Tacoma | 2,165 | 4,330 | 0.0041 |
| Volkswagen | Touareg | 334 | 668 | 0.0006 |
| Toyota | 4Runner | 254 | 508 | 0.0005 |

There are **254 year-unspecified correspondence-publication receipts**, totalling
**2,039,648 bytes / 1.95 MiB**, outside the model-year ranking. Of those, 253
Generation-anchored publication records total 1,776,617 bytes; one without a selected
Generation totals 263,031 bytes. They retain review/publication history and must not
be silently included in ordinary model-year cleanup. Toyota/Volkswagen's listed
legacy snapshots are empty JSON (`{}`, two bytes each), not the remaining storage issue.

## MY2022 exact scope and redundancy

- **55** `vehicle_definition_import / created` receipts, PK **3221–3275**.
- **55 distinct canonical VehicleDefinitions**, PK **950–1004**, all MY2022 US JL.
  Current creation PK/UUID/slug mirrors match each target; all 55 are linked to
  authored Engines. Factory-body FK is null on all 55; cleanup must not infer or
  assign a body relationship absent from the historical identity contract.
- All receipt target fields match their approved Matrix row and current canonical
  fields (using decimal numeric equality for stored precision), with the exact
  row/candidate hash, candidate reference and slug bindings verified.
- Six approved powertrain families: EC1 14, ERC 13, ERG 15, EXJ 9, ECX 3, ESG 1.
  Preserve ERC nonhybrid versus ERG mild hybrid, EXJ diesel, ECX PHEV and ESG 392.
- Preserve distinct `Unlimited High Tide` (`JL22-20`, VD969) and its QOP/Jeep Beach
  provenance. Deferred Sport RHD `JL22-53` is **not** part of these 55.

All 55 snapshots have resolution 1.1. Their **55 document collections are unique**,
so deduplicating whole arrays is not the main opportunity. They contain **709
occurrences of 185 unique canonical document objects**. Canonical array bytes total
6,427,742, versus 823,116 unique document-object bytes. Original stored array text
is larger (6,516,504) due to serialization spacing. Repetition is at the individual
structured document/provenance level, not evidence that the entire receipt is a
meaningless duplicate. Candidate-specific approvals and peer state remain material.

Every array exactly matches an independently retained candidate's structured
`evidence_documents`; every full generation-resolution object exactly matches an
execution manifest plan. There is no uniquely receipt-only document collection
in this inspected scope. Original root Matrix/attribution and original hash
preimages still need lossless archival before any replacement.

## Evidence/authorization inventory

Let `H = docs/implementation/handoffs/MY2022_JL/` and
`E = H/canonical_import_execution_20261112/attempts/matrix-2022-28s3gq0a/`.

| Required record | Retained artifact / result |
|---|---|
| Approved actual execution Matrix | `E/matrix.json`, 55 rows, 342,943 bytes |
| Matrix content digest | `sha256:e92f9ab6d7b585406e86f697e9cae8400233fc874f4ea884bec718b9148c56cb` |
| Matrix raw byte hash | `sha256:dc2198af761f1087b12cd70016247d231479d31b60a526b56ff4ad436850abc2` |
| Explicit approval | `E/approval.json`: approved by `project_owner`, `2026-11-12T19:03:20Z`; existing approval validator passes against recomputed Matrix digest |
| Candidates and actual execution manifests | All **55** `E/NNNN.candidate.json` and `E/NNNN.manifest.json` matched; all 55 manifest hashes recomputed successfully |
| Classification authority | `H/execution_and_planning_20261112/approved_adjudications/` and candidate-pinned declaration files; 55 direct JSON references all say `approved_classifications` |
| Manufacturer evidence | `H/discovery_20261109/manufacturer_source_inventory.json`, retained PDFs/excerpts and source assertion artifacts |
| Direct dependencies | **76** references: 19 PDFs, one CSV, 55 adjudication JSON files, one text artifact; all exist and match recorded SHA-256; combined file bytes 4,612,085 |
| Edmunds corroboration | `H/edmunds_comparison_20261109/README.md` and `row_comparison.csv`: 56 research offerings corroborated, not independent classification approval; original webpage bytes not claimed |
| Execution / target inventory | `H/canonical_import_execution_20261112/execution_results.json`, `imported_vehicle_definitions.csv`, `import_receipts.json`, integrity reports and artifact hashes |
| Historical pre-import DB | `backups/snapshots/db_snapshot_pre_my2022_canonical_import_20261112_190312.sqlite3`; exists, hash `sha256:5b97afb9c0fbfb7af9be5a84daaee63d5e33e838c0906b1e6d8cac151de75e20` matches retained verification |
| Later full recovery copy | `backups/review/my2021_live_snapshot_cleanup_20261116T195113Z/pre_cleanup.sqlite3`; read-only comparison confirms all 55 original MY2022 snapshot texts present exactly |
| Dedicated scoped snapshot archive | **None located** for MY2022. Must create/verify before a future cleanup, plus a fresh complete backup |

The pre-MY2022-import backup predates these receipts and alone cannot restore them.
The later full backup does contain them, but is not a substitute for fresh guarded
baseline/archival verification at execution time. Do not restore either over later
owner changes. No backup/archive was created, modified, restored or deleted here.

## Historical proofs and consumer compatibility

Found **66** recorded proof edges from **36** MY2022 receipts to **36** MY2022
creation receipts. All recorded whole-snapshot digests match current originals;
maximum chain depth is three edges. No incoming cross-year database proof references
to this set were found. External pinned artifacts may still refer to old proofs;
this is not a universal claim that no other consumer exists.

Current readers requiring examination for a MY2022-only compatibility change:

- `reference/ingestion/importing/powertrain_identity.py`: `assess_peer`,
  `nonidentity_variation`, `identity_proof` and exact-match/revalidation callers.
  Only the existing MY2021 compact version is dispatched specially.
- `reference/ingestion/importing/planner.py:_fields_match_exact`: structured
  exact matching currently delegates to receipt-backed assessment.
- `reference/ingestion/importing/matrix_workflow.py`: historical Matrix completion
  and execution expectations include original root Matrix/resolution/proof fields.
- Legacy `engine_distinction.py`, body-aware receipt readers and Admin/reporting
  must be classified by supported version, not silently coerced to a new format.

The 66 edges are ordinary structured-identity evidence, not exceptional generation
overlap. Under a separately approved new MY2022 agreement basis, they may become
explicitly archival-only **only after both endpoints revalidate successfully**.
Keep original hashes/preimages offline; never rewrite them to match new compact
JSON. Do not automatically inherit the prior year's authorization to retire proofs.
Historical Matrix re-execution must not silently fail or be used as the new normal
inspection route; document the accepted consumer/runbook boundary before live writes.

## Recommended next authorization and limits

Authorize **archival + bounded MY2022 canonical revalidation + isolated replacement
simulation only**, not immediate live cleanup:

1. Pin these exact 55 receipt identities by operation/outcome, year, fixed canonical
   hierarchy/FK and original hashes; capture fresh integrity, count and full-field baseline.
2. Export complete original JSON text losslessly with raw/canonical per-row and archive
   hashes; verify all restorations. Archive the 66 proof references and their consumers,
   approval/Matrix/candidate associations; retain a consistent complete SQLite backup.
3. Implement a separately bounded MY2022 profile authenticated to the **actual executed
   Matrix/approval**, reusing existing identity comparison/normalization conventions.
   Do not change MY2021 hard pins or create a generalized framework. Compare fixed
   Generation identity, five-field powertrains and preserved descriptors/slugs, current
   Engine associations and null body relationships; do not invent new identity mappings.
4. Independently evaluate all 55, check duplicate/ambiguous identities and original
   metadata, and preserve manufacturer authority plus Edmunds corroboration. Do not
   equate this audit's static match with a completed new evaluator or retroactive approval.
5. Prepare compact current-agreement records and narrow consumer handling; retire only
   explicitly approved ordinary proof edges. Keep genuine 2018 overlap and MY2024's
   specialized workflow unchanged. Block unresolved rows instead of forcing success.
6. Rehearse atomic JSON-only replacement, full-table/receipt-column comparisons,
   ordinary readers, rollback and copy-only compaction; measure actual size and required
   deployed Matrix/approval bytes before requesting separate live-cleanup authorization.

**Savings limits:** gross affected JSON is 6.70 MiB; measured document arrays account
for 6.21 MiB, leaving 505,229 bytes of other old snapshot text if only arrays were
removed. New record size and actual SQLite page reclamation are **unmeasured**.
These figures are not additive and do not establish a final DB size. Zero free pages
now means there is no comparable pre-existing freelist reclamation to assume from
MY2021. Any retained runtime basis adds deployment bytes; offline historical archives
must not be uploaded merely to move duplicated data within the same quota.

No missing/altered direct source, candidate, execution manifest or approval blocker
was found. Remaining prerequisites: new scoped snapshot export, complete dependency
closure/backup checks, explicit MY2022 evaluation/consumer and proof-retirement
approval, row-level revalidation, and isolated measurements. Human approval is still
required; current code intentionally supports only the MY2021 compact profile.

## Read-only verification

Measurements used `.venv/bin/python`, SQLite `mode=ro`/`query_only`, source/hash
inspection and system SQLite read-only `dbstat`. Existing MY2021 compact validation
ran for all 73 rows; no full test suite or data-generating tests were needed.
Existing pure Matrix/approval/manifest hash validators authenticated MY2022 artifacts;
no import, generation selection, acquisition or adjudication was executed.
All temporary scripts/metrics are under `/tmp/next_cleanup_*` or
`/tmp/rank_remaining_receipts.py`. The final database and pre-existing repository
file hashes are unchanged; this report is the only repository addition. No staging,
commit, push, migration, compaction, canonical change or deployment performed.
