# RA-044 — Structured powertrain identity implementation architecture

**Created:** 2026-11-07
**Status:** Accepted
**Accepted:** 2026-11-07
**Authority:** [ADR-0012](../ADR/ADR-0012-Structured-Powertrain-Identity-And-Hybrid-Terminology.md), JL-D19/JL-D20 and the director's structured-powertrain implementation-architecture task.
**Scope:** Architecture for the next implementation milestone. Accepted by the director on 2026-11-07. Implementation remains pending separate authorization; migrations and imports are not authorized by architecture acceptance.
**Director review:** DecimalField(5,2), positive cylinder count, the controlled taxonomies, five-field JL evidence requirement, Candidate 2.1.0, Manifest 2.1, Matrix 2.1, transaction-time proof and deferred historical backfill are approved. The refined deterministic slug rule and W2 forward-compatibility requirements are accepted on 2026-11-07.

## 1. Purpose and current boundary

Unblock evidence-supported US Wrangler JL MY2019–2026 configurations by persisting five manufacturer-neutral engine attributes on VehicleDefinition. MY2027 remains preliminary. Trim classification disputes remain independent director decisions. Equal evidentiary standing of Edmunds and J.D. Power does not permit invented mechanical applicability.

Current VehicleDefinition stores engine_name as free text. Its slug derives from year/trim/engine_name/drivetrain/market. Existing Candidate v2 schema 2.0.0 normalizes displacement/cylinders and binds complete retained evidence to generation resolution. The engine_distinction version 1.0 proof uses candidate descriptor evidence and peer creation receipts, permitting displacement/cylinder differences. Legacy Candidate v1 retains its drivetrain behavior. Matrix execution freshly plans each row inside one year transaction and atomically saves its creation receipt.

Keep those historical paths intact. Extend the same planner, importer, manifest, matrix, receipt and presentation services through explicit version dispatch. Do not add an engine entity, specification revisions, Admin approval workflow or a new application.

## 2. Exact proposed persistence

All fields are added to reference.VehicleDefinition. Use null=True and blank=True, with no semantic default. Normalize empty form input to None. Empty strings are not stored taxonomy values. Model/application validation and database constraints must agree.

| Field | Django definition | Valid established values |
|---|---|---|
| engine_displacement_liters | DecimalField(max_digits=5, decimal_places=2, null=True, blank=True) | Positive manufacturer-marketed displacement in liters, at most two fractional digits |
| engine_cylinders | PositiveSmallIntegerField(null=True, blank=True) | Positive integer, excluding bool and zero |
| engine_aspiration | CharField(max_length=24, null=True, blank=True, choices=...) | naturally_aspirated, turbocharged, supercharged, twincharged, other |
| fuel_type | CharField(max_length=24, null=True, blank=True, choices=...) | gasoline, diesel |
| electrification_type | CharField(max_length=24, null=True, blank=True, choices=...) | none, mild_hybrid, hybrid, plug_in_hybrid |

Quantities are marketed values. 3.6 and 3.60 compare equal as Decimal. No tolerance, rounding, conversion from exact cubic centimeters, or requirement for engineering displacement is introduced. A source value exceeding the representable precision blocks pending review. Raw source lexemes and units remain in evidence. Numeric storage precision does not expand the scope of acceptable manufacturer claims.

Add positive-or-null checks for numerical fields and allowed-token-or-null checks for categorical fields. Preserve every existing column, constraint, PK, UUID, slug and relationship. engine_name remains a display descriptor. No manufacturer-code uniqueness constraint is added.

Null consistently means unassessed/unknown. none is an established nonhybrid classification. A known other aspiration requires explanatory evidence and review, since two different unrepresented induction systems cannot be assumed equivalent.

Gasoline/diesel cover the JL milestone, including its gasoline PHEV and diesel variants when individually established. Electricity, hydrogen, multi-fuel, rotary and noncombustion applicability remain future vocabulary extensions. This implementation must reject unsupported new powertrain categories rather than represent them with zero displacement, zero cylinders, gasoline or none. There is no current need to implement their inapplicability schema to ingest the JL combustion-equipped baseline. This bounded choice satisfies ADR-0012's extension boundary without prematurely defining those future vehicles.

### Migration and historical assignment

Use one additive schema migration after separately authorized implementation. Add all fields as nullable with no data migration, engine_name parsing, guessed defaults or seed assignments. Test forward migration preservation against an isolated database. Application of that migration to development is separately authorized.

Existing rows stay null unless a later explicit operation assigns verified facts. Retained creation evidence may establish a planning premise without persisting a backfill. No new historical backfill/approval service is part of this milestone. Missing peer evidence blocks the affected create. A correction or backfill proposal must retain the original UUID/slug and use a separately approved audit path.

## 3. Candidate v2 extension

Propose Candidate schema 2.1.0, retaining artifact type rigarchive.candidate_configuration.v2. Keep schema 2.0.0 byte semantics, round trips and hashes unchanged. Candidate v1 remains unchanged. Candidate v3 is already reserved for body-aware work and is not implemented here.

Add exactly one required top-level object in 2.1.0, canonical_powertrain. It contains exactly the five proposed model-field keys from §2, each explicitly present and nullable. Encode marketed displacement as a canonical decimal string, removing insignificant trailing zeros and any redundant decimal point. Encode cylinders as an integer. Encode categorical fields as controlled strings or null. Reject unknown keys. The full candidate digest covers this object with the rest of the candidate.

Example identity fragment:

~~~json
{
  "canonical_powertrain": {
    "engine_displacement_liters": "2",
    "engine_cylinders": 4,
    "engine_aspiration": "turbocharged",
    "fuel_type": "gasoline",
    "electrification_type": "plug_in_hybrid"
  }
}
~~~

Normalization supplies mapped concepts named engine_displacement_liters, engine_cylinders, engine_aspiration, fuel_type and electrification_type. Each established value must have at least one qualified source_assertion_ref into the retained evidence documents. Preserve raw_source_value, manufacturer_term and rule notes. Decimal normalization for 2.1.0 uses canonical strings, extending TechnicalValue handling only through explicit schema dispatch. All five concepts must project exactly to canonical_powertrain. Duplicate unequal interpretations, invalid units, unsupported tokens and caller-context-only values block execution.

Five-field sufficiency requires support for all five attributes, not five sources. One authoritative source may establish multiple attributes. Multiple sources may jointly establish the tuple when their year, market, body, trim and mechanical applicability can be joined explicitly. A single source assertion may support multiple normalized interpretations with the same qualified reference. Preserve each mapping and its rationale. Do not require redundant corroboration or count sources as a substitute for applicability. Conflicting claims remain review-required under the existing reconciliation rules.

Keep the existing document, generation correspondence and source applicability contracts. A source's explicit eTorque claim can support mild_hybrid through a reviewed normalization rule. ESS alone does not establish mild_hybrid, and absence of a hybrid label does not establish none. A verified source rule can establish none from applicable manufacturer evidence. 4xe supports plug_in_hybrid only with the exact configuration association. Diesel and gasoline cannot be inferred solely from engine size.

Manufacturer engine and quick-order codes remain source assertions or source configuration identities. They can establish applicability and traceability. Code equality or inequality cannot establish canonical engine equivalence or distinctness. Emissions certification changes alone never split a baseline.

A 2.1.0 candidate may preserve null while being prepared, but a new JL create requires all five attributes established. Keep incomplete candidates review-required. An unchanged historical 2.0.0 candidate is not automatically upgraded. Do not add facts or regenerate historical candidate digests.

## 4. Engine identity and peer comparison

The engine identity tuple for the new path is the ordered sequence of all five normalized attributes from §2. engine_name, technology names, engine codes, transmission choices, horsepower and torque are outside that tuple.

Resolve Generation first. Compare same-generation/year/market/trim/drivetrain peers across statuses for duplicate/conflict detection. Within active peers, assess all five attributes and relevant source applicability. A create requires a verified unequal attribute from every otherwise equivalent peer, plus no unresolved overlap. Complete assessed equality is an existing identity, even when labels or codes differ. Do not create another row under a different display-derived slug.

For legacy null peers, source-qualified retained assertions and a successful creation receipt may supply a nonpersistent assessed tuple if all five facts are unambiguous and apply to that exact record. Bind its UUID/slug, current canonical fields, receipt UUID, evidence hashes and projected facts. Otherwise require review. Reading receipt lineage must not manufacture a new assignment or mutate old receipts.

Conflicting evidence, partial tuples and unknown values never prove difference or equality. Different cylinder layouts alone remain outside this milestone's five dimensions. A concrete layout-only factory difference is flagged for review. Identical assessed tuples with verified tuning differences follow JL-D20 and require review without generating an additional VehicleDefinition. Preserve existing tuning evidence without implementing numerical output persistence.

Within the new path, evaluate structured semantic identity before granting exact-match no-op, first-representation, mechanical or source-established-grade outcomes. A matching slug with mismatched or unassessed facts must not become an automatic no-op. Exact semantic equality with a different established slug returns the existing identity using that slug; it never renames it. For this exact-match result, target engine_name is the existing stored label, pinned with the existing UUID and slug. The new bound-plan validator checks candidate semantic equality and preserves its differing source label in lineage rather than requiring string equality with the stored display label. For creates, the target display label must still match the reviewed candidate projection. Existing canonical duplicates remain review-required rather than choosing one.

## 5. Plan, manifest, matrix and receipt bindings

Closed current contracts reject extra execution fields. Propose this explicit minor-version dispatch:

| Contract | Existing behavior retained | New behavior |
|---|---|---|
| Candidate v2 | schema 2.0.0 unchanged | schema 2.1.0 with canonical_powertrain |
| Canonical review manifest | version 2.0 unchanged | version 2.1 with exact ten-field target tuple |
| Generation resolution | existing version 1.0 unchanged | version 1.1 for engine-aware targets |
| Engine distinction | version 1.0 unchanged | version 2.0 full five-attribute proof |
| Matrix | v1 / v2.0 unchanged | v2.1 with ten-field target_fields |
| Matrix Approval | Approval v1 serialization unchanged | Existing approval binds the exact v2.1 matrix digest |

The ten target fields are the existing model_year, trim_name, engine_name, drivetrain and market plus the five proposed persistent fields. Decimal wire values are canonical strings. Convert to Decimal only at validated model boundaries. Define exact versioned key sets in serializers, validators, stale-plan comparison and matrix row matching. No unknown_fields shortcut may carry executable identity semantics into an older version.

Generation resolution 1.1 keeps its parent UUIDs, evidence documents, correspondence revisions and source restrictions, and binds the new target projection and structured semantics. Model-code correspondence publication need not change. Existing restriction keys retain their current meanings.

Engine proof 2.0 contains its version, canonical_powertrain for the candidate, and a stable PK-ordered peer list with each peer's UUID/slug, all five assessed values, canonical state, receipt identity when used, retained document hashes and proof projection digest. The candidate hash binds all qualified normalized evidence. The resolution and full manifest hashes bind the complete proof. No new persistent proof model or separate approval is required.

Every new 2.1 create writes all five fields and the existing receipt JSON records the exact resolution/proof and candidate/manifest identity. A successful receipt carries exact new target_fields_json. Historical receipt fields and payload bytes remain untouched. New code explicitly accepts and validates old versions. Old code rejects unsupported new versions; it must never silently omit identity fields. Historical approved plans may remain inspectable but become stale if their relevant assessed canonical premises have subsequently changed.

## 6. Slugs and collisions

Preserve every existing UUID and public slug. A slug is a locator, not proof of engine equality. The semantic identity comparison in §4 occurs before deciding whether a new locator is needed.

### Proposed engine-fields/1 new-record rule

For newly created 2.1.0 candidates, start with the existing five-field canonical slug builder using the reviewed engine_name. Its displacement and cylinder description must agree with the assessed marketed engine tuple. Then append only the following qualifiers, in aspiration / fuel / electrification order:

| Established attribute | Qualifier |
|---|---|
| naturally_aspirated | Omit |
| turbocharged | turbo |
| supercharged | supercharged |
| twincharged | twincharged |
| other aspiration | Review required before slug assignment |
| gasoline | Omit |
| diesel | diesel |
| none electrification | Omit |
| mild_hybrid | mhev |
| hybrid | hev |
| plug_in_hybrid | phev |

All generated tokens are lowercase. Qualifier presence is a fixed function of the established attributes, never whether another record already occupies an unsuffixed slug. The omissions encode explicitly assessed naturally aspirated / gasoline / none values. Unknown never selects an omitted qualifier or qualifies for a new JL create.

Examples using hypothetical reviewed display labels, without asserting year-specific factory availability:

| Engine display component and assessed facts | New-create suffix after the existing five-field base |
|---|---|
| 3.6L V6, naturally aspirated gasoline, none | No added suffix |
| 3.6L V6, naturally aspirated gasoline, mild_hybrid | -mhev |
| 2.0L I4, turbocharged gasoline, none | -turbo |
| 2.0L I4, turbocharged gasoline, plug_in_hybrid | -turbo-phev |
| 3.0L V6, turbocharged diesel, none | -turbo-diesel |

For example, a conventional gasoline V6 keeps the established year/trim/engine/drivetrain/market slug form. The turbo qualifier is emitted from the structured aspiration even if a source-specific reviewed engine_name also contains a turbo word. Do not remove arbitrary words from engine_name or inspect its spelling to decide which qualifiers to emit. A later presentation-only label adjustment does not regenerate a stored slug.

For the same reviewed candidate and identity tuple, the proposed new slug is identical whether it is the first or last imported row. Do not give the first engine an unsuffixed collision-based privilege. Existing assessed exact matches continue to use their immutable stored slug under §4, even if that older slug differs from the new-create recipe. That lookup preserves history and creates no ingestion-order-dependent new assignment.

### Collision and compatibility boundaries

Before planning a create and again inside the transaction, check the semantic identity and proposed slug across active and inactive rows. An occupied conflicting slug blocks. If different established mechanical tuples still map to the same candidate slug, report the collision for explicit resolution. Do not rename, renumber, truncate or regenerate any existing record. An exact inactive identity needs lifecycle review, not resurrection or a different locator.

If a display descriptor omits the displacement/cylinder distinction, or the complete slug exceeds 180 characters, block for review until a separately accepted representation can express it. Equal assessed engine tuples cannot create duplicates under different names or codes. Non-JL layout-only and other unrepresented distinctions remain review-required.

Use existing SQLite transaction and generation/slug uniqueness checks with semantic peer revalidation. Lock/uniqueness races abort safely. No database engine-identity digest column is required. Existing Candidate 2.0 slugs, historical body/series preimages and prior approvals keep their original interpretation.

This is a versioned new-record recipe under ADR-0012's authorized structured-identity extension. It does not amend ADR-0002's immutable-slug rule or change an existing identity preimage. Acceptance of this refinement is required before the corresponding implementation.

## 7. Matrix execution and stale state

Keep one model-year transaction, per-row replanning, unchanged human confirmation and per-create receipts. Before any creates, validate the matrix/approval digest, every candidate's complete assessed tuple and Generation binding, all target slugs, existing matches and prospective sibling identities.

A source-established-grade create followed by a same-trim second engine may switch to mechanical_dimension only if both bases were explicitly permitted by that approved row. The new peer's just-created canonical fields and receipt provide evidence inside the same transaction. Apply exactly the same comparison in either engine order. Proof insufficiency, new conflicts, unknown fields or changed evidence abort the year and roll back its records and success receipts.

The importer recomputes the assessed tuples and engine proof immediately before writing. Compare them exactly to the manifest-approved values and references, including any explicitly null canonical peer state plus its nonpersistent evidence projection. Relevant field edits, source changes, receipt drift or correspondence changes stale the plan. Do not fall back to engine_name comparison. Reconciliation checks the ten target fields, proof versions, receipt bindings, inactive/duplicate records and exact matrix row linkage. Retrying committed rows creates no extra records or success receipts.

## 8. Minimal presentation integration

One controlled-value definition supplies persistence choices and the display metadata. Presentation services consume it, leaving templates and JavaScript without independent label dictionaries.

| Value | VehicleDescription | Generation Configurator |
|---|---|---|
| mild_hybrid | Mild hybrid (MHEV) | MHEV |
| hybrid | Hybrid (HEV) | HEV |
| plug_in_hybrid | Plug-in hybrid (PHEV) | PHEV |
| none | No electrification qualifier needed | No abbreviation |
| null | Unknown when the context requires disclosure | Do not infer a classification |

Keep eTorque and other manufacturer terms in existing source/descriptive metadata. A conventional ESS configuration has no MHEV badge. Compose complete description text from the established engine descriptor and normalized long label. Choices use the short label when needed to distinguish variants. Ensure aspiration/fuel differences also remain distinguishable when engine_name is the same. Existing configuration-selection and URL behavior remains.

No horsepower/torque fields, slash-output rendering, specification catalogue changes, conditional-rating engine or Full Specifications work is part of this implementation milestone.

## 9. Implementation and test sequence

1. Add centralized controlled values and nullable fields with the additive migration. Test field validation, no defaults, and preservation of all old columns and identities in an isolated migration test.
2. Extend Candidate v2 serialization/normalization by schema version, exact key validation and evidence projection. Test all three hybrid types, conventional none, diesel, turbo/naturally aspirated and mixed missing/conflicting evidence. Keep old hash/round-trip fixtures unchanged.
3. Extend canonical planning, resolution/manifest validation, slug strategy and importer together. Reuse engine_distinction machinery. Test same-size MHEV versus none, gasoline versus diesel, I4 turbo versus PHEV, distinct aspiration, equal tuples with differing codes, emissions-only code changes, legacy peer evidence, and missing evidence.
4. Extend Matrix v2.1 review, proof/target reconciliation and existing commands' version dispatch. Test both candidate orders in one year, rollback after a failed later row, changed proof premises and safe idempotent retry.
5. Integrate centralized long/short labels through the existing presentation services. Test descriptions and configurator labels for MHEV/HEV/PHEV/none/null without changing old URLs.
6. Run focused regression selections during development. Before acceptance run one full Django suite, system check, migration-consistency dry-run and whitespace check with isolated databases. Repeat broader tests only for concrete failures or new changes.
7. After implementation acceptance and separate schema-application authorization, complete the dual-source MY2019–2026 evidence/trim decisions, reviewed candidate construction, correspondence and matrix preparation. Imports and any backfill still require exact human authorization.

Database migration, field backfill and model-year import are separate authorizations. Development/test migration runs do not authorize applying schema changes to the canonical database.

## 10. Final acceptance and remaining boundaries

The director has approved the numerical precision, initial choices, five-field evidence requirement, explicit version dispatch, transaction-time proof and deferred backfill. The refined engine-fields/1 recipe in §6 and the W2 forward-compatibility requirements are accepted on 2026-11-07. Implementation remains pending separate authorization. No code, migrations, schema application or import is authorized by this architecture acceptance.

[W2 domain forward compatibility](W2-Full-Specifications-Domain-Architecture.md#future-resolved-configurations-and-production-variation--compatibility-requirements) records subordinate resolved configurations and nonselectable production/tuning alternatives. Those requirements do not add models, URLs, output storage, specification ingestion or revision administration to RA-044. Their identity/URL contracts and any closed-schema extensions are future work. No existing W2 preimage or artifact hash is changed.

Future electric/noncombustion taxonomies, assessed body-plus-engine semantic preimages, and historical backfill services remain deferred. Candidate v3 remains independently scoped. There is no identified conflict between the new-create slug rule and accepted identity contracts, provided unsupported collisions remain blockers and all existing identifiers stay immutable.

The required project sequence is structured powertrain implementation, then Wrangler JL MY2019–2026 completion, then Full Specifications Ingestion, Correction and Audit Architecture.
