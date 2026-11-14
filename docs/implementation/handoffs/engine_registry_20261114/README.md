# Human-maintained Engine registry — implementation handoff

Created: 2026-11-14
Last Updated: 2026-11-14
Status: Accepted

Accepted by the Project Owner's conditional authorization on 2026-11-14 after
final correction and successful focused, targeted and complete-suite verification.
Operational deployment remains separately authorized. Baseline `main`, HEAD
`1a430ac80229b8daa86101dd27a9f0ababbdf663`. RA-050 work is preserved unchanged.
No external research or repeated engine classification occurred.

## Model and maintenance

`Engine` inherits existing BigAutoField PK, unique UUID and creation/update timestamps.

| Field | Definition |
| --- | --- |
| manufacturer | Required protected Manufacturer FK; no model/year restrictions |
| engine_code | CharField(100); surrounding whitespace stripped, ASCII uppercase; letters/digits plus internal dot/dash/underscore |
| name | Required CharField(100), nonblank human description |
| engine_displacement_liters | Existing DecimalField(5,2), nullable, minimum 0.01 L |
| engine_cylinders | Existing nullable PositiveSmallIntegerField, minimum 1 |
| engine_aspiration | Existing nullable CharField(24), unchanged aspiration choices |
| fuel_type | Existing nullable CharField(24), gasoline/diesel |
| electrification_type | Existing nullable CharField(24), unchanged none/MHEV/HEV/PHEV tokens |

Five tracked field definitions are identical to VehicleDefinition's, verified by
field-deconstruction tests. No transmission parameters or new classifications.
Database constraints enforce manufacturer/normalized-code uniqueness, canonical code
spelling, nonempty name, positive displacement/cylinders and valid controlled tokens.
The SQLite spelling check uses built-in GLOB/UPPER/TRIM, not a connection-local
REGEXP function, so existing plain-SQLite recovery snapshots remain usable.
Model validation rejects boolean values and applies existing powertrain semantics.
Incomplete human records may be maintained, but cannot supply a construction identity.

The **complete normalized manufacturer code** is the Engine identity within its
manufacturer namespace. `ea888-cjxc` normalizes to `EA888-CJXC`; internal hyphens,
other supported separators and meaningful suffixes are preserved. `EA888-CJXC` and
`EA888-CHHB` coexist as separate records even when their tracked parameters agree.
Lookup never falls back to `EA888` or removes separators. Empty/non-ASCII codes,
internal whitespace and unsupported characters are rejected. The prior normalizer
and built-in database constraint already supported hyphens; this final correction
makes that policy explicit and adds four focused regression methods. No schema
change or Volkswagen seed data was introduced.

Manufacturer, code and UUID are immutable on saved Engine instances. Partial/bulk
Engine writes are rejected; use validated individual saves. No generalized code-reuse
exception framework is introduced. The recognized BMW exception remains a future
explicit handling decision if encountered; a conflicting code is never auto-merged.

Admin exposes authoring, property correction, manufacturer filter/search, code/name
search, UUID and timestamps. Manufacturer/code are read-only after creation. Existing
Django permissions and LogEntry auditing apply; no independent approval subsystem.

## Vehicle and lookup behavior

`VehicleDefinition.engine` is nullable, blank, protected. New engine-associated
construction copies missing compatibility snapshots from the registered row and
rejects explicit disagreements or a different manufacturer. Existing slugs, UUIDs,
labels and historical records are not regenerated. Existing matching snapshots can
receive the association without changing their identity; no assignments were made.
Registry edits do not cascade into old vehicle snapshots or receipts, and unrelated
saves of historical snapshots remain valid. Engine properties are read-only on the
Admin view of an engine-associated vehicle. Partial saves validate the effective
persisted association/snapshot, and supported bulk paths cannot bypass the checks.

`reference.engine_registry.resolve_engine(manufacturer, engine_code,
incoming_powertrain=...)` returns the existing complete Engine without source lookup,
new approval or record creation. Supplied properties use the existing normalized
five-field vocabulary; null means no incoming claim. It returns these explicit errors:

- `ENGINE_NOT_REGISTERED`: unknown manufacturer/code.
- `ENGINE_REGISTRY_CONFLICT`: explicit supplied property contradicts the registry.
- `ENGINE_REGISTRY_INCOMPLETE`: authored record lacks a complete supported identity.

`prepare_registered_vehicle(...)` returns an **unsaved** VehicleDefinition with the
Engine FK and authoritative snapshots. It checks both supplied-property dictionaries
independently so one cannot hide another's conflict. It is a bounded construction
helper, not an import executor, candidate converter, or authorization path.

## RA-049 compatibility boundary

Candidate v3 wire bytes/hashes and accepted versioned contracts remain unchanged.
Legacy Candidate 2.1.0 and existing import behavior are preserved. No existing planner
or executor silently adds an Engine association.

Full RA-049 registry integration is stopped at a specific contract boundary:
`TargetFields`, Plan3/Proof3 state, revalidation, exact Matrix authorization and receipt
snapshots do not pin Engine UUID, registered properties/update state or registry
classification authority. Candidate v3 evidence interpretation cannot claim an
unrecognized registry finding is approved. Attaching the FK after approval or
replacing candidate values would escape the authorized snapshot/hash and stale-state
checks. The bounded helper works now for authorized callers; accepted RA-049 remains
unchanged and fails closed on unknown registry wire fields. Production integration
requires an explicitly authorized scoped contract/adapter change with exact registry
state and classification meaning pinned; no redesign was attempted here.

## Migration and seed proposal

`reference/migrations/0012_engine_registry.py` depends on 0011. It creates Engine,
adds the nullable protected FK and constraints, and updates only the existing engine
name help text. No data migration, seeding, backfill or operational application.
An isolated migration test compares every old table's original columns/values across
0011→0012, verifies the old vehicle FK remains null and Engine starts empty.

[Wrangler seed proposal](wrangler_engine_seed_proposal.json) contains seven authorable
records, using existing published canonical values and attributable receipt evidence:

| Code | Liters | Cylinders | Aspiration | Fuel | Electrification |
| --- | ---: | ---: | --- | --- | --- |
| EC1 | 2 | 4 | turbocharged | gasoline | none |
| EC3 | 2 | 4 | turbocharged | gasoline | mild_hybrid |
| ECX | 2 | 4 | turbocharged | gasoline | plug_in_hybrid |
| ERC | 3.6 | 6 | naturally_aspirated | gasoline | none |
| ERG | 3.6 | 6 | naturally_aspirated | gasoline | mild_hybrid |
| ESG | 6.4 | 8 | naturally_aspirated | gasoline | none |
| EXJ | 3 | 6 | turbocharged | diesel | none |

EXJ is the additional represented code beyond the requested list. Human-readable
names are existing published descriptor aliases, not new mechanical classifications.
The proposal pins manufacturer identity, vehicle PK/UUID/year, receipt PK/UUID,
candidate digest, receipt snapshot hash and retained qualified code assertions with
verified source-byte hashes. All 134 unambiguously joined supporting published rows
agree with their persisted five-field values; 141 receipt rows without an unambiguous
code join are excluded from seed proof, rather than assigned by engine label/year.
No same-code mechanical conflict was found in that supported set. No new engine
adjudication is performed and no production Engine row is populated.

## Final acceptance verification — 2026-11-14

Fresh isolated verification on the frozen corrected source files:

- **31 focused/backup tests passed in 2.210s** (29 Engine tests and two existing
  preservation tests), including populated-registry plain-SQLite backup.
- **457 targeted reference/import/preservation tests passed in 50.030s**.
- **997 complete Django tests passed in 85.807s**, no failures/errors/skips.
  The complete suite ran once for this final acceptance task.
- `manage.py check`, `makemigrations --check`, `git diff --check` and pre-commit
  staged whitespace checks pass. All Django commands use isolated test DB paths.

Hyphen tests cover both Volkswagen examples, coexistence, case/outer whitespace,
separator/suffix preservation, normalized uniqueness, exact full-code lookup,
non-equivalence of family prefixes, cross-model/year reuse and all seven Jeep codes.
No new evidence adjudication, registry population or operational work occurred.

Acceptance covers the exact nine paths: `reference/models.py`, `reference/admin.py`,
`reference/engine_registry.py`, `reference/migrations/0012_engine_registry.py`,
`reference/tests/test_engine_registry.py`, this README, the unchanged
`wrangler_engine_seed_proposal.json`, and Engine-only hunks in
`docs/implementation/CURRENT_STATE.md` and `CHANGELOG.md`. All other shared-document
changes, RA-050/MY2023/MY2024 material, research, scratch and operational DB files
are excluded. The local commit is authorized as
`Add human-maintained Engine reference registry`; no push is authorized.

## Historical implementation verification and preservation

Prior implementation verification (before this final acceptance): **27 focused/preservation tests passed** (1.967s), including
25 Engine tests and both existing data-preservation tests. **453 targeted tests
passed** (50.035s), covering model/Admin, registry, migrations, historical import/receipt,
Candidate v3 A–H, RA-048/049, unchanged RA-050 preparation and recovery compatibility.
System check, migration-drift check and `git diff --check` pass.

During that prior implementation task, the full suite ran **once: 992 tests in 87.178s, one error** in the existing physical
snapshot command. The initial new code constraint depended on SQLite REGEXP, which
the command's plain SQLite connection does not supply. Replaced that constraint with
equivalent built-in GLOB/UPPER/TRIM checks without changing backup infrastructure.
Added a populated-registry plain-SQLite backup regression and reran focused/targeted
checks successfully. That implementation task did not repeat the full suite, per the owner's then-applicable limit. Two early
focused test-expectation/fixture errors were corrected before the original 24-test
and 450-regression passing runs; neither required a change to historical behavior.

Isolated database
paths use `RIGARCHIVE_TEST_DB_PATH`; the existing explicitly authorized
`.venv/bin/python` fallback is Python 3.13.1/Django 6.0.7 because `venv/py313` remains
absent. No packages were installed.

Files changed: `reference/models.py`, `reference/admin.py`,
`reference/engine_registry.py`, `reference/migrations/0012_engine_registry.py`,
`reference/tests/test_engine_registry.py`, this handoff and its seed proposal,
and only Engine milestone additions in CURRENT_STATE/CHANGELOG.

Operational DB SHA-256 before and after:
`be3b1cfe8f03feda457f2aa7ef397b96f2cd673971aaf6a999c171c5523b32a6`.
No operational migration, Engine population, historical FK assignment, receipt/slug
rewrite, production Matrix or MY2024 publication. The final acceptance task permits
only the exact local acceptance commit listed above; no push.

The only owner follow-up beyond separately authorized deployment/
seed population is the bounded RA-049 registry-state/authority consumption decision.
Other Wrangler evidence dependencies do not extend this task.
