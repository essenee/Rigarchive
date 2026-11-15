# MY2026 Wrangler JL — Edmunds extraction

Extraction date: 2026-11-14. Read-only acquisition; no import implementation or publication.

## Coverage and result

Inspected **18 unique builder styles and 18 exact-style specification pages**, yielding **33 distinct canonical configurations: 33 gasoline, zero PHEV**. There are five two-door styles and 13 four-door styles; derived identities are ten two-door and 23 four-door. All listed styles were inspected; no offered style remains uninspected.

The year selector identifies modelyearId `402076473`. All three listed categories were examined: SUV, Willys 392 and Moab 392. The two 392 categories repeat IDs already listed under SUV; these are deduplicated, not additional styles. Both dedicated 392 builders have no Mechanical options section; their standard V8 is confirmed by their trim summary and exact-style specifications.

Entry points:

- [MY2026 builder](https://www.edmunds.com/jeep/wrangler/build/?defaultYear=2026)
- [All SUV styles](https://www.edmunds.com/jeep/wrangler/build/?modelyearId=402076473&submodel=SUV&allStyles)
- [Willys 392 styles](https://www.edmunds.com/jeep/wrangler/build/?modelyearId=402076473&submodel=Willys%20392&allStyles)
- [Moab 392 styles](https://www.edmunds.com/jeep/wrangler/build/?modelyearId=402076473&submodel=Moab%20392&allStyles)

Normal in-app browser navigation, JavaScript rendering and accessibility/visible DOM inspection were used. Expanded every available Mechanical options section, opened all exact-style specification pages, checked their selected style IDs and expanded Engine. Individual URLs, displayed descriptions, option prices, source table rows and registry references are in `inventory.json`. No quote forms, external manufacturer research or access-control workaround.

## Canonical inventory and registry mapping

| Trim | Bodies | Observed engines | Configurations |
| --- | --- | --- | ---: |
| Sport | Two/four-door | ERC standard, EC1 optional | 4 |
| Sport S | Two/four-door | ERC standard, EC1 optional | 4 |
| Willys | Two/four-door | ERC standard, EC1 optional | 4 |
| California Edition | Four-door | ERC standard, EC1 optional | 2 |
| Rubicon | Two/four-door | ERC standard, EC1 optional | 4 |
| 85th Anniversary Edition | Four-door | EC1 standard, ERC optional | 2 |
| Willys 41 | Four-door | EC1 standard, ERC optional | 2 |
| Sahara | Four-door | EC1 standard, ERC optional | 2 |
| Sport RHD | Four-door | EC1 only | 1 |
| Rewind | Four-door | EC1 standard, ERC optional | 2 |
| Rubicon X | Two/four-door | ERC standard, EC1 optional | 4 |
| Willys 392 | Four-door | ESG only | 1 |
| Moab 392 | Four-door | ESG only | 1 |

Resolved existing authored Engines: **ERC PK1 (15 configurations), EC1 PK2 (16), ESG PK3 (2)**. ECX PK6 exists but has no MY2026 offering. All five canonical engine properties and registered names are reused directly from those records; none was reconstructed. Edmunds does not print a manufacturer engine code in the inspected labels/tables: codes are the supplied established project associations, distinctly identified as such. No genuinely new/unrecognized engine appeared. No Engine was created or modified.

The [MY2026 Edmunds overview](https://www.edmunds.com/jeep/wrangler/2026/) explicitly identifies discontinuation of the Wrangler 4xe in its “What's new” section. No PHEV type/style is listed in the MY2026 builder or specifications catalogue. The [requested MY2026 4xe builder](https://www.edmunds.com/jeep/wrangler-4xe/build/?defaultYear=2026) returns Page Not Found. No old PHEV offering is carried forward.

## MY2025 comparison

- Styles: **20 → 18**; canonical configurations: **31 → 33**; gasoline: **24 → 33**; PHEV: **7 → 0**.
- Added gasoline trims: California Edition, 85th Anniversary Edition, Willys 41, Rewind, Willys 392 and Moab 392. The first four each offer both registered V6 and turbo gasoline engines; the last two offer V8.
- No longer listed: Rubicon 392 Final Edition and all seven MY2025 4xe trims (Sport S, Willys, Sahara, Willys '41, Rubicon, Backcountry, Rubicon X). Preserve “Willys 41” as MY2026 gasoline spelling; do not silently merge it with MY2025 “Willys '41 4xe”.
- All seven recurring gasoline trims retain their evidenced body/engine combinations: five trims have both bodies/both engines, Sahara remains four-door with both engines, and Sport RHD remains four-door turbo only. **23 combinations retained, ten added, eight removed.** No new engine family is introduced; ECX is absent from MY2026 availability.
- Two-door configurations remain ten; four-door configurations change from 21 to 23. Every added trim is four-door.
- Supporting prices: Sahara V6 option is $500 (MY2025 $2,000); Rubicon/Rubicon X four-door 850RE is $3,000 (MY2025 $2,500). Transmission changes do not create extra canonical identities.

## Ambiguities and blockers

No registry, schema or source-access blocker was found for the observed 33 identities. This is discovery, not an approved import plan.

Optional-engine transmission pairings remain unreported; co-listed manual/automatic options do not establish turbo/manual availability. Anniversary, Willys 41 and Rewind have eight-speed automatic standard specifications yet also list an optional 850RE; the relationship is unexplained. Option descriptions include cross-trim axle/camera notes: preserve them without inventing applicability or extra equipment identities. Standard transmission manufacturer codes and optional-engine octane requirements remain unknown. California/Rewind fuel tables include 0/0-mile range placeholders, which are not ingested as real specifications. None of these supporting-data gaps requires fabricating engine properties or automatically authoring an Engine.

## Preservation

Only this directory's two requested files were created. Development database hash and pre-existing tracked/index changes were verified unchanged. No application code, migrations, imports, staging, commits, pushes, deployment or environment changes. Artifact validation confirms 18 unique styles, 33 unique trim/body/registered-engine identities, registry property equality, complete source links and the comparison counts. Django tests were not run because no application behavior changed.
