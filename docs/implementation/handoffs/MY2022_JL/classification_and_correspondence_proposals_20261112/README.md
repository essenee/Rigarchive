# MY2022 Jeep Wrangler JL — Classification Adjudication Proposals & Corrected Correspondence Review

**Created**: 2026-11-12  
**Status**: Draft Handoff Prepared (Zero Database Writes; Awaiting Human Director Sign-Off)  
**Target Generation**: Jeep Wrangler JL (Generation PK 32 / UUID `38d3c3ac-f825-4406-abb5-c2d12b9129a4`)  

---

## Executive Summary

This handoff packages the complete, evidence-backed deliverables required to advance the 55 provisional MY2022 US Jeep Wrangler JL candidates toward canonical database import readiness, strictly observing all data-preservation, attribution, and governance boundaries.

1. **Powertrain Classification Adjudication Proposals (Item 2)**:
   * **55 Schema-Valid Proposals Generated**: Covering all 55 consumer candidates (`JL22-01` through `JL22-56`, excluding deferred Sport RHD `JL22-53`).
   * **112 Missing Fields Reconciled**: Formally proposed values for all 112 null powertrain attributes across all 12 review groups and all 6 engine families (`EC1`, `ERC`, `ERG`, `EXJ`, `ECX`, `ESG`).
   * **Evidence Anchors**: Bound to official FCA US MY2022 technical specifications (`2022_JP_Wrangler_SP.pdf`), authentic order-guide powertrain segments, and the Stellantis High Tide announcement.
   * **Attribution**: All 55 proposals are non-publishable drafts designated with `operator_label = "pending_human_signoff"` and `adjudication_decision = "proposed_classifications"`.
   * **Projection**: In-memory projection confirms 100% resolution to complete 5-field canonical powertrain tuples with zero remaining nulls.

2. **ERC vs. ERG Powertrain Verification (Item 3)**:
   * Rigorous engineering report in [ERC_VS_ERG_VERIFICATION.md](ERC_VS_ERG_VERIFICATION.md) confirming the physical and electrical distinction between Pentastar 3.6L V6 conventional ESS (`ERC`, manual / conventional auto, `electrification_type = none`) and eTorque mild-hybrid (`ERG`, 850RE automatic only, `electrification_type = mild_hybrid`).

3. **High Tide Trim Decision Formally Documented (Item 4)**:
   * Formal decision record in [HIGH_TIDE_CANONICAL_TRIM_DECISION.md](HIGH_TIDE_CANONICAL_TRIM_DECISION.md) documenting the approved project owner decision that `Unlimited High Tide` (`JL22-20`) is a distinct canonical marketed trim following Edmunds, retaining QOP `25D` and Jeep Beach Package `A1A` as supporting manufacturer evidence without normalizing into `Unlimited Sport S`.

4. **Corrected Generation Correspondence Proposal Drafts (Item 5)**:
   * **72 Draft Proposals Corrected**: Reconstructed across 18 manufacturer order-guide PDFs.
   * **Automated Agent Attribution Eliminated**: Replaced former automated agent references in `reviewer` with `pending_human_signoff`.
   * **Integrity & UUIDs**: All 72 `revision_uuid` and `correspondence_uuid` values verified unique with zero collisions against `db.sqlite3`. All content hashes recomputed and validated against `digest(payload)`.

5. **Shared Selector Documents**:
   * 72 selector documents (`shared_selectors/*.document.json`) copied and 100% byte-verified against retained source PDFs in `BASE_DIR`.

6. **Safety & Database Invariants**:
   * **Zero Database Writes**: Operational database `db.sqlite3` is byte-preserved with existing counts intact (**934** `VehicleDefinition`, **3,148** `ImportExecutionReceipt`, **159** `GenerationCorrespondenceRevision`).
   * **Zero Overwrites**: All existing lightweight candidate artifacts in `lightweight_candidates_20261109/` remain byte-identical.
   * **Zero Git Commits**: Repository working tree remains uncommitted for human director review.

---

## Deliverable Manifest

| Directory / File | Description |
| :--- | :--- |
| `classification_proposals/` | 55 evidence-backed classification adjudication proposals (`.proposed.adjudication.1.1.json`) |
| `correspondence_proposals/` | 72 corrected generation correspondence proposal drafts (`.review.json`) |
| `shared_selectors/` | 72 byte-verified shared selector documents (`.document.json`) |
| `HIGH_TIDE_CANONICAL_TRIM_DECISION.md` | Formal documentation of the approved High Tide canonical trim decision |
| `ERC_VS_ERG_VERIFICATION.md` | Technical verification of ERC (conventional ESS) vs ERG (eTorque mild-hybrid) |
| `FINALIZATION_AND_AUTHORIZATION_GUIDE.md` | Human director step-by-step instructions for proposal approval and CLI execution |
| `classification_proposals_manifest.json` / `.csv` | Machine-readable inventory of all 55 candidates and 112 adjudicated fields |
| `correspondence_coverage_matrix.json` / `.csv` | Matrix of all 72 correspondence keys, UUIDs, hashes, and source guide dates |
| `shared_selectors_manifest.json` | Manifest of all 72 shared selector documents and raw artifact hashes |
| `validation_report.json` / `.md` | Comprehensive validation results running real Django contracts |

---

## Powertrain Classification Resolution Summary

| Engine Code | Displacement & Layout | Marketed Powertrain Family | Adjudicated Field(s) | Proposed Value | Candidates | Total Entries |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **`EC1`** | 2.0L I-4 Turbo | 2.0L Turbo I-4 with ESS | `electrification_type`<br>`fuel_type` | `none`<br>`gasoline` | 14 | 28 |
| **`ERC`** | 3.6L V-6 Pentastar | 3.6L V6 Upgrade I with ESS | `engine_aspiration`<br>`fuel_type`<br>`electrification_type` | `naturally_aspirated`<br>`gasoline`<br>`none` | 13 | 39 |
| **`ERG`** | 3.6L V-6 Pentastar | 3.6L V6 eTorque Upgrade I | `engine_aspiration`<br>`fuel_type` | `naturally_aspirated`<br>`gasoline` | 15 | 30 |
| **`EXJ`** | 3.0L V-6 EcoDiesel | 3.0L V6 Turbo Diesel with ESS | `electrification_type` | `none` | 9 | 9 |
| **`ECX`** | 2.0L I-4 Turbo PHEV | 2.0L Turbo 4xe Plug-In Hybrid | `fuel_type` | `gasoline` | 3 | 3 |
| **`ESG`** | 6.4L V-8 HEMI | 6.4L V8 Rubicon 392 | `engine_aspiration`<br>`fuel_type`<br>`electrification_type` | `naturally_aspirated`<br>`gasoline`<br>`none` | 1 | 3 |
| **Total** | — | **6 Engine Families** | **3 Controlled Taxonomies** | — | **55** | **112** |
