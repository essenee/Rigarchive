# MY2022 powertrain evidence and classification limits

Created: 2026-11-09
Status: Proposed

`powertrain_evidence_matrix.json` supplies the five existing fields, nulls, raw
manufacturer descriptors, exact guide refs, technical context and possible values
requiring review. Values are research projections, not approved classifications.
The unchanged `_supports` predicate is applied to the engine descriptor column,
not QOP tokens such as 22L that could be mistaken for a liter measurement.

| Engine code/family | Guide availability | Transmission codes | Direct supported research fields | Pending fields |
| --- | --- | --- | --- | --- |
| ERC / 3.6 V6 ESS | Both bodies, positive trim-specific cells | DEM manual; DFT automatic where listed | 3.6 L; 6 cylinders | aspiration, gasoline fuel classification, electrification |
| ERG / 3.6 V6 eTorque | Both bodies; High Tide only ERG in guide | DFT automatic | 3.6 L; 6 cylinders; mild_hybrid | aspiration, gasoline fuel classification |
| EC1 / 2.0 I4 turbo ESS | Both bodies, including separate RHD | DFT automatic | 2 L; 4 cylinders; turbocharged | gasoline fuel classification, electrification |
| EXJ / 3.0 V6 turbo diesel ESS | Four-door conventional sections only | DFV automatic | 3 L; 6 cylinders; turbocharged; diesel | electrification |
| ECX / 2.0 I4 turbo PHEV | JLXP74 Sahara/High Altitude and JLXS74 Rubicon only | DFY PHEV automatic | 2 L; 4 cylinders; turbocharged; plug_in_hybrid | gasoline fuel classification |
| ESG / 6.4 V8 HEMI | Four-door Rubicon 392 only | DFV automatic | 6.4 L; 8 cylinders | aspiration, gasoline fuel classification, electrification |

No naturally aspirated or nonhybrid value is inferred from omission, displacement,
ESS or engine code. No ordinary hybrid or battery-only baseline is established.
The technical PDF supports family-level context but cannot create trim combinations.

Technical context: SP pp1–2 describes the 3.6 ESS/manual versus eTorque/automatic;
p2 describes 2.0 turbo and includes 4xe in shared text; p3 describes EcoDiesel and
6.4; p4 continues 6.4 fuel and 850RE; p5 describes 8HP75 and D478. FA p1 supplies a
body/trim engine/transmission grid. SP p5's manual/eTorque claim conflicts with
SP p1 and every guide manual ERC pairing. SP p2's grouped ESS/4xe phrasing and
p4's belt-starter heading must not erase ECX's explicit guide PHEV identity.
DFY/8P75PH is explicit in each applicable 4xe guide segment.

Fuel grade remains separate: SP p1 specifies unleaded regular 87 AKI for 3.6;
p2 specifies minimum 87 with 91+ recommended for its shared 2.0 section (review
4xe applicability); p3 specifies ultra-low sulfur diesel; p4 requires premium
91 AKI for 6.4. The current gasoline predicate does not accept octane/unleaded
wording by itself. Preserve wording for owner classification or acquire a more
explicit MY2022 fuel source; do not broaden the parser to force completion.

All mechanical code, source, QOP and transmission lineage remains separate from
the five-field identity. Transmission differences and Xtreme Recon equipment do
not independently multiply canonical VehicleDefinitions.
