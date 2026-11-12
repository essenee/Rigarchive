# MY2022 Jeep Wrangler Unlimited High Tide — Canonical Trim Adjudication Decision

**Created**: 2026-11-12  
**Status**: Approved Project Owner Decision  
**Scope**: Model Year 2022 US Jeep Wrangler JL  
**Target Candidate**: `JL22-20` (`JLJL74`, 4-Door, 3.6L V6 eTorque `ERG`, 850RE Automatic `DFT`, QOP `25D`)  

---

## 1. Owner Decision & Policy Mandate

The RigArchive project owner has rendered the following binding architectural decision:

> **MY2022 Wrangler Unlimited High Tide (`JL22-20`) is a distinct canonical marketed trim, following Edmunds.** Preserve that identity. Do not normalize it into Unlimited Sport S. Retain Quick Order Package (QOP) `25D` and Jeep Beach Package `A1A` as supporting manufacturer evidence.

This decision governs all downstream candidate construction, matrix certification, and canonical import execution for candidate `JL22-20`.

---

## 2. Evidence Synthesis & Context

### A. Consumer Marketed Taxonomy (Edmunds Baseline)
In Edmunds' MY2022 Jeep Wrangler taxonomy, the four-door High Tide offering is classified and marketed as an independent trim level:
* **Marketed Trim**: `Unlimited High Tide`
* **Consumer Offering**: Standalone vehicle grade with dedicated standard equipment, distinct pricing ($49,240 starting MSRP), and unique marketed identity.

### B. Manufacturer Production & Order Guide Evidence
Review of the retained FCA US Order Code Guides (February 10, 2022 reissue through June 1, 2022) confirms:
* **Model Code**: `JLJL74` (Wrangler Unlimited 4-Door).
* **Column Taxonomy**: The manufacturer Customer Preferred Code Guide features a dedicated, named marketed column heading: `HIGH TIDE`.
* **Quick Order Package (QOP)**: `25D` (3.6L V6 eTorque Engine Upgrade I `ERG` + 8-Speed Automatic 850RE Transmission `DFT`).
* **Packaging Exclusivity**: Code `25D` is available exclusively under the `HIGH TIDE` column heading.

### C. Manufacturer Public Announcement Evidence
Retained Stellantis Press Release (`stellantis_high_tide_release.txt`, dated Auburn Hills, Mich., Feb. 7, 2022):
* *"Special-edition Wrangler High Tide, available in new High Velocity yellow, will include limited run of 500 Jeep® Beach models in celebration of annual Jeep Beach Week in Daytona Beach, Florida."*
* *"2022 Jeep Wrangler High Tide, equipped for beach life, comes standard with 35-inch tires on beadlock-capable wheels, body-color hardtop with Sunrider Fliptop and Gorilla Glass windshield."*
* Standardizes pricing at $49,240 MSRP, identical to the base price of the first 500 special-run `Jeep Beach` package units (`A1A`).

---

## 3. Structural Canonical Invariants

1. **Identity Preservation**:
   * `candidate_identity.trim_name`: `Unlimited High Tide`
   * Canonical model-year identity remains distinct from `Unlimited Sport` (`JLJL74` QOP `25B`), `Unlimited Sport S` (`JLJL74` QOP `25S`), and `Unlimited Willys` (`JLJL74` QOP `25W`).
   * No synthetic alias or grade normalization is applied.

2. **Powertrain Identity**:
   * Displacement: `3.6` L
   * Cylinders: `6`
   * Engine Aspiration: `naturally_aspirated` (adjudicated from Pentastar architecture)
   * Fuel Type: `gasoline` (adjudicated from manufacturer regular unleaded 87 octane specification)
   * Electrification: `mild_hybrid` (direct evidence from eTorque `ERG` motor-generator system)
   * Transmission: 8-speed automatic (`850RE` / `DFT`)

3. **Packaging Evidence Retained**:
   * QOP `25D` and optional Jeep Beach Package `A1A` are preserved as supporting provenance evidence documents.
   * Neither package code diminishes or supersedes the canonical trim identity.

---

## 4. Downstream Impact

* **Candidate Artifact**: `JL22-20.candidate.2.1.0.json` retains `trim_name = "Unlimited High Tide"`.
* **Adjudication Proposal**: `JL22-20.proposed.adjudication.1.1.json` binds directly to `adjudicated_trim_name = "Unlimited High Tide"`.
* **Matrix Projection**: Generates unique target slug `2022-jeep-wrangler-unlimited-high-tide-3.6l-mhev-4wd` with zero internal or database collisions.
