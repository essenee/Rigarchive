# MY2021 JL approval application report

Created: 2026-11-09
Status: Accepted — exact classification application complete; final identity gate separately incomplete

Authority is the owner's explicit approval of the original MY2021 US owner-review
table and the current corrected prerequisite-order task. Historical review files
were not edited to manufacture approval status. The table's SHA-256 and exact
decision IDs are retained in `authorization.json`.

| Engine | Affected candidates | Field decisions | Approved values |
| --- | ---: | ---: | --- |
| ERC | 17 | 34 | naturally_aspirated; none |
| ERG | 20 | 20 | naturally_aspirated |
| EC1 | 20 | 20 | none |
| EXJ | 12 | 12 | none |
| ESG | 1 | 2 | naturally_aspirated; none |
| Total | 70 | 88 | Exact reviewed scope only |

All 73 bases passed contract, evidence-byte and serialization verification before
the first classification application. All approved fields were null in those
bases. The existing `adjudicate_canonical_import --classification-review` CLI was
invoked with `--operator project_owner` and the explicitly authorized
`APPROVE CLASSIFICATIONS` response, using `RIGARCHIVE_TEST_DB_PATH=:memory:`.
Seventy approved adjudication 1.1 artifacts and seventy separate candidate
revisions were produced. The 88 individual decision records identify their
contract envelope, claim, base digest, current digest and approval authority.

Approved records retain the proposal's exact evidence anchors. The CLI changed
only decision status, reviewer label, timestamp and adjudication hash. Every
claim retains moderate confidence, the reviewed derived reasoning/limitations,
source references and exact candidate/engine/model/QOP applicability. Existing
direct fields were unchanged. Human assertions retain `human_adjudicated`
provenance and are validated through the existing approved-projection consumer.

No decision was duplicated, extended to another year/market/engine or applied to
Sport RHD. CLASS-075 / JL21-71 remains deferred. Three ECX candidates retain the
directly supported 2L / 4-cylinder / turbocharged / gasoline / plug-in-hybrid tuple
and no human classification document. ERC/ERG identity distinctions and temporal
guide evidence remain unchanged; transmission/package differences do not add rows.

The application index, current index, 88 decision records, 70 approved contract
artifacts, CLI logs and superseded-base index provide the complete audit trail.
Evidence hashes, approved projections, uniqueness and serialization checks passed.
Original bases, all discovery/review artifacts and live database bytes are preserved.

**Separate final-validation limitation:** JL21-70's unapproved fuel-validation
gap remains null. It is not an omitted one of the 88 decisions and does not
invalidate application of the two approved ESG classifications. It prevents
claiming 73 complete five-field identities or overall task completion.
