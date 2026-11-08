# MY2019 ERC human classifications approved

Created: 2026-11-08
Status: Accepted

The project owner explicitly approved the two proposed classifications for the ten
reviewed US MY2019 Wrangler JL ERC offerings. The existing
`adjudicate_canonical_import --classification-review` workflow recorded each
finding with declared human director `project_owner` and the authorized
`APPROVE CLASSIFICATIONS` confirmation. Each command returned successfully.
No approval mechanism was bypassed and no application code was changed.

**Ten separate approved adjudication 1.1 artifacts and ten separate Candidate
2.1.0 revisions were created. All 19 MY2019 candidates now have complete
structured powertrain identities.**

## Exact approved scope

| Rows | ERC trim/body configurations |
| --- | --- |
| JL19-01, JL19-03, JL19-05 | Sport, Sport S, Rubicon two-door |
| JL19-07, JL19-09, JL19-11 | Unlimited Sport, Sport S, Sport Altitude four-door |
| JL19-13, JL19-15, JL19-17 | Unlimited Sahara, Sahara Altitude, Moab four-door |
| JL19-18 | Unlimited Rubicon four-door |

The approved ERC tuple is:

| Field | Value | Provenance |
| --- | --- | --- |
| `engine_displacement_liters` | `"3.6"` | Retained source evidence |
| `engine_cylinders` | `6` | Retained source evidence |
| `engine_aspiration` | `naturally_aspirated` | Approved human-derived conclusion |
| `fuel_type` | `gasoline` | Retained source evidence |
| `electrification_type` | `none` | Approved human-derived conclusion |

Both human classifications retain **moderate confidence**, the exact reasoning,
source references, applicability and limitations from their proposals. The
approved `evidence_anchors` were checked to equal the proposed anchors unchanged.
This does not assert direct manufacturer wording for either derived conclusion.
The cross-market induction interpretation, equipment-applicability limitations,
catalog provenance and broader MY2019 3.6L hybrid/eTorque scope caveats remain
explicitly retained.

Approval applies only to the exact ten candidate digests and their documented
evidence. No values were propagated to another model year, market, engine or
configuration. The nine existing EC3 artifacts were validated and referenced
without copying, editing or creating new EC3 revisions.

## Artifact index and lineage

- `authorization.json`: owner approval scope and processing record; no inferred
  authority for imports, publication or database writes.
- `adjudications/JL19-*.approved.json`: ten approved findings, with human role,
  recorded timestamp, exact candidate/source bindings and actual semantic hashes.
- `candidates/JL19-*.candidate.json`: ten separate ERC revisions. Original
  candidate references are retained; revised content digests distinguish revisions.
- `approval_index.json`: proposal-to-approval-to-candidate links, including the
  original proposal hashes, approved semantic and byte hashes, candidate semantic
  and byte hashes, and successful workflow outcomes.
- `complete_19_candidate_index.json`: exact paths/digests for the ten new ERC
  revisions plus the nine unchanged EC3 artifacts. This is a completeness inventory,
  not a canonical import plan, engine-peer assessment or Matrix authorization.
- `preservation.json`: actual before/after development database hash and hashes
  for all 184 pre-existing MY2019 handoff files.

The revised candidates retain original source documents and add structured human
declarations. The declaration source ID, qualified references, exact approved-file
hash and semantic adjudication hash keep these conclusions distinct from
manufacturer observations. Subsequent validation checks the full exact projection,
approval, original candidate and retained evidence. Content changes invalidate the
bindings; no source artifact was overwritten or relabelled as direct evidence.

## Verification

- `.venv/bin/python`: Python 3.13.1, Django 6.0.7, pypdf 6.16.1.
- All ten approved adjudications passed approval-required validation.
- All 19 selected candidates passed contract validation, complete five-field
  powertrain validation, actual retained-byte checks and serialization round trips.
- All 19 trim/powertrain tuples are distinct within the reviewed set. This is
  intra-artifact validation, not a fresh canonical peer or import assessment.
- **44 focused tests passed**, zero failures/errors: classification adjudication,
  generation-projection completeness and ingestion serialization. Tests used
  `RIGARCHIVE_TEST_DB_PATH=:memory:` with isolated evidence/media; Django's test
  system check reported zero issues. Synthetic workflow tests do not write the
  development database. No full suite or development migration was run.
- Development database SHA-256 remained
  `b045601a33811b44a443b7c0cc78ce916e9af476cb3c5f4c5b94dc2fdf18e26f`.
  All original proposals, candidates and handoff artifacts remain byte-identical.

## Remaining boundaries

Complete candidate powertrain evidence does not establish canonical import
readiness or authorize execution. Generation-correspondence review/publication,
fresh canonical planning and exact human import authorization remain separate
future tasks. This task generated no real canonical plans, published no
correspondence, performed no canonical import/backfill, and changed no canonical
records. Existing working-tree changes and backups were preserved. No commit or
push was performed.
