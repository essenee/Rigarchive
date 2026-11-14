# RA-056B — intervening database change verification

Created: 2026-11-14
Status: Proposed

**31/31 exact RA-056A-referenced plans remain valid, non-stale CREATE proposals.
Zero blocked, zero slug conflicts. The existing RA-056A approval package remains
valid for explicit owner approval. No Approval1 or execution is authorized here.**

## Database comparison and verified logical change

Historical RA-056 SHA-256:
`46aafa64d6b34f880a441a000675becedb890ff6a225a745208dd00bcb75e5ef`.

Current SHA-256, identical before/after this verification:
`d0274e8748f3f4ff39cdb4f18c822b46461a914d26364c1e505ada0131d43260`.

An exact retained copy with the historical RA-056 hash was not found among project
snapshots or the relevant existing task-level temporary SQLite artifacts. Therefore
an exact byte-for-byte historical comparison or reconstruction was **not possible**.
No database was restored, vacuumed, migrated or copied into operational use.

Compared the current database read-only against the existing RA-053 pre-publication
snapshot:
`backups/snapshots/db_snapshot_pre_ra053_20261114T165126282187Z.sqlite3`, verified
SHA-256 `4f25c195428887d4528d119292bcf5bc2c750992e6482407d1ae7692310523b3`.
Every table/schema was compared by primary-key-ordered rows. The complete logical
difference is:

| Table | Verified difference |
| --- | --- |
| `django_session` | One existing row updated: `session_data` and `expire_date`; no session added/deleted |
| `reference_generationcorrespondencerevision` | Exactly the twelve authorized RA-053 additions, PK243–254; no pre-existing row changed |
| `reference_importexecutionreceipt` | Exactly their twelve authorized publication receipts, PK3351–3362; no pre-existing row changed |
| `sqlite_sequence` | The two corresponding publication-table sequence increments |
| All other tables and schema objects | Unchanged |

The session expiry changed from `2026-11-28 16:23:47.993326` to
`2026-11-28 18:01:43.858984` (stored UTC timestamps). The expiry is not a proven
write-time timestamp. Session keys and session contents are intentionally omitted.
No session payload was decoded and no actor/request is attributed from these data.

RA-053's retained verification records the expected twelve additions and preservation
of every pre-existing row at the `46aafa…` post-publication baseline. The additional
logical difference now found is thus an **unrelated Django session-state update**,
not a vehicle/reference-data change. It is not merely a changed file hash with no
logical change. Exact causation of every changed storage byte, the caller and any
additional storage-only rearrangement cannot be established without the historical
file. This limitation does not prevent direct verification of the exact plan state.

All twelve current publication payloads/content hashes and receipt snapshots still
match the original RA-053 publication artifacts. Counts remain **1,053
VehicleDefinitions, 254 correspondence revisions, 3,362 receipts, seven Engines and
two bodies**. Historical Engine/body assignments remain null; zero MY2024 JL
canonical records. SQLite integrity is `ok`; foreign-key violations are zero.

## Exact artifact and stale-state verification

Verified unchanged identities:

- Approval manifest SHA-256:
  `fb8e3a69066d5ee3b317c5c0eb64a458c9a5fe47590c30cbac6b504ff7cfbd07`.
- Display matrix CSV SHA-256:
  `e3bc6e64c1b07ba5755174587415b8f99453ae9e9d8674fe6cdcded704d13848`.
- Native Matrix3.1 digest:
  `sha256:84c0f0a630e1547593001b7e4ce25158b5f51528633c6f6ce1e2815ac83c44dd`.

The manifest's complete file inventory, human-view hashes, exact RA-055 plan-file
hash, each of its 31 plan hashes and native Matrix reconstruction all matched.
Every plan passed the existing Plan3.1 validator and still specifies CREATE.

Used the read-only reconstruction/equality portion of
`registry_body_import.revalidate`: `RegistryRelease.load()` reloaded the complete
family and current evidence/parents, then `plan_resolved` plus `wrap_plan` were
compared for exact equality with each saved plan. **31 exact matches, zero
STALE_PLAN failures.** These in-memory comparisons are stale-state verification,
not replacement plans: no candidate/plan artifact was regenerated or saved.

The authorization-gated `revalidate(manifest, …)` entry point itself was not invoked:
it requires a real approved runtime manifest/Approval1, which this task forbids
creating. No fake approval or bypass was supplied. Its existing state-comparison
algorithm was used directly; approval verification and transactional execution
remain required in a subsequent separately authorized operation.

The equality checks cover Generation and published correspondence snapshots,
Engine state/bindings, exact body tuple/UUID/update state, source/evidence pins,
complete-family identity, peers, active/inactive slug namespace, proposed fields and
slug. All 31 slugs remain unique with zero current owners/collisions in Generation32.
All 31 body-aware public names were re-derived using `VehicleDefinition.__str__`
from exact plan powertrain/body state and matched the approval CSV.

No saved canonical identity or approved classification changed. A session-table
update does not enter this contract's semantic identity, evidence, parent, peer or
slug snapshots; the exact comparisons confirm it has no material import effect.

## Disposition and preservation

**Ready for approval: 31; blocked: 0.** All plans remain executable inputs subject
to exact human authorization and fresh transactional revalidation at execution.
The existing RA-056A review manifest can proceed directly to owner approval; no
new plan, matrix or evidence package is needed because of the database file hash.

Operational access used SQLite URI `mode=ro` and `PRAGMA query_only=ON`. No application
code, existing artifact or database row was modified. No tests/full suite were run.
Only this requested report was created. All unrelated working changes, including
RA-054/055/056A code and artifacts, are preserved. Git whitespace checks passed;
HEAD is unchanged, the index is empty, and nothing was staged, committed or pushed.
No Approval1, import execution, canonical publication or owner approval was recorded.
