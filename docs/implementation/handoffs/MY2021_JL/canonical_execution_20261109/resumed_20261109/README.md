# MY2021 JL canonical execution — completed

Created: 2026-11-09
Status: Completed

The owner-authorized exact Matrix `sha256:6926df6c06e4bd471bbda02c67257cf7a7e2999cf5cdfebfc8b06ead31a9996e` committed through the unchanged accepted Matrix 2.1 execution CLI in one durable model-year transaction. Every row was freshly planned against the evolving transaction state; retained standalone planning snapshots were not executed unchanged. There were **73 creations, 73 execution receipts and zero no-ops**, with no blocked/conflicting or unexpected rows.

- VehicleDefinition PKs: **877–949**, all 73 unique UUIDs and deterministic immutable slugs.
- Execution receipt PKs: **3076–3148**.
- Target: Generation **32**, UUID `38d3c3ac-f825-4406-abb5-c2d12b9129a4`.
- Scope: **23 two-door / 50 four-door**, **24 approved labels**, all 73 complete five-field identities.
- Counts: **861 → 934 definitions; 3,075 → 3,148 receipts; 159 → 159 correspondences**.
- Actual fresh-plan creation bases: **1 first representation / 23 source-established grades / 49 mechanical distinctions**. Namespace counts at row creation are 0–72.

## Authorization and preservation

[Reconciled baseline](../../session_reconciliation_20261109/execution_baseline.json) records `sha256:058bbd44e0811c83bf67c916ae92e27b6a0b062c26be031876e9582190e01473`. Pre-import checks compared every table, canonical identities, correspondence targets and receipt lineage, rather than relying on the file hash alone. No intervening unexplained application change was found. No session-row changes occurred during the resumed execution checks. Session changes are permitted only after independent signature/authentication/history/expiry validation; actual phase checks are retained alongside the guard and its eight regression tests.

[Verification](verification.json) confirms all 861 original definitions, 3,075 original receipts and 159 correspondences unchanged, unchanged schemas and all other preexisting non-session rows preserved. Local authentication state is preserved. All 88 prior approved classification decisions, the additional Rubicon 392 gasoline decision with separate premium 91-octane wording, and direct ECX technical evidence remain intact. Original candidate/approval/evidence artifacts and application/contracts are hash-preserved. Sport RHD JLUL74 and CLASS-075 remain excluded and deferred.

The prior stopped attempt and its README/log/hash inventory remain historical evidence. This resumed package records the successful execution; it does not overwrite that attempt.

## Consistent backup

Layer 1 `snapshot_db` backup, verified SQLite integrity, foreign keys, logical contents and unchanged backup hash:

`/Users/cosmo/dev/Rigarchive/backups/review/MY2021_JL_canonical_preimport_20261109T171124979026Z.sqlite3`

`sha256:21bd8db4505b96eff57696d02b5cdf51bdeadd0dae9bddb8aff11b54cc135a97`

See [backup reference](backup_reference.json), [preflight](preflight.json) and [preservation baseline](preservation_baseline.json). The backup preserves operational authentication state and remains ignored by Git.

## Reconciliation and tests

[Complete 73-row JSON mapping](candidate_to_canonical_mapping.json) and [CSV mapping](candidate_to_canonical_mapping.csv) enumerate every PK, UUID, slug, receipt, candidate digest, fresh execution-manifest hash and creation basis. [Committed workflow result](committed_execution.json), [attempt artifacts](attempts/) and [Matrix reconciliation](matrix_reconciliation.json) establish 73 newly-created rows followed by 73 previously-completed receipt matches, without replay. All Engine proof 2.0 and Resolution 1.1 evidence, candidate snapshots and exact published correspondence UUID/hash sets reconcile to receipt lineage.

**165 isolated focused tests passed**, including candidate construction/serialization, five-field classification/adjudication, correspondence/resolver/Matrix contracts, approval/execution and eight session-baseline guard regressions. Django system checks passed; migration dry-run reported no changes. SQLite integrity is `ok`; foreign-key violations: zero. Python **3.13.1**, interpreter `/Users/cosmo/dev/Rigarchive/.venv/bin/python`; Django 6.0.7/pypdf 6.16.1 pins and `pip check` passed. No dependency installation/substitution. Full suite was not rerun. An initial test launcher typo failed before setup; corrected invocation passed all 165 tests; both logs are retained.

No scope deviation or remaining execution blocker. Database changes are the expressly authorized 73 definitions and 73 receipts plus their SQLite sequences. No application/contract/migration/correspondence/classification change, unrelated import, backfill, commit or push.
