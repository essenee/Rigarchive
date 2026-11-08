# MY2019 ERC classification proposals for human review

Created: 2026-11-08
Status: Proposed

**The policy adjustment is authorized. The classifications below are not approved.**
Ten adjudication 1.1 proposals cover the exact retained ERC candidates: Sport,
Sport S and Rubicon two-door; Unlimited Sport, Sport S, Sport Altitude, Sahara,
Sahara Altitude, Moab and Rubicon four-door. Each proposes:

| Classification | Proposed value | Confidence | Status |
| --- | --- | --- | --- |
| Engine aspiration | `naturally_aspirated` | Moderate | Human sign-off required |
| Electrification | `none` | Moderate | Human sign-off required |

These are evidence-backed engineering conclusions, **not direct manufacturer
assertions**. `review.csv` and `index.json` list all ten candidate references,
proposal paths and actual content hashes. Each `proposals/*.adjudication.json`
binds the exact original candidate digest/path, supporting document hashes,
qualified source references, reasoning, applicability, limitations and confidence.
All decisions are `proposed_classifications`, attributed to
`pending_human_signoff`. No completed real candidate revision was generated.

## Reasoning for review

**Naturally aspirated.** The MY19 Australian technical guide explicitly identifies
the 3.6L Pentastar ESS induction. US guide/specification lineage identifies the
target ERC offering and its marketed engine dimensions and configurations. The
proposal asks the human reviewer to accept continuity of the induction architecture
across those regional implementations, considered alongside manufacturer family
information. It does not claim that matching names, codes or dimensions alone
proves equivalence. A direct US ERC induction statement remains unavailable.

**Nonhybrid.** The US/Canada MY2019 Mopar manual's hardware explanation
distinguishes conventional ESS starting equipment from an eTorque motor-generator,
hybrid battery, recovered energy and launch assistance. Positive without-eTorque
alternator applications, separate ERG BSG catalog entries, the US ERC offering
lineage and contemporaneous MY2020 V6 eTorque powertrain material jointly support
the proposed conventional ERC interpretation. No one of ESS terminology, missing
eTorque wording, family membership or introduction chronology is used as proof.

The inference is restricted to these ten ERC offerings, not every MY2019 3.6L
Wrangler. Manufacturer/regulatory records also describe MY2019 3.6L hybrid/eTorque
applications; actual copies of the CARB HEV order and retrospective FCA Y40
bulletin are retained in `evidence/`. They do not expressly classify the targeted
ERC offering as hybrid, but their broader scope must remain visible to the human
reviewer. The proposal does not assert that a MY2019 hybrid was impossible, or
that engine-code differences alone establish a mechanical distinction.

## Sources and limitations

`evidence/erc_research_dossier.json` records the exact URLs, titles, pages,
explicit observations, derived interpretation and limitations, including:

- FCA Australia MY19 JL technical guide, page 10 induction, pages 11–12 regional
  codes/applicability: explicit Australian fact; US transfer is derived.
- Official Mopar MY2019 New Wrangler User Guide, 19JL-926-AA, printed pages
  163/166: actual hardware distinction; not an exhaustive ERC application list.
- US MY2019 two-door ordering guide, reissued October 4, 2018, pages 2/5, and
  the already retained June four-door guide pages 2/5/9: actual ERC offering scope.
- JeepPartsDeal alternator catalog: authentic retained retailer HTML, with
  positive without-eTorque applications and separate ERG BSG entry. It is not
  represented as an authenticated FCA-issued catalog.
- FCA Pentastar factsheet, page 1: authentic retained manufacturer bytes,
  family availability and distinct hybrid/eTorque applications.
- Manufacturer-authored 2020 Wrangler Fact Sheet, August 31, 2019, mirrored
  web-cached text: historical V6 eTorque menu context. Mirror download returned
  HTTP 403; no original PDF hash or independent authenticity verification is
  claimed. Contemporaneous secondary reporting is labeled as corroborating
  historical context, not decisive manufacturer proof.

The dossier is honestly labeled research synthesis, not a manufactured source
document. Its hash and the actual supporting bytes are bound by
`evidence/supporting_documents.json`. Previously retained evidence is referenced
without overwriting or duplicating it. No source assertion was rewritten to say
`naturally_aspirated`, `none` or `nonhybrid` merely to satisfy a parser.

## Approval procedure and subsequent gates

The existing `adjudicate_canonical_import` command now has a classification review
mode. After human authorization of an exact proposal, supply its path using
`--classification-review`, a declared human `--operator`, and distinct new
`--output` / `--candidate-output` paths. The command displays the proposal and
requires exact interactive `APPROVE CLASSIFICATIONS` confirmation. It writes a
separate approved finding and candidate revision only after confirmation. Do not
run it as if this proposal-preparation authorization approved the facts.

The revised candidate preserves the source evidence and adds a structured human
declaration with reviewer/time, semantic adjudication hash and raw artifact hash.
It cannot be consumed as direct manufacturer wording. The ordinary planner,
Matrix 2.1, manifest and execution receipts bind and revalidate that lineage.
An approval record is a declared human action, not a cryptographic identity proof.

Classification sign-off does not authorize or perform generation-correspondence
publication, canonical planning/execution, backfill or any other database write.
Generation and exact import authorization remain separate gates. Unsupported,
materially contradictory or unapproved conclusions remain blocked.

## Current outcome

- Ten structurally valid proposals, twenty proposed decisions, zero fact approvals.
- All ten existing ERC candidates remain unchanged with null aspiration and
  electrification. No live import plans or completed candidate revisions created.
- Original director-review artifacts and database bytes preserved; hashes are
  recorded in `preservation.json`.
- Implementation and focused verification are recorded in
  [the task report](../../../../tasks/MY2019-erc-classification-adjudication.md).
