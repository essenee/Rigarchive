# VehicleDefinition Admin Engine assignment repair

Created: 2026-11-15
Status: Accepted
Disposition: Owner-approved repair unchanged; isolated commit preparation; no operational data assignments.

## Confirmed failure and scope

Django 6.0.7's generated `VehicleDefinitionForm` derives from
`reference/admin.py::VehicleDefinitionAdminForm`. VehicleDefinitionAdmin fieldsets
exclude all five structured powertrain fields; engine-associated records also have
those fields and engine_name marked read-only. This is intentional: registered
properties should not be independently edited in each vehicle's Admin form.

ModelForm constructs the instance with the selected Engine, then calls model
validation before save. `VehicleDefinition.clean()` invokes
`_validate_registry_engine()`, which may raise a field-keyed ValidationError. Django's
`BaseModelForm._update_errors()` then attempts to attach it to a missing form field,
raising ValueError instead of displaying the model validation error.

There is also a distinct synchronization gap: the validator formerly filled missing
snapshot values only when no stored VehicleDefinition existed. Initial Engine
assignment to an existing row with NULL snapshots therefore failed validation rather
than completing the previously unknown fields. There was no later existing-row
synchronization step that save could reach. A correctly matching association already
worked; this is not a failure of every Engine assignment.

Read-only reproduction before changing code, using real Admin-generated forms:

| Existing record / selected Engine | Before repair | After repair, validation only |
| --- | --- | --- |
| PK890, MY2021 Wrangler Sport S / ERC | ValueError: no field named electrification_type. The stored mild_hybrid differs from ERC's none. | Normal non-field conflict error; known hybrid fact retained. |
| PK890 / ERG | Valid; stored tuple matches the registered mild-hybrid tuple. | Still valid; no classification change. |
| PK16, MY2020 Toyota 4Runner SR5 / 1GR-FE | ValueError: no field named engine_displacement_liters; all five snapshots are NULL. | Valid unsaved candidate; registry supplies all five unknowns. |

PK890 and PK16 still have no Engine FK after this diagnostic: no save was performed.
Matching ERG to PK890's registered tuple is not independent proof of original factory
engine code or model-year fitment. Selecting the correct Engine remains the human
administrator's responsibility; this repair does not infer codes from labels/year.

## Authority and snapshot semantics

The registered Engine authors displacement, cylinders, aspiration, fuel and
electrification. VehicleDefinition stores the five compatibility snapshots:
`engine_displacement_liters`, `engine_cylinders`, `engine_aspiration`, `fuel_type`,
`electrification_type`. engine_name is a historical display descriptor/alias; an
existing nonblank label is retained rather than renamed to Engine.name.

RA-044/ADR-0012 distinguish unknown NULL from known `none` and forbid guessed
historical backfills. The accepted Engine registry handoff
`docs/implementation/handoffs/engine_registry_20261114/README.md` establishes registry
authority, explicit-conflict rejection, matching historical associations and no
cascade of registry edits into old snapshots. This task explicitly authorizes a
safe individual-assignment repair, not automatic historical reconciliation.

Completing unknown fields from the explicitly selected authored Engine is consistent
with those rules. Silently replacing mild_hybrid with none, diesel with gasoline or
another known fact is not. No accepted ADR or governance file was changed, and no
automatic overwrite or Wrangler-specific exception was introduced.

## Smallest correction and behavior

`reference/models.py::_validate_registry_engine` remains the single snapshot
validation/completion boundary, called by both clean and save:

- A new record or explicit new Engine association may fill only missing snapshot
  values whose stored value is also unknown. Blank strings normalize to NULL through
  existing model cleaning. Registry identity must be complete and manufacturer match.
- Explicit known disagreements remain `ENGINE_REGISTRY_CONFLICT` errors. Messages now
  identify the attribute, incoming/registered values and selected Engine code, and
  explain that known values are not overwritten. Clearing a known value to disguise
  a conflict as unknown is rejected.
- Existing nonblank display aliases survive assignment, including a retried Admin
  submission with a missing description. If both incoming and stored label are blank,
  Engine.name supplies the default. Stored slug, PK/UUID and unrelated fields remain.
- Changing to another Engine is allowed only when known structured properties agree;
  conflicting properties/manufacturer are rejected, including from existing Engine
  edit forms where snapshot fields are read-only.
- An unchanged association on an unrelated edit is not resynchronized, even after an
  authorized registry property correction. Existing historical snapshots stay valid
  under the established no-cascade rule. Direct explicit snapshot edits still undergo
  existing validation.
- The validator reports which unknown fields it completed. For a partial save,
  `save()` validates the effective persisted association/snapshot and includes only
  those auto-completed fields in update_fields. An Engine FK cannot be persisted with
  the completion silently omitted. Omitted dirty caller fields do not bypass stored
  conflict checks; the existing partial-save regression remains passing.

`reference/admin.py::VehicleDefinitionAdminForm._update_errors` routes model errors
for excluded/read-only fields to non-field errors, prefixing the attribute and
preserving its error code and formatted message. Errors for editable fields retain
Django's normal field handling. Existing non-field errors remain non-field errors.
No validation is suppressed or exception merely swallowed. All five snapshot
attributes can produce the original failure; electrification is only one example.
No snapshot field was exposed for editing to work around the crash.

No synchronization was duplicated in Admin or ingestion services. No Engine record
is created or edited by assignment, no general import fields/identity contracts were
changed, and no schema migration is needed.

## Regression tests and checks

New `reference/tests/test_admin_engine_assignment.py` has 12 tests covering:

- Initial pre-MY2022 Wrangler and non-Wrangler association, all-NULL and partial
  snapshots, preserved historical descriptions and retry with omitted description.
- Known disagreements in every one of the five attributes; the original excluded
  electrification-field ValueError reproduced using Django's unmodified base hook,
  followed by a normal non-field error with preserved code through the custom form.
- Compatible existing-Engine change, incompatible hybrid change, manufacturer
  mismatch and incomplete registry identity: normal Admin errors, never HTTP 500.
- Unchanged association after registry property edits, direct model validation outside
  Admin, safe partial saves and rejection of cleared-known-value conflict bypass.
- Unchanged registry rows during assignment, PK/UUID/slug/body/MSRP/visibility/lifecycle
  and unrelated field preservation.

All 240 focused/regression tests pass: new assignment tests plus Engine registry,
MY2025/MY2026 imports, canonical import/correction lifecycle, visibility, configurator,
homepage, navigation, MSRP and controlled slug editing. Isolated test databases only.
Final full suite: 1,119 tests in 114.183 seconds with exactly the same 25 previously
recorded label/drive-wheel failure entries, no errors or new failures. The full suite
remains non-green; no unrelated failure was altered or suppressed. Current interpreter:
`.venv/bin/python`, Python 3.13.1 / Django 6.0.7. System, migration drift/state,
SQLite integrity/FK and whitespace checks pass. No migration drift or pending
migration. Final database/index hashes and affected record FKs reverified unchanged.

## Operational preservation and remaining questions

Captured the affected records, all nine currently authored Engines and database/index
hashes in `/private/tmp/admin-engine-assignment-baseline.json` before code changes.
Read-only post-repair form validation completed candidate values in memory only.
Affected-record/registry snapshots and the entire development database hash remain
identical; no persistent Engine assignment, bulk rewrite, correction, reconciliation
or migration was executed. Existing staged owner image work and unrelated modified
files are preserved. No dependencies/environment changes, staging, commit, push or
deployment.

No architectural blocker remains for compatible explicit assignments. PK890→ERC is
still incompatible with its recorded hybrid classification: it needs a correct Engine
selection or separately authorized evidence-based historical reconciliation, not a
code exception. This repair does not decide any record's historical source truth or
provide a new workflow for overwriting known facts. Owner manual Admin QA remains.

## Owner-approved commit preparation

The owner approved this repair unchanged after architectural assessment confirmed
that assignment uses the explicit five-field FIELDS boundary. No Full Specs fields,
internal discriminator, new models, fieldsets or future architecture are implemented
or included in this commit.

Prepare only six files: model/Admin correction, regression tests, this report and
repair-only CURRENT_STATE/CHANGELOG sections. The separate index is
`/private/tmp/rigarchive-engine-assignment-repair.index`, based on HEAD 7431af6.
The normal index and intentionally staged Wrangler JK image changes are preserved
byte-for-byte. Database, images, research artifacts and unrelated documentation are
excluded. The isolated staged snapshot independently passes all 240 focused/regression tests,
Django system checks and migration-drift checks. Actual local migration state is
current. Isolated/working whitespace and database integrity/FK checks pass. No full
suite rerun was needed for staging; the documented 1,119-test/25-known-failure baseline
is retained. Normal-index and database hashes are rechecked before handoff.
Proposed commit: `Fix VehicleDefinition Admin Engine assignment validation`.
No commit, push, deployment, migration or development database write performed.
