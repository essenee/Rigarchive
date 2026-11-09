# MY2020 US Wrangler JL factory offering discovery

Created: 2026-11-08
Status: Proposed

Research and discovery only. No Candidate 2.1.0 artifacts, adjudication approvals,
correspondence proposals/publications, canonical import plans or imports were
created. Existing contracts and the accepted MY2019 architecture are unchanged.

## Proposed offering union

**49 unique body/marketed-trim/powertrain proposals: 15 two-door and 34 four-door,
across 21 body/trim variants.** The union is supported by populated QOP cells in
20 retained manufacturer-issued US order guides: 9 two-door and 11 four-door.
Twenty-two distinct guide URLs were located, with two unretained gaps documented
below. This is the complete observed retained-guide union, not a certification
that every manufacturer revision or delivered factory configuration is covered.

| Proposed trim label | Model code | Offered engine codes in retained revision union | Rows |
| --- | --- | --- | ---: |
| Black and Tan | JLJL72 | EC1, ERC | 2 |
| Freedom | JLJL72 | EC1, ERC | 2 |
| Rubicon | JLJS72 | EC1, ERC | 2 |
| Rubicon Recon | JLJS72 | EC3 | 1 |
| Sport | JLJL72 | EC1, ERC | 2 |
| Sport S | JLJL72 | EC1, ERC | 2 |
| Unlimited Black and Tan | JLJL74 | EC1, ERC | 2 |
| Unlimited Freedom | JLJL74 | EC1, ERC | 2 |
| Unlimited North Edition | JLJP74 | EC3 | 1 |
| Unlimited Rubicon | JLJS74 | EC1, ERC, EXJ | 3 |
| Unlimited Rubicon Recon | JLJS74 | EC3 | 1 |
| Unlimited Sahara | JLJP74 | EC3, ERC, ERG, EXJ | 4 |
| Unlimited Sahara Altitude | JLJP74 | EC3, ERC, ERG, EXJ | 4 |
| Unlimited Sahara High Altitude | JLJP74 | EC3, ERG, EXJ | 3 |
| Unlimited Sport | JLJL74 | EC1, ERC, EXJ | 3 |
| Unlimited Sport Altitude | JLJL74 | EC1, ERC, EXJ | 3 |
| Unlimited Sport S | JLJL74 | EC1, ERC, EXJ | 3 |
| Unlimited Willys | JLJL74 | EC1, ERC, EXJ | 3 |
| Unlimited Willys Sport | JLJL74 | EC1, ERC | 2 |
| Willys | JLJL72 | EC1, ERC | 2 |
| Willys Sport | JLJL72 | EC1, ERC | 2 |

Engine totals: ERC 17; ERG 3; EC1 15; EC3 6; EXJ 8. There is no additional offered
engine code in the retained guides. `ERS` in the specifications is transmission
Electronic Range Select, not an engine. Only model codes JLJL72, JLJS72, JLJL74,
JLJP74 and JLJS74 were observed; no RHD-specific model code was found.

Each matrix row contains exact guide source IDs, positive availability-cell
references, printed dates, model code, QOP codes and engine/transmission codes.
There are 547 positive package-cell observations across revisions and 51 retained
powertrain-table excerpts. Trim labels are proposed normalization; the source
columns and raw table text remain separate. Blank cells never become offerings.

Transmission codes are DEM (six-speed manual), DFT (850RE eight-speed automatic)
and DFV (8HP75 eight-speed automatic). Prefixes 23/24 describe ERC manual/automatic
alternatives; 22 EC1/DFT, 25 ERG/DFT, 28 EC3/DFT and 26 EXJ/DFV are verified
against their actual engine/transmission table segments. Codes are scoped by
model code. Manual/automatic versions of the same structured identity are merged.
ERC versus ERG on Sahara is a proposed electrification distinction, not merely a
transmission split or engine-code distinction.

## Revision findings

[Revision review](REVISION_REVIEW.md) records every retained revision and its
additions/omissions. The early two-door retained guide has 8 combinations;
Willys, Freedom, Willys Sport and Recon expand it to 15. The four-door guide
starts at 16, adds Willys, Freedom, North Edition, diesel combinations, Willys
Sport, Recon and finally Sahara High Altitude, reaching 34.

March 3 guides together contain the full observed 49-row union. April contains
44: Black and Tan disappears in both bodies, and ordinary four-door Rubicon
EXJ/DFV/26R disappears. Earlier positive cells preserve those five combinations
in the model-year union. No cancellation or production-end date is inferred.
North Edition already appears in the October 15 guide; printed provenance does
not imply retail launch date. Prices and transaction-specific QOP changes are
retained separately and do not inflate the configuration count.

The specific two-door Recon EC3/DFT/28Y offering is explicit in retained guides.
It must not be replaced with EC1 by a generic early specification's eTorque
body/trim availability statement. Sahara High Altitude supports EC3, ERG and EXJ;
North Edition supports EC3 only. Do not expand either to every Sahara engine.
Willys Sport and Freedom do not acquire diesel merely because another Sport-family
column offers it.

## Evidence and classification status

Full source URLs, actual PDF SHA-256 hashes, printed issue/reissue dates, page
counts and archive origins are in [the inventory](source_revision_inventory.json)
and its CSV counterpart. Raw PDFs are retained unchanged in `source_pdfs/`.
`evidence/*.text.json` contains derived pypdf layout extraction with the original
PDF hash; `evidence/powertrain_table_excerpts.json` and `evidence_index.json` bind
individual tables. Selected critical January/March/April table renderings were
visually reviewed; derived images and hashes are retained in the visual index.
A derived extraction/image hash is never represented as an original PDF hash.

The manufacturer-hosted US MY2020 specifications PDF is retained with hash
`sha256:8ca6c22b9af4a87f33700b3a3455fa3fae9ea5799218f232cbbb1b31eabf8354`.
The retained February 6 FCA High Altitude press release corroborates marketed
edition identity. The [engine assessment](ENGINE_CLASSIFICATION_REVIEW.md)
distinguishes manufacturer assertions, code/family joins and unapproved conclusions.

Aspiration for ERC/ERG and electrification `none` for ERC/EC1/EXJ remain proposed,
unapproved classifications affecting 43 rows. ESS terminology or missing eTorque
words do not prove nonhybrid status. Strengthen applicable hardware/classification
evidence and use the existing bounded human-adjudication workflow. Six EC3 rows
have manufacturer-backed proposed tuples; no executable candidate or evidence
certification is implied. MY2019 approvals do not propagate to MY2020.

## Scope reconciliation

Read-only live database inspection confirms 812 VehicleDefinitions and 2,880
receipts, with no MY2020 JL records and no published JL correspondence covering
MY2020. Existing Generation PK 32 / UUID 38d3c3ac-f825-4406-abb5-c2d12b9129a4
remains the intended subject; no generation resolution/publication is performed.
The five MY2019 mappings are year-bounded and cannot simply be reused.

Compared with the 19 final MY2019 candidates, 11 trim/proposed-powertrain tuple
pairs recur across model years. This continuity count assumes the unapproved
MY2020 proposals and is not an approval or same-year duplicate assessment. Seven
non-Sahara EC3 trim/body offerings from MY2019 are represented by EC1 in the
MY2020 guides; MY2019 Unlimited Moab does not appear in the retained MY2020
union. No MY2019 canonical record, evidence or approval changed.

## Gaps and precise next step

The July two-door link (attachment 199518) could not be downloaded or inspected;
its filename date is not treated as a verified printed date. The additional
February 7 four-door guide (280869) was web-readable but not byte-retained; the
archive's current February link resolves to February 11 (281242). Both have null
original-document hashes and were not used to establish unique rows. The located
manufacturer fact-sheet mirror is similarly web-only context. No source hash or
coverage was invented. June 2020 guides found in search identify MY2021 and are
outside this model-year scope.

The [open questions and next scope](OPEN_QUESTIONS_AND_NEXT_SCOPE.md) recommend
review of exactly 49 offerings and 21 grade/body labels under existing
source-established-grade rules, retaining all historical evidence. After owner
review, authorize candidate construction and bounded adjudication proposal
preparation with unresolved fields left null. Recover the two missing originals
or explicitly accept the retained-source scope limitations. Publication, final
planning and any import require later separate authorization.

## Verification and preservation

The task-used `.venv/bin/python` reports Python 3.13.1, Django 6.0.7 and pypdf
6.16.1. Offline focused checks rehashed all retained guides, reconstructed the
observed cell union, verified code/engine/transmission binding, rejected unknown
suffixes, checked unique proposed structured identities and confirmed no
transmission-only duplicates. Critical table blank-cell and edition bindings were
visually reviewed. Source-only research does not justify a full application test
suite; none is claimed.

Database access used SQLite URI `mode=ro` plus `PRAGMA query_only=ON`. Integrity
and foreign-key checks pass. Before/after database SHA-256 remains
`f0d32327e0d688b56711a572375e4e462a266ebb8fdb250b97965e392dff07ab`.
The live DB intentionally differs from Git's sanitized snapshot; no replacement,
reset, migration, import or backfill occurred. Existing working-tree data and all
MY2019 files remain unchanged. No application, contract, governance or other
tracked file was edited; no staging, commit or push occurred.

Direct shell downloads were blocked for the forum; Python's restored certificate
bundle also rejected TLS verification. TLS checks were not disabled. Public
browser download controls retained the authentic guide bytes. Downloads initially
attempted concurrently within a tab were rejected; acquisition was corrected to
sequential downloads per tab. A diagnostic initially treated the engine descriptor
24V as a QOP and did not recognize the cover's body heading spacing; both were
corrected before artifact generation, with explicit valve-token exclusion and
internal model-code/body consistency checks. These were research extraction
issues, not application defects. Poppler emitted local font-cache warnings, but
selected rendered tables were legible and visually checked. No system settings,
permissions or dependencies were changed.

## Artifact map

- `source_revision_inventory.json` / `.csv`: retained and unretained source scope.
- `source_indexes/archive_links.json`: observed public archive links, not raw HTML.
- `evidence_index.json`, `source_pdfs/`, `evidence/`: authentic sources and extraction lineage.
- `preliminary_factory_offerings.json` / `.csv`: 49 research rows; not Candidate artifacts.
- `revision_comparison.json`, `REVISION_REVIEW.md`: observed dated revision deltas.
- `engine_classification_assessment.json`, `ENGINE_CLASSIFICATION_REVIEW.md`: direct versus proposed values.
- `canonical_and_MY2019_reconciliation.json`: current read-only comparison.
- `OPEN_QUESTIONS_AND_NEXT_SCOPE.md`: decisions and construction recommendation.
- `build_discovery_artifacts.py`: offline discovery builder; exclusive outputs.
- `discovery_validation.json`, `final_verification.json`, `artifact_hashes.json`: focused checks and preservation.
