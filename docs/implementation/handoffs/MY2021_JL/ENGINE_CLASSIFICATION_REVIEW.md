# Structured powertrain evidence assessment

Created: 2026-11-08
Status: Proposed

No field is approved here by inference. Direct normalized fields, pending values,
row applicability, source page/hash references and limitations are retained in
engine_classification_assessment.json. Historical approvals are not extended.

| Engine | Rows | Direct normalized fields | Pending human review |
| --- | ---: | --- | --- |
| ERC | 17 | engine_displacement_liters=3.6, engine_cylinders=6, fuel_type=gasoline | engine_aspiration=naturally_aspirated, electrification_type=none |
| ERG | 20 | engine_displacement_liters=3.6, engine_cylinders=6, fuel_type=gasoline, electrification_type=mild_hybrid | engine_aspiration=naturally_aspirated |
| EC1 | 21 | engine_displacement_liters=2, engine_cylinders=4, engine_aspiration=turbocharged, fuel_type=gasoline | electrification_type=none |
| EXJ | 12 | engine_displacement_liters=3, engine_cylinders=6, engine_aspiration=turbocharged, fuel_type=diesel | electrification_type=none |
| ESG | 1 | engine_displacement_liters=6.4, engine_cylinders=8, fuel_type=gasoline | engine_aspiration=naturally_aspirated, electrification_type=none |
| ECX | 3 | engine_displacement_liters=2, engine_cylinders=4, engine_aspiration=turbocharged, fuel_type=gasoline, electrification_type=plug_in_hybrid | None |

The marketed 3.6, 2.0, 3.0 and 6.4 displacements come from explicit descriptors;
technical cubic-centimeter precision is preserved in original evidence rather
than substituted for marketed displacement. V6/I4/V8 establish cylinder counts,
not a layout-specific canonical enum. Unleaded/octane fuel requirements support
normalization to gasoline; EXJ explicitly identifies diesel. `TURBO` explicitly
supports turbocharged for EC1/EXJ/ECX. Applicable manufacturer specifications call
ERG's eTorque mild hybrid; the exact guide ERG association supplies scope.

For ECX, the four-door QOP table explicitly says turbo PHEV and links ECX to DFY.
The 4xe specification identifies 2.0L I4 turbo, unleaded fuel, plug-in hybrid
transmission, electric motor-generators and high-voltage battery. It is a
combustion-equipped gasoline PHEV under accepted RA-044, not electricity coerced
into gasoline and not MHEV merely because it has a belt motor-generator.

89 pending field-level conclusions affect 71 research rows. Naturally aspirated
ERC/ERG/ESG and nonhybrid ERC/EC1/EXJ/ESG remain **null in direct projections**.
Their plausible proposed values require new MY2021 bounded evidence-backed human
adjudication, with moderate confidence and explicit limitations. ESS alone,
absence of eTorque, generic alternator availability or model-code similarity is
not fabricated as a direct nonhybrid assertion. The 392 specification does
explicitly document its 180-amp alternator and 700-CCA battery; none remains a
reasoned interpretation. Concept-392 naturally-aspirated statements were found
but are not substituted for production-MY2021 applicability.

The US specification's broad V6-automatic/eTorque description is an availability
snapshot. Later manufacturer order-guide 24-series ERC automatic cells preserve
specific applicability; do not overwrite them using that broad statement. The
supplemental PDF metadata/search title can say 2022 Product Information while
content says 2021: scope is established from content and primary guide matching,
not that metadata title. No Canada specification is silently used for US scope.

No EC3 offering is supported by any positive MY2021 QOP cell. No new engine code
beyond ERC/ERG/EC1/EXJ/ECX/ESG is identified. Codes alone never prove distinctions;
complete tuples and evidence are required before canonical eligibility.
