# Consolidated structured-powertrain classification review

Created: 2026-11-08
Status: Proposed — owner approval pending

All **89 unresolved field decisions across 71 research rows** remain proposed.
There are seven engine/field groups. The proposed construction subset contains
88 decisions across 70 of its 73 rows; ECX's three rows already have all five
fields directly supported. The remaining one EC1 decision belongs to deferred RHD.
These counts are field decisions, not additional vehicles or Candidate revisions.

`classification_review_89_decisions.json` / `.csv` pin every affected research
identity, source-matrix row digest, field, proposed value, group, confidence,
evidence locators and pending disposition. `classification_groups.json` retains
full manufacturer observations, secondary references, inference and limitations.
No executable CanonicalImportAdjudication 1.1 record or approval signature is made.

| Engine / field | Proposed value | All rows | Construction scope | Confidence | Human approval needed |
| --- | --- | ---: | ---: | --- | --- |
| ERC / engine_aspiration | naturally_aspirated | 17 | 17 | moderate | Yes |
| ERC / electrification_type | none | 17 | 17 | moderate | Yes |
| ERG / engine_aspiration | naturally_aspirated | 20 | 20 | moderate | Yes |
| EC1 / electrification_type | none | 21 | 20 | moderate | Yes |
| EXJ / electrification_type | none | 12 | 12 | moderate | Yes |
| ESG / engine_aspiration | naturally_aspirated | 1 | 1 | moderate | Yes |
| ESG / electrification_type | none | 1 | 1 | moderate | Yes |

## Evidence and applicability

- ERC/ERG aspiration: MY2021 US technical engine architecture and code-linked
  guides plus a contemporary technical report explicitly describing the V6 as
  naturally aspirated with/without 48V assist support the conclusion. The retained
  manufacturer text does not directly state the induction enum. Keep derived
  provenance and moderate confidence. These are not renewed MY2019/2020 approvals.
- ERC/EC1/EXJ nonhybrid: exact MY2021 ESS engine-code cells, the 2021 manual's
  conventional starter/12V battery versus eTorque motor-generator/hybrid-battery
  descriptions, and guide group-detail eTorque 48V/alternator-delete equipment
  support a bounded derived conclusion. The manual was printed as Fourth Edition
  V1 with 2022 copyright for MY2021; its filename E5 is not its printed edition.
  It covers several options, does not bind sales codes and is not proof by itself.
  ESS spelling, absent eTorque wording or starter presence alone would be insufficient.
- ESG aspiration: production North American MY2021 release/specifications and
  exact US ESG/27X guide correspondence establish the production engine. A
  contemporary production technical report explicitly calls it naturally
  aspirated. This remains a supported human-derived conclusion, not a fabricated
  manufacturer assertion. No 450-hp concept source is substituted.
- ESG nonhybrid: production 392 specification page 2 explicitly documents a
  180-amp alternator and 700-CCA battery; its architecture joined to the production
  ESG guide supports none. The source does not explicitly use a nonhybrid enum,
  and an alternator alone is not a universal nonhybrid test. Preserve moderate
  confidence and derived limitations.

Every group is bounded to the exact listed MY2021 US Wrangler JL rows. No global
engine rule, other-year propagation, fuel/induction default or canonical write is
approved. Applicable source hashes are pinned through the original technical
inventory and the new additional_source_index.json.

The general technical snapshot describes V6 automatic availability as eTorque;
later 24-series ERC automatic guide cells are more specific evidence for those
rows. Preserve that temporal distinction rather than changing ERC into ERG or
inventing a new transmission-only identity.

## ECX — direct five-field assessment, no pending human classification

The exact Sahara/High Altitude/Rubicon four-door 4XE cells say 2.0L I4 turbo PHEV,
ECX, DFY. The manufacturer 4xe specification page 1 identifies marketed 2.0L,
four cylinders, turbocharging and unleaded fuel; pages 2–3 identify plug-in hybrid
transmission, traction motor and high-voltage battery. Proposed normalized tuple:
`2`, `4`, `turbocharged`, `gasoline`, `plug_in_hybrid`.

These are evidence-backed normalizations, not an inference solely from the 4xe
brand. Gasoline denotes the combustion fuel under accepted RA-044; electrical
propulsion is retained as PHEV electrification. A belt-start motor with an eTorque
label in the technical PDF does not reclassify the complete PHEV as MHEV or HEV.
The three 4xe research rows do not need added classification decisions within the
89. They still require later Candidate construction and normal contract validation.

## ESG — five-field assessment

Guide 27X/ESG and the production specification establish marketed `6.4`, eight
cylinders and premium gasoline. Preserve the exact 6,417cc technical observation
without replacing marketed displacement. Naturally aspirated and none remain the
two moderate-confidence proposed human classifications above. Standard DFV
eight-speed automatic and four-door applicability are source-linked, not new
identity dimensions or permission for a separate vehicle model/Generation.

## Existing workflow

After separate owner approval and Candidate construction, the existing workflow
can bind supported conclusions to exact candidate digests, source assertion
references, confidence and limitations, then emit immutable human-provenance
revisions. This review does not pre-empt that order or fabricate candidate hashes.
Direct-source validation remains unchanged; contradictory or unsupported findings
must remain blocked even after a broad policy approval.
