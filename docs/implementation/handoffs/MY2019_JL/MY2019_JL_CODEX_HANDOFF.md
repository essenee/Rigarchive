# RigArchive — MY2019 Wrangler JL Codex handoff (2026-11-07)

## Authority and status
The live repository and accepted ADRs/designs govern. RA-044 Structured Powertrain Identity is accepted and its implementation was verified: 129 focused tests and 691 full-suite tests reported passing; development migrations reference.0007–0010 applied successfully; Django checks and SQLite integrity/foreign keys passed. User compared a pre-migration backup with the live database: 793 VehicleDefinitions unchanged (PK/UUID/slug), 2,856 import receipts unchanged, and all five new structured powertrain fields null on historical rows. Record acceptance in CURRENT_STATE.md and implementation report if not already recorded. No commits or pushes without user approval.

## Goal
Produce **real** MY2019 US Wrangler JL Candidate 2.1.0 source-backed artifacts and a read-only canonical peer/engine-proof 2.0 review matrix for director authorization. Do not execute canonical imports, backfill historical data, alter historical hashes/receipts, or modify W2. Use existing repository ingestion mechanisms and accepted contracts; don't introduce parallel ungoverned import formats.

## Provisional inventory
10 marketed trim/body combinations, 19 trim/powertrain combinations:
- Two-door: Sport, Sport S, Rubicon, each ERC 3.6L V6 ESS and EC3 2.0L turbo eTorque (6).
- Four-door: Unlimited Sport, Sport S, Sport Altitude, Sahara, Sahara Altitude, Rubicon, each ERC and EC3 (12); Unlimited Moab ERC only (1).
- Model codes: 2-door Sport family JLJL72; Rubicon JLJS72. Four-door Sport family JLJL74; Sahara family JLJP74; Rubicon JLJS74. Quick-order codes are NOT globally unique and must be scoped by model code.
- Proposed ERC attributes: displacement 3.6, cylinders 6, aspiration naturally_aspirated, fuel gasoline, electrification none.
- Proposed EC3 attributes: displacement 2.0, cylinders 4, aspiration turbocharged, fuel gasoline, electrification mild_hybrid. Verify each against applicable explicit source assertions; never infer none/gasoline from silence.
- Preserve separate marketed Altitude and Moab trim identities; no Moab EC3 offering shown in reviewed revisions.

## Source provenance
Forum index (original manufacturer PDF attachments):
- Four-door: https://www.jlwranglerforums.com/forum/threads/2019-jeep-wrangler-4-door-jlu-order-guide-and-pricing-u-s.15026/
- Two-door: https://www.jlwranglerforums.com/forum/threads/2019-jeep-wrangler-2-door-jl-order-guide-and-pricing-u-s.15025/
Direct four-door attachments:
- October: https://www.jlwranglerforums.com/forum/attachments/2019_wrangler_4_door_10_04_2018-pdf.96816/
- November: https://www.jlwranglerforums.com/forum/attachments/2019_wrangler_4_door_11_07_2018-pdf.108687/
- December: https://www.jlwranglerforums.com/forum/attachments/2019-wrangler-4d-december-pdf.121623/
- January: https://www.jlwranglerforums.com/forum/attachments/2019_wrangler_4_door_01_08_2019-pdf.128242/
- February: https://www.jlwranglerforums.com/forum/attachments/2019-wrangler-4-door-february-6-2019-pdf.140201/
- March: https://www.jlwranglerforums.com/forum/attachments/2019-wrangler-4dr-march-1-2019-pdf.153878/
- April: https://www.jlwranglerforums.com/forum/attachments/2019-jeep-wrangler-unlimited-jlu-4-door-order-guide-4-8-19-pdf.165837/
- May: https://www.jlwranglerforums.com/forum/attachments/4-door-5-9-19-pdf.179631/
- June: https://www.jlwranglerforums.com/forum/attachments/4-door-6-4-19-pdf.190918/

Prior research reports all nine revisions for each body were reviewed and supports the 19-row union, with Altitude explicitly present by April 8, 2019. HOWEVER the attached CSVs are **research scaffolds, not source-certified assertions**. Independently validate any needed claim against accessible PDFs and repository contracts; record actual revision date printed inside each document (the four-door March filename says March 1 but the document reportedly says March 4). Source authenticity may be accepted for published guides absent contrary evidence; retain URLs, dates, page references and raw bytes/hash when technically required. Never fabricate source hashes, identifiers, page evidence, or claim the research CSVs are valid import artifacts.

## Working instructions
1. Inspect live repo status, ADR-0012, accepted RA-044, RA-018, CURRENT_STATE.md, ingestion contract validators, Jeep acquisition/extraction code, and existing 2018 JL workflow. Preserve preexisting changes and do not commit/push.
2. Inspect attached inventory, June JLU page-reference CSV, revision ledger and source index. Verify actual manufacturer documents and identify precise applicable evidence for all five structured attributes and every trim/engine offering; use dated-revision union.
3. Construct genuine versioned source/candidate artifacts using existing production contracts. If raw PDF download/hash is technically required and unavailable, stop with a precise blocked-artifact report; do not invent metadata or weaken accepted contracts.
4. Validate Candidate 2.1.0, resolution 1.1, engine proof 2.0, and matrix 2.1 against the **current local database** (post-migration). Inspect existing JL peers, identity collisions and slug behavior. Do not treat the older uploaded database snapshot as live state.
5. Produce an evidence-linked 19-row director-review matrix, clearly marking verified, ambiguous, and blocked rows; note any deviations from the 19-row historical union.
6. Run only focused tests/checks for any code changes and one full suite only if warranted. Prefer using existing tooling; no unnecessary architecture expansion or unrelated refactors.
7. Report source locations, artifacts, checks, unresolved issues, precise authorization request for the next stage. Do not execute imports or apply any further migrations without authorization.

## Bundle layout
- readiness/: latest 19-row RA-044 review and pre-migration 2018 peer snapshot (not live proof)
- consolidated/: 19-row review and 18-revision tracking
- june_jlu/: June four-door offering extraction with page references
- source_index/: source edition index and provisional inventory
- scaffold/: original provisional inventory and evidence ledger template

## Cautions
This handoff includes no original manufacturer PDF binaries. The prior review was conversational; attached research summaries are aids, not authoritative source artifacts. Existing 2018 Jeep extractor was bounded to 2018 and should not be blindly reused for 2019. Preserve historical Candidate/Manifest/Matrix version semantics and hashes.
