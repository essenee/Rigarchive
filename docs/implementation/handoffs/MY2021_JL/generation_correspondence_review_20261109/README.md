# MY2021 JL generation correspondence owner review

Created: 2026-11-09
Status: Proposed — preparation verified; publication authorization pending

**73/73 current consumer candidates resolve to existing Wrangler JL Generation
PK 32 / UUID `38d3c3ac-f825-4406-abb5-c2d12b9129a4` in proposed-state simulation.**
Coverage requires **95 distinct source/model keys**, **zero reusable existing
correspondences**, and **95 new unpublished correspondence proposals**.

Each key already has one exact shared selector document in every matching current
candidate. This package copies those existing documents for review. It adds no
candidate evidence and creates no candidate revision. No contract incompatibility
or preparation blocker remains. **Nothing has been published.** Actual
published-only resolution remains missing for all 73 MY2021 candidates until
separately authorized publication succeeds.

## Scope and coverage

The latest index is taken from `../fuel_completion_20261109/`, not superseded
candidate indices. Its exact file hash and all 73 current artifact/content digests
are retained in `current_candidate_references.json`. Scope remains **23 two-door /
50 four-door**, **24 approved body/trim labels**, and **73 complete five-field
identities**, including the resolved 392 gasoline classification.

| Manufacturer model code | Distinct source/model keys and new proposals | Unique candidates covered |
| --- | ---: | ---: |
| JLJL72 | 13 | 20 |
| JLJL74 | 14 | 31 |
| JLJP74 | 14 | 11 |
| JLJS72 | 13 | 3 |
| JLJS74 | 14 | 4 |
| JLJX74 | 9 | 1 |
| JLXP74 | 9 | 2 |
| JLXS74 | 9 | 1 |
| Total | 95 | 73 |

The 95 keys span 27 original order-guide revisions. A key is the exact tuple
`source_id / source_namespace / identity_type / native_identifier`, with namespace
`source_model_code` and type `model_code`. Multiple retained guide revisions are
distinct source IDs, so eight manufacturer codes do not imply eight proposals.
Each candidate requires every applicable retained source/model key in its evidence.

`correspondence_coverage_matrix.json` and `.csv` enumerate all 95 keys with their
candidate references/counts, body styles, approved trims, exact current revisions,
manufacturer headings, guide URLs/dates/pages/hashes, source/model identities and
target Generation. Candidate groups overlap across guide revisions; their per-key
coverage counts must not be summed as additional vehicles.

## Existing state and reuse assessment

Live read-only inspection verified **861 VehicleDefinitions, 2,980 audit receipts
and 64 published correspondence revisions**. All 64 payload hashes, model
contracts and retained evidence bytes validate. Their year scopes are eight
MY2018 records, five MY2019 records and 51 MY2020 records; none applies to 2021.
The 56 MY2019/MY2020 mappings have their original successful publication receipts.

No exact MY2021 source/model key is already published. Same-code earlier-year
correspondences cannot be extended by inference: accepted lookup checks the
exact four-part key, model, market, year and active revision, followed by exact
selector evidence inclusion. `existing_correspondence_reuse_assessment.json`
retains all 64 records, their original review payloads/hashes and the reuse result.
No existing record is modified or proposed for revision.

The canonical target was inspected independently: existing active Jeep Wrangler
JL PK 32, UUID above, start year 2018, open end year, active Wrangler model and
Jeep manufacturer. The active JK generation ends in 2018. Proposal applicability
is narrowly **US MY2021 only**. Dated source issue dates in 2020 are not mistaken
for vehicle model year; the manufacturer guide heading explicitly establishes
United States / 2021 / Wrangler/body applicability.

The reviewed relation uses the manufacturer model/body tables and accepted
MY2021 US Wrangler JL offering context, existing canonical target and temporal
applicability. It is not an automatic match from a code prefix, similar display
name or unscoped prior-year publication. 4xe and 392 remain within their documented
Wrangler Unlimited family; no new model or Generation is introduced.

## Shared selectors and proposed publications

For every key, the intersection of all matching candidates' complete evidence
document dictionaries contains exactly one valid selector for that key. These
are the already-retained shared source/model documents, not candidate-specific
IDs. Raw source hash alone is insufficient: the accepted resolver requires the
entire proposed evidence document to occur exactly in each matching candidate.

`shared_selectors/` retains 95 verbatim document dictionaries. The selector index
records exact document/file hashes, original assertion-set IDs and all matching
candidate references. No assertion ID, source/model key, candidate identity,
classification, approval or candidate digest was changed to meet this condition.
The MY2020 mismatch was reviewed; the current MY2021 packaging already satisfies
its required exact shared-document inclusion.

`new_correspondence_proposals/` contains 95 accepted-format review artifacts, each
with exact `review` and `content_hash` fields, fresh revision/chain UUIDs, revision
number 1, no predecessor, one original selector, no extra restrictions and target
JL Generation UUID. Contract/model validation, source-byte checks, UUID/key
uniqueness and JSON round trips pass. These are review findings, **not publication
authorizations or publication receipts**.

## Resolution simulation and tests

The real read-only resolver first rejects all 73 candidates against published
state alone with `Missing reviewed generation correspondence.` For simulation,
only `_applicable_revisions` is supplied with the union of the real published
lookup and the correctly filtered **unsaved** proposals. Accepted candidate
evidence projection, exact selector inclusion, content hashes, restrictions,
active parents, generation range and single-target checks run unchanged.

All 73 then resolve with basis `reviewed_source_correspondence` to PK 32 and the
expected UUID. Returned revision UUID/hash sets exactly match each candidate's
required proposal keys. There are **zero unmatched keys, duplicate proposal keys,
conflicting targets or RHD dependencies** in this combined proposed state.

Necessity and compatibility were tested for every one of the 95 proposals:

- Removing that proposal makes an affected candidate fail with missing reviewed
  correspondence; no year-only fallback occurs.
- Supplying a hypothetical metadata-altered selector copy makes an affected
  candidate fail exact evidence matching. These are in-memory negative controls;
  no candidate artifact or revision is changed.

All **190 negative controls** passed. All **125 focused correspondence,
generation-projection, candidate, adjudication, structured-powertrain and
serialization tests** passed with isolated databases/media. Django system checks,
migration consistency and dependency checks passed. Exact environment:
`/Users/cosmo/dev/Rigarchive/.venv/bin/python`, Python **3.13.1**, Django **6.0.7**,
pypdf **6.16.1**; dependencies match `requirements.txt`. No software was installed
or upgraded. See `verification_report.md` for commands and logs.

## Preservation and next boundary

All **73 candidate hashes**, all **88 prior approved decisions**, the additional
392 fuel approval, direct ECX evidence and every preexisting MY2021 handoff file
remain unchanged. Sport RHD JLUL74 / JL21-71 and CLASS-075 remain in their original
deferred preservation records. No correspondence proposal references JLUL74.

The live database remains byte-for-byte unchanged, with SHA-256:
`ec1eb2adb8becf62a6d8ef18e5ae2dee37d5049620faaaeec51ab8c69b0ee4f9`.
Counts are unchanged; SQLite integrity and foreign keys pass. All 950 preexisting
MY2021 handoff files retain their hashes. Application/contract files are unchanged.
`CURRENT_STATE.md` and `CHANGELOG.md` record only completed preparation and its
unpublished status. No commit or push occurred; all preexisting work was preserved.

**Recommendation: review exactly these 95 proposals, then separately authorize
publication if accepted.** Fresh candidate/source/selector, UUID, applicability,
target and database checks must precede any later publication. No unresolved
preparation question remains; RHD semantics remain intentionally outside scope.

No correspondence or publication receipt, candidate revision, canonical import
plan, VehicleDefinition, Matrix certification, migration or backfill was created.

## Package index

- `repository_and_database_state.json`, `environment.json`: verified current
  target, counts, existing publication integrity, historical workflow references
  and actual environment.
- `correspondence_coverage_matrix.json` / `.csv`: every key and candidate group.
- `existing_correspondence_reuse_assessment.json`: all existing records assessed.
- `new_correspondence_proposal_index.json`, `new_correspondence_proposals/`:
  95 exact unpublished review artifacts and hashes.
- `shared_selector_index.json`, `shared_selectors/`: exact existing selectors.
- `candidate_resolution_index.json`, `current_candidate_references.json`:
  all current revisions/digests and their expected correspondence bindings.
- `source_and_evidence_hash_inventory.json`: original documents/extractions and
  shared-selector hashes; candidate hashes are in the candidate-reference index.
- `resolution_simulation_report.json`, `validation_results.json`: complete
  positive/negative results, uniqueness, preservation and applicability checks.
- `publication_recommendations.json`: unresolved questions and next authorization.
- `verification_report.md`, test/check logs: executed verification.
- `preservation_baseline.json`, `artifact_hashes.json`: before/after preservation
  and complete review-package hash inventory.
- `prepare_review.py`: bounded artifact driver; no publication/save/plan API.
