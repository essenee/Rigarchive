# MY2021 JL generation correspondence publication

Created: 2026-11-09
Status: Accepted — published atomically and independently verified

The owner-authorized exact **95 MY2021 correspondence proposals** were published
through the existing human-confirmed CLI/service in **one outer durable Django
transaction**. Results are **95 new immutable correspondence revisions, PK 65–159**,
and **95 publication receipts, PK 2981–3075**. All outcomes are `created`; no
additional rejected, stale or no-op publication receipt remains.

All **73 current MY2021 consumer Candidate 2.1.0 artifacts** now resolve through
the **actual committed published database state**, without simulated lookup or
year-only fallback, to existing active Wrangler JL **Generation PK 32 / UUID
`38d3c3ac-f825-4406-abb5-c2d12b9129a4`**. Exact returned revision UUID/hash sets
match the approved proposals for each candidate. No candidate is unresolved or
targets another Generation.

Final totals: **861 VehicleDefinitions, 3,075 audit receipts and 159 published
correspondences**. The only database additions are 95 correspondence rows and
95 publication receipts, plus normal sequence advances. Every preexisting row
in every table, and the schema, remain unchanged.

## Exact approved coverage

| Manufacturer code | New correspondence keys | Current candidates resolved |
| --- | ---: | ---: |
| JLJL72 | 13 | 20 |
| JLJL74 | 14 | 31 |
| JLJP74 | 14 | 11 |
| JLJS72 | 13 | 3 |
| JLJS74 | 14 | 4 |
| JLJX74 | 9 | 1 |
| JLXP74 | 9 | 2 |
| JLXS74 | 9 | 1 |
| Total | 95 | 73 |

Scope remains **23 two-door / 50 four-door**, with all **24 approved body/trim
labels**, all complete five-field powertrain identities and all earlier-supported
combinations. Exact source/model keys, 95 shared selector documents and all
candidate-specific source assertions were preserved. No prior-year mapping was
extended or reused; each new record is restricted to **US MY2021**.

All 88 original approved classification decisions, the additional 392 gasoline
approval and its premium-91-octane evidence, and direct ECX technical evidence
remain unchanged. Sport RHD JL21-71 / JLUL74 and CLASS-075 remain separately
preserved/deferred and outside candidate/correspondence publication scope.

## Preflight, backup and atomic publication

Fresh preflight verified the entire original review manifest, all 95 proposal
payload/file hashes and UUIDs, all 95 distinct keys and target UUIDs, exact selector
inclusion for every matching candidate, absence of existing overlapping keys or
UUID/chain reuse, all 73 current candidate digests, prior approval claims, active
canonical parents and current database counts. The original unchanged resolver
again resolved all 73 against unsaved proposals; removing each of the 95 proposals
individually still failed required coverage. No source/identity/scope discrepancy
was found.

The existing `snapshot_db` Layer 1 procedure created a new `VACUUM INTO` backup
from a **read-only live SQLite URI** before publication. Backup integrity, foreign
keys, schema, every application table/row hash and sequence values matched live
state. The source database hash remained unchanged during backup preparation.

Backup location:

`/Users/cosmo/dev/Rigarchive/backups/review/MY2021_JL_correspondence_prepublication_20261109T154455104372Z.sqlite3`

Backup SHA-256:

`06502534d35395b97d74447b98c760f237a1e2aba04860f32d349fab62bd1d92`

The backup is a complete local recovery file in ignored `backups/review/` storage.
It has not been replaced, altered or staged. Its hash was checked again after
publication and tests. `backup_reference.json` and `preservation_baseline.json`
retain the exact pin and hashed all-table baseline without printing private rows.

Publication supplied the owner's explicit confirmation to the existing
`publish_generation_correspondence` command, declaring human `project_owner` and
agent `codex`. All 95 command/service calls ran on the same Django connection
inside `transaction.atomic(durable=True)`. Each outcome had to be a new `created`
revision and matching receipt; any command failure, service rejection, unexpected
count, source drift, failed actual resolution or preservation/integrity failure
would raise and roll back the whole batch. No separate child process committed
individual proposals. Success records were written only after the outer commit.

Before commit, all 73 real resolutions, exact totals, all-table preservation,
integrity, foreign keys and original file hashes passed. Independent post-commit
verification then repeated actual resolution and proposal/receipt reconciliation
through read-only live connections. Original proposal payloads retain their
historical unpublished-review wording; actual publication is established by the
new persisted revisions and receipts, not by rewriting those proposal notes.

## Resolved pre-write diagnostic

The first execution attempt stopped **before any publication call** at a task-local
snapshot comparison. Django's SQLite declared-type conversion, notably bool/date,
gave different Python representations from the plain SQLite backup reader. An
independent comparison confirmed that the live database still exactly matched
the verified pre-publication baseline; no proposal had failed or been published.

The artifact driver's hash comparison was corrected to read identical native
SQLite values through no-op SQL expressions. A regression verifies equality across
both connection types. The unchanged live database and original backup then
matched the original baseline on both readers, and the same exact authorized batch
proceeded. No application, accepted contract or resolver was modified. Original
failure/diagnostic logs remain retained. No proposal failed during publication,
and no retry of an already-published proposal occurred.

## Post-publication verification

- All **95 persisted review payloads and hashes** equal their exact approved
  proposals; every new revision has exactly one matching successful publication
  receipt with source identity, approval hash, director and agent provenance.
- All **73 candidates** resolve through actual committed state to JL32 with
  expected exact correspondence UUID/hash bindings.
- All **861 preexisting VehicleDefinitions**, **64 earlier correspondences**,
  **2,980 earlier receipts**, and every other preexisting database row remain
  unchanged. Only the two authorized tables and their sequences gained rows.
- All **1,165 preexisting MY2021 handoff files**, source evidence, current
  candidates, classification approvals and inspected application/contract files
  retain their original hashes.
- SQLite integrity is `ok`; foreign-key violations are zero; live read-only
  Django checks pass. Migration consistency reports no changes; no migration ran.
- **130 isolated focused tests passed**, including five task-local regressions
  for successful batch publication, rollback after CLI/service/verification
  failures, and connection-independent snapshot hashes. The 125 existing focused
  resolver/projection/candidate/approval/serialization tests are included.

Environment: `/Users/cosmo/dev/Rigarchive/.venv/bin/python`, **Python 3.13.1**,
**Django 6.0.7**, **pypdf 6.16.1**. Dependency pins match requirements; no software
was installed or upgraded. Tests used isolated databases and temporary media.

Live database SHA-256 before publication:
`ec1eb2adb8becf62a6d8ef18e5ae2dee37d5049620faaaeec51ab8c69b0ee4f9`.

Live database SHA-256 after publication:
`51cfe5595492b454484f106df9aade9b02e6ded681ce39eaeae3c4590443b975`.

The live database intentionally changed only through this authorized publication;
it was not reset, replaced or restored. `CURRENT_STATE.md` and `CHANGELOG.md`
record the completed milestone. No other preexisting work was discarded. No
application, contract, candidate, schema, canonical plan, Matrix certification,
VehicleDefinition or historical backfill changed. No commit or push occurred.

## Deliverables and next boundary

- `preflight.json`, `environment.json`: exact approval scope, fresh gates and runtime.
- `preservation_baseline.json`, `backup_reference.json`, `backup_command.txt`:
  consistent recovery backup, SHA-256 pin and all-table preservation baseline.
- `publication_results.json`, `publication_records/`, `workflow_logs/`: all 95
  committed revision/receipt PKs and UUIDs, command audit and source-key coverage.
- `complete_95_key_coverage.json` / `.csv`: complete source/model-key-to-publication
  index, candidate coverage, original evidence and review references.
- `proposal_publication_reconciliation.json`: exact approved/published hash equality.
- `candidate_resolution_report.json`: every real published-state resolution.
- `postpublication_verification.json`: totals, database integrity, schema/row/sequence
  preservation and final database/backup hashes.
- `verification_report.md`, test/check logs: actual commands and test outcomes.
- `publication_failure.json`, `prewrite_guard_diagnostic.json`: resolved pre-write
  comparison stop, explicitly not a failed proposal or partial publication.
- `publish_atomic.py`, `test_atomic_publication.py`: task-local orchestration and
  isolated atomicity/snapshot regressions; accepted application code is unchanged.
- `final_verification.json`, `artifact_hashes.json`: final evidence/backup audit and
  hashes of the complete publication checkpoint.

**No correspondence blocker remains for this 73-candidate set.** Fresh Matrix 2.1
assessment/certification and canonical planning/import are separate tasks requiring
explicit owner authorization. Publication does not certify canonical import
eligibility; no such work was performed.
