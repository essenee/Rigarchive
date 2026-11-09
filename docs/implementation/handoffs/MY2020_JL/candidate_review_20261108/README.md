# MY2020 US Wrangler JL candidate construction review

Created: 2026-11-08
Status: Proposed

This separate review preserves the discovery handoff unchanged. The current entry
points are `candidate_index.json`, `reviewed_offering_matrix.json`,
`classification_proposal_index.json`, `edmunds_comparison.json`,
`trim_review.json`, `evidence_index.json` and `validation_results.json`.
This is an offering review, not a certified Matrix or import plan.

## Constructed scope

49 Candidate 2.1.0 artifacts: 15 two-door and 34 Unlimited, across 21 body/trim
variants. Engine counts are ERC 17, ERG 3, EC1 15, EC3 6 and EXJ 8. No rows were
excluded or added. Transmission alternatives do not create extra candidates.
Every candidate retains its positive revision-level guide evidence, exact model
code, QOP associations and a March 3 primary table. Headings independently
establish US market, MY2020 and body/model applicability. Generation is not
selected by caller context; source model-code evidence is retained for later
correspondence review. No correspondence was proposed or published.

The five earlier-only combinations remain: Black and Tan ERC/EC1 in both bodies,
and Unlimited Rubicon EXJ. April omissions do not establish cancellation dates.
Manufacturer editions are evaluated as marketed grade columns with scoped QOP
availability, not arbitrary accessory/option permutations. See `trim_review.json`.
Unlimited **Sahara High Altitude** is retained as the discovery normalization;
three candidates require review of that label versus marketed **Unlimited High
Altitude**. No candidate label was silently changed to match Edmunds.

## Classifications requiring human decisions

43 separate **proposed**, unapproved Adjudication 1.1 records bind exact candidate
semantic hashes, immutable source references and candidate-specific applicability.
No proposal was approved or applied. All unresolved candidate fields remain null.

| Engine | Candidates | Proposed fields | Evidence assessment |
|---|---:|---|---|
| ERC | 17 | naturally_aspirated; none | Moderate-confidence bounded family/hardware conclusions; fresh MY2020 sign-off required |
| ERG | 3 | naturally_aspirated | Moderate-confidence Pentastar induction continuity conclusion; sign-off required |
| EC1 | 15 | none | Moderate-confidence non-MGU/eTorque variant association; sign-off required |
| EXJ | 8 | none | Low-confidence unsupported proposal; positive applicable diesel hardware/nonhybrid evidence still required |

There are 60 field proposals: 20 aspiration and 40 electrification. The 52 ERC,
ERG and EC1 claims are supported **proposed engineering conclusions**, not direct
manufacturer assertions or approved facts. Their code/family/market-year joins
remain explicit review limitations. An owner can reject those joins. EXJ's eight
claims cannot become eligible merely by approving an unsupported proposal.

Directly sourced fields use guide engine descriptors and exact code associations;
US Mopar manual printed page282 explicitly identifies gasoline for both 2.0 and
3.6 families. Printed284–285 distinguishes without-MGU and with-MGU 2.0 hardware,
MGU and battery coolant. Those facts support a proposed architectural association,
not an explicit declaration that EC1/ESS is nonhybrid. MY2019 hardware/catalog,
Pentastar, regulatory and recall material is reused only as contextual evidence;
its original source applicability and cautions remain. No MY2019 human declaration
or approval is used as evidence or extended to MY2020. Neither ESS nor missing
hybrid wording alone establishes `none`. US technical specifications govern model
layout; their early generic eTorque availability does not override explicit later
Recon 28Y evidence. All six EC3 candidates have five complete fields; the other
43 remain incomplete and cannot proceed as complete canonical identities.

## Edmunds cross-check

All 21 US body/trim listings were inspected, expanding Engine, Mechanical Options
and Packages on their individual specification pages. Edmunds puts Wrangler and
Unlimited styles under one 2020 Wrangler model URL. Exact URLs and observed engine
and QOP facts are retained in `evidence/edmunds_observed_identity_facts.json`;
`edmunds_comparison.json` maps each of the 49 manufacturer combinations.
The retained snapshot is a manually transcribed secondary observation, **not raw
HTML**. Its computed hash must not be described as Edmunds original-page bytes.

- **48 combinations corroborated**, using base/optional engines and scoped QOPs.
- **No additional Edmunds-only body/trim/engine combination observed** among these
  inspected listings. Transmission-specific versions are collapsed.
- **One manufacturer-supported combination absent:** Unlimited Rubicon EXJ diesel.
  Its Edmunds page lists the 2.0 turbo option and 23R/22R/24R, without diesel/26R.
  Earlier retained guides explicitly support 26R; April also omits it. Retain the
  model-year union; investigate revision/availability timing before scope closure.
- Edmunds calls the High Altitude grade **Unlimited High Altitude**, omitting
  Sahara from the discovery proposal. All three engines are corroborated there.
- The Sahara Altitude page labels its diesel 26L package **Unlimited Sport
  Altitude**. It separately lists the diesel mechanical option. Record this as a
  secondary naming/attribution inconsistency; model codes distinguish the two
  manufacturer families even though both use suffix L.
- Willys Sport/Willys, Freedom, Black and Tan, Recon, North Edition and Altitude
  variants have separate Edmunds styles while their QOPs also appear as packages.
  This corroborates marketing identity but cannot alone settle canonical grade
  taxonomy. No cross-product of parent-trim engines was introduced.

Edmunds did not add or remove candidates, establish engine codes independently,
or supply direct-source assertions in the candidates.

## Missing archives and next review

The two-door July2 archive and extra four-door February7 revision remain
unretained. None of these 49 rows depends exclusively on either missing PDF:
the retained March3 pair independently documents all49. Thus no current row loses
its positive offering proof. The missing documents could establish additional
short-lived offerings, revision boundaries or corroboration, so universal
model-year completeness is not certified. They cannot currently resolve EXJ's
nonhybrid classification; their possible substantive contents are unknown.

Next: owner reviews the 52 supported bounded classification proposals and the
High Altitude normalization, while applicable positive EXJ evidence and the
Rubicon diesel/revision discrepancy are investigated. Any approval must identify
exact proposal/candidate hashes and scope. No publication, certification, planning
or import is authorized by this review.

## Validation and preservation

All49 candidates and all retained SourceAssertionSets pass contract validation,
actual retained-source hash checks and serialization round trips. All43 proposal
records pass Adjudication1.1 structural/lineage validation and fail the explicit
approval gate as expected. Uniqueness is checked on body/grade/engine proposals;
it is not a claim that 43 unresolved structured identities are import-eligible.
Source revisions/mirrors are not independent manufacturers; repeating FCA guide
revisions is lineage/history support, not independent corroboration.

Focused isolated tests: 67 classification, structured-powertrain and generation
projection tests passed. A further 29 serialization/construction tests passed (96 total). Final
read-only DB/preservation verification are retained in `verification_report.json`.
The approved `.venv/bin/python` was used; no dependency or environment changes.
No application/contracts/governance edits, canonical writes, imports, migrations,
backfills, correspondence publications, commits or pushes were performed.
