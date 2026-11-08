# MY2019 ERC supplied-source assessment

Created: 2026-11-08
Status: Draft

**Zero of the ten US MY2019 ERC candidates can be completed from the supplied
evidence chain as currently verified.** Their aspiration and electrification
fields remain null. No candidate revision, generation publication or import plan
was created. This report supersedes no previous evidence or candidate artifact.

## Sources and findings

`source_review.json` records every exact supplied URL, publisher, title, page or
section, retrieval result, applicability finding and retained-source hash.

1. **FCA Australia MY19 JL Buyer's Guide, January 2019**, printed pages 10–12.
   Page 10 expressly classifies its 3.6L Pentastar ESS as naturally aspirated.
   Page 12 identifies FCA Australia and Australian applicability. Its model codes
   are JLUL/JLUP/JLUS, rather than the US JLJL/JLJP/JLJS codes. No ERC identifier
   was found. The finding is explicit for those Australian applications; transfer
   to all US ERC offerings is an unverified cross-market correspondence. Matching
   family names, liters and cylinders is not enough under ADR-0005/RA-044.
   Cached PDF text was inspected; direct retrieval returned HTTP 403. No original
   PDF bytes or hash are claimed for this source.
2. **Supplied US owner's-manual URL** returned HTTP 403 through both retrieval
   routes. Its exact bytes/edition could not be verified. The already retrieved
   **official Mopar 2019 New Wrangler User Guide, 19JL-926-AA First Edition**,
   printed pages 163 and 166, independently contains the described hardware
   distinction. Its cover establishes US/Canada scope. Conventional ESS uses
   upgraded starting hardware; eTorque uses a motor-generator, additional hybrid
   battery, recovered energy and launch assistance. These are conditional
   equipment sections, not an exhaustive per-ERC application table. Their text
   does not itself establish that every ERC offering has the conventional
   architecture. A compact selected-facts representation is retained and hashed;
   its hash is explicitly separate from the observed original PDF hash.
3. **FCA US MY2019 two-door code guide**, issued September 11 and reissued
   October 4, 2018, printed pages 1, 2 and 5. Cached source text explicitly binds
   ERC to the US two-door 3.6L V6 ESS offering for Sport, Sport S and Rubicon.
   The seven four-door ERC offerings already have the retained June guide
   linkage. This confirms the offered engine-code association; neither guide
   establishes the Australian engine's equivalence or a nonhybrid classification.
   Direct original retrieval returned HTTP 403; no PDF hash was invented.
4. **JeepPartsDeal MY2019 Wrangler alternator catalog.** Original HTTPS HTML,
   including embedded catalog data, is retained unchanged and hashed. Several
   conventional alternators explicitly specify without-eTorque 3.6L applications.
   The same page also lists an ERG 3.6L belt-driven starter-generator application
   for both body types. No exact ERC token appears. Thus the page positively
   supports a without-eTorque subset, but cannot establish that all MY2019 3.6L
   configurations or all ten ERC offerings belong to it. It is retailer-hosted
   OE parts data; it was not represented as an authenticated FCA-issued catalog.
5. **FCA Pentastar V-6 factsheet**, page 1, Availability and Production Sites.
   Authentic downloaded PDF bytes are retained and hashed. It lists MY2019
   Wrangler family availability and separately describes eTorque/hybrid family
   applications. It does not state that every family variant has one induction
   or electrification classification, or bridge the Australian variant to US ERC.

None of these limitations means the proposed classifications are false. They
mean this chain does not establish their exact required applicability. No code,
descriptor, regional similarity or omission was substituted for that evidence.

## Accepted contract versus implementation

RA-044 section 3 permits `none` through a **verified source rule** grounded in
applicable manufacturer evidence. It forbids using ESS alone or missing hybrid
terminology. A multi-source inference is therefore not categorically prohibited,
but its premises and configuration associations must first be verified.

The live implementation adds an integration limitation: `_supports()` accepts
explicit `none`, `nonhybrid` or `non hybrid` raw claims, while `ESS` and
`Without E-Torque` both return false for `electrification_type=none`. It does not
evaluate the proposed multi-document hardware rule. An Australian naturally
aspirated phrase would pass the lexical aspiration check, but lexical acceptance
does not prove US applicability. We did not attach that phrase to US candidates
or invent a manufacturer `nonhybrid` claim to satisfy the validator.

Two paths remain: obtain directly applicable US ERC induction/nonhybrid claims
that existing validators support, or first establish the missing evidence-backed
associations and separately review implementation support for a verified hardware
rule. No accepted contract or application implementation was changed here.

## Candidate coverage and remaining input

`coverage.csv` lists all ten unchanged inputs and their actual SHA-256 hashes:
three two-door and seven four-door candidates, including the separately marketed
Altitude and Moab offerings. All ten retain null aspiration and electrification.
There is no adequately established subset that can be safely promoted now.

The missing evidence is precisely:

- A manufacturer statement applying naturally aspirated induction directly to
  the US MY2019 ERC offering, or an explicit manufacturer-supported correspondence
  between the Australian technical variant and that US offering. Engine-family
  naming or matching technical dimensions alone cannot supply this link.
- A manufacturer-supported application/architecture association binding the
  conventional, nonhybrid system to ERC across all ten US offerings. A catalog
  that includes a without-eTorque subset is not an exhaustive ERC determination.
- If using the hardware inference rather than an explicit raw classification,
  compatibility review of the existing source-support validator is also needed.

## Verification and preservation

- `.venv/bin/python`: Python 3.13.1, Django 6.0.7, pypdf 6.16.1.
- **69 focused tests passed**, zero failures/errors, using an isolated test
  database with `RIGARCHIVE_TEST_DB_PATH=:memory:`: StructuredPowertrainTests,
  generation-projection completeness and ingestion serialization. Django's test
  system check reported zero issues. No full suite or development migration ran.
- All ten current ERC candidates pass fresh contract validation, qualified
  retained-byte validation and serialization round trips; both unresolved fields
  were explicitly checked to remain null. No planner/importer was invoked.
- A direct read-only compatibility diagnostic confirmed the source-support
  behavior described above. No new tests or application code were written.
- `preservation.json` verifies all 159 pre-existing handoff files plus the
  development database against their prior byte hashes. Database SHA-256 remains
  `b045601a33811b44a443b7c0cc78ce916e9af476cb3c5f4c5b94dc2fdf18e26f`.
- Only this new research directory was added. Prior candidates/assertion sets,
  accepted governance/contracts, existing Git changes, database and backups were
  preserved. No correspondence publication, import plan, canonical write,
  backfill, commit or push occurred.

An initial research-artifact writer had a syntax error before execution and wrote
nothing; the corrected writer completed. This did not affect candidate validation
or the test results above.
