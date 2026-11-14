# RA-052 — MY2024 Wrangler JL Generation correspondence proposal

Created: 2026-11-14
Status: Proposed

**12/12 selectors prepared, 12 supported by existing retained evidence, zero
unsupported or conflicting selectors. Coverage: all 31 retained consumer offerings.**
Nothing has been published or authorized for publication by this preparation.

## Exact decisions

Every row proposes `finding=established`, `revision_number=1`, no predecessor,
empty restrictions, market **US**, and **start_year=end_year=2024**. The target is
Generation **PK32 / UUID `38d3c3ac-f825-4406-abb5-c2d12b9129a4`**, name/slug JL/jl,
start 2018, end null, active; its actual parent is active Wrangler PK21 / UUID
`5ec5f58a-b140-484c-97f0-c90ec9c134d6`, under active Jeep PK20 / UUID
`42eefe42-0f2f-4e31-b4b2-f3e520ea0e50`. Generation has no market attribute;
US applicability belongs to each correspondence, not an invented parent field.

All selectors use `source_namespace=source_model_code`, `identity_type=model_code`.
Source abbreviations in the table retain these exact identities:

- **E**: `rigarchive_MY2024_edmunds_reconciliation`
- **G**: `fca_us_2024_jlu_order_guide_transcription`

| Source | Exact native model code | Affected offerings | Supporting retained evidence | Published JL precedent PK | Proposed status / conflict |
| --- | --- | --- | --- | ---: | --- |
| G | JLJP74 | JL24-18 | Guide transcription row + inventory JL join | 235 | established, unpublished / none |
| G | JLXL74 | JL24-27 | Guide transcription row + inventory JL join | 239 | established, unpublished / none |
| E | JLJL72 | JL24-01, JL24-02, JL24-03, JL24-04, JL24-05, JL24-06 | Inventory row + shared selector | 233 | established, unpublished / none |
| E | JLJL74 | JL24-11, JL24-12, JL24-13, JL24-14, JL24-15, JL24-16 | Inventory row + shared selector | 232 | established, unpublished / none |
| E | JLJP74 | JL24-17 | Inventory row + shared selector | 235 | established, unpublished / none |
| E | JLJS72 | JL24-07, JL24-08, JL24-09, JL24-10 | Inventory row + shared selector | 236 | established, unpublished / none |
| E | JLJS74 | JL24-19, JL24-20, JL24-21, JL24-22 | Inventory row + shared selector | 237 | established, unpublished / none |
| E | JLJX74 | JL24-23, JL24-24 | Inventory row + shared selector | 238 | established, unpublished / none |
| E | JLXL74 | JL24-25, JL24-26 | Inventory row + shared selector | 239 | established, unpublished / none |
| E | JLXP74 | JL24-28 | Inventory row + shared selector | 240 | established, unpublished / none |
| E | JLXS74 | JL24-30, JL24-31 | Inventory row + shared selector | 241 | established, unpublished / none |
| E | JLXT74 | JL24-29 | Inventory row + shared selector | 239 | established, unpublished / none |

The [consolidated selector inventory](selectors.csv) records each complete selector,
revision and chain UUID, exact content hash, payload path, source reference/hash,
assertion-set ID, original proposal, relevant published revision UUID/hash/source/year,
full affected IDs and conflict result. Its twelve rows are the complete proposal;
RHD and quarantined offerings are excluded.

## Evidence and bounded interpretation

The hash-pinned existing MY2024 `candidate_inventory.csv` explicitly identifies
Jeep, Wrangler, JL, US, 2024 and the exact model code for each of the 31 offerings.
All retained rows for each selected model code agree on JL. Ten E selectors retain
this reconciliation provenance; the two G selectors retain their distinct manufacturer
guide-transcription source IDs, `factory_reconciliation.csv` references, guide
revision/page attribution and exact codes. Their affected IDs join the same existing
inventory's explicit JL assignment. No attribution is transferred between sources.

Each payload includes **the exact existing shared-selector document object from
RA-051 Candidate 3.1.0**, unchanged. Assertions, contexts, raw reference/hash,
extractor, publication revision and source applicability are preserved. Retained raw
bytes were verified. These are reconciled/transcribed sources; the proposals do not
claim newly acquired original guide PDFs or newly authenticated manufacturer claims.
The existing qualified model-code selectors and previously accepted JL identity
support this bounded Generation decision without engine/property or availability
inference. The source evidence is sufficient for this proposal; no new research or
repeat classification review is requested.

Eleven selectors have same-code published JL precedents from earlier years. Their
exact UUIDs/hashes are in `selectors.csv`; those older source/year scopes are not
extended or replaced. **JLXT74 has no earlier exact-code published precedent**:
its current retained MY2024 row explicitly supplies the JL assignment. Its cited
JLXL74 precedent is only a comparison of publication pattern/schema, not proof of
JLXT74 or adjacent-year availability. This distinction is recorded in its payload.

## Exact payloads and publication compatibility

[proposals/](proposals/) contains exactly twelve ordinary existing-workflow JSON
artifacts, each `{"review": Review1, "content_hash": digest(Review1)}`. No new approval
format, Approval1, Matrix or publication script was created.

The older unpublished proposals used legacy document projections that differ from
the current Candidate 3.1.0 objects (including timestamp canonicalization and removal
of empty legacy applicability extensions). Publishing those unchanged would fail
the resolver's exact-document membership requirement. These proposals use the
current existing documents without modifying candidates or raw evidence. Existing
unpublished chain UUIDs are retained; new deterministic revision UUIDs distinguish
the corrected proposal bytes. There is no database predecessor and `supersedes_uuid`
remains null. Old artifacts are preserved, not rewritten.

`reviewer=codex` and `reviewed_at` record this actual preparation, not fictitious
owner signoff. Each `review_notes` explicitly says proposed and pending Project Owner
publication authorization. The `established` value is the proposed domain finding;
it does not grant authority to execute publication.

## Read-only validation actually performed

- Exactly twelve unique source/namespace/type/native-code selectors and revision IDs.
- All 12 passed `validate_review_payload`, retained-byte `validate_documents`, exact
  content hashing and unsaved `GenerationCorrespondenceRevision.full_clean()`.
- All 12 matched the verified active parent chain, US market and MY2024-only scope;
  no existing chain/revision UUID collision or current overlapping published selector.
- All 31 passed existing `validate_generation_evidence`; each Generation selector is
  covered by one proposal and each proposed evidence object is exactly present in
  every affected candidate. Restrictions remain empty and all candidate selectors
  stay within the proposed year/market. This checks the resolver's relevant
  publication/document prerequisites without pretending proposals are published.
- Relevant older published JL payload hashes and retained source bytes were verified.
- No publication function was invoked: it can create receipts even on a failed
  publication attempt. No database save was called; validators performed queries only.
- No application code, schema, candidate or existing evidence was modified. No full
  Django suite or new tests were run. Git whitespace checks passed.

Results and parent snapshot: [validation.json](validation.json).

## Preservation and next authorization

Expected, actual before, and actual after operational DB SHA-256 all match:
`6edc62df2940eab2019593f9fcc6c8c239787733879e2f6ef00edf8c56d07e2a`.

All database table row fingerprints are unchanged. Counts remain **1,053
VehicleDefinitions, 3,350 receipts, 242 correspondence revisions, seven Engines and
two bodies**. No historical Engine/body FK assignments exist; zero MY2024 JL
VehicleDefinitions. SQLite integrity is `ok`; foreign-key violations are zero.
Read-only SQLite URI `mode=ro` plus `PRAGMA query_only=ON` protected operational
access. Used the previously authorized `.venv/bin/python` fallback; the required
`venv/py313/bin/python` remains absent. HEAD remains
`a99187227e862a5c97fcdb12491a5bac2e2f1ffb`. Unrelated working changes and untracked
artifacts are preserved. Nothing was staged, committed or pushed.

**Smallest next step:** owner authorization to publish exactly the twelve Review1
payloads and content hashes in `selectors.csv` through the existing correspondence
publication workflow, with fresh state/conflict validation and normal publication
receipts. After authorized publication, rerun the existing complete-family planner.
This proposal does not authorize vehicle publication or imply that later source,
body, identity, slug or Matrix/approval checks have passed.
