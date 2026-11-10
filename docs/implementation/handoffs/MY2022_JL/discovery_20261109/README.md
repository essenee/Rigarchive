# MY2022 US Jeep Wrangler JL — manufacturer evidence discovery

Created: 2026-11-09
Status: Proposed

Discovery and evidence acquisition only. No Candidates, classification approvals,
generation publications, Matrix certification, canonical imports, migrations or
operational database writes are authorized or performed by these artifacts.

## Result

Retained **21 manufacturer-origin sources: 18 US ordering-guide PDFs, two
publisher-hosted technical PDFs, and one Stellantis-authored press release
distributed by PR Newswire**. The ordering guides are manufacturer-issued copies
on a third-party archive, not official-host acquisitions. Their US/MY2022 headers,
FCA footer, dates and model/QOP tables were checked; no signature authentication
is claimed. Third-party forum commentary does not establish configuration facts.

The observed guide union contains **56 provisional research rows: 15 two-door and
41 four-door**. Of these, **55 are consumer proposals and one is a separately
flagged Sport RHD scope question**. These represent 20 body/model/column-label
groups, nine manufacturer model codes, six engine codes, 543 positive QOP cells
and 81 powertrain-table pages. Transmission alternatives remain within rows.
There are 224 retained package/option/group pages, without synthesizing package
permutations. **Jeep Beach is a confirmed marketed edition with unresolved
identity/code correspondence, retained separately rather than counted as another
canonical configuration.** The count is therefore an observed-guide count, not a
certified complete factory configuration count or approved taxonomy.

| Model code | Body | Raw marketed labels represented |
| --- | --- | --- |
| JLJL72 | Two-door | Sport; Willys Sport; Sport S; Willys |
| JLJS72 | Two-door | Rubicon |
| JLJL74 | Four-door | Sport; Willys Sport; Sport S; Willys; Altitude; High Tide |
| JLJP74 | Four-door | Sahara; Altitude; High Altitude |
| JLJS74 | Four-door | Rubicon |
| JLJX74 | Four-door | Rubicon 392 |
| JLUL74 | Four-door | Sport RHD — scope held for review |
| JLXP74 | Four-door | Sahara 4xe; High Altitude (under Sahara 4xe heading) |
| JLXS74 | Four-door | Rubicon 4xe |

## Revision coverage

Both body styles have nine retained revisions: 2021-10-08, 2021-11-10,
2021-12-07, 2022-01-12, 2022-01-17, 2022-02-10, 2022-03-11, 2022-04-07,
and June (two-door 2022-06-03; four-door 2022-06-01). All guides print an initial
issue of 2021-10-08. These are all PDFs listed in the first-post collections
inspected at the [two-door archive](https://www.jlwranglerforums.com/forum/threads/2022-jeep-wrangler-jl-2-door-order-guide-updated-monthly.80533/)
and [four-door archive](https://www.jlwranglerforums.com/forum/threads/2022-jeep-wrangler-unlimited-jlu-4-door-order-guide-updated-monthly.80490/).
They do not prove that no other historic revisions exist. No later MY2022 guide
was established in the focused search; calendar-year 2022 MY2023 guides are not
MY2022 evidence.

Multiple revisions are necessary: October preserves ERC automatic availability;
November adds positive High Altitude EC1/ERG cells; February adds High Tide.
October plus November plus February covers the observed body/trim/engine and
transmission union (two-door October alone covers its observed union). Retain all
18 for date-sensitive restrictions. Guide dates are observation dates, not proven
production start/end boundaries.

## Evidence and review

See [workflow review](WORKFLOW_REVIEW.md), [powertrain review](POWERTRAIN_REVIEW.md),
[comparison](MY2021_TO_MY2022.md), and [unresolved questions](UNRESOLVED_AND_NEXT_STAGE.md).
Every JSON/CSV research row links to exact source hash, revision, QOP and PDF page.
The five-field matrix preserves nulls where direct terminology is insufficient;
possible review values are explicitly proposals. No MY2021 decision is inherited.

The technical specification conflicts with the guides and itself: SP p1 describes
ESS/manual and eTorque/automatic, whereas p5 describes manual/eTorque; SP p1 also
omits early ERC automatics. These conflicts remain unresolved, not repaired by
changing source bytes or inventing new pairings.

## Artifact map

- `manufacturer_source_inventory.json` / `.csv`: 20 PDFs, URLs, printed dates, hashes, page counts and retention timestamps.
- `supplemental_source_inventory.json`: distributed manufacturer press release, date, hash and use limitations.
- `raw_source_retention_manifest.json`: all 21 raw source references and hashes.
- `source_pdfs/`: unchanged acquired PDFs. `evidence/`: full PDF layout extraction and original press-release HTML/text.
- `provisional_configuration_inventory.json` / `.csv`: 56 nonexecutable research rows.
- `positive_package_observations.json`, `evidence_index.json`: 543 positive availability cells and 81 table excerpts.
- `revision_comparison.json`: dated pairing additions and omissions.
- `factory_package_availability_excerpts.json`: retained package/options/group evidence.
- `powertrain_evidence_matrix.json`: six families, five fields, fuel-grade notes and unresolved classifications.
- `MY2021_to_MY2022_comparison.json` / `.csv`: evidence-linked year comparison.
- `edition_and_scope_review.json`: Jeep Beach, RHD and unsupported carryforward cases.
- `build_discovery.py`, `build_assessments.py`, `validate_discovery.py`, `verify_project.py`: bounded offline transcription and verification.
- `VALIDATION.md`, check transcripts, `preservation_baseline.json`, `artifact_hashes.json`: actual verification and preservation evidence.

Stop at discovery. The next stage requires owner review and separate authorization.
