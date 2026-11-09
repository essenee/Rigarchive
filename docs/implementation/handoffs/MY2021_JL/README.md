# MY2021 US Wrangler JL factory offering discovery

Created: 2026-11-08
Status: Proposed
Last Updated: 2026-11-08

Research only. No Candidate artifacts, human approvals, correspondence proposals,
Matrix certification, executable import plans or canonical writes were produced.
Accepted ADR-0012, RA-044 and the MY2019/MY2020 workflows remain unchanged.

## Observed manufacturer offering union

**74 provisional configurations: 23 two-door and 51 four-door, across 25 body/trim
variants and six engine codes.** This includes **73 consumer-scope proposals plus
one explicitly flagged Unlimited Sport RHD row requiring an owner identity/scope
decision**. Do not silently exclude it or treat steering position as a consumer
trim without that decision. All 74 remain in the discovery matrix.

| Body style | ERC 3.6 ESS | ERG 3.6 eTorque | EC1 2.0 turbo ESS | EXJ 3.0 diesel | ECX 4xe | ESG 392 | Total |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Two-door | 7 | 8 | 8 | 0 | 0 | 0 | 23 |
| Four-door | 10 | 12 | 13* | 12 | 3 | 1 | 51 |
| Total | 17 | 20 | 21 | 12 | 3 | 1 | 74 |

*Includes the RHD review row. Electrification/aspiration conclusions for ordinary
engines are proposed, not automatically copied from earlier MY approvals.

The primary archive first posts expose 27 PDFs: 13 two-door and 14 four-door.
All were retained unchanged with SHA-256 hashes, internal dates and page counts.
Both start at June 4, 2020 and end at August 6, 2021. There are 106 powertrain-table
excerpts and 900 positive QOP-cell observations. First/last observed dates are
**guide observation dates**, not production boundaries. The September two-door
and December four-door guides together cover the observed union. The final August
guides show only 50 rows; 24 earlier-supported combinations remain in the union.

| Proposed display label | Model code | Engine codes | Rows |
| --- | --- | --- | ---: |
| 80th Anniversary Edition | JLJL72 | EC1, ERG | 2 |
| Freedom | JLJL72 | EC1, ERC, ERG | 3 |
| Islander | JLJL72 | EC1, ERC, ERG | 3 |
| Rubicon | JLJS72 | EC1, ERC, ERG | 3 |
| Sport | JLJL72 | EC1, ERC, ERG | 3 |
| Sport S | JLJL72 | EC1, ERC, ERG | 3 |
| Unlimited 80th Anniversary Edition | JLJL74 | EC1, ERG, EXJ | 3 |
| Unlimited Freedom | JLJL74 | EC1, ERC, ERG, EXJ | 4 |
| Unlimited High Altitude | JLJP74 | EC1, ERG, EXJ | 3 |
| Unlimited High Altitude 4xe | JLXP74 | ECX | 1 |
| Unlimited Islander | JLJL74 | EC1, ERC, ERG, EXJ | 4 |
| Unlimited Rubicon | JLJS74 | EC1, ERC, ERG, EXJ | 4 |
| Unlimited Rubicon 392 | JLJX74 | ESG | 1 |
| Unlimited Rubicon 4xe | JLXS74 | ECX | 1 |
| Unlimited Sahara | JLJP74 | EC1, ERC, ERG, EXJ | 4 |
| Unlimited Sahara 4xe | JLXP74 | ECX | 1 |
| Unlimited Sahara Altitude | JLJP74 | EC1, ERC, ERG, EXJ | 4 |
| Unlimited Sport | JLJL74 | EC1, ERC, ERG, EXJ | 4 |
| Unlimited Sport Altitude | JLJL74 | EC1, ERC, ERG, EXJ | 4 |
| Unlimited Sport RHD | JLUL74 | EC1 | 1 |
| Unlimited Sport S | JLJL74 | EC1, ERC, ERG, EXJ | 4 |
| Unlimited Willys | JLJL74 | EC1, ERC, ERG, EXJ | 4 |
| Unlimited Willys Sport | JLJL74 | EC1, ERC, ERG, EXJ | 4 |
| Willys | JLJL72 | EC1, ERC, ERG | 3 |
| Willys Sport | JLJL72 | EC1, ERC, ERG | 3 |

## Identity and evidence rules

Rows merge transmission/QOP alternatives only within the same documented
body/trim/engine offering. Prefix 23/ERC/DEM and 24/ERC/DFT do not create two
baselines. ERG and ERC are kept as separate provisional powertrains because the
MY2021 manufacturer documents explicitly distinguish eTorque mild-hybrid assist;
engine codes alone are not identity discriminators. 22/EC1/DFT, 25/ERG/DFT,
26/EXJ/DFV, 27/ESG/DFV and 29/ECX/DFY are verified against actual engine segments.
Blank table cells never create offerings. `24V` denotes valves, not a QOP cell.

4xe is documented only in four-door form: JLXP74 Sahara/High Altitude and JLXS74
Rubicon, ECX/DFY. Rubicon 392 is JLJX74, ESG/DFV, not a new Generation/model.
No offered EC3 or other engine code appears in the retained positive availability
cells. All nine model codes and their exact row coverage are in offering_summary.json.

Edmunds corroborates all 25 labels and all 74 described body/trim/engine families.
This does not independently prove engine sales codes, complete RA-044 tuples, or
every revision-level ERC automatic pairing. The comparison uses individual
conventional feature pages and a separate 4xe comparison page. No secondary-only
configuration was identified. See EDMUNDS_COMPARISON.md for limitations.

## Review gates before Candidate construction

- Owner review of the 73 consumer proposals and the separate RHD identity question.
- Review new MY2021 edition normalization, especially High Altitude 4xe. No prior
  approval is silently extended to this model year.
- Prepare bounded human classification proposals if desired: 89 unresolved field
  conclusions across 71 research rows. They remain null in directly supported
  projections; ECX's three rows have all five fields supported.
- Retained guide coverage is complete for the two indexed first-post collections,
  not proof that every historic manufacturer revision or delivered vehicle exists
  in those archives. No currently indexed PDF is missing.

## Files

- source_revision_inventory.json / .csv: 27 original-guide URLs, dates, hashes and pages.
- source_pdfs/: unchanged 27 guide PDFs and four publisher-hosted technical PDFs.
- supplemental_source_inventory.json: technical-source applicability and hashes.
- evidence_index.json and evidence/: 106 page excerpts and PDF-derived layout text.
- positive_package_observations.json: all 900 engine/transmission/QOP observations.
- factory_package_availability_excerpts.json: raw package, option and group-detail pages.
- package_and_hardware_excerpt_index.json: edition, RHD, hardware and Recon references.
- preliminary_factory_offerings.json / .csv: 74 nonexecutable research rows.
- revision_comparison.json and REVISION_REVIEW.md: revision-level additions/omissions.
- engine_classification_assessment.json and ENGINE_CLASSIFICATION_REVIEW.md.
- TRIM_EDITION_REVIEW.md; EDMUNDS_COMPARISON.md / edmunds_comparison.json.
- MISSING_SOURCES_AND_NEXT_SCOPE.md; canonical_reconciliation.json.
- discovery_validation.json, verification_results.txt and artifact_hashes.json.

Verification uses `.venv/bin/python`, offline retained-source checks and read-only
SQLite inspection. The development database is preserved byte-for-byte. No commit
or push. Candidate construction requires a separate owner-approved task.
