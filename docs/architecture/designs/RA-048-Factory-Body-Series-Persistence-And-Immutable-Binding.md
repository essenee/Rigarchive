# RA-048 — Minimal Factory Body Configuration Persistence

Created: 2026-11-13
Last Updated: 2026-11-13
Status: Accepted

Authority: the Project Owner's explicit minimal-persistence implementation task on
2026-11-13 supersedes this document's original, unapproved D1–D3 recommendations.
The Project Owner explicitly accepted this minimal implementation on 2026-11-13,
including the final bulk-upsert and partial-save corrections. Downstream imports
and operational writes remain outside this acceptance.
The historical filename is retained to preserve links.

## Immediate milestone

Persist one Generation-scoped `FactoryBodyConfiguration` and one nullable protected
`VehicleDefinition.factory_body_configuration` association. This is canonical storage,
not completion of the Candidate v3 binding, authorization or import workflow.
[ADR-0013](../ADR/ADR-0013-Unified-Factory-Body-Identity.md), RA-045 and the RA-046/047
pure contracts remain unchanged. No other canonical models or FKs are introduced.

## Model and identity

The model inherits the existing integer PK, UUID and timestamp conventions.
`generation` is required, uses PROTECT and reverse name `factory_body_configurations`.
Seven nullable designation groups use explicit CharFields (128 characters):

- `body_style`
- `wheelbase_designation`
- `body_length_designation`
- `roof_height_designation`
- `door_configuration`
- `side_door_arrangement`
- `body_code`, paired with `body_code_namespace`

The paired code uses two scalar columns; it remains one logical body dimension.
Tokens use the existing pure identity grammar. The verified Wrangler tokens are
`two-door` and `four-door`. Blank strings normalize to null; populated designations
must already be canonical tokens. No alias inference, measurements, fabricated
attributes or automatic combination expansion is performed. Null means unspecified,
not universal applicability. Reviewed evidence remains responsible for token meaning.

At least one dimension must be populated. Code and namespace must appear together.
Database checks enforce presence, pairing and nonempty populated strings. An expression
unique constraint on Generation plus the complete eight-column tuple uses COALESCE
with an empty-string sentinel; empty strings are disallowed, so null tuples receive
exact uniqueness under SQLite. Model full_clean validates this constraint before save;
the database constraint also protects against duplicate insert races. No digest is stored.
Sparse and richer tuples remain separate: compatibility never authorizes merging or
establishes distinct physical bodies.

## Vehicle association and correction

`VehicleDefinition.factory_body_configuration` is nullable, blank, PROTECT, with
reverse name `vehicle_definitions`. Existing rows retain null; no backfill is included.
The existing VehicleDefinition Generation remains authoritative. Both clean and save
validate non-null assignments against it. Partial VehicleDefinition saves validate the
effective persisted pair, rather than relying on unsaved fields omitted from update_fields.
Changing a referenced body's Generation must remain consistent with all referring vehicles.
Save transactions lock the body row where supported; SQLite retains its transaction
locking semantics. These validations are model boundaries, not only Admin form rules.

Normal body saves validate the complete tuple. Body bulk writes and partial saves are
rejected; callers use individual complete instance saves. Vehicle bulk body assignment,
bulk creation with a body, and bulk Generation changes of body-associated rows are
rejected. Conflict upserts may not update Generation/body fields even if incoming
objects have null bodies, because existing conflict targets can have a body. Partial
VehicleDefinition saves materialize update_fields once, including iterators. Safe
unrelated conflict updates and legacy null-body bulk workflows remain available. Direct SQL/private ORM
bypasses are not an authorized correction interface; cross-table scope is application
validation, not a new composite database FK.

Ordinary Django Admin permissions govern creation and correction. The Admin displays
Generation and all dimensions, and exposes the VehicleDefinition FK with autocomplete.
Shared body edits show a warning that all referring vehicles are affected; prefer an
incorrect vehicle FK correction or a distinct body record. Protected deletion and
standard Django Admin LogEntry auditing apply. Shared corrections are permitted;
no immutable binding subsystem or new approval workflow is introduced. UUIDs, slugs,
marketed trims and historical provenance are not rewritten by body correction.

## Migration and preserved boundaries

`reference/migrations/0011_factory_body_configuration.py` depends on 0010 and only
creates the body table, adds the nullable VehicleDefinition FK, and adds its constraints.
There is no data migration, backfill or operational application in this milestone.
Tests migrate an isolated database from 0010 to the latest state and compare every
pre-existing table's original columns and values, including historical vehicle identity.

The same body can be reused across trims and years within its Generation. Two-door
and four-door Sport vehicles can retain canonical trim `Sport`. Storage supports
separate associations; the existing slug builder/import identity path is unchanged.
Creating otherwise identical Sport records through that legacy path still needs the
separate body-aware slug/matching/import milestone. This is not executable MY2024
import readiness, nor authorization to change existing Wrangler records.

Candidate v3.0.0 serialization, semantic hashes, A–H fixtures, Candidate 2.1.0 and
receipts are untouched. Existing reviewed evidence may be reused; no new Wrangler
review round is required solely to populate body configuration. Applying the operational
migration and assigning reviewed body records require separate owner authorization,
record selection and preservation checks. No actual Wrangler records are changed here.

## Original proposals: deferred, not approved for implementation

| Original recommendation | Disposition |
| --- | --- |
| D1: controlled Scope-key registry/fields | Deferred; Generation FK is the immediate persistence scope. No registry fields. |
| D2: exact immutable evidence binding snapshot/hash and evidence bridge | Deferred; no snapshot, binding or evidence-reference models. |
| D3: VehicleDefinition binding-revision anchoring | Deferred; no revision FKs. Ordinary validated administrative correction is authorized. |

FactorySeries and its association are deferred. Further evidence binding, canonical
parent resolution, body-aware matching/slugs, publication authorization and Candidate
v3 import execution remain separate milestones. No generalized attribute engine,
new audit models, review rounds or replacement infrastructure is implemented.

See the [implementation handoff](../../implementation/handoffs/RA048_body_series_persistence_20261113/README.md)
for exact files, executed checks and preservation results.
