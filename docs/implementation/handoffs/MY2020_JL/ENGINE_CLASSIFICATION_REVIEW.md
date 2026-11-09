# MY2020 JL engine classification evidence review

Created: 2026-11-08
Status: Proposed

This is discovery research, not an approved adjudication or Candidate 2.1.0
artifact. Proposed values do not fill canonical fields. No MY2019 approval is
transferred to MY2020. The existing human-classification workflow remains the
resolution path for supported conclusions requiring a director decision.

| Code | Marketed engine | Aspiration proposal | Fuel evidence | Electrification proposal | Rows |
| --- | --- | --- | --- | --- | ---: |
| ERC | 3.6L V6 VVT UPG I with ESS | naturally_aspirated; review required | gasoline, corroborated US manufacturer family specification | none; review required | 17 |
| ERG | 3.6L V6 VVT eTorque UPG I | naturally_aspirated; review required | gasoline, corroborated US manufacturer family specification | mild_hybrid, explicit manufacturer eTorque classification | 3 |
| EC1 | 2.0L I4 DOHC DI Turbo with ESS | turbocharged, explicit guide descriptor | gasoline, corroborated US manufacturer family specification | none; review required | 15 |
| EC3 | 2.0L I4 DOHC DI Turbo eTorque | turbocharged, explicit guide descriptor | gasoline, corroborated US manufacturer family specification | mild_hybrid, explicit manufacturer eTorque classification | 6 |
| EXJ | 3.0L V6 Turbo Diesel with ESS G3 | turbocharged, explicit guide descriptor | diesel, explicit guide and US specification | none; review required | 8 |

The machine-readable assessment retains proposed tuples separately from
manufacturer-supported values, with unapproved fields explicitly listed.
Displacement and cylinders are directly described with the engine code in each
order guide. Preserve the marketed decimal representation: canonical `3.6`, `2`,
`3` correspond to marketed 3.6L, 2.0L and 3.0L. Do not replace them with swept
volumes converted from 3,604 / 1,995 / 2,987 cc. The differences are not extra
engine identities.

## Admissible retained primary material

The 20 order guides explicitly bind the five engine codes to model codes,
marketed-grade columns, engine/transmission descriptions and populated QOP cells.
Each observation retains the actual PDF hash, printed revision and PDF page in
`evidence/powertrain_table_excerpts.json`. No offering is inferred from a blank
cell or an edition's parent family alone.

[FCA US MY2020 Wrangler specifications](source_pdfs/FCA_2020_Wrangler_US_specifications.pdf)
was acquired directly from the manufacturer media S3 origin. Its SHA-256 is
`sha256:8ca6c22b9af4a87f33700b3a3455fa3fae9ea5799218f232cbbb1b31eabf8354`.
Pages 1–2 distinguish the 3.6 ESS and eTorque alternatives, pages 2 and 12 support
gasoline for the 2.0 family, page 3 explicitly identifies diesel fuel, and pages
1 and 5 establish the model's four-wheel-drive architecture. Pages 1–2 explicitly
call the eTorque versions mild hybrids. Code-to-family correspondence is a joined
reading with the guides, not a claim that the technical specification prints the
order-guide engine codes.

## Findings that are still derived or unresolved

The US technical specification does **not** explicitly classify either 3.6 engine
as naturally aspirated. Naturally aspirated is a proposed family/architecture
conclusion; record the detailed supporting family evidence and limitations in
future proposals, and obtain fresh MY2020 human approval. Neither the engine
code, cylinder count, displacement nor omission of turbo terminology proves it.

The retained descriptions distinguish ESS versions from eTorque mild hybrids, but
ESS wording and absence of an eTorque label do **not** independently prove `none`.
For ERC, EC1 and EXJ, retain that field as unknown in any unapproved candidate.
Obtain positive applicable conventional-versus-motor-generator hardware evidence,
explicit corroboration, or a supported human adjudication with its documented
premises. For EXJ especially, a conventional diesel architecture is currently a
working proposal, not a sufficiently documented nonhybrid assertion. Do not
approve an unsupported inference merely because it is plausible.

Thus 43 research rows have at least one unapproved classification field. The six
EC3 rows have manufacturer-backed proposed five-field tuples, but no Candidate
contract, lineage certification or import eligibility has been granted here.

## Applicability and source limitations

The generic US specification lists 2.0 eTorque in the Sahara context and its fuel
economy section calls eTorque four-door-only. Later retained guides explicitly
list EC3/DFT `28Y` for two-door Rubicon Recon. Treat the generic specification as a
publication snapshot; do not reject the later explicit factory offering or
propagate its early availability restriction as a timeless engine rule. Retain
specific Recon guide lineage for both bodies. The engine's electrification type
and its trim/body availability are separate findings.

ERG is observed only for four-door Sahara, Sahara Altitude and Sahara High
Altitude. ERC is manual-only in the observed Sahara/Sahara Altitude tables;
ERG automatic is a different electrification identity, not a transmission-only
duplicate. Elsewhere ERC manual/automatic QOPs collapse into one proposed baseline.

The web-readable August 31, 2019 manufacturer fact sheet corroborates the
powertrain families, but raw retrieval failed and its corporate boilerplate was
subsequently updated. Its original byte identity is unestablished; it is context
only. The 2019 ERC approval is similarly contextual to this research, never an
approval of MY2020 classifications. Shared family publications and successive
order-guide revisions are not independent sources merely because used repeatedly.

No additional offered engine code was found. `ERS` in the specification means
Electronic Range Select transmission control; it is not an engine code. No
US MY2020 4xe, 392, export 2.2 diesel or ERG two-door offering is established by
the retained guides.
