# RA-054 — MY2024 Wrangler JL drivetrain dependency correction

Created: 2026-11-14
Status: Proposed

**Correction implemented; 31/31 regenerated registry candidates validate.** All 31
resolve published Generation correspondences, registered Engines and exact body
parents. All 31 read-only complete-family planning attempts now pass the historical
PDF gate and stop at a separate shared-heading projection mismatch: **zero executable
plans, zero ready, 31 blocked**. No further remediation was started.

## Root cause and exact correction

`prepare_retained_candidate` copied the old Candidate 2.1.0
`generic_drive_classification` interpretation, keeping its qualified reference to
`2022_JP_Wrangler_SP / MY2024_Wrangler_technical_layout / tech-4wd`. The registry
adapter omits repeat Engine classification claims but retained this non-engine
assertion. `Release._evidence` consequently required a PDF source reader before
checking the already-established MY2024 offering row.

Only `reference/ingestion/importing/registry_body_import.py` and
`reference/tests/test_registry_body_import.py` changed in application/test code:

- The bounded 3.1.0 preparation helper selects the **existing**
  `research_offering_correspondence` assertion's `drivetrain=4WD` member. It checks
  the exact candidate/retained-inventory row and preserves each existing value.
- The 3.1.0 runtime adapter verifies the existing raw member's literal mapping to
  `generic_drive_classification`, candidate ID, MY2024/US applicability and positive
  same-document offering linkage. It accepts only the retained inventory or factory
  reconciliation CSV path. Source-byte and exact-row verification remain mandatory
  in the existing reader; no source-reader exemption or fabricated assertion exists.
- After this bounded check, the pure supplied-data evidence projection excludes
  this already-checked drivetrain target, as the existing registry projection does
  for its independently checked Engine targets. The actual candidate, target fields,
  body-aware baseline and slug inputs still retain **4WD** unchanged.
- The obsolete MY2022 technical-layout document is excluded from the new candidate's
  active MY2024 evidence set. Full original evidence provenance remains in the
  unchanged, byte-hash-pinned `source_candidate` Candidate 2.1.0 artifact. Older
  Candidate 3.1.0 snapshots and historical raw evidence remain untouched.

No pure Candidate 3.0.0 contract, serializer, evidence checker or legacy Release path
was changed. Native direct configuration evidence still follows the existing pure
validator. Unknown non-engine evidence still fails its source-reader checks. No
new registry, normalization contract, adjudication process or schema was introduced.
Owner-confirmed drivetrain classification was consumed without research or signoff
requests. Engine authority, Generation resolution, body identity, slug algorithm,
human authorization, stale-plan revalidation and atomic execution are unchanged.

## Construction, resolution and read-only planning

Used the accepted production helper and RegistryRelease, with actual operational
registry parents. All 31 envelopes serialize/parse under the existing 3.1.0 contract.
Compared against RA-051: all drivetrain values, Engine bindings, body identities,
Generation evidence and original source-candidate pins remain equal. Only active
evidence selection, the drivetrain interpretation's qualified source reference and
resulting candidate/envelope hashes changed. No original artifacts were rewritten.

Every complete-family attempt supplied the full 31-member family. Parent resolution
passed independently for all 31. The planner now reports:

`PROJECTION_MISMATCH: Retained CSV assertion differs from its exact row.`

The precise next condition is `Release._evidence`'s inventory-CSV
`source_document_heading` branch. It compares **every** heading to the current
individual offering heading, including the existing published shared-selector
heading. For the first family member, JL24-01:

- Existing shared assertion: `United States / MY2024 / Jeep Wrangler (2-door) / Model Code Family JLJL72`
- Reader expects: `United States / MY2024 / Jeep Wrangler (2-door) / Sport [JLJL72 / 22B]`

The model-family heading is an already-retained shared Generation selector, not an
individual trim/QOP heading. This is an **implementation/projection mismatch and
redundant revalidation of an established shared selector**, not missing MY2024
configuration information, a canonical identity conflict, or a new drivetrain/Engine
decision. The full-family gate propagates the first member's failure to all 31
planning assessments. No assertion or reader was changed to clear this new gate.
Exact diagnostic/context: [data/next_blocker.json](data/next_blocker.json).

**Smallest next task:** narrowly distinguish the already-published shared-selector
heading from an individual offering heading in the existing reader, retaining exact
published-payload/raw-byte verification and individual row checks; then replan.
Do not request a new general configuration/drivetrain review. Execution still
requires separate exact Matrix/approval authorization after executable planning.

**Production complete-family slug planning was not reached.** No new production
slug-collision result is claimed. The focused existing synthetic registry regression
for all 31 slugs and ten body collision pairs passed; target drivetrain/body/Engine
inputs and the slug implementation are unchanged.

## Exact 31-row readiness inventory

All rows are MY2024 US, 4WD. Each candidate is contract-valid; Generation/Engine/body
parents resolve. `H` = the common shared-heading mismatch; action unavailable.

| Offering | Trim | Doors | Engine | Candidate/parents | Plan |
| --- | --- | --- | --- | --- | --- |
| JL24-01 | Sport | two-door | EC1 | valid/resolved | blocked H |
| JL24-02 | Sport | two-door | ERC | valid/resolved | blocked H |
| JL24-03 | Sport S | two-door | EC1 | valid/resolved | blocked H |
| JL24-04 | Sport S | two-door | ERC | valid/resolved | blocked H |
| JL24-05 | Willys | two-door | EC1 | valid/resolved | blocked H |
| JL24-06 | Willys | two-door | ERC | valid/resolved | blocked H |
| JL24-07 | Rubicon | two-door | EC1 | valid/resolved | blocked H |
| JL24-08 | Rubicon | two-door | ERC | valid/resolved | blocked H |
| JL24-09 | Rubicon X | two-door | EC1 | valid/resolved | blocked H |
| JL24-10 | Rubicon X | two-door | ERC | valid/resolved | blocked H |
| JL24-11 | Sport | four-door | EC1 | valid/resolved | blocked H |
| JL24-12 | Sport | four-door | ERC | valid/resolved | blocked H |
| JL24-13 | Sport S | four-door | EC1 | valid/resolved | blocked H |
| JL24-14 | Sport S | four-door | ERC | valid/resolved | blocked H |
| JL24-15 | Willys | four-door | EC1 | valid/resolved | blocked H |
| JL24-16 | Willys | four-door | ERC | valid/resolved | blocked H |
| JL24-17 | Sahara | four-door | EC1 | valid/resolved | blocked H |
| JL24-18 | Sahara | four-door | ERC | valid/resolved | blocked H |
| JL24-19 | Rubicon | four-door | EC1 | valid/resolved | blocked H |
| JL24-20 | Rubicon | four-door | ERC | valid/resolved | blocked H |
| JL24-21 | Rubicon X | four-door | EC1 | valid/resolved | blocked H |
| JL24-22 | Rubicon X | four-door | ERC | valid/resolved | blocked H |
| JL24-23 | Rubicon 392 | four-door | ESG | valid/resolved | blocked H |
| JL24-24 | Rubicon 392 Final Edition | four-door | ESG | valid/resolved | blocked H |
| JL24-25 | Sport S 4xe | four-door | ECX | valid/resolved | blocked H |
| JL24-26 | Willys 4xe | four-door | ECX | valid/resolved | blocked H |
| JL24-27 | Jeep Beach 4xe | four-door | ECX | valid/resolved | blocked H |
| JL24-28 | Sahara 4xe | four-door | ECX | valid/resolved | blocked H |
| JL24-29 | High Altitude 4xe | four-door | ECX | valid/resolved | blocked H |
| JL24-30 | Rubicon 4xe | four-door | ECX | valid/resolved | blocked H |
| JL24-31 | Rubicon X 4xe | four-door | ECX | valid/resolved | blocked H |

Artifacts: [data/candidates/](data/candidates/) (31 new envelopes),
[data/readiness.csv](data/readiness.csv),
[data/planning_results.json](data/planning_results.json),
[data/parent_resolutions.json](data/parent_resolutions.json), and
[data/summary.json](data/summary.json). Provenance, source pins, original labels and
transmission/QOP distinctions remain associated with their original offering.

## Verification actually executed

- **46 passed**: `test_registry_body_import` and `test_body_import_final_review`.
  New regressions exercise all 31 retained drivetrain row mappings and original
  provenance, invalid/cross-candidate/year/market claims, unchanged 3.0 projection
  behavior, and rejection of unrelated unsupported non-engine evidence. Existing
  registry execution, parent/identity, stale-state, authorization, receipt, atomicity
  and ten-pair/all-31 slug regressions remain passing.
- **80 passed**: `test_candidate_v3_wire` and `test_body_import_contracts`, preserving
  historical 3.0.0 behavior, fixtures and closed contracts. **126 tests total**;
  no full suite run.
- `manage.py check`: passed. `makemigrations --check`: no changes detected.
  `git diff --check`: passed.
- Operational verification opened SQLite via `mode=ro` and `query_only=ON`;
  all database table row fingerprints remained equal. Counts remain **1,053
  VehicleDefinitions, 254 correspondences, 3,362 receipts, seven Engines, two bodies**.
  Historical Engine/body FKs remain null; zero MY2024 JL VehicleDefinitions.
  Integrity `ok`; foreign-key violations zero.
- Before/after database SHA-256:
  `46aafa64d6b34f880a441a000675becedb890ff6a225a745208dd00bcb75e5ef`.
- Tests used isolated test databases through `RIGARCHIVE_TEST_DB_PATH` with the
  previously authorized `.venv/bin/python` fallback; no operational writes occurred.
  Required `venv/py313/bin/python` remains absent.

HEAD remains `a99187227e862a5c97fcdb12491a5bac2e2f1ffb`. Pre-existing unrelated work,
RA-051/052/053 artifacts and operational data are preserved. No staging, commit,
push, imports, approvals, new correspondences, Engine/body edits or historical
associations were performed. The next mismatch is reported, not remediated here.

## Deferred ingestion simplification — after MY2024 publication

Design objectives recorded only; no redesign implemented:

1. Canonical records and human-approved classifications should be reusable without repeating original source research.
2. Source provenance should be preserved without making every future ingestion dependent on historical extraction machinery.
3. Configuration identity, classification, evidence acquisition and publication authorization should have clearly separated responsibilities.
4. Established decisions should remain authoritative unless a concrete contradiction is identified.
5. Ingestion should require the minimum necessary human decisions and validation steps.
6. New model-year ingestion should not require a new architecture milestone or extensive evidence-remediation process.
