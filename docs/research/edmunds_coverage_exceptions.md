# RigArchive — Edmunds Coverage Exceptions Register

**Created:** 2026-11-12  
**Last Updated:** 2026-11-13  
**Status:** Accepted  
**Domain:** `reference` (Ingestion & Provenance Research)

---

## 1. Purpose and Scope

Under the approved **W2 (Edmunds-first provisional)** ingestion workflow (`docs/development/INGESTION_PROTOCOL.md`), Edmunds trim-specific Mechanical Options, Packages/QOP, and marketed taxonomy serve as the primary working baseline for initial candidate inventory construction, while targeted manufacturer ordering guides and technical specifications are used to resolve ambiguities and verify coverage.

This project-wide register records confirmed discrepancies between initial Edmunds-derived working inventories and verified primary manufacturer evidence, distinguishing between:

1. **Missing Configurations (`missing_configuration`):** Factory-confirmed model/trim/powertrain configurations established by authentic manufacturer ordering guides or specifications that were absent from our initial Edmunds-derived working inventory.
2. **Incorrect Technical Specifications (`incorrect_technical_specification`):** Attributes or availability assertions in the initial Edmunds-derived working inventory that are directly contradicted by authentic manufacturer ordering guides or technical specifications.

> **Methodological Note:** Entries classified as `missing_configuration` document manufacturer-only discoveries relative to RigArchive's initial Edmunds-derived working inventory at the time of ingestion. They do not claim that every historical or current Edmunds page or API endpoint universally omits the configuration unless independently verified across all Edmunds surfaces.

---

## 2. Running Tally of Confirmed Coverage Exceptions

| Category | Confirmed Count | Exception IDs | Affected Model Years / Vehicles |
|---|---:|---|---|
| **Missing Configurations (`missing_configuration`)** | **3** | `ECE-001`, `ECE-002`, `ECE-003` | MY2023 & MY2024 US Jeep Wrangler JL |
| **Incorrect Technical Specifications (`incorrect_technical_specification`)** | **0** *(tracked separately from quarantined manual Sahara / non-hybrid High Altitude rows unless registered)* | — | — |
| **Total Confirmed Coverage Exceptions** | **3** | `ECE-001`, `ECE-002`, `ECE-003` | MY2023 & MY2024 US Jeep Wrangler JL |

---

## 3. Documented Exceptions

### `ECE-001` — MY2023 Wrangler Unlimited Freedom Edition EcoDiesel

- **Exception ID:** `ECE-001`
- **Exception Category:** `missing_configuration` (Manufacturer-only discovery relative to our initial Edmunds-derived inventory)
- **Vehicle / Generation:** Jeep Wrangler JL (Generation PK `32`, UUID `38d3c3ac-f825-4406-abb5-c2d12b9129a4`)
- **Market / Model Year:** United States / MY2023
- **Candidate Reference:** `JL23-ADD-01`
- **Marketed Trim:** `Unlimited Freedom` (Unlimited Freedom Edition)
- **Body Style:** 4-Door Unlimited (`JLU`)
- **Manufacturer Model Code:** `JLJL74`
- **Quick Order Package (QOP):** `26F` (`Customer Preferred Package 26F`)
- **Engine:** `EXJ` — 3.0L V6 Turbo Diesel (`EcoDiesel` w/ ESS G3)
- **Transmission:** `DFV` — 8-speed automatic (`8HP75`)
- **Drivetrain:** `4WD`
- **Primary Manufacturer Evidence:**
  - Authentic FCA US LLC **2023 Jeep Wrangler 4-Door Customer Preferred Code Guide** (Reissued `09/14/2022`, page 2, `sha256:f13bb9732eea7bf31b1a0ca1af7c9576fc2ad975eaff742f4ac248ba8c6a1f10`), which explicitly lists Quick Order Package `26F` under model code `JLJL74` pairing the Freedom Edition with the `EXJ` 3.0L V6 Turbo Diesel engine and `DFV` 8HP75 8-speed automatic transmission (MSRP \$49,850 / FWP \$47,639).
- **Discovery Context:**
  - Absent from the initial 65-candidate MY2023 Edmunds-derived consumer inventory (`docs/implementation/handoffs/MY2023_JL/lightweight_ingestion_initial_20261112/`), which included the 2.0L I4 Turbo (`EC1`, `JL23-31`), 3.6L V6 6M (`ERC`, `JL23-32`), and 3.6L V6 eTorque 8A (`ERG`, `JL23-33`) Unlimited Freedom configurations but did not include the 3.0L EcoDiesel (`EXJ`) pairing.
- **Canonical Disposition:**
  - Added to the active MY2023 US Wrangler JL consumer inventory as candidate `JL23-ADD-01`, bound via reviewed manufacturer order-guide correspondence (`source_id = "4-door-9-14-22-pdf"`, model code `JLJL74`, `GenerationCorrespondenceRevision` PK `232`, UUID `6195b3ad-df3a-5ee7-8646-d79c88dfc057`), and atomically promoted to canonical `VehicleDefinition` PK `1068` (UUID `2771f761-8c25-4cc0-983c-1263c9a69c7a`, slug `2023-unlimited-freedom-30l-v6-turbo-diesel-4wd-us-turbo-diesel`, `ImportExecutionReceipt` PK `3350`, UUID `09fdb068-d698-4673-acf3-c8c55f3a731f`).

---

### `ECE-002` — MY2024 Wrangler Sahara 3.6L V6 8-Speed Automatic (`24G`)

- **Exception ID:** `ECE-002`
- **Exception Category:** `missing_configuration` (Manufacturer order-guide union addition absent from the initial Edmunds-derived inventory / inspected Specs & Features extraction; website-wide absence not established)
- **Vehicle / Generation:** Jeep Wrangler JL (Generation PK `32`, UUID `38d3c3ac-f825-4406-abb5-c2d12b9129a4`)
- **Market / Model Year:** United States / MY2024
- **Candidate Reference:** `JL24-18`
- **Canonical MY2024 Marketed Trim:** `Sahara` (owner-required normalization; source transcription retains `Unlimited Sahara`)
- **Body Style:** 4-Door Unlimited (`JLU`)
- **Manufacturer Model Code:** `JLJP74`
- **Quick Order Package (QOP):** `24G` (`Customer Preferred Package 24G`)
- **Engine:** `ERC` — 3.6L V6 24V VVT Engine Upg I w/ ESS
- **Transmission:** `DFT` — 8-speed automatic (`850RE`)
- **Drivetrain:** `4WD`
- **Primary Manufacturer Evidence:**
  - Authentic FCA US LLC **2024 Jeep Wrangler 4-Door Customer Preferred Code Guide** (Issued `04/26/2023`, Page 6, model code `JLJP74`), which explicitly lists Quick Order Package `24G` pairing the Unlimited Sahara with the `ERC` 3.6L V6 24V VVT ESS engine and `DFT` 850RE 8-speed automatic transmission (FWP \$49,519 / MSRP \$51,195; valid for MY2024 under the factory ordering-guide union rule alongside standard `22G` `EC1` + `DFT`). Note that `JLJP74` in the 2024 4-Door Customer Preferred Code Guide (Page 6) offers zero 6-speed manual (`DEM` / `23G`) configuration.
- **Discovery Context:**
  - The initial Edmunds-derived inventory / inspected Sahara Specs & Features extraction (`https://www.edmunds.com/jeep/wrangler/2024/st-401989674/features-specs/`) recorded the standard 2.0L turbo and did not include the `24G` ERC/DFT alternative. This is a bounded inventory/extraction finding, not independently established absence across all Edmunds pages or dates.
- **Canonical Disposition:**
  - Included in the active MY2024 US Wrangler JL consumer candidate inventory (`docs/implementation/handoffs/MY2024_JL/lightweight_ingestion_review_20261113/`) as candidate `JL24-18` under `source_id = "fca_us_2024_jlu_order_guide_transcription"` (`JLJP74`), with pre-validated `CandidateConfigurationDocument` `2.1.0`, proposed `CanonicalImportAdjudication` `1.1`, and proposed `GenerationCorrespondenceReview` `1.0` awaiting owner adjudication and publication authorization.

---

### `ECE-003` — MY2024 Wrangler Jeep Beach 4xe (`29E`)

- **Exception ID:** `ECE-003`
- **Exception Category:** `missing_configuration` (Manufacturer-confirmed addition to the initial working inventory; Specs & Features extraction/selection-view gap, not a verified website-wide omission)
- **Vehicle / Generation:** Jeep Wrangler JL (Generation PK `32`, UUID `38d3c3ac-f825-4406-abb5-c2d12b9129a4`)
- **Market / Model Year:** United States / MY2024
- **Candidate Reference:** `JL24-27`
- **Canonical MY2024 Marketed Trim:** `Jeep Beach 4xe` (owner-required normalization; source transcription retains `Unlimited Jeep Beach 4xe`)
- **Body Style:** 4-Door Unlimited (`JLU`)
- **Manufacturer Model Code:** `JLXL74`
- **Quick Order Package (QOP):** `29E` (`Customer Preferred Package 29E` — Jeep Beach)
- **Engine:** `ECX` — 2.0L I4 DOHC DI Turbo PHEV Engine (`4xe`)
- **Transmission:** `DFY` — 8-speed automatic PHEV (`8P75PH`)
- **Drivetrain:** `4WD`
- **Primary Manufacturer Evidence:**
  - Authentic FCA US LLC **2024 Jeep Wrangler 4-Door Customer Preferred Code Guide** (Reissued `05/14/2024`, Page 17, model code `JLXL74`), which explicitly lists Quick Order Package `29E` (`Jeep Beach 4xe`) pairing model code `JLXL74` with the `ECX` 2.0L I4 DOHC DI Turbo PHEV engine and `DFY` 8P75PH 8-speed PHEV automatic transmission (FWP \$58,231 / MSRP \$60,295; 500-unit limited edition).
- **Discovery Context:**
  - The initial Specs & Features-derived inventory/selection view (`https://www.edmunds.com/jeep/wrangler-4xe/2024/features-specs/`) recorded six 4xe trims and did not extract Jeep Beach. That bounded discovery gap explains why factory transcription added `JL24-27`; it is not proof of absence throughout Edmunds.
  - Subsequent inspection found Jeep Beach on Edmunds' broader trim overview/model surfaces. On 2026-11-13 the [MY2024 4xe trim comparison](https://www.edmunds.com/jeep/wrangler-4xe/2024/trims/) was checked directly: its comparison table includes Wrangler 4xe Jeep Beach among seven trim columns. The source's separate website model grouping does not authorize a separate canonical Wrangler 4xe VehicleModel.
  - Preserve this exception and discovery history as an extraction/selection-view coverage issue; do not relabel it a verified website-wide omission.
- **Canonical Disposition:**
  - Included in the active MY2024 US Wrangler JL consumer candidate inventory (`docs/implementation/handoffs/MY2024_JL/lightweight_ingestion_review_20261113/`) as candidate `JL24-27` under `source_id = "fca_us_2024_jlu_order_guide_transcription"` (`JLXL74`), with pre-validated `CandidateConfigurationDocument` `2.1.0`, proposed `CanonicalImportAdjudication` `1.1`, and proposed `GenerationCorrespondenceReview` `1.0` awaiting owner adjudication and publication authorization.

## 4. MY2024 continuation qualification (2026-11-13)

ECE-002 and ECE-003 preserve **recorded** factory confirmation, not a new independent
PDF verification by the continuation task. Original MY2024 guide PDFs were not
located in the repository; the current artifacts retain local, hash-bound factory
transcriptions. ECE-002 cites the April 26, 2023 guide p6 (JLJP74/24G/ERC/DFT);
ECE-003 cites May 14, 2024 p17 (JLXL74/29E/ECX/DFY; recorded 500-unit edition).
The existing source inventory's later default revision label must not silently
supersede ECE-002's specific earlier revision. Source transcriptions remain unchanged.

The [continuation review](../implementation/handoffs/MY2024_JL/lightweight_ingestion_review_20261113/CONTINUATION_REVIEW_20261113.md)
withdraws final readiness pending body-aware canonical identity approval. These
are still provisional candidates; neither the naming decision nor the corrected
exception wording publishes a correspondence, approves classifications or imports
a configuration. ECE-001 and its MY2023 execution history remain unchanged.
