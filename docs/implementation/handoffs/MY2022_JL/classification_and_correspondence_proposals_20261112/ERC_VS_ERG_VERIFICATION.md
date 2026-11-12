# MY2022 Jeep Wrangler JL — ERC vs. ERG Powertrain Verification

**Created**: 2026-11-12  
**Status**: Technical Verification Report  
**Subject**: Physical, Electrical, and Architectural Distinction between Codes `ERC` and `ERG`  

---

## 1. Executive Summary

Both engine codes denote versions of the 3.6-Liter Pentastar V-6 engine (`220 cu. in. / 3,604 cc`, DOHC 24-valve, 60-degree V-type, compression ratio `11.3:1`). However, they represent distinct physical and electrical architectures in the manufacturer's order guides, engineering specifications, and EPA certifications:

* **`ERC` (Engine Stop-Start / Conventional 12V ESS)**:
  * Indicated in order guides as: `3.6L V6 24V VVT ENGINE UPG I W/ESS (ERC)`.
  * Transmission pairing: Standard 6-speed manual (`DEM`, QOP `23x`); optional 8-speed automatic (`DFT` / `850RE`, QOP `24x` in select Willys packages).
  * Electrical architecture: Conventional 12V starting and charging system with 180A alternator and dual 12V battery engine stop-start (ESS).
  * Electrification category: **`none`**.

* **`ERG` (eTorque Mild-Hybrid Assist / 48V MHEV)**:
  * Indicated in order guides as: `3.6L V6 24V VVT ETORQUE ENGINE UPG I (ERG)`.
  * Transmission pairing: Paired exclusively with 8-speed automatic (`DFT` / `850RE`, QOP `25x`).
  * Electrical architecture: 48V mild-hybrid system featuring a liquid-cooled Belt-Start Generator (BSG) / motor-generator unit, 48V Powernet architecture, and a 48V lithium-ion battery pack supplying engine restart and low-speed supplementary launch torque.
  * Electrification category: **`mild_hybrid`**.

---

## 2. Evidence Comparison Matrix

| Engineering Dimension | Code `ERC` (Conventional ESS) | Code `ERG` (eTorque Mild-Hybrid) | Source Evidence Reference |
| :--- | :--- | :--- | :--- |
| **Order Guide Heading** | `3.6L V6 24V VVT ENGINE UPG I W/ESS (ERC)` | `3.6L V6 24V VVT ETORQUE ENGINE UPG I (ERG)` | All 18 retained MY2022 Order Guides (page 2 / page 7) |
| **Quick Order Package Code Family** | `23x` (Manual), `24x` (Auto) | `25x` (Auto only) | Order Guides, Powertrain Matrix Tables |
| **Transmission Availability** | Standard 6-Speed Manual (`DEM`); Select 8-Speed Auto (`DFT`) | Exclusively 8-Speed Auto (`DFT` / `850RE`) | Specifications PDF (`2022_JP_Wrangler_SP`) pages 1, 4 |
| **Availability Specification** | *"Standard (all engine stop-start, MTX only) — Sport, Sahara, Rubicon"* | *"Available (all eTorque mild-hybrid assist, ATX only) — Sport, Sahara, Rubicon"* | Specifications PDF page 1 |
| **EPA Fuel Economy (City/Hwy/Comb)** | `17 / 25 / 20` (2-Door Manual), `17 / 23 / 19` (4-Door Manual) | `18 / 23 / 20` (2-Door Auto eTorque), `19 / 22 / 20` (4-Door Auto eTorque) | Specifications PDF page 2 |
| **Displacement** | 3.6L (3,604 cc / 220 cu. in.) | 3.6L (3,604 cc / 220 cu. in.) | Specifications PDF page 1 |
| **Cylinder Count & Configuration** | 6 Cylinders, 60-degree V | 6 Cylinders, 60-degree V | Specifications PDF page 1 |
| **Aspiration** | Naturally Aspirated (`11.3:1` compression) | Naturally Aspirated (`11.3:1` compression) | Specifications PDF page 1 |
| **Fuel Requirement** | Unleaded regular, 87 octane (R + M)/2 | Unleaded regular, 87 octane (R + M)/2 | Specifications PDF page 1 |
| **Auxiliary Electrical Hardware** | Conventional 180A alternator + 12V auxiliary ESS battery | 48V Belt-Start Generator (BSG) + 48V 430 Wh lithium-ion battery pack | Specifications PDF pages 4, 8; Mopar Technical Documentation |
| **Electrification Classification** | `none` | `mild_hybrid` | RigArchive Powertrain Taxonomy (RA-044) |

---

## 3. Detailed Architectural Findings

### A. Transmission Association Invariance
In MY2022 US order guides:
1. Every candidate equipped with a 6-speed manual transmission (`DEM`) is powered by engine code `ERC`. Zero manual transmission offerings exist with `ERG`.
2. Package `25x` in every guide strictly requires and incorporates `ERG` with the 8-speed automatic transmission (`850RE` / `DFT`).
3. Package `24x` (where offered, such as Willys Sport `24K` or Willys `24W`) pairs `ERC` with the 8-speed automatic transmission (`850RE` / `DFT`), retaining the non-eTorque engine stop-start setup.

### B. Shared Combustion Hardware
Both `ERC` and `ERG` share the identical underlying internal combustion architecture:
* Displacement: `3.6` liters
* Cylinders: `6`
* Aspiration: `naturally_aspirated` (no turbocharger or supercharger)
* Fuel Type: `gasoline` (87 octane regular unleaded minimum)

### C. Independence of Identity
Because `ERC` and `ERG` feature distinct electrification classifications (`none` vs. `mild_hybrid`), they generate distinct canonical configuration signatures under RA-044. For any given trim level (e.g. `Sport S` 4-door):
* `ERC` with 6-speed manual produces slug: `2022-jeep-wrangler-unlimited-sport-s-3.6l-4wd`
* `ERG` with 8-speed auto produces slug: `2022-jeep-wrangler-unlimited-sport-s-3.6l-mhev-4wd`

This distinction is verified against physical evidence and prevents collision between manual/conventional automatic offerings and mild-hybrid automatic offerings.
