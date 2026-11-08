# W2: Full Specifications domain architecture

**Last Updated:** 2026-11-07

**Status**: Approved architecture contracts, incorporating director-approved Phase A corrections on 2026-11-04. Not implemented; no migration or canonical-write authorization.

Authority: current task, accepted ADRs, CURRENT_STATE, approved RA designs, Handbook, Blueprint. [ADR-0011](../ADR/ADR-0011-Factory-Body-Configuration-Identity.md) is required for body identity. Read with the [property contract](W2-Specification-Property-Applicability-Contract.md), [publication contract](W2-Enrichment-Publication-Contract.md), [plan](W2-Phase-A-Implementation-Plan.md), [operational protocol](../../development/INGESTION_PROTOCOL.md), and [W1 closeout](../../development/JEEP_W1_CLOSEOUT.md).

## 1. Existing implementation versus proposed state

Reference models currently have no specification catalogue, transmission offerings, equipment persistence or body relationship. VehicleDefinition has free-text engine/trim and Generation-scoped immutable slug; clean validates model-year range. Candidate v2 preserves complete document-qualified generation evidence, retained assertions and hash bindings. `generation_correspondence.py` supplies reviewed resolution and stale-state checks. `manifest.py` and `importing/workflow.py` enforce exact baseline import authorization with atomic receipts. Candidate builder technical structures and factory features are intermediate representations, not persistent offerings; packages/options currently project empty. `get_full_specifications_context` supplies baseline identity, siblings, measurements and one creation/match receipt, not a comprehensive evidence catalogue.

Reuse BaseModel, protected relationships, artifact storage, source assertions, normalizer provenance, review conventions and manifest hashing. Keep new models in Reference and existing services/layering. No new Django app, shared engine entity, generalized mapping engine or unrestricted rule evaluator is needed. Proposed enrichment execution is a separate operation, not a changed meaning of the baseline importer.

## 2. Shared persistence and revision contract

All persistent identities have generated integer PK, UUID, created_at/updated_at from BaseModel; UUID is the external identity. Published content is immutable despite inherited timestamps. PK is never an evidence identity. References below use protected foreign keys; published parent/member/evidence rows cannot be deleted. Explicit member association tables are protected too; avoid cascade deletion of published membership. Drafts remain versioned artifacts outside the canonical tables.

Revisioned entities have stable logical UUID, revision UUID, positive revision_number, nullable protected supersedes reference, lifecycle finding (`established`, `unresolved`, `withdrawn`), content hash, nonempty reviewer attribution, aware reviewed_at and review notes. Enforce unique `(logical_uuid, revision_number)`, unique predecessor successor and unique first revision per chain. Successor must be same chain, number n+1 and current leaf. Concurrent publication uses transactional compare-and-insert plus database constraints; losing attempts do not auto-retry. Withdrawal is a successor, not deletion or rewriting. Historical catalogues keep exact historical members; current selection cannot use withdrawn content as newly established availability. Source withdrawal does not erase historical factory availability.

Hashing uses the publication contract. Stable identity metadata is immutable; descriptive changes create revisions. A genuinely different semantic identity gets a new logical identity, not a revision that changes meaning. Published chains may never fork. An identity cannot be reused solely because its name/code resembles another.

## 3. Evidence contracts

### EvidenceDocument

Immutable reference to a retained document acquisition record, not duplicate byte storage. Required: UUID, source_id, raw_artifact_hash/reference, source_locator, acquired_at, acquisition_method, media_type, byte_size, publisher label, publication_kind, revision-status (`established`/`unknown`), publication revision when established, and source applicability with explicit unknowns. Optional: publication_date, original filename, native publication ID. Unique canonical acquisition metadata digest; identical bytes can have distinct honest acquisition events/locators. Reuse snapshot metadata rather than inventing a second source authority. Its hash covers acquisition identity; byte hash covers original bytes. A later publication is another record, never an overwritten file. No fabricated publisher revision/date or source authenticity stage for official Jeep PDFs.

### EvidenceAssertionReference

Immutable resolved reference with document FK, extractor ID/version/mode, assertion_set_id, local assertion_id, original attribute key/value, location (page/table/row/column/paragraph/bounding box as available), and retained assertion-artifact hash/reference. Unique `(document, extractor_id, extractor_version, extraction_mode, assertion_set_id, local_assertion_id)`; different extraction results at that key are a conflict, not an overwrite. Local IDs from different documents never collapse. Hash covers the complete assertion/provenance payload. Verify bytes and referenced assertion content before publication. A page-text block may evidence retention, not the extraction of every cell or visual relationship.

Normalization evidence links separately retain interpretation ID, transformation method, rule ID/version, source references, original terminology, normalized output and notes. Many-to-many evidence links require role (`supports`, `contradicts`, `qualifies`, `excludes`) and location. A source join requires reviewed correspondence evidence, not text equality. All facts below require at least one supporting assertion and preserve contradictory/qualifying references. Body/profile and vocabulary curation use the same review/evidence discipline but require separately scoped authorization.

## 4. Model field contracts

### SpecificationDefinition

Immutable UUID and unique stable machine key such as `dimensions.exterior.overall_length`. Required semantic revision: name, category, description, value_kind, dimensional_family (or categorical domain), allowed qualifiers/component selectors and method semantics. Revision fields follow section 2. No default result unit. A semantic meaning or dimensional-family change needs a new definition key; compatible display/clarification changes create a definition revision. Assertions pin exact definition revision. Controlled vocabulary additions are reviewed and versioned, not inferred from arbitrary source labels. Definition review cites source concepts and a curator rationale; no numeric vehicle availability is implied.

### SpecificationAssertion

Immutable UUID/content hash; required definition revision, typed value/status, original label/value/unit, explicit qualifier and applicability objects, evidence links, normalization provenance, reconciliation state and review finding. Optional component locator (e.g. front axle or gear 3), method reference, source effective dates and stated uncertainty. Assertion rows are immutable reported claims, not automatically selected truth. Corrections append a new assertion with nullable protected `supersedes_assertion_uuid`; at most one same-lineage successor, cycle-free. Independently reported duplicates/conflicts are permitted, not unique by property/baseline. Catalogue membership supplies the exact baseline; reusable assertions require separately proven applicability for each membership. No global publisher precedence or numeric averaging.

### SpecificationCatalogueRevision

Stable catalogue identity unique per exact VehicleDefinition, revision identity/lineage and review fields. Required baseline UUID/identity snapshot, exact member lists (definition/assertion, transmission, equipment, compatibility and feature mapping revisions), evidence/inventory digests, four independent coverage reports and optional production/date applicability. Catalogue publication means a coherent, referentially valid reviewed snapshot, not absence of conflicts or complete knowledge. A conflict may be published only with explicit unresolved state and no definitive chosen value. A current successor is a complete membership snapshot, never a dynamic patch. No latest-member lookups; rule dependencies must be inside the snapshot. At most one current leaf per chain. Non-overlapping effective-date contexts may coexist within a snapshot; unspecified date cannot choose one arbitrarily.

### TransmissionDescription / TransmissionDescriptionRevision

Stable UUID with manufacturer/namespace/native code when established; absent code uses a documented source-local identity. Required revision designation, normalized type/status, forward speed count/status, evidence and provenance. Optional code, engineering details as linked specification assertions (ratios, operation), not invented global hardware identity. Code uniqueness is scoped by manufacturer, namespace and reviewed applicability; reuse/renaming requires identity review. Type/speed equality never merges descriptions. A logical identity cannot change physical transmission meaning in a successor.

### TransmissionOfferingRevision

Revisioned logical offering tied to exactly one VehicleDefinition and one exact transmission description revision. Required availability (`standard`, `optional`, `unavailable`, `unknown`), predicate, effective scope and evidence. Exact baseline supplies year/market/engine/trim/drivetrain; additional restrictions cannot be dropped. Unique member UUID and chain/revision, not merely code/name. Parallel overlapping contradictory offerings remain review-required rather than silently deduplicated. One offering is not proof of exclusivity. Withdrawal and description changes require explicit successor and a new catalogue to affect current publication.

### EquipmentItem / EquipmentItemRevision

Stable UUID and manufacturer namespace/source-local identity. Required revision manufacturer name, kind (`equipment_item`, `factory_package`, `factory_option`, `accessory`), installation-channel finding, evidence and provenance; optional native code/description. A package requires explicit manufacturer package identity and contents: exact item revisions, quantities if given, conditional inclusion/replacement rules. Nonselectable constituent equipment is representable without falsely claiming standalone availability. Prevent membership cycles and conflicting code identity. Classification change is reviewed, never automatic; packages cannot be fabricated by grouping options. Standardness belongs to offering scope, not permanent item identity.

### EquipmentOfferingRevision

Revisioned logical relationship to exactly one baseline and exact item revision. Required assignment (`standard`, `optional`, `unavailable`, `unknown`, or `accessory_catalogue_only`), predicate, effective scope, evidence, and equipment-policy assessment including applicable brochure hash/reference. Packages/options need documented contents/applicability; standard assignments need source-supported scope. Accessories absent from brochure cannot be published as offerings; full raw publications may remain retained. Brochure-listed accessories remain catalogue-only and never enter factory selection, compatibility, specification effects or feature inference. Exceptional optional-equipment classification requires a pinned director authorization artifact; caller flags are not authority. The categorical absent-brochure accessory exclusion has no exception path.

### CompatibilityRuleRevision

Immutable revision of a reviewed logical rule scoped to a catalogue/baseline and exact offering revisions. Required rule_kind, versioned operands, evidence, effective scope and review. Kinds: `requires_all`, `requires_any`, `excludes`, `includes`, `replaces`, `cardinality`, `supports_combination`. Validate references/types, unsatisfiable requirements and prerequisite/inclusion cycles. Scope-completeness declaration requires evidence identifying the covered universe and permitted configurations. No missing rule means compatible; whole-set support must be established. Codes alone cannot identify operands. See predicate/evaluation contract.

### PhysicalFeatureMappingRevision

Revisioned mapping with exact baseline, predicate, protected ApplicabilityFeature/ApplicabilityState references, evidence and review. State must belong to feature. Multiple outputs of one feature are allowed only under provably disjoint predicates; unresolved overlap blocks state inference. No unchecked option => absent inference. Catalogues pin exact mappings; unresolved or incompatible contexts cannot establish measurement applicability. Keep MeasurementResult at Generation and do not change its result/unit/AND semantics.

## 5. FactoryBodyConfiguration and van/1.0

General immutable identity: UUID, protected Generation, profile_id/version, semantic_identity_digest, source identity references, evidence/review references. Optional manufacturer/model scope may be derived through Generation; no duplicated writable parent chain. Van profile has five explicit dimension objects: `body_style`, `wheelbase_designation`, `body_length_designation`, `roof_height_designation`, `body_code`. Each carries status, nullable canonical designation token, original manufacturer label, evidence and `identity_role` (`distinguishing`, `alias`, `not_distinguishing`, `unresolved`). Established distinguishing tokens are controlled manufacturer-scoped terms, not measurements. Body code also carries namespace; multiple aliases can identify one reviewed body, but unexplained different codes do not merge.

`not_applicable` requires evidence that the dimension does not apply; `not_differentiated` requires evidence of no manufacturer distinction within the reviewed scope; `unknown` states lack of knowledge and must not be substituted for either. Empty strings/null do not encode these meanings. Published body identity requires established body style and all source-demonstrated distinguishing dimensions. Unknown optional code is allowed when semantic identity is fully established and no code conflict exists. An unresolved potentially distinguishing dimension blocks canonical matching. Omit unknown/inapplicable/not-differentiated fields from public identity labels, retaining accessible evidence/status detail separately.

Unique `(generation, profile_id, semantic_identity_digest)` across serialization profile versions; the exact canonical preimage and version safeguards are in §8. Token synonyms and source-code aliases require reviewed equivalence; normalized text alone is insufficient. Unknown values cannot participate in a merge key. Body identity is immutable: new evidence can be added through immutable reviewed binding revisions; semantic correction creates a new identity and blocks any reassignment pending separately authorized canonical correction. Existing linked identity is never silently changed. Body evidence bindings have the shared chain/supersession/hash contract.

Van profile recognizes reviewed body styles without imposing commercial purpose or exhaustive fixed modern types: cargo, passenger, crew, cutaway, incomplete chassis and other evidenced manufacturer terminology. Do not call a historical conventional roof `low` unless the source does. Body dimensions distinguish manufacturer configurations, not arbitrary physical measurements. Numeric wheelbase/overall length/roof height are specifications linked by reviewed applicability.

### Series and grade

Approved future `FactorySeries` identity (UUID, protected manufacturer/model context, namespace, designation token and reviewed source identities) is independently queryable; immutable meanings and revisioned evidence bindings follow body identity rules. Where series and grade are distinct, VehicleDefinition has optional protected series FK and existing trim remains grade. Where series is the manufacturer grade dimension, approved trim normalization suffices and a second identical discriminator is prohibited. An explicit `series_binding_status` distinguishes `legacy_unassessed`, `not_separate` and `established`; established requires FK, other statuses prohibit FK. No arbitrary series/grade string concatenation.

### Canonical identity integration

Approved future body-aware candidate v3 (`rigarchive.candidate_configuration.v3`, schema `3.0.0`) adds reviewed profile/body and series binding status, qualified dimension evidence, body/series UUID and evidence-binding revision/hash once resolved. Candidate caller UUID/labels are routing context, not evidence. Construction preserves unknowns and contradictions. Resolve body/series only after existing reviewed Generation resolution. Identity tuple is existing generation/year/trim/engine/drivetrain/market plus established series and body identity. `legacy_unassessed` body binding is not a wildcard; future van candidates must resolve body or block.

Exact tuple match => no-op only after full evidence and parent revalidation. Otherwise identical baselines with different established body/series => approved future create basis `factory_identity_dimension`. It requires reviewed factory distinctions and no unassessed conflicting legacy baseline; it is not a grade-adjudication bypass. Different grade alone continues existing review rules. Conflicting parents, unresolved body distinctions and arbitrary code differences cannot authorize creation. Duplicate prevention must compare semantic identity as well as slug inside the transaction, backed by a body-aware uniqueness constraint; its legacy-compatible implementation must preserve pre-existing duplicates and avoid relying on SQL NULL equality. New assessed rows use an explicit identity-contract/version marker and constrained identity digest defined in §8; old rows remain outside that new unique index without invented assignments.

For new body-aware records only: existing base slug + `-body-<full-body-uuid-hex>`; append `-series-<full-series-uuid-hex>` when series is independent. Fixed 32-character UUID tokens are persistent identifiers, not random collision retries. Full proposed slug must fit 180 characters; overlength is review-required, never automatic truncation/suffixing. Preserve current slug builder for non-body legacy identities. UUIDs are generated only during separately authorized parent curation; zero-write planning cannot create body/series parents. New body changes create a distinct baseline where justified, never rewrite an existing UUID/slug.

Approved future body-aware import manifest is separate version `3.0`, explicitly supported by future baseline execution, binding exact dimension evidence, body/series identities and binding revisions, identity digest, create basis and target absence. Current candidate v2/manifest 2.0 remain unchanged; body-aware execution through old contracts must fail closed. Receipts retain full body/series snapshots and immutable bindings. No automatic backfill. Jeep two-door/Unlimited normalization is untouched.

## 6. Catalogue selection and Measurements

A selection is temporary baseline UUID + catalogue revision + optional transmission offering + selected factory offering revisions + known effective date/physical context. Not a physical build, new baseline or installation claim. Generation funnel remains unchanged. Full Specifications presents transmission first, packages/options second; accessories separately as catalogue-only. Standard assignments are not optional checkboxes. Unknown selections are not absence. GET/no-JavaScript forms, labelled groups, keyboard operation, focus retention and announced changes are required in future UI work. Invalid foreign offerings fail validation, never silently fall back. Reproducible links pin catalogue revision; withdrawn historic catalogues are labelled and do not become current support.

Manufacturer specification assertions stay in Reference. MeasurementResult remains Generation-anchored, independent reports coexist, result owns units, zero conditions means Generation-wide, multiple physical conditions mean AND. No factory-dimension ingestion into MeasurementResult and no automatic reconciliation/canonical measurement winner. Existing physical states are reused only when semantically correct. A mapping matches all report conditions => applicability established; contradiction => inapplicable; unknown/conflict => unestablished. This labels applicability, not verification of measured value.

## 7. Compatibility and migration

Additive future schema only. Do not modify old UUIDs/slugs/URLs, Generation ranges or receipts; no automatic Toyota/VW/Jeep offering/body enrichment. Existing pages render missing catalogue as not recorded, not absent equipment. Keep historical readers/executors limited to their proven semantics. No body values synthesized for legacy rows. Existing measurement definitions/results/conditions remain intact. See the publication contract for a coherent snapshot and the implementation plan for prerequisites.

## 8. Normative semantic identity preimages

These are closed canonical JSON objects, not Python or executable expressions. Hash with the Publication §5 canonical UTF-8 SHA-256 algorithm; prefix `sha256:`. No UUID, PK, display/manufacturer label, source URL, evidence hash, review timestamp, provenance, arbitrary generated identifier or serialization profile version belongs to a semantic identity preimage.

### Scope and controlled tokens

`Scope = {manufacturer_key: Token, model_key: Token, generation_key: Token}`. These are stable controlled semantic registry keys for the canonical manufacturer brand, model and Generation lifecycle scope. They are manufacturer-scoped attributes, not corporate publisher names or UUID-derived strings. Generation relationship and parent chain must resolve to exactly this reviewed scope. Assign/verify these keys through reviewed manufacturer taxonomy; no automated key synthesis from a label, UUID or insertion order. Registry additions require separate curation authority. Reused historical names are not proof of shared scope. No new keys or values for actual vans are established here.

`Token` consists of lowercase ASCII segments `[a-z0-9]+` separated by single `-`, `.`, or `_`, with no leading/trailing separator and at most 128 characters. Reject noncanonical tokens; do not silently casefold, transliterate, strip punctuation/zeros or convert designations to measurements. Manufacturer labels are preserved verbatim outside the preimage. Source spellings map to tokens only through reviewed equivalence entries; case/spacing differences do not automatically prove equivalence. The body namespace registry is scoped by Scope and dimension, so an identical token under another manufacturer/model/Generation cannot merge identities.

### Body identity

Exact preimage:

```json
{
  "identity_contract": "factory-body-semantic/1",
  "profile_family": "van",
  "scope": {"manufacturer_key":"<token>","model_key":"<token>","generation_key":"<token>"},
  "dimensions": {
    "body_style": {"state":"value","token":"<token>"},
    "wheelbase_designation": {"state":"value","token":"<token>"},
    "body_length_designation": {"state":"value","token":"<token>"},
    "roof_height_designation": {"state":"not_differentiated"},
    "body_code": {"state":"not_identity_bearing"}
  }
}
```

Each of the five keys is mandatory. The shape is illustrative, not evidence of an actual configuration. A dimension preimage is exactly one of `{state:"value", token:Token}`, `{state:"not_applicable"}`, `{state:"not_differentiated"}`; a distinguishing body code instead uses `{state:"value", namespace:Token, token:Token}`. Body style must be `value`. Established identity-bearing attributes use `value`; manufacturer-evidenced absence of applicability/differentiation uses the corresponding literal token, never null/empty string. Not-applicable and not-differentiated are distinct, evidence-reviewed semantics, not wildcard equality.

`unknown` and `unresolved` are valid draft dimension findings, but have NO executable merge/digest token for potentially distinguishing dimensions: fail resolution rather than hash guessed missingness. For body_code ONLY, reviewed alias/not-distinguishing status or unknown optional code with no unexplained code conflict is projected as `{state:"not_identity_bearing"}`. The full evidence record preserves its true missingness/labels, but an alias becoming known does not change body identity. A genuinely distinguishing body code uses namespace/token; if that status is unresolved, block. Other established dimensions that the manufacturer does not distinguish use `not_differentiated` with evidence; do not include a merely decorative label. A known code difference cannot be discarded without reviewed equivalence/non-distinguishing evidence.

Uniqueness is `(Generation, profile_family, semantic_identity_digest)` across ALL profile serialization versions. `van/1.0` records the interpreting profile, not an extra distinction in the digest. A compatible later profile version must produce the same preimage/digest for existing semantics. A semantic-contract change requires explicit versioned equivalence/collision review across all older profiles before any new identity is created; unresolved equivalence blocks creation. It cannot bypass uniqueness by changing `profile_version` or `identity_contract`. No automatic reassignment of linked VehicleDefinitions. The registry prevents duplicate logical scope keys/aliases from bypassing this check.

### Series and assessed baseline identity

Series preimage is exactly `{identity_contract:"factory-series-semantic/1", scope:{manufacturer_key:Token,model_key:Token}, namespace:Token, designation:Token}`. Generation/year applicability is reviewed in bindings; source reuse of the same namespace/code for a different series meaning requires a new reviewed semantic namespace, not accidental merging. No display labels/UUIDs/provenance. Series identity uniqueness uses semantic digest within the model scope, not generated UUID alone.

Assessed baseline preimage is exactly `{identity_contract:"vehicle-definition-body/1", scope:Scope, model_year:Integer, trim_name:String, engine_name:String, drivetrain:Enum, market:Enum, body_digest:Hash, series:SeriesIdentity}`. `SeriesIdentity` is `{state:"established", digest:Hash}` or `{state:"not_separate"}`. Legacy-unassessed series/body is not executable through this identity contract. Trim/engine are exact approved canonical strings under existing normalization, not newly lowercased/reformatted by this contract. Drivetrain/market use existing supported canonical enums. Generation scope is independently resolved through existing correspondence. Identity-bearing body/series digests use the semantic rules above, never their UUIDs. Enforce one assessed baseline per digest plus semantic tuple verification; hash equality is not a substitute for validating preimages. Actual FK/UUID bindings remain frozen in the reviewed import manifest and receipt.

Existing baselines have no retroactively assigned digest and stay outside assessed-row uniqueness. Before new assessed creation, check potentially matching unassessed old tuples and block for review; no assumed wildcards. New slug suffixes use already curated full body/series UUIDs, not the semantic digest; the digest prevents duplicate semantic bodies with different UUIDs. Existing slugs/UUIDs/URLs are never regenerated. Body/series publication/curation operation schemas remain B5 work, not part of enrichment publication v1.

## Approved engine-identity reconciliation — architecture only

[ADR-0012](../ADR/ADR-0012-Structured-Powertrain-Identity-And-Hybrid-Terminology.md) extends future baseline engine identity with first-class displacement, cylinders, aspiration, fuel/energy and electrification. Its JL-D20 keeps verified tuning output pairings under one otherwise identical VehicleDefinition with explicit review. Existing W2 sourced quantities, units, RPM/rating qualifiers, catalogue membership and immutable publication remain the reuse points.

The vehicle-definition-body/1 preimage in the semantic-identity section includes engine_name. That preimage retains its original meaning for old artifacts. Before engine-aware body creation, approve a successor preimage and compatible candidate/import versions that bind the assessed engine facts. Do not mutate vehicle-definition-body/1 hashes or infer new fields from engine_name. ADR-0011 body/series semantics and existing legacy UUIDs/slugs remain preserved. No models, migrations, backfill or new publication were delivered by this reconciliation.


## Future resolved configurations and production variation — compatibility requirements

**Director-approved forward compatibility, 2026-11-07.** These requirements supplement ADR-0010 and ADR-0012. RA-044 remains limited to baseline structured powertrain implementation. No subordinate configuration model, route, new wire contract, numerical output store, evidence import or Admin revision workflow is implemented or authorized here.

### Subordinate resolved configurations

The future application must permit configuration-specific Full Specifications pages beneath an existing VehicleDefinition. A selection of supported transmission, factory packages and individual factory options may resolve to a stable subordinate identity and URL. The parent baseline UUID, mechanical identity and immutable slug remain unchanged. A selection requiring a different baseline links to that baseline; it cannot mutate the parent identity.

Reuse the existing pinned catalogue, offering revisions, independent transmission/equipment selection knownness, applicability predicates and whole-selection compatibility evaluation. Persist or address a resolved configuration only through a separately reviewed future identity/URL contract. The current Selection is a validation context, not an already approved persistent identity preimage. A stable selection identity must distinguish the parent and exact reviewed choices without equating unknown selections or silently changing meaning when catalogues evolve. Its durable identity and its versioned evidence/result representation need explicit future design; no digest preimage is defined by this addendum.

Retain specification and equipment applicability structurally with exact source-qualified facts, parent/configuration association, known effective dates and applicable offerings. Shared assertions stay at their supported scope and are referenced by resolved results, not duplicated for every possible combination. Preserve existing evidence identifiers and raw sources so later resolution can reuse adequate retained facts. If earlier material lacks essential applicability, record that gap and acquire or review only the affected facts. A future resolver must not assume that raw retained material is already a complete structured specification.

An unknown, unsupported or incompatible choice context cannot produce a definitively supported selected-build sheet. Existing W2 rules permitting baseline-unconditional facts while conditional facts remain unestablished still apply. Brochure-governed accessory exclusions and equipment classification rules remain unchanged.

### Nonselectable factory variations

One VehicleDefinition may retain multiple verified horsepower/torque pairings and other specification alternatives caused by production-period changes, calibration revisions or other nonselectable factory variations. Preserve numerical values separately, paired output relationships, rating method/units/RPM, source provenance and production applicability where known. Nonselectable variation is not a user-selected option. The resolver must not invite a user to choose an arbitrary calibration merely to suppress uncertainty.

A known production date or other evidenced applicability context may select the applicable assertions through existing predicates. When applicability is unknown or overlapping, show the alternatives and their limitations. Do not pick one output as universal, infer a date range from document order, or combine a power value from one pairing with torque from another. Incompatible rating standards cannot be silently merged into a single slash-separated presentation.

JL-D20 prohibits automatic baseline proliferation from tuning-only differences. A future director decision may authorize canonical separation for materially distinct factory configurations where necessary. Such a decision needs explicit identity rationale, applicable versioned contracts and separate correction/import authorization. If the standard identity tuple still matches, current duplicate prevention remains in force until that contract question is resolved. A review flag or chosen output figure cannot bypass it. Existing UUIDs, slugs, receipts and parent/subordinate links cannot be silently split or reassigned.

### Existing contract reconciliation

These requirements agree with existing subordinate transmission/equipment offerings and three-valued applicability. The current closed Selection/enrichment/publication schemas do not define a stable subordinate configuration identifier, URL or numerical output-pair linkage. That is a future contract gap, not permission to insert undeclared keys into current artifacts. Define any successor schema explicitly and preserve old bytes and hashes.

The vehicle-definition-body/1, body/series semantic preimages and existing publication contracts remain unchanged by this addendum. Any future canonical separation or combined assessed-body/engine contract requires the existing architecture and authorization process. There is no identified contradiction requiring an immediate W2 contract amendment. The deferred identity/URL and pairing contracts must be resolved after JL completion, before implementing those features.

See [RA-044](RA-044-Structured-Powertrain-Identity-Implementation-Architecture.md) for the accepted baseline implementation architecture (2026-11-07); implementation remains pending separate authorization and [ADR-0012](../ADR/ADR-0012-Structured-Powertrain-Identity-And-Hybrid-Terminology.md) for the accepted powertrain and tuning policies.
