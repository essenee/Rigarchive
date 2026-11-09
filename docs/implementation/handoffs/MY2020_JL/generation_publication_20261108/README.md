# MY2020 JL generation correspondences — published and verified

Created: 2026-11-08
Status: Accepted

The owner authorized the exact51 reviewed MY2020 correspondence proposals after
fresh verification. All gates passed. The existing human-authorized
`publish_generation_correspondence` CLI published51 immutable correspondence
revisions, PK14–64, with publication receipts **2881–2931**. Every invocation
returned successfully and each new receipt's outcome is `created`.

All49 approved candidates now resolve through the **actual published database
state**, without a lookup simulation or year-only fallback, to existing active
Wrangler JL Generation PK32 / UUID38d3c3ac-f825-4406-abb5-c2d12b9129a4.

## Exact scope and coverage

| Manufacturer model code | US MY2020 candidates resolved to JL PK32 |
|---|---:|
| JLJL72 | 12 |
| JLJS72 | 3 |
| JLJL74 | 18 |
| JLJP74 | 12 |
| JLJS74 | 4 |
| Total | 49 |

There are51 required source/model keys across20 authentic retained manufacturer
guide PDFs. The five-model-code count is not a five-record publication scope:
retained source IDs distinguish document revisions. Preflight checked the exact
reviewed manifest, candidate/proposal indices, all source bytes and semantic/file
hashes, source namespaces/model keys, US MY2020 scope, active target parents,
exact shared-selector inclusion and absence of existing conflicting/duplicate
records or reused revision/chain UUIDs.

All51 proposals were required: full-set simulation covered all49 candidates, and
removing each proposal in turn caused the accepted resolver to reject missing
coverage for an affected candidate. One exact proposal per retained key was then
published. No source identity was collapsed or evidence assertion changed.
Existing MY2019 correspondences remain unchanged and were not extended to2020.

`publication_results.json` records every source/model key, proposal path/hash,
correspondence/revision UUID, revision PK, receipt PK/UUID, target and candidate
coverage. `publication_records/` retains an individual result for every successful
publication; `workflow_logs/` retains actual CLI output. Declared human director
was `project_owner`, execution agent `codex`, and the owner's explicit authorization
was supplied as affirmative confirmation to each accepted command. The original
proposal payloads, including historical wording describing their then-unpublished
status, were preserved exactly. Successful current publication is established by
the separate receipts and published records, not by rewriting historical notes.

## Consistent pre-publication backup

Backup location:

`backups/review/MY2020_JL_correspondence_prepublication_20261108T231420638715Z.sqlite3`

SHA256:
`1ed8d207e4300de4a8eb164c1c958e8545fd709704e137cbd3394226caffa014`

SQLite's backup API copied a read-only source connection to this new ignored
project-local file before any publication. Backup integrity and foreign keys
passed. Schema, every application table's columns/rows, counts and sequence values
matched the live database before execution. The backup was not replaced or changed.
It preserves the live development data; it is not a sanitized Git snapshot and
must not be staged. Retained audit metadata uses hashes of primary-key tuples
and row values rather than private session/account contents.

## Post-publication verification

Counts are now **812 VehicleDefinitions,2931 import execution receipts,64
correspondence revisions**. Exactly51 correspondence records and51 publication
receipts were added. Every new revision payload/hash equals its reviewed proposal,
resolves to the intended existing target and has one successful publication receipt
with matching source identity, review snapshot, hash and human/agent provenance.
There were no additional no-op, rejected or stale-publication receipts.

All49 final candidate resolutions were recomputed using the normal resolver
against published rows, with each returned revision UUID/hash set checked against
the expected exact proposals. Candidate contracts, complete structured powertrain
values, retained byte hashes and approved-human lineage were revalidated. The60
approved classification decisions,43 adjudication evidence revisions, six EC3
identities and three approved Unlimited High Altitude trims remain untouched.

Comparison with the consistent backup verifies **every preexisting row in every
application table unchanged**, including all812 VehicleDefinitions, prior13
correspondences, prior2880 receipts, migrations, sessions and required reference
data. Schema is identical. Only the two authorized table additions and their
normal SQLite sequence advances occurred. No existing canonical row was updated
or deleted. All1124 preexisting MY2020 handoff files retain their byte hashes.

SQLite integrity returned `ok`, foreign-key violations are zero, and Django system
checks passed using a read-only connection. **125 isolated focused tests passed**
after publication. No live migration or database-writing diagnostic was run.
Post-publication liveDB SHA256:
`a39f704c1347baa48b5d3fef2da8f3cac19db7f4f27cefd8ce954636cead410f`.

The live database intentionally differs from the sanitized tracked snapshot and
was neither replaced nor staged. The only live writes were through the existing
publication CLI. No application code, architecture, contract, migration, candidate,
classification, trim identity, source assertion or original review artifact changed.

## Review records and next boundary

- `preflight.json`: all fresh verification gates, exact51 proposals, full-set
  simulation, necessity proof, baseline counts and consistent backup.
- `preservation_baseline.json`: preexisting artifact hashes, backup pin and schema/
  table preservation hashes; private row identifiers are hashed.
- `publication_results.json`, `publication_records/`, `workflow_logs/`: exact
  publication outcomes and accepted-workflow audit provenance.
- `postpublication_verification.json`: all49 real resolutions, receipt/record
  bindings, all-table comparison, source preservation and DB checks.
- `focused_test_results.txt`, `final_verification.json`, `artifact_hashes.json`:
  actual checks and completed checkpoint integrity.

No publication-condition failure or execution deviation occurred. No generation
correspondence blocker remains for this49-candidate set. Fresh Matrix2.1 scope,
engine proof, canonical peer/identity assessment and create-only planning remain
separate tasks requiring authorization; publication does not certify import
eligibility. No Matrix was certified, no canonical import plan or import was
executed, no VehicleDefinition created/modified, and no backfill, commit or push
occurred. Current state/changelog and the task completion record document the
verified publication milestone.
