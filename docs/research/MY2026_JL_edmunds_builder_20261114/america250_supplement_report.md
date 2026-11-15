# MY2026 Wrangler America250 — supplemental publication

Date: 2026-11-14. Local implementation/execution complete; owner human QA approved.

The owner confirmed America250, four-door, ERC (existing Engine PK1) and EC1
(existing Engine PK2) in Jeep.com's official builder. The supplied URL is retained
verbatim in `america250_supplement.json`; it explicitly demonstrates ERC. EC1 is an
independent owner-confirmed alternative, not a configuration proved by that ERC URL.
No automated Jeep inspection, standard/optional engine ranking, transmission pairing,
new Engine or Edmunds style ID is claimed.

The supplement uses the established inventory fields while remaining separate from
the byte-identical Edmunds extraction. The current importer binds both artifacts
and records actual per-row publisher, source hash/path, source identity, URL and owner
confirmation. This preserves the prior 33 creation receipts' original source bytes.
Existing Engine properties and the exact four-door body are reused.

- Incremental preview: **2 create / 33 skip / 0 block**.
- Execution: **2 created / 33 skipped / 0 failed**; new definition PK1164 (ERC)
  and PK1165 (EC1), creation receipts3555–3556.
- Fresh rerun preview: **0 create / 35 skip / 0 block**.
- Actual second execution: **0 created / 35 skipped / 0 failed**, every definition
  field unchanged. Audit totals added: two creation receipts and 68 no-op receipts.
- Final MY2026: **35 active definitions, 19 groups, ERC16 / EC1 17 / ESG2,
  ten two-door / 25 four-door, zero PHEV**.
- All preexisting rows in all 49 tables remain field-identical; schema/integrity/FK
  checks pass. No existing Engine, definition, receipt, body or parent was modified.
- All **72 focused tests** pass, including source attribution, incremental behavior,
  transactional rollback, registry resolution and public grouping. Django system and
  migration-drift checks pass. All 19 public group pages and 35 Specs pages render
  HTTP200 using read-only verification, without persisted sessions.

See the `america250_*.json` preview/execution/idempotency/post-verification artifacts
for exact identities, hashes and preservation results. The original extraction report
continues to describe only its 18-style/33-configuration Edmunds observation; it is
not rewritten to imply Edmunds supplied America250.

No migration, pricing/ordering/Admin change, staging, commit, push or deployment.
Prior full-suite label-test failures remain documented and were not rerun here.
Human factual/visual website QA is completed and approved by the owner as recorded
in the MY2026 completion task. Unsupported transmission pairings and
engine ranking remain unknown. No publication blocker remains for these two rows.
