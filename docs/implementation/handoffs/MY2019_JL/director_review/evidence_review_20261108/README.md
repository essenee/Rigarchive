# MY2019 Wrangler JL evidence and import-readiness review

Created: 2026-11-08
Status: Draft

**Not ready for import authorization.** All 19 candidates are contract-valid; zero
are currently eligible, 19 are blocked, and no canonical or intra-set identity
conflict was found. No final executable Matrix 2.1 or resolution 1.1 plan exists.

## Four evidence gates

| Gate | Result | Remaining requirement |
| --- | --- | --- |
| A: ERC | Gasoline established. Marketed 3.6L/V6 and ESS offering retained. | Explicit applicable naturally aspirated and nonhybrid classifications. Both fields remain null on all 10 ERC candidates. ESS does not establish either classification. |
| B: EC3 | Gasoline established for all 9 EC3 candidates. Existing applicable turbo/eTorque evidence remains separately bound. | None for the five-field candidate tuple. eTorque remains mild_hybrid, separate from turbocharged aspiration. |
| C: two-door drive | Explicit MY2019 manufacturer model-wide four-wheel-drive statement bound to all 6 two-door candidates. | None for generic 4WD. No four-door-only equipment statement was generalized to two-door vehicles. |
| D: generation | Existing active JL PK 32 / UUID `38d3c3ac-f825-4406-abb5-c2d12b9129a4` and five manufacturer model-code mappings reviewed; five fresh 2019-only review proposals validate. | Human review and separately authorized correspondence publication. None was published. All 19 live plans report missing reviewed correspondence. |

The accepted 19-offering inventory remains unchanged: 6 two-door, 13 four-door;
10 ERC, 9 EC3. Marketed Altitude and Moab identities remain separate. No EC3 Moab,
transmission permutations, factory-body schema or additional canonical candidates
were introduced.

## Evidence retained

The existing 19 Candidate 2.1.0 artifacts and 32 SourceAssertionSets in
`../compact_evidence_revision_2/` all passed fresh validation. Their original bytes
were preserved. The new `candidates/` revision adds only supported facts and shared
correspondence evidence; it does not replace prior revisions.

- `evidence/mopar_2019_fuel_selected_facts.json`: selected fuel facts from the
  official Mopar MY2019 New Wrangler User Guide, edition 19JL-926-AA First Edition,
  printed page 246 / PDF page 248. Both named-engine subsections explicitly use
  gasoline. The printed cover establishes US and Canadian applicability, despite
  the download URL containing `/en-ca/`. The page was rendered and inspected.
- `evidence/jeep_2019_specification_selected_facts.json`: selected layout and body
  applicability facts from the manufacturer MY2019 Wrangler Specifications,
  printed page 1, also rendered and inspected. The layout specifies four-wheel
  drive; the same page explicitly includes both body styles. Pages 1–2 identify
  the two engines as standard/available across all models. No publication day
  was invented. Directly downloaded bytes identify MY2019; the web viewer's
  rewrite to a MY2018 specification was rejected as evidence for this model year.

These small, honestly labeled representations are hashed as retained JSON, not as
PDFs. Original downloaded PDFs were inspected in temporary storage and are not
downstream evidence dependencies. The prior compact-evidence policy permits this
approach. The existing manufacturer offering inventory establishes the actual
trim/engine combinations; general specifications do not generate combinations.
The new first-party documents share manufacturer lineage and are not counted as
independent publishers or multiplied corroboration.

The June two-door order-guide text was available through the web viewer, but
direct download returned HTTP 403 and the screenshot route failed. It was not
promoted into a newly certified retained table. Gate C instead uses the directly
retrieved, visually checked model-wide manufacturer specification. No original
two-door PDF bytes or hash are fabricated.

Narrow searches for ERC aspiration/nonhybrid facts found no sufficiently scoped
admissible retained assertion. Dealer listings, another market's vehicle,
unconfirmed future-model reports, and absence of turbo/eTorque words were not
used to fill those values. The exact remaining evidence request is a source-linked
manufacturer or otherwise admissible assertion establishing naturally aspirated
and nonhybrid status for the MY2019 US ERC offering. One properly applicable
source can cover all ten rows; ten duplicate documents are unnecessary.

## Correspondence, peers and proof

`correspondence_proposals/` contains five closed-schema review 1.0 artifacts,
including their real content hashes and explicit implementation-agent attribution.
They relate the director-accepted MY2019 JL inventory's exact manufacturer model
codes to the same JL target as the verified, published MY2018 manufacturer-code
reviews. The old reviews' hashes and retained evidence bytes were checked; no
2018 review was reused as a 2019 publication. New proposal findings remain subject
to human review and publication authorization.

One common selector SourceAssertionSet per model code binds the identical retained
inventory bytes and is included in every affected candidate. This allows each
proposal's exact evidence document to be present in every relevant candidate;
per-row assertion-set identities are not silently treated as interchangeable.
The common selector is the same research lineage, not another independent source.
No generation identity was removed to enable year-range fallback.

`live_peer_assessment.json` records a read-only current database assessment. The
JL MY2019 namespace is empty, including inactive records and all markets. The
existing 15 JL definitions are MY2018, outside the MY2019 identity scope. No
preexisting MY2019 target, duplicate or conflicting representation was found.

`engine_proof_assessment.json` contains **nine successful standalone engine proof
2.0 sub-assessments** for the complete EC3 tuples against an empty relevant peer
set. The ten ERC assessments reject incomplete tuples. These standalone results
do not constitute full resolution 1.1 plans: live generation resolution is blocked
for all rows by unpublished correspondence. They must be refreshed after any
publication, evidence or canonical-state change.

`director_review_19_rows_BLOCKED.csv` and `candidate_review.json` give row-level
results. `matrix_readiness.json` records why no final Matrix 2.1 was generated.
The closed Matrix 2.1 schema requires complete target tuples and executable row
actions; it cannot honestly encode these 19 blocked rows as a final import scope.
No nonstandard substitute was presented as a valid matrix.

## Verification and preservation

- Interpreter: repository `.venv/bin/python`, Python 3.13.1, Django 6.0.7,
  pypdf 6.16.1, as explicitly directed by this task. Existing environment metadata
  has `include-system-site-packages = true`; the environment was not rebuilt or
  changed. Older repository interpreter instructions remain unchanged.
- `pip check`: no broken requirements.
- Django system check: zero issues with `RIGARCHIVE_TEST_DB_PATH=:memory:`.
- Focused test selection: **89 passed**, zero failures/errors. Modules:
  `test_structured_powertrain`, `test_ingestion_serialization`,
  `test_candidate_construction`, `test_generation_projection_completeness`, and
  `test_generation_trim_matrix`. Tests used Django's isolated test database;
  synthetic evidence/media fixtures use temporary roots. No development migration
  was run. The full suite was not run.
- Fresh artifact validation: 19 original candidates, 32 original assertion sets,
  19 revised candidates, 7 shared new assertion sets, 5 correspondence proposals;
  qualified source bytes, round trips and five-field completeness were checked.
  A supplementary exact source-projection comparison initially failed because
  its filesystem glob supplied shared documents in a different order. Repeating
  it with the recorded construction order passed for all 19 serialized artifacts;
  no artifact or application code change was needed.
- Live queries used SQLite URI `mode=ro` plus `PRAGMA query_only=ON`.
  The database remains 793 VehicleDefinitions and 2,856 receipts. SHA-256 before
  and after is `b045601a33811b44a443b7c0cc78ce916e9af476cb3c5f4c5b94dc2fdf18e26f`.
- `preservation.json` records matching hashes for all prior director-review files.
  Prior evidence, candidates, backups, application code, accepted architecture,
  contracts and Git changes were preserved. No canonical writes, publication,
  imports, backfill, W2 work, staging, commit or push occurred.

The task-local `../review_20261108.py` records the artifact construction and
validation procedure and refuses to overwrite this output revision. No
application implementation defect was identified. Completion is limited by the
two missing ERC facts and the explicitly separate correspondence publication gate.
