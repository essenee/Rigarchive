# Completeness and proposed construction scope

Created: 2026-11-08
Status: Proposed — owner approval pending

Reconciliation preserves the exact 74-row discovery union and all 900 positive
QOP observations across 27 guide revisions, the four technical PDFs, 106 powertrain
excerpts, 312 option/package pages and Edmunds comparison. No original artifact
is rewritten. `completeness_reconciliation.json` lists the exact 24 earlier-only
rows and the rows with collapsed manual/automatic alternatives.

Final August guides show 50 rows; the other 24 remain because earlier positive
manufacturer cells establish model-year availability. No final-guide-only filter
or secondary production-end annotation removes them. First/last observed dates
are source observation dates, not inferred build start/end dates.

The positive QOP cells are not 900 VehicleDefinitions. Same-trim ERC DEM/DFT and
23-/24-series alternatives already collapse into one engine identity. No additional
transmission-only duplicate is found among the 74 rows. ERG versus ERC is retained
for the supported mild-hybrid distinction, not merely for engine-code inequality.
No optional Xtreme Recon, roof/door/towing package or alternative axle/transfer-case
choice becomes another baseline. No additional package-only row needs removal.

Technical snapshot differences are scoped rather than forced to override dated
order guides. The union has no two-door diesel, two-door 4xe or two-door 392. EC3
is not offered by a positive retained MY2021 cell. RHD remains a distinct observed
factory variant pending canonical treatment, not an unsupported Cartesian product.

Edmunds corroborates all 25 body/trim labels and all 74 described engine-family
combinations. The comparison is not independent proof of exact code assignment,
all structured classifications or every late ERC automatic pairing. It does not
establish that special-edition discontinuation annotations are factory build dates.
No secondary-only configuration or genuinely unmatched manufacturer family has
been identified in the inspected listings.

## Remaining risks

No indexed guide is missing. The 27 first-post attachments do not prove that no
unindexed or short-lived historical revision existed. A delivered-production census
or full W2 conditional option catalogue has not been established. These are bounded
completeness limitations rather than a known missing supported combination.

RHD retail restriction is not established. Its reference inclusion/public visibility
and canonical steering semantics remain an owner/architecture decision. There is
no new schema, hidden inactive-row workaround or general variant framework here.

## Recommended scope

Approve the 24 consumer body/trim names and preserve all earlier-only rows. The
proposed later construction scope is **73 rows: 23 two-door and 50 four-door**,
across eight model codes. Keep JLUL74/JL21-71 separately preserved and deferred.
The term consumer scope names this task partition; it is not proof that RHD was
ineligible for retail sale. The 73-row scope is retained in proposed_consumer_scope.json,
with source-row hashes and exact original lineage. It is not Candidate 2.1.0.

Request 88 supported derived field decisions for the 70 affected scope rows,
with the one RHD field decision deferred. ECX's three scope rows retain direct
technical support. Candidate construction, approval application, correspondence,
Matrix certification and import planning all require separate authorized tasks.
