# Engine internal variant key — implementation readiness

Created: 2026-11-16
Status: Proposed implementation plan; no implementation or data authorization

## Conclusion and authority

The requested composite identity is feasible with one additive field, replacement
uniqueness constraint and bounded consumer corrections. **It is not safe to relax
manufacturer/code uniqueness while leaving `.first()` resolution unchanged.**
Schema, fail-closed lookup and exact-reference compatibility must be reviewed and
released together. Variant-aware serialized contracts can be a separate checkpoint,
but no nonempty variants should be operationally authored until their consumers
have an approved representation and review path.

The current task establishes the intended identity/field semantics; those do not
need another speculative ADR. Existing authority already establishes human-maintained
registry authoring, no automatic registration, full authentic codes, controlled
five-field snapshots, explicit approval and stable canonical identity:

- `docs/development/INGESTION_PROTOCOL.md`, **Permanent Engine registry rule
  (owner-approved 2026-11-14)**: reuse established registry associations; flag missing,
  ambiguous/conflicting associations; no automatic Engine creation or property invention.
- Accepted ADR-0012 and RA-044 preserve the VehicleDefinition five-field comparison
  boundary; code spelling, variant keys and output values cannot independently create
  new canonical vehicle distinctions.
- `CURRENT_STATE.md`, accepted Engine registry/integration records and
  `tasks/engine-registry-reconciliation-and-display.md` describe the implemented
  registry, pinned references and deferred shared-code variant capability.

The older CURRENT_STATE Engine chapter's “0012 not applied” is a historical checkpoint:
actual local migrations through reference **0014** are applied. The live repository
and read-only database observations below establish implementation state. No governance
file was edited or historical statement silently reconciled.

## Current implementation

| Path / symbol | Actual behavior / impact |
|---|---|
| `reference/models.py:67`, `normalize_engine_code` | ASCII only; strip outer whitespace; uppercase; `[A-Z0-9][A-Z0-9._-]{0,99}`. Preserves full hyphenated codes, never prefix aliases. |
| Same, `Engine` at 112, `Meta.constraints` at 134 | No variant field. Functional uniqueness on manufacturer + `Upper(Trim(engine_code))`; SQLite built-in normalization/character checks. |
| Same, `Engine.clean_fields/clean/save`, 144–170 | Code normalization; five-field validation; manufacturer/code/UUID immutable; transaction and existing-row lock; full individual saves required. |
| Same, `EngineQuerySet` at 101 | Bulk create/update and QuerySet.update blocked. Immutability is model/workflow enforcement, not an immutable-column database trigger against arbitrary SQL. |
| `reference/engine_registry.py`, `resolve_engine` | Manufacturer/code `.first()` currently relies on uniqueness; validates explicit incoming known properties and complete registered tuple. No creation. |
| Same, `prepare_registered_vehicle` | Resolves code, separately checks incoming claims and explicit five fields, returns unsaved vehicle. Repeats code lookup; no variant argument. |
| `reference/models.py`, `VehicleDefinition._validate_registry_engine/save` | Protected FK; exact engine ID lookup, manufacturer/known-value checks, unknown-only completion on new association. No automatic cascade or old-name/slug rewriting. |
| `reference/admin.py:208`, `EngineAdmin` | Code/manufacturer readonly on change; list/search code/name/five properties. VehicleDefinition engine uses Admin autocomplete. |
| `reference/engine_reconciliation.py`, `_engine`, `_receipt_pins`, `preview_engine_assignments` | `_engine` already emits `internal_variant_key=getattr(engine, ..., '')`. Explicit PK/UUID receipt pins and existing FKs take precedence; names/ESS aliases remain bounded. |
| `reference/engine_assignment.py`, `validate_assignments/execute_assignments/canonical_state` | Executor pinned to original 507-row artifact and approval digest. Uses exact PK/UUID and full preservation guard. `canonical_state` takes all concrete Engine fields via `.values()`. |
| `reference/management/commands/{preview_engine_assignments,assign_registered_engines}.py` | Read-only preview / separately authorized pinned executor; do not repurpose old approval for variants. |
| `reference/my2025_wrangler_import.py`, `preview/execute/snapshot` | Requires one registry row per manufacturer/code; snapshots every concrete field; rebuilds preview and exact plan hash at execution. |
| `reference/my2026_wrangler_import.py`, `preview/execute` | Similar full snapshots/unique-code assumptions; source inventory additionally checks established Engine PK/UUID and `EXPECTED_ENGINE_PKS`. Those exact references must not be discarded by a subsequent code-only lookup. |
| `reference/ingestion/importing/registry_body_import.py`, `Binding`, `engine_binding`, `_conflicts`, `prepare_registry_candidate`, `RegistryRelease._read_candidate` | Closed registry-aware 3.1.0 wrappers bind manufacturer, Engine PK/UUID, full code/name/properties/update time. Current loading/compatibility checks re-resolve by code despite the exact pin. |
| `reference/my2021_wrangler_revalidation.py`, `identity/evaluate/validate_compact`; MY2022 counterpart | Compact identity includes Engine PK/UUID and existing five properties; does not dump every Engine column or resolve by code. |
| `reference/services.py`, `_label_configuration_choices`; `reference/powertrain.py`, `engine_label` | Registered name / code / five-property display; no proposed key. Public labels/slugs need no change. |

## Read-only database assessment

Current registry: **ten Engines** (eight Jeep, two Toyota). **1,150** VehicleDefinitions:
**692 linked / 458 unlinked**. Existing Engine association counts:

| PK | Manufacturer | Code | Linked VehicleDefinitions |
|---:|---|---|---:|
| 1 | Jeep | ERC | 158 |
| 2 | Jeep | EC1 | 104 |
| 3 | Jeep | ESG | 9 |
| 4 | Jeep | EC3 | 22 |
| 5 | Jeep | ERG | 55 |
| 6 | Jeep | ECX | 25 |
| 7 | Jeep | EXJ | 40 |
| 8 | Jeep | EGT | 38 |
| 9 | Toyota | 1GR-FE | 241 |
| 10 | Toyota | T24A-FTS | 0 |

PK10 verified: UUID **f65ff3d3-2a11-4934-888c-cbeb647ede61**, Toyota manufacturer
PK17, name `2.4L I4 Turbo`, 2.4L/four/turbocharged/gasoline/none. It is not a hybrid
placeholder. **No proposed variant or automatic assignment is justified by this row.**
It must receive empty key without changing its identity, properties or associations.

No duplicate `(manufacturer_id, upper(trim(engine_code)))` groups exist; therefore
all ten proposed empty-key composite identities are distinct. The database has no
variant column, and its current expression unique index enforces the older identity.
SQLite integrity `ok`, zero FK violations. Verified database SHA-256:
`sha256:23b615b05b7dd670bb4bb1eab2645c0f207d2b6159fff1ee0287c523be2d359a`. The pre-existing ` M db.sqlite3` difference
was present before this audit and is preserved; no assumptions about its disposability.

## Proposed model, validation and migration

Proposed field (not implemented):

```python
internal_variant_key = models.CharField(
    max_length=100, blank=True, null=False, default="",
    help_text="Reviewed internal discriminator; empty means no explicit discriminator is established.",
)
```

Use a small `normalize_internal_variant_key` function alongside code normalization:
require a string and ASCII **before** lowercasing; trim outer whitespace; lowercase;
accept the full match `[a-z0-9_-]{0,100}`. Empty is valid; explicit `None`, booleans,
non-ASCII, internal whitespace, dots, slashes, punctuation/newlines inside a key,
and overlength values reject. No unrequested leading-character rule. Never collapse
hyphens/underscores, derive keys from names/years/output, or modify authentic codes.

Normalize in `clean_fields` before field/constraint validation, then extend `clean`'s
saved-identity comparison to manufacturer/code/**variant**/UUID. Include empty→nonempty
and nonempty→empty immutability. Existing empty keys must not later be renamed to
“gasoline” or “standard” in place. Preserve validated-save locking and bulk-write
restrictions. Raw SQL bypass of model identity protection remains outside ordinary
registry authoring; no new trigger framework is proposed.

Replace the old unique constraint with, for example:

```python
models.UniqueConstraint(
    models.F("manufacturer"),
    Upper(Trim("engine_code")),
    Lower(Trim("internal_variant_key")),
    name="reference_unique_engine_manufacturer_code_variant",
)
```

Keep the current code-normalization constraint unchanged. Add a variant storage check
for canonical lowercase trimmed ASCII/allowed characters and length <=100, explicitly
allowing empty. SQLite `varchar(100)` alone does not enforce length. Follow existing
built-in SQLite character-check conventions; do not introduce a REGEXP dependency
that breaks ordinary SQLite backup integrity checks. Exercise bound values during
`full_clean`: `EngineCodeCharacters.as_sql` duplicates params for its existing
**two-use** expression template; it cannot be reused blindly for a one-use template.
Backend-specific GLOB portability is an existing limitation, not authorization to
redesign database infrastructure here.

Next additive migration is expected to be reference **0015**, subject to the actual
migration graph at implementation time. Add the non-null default-empty field and
replace uniqueness/add checks transactionally. No RunPython authoring/merging/rebinding
step is needed. All ten records gain only `""`; PKs, UUIDs, codes, timestamps, five
properties and every FK remain unchanged. SQLite constraint operations can rebuild
tables, so verify all old columns and relations on an isolated pre-migration copy,
not just row counts. Do not edit 0012 or any committed migration. Operational migration
requires separate explicit backup/write authorization; none is granted by this plan.

## Resolution semantics

Recommended API shape: `resolve_engine(..., internal_variant_key=UNSET,
incoming_powertrain=None)`, with the same explicit sentinel passed through
`prepare_registered_vehicle`. Omitted is not `None` or an explicitly supplied empty string.

| Input | Required behavior |
|---|---|
| Explicit `""` | Exact manufacturer/normalized-code/empty-key lookup; no named-variant fallback. |
| Explicit nonempty key | Normalize and resolve that exact composite; missing key fails, no registration. |
| Omitted key | Cardinality check across all same-manufacturer/code rows; zero missing, one candidate then compatibility check, multiple ambiguous. Never prefer empty. |
| Explicit PK/UUID already authorized | Load/verify exact Engine directly; check manufacturer/code and any explicit key, then five-field compatibility. Do not undo the pin with code-only lookup. |
| Unknown/conflicting facts | Incomplete/conflicting/unresolved result; never invent properties or a variant. |

**Recommendation:** multiple same-code rows remain ambiguous even when a partial
five-field claim excludes some. Calibration/output variants can share the same tuple;
reviewed explicit discrimination is safer than implementing evidence-based ranking.
This is the smallest strict interpretation of the requested fail-closed rule. If the
owner instead wants fully evidenced elimination to resolve multiple rows, that needs
an explicit applicability rule; do not silently implement such selection.

Extracting existing tuple compatibility into a tiny private helper taking an Engine
instance is appropriate: it lets exact-reference consumers validate without re-querying
by code. Preserve the current separate validation of both incoming dictionaries in
`prepare_registered_vehicle`; neither claim set may overwrite the other's conflict.

## Evidence and authoring boundary

Nonempty key authoring remains a separate human-reviewed data operation. Retain a
review record in existing research/task artifacts with manufacturer/code/key, source
URLs/retained hashes/sections, distinctions and application scope, limitations, human
approval/date, and eventual Engine PK/UUID. Reuse across applicable models/years;
model-year changes or importer conflicts are not evidence of a new Engine.
Distinguish engine output from combined hybrid-system output. Horsepower/torque
alone do not automatically confer identity; do not add EngineApplication or move
hybrid-system specification ownership.

Existing Engine authoring has **no evidence/approval field or automatic evidence gate**.
Recommend preserving the current owner-authorized manual-authoring boundary with a
retained review artifact. If mechanical enforcement is required, approve a bounded
Admin form check/approval-reference audit entry before implementation; adding the
field alone cannot truthfully claim to enforce evidence review. No new evidence or
approval subsystem is proposed.

## Consumer and historical compatibility plan

| Consumer | Necessary handling / unchanged boundary |
|---|---|
| Registry resolver and unsaved construction | Sentinel-aware exact composite lookup, no `.first()`, compatibility by resolved instance. Land before uniqueness relaxation is used. |
| VehicleDefinition validation and existing FKs | Continue exact FK and manufacturer/five-field checks. Do not add key to vehicle snapshots, semantic identity, slugs or UUIDs. Different Engine keys alone do not authorize duplicate VehicleDefinitions. |
| Reconciliation preview | `_engine` already emits empty variant key, so adding an empty DB field need not change that projection or its original digest. Multiple unpinned name/code candidates must remain ambiguous; explicit pins/FKs remain authoritative. |
| Original assignment executor | Preserve original 507 artifact and its digest. Full `.values()` preservation baselines gain a new column; do not confuse fresh baseline shape with old authorization shape. No new assignments under old approval. |
| MY2025/MY2026 bounded previews | `.snapshot(obj)` serializes **every concrete field**; the new field changes prospective plan hashes even when empty. Existing 2026 source PK/UUID pins must be honored before ambiguous code fallback. Code-only source rows still fail when ambiguous. |
| Registry-aware body 3.1.0 | Load old Engine bindings by their exact manufacturer/Engine PK/UUID; retain code/properties/update-time checks. `_conflicts` must validate selected instance, not code-only. Keep old wire fields and hash domain unchanged. |
| New variant-aware wrappers | Recommend an explicit registry envelope minor version, e.g. **3.2.0** (owner decision), adding the variant key to Binding and dependent hashes. Inner Candidate/body contracts remain unchanged unless a separate concrete need is found. Do not append fields to closed 3.1.0 objects or globally change VERSION and invalidate old readers. |
| Original MY2021/MY2022 compact readers | They pin Engine PK/UUID and five properties, not all concrete Engine fields. Empty-key schema addition should not alter their stored record/metadata hashes or approved Matrix. No automatic regeneration/upgrade needed. |
| Historical ImportExecutionReceipts, Matrix/adjudications | Never rewrite payloads/digests/approvals or reassign FKs. Retain original versioned validation and raw proof preimages; new key is not evidence that old unknown facts were established. |
| Public presentation | Keep Engine.name, engine_label, canonical ordering and VehicleDefinition slugs/URLs unchanged. Internal key is not an automatic display suffix. |

Registry 3.1.0 already pins exact PK/UUID. Recommend old empty-key Engines remain
verifiable even after another same-code variant is authored; unrelated additions
must not make an exact pin arbitrarily select another row. Legacy artifacts must
not gain executable nonempty-key semantics by inference. New explicit variant
selection belongs in its reviewed new envelope. Unsupported combinations fail closed.

For full-concrete-field MY2025/2026 snapshot hashes, prefer **explicit historical
version projections**: old profile serialization retains its old field set for
legacy-compatible empty-key rows; new variant-aware profile versions include the new
key. Alternatively old *unexecuted* previews may be deliberately marked stale and
newly reviewed, but this must be documented—not reported as unchanged replay.
Existing receipt bytes never change in either option. Do not replace all-field
preservation checks with partial comparisons; only the versioned authorization
serialization uses the historical projection. Full fresh baselines must still compare
every live field, including the new key.

`reference/body_identity.py:109`, `baseline_preimage`, binds the canonical five-field
powertrain/body/series identity—not Engine variant key or Engine UUID. Preserve that
preimage. Registry binding identity is a separate concern. There is no basis to
rewrite generic Candidate 2.1.0 or Candidate v3 source schemas merely for this field.

## Admin and public UI

Add variant key to Engine list/search and creation form with neutral empty-key help.
Readonly on change alongside manufacturer/code; model validation remains authoritative.
Admin Engine autocomplete labels must distinguish same-code/name variants. Prefer an
Admin-only serializer/choice label (`[no discriminator]` for empty, internal key for
named variants) rather than changing global `Engine.__str__` or public names. Account
for VehicleDefinitionAdmin's existing autocomplete, not just an ordinary select field.
No public view/template/slug changes are needed. Keep any future presentation decision
separate from internal identity.

## Bounded implementation sequence and owner decisions

1. **Approve remaining contract choices:** strict multiple-code ambiguity; evidence
   review enforcement (existing human authorization recommended); new wrapper/profile
   version names and historical snapshot projection versus deliberate stale previews.
   The requested field/composite identity itself is already specified by this task.
2. **One coherent model/lookup compatibility checkpoint:** field/checks/immutable-save
   extension, new migration, sentinel resolver/constructor, exact-reference reader
   corrections, Admin, and preservation tests. Do not ship relaxed uniqueness with
   old `.first()` or known pinned consumers still re-resolving by code.
3. **Variant-aware writer integration checkpoint:** explicit key selection/review in
   registry preparation, new serialized bindings/wrappers/profiles where needed,
   stale/replay/transaction tests and historical fixtures. Keep old readers supported.
   This can be separately reviewed from the migration, but nonempty operational
   authoring should wait until applicable consumers are ready. No new numbered
   architecture milestone/general framework is required.
4. **Separate operational authorization:** consistent backup, isolated migration
   rehearsal/full-field comparison, then specifically approved live schema change.
   No variant seed/reassignment is part of migration. Later reviewed variant creation
   and any VehicleDefinition correspondence/assignment require their own scope.

## Focused future tests — not implemented or run

- Migration current 0014→new leaf: ten empty keys; all old Engine/vehicle/receipt fields,
  UUIDs, PKs, timestamps, codes, FKs, indexes and integrity preserved; rollback rules
  must refuse loss of authored nonempty variants without separately approved recovery.
- Composite uniqueness: same manufacturer/code/key rejects, different keys coexist,
  manufacturer isolation, normalized casing/outer spaces; raw SQL duplicate and invalid
  character/length checks, empty/default/None, Unicode-before-lowercasing rejection.
- Immutability: every identity component including empty-key transitions, direct model
  saves/full_clean, Admin edit, partial/bulk-write rejection, concurrent updates.
- Resolution: omitted versus explicit empty/nonempty, only named row, empty+named rows,
  multiple equally compatible/differently compatible variants, incomplete evidence,
  conflict rejection, no Engine creation or guessed key. Preserve full hyphenated codes.
- Concurrency: isolated file SQLite with two connections, duplicate authoring cannot
  commit twice; handle IntegrityError/lock races without partial data or arbitrary reuse.
- Integration: exact PK/UUID remains selected with same-code siblings; candidate/code
  correspondence and five-field conflicts still checked; original 3.1.0 round trips,
  new-version dispatch, unsupported fields/versions, approval/hash/stale/replay behavior.
- Full snapshot profiles: assert known historical empty-key preimages unchanged under
  chosen policy, new variant changes require explicit new approval, full preservation
  baseline still sees every concrete field. Do not silently unpin original 507 approval.
- MY2021/MY2022 compact records, MY2024 body bindings, MY2025/MY2026 registered profiles,
  Engine assignment/reconciliation and protected-FK invariants; use isolated DB/media.
- Admin search/list/readonly/form/duplicate autocomplete distinctions; no public key
  leakage, changed labels/ordering, altered URLs/slugs or VehicleDefinition identities.

## Verification and exclusions

Planning inspection only. Read-only SQLite counts/schema/migrations/duplicate queries,
integrity and FK checks executed; **no tests, migration commands, acquisition or data
writes**. Existing tests were inspected to plan extensions, not modified.
No Engines or speculative variants were created, reclassified, merged or rebound;
no Toyota hybrid or combined-output assumptions adopted; no EngineApplication,
generation-resolution work, ADR change, roadmap/state change or deployment proposed
as an automatic consequence. Only this research report is a new repository file.
All existing working files and DB bytes remain unchanged; no staging, commit or push.
