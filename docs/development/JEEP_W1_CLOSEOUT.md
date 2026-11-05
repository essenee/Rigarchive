# Jeep Wrangler W1 closeout — 2026-11-04

## Status and scope

W1 is complete as a bounded, evidence-backed two-configuration pilot, not complete Wrangler model-year, trim, body-style, engine or market ingestion. Exactly one MY2018 Sport two-door, 3.6L V6, 4WD, US VehicleDefinition exists under each of JK and JL. Generation lifecycle ranges do not establish catalogue coverage or authorize inferred configurations. No YJ/TJ population, transmission offerings, package persistence or comprehensive Full Specifications schema was implemented.

Migration `reference.0006_generationcorrespondencerevision_and_receipt_resolution` is applied. Earlier implementation checkpoints recording it as unapplied remain historical. Current counts: 700 VehicleDefinitions, 14 Generations, 2,758 execution receipts, three correspondence revisions and 31 corrections.

## Retained manufacturer evidence

Original inputs remain under `storage/acquisition_inputs/jeep_2018/`; content-addressed originals remain under `storage/raw_source_artifacts/`. Local intake metadata records retrieval, publication/revision identity and original URLs; do not reinterpret local intake as a historical publisher download. Official jeep.com documents are accepted as authentic under director policy without redundant independent publisher authentication.

| Publication | Publisher URL | SHA-256 |
| --- | --- | --- |
| 2018 JK brochure, form 74-383-3802 | https://www.jeep.com/content/dam/fca-brands/na/jeep/en_us/global/pdf/brochure/eBrochure%20-%20Jeep%20Wrangler%20JK%20%282018%29_ver01.pdf | `800f8ecd964e4df584cf6c382216f8401c5b273b85befa686faf93f92841a158` |
| 2018 JL reveal brochure, form 74-383-3871 | https://www.jeep.com/content/dam/fca-brands/na/jeep/en_us/global/pdf/brochure/Jeep_Wrangler_JL_Reveal_Brochure_2018.pdf | `711e265443dcf830ee789bdfd8cedd51699ab19a176ccd2718040c11dee20433` |
| Mopar all-new 2018 Wrangler release, published 2017-12-04; retained revision metadata 2026-03-31 | https://www.media.stellantis.com/em-en/stellantis-parts-services/press/mopar-premieres-pair-of-customized-all-new-2018-jeep-wrangler-vehicles-at-la-auto-show | `1378745a03e10f2a60e8080ee09f06b24116b078667057f513a6deecd1f3a4b7` |

JK generation identity includes visual cover evidence absent from its text layer. PDF page 10 Sport standard-equipment/body evidence supports the two-door identity. JL brochure Sport standard equipment supports stock mechanics; the release introduction explicitly identifies an all-new MY2018 two-door Sport. The release's customization qualifier is retained: its accessories do not establish stock mechanical specifications or factory packages. Cross-document applicability was explicitly reviewed, not inferred from matching labels alone. J.D. Power is not required corroboration; conflicting associations are not promoted into configuration evidence. W1 does not claim acquisition or completeness of unavailable J.D. Power documents.

Raw PDFs, page text/layout, visual-review assertions and qualifiers are retained for future technical-specification ingestion. Raw retention does not mean every technical property has a permanent structured representation. W2 must reconcile the retained assertion inventory, applicability and representation gaps before claiming comprehensive Full Specifications coverage.

## Published correspondence and canonical imports

All three correspondence revisions are revision 1, apply only to MY2018/US, and target the existing Wrangler model. Original AI reviewer attribution/timestamps were preserved; publication receipts record genuine current director authorization and execution time.

| Source | Revision PK / UUID | Target Generation | Publication receipt PK |
| --- | --- | --- | --- |
| JK brochure | 1 / `3ecfe94b-a41c-4a85-8610-f7e0913e5e7c` | JK 31 | 2754 |
| JL brochure | 2 / `713135b1-ed92-4257-ad65-7b08302809ad` | JL 32 | 2755 |
| Release-first revised proposal | 3 / `acade427-006b-4ea0-9712-00ba9c9ad0ea` | JL 32 | 2756 |

The approved release-first content hash is `sha256:8b700eda1123f9ac77e2ba2360c74a0f341306fad5f87ac41c4357e5a1da33b2`. The original proposal remains preserved. Full proposal hashes, chain identities, evidence bindings and receipt UUIDs are in `storage/acquisition_inputs/jeep_2018/w1_published_20261104T180404Z/publication_receipts.json` and `verification_and_manifest_inventory.json`.

| Import | VehicleDefinition PK / UUID | Generation | Import receipt PK / UUID |
| --- | --- | --- | --- |
| JK Sport | 714 / `edf85ecf-568a-4d8a-b1b2-936e0a4f49e3` | 31 | 2757 / `53b02b48-ba0d-4c0f-a95d-ea9792d05bbc` |
| JL Sport | 715 / `9bad2422-3c20-4e72-a52b-280080026472` | 32 | 2758 / `bac96e0c-fe99-477b-9bec-fb1e4dff9025` |

Both records: model year 2018, trim `Sport`, engine `3.6L V6`, drivetrain `4WD`, market `US`, slug `2018-sport-36l-v6-4wd-us` within their distinct Generations. Both exact manifest 2.0 imports used `CREATE / first_representation` with reviewed source correspondence. Each creation and success receipt committed atomically; no replacement plan was authorized.

Exact manifest hashes:

- JK: `sha256:def7e528922c833c1f1e2795e89b32f1126571f083f0d68fef44707af7bc0adf`.
- JL: `sha256:e3a8cc11c8fb50b9a1099540cb7b1d6cc9c8ecc1ceb66e13dc97c581387d3f76`.

Manifests remain in `storage/acquisition_inputs/jeep_2018/w1_published_20261104T180404Z/`. Complete import fields, receipts and typed-row preservation results are in `storage/acquisition_inputs/jeep_2018/w1_imported_20261104T185112Z/execution_report.json`.

## Permanent optional-equipment policy

The authoritative [ingestion protocol](INGESTION_PROTOCOL.md#brochure-governed-optional-equipment-policy) already records the manufacturer-neutral policy. Brochure-listed packages, individual options, standard equipment and accessories remain distinct. Accessories absent from the applicable brochure are excluded even when present in manufacturer releases. Vehicle identity and technical specifications may use other authoritative manufacturer publications; identity evidence does not authorize accessory ingestion. No policy rewrite was needed for closeout.

## Catalogue presentation inspection

`GenerationDetailView`, `get_generation_hub_context` and `templates/reference/generation_detail.html` were inspected. Year choices and statistics derive only from active VehicleDefinitions, and trims derive from the selected year's records. No years are generated from Generation ranges.

Both actual Generation pages rendered HTTP 200 for default, MY2018 and unavailable MY2017 requests using read-only SQLite and transient signed-cookie sessions, without middleware/session database writes. Each shows only 2018, Sport after year selection, and counts of one model year/configuration/engine/drivetrain. Invalid MY2017 does not produce a configuration. The header's JK 2007–2018 and JL 2018–present labels describe lifecycle, not populated years.

Presentation ambiguity: “Explore available factory configurations” and unqualified statistic labels can be mistaken for complete manufacturer availability. Proposed minimal follow-up, not implemented: use “Explore configurations currently recorded in RigArchive”, qualify counts as archived records, and state “Generation dates describe lifecycle; catalogue coverage may be partial.” No UI files changed.

## Verification and preservation

Publication and import runs each passed 141 relevant isolated regression tests, system checks and migration-consistency checks. Import verification compared every pre-existing typed database row and retained evidence: only the two approved VehicleDefinitions, their two receipts and expected sequence increments were added.

Closeout reran 144 tests across views, Generation hub, correspondence, projection completeness, canonical execution, equipment policy, Jeep brochures and release identity: all passed. System check passed; migration consistency reported no changes. Tests used an isolated in-memory database, temporary media and persistent-storage deletion guards. All 67 pre-existing acquisition/raw evidence files remained byte-identical. SQLite integrity was OK; foreign-key check found no violations. No full-suite or JavaScript rerun is claimed for closeout; the previously documented unrelated homepage PNG failure remains unresolved.

Closeout development database SHA-256 before/after checks and tests: `ace233ac349ba867572cba2ec07c96c575b96371601f911c7c31ef94abd6aa6b`. This differs from the prior import report's `dcce7cfbe5471a0371ee24ba20ad7515c0a9b9491c3ad694d3a19230aa1e2c80`. Cause is not established; current counts and integrity match, but no task-wide byte preservation across that intervening interval is claimed. No restoration or database modification was performed during closeout. Earlier historical database-hash qualifications remain preserved.

## Next evidence-backed catalogue work

1. Director defines the next bounded model-year/generation/market slice and authorizes acquisition; do not infer coverage from JK/JL dates or assume YJ/TJ boundaries.
2. Retain original manufacturer model-year brochures, specifications and order guides with revisions; enumerate documented trims, two-door/Unlimited distinctions and engine/drivetrain availability. Distinguish grades from packages and do not create Cartesian products.
3. Maintain an explicit coverage ledger of documented, excluded, conflicting and missing configurations. Reconcile each identity dimension and body/trim normalization before candidate construction; preserve unknowns.
4. Extend bounded extraction/normalization only for inspected layouts, with golden tests, complete document-qualified generation evidence and technical-corpus accounting. Review whether new source selectors need separate correspondence revisions; existing MY2018 correspondences authorize no other year.
5. Review and publish only explicitly authorized correspondences. Produce Candidate v2 documents and zero-write exact manifests, obtain separate director authorization, then import through the protected single-plan workflow with receipts and preservation checks. Do not use legacy bootstrap/batch shortcuts.
6. Audit achieved coverage against the retained manufacturer configuration universe, including exclusions, before claiming any model year complete. Full history requires separately evidenced YJ/TJ curation and subsequent source-backed slices. Transmission offerings and factory-package persistence/conditional specifications remain separate ADR-0010 Milestones 2 and 3; comprehensive Full Specifications architecture remains future W2 work.
