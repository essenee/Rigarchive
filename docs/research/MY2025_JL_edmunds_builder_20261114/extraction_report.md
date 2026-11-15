# MY2025 Wrangler JL — Edmunds builder extraction

Extraction date: 2026-11-14. Acquisition only; no import or publication.

## Result

20 builder styles examined: 13 gasoline and 7 PHEV. Each individual builder's Mechanical options and each exact-style specifications page were inspected. The inventory contains 31 proposed canonical configurations: 24 gasoline and 7 PHEV. All requested builder/specification pages were readable; none remain uninspected.

Gasoline: Sport, Sport S, Willys, Rubicon and Rubicon X each have two bodies and two engines (20 configurations). Sahara has two engines (2); Sport RHD and Rubicon 392 Final Edition each have one (2). PHEV: Sport S, Willys, Sahara, Willys '41, Rubicon, Backcountry and Rubicon X each have one four-door PHEV configuration (7). Canonical PHEV trims retain the 4xe suffix. Door identities remain separate from trim.

## Method and evidence

Used the in-app JavaScript browser, ordinary navigation and rendered accessibility/DOM text. Expanded every Mechanical options section. Opened each exact-style specifications URL, verified the selected style ID, and read Fuel & MPG, Engine and Drivetrain; expanded every Engine section. Tested each optional engine checkbox. No quote, login or contact form was submitted. No anti-bot restriction was bypassed.

`inventory.json` contains the enumeration URLs, per-style builder/specification URLs, displayed trim summaries, expanded engine rows, fuel and drivetrain rows, exact engine/transmission option labels and prices, complete displayed engine/transmission option descriptions, proposed normalized fields, source ambiguities and counts. Repeated engine parameters are referenced by artifact-local profile keys, which are not manufacturer codes. Source output from an initial selector-navigation attempt that did not verify the selected style was discarded and replaced by exact-style inspections. One browser execution timeout was recovered; it did not leave any page uninspected.

## Availability and transmission handling

Ten V6-base styles display “2.0L I4 DOHC DI Turbo Engine w/ESS” at $0 and “8-Speed Automatic 850RE Transmission” at $2,500. Sahara displays “3.6L V6 24V VVT Engine UPG I w/ESS” at $2,000. Sport RHD, Final Edition and all seven PHEV styles display no engine/transmission alternatives. Standard V6 styles list six-speed manual; other standard styles list eight-speed shiftable automatic.

Transmission alternatives do not multiply canonical identities (ADR-0010). Selecting the turbo on each V6-base style left the automatic checkbox unchecked and produced no dependency dialog. Sahara's V6 selection also produced no dependency message. The builder's behavior does not establish valid optional-engine/transmission pairings: no turbo/manual claim is made. Rubicon/Rubicon X transmission descriptions explicitly mention full-time Rock-Trac; those descriptions and tire/axle associations are retained without generating equipment permutations. Standard tables report part-time 4WD for gasoline styles except Final Edition; Final Edition and all PHEVs report full-time 4WD.

## Unresolved information

- No manufacturer engine code is displayed. No registry code or Engine association is inferred.
- V6/V8 aspiration is not explicitly stated even in expanded Engine tables; 12 derived configurations retain null aspiration. The availability inventory is complete, but these are not complete five-field powertrain inputs.
- Optional-engine transmission pairings and restrictions are not established beyond the displayed descriptions. Null pairing does not negate engine availability.
- Optional-engine octane requirements are unreported. Gasoline/nonhybrid normalization follows the gasoline builder context; ESS and auxiliary batteries are not classified as MHEV.
- Standard transmission manufacturer codes are unreported. 850RE is retained only for the explicitly named option.
- The 4xe overview prose mentions High Altitude, whereas its actual builder and specifications selector include Backcountry and no High Altitude. No additional High Altitude style was invented.

## Preservation and validation

Only this new directory's `inventory.json` and `extraction_report.md` were created. Existing project files and database were not written. No dependencies installed, application code, fixtures, migrations, imports, commits, pushes or deployment. Artifact checks verify 20 unique styles, 31 unique trim/body/engine configurations, seven PHEVs, and 12 null-aspiration rows. Django checks/tests were not run because this is acquisition only; the prescribed repository interpreter is absent. Pre-existing changes remain untouched.
