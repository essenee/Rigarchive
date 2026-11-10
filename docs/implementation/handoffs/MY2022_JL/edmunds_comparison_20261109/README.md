# MY2022 Wrangler — lightweight Edmunds cross-check

Created: 2026-11-09
Status: Proposed

**All 56 manufacturer research rows have an Edmunds offering counterpart**, across
all 20 body/trim groups and six powertrain families. No additional baseline or
direct configuration contradiction was established. This corroborates offering
coverage; it does **not** establish every unresolved canonical classification.

Read the existing [56-row matrix](../discovery_20261109/provisional_configuration_inventory.json)
and six-family assessment directly; no PDF reconstruction or manufacturer discovery.
The matrix SHA-256 is `c07f3b2aba1876011ac88751f51e725d3658f7a559d0d80110b2935fb15bb656`.

## Method and exact counts

Inspected only the supplied [Wrangler trims](https://www.edmunds.com/jeep/wrangler/2022/trims/),
[Wrangler specifications](https://www.edmunds.com/jeep/wrangler/2022/features-specs/),
[4xe trims](https://www.edmunds.com/jeep/wrangler-4xe/2022/trims/) and
[4xe specifications](https://www.edmunds.com/jeep/wrangler-4xe/2022/features-specs/),
including their trim selectors and expanded Mechanical Options/Packages tables.
Observed 17 conventional/392 trim entries plus three 4xe entries and 59 QOPs.
Optional engines are counted only when listed for that specific trim and joined
to an existing manufacturer row, never by multiplying the generic engine list.
Live selector style IDs and source URLs are retained in the CSV. Prices and vehicle
advertisements were excluded. Observations were made on 2026-11-09; these are
research transcriptions, not retained original webpage bytes or historical revisions.

[Row-by-row CSV](row_comparison.csv) contains exactly 56 unique manufacturer row
IDs, dimensional comparisons, source style IDs, matching QOPs, transmission gaps
and unresolved identity fields.

| Offering comparison outcome | Rows |
| --- | ---: |
| Exact match of comparable offering/name | 45 |
| Equivalent configuration with different naming | 11 |
| Manufacturer-only configuration | 0 |
| Edmunds-only configuration | 0 |
| Genuine contradiction | 0 |
| Insufficient evidence to identify an offering counterpart | 0 |
| **Matching offering counterparts** | **56** |

Here **exact match means an offering counterpart on the observed comparable
attributes**, with the four-door Unlimited body prefix accounted for. It is not a
claim of a complete five-field identity proof. Unknown aspiration/electrification
is preserved rather than treated as agreement. On that stricter field test,
**53 rows still have insufficient explicit five-field corroboration**; only the
three ECX rows have explicit turbo/gas-electric/PHEV family descriptions covering
the five concepts. No classification was applied to the original matrix. The
matrix does not project drive category: Edmunds specifies 4WD throughout, so no
manufacturer-versus-Edmunds drive equality is certified from these inputs alone.
Thus **zero rows are certified exact across every requested dimension**.

The 11 naming equivalences are the eight JLJL74/JLJP74 Altitude rows, distinguished
by Edmunds as Sport Altitude versus Sahara Altitude, and the three ECX rows whose
4xe identity is conveyed through Edmunds' separate Wrangler 4xe model rather than
always through a trim suffix. No two manufacturer rows are merged.

## Six powertrain families

| Family | Rows | Edmunds evidence and remaining limit |
| --- | ---: | --- |
| ERC 3.6 V6 ESS | 13 | 3.6/6-cylinder gas manual bases and matching 23x QOPs; some 24x alternatives. Naturally aspirated/nonhybrid conclusions are not explicitly stated for every pairing. |
| ERG 3.6 V6 eTorque | 15 | Trim-specific eTorque options and 25x QOPs; High Tide explicitly identifies a gas/electric mild hybrid. Naturally aspirated classification still needs a reviewed conclusion. |
| EC1 2.0 I4 turbo ESS | 15 | Turbo four-cylinder options/22x QOPs; RHD and conventional High Altitude explicitly show gas turbo automatic bases. Nonhybrid classification is not an explicit universal option-level statement. |
| EXJ 3.0 V6 turbo diesel | 9 | Trim-specific turbo diesel option, 26x QOPs and 8HP75 automatic option; nonhybrid classification remains a reviewed conclusion. |
| ECX 2.0 I4 turbo PHEV | 3 | Separate 4xe listings explicitly establish turbo, four cylinders, gasoline/electric plug-in hybrid, automatic and 4WD. 29P/N/V align with the manufacturer rows. |
| ESG 6.4 V8 / 392 | 1 | 6.4/8-cylinder gas automatic, 27X, 4WD and required premium unleaded. Naturally aspirated/nonhybrid conclusions are not explicit in the inspected fields. |

Edmunds' gas descriptions strengthen the gasoline interpretation, particularly the
392 fuel question and explicit gas/electric 4xe description. They support a bounded
reviewed semantic mapping; they do not automatically satisfy the current literal
support predicate or authorize changing it. Neither omission of a turbo label nor
ESS proves naturally aspirated/nonhybrid status. The generic five-engine narrative
also does not collapse ERC and ERG into one canonical engine identity.

## Discrepancies and special cases

- **Eight transmission/QOP gaps, not eight missing configurations:** two-door
  Sport/Sport S/Willys/Willys Sport ERC automatics (24B/S/W/K), four-door Sport
  Altitude 24L, Willys 24W, Sahara Altitude 24L and Sahara 24G. Their rows still
  match through manual 23x evidence. Preserve all manufacturer-supported alternatives;
  absence from current Edmunds options does not contradict earlier guide availability.
- **High Tide:** independently listed as Unlimited High Tide, style 401927272,
  3.6 V6 mild hybrid/8-speed/4WD, QOP 25D. This materially corroborates the existing
  High Tide row; it is not an invented engine/package permutation.
- **Jeep Beach:** the trim narrative calls it a High Tide add-on package, not a
  separate selector configuration. This supports retaining it as equipment/edition
  treatment without a 57th baseline, subject to owner acceptance. The narrative's
  equipment detail is not used to build a package catalogue or contradict the
  retained manufacturer announcement about the first 500 High Tide vehicles.
- **Sport RHD:** explicitly listed, style 401915672, 2.0 turbo/8-speed/4WD, 22A.
  Existence is corroborated; consumer/fleet scope and canonical treatment remain
  owner decisions. It stays separate from the 55 consumer proposals.

## Verification and recommendation

CSV checks passed: 56 unique input IDs, all 20 groups mapped, at least one observed
QOP per row, and every observed Edmunds QOP already present in the corresponding
manufacturer group. Source/discovery files and db.sqlite3 match the recorded
preservation hashes. Only this report and CSV were created. No application code,
architecture/schema, original discovery, CURRENT_STATE or CHANGELOG was changed.
No Django suite was run; no candidates, database writes, commits or pushes occurred.
Pre-existing working-tree changes were preserved.

**Recommendation: sufficient to proceed to lightweight candidate construction
for the 55 consumer proposals, preserving unresolved values as null, once separately
authorized; no repeat manufacturer discovery is warranted by this comparison.**
Before complete five-field candidates can be certified, obtain only the material
owner findings: MY2022 grade/naming acceptance (including High Tide and Beach as
subordinate equipment), naturally aspirated and nonhybrid family conclusions where
not explicit, and the reviewed gasoline terminology mappings. Keep RHD deferred
unless its scope is approved. The missing transmission alternatives are not blockers
to baseline construction and must remain retained; Edmunds does not resolve historic
ordering windows. These sources do not authorize import or Matrix certification.
