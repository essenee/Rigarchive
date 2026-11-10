# Existing ingestion workflow and discovery boundary

Created: 2026-11-09
Status: Proposed

The repository at main/bef7d76e3fe4f33990180694f845a436b7987da3 is the implementation
baseline. Existing local changes to db.sqlite3 and DATA_PRESERVATION.md are preserved.
CURRENT_STATE's completed MY2021 chain is consistent with the inspected handoffs;
older architecture text describing preimplementation state is historical context.

| Procedure | Existing authority and implementation | Discovery use / later gate |
| --- | --- | --- |
| Discovery/acquisition | ADR-0006; RA-022; acquisition/manufacturer.py, profiles.py, snapshots.py | Retain original bytes, full SHA-256 and locator. Follow MY2021 handoff retention precedent. Existing Jeep brochure extractor is publication-specific; do not force MY2022 guides through its 2018 constants. |
| Source assertions | RA-011; contracts.py, serialization.py, validation.py | Preserve raw page/section and source applicability; no formal assertion sets constructed in this discovery. |
| Normalization and market | ADR-0005; RA-014/020; normalization/manufacturer.py and powertrain.py | US heading establishes guide market independently of request context. Keep model year, revision, raw labels and code grouping. |
| Manufacturer code and body/trim | ADR-0010/0011; MY2021 discovery and classification handoffs | Codes remain source-native evidence, not canonical keys. Raw Altitude columns remain distinguished by model section; no new trim taxonomy approval. Wrangler body handling remains approved two-door/four-door trim normalization. |
| Five-field powertrain | ADR-0012; RA-044; reference/powertrain.py and importing/powertrain_identity.py | Direct terminology assessed with existing _supports; null never defaults to none or naturally_aspirated. Engine codes are lineage, not identity. No application code changed. |
| Candidate construction | RA-016; candidate/builder.py; Candidate 2.1.0 | Future stage only; joins need actual coexistence, never Cartesian products. |
| Human adjudication | ADR-0008; classification_adjudication.py; MY2021 candidate/fuel handoffs | Future exact-base proposals and explicit owner decisions. An adjudication is not import authorization. |
| Generation correspondence | ADR-0010; generation_correspondence.py | Future reviewed source-bound applicability and target UUID, followed by separately authorized publication. No new correspondence reused/published here. |
| Matrix certification | matrix.py, matrix_approval.py and MY2021 final planning | Future complete five-field candidate checks and exact evidence-bound Matrix 2.1 review. No Matrix constructed or certified. |
| Canonical import | ADR-0004/0007; importing/planner.py, importer.py, workflow.py and matrix_workflow.py | Future replan, exact human authorization, atomic create/receipt and peer checks; none invoked here. |

Reviewed MY2021 README, revision inventory, discovery builder/validator, supplemental
inventory, candidate classification README and preflight, and CURRENT_STATE's final
canonical checkpoint. MY2021's 74 discovery rows (73 approved consumer rows plus
RHD) are comparison evidence, never a MY2022 target. MY2019/MY2020 precedents remain
unchanged and subordinate to actual MY2022 availability evidence.

This is a handoff-local research transcription following the MY2021 precedent;
it introduces no ingestion schema, production extractor, framework, dependency,
Django application or migration. The raw retention manifest is a research index,
not an executable import manifest. No architecture decision is required.
