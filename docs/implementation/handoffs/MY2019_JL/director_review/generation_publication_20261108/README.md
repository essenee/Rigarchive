# MY2019 JL generation correspondence publication

Created: 2026-11-08
Status: Accepted

The owner conditionally authorized publication of the five existing proposals once
all passed validation. Read-only preflight confirmed all five were unpublished,
valid and non-overlapping. The accepted `publish_generation_correspondence`
workflow published each exact proposal with declared director `project_owner`,
agent `codex`, and the owner's explicit authorization supplied as its affirmative
CLI confirmation. Original proposals, reviewer text and evidence were unchanged.

## Results

| Source model code | Result | Revision PK | Publication receipt PK | Candidate coverage |
| --- | --- | --- | --- | --- |
| JLJL72 | Created | 9 | 2857 | 4 |
| JLJL74 | Created | 10 | 2858 | 6 |
| JLJP74 | Created | 11 | 2859 | 5 |
| JLJS72 | Created | 12 | 2860 | 2 |
| JLJS74 | Created | 13 | 2861 | 2 |

Every mapping targets the existing active Jeep Wrangler **JL Generation PK 32,
UUID `38d3c3ac-f825-4406-abb5-c2d12b9129a4`**. Each is narrowly scoped to US MY2019,
with source `reviewed_jeep_order_guide_inventory`, namespace `source_model_code`,
identity type `model_code`, finding `established`, and no additional restrictions.

The proposals retain the director-accepted MY2019 offering inventory and its
actual SHA-256-bound research snapshot, shared per-code selector document and
explicit manufacturer model-code assertions. Applicability and the intended
canonical parent were checked independently of name similarity. Model validation
confirmed active parents, correct UUID/model ownership and target year range.

## Candidate coverage

All **19 completed candidates** now resolve through exactly one of these published
mappings using the existing read-only generation resolver, with basis
`reviewed_source_correspondence`, to the exact JL target above. Both per-row and
shared selector evidence are covered. The correspondence document appears exactly
in every applicable candidate's retained evidence; no year-only fallback, source
revision substitution or implicit publication was used.

This is generation coverage only. No canonical import plan, peer-assessment plan,
final Matrix or import execution was generated. The ten approved ERC findings and
all 19 candidate powertrain classifications were not revisited or altered.

## Integrity and preservation

- Five independent accepted workflow invocations returned successfully. Each
  revision and its receipt were created atomically by the existing service.
- Post-publication inspection found every exact revision UUID/content hash once
  and one original successful creation receipt per revision. No duplicate
  publication or additional no-op receipt was created.
- Correspondence count increased **8 → 13**; receipt count **2,856 → 2,861**.
- VehicleDefinition count remained **793**. Every pre-existing row in every
  application table was compared by column inventory and row hash with a
  consistent pre-publication backup. No pre-existing row changed or disappeared.
- The only additions are the five correspondence rows and five receipt rows.
  SQLite's two related sequence counters advanced normally. All other tables,
  including VehicleDefinitions, migrations and historical audit records, match
  the backup exactly.
- All prior MY2019 handoff files, including proposals, evidence, approved ERC
  adjudications and the 19 selected candidates, retain their original byte hashes.
  The pre-publication backup is preserved and its hash verified.
- SQLite integrity check returned `ok`; foreign-key check returned no violations.
  Django system checks passed using a read-only connection.
- No application code changed, no migration ran, no VehicleDefinition was created,
  and no backfill, canonical planning/import, staging, commit or push occurred.

An initial read-only diagnostic used the wrong reverse-relation accessor while
printing a count, after source/coverage checks had passed. The diagnostic was
corrected before publication; it performed no writes and indicated no application
defect. The publication script repeated all preflight checks successfully.

## Records

- `preflight.json`: exact scope, expected coverage, existing row-hash baseline,
  preserved handoff file hashes, and consistent backup path/hash.
- `results.json`: each proposal path, full revision/receipt UUID, semantic hash,
  canonical target and covered candidate row IDs.
- `workflow_logs/`: actual accepted CLI publication output for each model code.
- `verification.json`: 19 row-level generation resolutions, before/after count
  reconciliation, all-table preservation checks, SQLite checks and final DB hash.

The consistent database backup is under the project-local ignored
`backups/review/` path recorded in `preflight.json`. No backup was replaced.

## Remaining work

There is no remaining blocker to this correspondence-publication task. Fresh
canonical import planning/review and any later exact import authorization require
a separate task. Candidate completeness plus generation coverage does not itself
certify import eligibility or authorize creating canonical configurations.
