# MY2020 JL evidence resolution and owner adjudication review

Created: 2026-11-08
Status: Proposed

All **49 configurations are retained**: 15 two-door, 34 Unlimited, 21 body/trim
variants. This review prepares decisions; no classification approval has been
applied. Six EC3 candidates remain directly complete. All unapproved fields in
the other 43 remain null, including EXJ electrification.

Use this directory's `candidate_index.json` and `classification_proposal_index.json`
as the current review selection. The earlier discovery and construction directories
are preserved historical checkpoints. There are **60 field decisions affecting
43 existing candidates**, not 60 new vehicles. No new configuration was added.

## Owner approval table

| Engine | Proposed field | Proposed value | Candidates | Confidence | Principal limitation |
|---|---|---|---:|---|---|
| ERC | engine_aspiration | naturally_aspirated | 17 | Moderate | Pentastar induction continuity across source market/year remains derived; no explicit US MY2020 ERC induction statement |
| ERC | electrification_type | none | 17 | Moderate | Positive conventional ESS versus motor-generator architecture; exact offered ERC application is an engineering join, not ESS wording alone |
| ERG | engine_aspiration | naturally_aspirated | 3 | Moderate | Shared Pentastar induction interpretation does not automatically follow from eTorque/code equality; fresh scoped approval required |
| EC1 | electrification_type | none | 15 | Moderate | 2.0 without-MGU hardware and separate EC3 eTorque offering support a derived code-to-hardware association |
| EXJ | electrification_type | none | 8 | Moderate | Secondary alternator observation plus OEM architecture comparison supports inference; no explicit OEM EXJ nonhybrid declaration |

Machine-readable rows, exact affected candidate references and limitations are in
`owner_approval_table.json` and `.csv`. Exact proposed Adjudication1.1 hashes,
predecessors and current candidate digests are in `classification_proposal_index.json`.
All 43 records retain `proposed_classifications` / `pending_human_signoff`.
The explicit approved-only guard rejects every proposal. Nothing was applied.

## EXJ evidence finding

The eight earlier unsupported `none` proposals have separate evidence-review
revisions, now assessed as **supported derived conclusions for human review**.
They do not claim a direct manufacturer classification.

1. Original US MY2020 guides bind EXJ to the 3.0L V6 turbo diesel, DFV automatic,
   model family, marketed grade and exact positive QOP cells.
2. Ron Sessions' January8 J.D. Power MY2020 US EcoDiesel technical review explicitly
   describes an alternator moved higher on the engine. This is an independently
   authored secondary observation, not an OEM service specification. Its broad
   statement about all four-door trims does not override guide-specific availability.
3. The retained official MY2020 Mopar manual, PDF180/printed178 and PDF182/printed180,
   positively distinguishes heavy-duty ESS starting equipment and enhanced battery
   from eTorque motor-generator, extra hybrid battery, energy recovery and launch
   assistance. This improves the earlier proposals' hardware evidence, which had
   emphasized coolant tables. The manual covers gasoline families and does not
   expressly identify EXJ. It is an architecture comparison, not diesel applicability
   proof by itself.
4. The manufacturer blog's searchable archived text corroborates Sport/Sahara/Rubicon
   EcoDiesel and ESS. Its live site reports a stopped web app; original HTML is not
   retained. The cached observation is context only, not executable primary proof.

The conclusion combines a positively observed diesel charging component, exact
manufacturer offering lineage and an explicit manufacturer architecture contrast.
Neither an alternator alone, ESS terminology, nor absent eTorque wording proves
nonhybrid. An alternator can coexist with hybrid architectures. Accepting the
bounded conventional-system association is the proposed human engineering decision.
The evidence does not assert an OEM diesel starter part number or wiring topology.
Do not propagate to other model years, markets, engines, trims or configurations.

The other 52 proposals retain their previously proposed values and moderate
confidence. Their original evidence, limitations and source scopes remain.
The same newly retained manual hardware assertions are added to support a consistent
ESS/eTorque distinction; aspiration remains a separate induction conclusion.
MY2019 contextual evidence is not a transferred human approval. Regulatory/recall
cautions about ERG hybrid applications remain in the supporting records.

## High Altitude trim and naming

The three current review revisions use **Unlimited High Altitude**. Originals are
untouched. `naming_revisions.json` binds each previous/current candidate hash and
path. The evidence retains the Sahara model family **JLJP74** and exact 25N/28N/26N
ordering associations. Original raw tables, model headings and source strings are
unchanged. Only display normalization, supporting marketed-edition evidence and
explicit revision lineage were added; structured powertrain values are identical.

Under ADR0005 as narrowly extended by ADR0010, a QOP code or optional equipment
bundle alone is insufficient grade proof. Here the February6 manufacturer-issued
FCA release markets High Altitude as a named Wrangler model/edition; later US guides
provide its dedicated Sahara-family availability column and distinct order baseline.
Together these support retaining the marketed edition as a separate trim rather
than projecting arbitrary option permutations into VehicleDefinitions. The family
relationship does not require putting Sahara in the normalized marketed display
name. Edmunds independently lists Unlimited High Altitude with the same three
engine/QOP alternatives. It corroborates, rather than governs, that finding.

The proposed owner decision is to retain this distinct grade and accept the
normalized label for all three candidates. Naming preparation is authorized by
the current task; canonical grade promotion and classification approval are not.
Two revised classification proposals (ERG aspiration and EXJ electrification)
are rebound to the new candidate digests. The EC3 naming revision needs no new
classification proposal. The other 46 candidates remain selected from their
original unchanged artifacts.

## February7 guide and Rubicon diesel

The original **23-page February7 US MY2020 four-door PDF was recovered** through
the public archive link in the Recon discussion. Its original-byte SHA256 is
recorded in `source_inventory.json`; full layout extraction and page renders are
retained separately. Cover identifies issue July2 2019/reissue February7 2020,
United States, MY2020 and model codes JLJL74/JLJP74/JLJS74. FCA copyright/dealer
footer, internal dates and scoped tables support authenticity as an archived
manufacturer-issued document; no digital-signature claim is made.

All three offering tables, PDF2/7/11, were visually inspected. The recovered guide
contains **31 unique four-door combinations**, all already in the retained union.
It has no additional configuration. The three High Altitude combinations are not
in this earlier revision; later retained guides supply them. The 15 two-door rows
are outside this guide's body scope, not absent offerings. Full49-row comparison,
positive QOP cells and page references are in `february_guide_reconciliation.json`.
No earlier-only offerings were removed.

PDF11 explicitly offers **JLJS74 + EXJ + DFV + 26R** for Unlimited Rubicon diesel.
This agrees with retained January/March guide evidence and manufacturer blog
availability. Edmunds' inspected Unlimited Rubicon page omits the diesel engine
and26R. That is a secondary listing coverage discrepancy, not an identity conflict
or exclusion basis. April's omission remains a revision observation; neither it
nor Edmunds establishes cancellation dates or absence from the MY union.

One original-byte archive gap remains: the two-door July2 guide. It is not needed
to support any of these49 existing positive offerings, but exhaustive coverage of
every transient revision/possible extra offering is still not certified.

## Source retention and audit

`source_inventory.json` distinguishes original PDF/HTML hashes from hashes of
retained browser/search observations. The manual and FCA High Altitude HTML were
already retained and reused by exact path/hash. J.D. Power direct retrieval returned
403; a browser-rendered exact alternator excerpt and metadata are retained as
`jdpower_browser_observation.json`. That observation's hash is not the original
HTML hash. Its SourceAssertionSet explicitly identifies secondary/manual extraction.
The stopped Stellantis blog has no invented original hash; its cached excerpts
remain context. Edmunds' existing21-style observation snapshot is reused unchanged.
No mirrors/revisions of FCA publications are counted as independent manufacturers.

## Verification and remaining decisions

Candidate contracts, all revised proposal contracts, retained source bytes,
qualified assertion references and candidate bindings pass validation. Naming
revisions and SourceAssertionSets round-trip through existing serializers.
The 49-row scope and 60 field-decision count are unchanged. Focused isolated tests
and final preservation checks are recorded in `final_verification.json`.

Owner decisions remain: the five classification groups above, bounded to their
exact proposal hashes/candidate references, and High Altitude grade/name treatment.
All are ready for human adjudication review, including EXJ as an explicitly derived
moderate-confidence conclusion. A reviewer may decline any evidentiary join; no
rule was relaxed and no unsupported inference was silently inserted into a candidate.
No correspondence publication, Matrix certification, canonical planning/import,
backfill, application/contract/governance edit, migration, commit or push occurred.
