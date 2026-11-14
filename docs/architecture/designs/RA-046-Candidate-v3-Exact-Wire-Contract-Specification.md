# RA-046 — Candidate v3 Exact Wire Contract Specification

Created: 2026-11-13
Last Updated: 2026-11-13
Status: Approved
Approved: 2026-11-13

**Approval:** Explicit Project Owner approval on 2026-11-13 for the current reviewed
revision, including the final contract clarifications.

**Authority:** Approved Candidate v3.0.0 exact wire-contract specification. [ADR-0013](../ADR/ADR-0013-Unified-Factory-Body-Identity.md)
and [RA-045](RA-045-Unified-Factory-Body-Identity-Architecture.md) govern the semantics.
The exact wire choices below are approved for this revision. Approval does not
authorize future contracts, persistence, live resolution, publication or operational
writes. Candidate validity itself remains neither evidence acceptance nor import
authorization.

## 1. Scope, findings and continuity

This specification resolves the full Candidate 3.0.0 envelope, recursive closed
shapes, sparse parent descriptors, qualified evidence, normalization, hashing and
validation boundaries left open by the [phase-one handoff](../../implementation/handoffs/RA045_phase1_20261113/README.md).
Only this document is delivered. No schema file, executable fixture, application/test
change, migration, candidate regeneration, publication, staging, commit or import occurs.

Read governing AGENTS/GEMINI/CURRENT_STATE, ADR-0002/0007/0010–0013, RA-011/024/025/044/045,
W2 domain/publication proposals, current contracts, serialization, normalization,
candidate construction, classification adjudication, Generation correspondence,
planning/execution and representative MY2024 Candidate 2.1.0/continuation artifacts.

| Repository evidence | What is actually reusable / limitation |
| --- | --- |
| [contracts](../../../reference/ingestion/contracts.py), [serialization](../../../reference/ingestion/serialization.py), [validation](../../../reference/ingestion/validation.py) | Existing envelope, candidate terminology, technical projections and document-qualified interpretations; v1/v2 retain unknown-field preservation. This proposed v3 instead closes modeled objects explicitly. |
| [Generation normalization](../../../reference/ingestion/normalization/generation.py), [correspondence](../../../reference/ingestion/generation_correspondence.py) | Existing retained-document fields, four-part assertion reference, explicit source identities and exact Generation projection. Context names or PK 32 alone do not establish correspondence. |
| [powertrain identity](../../../reference/ingestion/importing/powertrain_identity.py), [RA-044](RA-044-Structured-Powertrain-Identity-Implementation-Architecture.md) | Five exact fields, source-qualified support and existing classification guards; ESS is not MHEV and missing fuel is not gasoline. |
| [body primitives](../../../reference/body_identity.py), [v3 foundations](../../../reference/ingestion/candidate/v3_foundations.py) | Sparse body/2 and baseline/2 construction/hash/comparison exist; v3 currently supports only an isolated identity-field projection and rejects non-null parents. Its checksum is not the artifact hash below. |
| [adjudication](../../../reference/ingestion/classification_adjudication.py), [RA-025](RA-025-Production-Manufacturer-Extraction-Review-Adjudication-Architecture.md) | Human findings remain distinct from manufacturer claims; implemented classification 1.1 explicitly requires a Candidate 2.1.0 base. No silent v3 reuse as a new adjudication approval. |
| [planner](../../../reference/ingestion/importing/planner.py), [execution](../../../reference/ingestion/importing/importer.py), [RA-024](RA-024-Canonical-Reference-Import-Execution-Execution-Provenance-Workflow-Architecture.md) | Plans and exact authorization, stale checks, atomic writes/receipts remain mandatory; no operational v3 execution path exists. |

The retained inventory has 31 active consumer offerings, ten two-door and 21 four-door;
normalizing Unlimited away causes ten collisions under current body-independent identity.
This document does not reclassify engines, publish pending Generation correspondences,
verify unavailable original MY2024 PDFs, or reinterpret transcription hashes as originals.
The accepted door taxonomy can be reused without a second body-review stage.

## 2. Primitive types and closed-object notation

In the type tables, unmarked members are required; `?` means optional/omittable;
`T|null` permits literal null. No other members are allowed. Omitted optional members
are NOT inserted during parsing or hashing. Optional omission and explicit null can
have the same absence meaning but different artifact bytes/hashes. Empty lists are
allowed unless `+` is written. Duplicate identifiers/references are rejected.

| Type | Exact constraint |
| --- | --- |
| Token | `[a-z0-9]+(?:[-._][a-z0-9]+)*`, ASCII, 1–128 characters, as W2 domain §8. No automatic casefolding, transliteration or measurement rounding. |
| Text | Nonempty Unicode scalar string after checking it contains non-whitespace; stored spelling is unchanged. No lone surrogates. |
| ID | Text without `|`; local IDs/source IDs/assertion-set IDs/assertion IDs must not contain the qualifier separator. Existing interpretation IDs may be qualified references and thus contain `|`. |
| Hash | `sha256:` plus exactly 64 lowercase hexadecimal characters. |
| UUID | Canonical lowercase hyphenated non-nil UUID string; no UUID minted in a pending descriptor. UUID format validation does not establish existence. |
| Year | JSON integer 1–32767, never boolean. |
| Market / Drive | `US`, `CA`, `OT` / `2WD`, `4WD`, `AWD`, `UNK`. Null or UNK does not establish executable drive. |
| RefPath | Nonempty repository-relative POSIX retained-artifact path; no leading slash, empty/`.`/`..` components or backslashes. Future byte verification must confine resolved paths to the authorized root, including symlinks. A URL is not a retained path. |
| Timestamp | RFC3339 UTC `YYYY-MM-DDTHH:MM:SS[.ffffff]Z`; no automatic timestamp generation during serialization. |
| Scope | `{manufacturer_key:Token, model_key:Token, generation_key:Token}`; proposed controlled registry scope, independently verified by Generation resolution before execution. |
| ModelScope | `{manufacturer_key:Token, model_key:Token}`; exactly the first two Scope keys. |
| QRef | `source_id|raw_artifact_hash|assertion_set_id|assertion_id`; four exact components, Hash syntax in component two, resolves to exactly one embedded retained assertion. |
| JSON | Recursive JSON values; duplicate keys, nonfinite numbers and non-string object keys forbidden. Objects inside raw source values are opaque source data, not an escape for candidate fields. |

All modeled objects below are recursively closed. The only free-key source-data maps
are `raw_value`, `raw_source_value`, `TechnicalValue.extra_context`, and
`DrivetrainComponent.extra_properties`;
these are inert JSON, never executable canonical body/series fields. Other maps have
explicit constrained key domains. No `unknown_fields`, arbitrary extension bag,
`$ref`, expression, script or fetch instruction is evaluated.

## 3. Exact envelope and root object

Dispatch on **both** `envelope.artifact_type = "rigarchive.candidate_configuration.v3"`
and `envelope.schema_version = "3.0.0"`. Schema identifier is exactly
`urn:rigarchive:contract:candidate_configuration:3.0.0`, stored in the required
`envelope.$schema`. This URN is a local identifier, not a network resource.

**Envelope** = `{artifact_type:constant, schema_version:constant, $schema:constant,
created_at?:Timestamp, generator?:Text}`. Preserve existing field names; require the
schema identifier only for v3. A created time/generator, when supplied, is hashed.

| Candidate root member | Type / constraint |
| --- | --- |
| envelope | Envelope |
| candidate_reference | Text, transient artifact identifier, never canonical UUID |
| candidate_identity | CandidateIdentity below |
| canonical_scope | Scope|null; null is a structurally valid unresolved-Generation draft |
| canonical_identity_contract | Constant `vehicle-definition-body/2` |
| drivetrain | Drive|null; explicit canonical projection, separate from retained rich drivetrain |
| configuration_refs | QRef[+]; references to claimed positive grouping/coexistence evidence; source-established same-configuration membership must independently satisfy §4.1 |
| applicability | Applicability[+], sorted unique applicability_id |
| evidence_documents | EvidenceDocument[+], sorted by (source_id, raw_artifact_hash, assertion_set_id) |
| evidence_raw_hashes | Hash[+], sorted unique, exactly the retained documents' hashes |
| generation_evidence | GenerationEvidence[], exact current source-identity projection, sorted by qualified assertion identity |
| normalized_assertions | Interpretation[], sorted unique interpretation_id |
| source_configuration_identities? | SourceConfigurationIdentity[], sorted by (source_id, identity_type, native_identifier) |
| canonical_powertrain? | null or Powertrain; a non-null object has exactly five keys, nullable values in drafts |
| factory_body? | null or BodyParent union (§5) |
| factory_series? | null or SeriesParent union (§6) |
| reviewed_findings? | FindingReference[], sorted unique finding_id; empty/omitted is normal |
| attribute_provenance? | Map from Text attribute key to sorted unique QRef[+]; canonical-target entries must agree with interpretations, not replace them; retained technical entries remain nonidentity lineage |
| normalized_technical_details? | NormalizedTechnicalDetails|null (§8) |
| factory_technical_features? | FactoryTechnicalFeature[] (§8), retained order |
| packages_and_options? | PackageOrOption[] (§8), retained order; not identity |
| reconciliation_and_review? | ReconciliationAndReview|null (§8); advisory derived workflow state, never approval |
| revision_lineage? | Lineage (§8), replacing free-form research_revision_lineage for new v3 only |
| candidate_hash | Hash calculated by §9 |

**CandidateIdentity** = `{manufacturer_name:Text, vehicle_model_name:Text,
model_year:Year|null, market:Market|null, trim_name:Text|null, generation_name?:Text|null}`.
Trim is at most 100 characters and is exact canonical marketed trim. Source trim
belongs in raw assertions/manufacturer_term, not a door suffix or engine descriptor.
Names and proposed Scope must agree through qualified taxonomy; names/keys alone
are not proof. A draft may leave year/market/trim null with retained evidence and
existing incomplete-classification behavior, not a universal body-review obligation.

**Powertrain** has exactly `engine_displacement_liters:string|null`,
`engine_cylinders:integer|null`, `engine_aspiration:token|null`, `fuel_type:token|null`,
`electrification_type:token|null`. Reuse `reference.powertrain.validate_powertrain`:
positive displacement below 1000, at most two fractional digits, exact canonical
Decimal string without insignificant trailing zeros; cylinders 1–32767;
aspiration `naturally_aspirated|turbocharged|supercharged|twincharged|other`;
fuel `gasoline|diesel`; electrification `none|mild_hybrid|hybrid|plug_in_hybrid`.
Do not add unsupported electric/fuel vocabularies through this task. Other aspiration
and incomplete tuples retain existing eligibility safeguards. No null-to-default inference.

The candidate proposes identity; it does NOT contain an import eligibility flag,
canonical slug, new parent UUID allocation, live-peer proof, plan or execution approval.

## 4. Exact retained evidence, applicability and interpretation shapes

**EvidenceDocument** required members are `{source_id:ID, raw_artifact_hash:Hash,
raw_artifact_reference:RefPath, extractor_id:Text, extractor_version:Text,
extraction_mode:Text, assertion_set_id:ID, assertions:Assertion[+]}`. Optional members:
`source_locator:Text|null`, `retrieved_at:Timestamp|null`,
`source_applicability:SourceApplicability|null`, `publication_revision:Text|null`,
`generation_normalizer:{id:Text,version:Text}`. Assertions sort by assertion_id.

**Assertion** = `{assertion_id:ID, attribute_key:Text, raw_value:JSON,
source_context:Text, extracted_at?:Timestamp|null}`. Raw value may be null; do not
change an existing assertion value or its source_context while copying it. Original
JSON lexical number formatting is preserved by the retained raw artifact bytes/hash,
not recreated from an embedded parsed excerpt. New v3 wrappers omit old empty
unknown_fields containers; nonempty legacy extensions need explicit interpretation
or retention solely as source evidence, never silent promotion.

**SourceApplicability** = `{market?:Market|null, applicability_basis?:Text|null,
publisher_jurisdiction?:Text|null, applicability_scope?:"configuration"|"model_year"|null}`.
This preserves existing provenance fields; country of hosting/publisher is not commercial market.

**SourceConfigurationIdentity** = `{source_id:ID, identity_type:Text,
native_identifier:Text, source_description?:Text|null}`. Source_id must resolve to a
retained document; positive coexistence comes from configuration_refs and original
source grouping, not native code equality. Code reuse across years/engines/grades is normal.

**GenerationEvidence** retains exactly `{source_id:ID, source_namespace:Text,
identity_type:"model_code"|"generation_designation", native_identifier:Text,
document_hash:Hash, assertion_set_id:ID, assertion_id:ID, normalizer_id:Text,
normalizer_version:Text}`. Reproduce `generation_evidence_from_documents` exactly:
source namespaces `generation_designation|generation_code|source_model_code|generation_section`,
normalizer `explicit_generation_identity` / `1.0.0`, identities derived only from
those explicit assertions. All expected identities must be present, even conflicting
ones; none are canonical Generation approval. No invented JK/JL model-year inference.

**Applicability** = `{applicability_id:ID, scope:Scope|null, market:Market|null,
start_year:Year|null, end_year:Year|null, configuration_refs:QRef[+],
source_assertion_refs:QRef[+], finding_refs:ID[]}`. Both years are null or both valid
with start <= end; null is unestablished coverage, not unlimited coverage. A populated
Scope must match canonical_scope. Every asserted parent/interpretation references one
entry. Configuration refs must be within root configuration_refs; all lists are sorted
unique. A binding may narrow source coverage but cannot broaden it. Source assertions
or an applicable reused finding must support the actual model/year/market/configuration
join. Several fields can share one entry and one legitimate composite source assertion.

### 4.1 Positive grouping is a source claim, not document membership

`configuration_refs` provide positive grouping evidence **only when the underlying
source establishes that the referenced assertions describe the same factory
configuration**. A reference's presence or successful QRef lookup does not establish
that relationship. Distinguish:

- Positive same-configuration membership: an explicit configuration row, selector
  entry, source-native grouping or demonstrated cross-reference establishes the
  attributes' coexistence for the applicable factory configuration.
- Mere proximity: assertions share a document, source assertion set, table or
  extraction batch without a source-established relationship. This is not coexistence.
- Alternatives: assertions describe mutually exclusive choices or different factory
  configurations. Shared location does not permit combining them into one baseline.

Body, series, trim, drivetrain and powertrain assertions from independent sources
must not be assembled into a purported factory configuration without sufficient
qualified coexistence evidence. A broad shared model code or equal attribute text
is not a substitute for the demonstrated join. Preserve legitimate existing grouping
and cross-source linkage through the current references, source_context, applicability
and retained findings; no new mandatory evidence field or extra body review is added.
Sparse proposals need support only for their actual asserted identity, not fabricated
combinations or missing-dimension findings. Historical contracts remain unchanged.

**Interpretation** required shape:
`{interpretation_id:Text, source_assertion_ref:QRef, target_attribute_key:Target,
normalized_concept:typed-value|null, mapping_status:"mapped"|"unresolved"|"conflicting",
applicability_ref:ID, normalization:{id:Token,version:"1.0.0"}, finding_refs:ID[]}`.
Optional: `raw_source_value:JSON`, `manufacturer_term:Text|null`,
`normalization_notes:Text|null`. raw_source_value, when present, equals the referenced
raw_value. Every finding_ref resolves; applicability_ref covers this positive source
group. Null/unresolved/conflicting entries are retained but do not establish values.
Human approval cannot waive a hard source/parent contradiction or substitute an
unsupported value; source-scope correction must itself have attributable evidence.

**Target** is closed: `make`, `model`, `model_year`, `market`, `trim_name`,
`generic_drive_classification`, `canonical_scope.manufacturer_key`,
`canonical_scope.model_key`, `canonical_scope.generation_key`, the five Powertrain
field names, `factory_body.` followed by one of the seven explicit dimension names,
`factory_series.namespace`, `factory_series.designation`, `factory_series.identity_role`,
or `body_identity_equivalence`. Values use the matching destination type; series role
is exactly `independent_series`; equivalence is a body semantic Hash. Targets do not
admit arbitrary attribute names. Technical-only facts remain in retained assertions
and §8 projections rather than expanding the canonical target vocabulary.

Proposed normalization registry for 3.0.0 (all version `1.0.0`):

| normalization.id | Exact permitted operation / prerequisites |
| --- | --- |
| source_literal | Select the target's explicit same-typed value from raw scalar or the unique named member of one composite raw configuration object. Compare strings exactly; no unsupported inference. For composite objects the member is the full target key or its canonical source key (`make`, `model`, `model_year`, `market`, `trim_name`, `generic_drive_classification`); aliases require a different rule. Ambiguous members do not project. |
| decimal_liters | Explicit displacement supplied in liters; use existing exact Decimal-string rules. No rounding or inferred unit; displacement is not a body designation. |
| powertrain_terminology | Reuse RA-044’s existing explicit raw-support checks for the five powertrain targets in the exact supported configuration. Liters/cylinders must be explicitly expressed with unambiguous units/count; use existing Decimal handling. Explicit turbo/naturally-aspirated, gasoline/petrol/diesel and hybrid terminology must uniquely support the proposed token. eTorque maps to mild_hybrid and 4xe to plug_in_hybrid only in their supported Wrangler configuration; ESS alone establishes neither MHEV nor none. No engine-code-only, adjacent-year or absent-label inference; newly ambiguous classifications retain normal review. This rule does not require a second human approval for an already approved direct source normalization. |
| wrangler_selector_heading | Parse the retained explicit `United States / MY2024 / Jeep Wrangler (<doors>) / <source trim> [<model code> / <QOP>]` heading grammar; project only literal make/model/year/US market and exact canonical trim pairs in the owner-required MY2024 normalization audit. Sport maps to Sport; Unlimited Sport maps to Sport. Other pairs must be in that retained reviewed mapping, not invented by unrestricted prefix stripping. Missing/contradictory headings stay unresolved. This compiled accepted mapping requires no additional body-only review. |
| wrangler_door_taxonomy | Within the reviewed Wrangler JL source grouping, explicit `(2-door)`/`2-Door`/`two-door` or `(4-door)`/`4-Door`/`four-door` taxonomy maps to two-door/four-door. Exactly one door class must be asserted for that positive group. Unlimited alone, model-code suffix alone, adjacent year, or absence is insufficient. Evidence of canonical Sport and door count remains separate. Existing qualified headings can support doors directly; no extra finding_ref or parent-review approval is required. |
| reviewed_alias | Apply exact scoped source spelling/typed-value equivalence explicitly identified by a referenced existing reviewed finding. No free-form notes can create a mapping. Multiple claims can reuse that same finding. |
| reviewed_classification | Reuse a qualified, explicitly approved interpretation within its original authority/applicability. Requires applicable finding_ref; cannot carry a Candidate 2.1.0-bound approval onto a different v3 base. A new material decision uses the separately versioned future adjudication contract. |
| existing_body_equivalence | Existing parent only: an exact complete native configuration/body alias is already linked by the referenced immutable binding revision to this frozen body digest in this scope/applicability. A broad model code, unique compatible match, or matching label alone is insufficient. Resolving that recorded equivalence requires live binding verification, not a new human review. |

This registry is a proposed wire-level selection, not a claim that these implementations
already exist or that every retained raw string is covered. Future implementation
must implement these exact accepted rules and reject unknown IDs/versions; rule changes
require versioned artifacts/review, never mutable behavior under an unchanged identifier.
Unsupported raw formats stay unresolved or use an existing reviewed mapping. Do not
silently widen a regex to approve values. Retained review evidence, not this specification,
establishes a real manufacturer's classifications.

**FindingReference** = `{finding_id:ID, artifact_type:"workflow_review"|"canonical_import_adjudication"|"generation_correspondence_review",
artifact_version:Text, artifact_reference:RefPath, artifact_hash:Hash,
locator:Locator, applicability_ref:ID}`. **Locator** is exactly either
`{kind:"json_pointer",pointer:string}` (RFC6901; empty root allowed) or
`{kind:"utf8_lines",start_line:positive-integer,end_line:positive-integer}` (inclusive,
start <= end). This is a reference to an already retained finding, not a new approval
artifact format or a boolean `approved` assertion. Per-type/version readers must verify
the underlying finding's authority, exact original scope, approved disposition and
bound base hashes. Unknown reader/version yields an unsupported-review dependency
at resolution; do not treat an arbitrary Markdown line or JSON pointer as authorization.
Finding applicability_ref identifies intended scope, never self-proves it; read the
original artifact independently and reject circular/self-supporting finding chains.
A Generation finding establishes Generation only, not body/grade/classification.
Proposed/pending decisions remain proposed; no source assertion is relabeled human-approved.
No finding_ref is required for mere missingness or a direct supported normalizer.

## 5. FactoryBodyConfiguration parent union

`factory_body` may be omitted or null. No body status, placeholder, negative-evidence
finding, seven-status checklist or separate body-publication review is required.
When non-null it is **exactly** one of:

**PendingBody** = `{disposition:"pending", identity:BodyIdentity, support:ParentSupport}`.
No parent_uuid, binding_revision, created UUID or existence claim is permitted.

**ExistingBody** = `{disposition:"existing", parent_uuid:UUID, identity:BodyIdentity,
binding_revision:BindingRevision, support:ParentSupport}`.

**BodyIdentity** = `{semantic_digest:Hash, preimage:BodyPreimage}`.
**BodyPreimage** = `{identity_contract:"factory-body-semantic/2",
profile_family:"factory-body", scope:Scope, dimensions:Dimensions}`.
**Dimensions** is nonempty and admits only `body_style`, `wheelbase_designation`,
`body_length_designation`, `roof_height_designation`, `door_configuration`,
`side_door_arrangement`, `body_code`. Values are Token; body_code is exactly
`{namespace:Token,token:Token}`. Omit blank dimensions; null/empty-string dimensions
are not canonical preimage entries. Input normalization can omit blanks, but serialized
preimages contain established values only. Body form need not be populated.

**ParentSupport** = `{applicability_ref:ID, configuration_refs:QRef[+],
interpretation_refs:Text[], equivalence_interpretation_ref:Text|null}`.
Lists sort uniquely; support.applicability_ref and binding_revision.applicability_ref
must be identical in existing mode. configuration_refs must be a subset of the referenced
Applicability and root grouping. All interpretation_refs resolve to normalized_assertions
using this same applicability_ref and positive source group. A populated designation
requires evidence of an identity-bearing factory baseline, not merely an equipment
option with the same words. source_literal validates a typed value but does not
on its own convert optional door equipment into structural identity. Unclear actual
equipment/body taxonomy follows normal review; unreported fields do not. For pending body, equivalence reference must be null;
every frozen basis entry needs support from mapped field interpretations (one composite
source/finding may support all entries). No identity-bearing known distinction may be
silently dropped. At least one supporting interpretation is therefore needed.

For existing body, the same direct complete basis support suffices without new review.
Alternatively, sparse observations plus `equivalence_interpretation_ref` may reuse an
already-established complete-configuration equivalence to the *exact* frozen digest.
The referenced interpretation must have target body_identity_equivalence, normalizer
existing_body_equivalence, matching digest/applicability, and a qualified assertion
matching an alias recorded in the specified binding revision. Existing supported
observations may not contradict the frozen basis. A merely compatible subset, or
unique compatible candidate, never supplies missing equivalence. The planner must
not silently add missing basis dimensions to the candidate before hashing.

**BindingRevision** = `{revision_uuid:UUID, content_hash:Hash, applicability_ref:ID}`.
The referenced immutable persisted revision is independently fetched and hash-checked
later. Its canonical snapshot content/hash contract belongs to the later binding/proof
implementation, not a new Candidate-owned publication schema. Its persisted parent,
frozen preimage/digest, source grouping, scope, applicability, active/supersession state
and full parent chain must agree. Candidate binding applicability_ref identifies the
exact candidate coverage being claimed, which must be contained by the revision's
supported coverage; UUID alone never establishes it. Parent identity/binding mismatch
or unavailable support blocks reuse, without mutating historical bindings.

The body semantic digest is recomputed from the preimage, not trusted. It binds scoped
meaning only. Parent UUID and revision hash are required in existing mode; candidate
Scope, duplicated preimage Scope and applicability Scope must agree. Existing parent
records/bindings do not yet exist in the deployed schema; example D is synthetic.

A pending descriptor means **not bound to a persisted parent**, not a certificate
that the namespace is empty or that a new body is distinct. Its deterministic
proposal checksum is SHA-256 of canonical JSON for the entire PendingBody object
(including support), with no stored checksum member. Identity digest is separately
recomputed from identity.preimage. Both are derivable; neither authorizes a write.
Read-only planning compares the relevant peer/source evidence set as a whole,
without first-match selection or record-order dependence. The following outcomes
apply to pending body parents and, under §6, pending series parents.

### 5.1 Read-only pending-parent outcomes

| Outcome | Required identity/evidence relationship | Permitted planning result |
| --- | --- | --- |
| A. Exact established identity | Evidence establishes a match under the governing semantic rules, not mere compatibility | Proposed reuse, subject to independently verifying the existing parent's frozen identity, immutable binding and exact applicability |
| B. Supported new distinct identity | Positive factory evidence establishes an identity distinct from relevant existing parents; a genuinely empty relevant namespace still requires positive support for the proposed identity | Proposed creation, subject to the existing evidence, planning, exact authorization, stale-state and atomic execution safeguards |
| C. Unresolved identity relationship | Incomplete, contradictory or insufficient evidence establishes neither exact reuse nor supported distinct creation | No create/reuse disposition; retain the unresolved relationship for applicable targeted review or reconciliation |

A newly calculated semantic digest is not evidence that a new parent should be
created. Absence of an exact digest match is not sufficient proof of distinct identity.
Compatibility of partial observations is not proof of identity. In particular, a
pending sparse basis can hash differently from all existing frozen bases while its
relationship to them remains unresolved (C); no automatic creation follows.

Missing optional body dimensions alone do not require review, block an otherwise
supported candidate or require a parent. Outcome C concerns an actual unresolved
identity relationship affecting a proposed action, not hypothetical unknown fields.
Candidates needing neither body nor series parents continue through the ordinary
workflow without this becoming a mandatory parent-publication or review stage.

Later execution may create parent+binding+VD+receipt atomically only when exact write
authorization covers those operations and read-only premises are still current. A
reviewed plan expecting creation cannot silently switch to reuse after namespace
change, nor allocate a UUID early. Abort stale state and obtain fresh exact review;
any batch replanning remains within its separately approved exact batch protocol.
Shared source/body findings are reused, not independently approved per engine or trim.

## 6. Independent FactorySeries union

Series is independently omitted/null or:

**PendingSeries** = `{disposition:"pending", identity:SeriesIdentity, support:ParentSupport}`.
**ExistingSeries** = `{disposition:"existing", parent_uuid:UUID, identity:SeriesIdentity,
binding_revision:BindingRevision, support:ParentSupport}`.
**SeriesIdentity** = `{semantic_digest:Hash, preimage:{identity_contract:"factory-series-semantic/1",
scope:ModelScope,namespace:Token,designation:Token}}`.

Model scope must match canonical_scope's manufacturer/model. Support establishes
namespace/designation **and** a mapped factory_series.identity_role = independent_series,
through the manufacturer's taxonomy or an applicable existing reviewed finding.
This is evidence that a *populated* series has the intended meaning, not a requirement
to adjudicate absent series. One existing finding/composite source can support all three
interpretations; no new human decision per field. Never also represent the same
series discriminator as canonical trim. String similarity alone cannot decide that;
actual conflicting taxonomy is reviewed normally. Physical capacity/measurements are
not series identity by default.

For this first exact series wire, equivalence_interpretation_ref is always null;
namespace/designation/role need direct qualified support even for existing parents.
No generic series-equivalence rule is silently introduced. Existing bindings can be
reused as supporting reviewed evidence within their original scope without new review.
Parent/binding applicability is still checked for exact year/market/Generation even
though semantic identity is model-scoped. Body and series may independently be pending,
existing or absent. Body codes cannot substitute for independent series evidence. Pending series uses
the same three read-only outcomes in §5.1; no absent-series review is introduced.

## 7. Projection, evidence and resolution responsibilities

Validation returns stage-specific diagnostics `{stage,code,path,message}`; this is the
proposed diagnostic shape, not a future proof/resolution schema. path is RFC6901.
The candidate itself stores no live-parent alternative list or execution eligibility.
A truthful conflicting/incomplete source set can be structurally valid while unresolved.

### 7.1 Structural and cryptographic validation

This layer checks the exact Candidate 3.0.0 schema, enumerations and discriminated
unions; deterministic canonical serialization of identity preimages; independently
reconstructed semantic digests and the whole-candidate artifact hash; and contract-level
field/reference requirements, including locally resolvable qualified references.
It establishes the document's structural/cryptographic validity, not the truth or
applicability of its normalized claims. A resolvable reference is not source support.

### 7.2 Evidence and identity validation

Independently assess qualified support for normalized values, source applicability
and positive coexistence (§4.1), contradictions or unsupported identity conclusions,
and whether parent reuse or creation is justified under §5.1. Actual unresolved
relationships follow targeted review/reconciliation. Live resolution can remain
unresolved despite successful structural/hash validation; do not relabel that outcome
as a schema or hash failure.

**A structurally valid, correctly hashed Candidate v3 document is not thereby
evidence-accepted, resolution-approved, publication-eligible, or authorized for
canonical import.** These are separate boundaries. No approval state is added to
§9's hash algorithm, and contract validity is not adjudication.


| Situation | Contract/evidence result | Later resolution / action |
| --- | --- | --- |
| Same normalized frozen basis, alias/evidence labels differ | Valid; same semantic digest, possibly different artifact hash | Potential exact reuse/no-op after qualified/current-state checks |
| Established two-door versus four-door | Valid distinct bodies, not a contradiction merely because they differ | Distinct supported VD identities; body-aware create basis subject to normal gates |
| Omitted irrelevant roof/side doors, no evidenced alternatives | Valid sparse body; no missing-body diagnostic | Proceed normally; no hypothetical review |
| No demonstrated body distinction | factory_body null/omitted is valid | Existing no-body workflow; no placeholder/review/selector/suffix requirement |
| Existing parent supported by full basis or recorded complete-configuration equivalence | Valid reference, not yet proven live | Unique safe reuse once immutable binding/Generation/current state revalidate; no duplicate body review |
| Partial observation matches exactly one parent but lacks equivalence | Valid pending observation; not proven equal | Seek already available source equivalence; no automatic parent assignment or new-identity creation. Only actual inability to distinguish the proposed action triggers review, not missingness itself. |
| Partial observation fits two established alternatives | Valid pending sparse candidate (H); schema does not encode an arbitrary selection | `resolution/BODY_AMBIGUOUS`, review-required and execution-ineligible; compare whole set, order independent |
| Conflicting known assertions about one positive configuration | Preserve both conflicting interpretations; structure may be valid | `evidence/SOURCE_CONFLICT`, review-required and execution-ineligible; do not choose a favorable source |
| Candidate contradicts its selected mapped value or known discriminator is omitted to force equality | Structurally parseable; `evidence/PROJECTION_MISMATCH` or `KNOWN_DISCRIMINATOR_OMITTED` | Invalid evidence projection; cannot match/create by omission; no blanket requirements for unreported fields |
| Null legacy VD body association | Neither complete assessment nor universal body | Existing legitimate matching/no-op remains possible absent evidenced conflict; actual ambiguous overlap requires targeted reconciliation, not an automatic null-body gate |

Structural and cryptographic errors use `contract/` codes: UNKNOWN_FIELD,
MISSING_FIELD, INVALID_TYPE, INVALID_TOKEN, DUPLICATE_KEY, DUPLICATE_ID,
NONCANONICAL_ORDER, UNSUPPORTED_VERSION, INVALID_DECIMAL, INVALID_HASH,
INVALID_PREIMAGE, BROKEN_REFERENCE (unresolvable local contract references),
SEMANTIC_DIGEST_MISMATCH and ARTIFACT_HASH_MISMATCH. Independently unsupported
normalized values, falsely claimed applicability/coexistence and invalid human-finding
scope use `evidence/PROJECTION_MISMATCH`, APPLICABILITY_MISMATCH,
COEXISTENCE_NOT_ESTABLISHED and FINDING_SCOPE_MISMATCH; actual contradictions use
SOURCE_CONFLICT. A correctly hashed unsupported body projection fails evidence
validation, not schema/hash validation. Missing retained bytes/dependency reader are reported as
`dependency/UNAVAILABLE_ARTIFACT` or UNSUPPORTED_REVIEW_VERSION, not as invented source
contradictions. Changed bytes/revisions after review produce stale-artifact/plan
outcomes before execution. Diagnostic stage/code are stable strings; messages may
change. No automatic repair or null-fill occurs in validation.

Order: parse/close/type/order; reconstruct semantic digests and local references;
check qualified projection/applicability; evaluate actual source conflicts; later
read-only Generation/parent/whole-peer resolution; later exact proof/authorization.
Known-discriminator coverage is checked against the retained applicable source group
under the approved normalization rules, not only the interpretations a caller elected
to submit. Omitting a mapped door interpretation cannot hide an explicit reviewed
Wrangler door distinction in its qualified source heading. Ordinary unreported values
do not create a coverage requirement.

Checking artifact shape/hash alone confers no evidence validity or approval. A source
heading can support multiple interpretations, but unrelated co-listing cannot join
body, trim, year and powertrain into a fabricated tuple.

## 8. Retained technical, review and lineage types

These optional nonidentity payloads retain RA-011 terminology without opening a second
body schema. Fields below are all optional unless explicitly marked required; absent
projections do not discard source assertions. Unknown members remain forbidden.

| Type | Closed members and types |
| --- | --- |
| NormalizedTechnicalDetails | engine:EngineDetails|null; drivetrain_details:DrivetrainDetails|null; transmission:TransmissionDetails|null |
| TechnicalValue | normalized_value:finite JSON number or string or null; normalized_unit:Text|null; raw_source_string:Text|null; rpm_normalized:integer|null; extra_context:JSON-object |
| EngineDetails | code:Text|null; cylinders:positive-integer|null; displacement:TechnicalValue|null; horsepower:TechnicalValue|null |
| TransmissionDetails | code:Text|null; type:Text|null; speeds:positive-integer|null |
| DrivetrainDetails | generic_classification:Drive|null; architecture:Text|null; components:DrivetrainComponent[]; operating_modes:DrivetrainMode[]; capabilities:Text[]; manufacturer_terminology:Text|null |
| DrivetrainComponent | component_type:Text **required**; name:Text **required**; low_range_ratio:finite JSON number|null; has_locking_feature:boolean|null; extra_properties:JSON-object |
| DrivetrainMode | mode_code:Text **required**; name:Text **required**; center_coupling:Text|null; center_differential_state:Text|null; low_range:boolean|null; torque_split_default:Text|null |
| FactoryTechnicalFeature | feature_name:Text **required**; source_classification:Text|null; normalized_classification_status:Text|null; source_assertion_ref:QRef|null; category_status:Text|null; notes:Text|null |
| PackageOrOption | name:Text **required**; source_classification:Text|null; normalized_classification_status:Text|null; is_distinct_trim_identity:boolean; availability:Text|null |
| ReconciliationAndReview | requires_human_review:boolean; review_workflow_disposition:`not_required|pending_review|under_review|resolved|rejected_excluded`; attribute_states:map Text attribute key to AttributeState; reconciliation_notes:Text|null |
| AttributeState | reconciliation_state:`single_source|corroborated|conflicting|ambiguous|incomplete` **required**; review_disposition:same review-workflow enum **required**; conflict_details:Text|null |
| Lineage | base_artifact_reference:RefPath **required**; base_artifact_hash:Hash **required**; base_schema_version:Text **required**; change_reason:Text **required** |

The legacy Text-keyed provenance/review maps remain nonidentity annotations. They
are not extension bags for executable candidate fields: canonical entries must agree
with qualified interpretations and technical entries must point to retained technical
facts; unknown strings never become body dimensions or import decisions.

Rich drivetrain/engine projections cannot contradict an asserted canonical value.
No transmission, package, output number, notes or decorative label becomes a body or
powertrain discriminator through §8. When copying a historical artifact, retain it as
an immutable lineage source. Conversion into a new v3 revision is explicit; the old
artifact is never rewritten. Self-reported resolved review state cannot override
missing qualified evidence or pending owner approvals. Missing optional dimensions
must not generate attribute_states entries requiring review.

## 9. Semantic versus artifact hashing

Semantic preimages follow accepted RA-045/W2 rules, not new hashes over labels:
body/2 uses exactly its sparse preimage; series uses factory-series-semantic/1;
baseline/2 has exactly identity_contract, scope, model_year, trim_name, drivetrain,
market, canonical_powertrain, body_digest (Hash|null), series (null or `{digest:Hash}`).
It excludes engine_name, parent UUIDs, evidence, aliases and display labels. Require
the complete existing five-field engine before constructing an executable baseline/2;
incomplete drafts have no fabricated baseline digest. These three preimages are not
stored as an additional redundant root baseline projection; reconstruct when complete.

The **candidate_hash** is:

```text
sha256: + lowercase_hex(SHA256(UTF8(CANONICAL_JSON(root without root.candidate_hash))))
```

Exclude **only** the top-level candidate_hash. Include envelope.$schema, artifact_type,
schema_version, optional timestamps/generator when supplied, all proposed parent
payloads, revision UUID/hash references, applicability, complete evidence excerpts,
raw document hashes/paths, normalization IDs/versions, findings and lineage. No recursive
hash-field stripping: a nested artifact_hash/content_hash remains bound. No excluded
"mutable metadata" bag. Candidate hash is not the file's raw-byte hash; retained file
integrity checks use raw SHA-256 separately where an artifact reference specifies it.

CANONICAL_JSON is the existing project's Python canonical JSON convention:
`json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)`
encoded as strict UTF-8 without BOM/newline. Recursive object keys are sorted using
Unicode scalar/codepoint order; no Unicode NFC/NFKC, trimming or case changes. Pretty
printing is permitted for transport; parse with duplicate-key rejection at every level
before validating/hash reconstruction. Set-like arrays must already be in the specified
canonical order; reject rather than silently reordering a received signed/hashed payload.
Reference string lists sort lexically; qualified Generation identities sort by
(source_id, document_hash, assertion_set_id, assertion_id). Every other modeled array
preserves order and thus changes artifact hash when reordered. Raw JSON arrays always
preserve source order, irrespective of their contents.

Canonical identity/powertrain decimals are strings, never binary floats; canonical
positive liters must equal existing decimal_string output. Retained nonidentity TechnicalValue numbers and raw JSON may
contain finite integer/binary64 number values as parsed by Python 3.13's standard
JSON decoder; canonical number formatting follows that pinned encoder, including
`1.0` versus `1` and exponent formatting. Reject NaN/Infinity, overflow to infinity,
booleans in numeric typed fields and lone surrogates before encoding. Raw source
numeric lexemes are authenticated in original artifact bytes, not reconstructed from
parsed JSON. This is explicitly the existing Python convention, **not RFC8785/JCS**;
other-language readers need conformance vectors before acceptance.

Absent optional fields stay absent; null stays null. Semantic identity can remain
unchanged while path, finding revision, alias, optional metadata or evidence changes
candidate_hash. New normalization/binding applicability requires a new artifact hash
and review subject; no timestamp refresh or hash recomputation can silently preserve
old approval. Reconstruct exact candidate hash, semantic digests and retained references
before later planning; recheck state/bytes independently at execution. The isolated
phase-one projection checksum cannot be substituted at any step.

## 10. Compatibility and downstream coordination

| Contract | Explicit boundary |
| --- | --- |
| Candidate 1.x / 2.0.0 / 2.1.0 | Original readers, allowed fields, unknown-field preservation, serialization and hashes unchanged; no reinterpretation of old research body metadata. Existing fixtures stay byte-identical. |
| Candidate 3.0.0 | Require the exact envelope triple in §3; reject all other versions until separately supported. A v2 artifact_type with 3.0.0 or a v3 artifact_type with 2.1.0 is invalid. Unsupported readers must fail, never downgrade by discarding body fields. |
| Engine Proof 2.0 | Original five-field proof/legacy peer semantics remain; cannot attest a body-aware v3 match. |
| Adjudication 1.0 / 1.1 | Their original exact base/candidate/version/field limits remain. Retained applicable independent source findings may be cited honestly, but old candidate-bound approval does not approve a new v3 artifact. Future adjudication 2.0 must bind exact v3 review subjects. |
| Generation correspondence 1.0 | Reuse unchanged selector/evidence/year/market/restriction semantics where applicable; source lineage preserved. No new unsupported body restriction key. |
| Future proof 3.0 / Resolution 2.0 | Must bind exact candidate hash, semantic preimages, applicable immutable parent/binding snapshots, relevant whole-set peers and stale-state premises; not designed in full here. |
| Future Manifest/Matrix 3.0 and receipt snapshots | Must bind optional parents and exact create/reuse dispositions, explicit parent-write authorization, proof/version dispatch and atomic audit results. Historical manifests/matrices/receipt payloads remain unchanged. No new receipt schema is implemented or fully specified here. |

A Candidate v3 artifact is never executable merely because it validates. Existing
importer/executor must reject it until the coordinated future path is authorized,
implemented and tested. Ordinary no-body candidates do not need invented body parents
or reviews; legitimate historical-style Candidate 2.1 workflows remain supported in
scopes without a known body distinction. Caller selection of v2 cannot suppress a
known source distinction. Slug policy remains accepted ADR-0013 readable-first;
existing slugs are immutable under ADR-0002; a slug cannot repair semantic ambiguity.

## 11. Complete illustrative documents

All eight blocks below are **documentation fixtures only**, not executable artifacts,
verified factory offerings, approved classifications, real parent records or import
plans. A/D/E/F/G/H use clearly synthetic example-only source namespaces and parent
identifiers. B/C copy authentic identifiers, hashes and explicit heading assertions
from retained JL24-01/JL24-11 Candidate 2.1.0 documents; their new v3 references and
normalizer names are illustrative proposals, not regenerated candidates. They omit
unapproved engine/drive projections intentionally and are valid *drafts*, not eligible
imports. No Wrangler parent UUID or approval receipt is invented. Source paths/hashes
identify retained transcription bytes, not original manufacturer PDFs.

For executable implementation fixtures, copy actual retained document/qualified
assertion identifiers and source-context grouping byte-faithfully, obtain reviewed
controlled registry keys through the existing scope process, and resolve genuine
persisted parent/revision UUIDs only after authorized persistence exists. Recompute
all v3 hashes under the accepted spec; never promote synthetic example parents or
classifications. Fixture candidate hashes below are computed from their exact proposed
objects, not source authenticity or authorization claims.

### A. Ordinary 2007 Toyota 4Runner — hypothetical no-body proposal

Full hypothetical five-field powertrain illustrates no-body legality, not source approval or a statement about an actual imported 4Runner. Scope keys are example registry keys.

```json
{
  "envelope": {
    "artifact_type": "rigarchive.candidate_configuration.v3",
    "schema_version": "3.0.0",
    "$schema": "urn:rigarchive:contract:candidate_configuration:3.0.0"
  },
  "candidate_reference": "illustration-A",
  "candidate_identity": {
    "manufacturer_name": "Toyota",
    "vehicle_model_name": "4Runner",
    "model_year": 2007,
    "market": "US",
    "trim_name": "SR5"
  },
  "canonical_scope": {
    "manufacturer_key": "toyota",
    "model_key": "4runner",
    "generation_key": "example-fourth"
  },
  "canonical_identity_contract": "vehicle-definition-body/2",
  "drivetrain": "4WD",
  "configuration_refs": [
    "example_only_a|sha256:22eec990fae9c9f984d600e760e2941c5fe35ff1105f8bcb310871e4ba3ecd00|example-set|configuration"
  ],
  "applicability": [
    {
      "applicability_id": "app",
      "scope": {
        "manufacturer_key": "toyota",
        "model_key": "4runner",
        "generation_key": "example-fourth"
      },
      "market": "US",
      "start_year": 2007,
      "end_year": 2007,
      "configuration_refs": [
        "example_only_a|sha256:22eec990fae9c9f984d600e760e2941c5fe35ff1105f8bcb310871e4ba3ecd00|example-set|configuration"
      ],
      "source_assertion_refs": [
        "example_only_a|sha256:22eec990fae9c9f984d600e760e2941c5fe35ff1105f8bcb310871e4ba3ecd00|example-set|configuration"
      ],
      "finding_refs": []
    }
  ],
  "evidence_documents": [
    {
      "source_id": "example_only_a",
      "raw_artifact_hash": "sha256:22eec990fae9c9f984d600e760e2941c5fe35ff1105f8bcb310871e4ba3ecd00",
      "raw_artifact_reference": "docs/examples/not-retained/A.json",
      "extractor_id": "example-only",
      "extractor_version": "1.0.0",
      "extraction_mode": "illustration",
      "assertion_set_id": "example-set",
      "assertions": [
        {
          "assertion_id": "configuration",
          "attribute_key": "configuration",
          "raw_value": {
            "make": "Toyota",
            "model": "4Runner",
            "model_year": 2007,
            "market": "US",
            "trim_name": "SR5",
            "engine_displacement_liters": "4",
            "engine_cylinders": 6,
            "engine_aspiration": "naturally_aspirated",
            "fuel_type": "gasoline",
            "electrification_type": "none",
            "generic_drive_classification": "4WD"
          },
          "source_context": "Hypothetical positive configuration; not verified manufacturer evidence"
        }
      ]
    }
  ],
  "evidence_raw_hashes": [
    "sha256:22eec990fae9c9f984d600e760e2941c5fe35ff1105f8bcb310871e4ba3ecd00"
  ],
  "generation_evidence": [],
  "normalized_assertions": [
    {
      "interpretation_id": "i-electrification_type",
      "source_assertion_ref": "example_only_a|sha256:22eec990fae9c9f984d600e760e2941c5fe35ff1105f8bcb310871e4ba3ecd00|example-set|configuration",
      "target_attribute_key": "electrification_type",
      "normalized_concept": "none",
      "mapping_status": "mapped",
      "applicability_ref": "app",
      "normalization": {
        "id": "source_literal",
        "version": "1.0.0"
      },
      "finding_refs": []
    },
    {
      "interpretation_id": "i-engine_aspiration",
      "source_assertion_ref": "example_only_a|sha256:22eec990fae9c9f984d600e760e2941c5fe35ff1105f8bcb310871e4ba3ecd00|example-set|configuration",
      "target_attribute_key": "engine_aspiration",
      "normalized_concept": "naturally_aspirated",
      "mapping_status": "mapped",
      "applicability_ref": "app",
      "normalization": {
        "id": "source_literal",
        "version": "1.0.0"
      },
      "finding_refs": []
    },
    {
      "interpretation_id": "i-engine_cylinders",
      "source_assertion_ref": "example_only_a|sha256:22eec990fae9c9f984d600e760e2941c5fe35ff1105f8bcb310871e4ba3ecd00|example-set|configuration",
      "target_attribute_key": "engine_cylinders",
      "normalized_concept": 6,
      "mapping_status": "mapped",
      "applicability_ref": "app",
      "normalization": {
        "id": "source_literal",
        "version": "1.0.0"
      },
      "finding_refs": []
    },
    {
      "interpretation_id": "i-engine_displacement_liters",
      "source_assertion_ref": "example_only_a|sha256:22eec990fae9c9f984d600e760e2941c5fe35ff1105f8bcb310871e4ba3ecd00|example-set|configuration",
      "target_attribute_key": "engine_displacement_liters",
      "normalized_concept": "4",
      "mapping_status": "mapped",
      "applicability_ref": "app",
      "normalization": {
        "id": "source_literal",
        "version": "1.0.0"
      },
      "finding_refs": []
    },
    {
      "interpretation_id": "i-fuel_type",
      "source_assertion_ref": "example_only_a|sha256:22eec990fae9c9f984d600e760e2941c5fe35ff1105f8bcb310871e4ba3ecd00|example-set|configuration",
      "target_attribute_key": "fuel_type",
      "normalized_concept": "gasoline",
      "mapping_status": "mapped",
      "applicability_ref": "app",
      "normalization": {
        "id": "source_literal",
        "version": "1.0.0"
      },
      "finding_refs": []
    },
    {
      "interpretation_id": "i-generic_drive_classification",
      "source_assertion_ref": "example_only_a|sha256:22eec990fae9c9f984d600e760e2941c5fe35ff1105f8bcb310871e4ba3ecd00|example-set|configuration",
      "target_attribute_key": "generic_drive_classification",
      "normalized_concept": "4WD",
      "mapping_status": "mapped",
      "applicability_ref": "app",
      "normalization": {
        "id": "source_literal",
        "version": "1.0.0"
      },
      "finding_refs": []
    },
    {
      "interpretation_id": "i-make",
      "source_assertion_ref": "example_only_a|sha256:22eec990fae9c9f984d600e760e2941c5fe35ff1105f8bcb310871e4ba3ecd00|example-set|configuration",
      "target_attribute_key": "make",
      "normalized_concept": "Toyota",
      "mapping_status": "mapped",
      "applicability_ref": "app",
      "normalization": {
        "id": "source_literal",
        "version": "1.0.0"
      },
      "finding_refs": []
    },
    {
      "interpretation_id": "i-market",
      "source_assertion_ref": "example_only_a|sha256:22eec990fae9c9f984d600e760e2941c5fe35ff1105f8bcb310871e4ba3ecd00|example-set|configuration",
      "target_attribute_key": "market",
      "normalized_concept": "US",
      "mapping_status": "mapped",
      "applicability_ref": "app",
      "normalization": {
        "id": "source_literal",
        "version": "1.0.0"
      },
      "finding_refs": []
    },
    {
      "interpretation_id": "i-model",
      "source_assertion_ref": "example_only_a|sha256:22eec990fae9c9f984d600e760e2941c5fe35ff1105f8bcb310871e4ba3ecd00|example-set|configuration",
      "target_attribute_key": "model",
      "normalized_concept": "4Runner",
      "mapping_status": "mapped",
      "applicability_ref": "app",
      "normalization": {
        "id": "source_literal",
        "version": "1.0.0"
      },
      "finding_refs": []
    },
    {
      "interpretation_id": "i-model_year",
      "source_assertion_ref": "example_only_a|sha256:22eec990fae9c9f984d600e760e2941c5fe35ff1105f8bcb310871e4ba3ecd00|example-set|configuration",
      "target_attribute_key": "model_year",
      "normalized_concept": 2007,
      "mapping_status": "mapped",
      "applicability_ref": "app",
      "normalization": {
        "id": "source_literal",
        "version": "1.0.0"
      },
      "finding_refs": []
    },
    {
      "interpretation_id": "i-trim_name",
      "source_assertion_ref": "example_only_a|sha256:22eec990fae9c9f984d600e760e2941c5fe35ff1105f8bcb310871e4ba3ecd00|example-set|configuration",
      "target_attribute_key": "trim_name",
      "normalized_concept": "SR5",
      "mapping_status": "mapped",
      "applicability_ref": "app",
      "normalization": {
        "id": "source_literal",
        "version": "1.0.0"
      },
      "finding_refs": []
    }
  ],
  "canonical_powertrain": {
    "engine_displacement_liters": "4",
    "engine_cylinders": 6,
    "engine_aspiration": "naturally_aspirated",
    "fuel_type": "gasoline",
    "electrification_type": "none"
  },
  "factory_body": null,
  "factory_series": null,
  "candidate_hash": "sha256:6544ca772bf73fa9fa337fac4c57c432ea1e097b14b69da674e7048304bdd845"
}
```

### B. 2024 Wrangler Sport 2-Door — authentic retained heading, new illustrative v3 draft

The qualified heading and model-code assertion are authentic retained identifiers. Source engine details remain raw and canonical_powertrain/drivetrain are null; existing classification/Generation gates remain. No second review is needed just to recognize the explicit two-door taxonomy.

```json
{
  "envelope": {
    "artifact_type": "rigarchive.candidate_configuration.v3",
    "schema_version": "3.0.0",
    "$schema": "urn:rigarchive:contract:candidate_configuration:3.0.0"
  },
  "candidate_reference": "illustration-B",
  "candidate_identity": {
    "manufacturer_name": "Jeep",
    "vehicle_model_name": "Wrangler",
    "model_year": 2024,
    "market": "US",
    "trim_name": "Sport"
  },
  "canonical_scope": {
    "manufacturer_key": "jeep",
    "model_key": "wrangler",
    "generation_key": "jl"
  },
  "canonical_identity_contract": "vehicle-definition-body/2",
  "drivetrain": null,
  "configuration_refs": [
    "rigarchive_MY2024_edmunds_reconciliation|sha256:3dd67950ed426a9e5c575af68d3b4ce4807f879d95c0eed5f945a309aa03c6fb|JL24-01-edmunds-transcription|JL24-01-heading"
  ],
  "applicability": [
    {
      "applicability_id": "app",
      "scope": {
        "manufacturer_key": "jeep",
        "model_key": "wrangler",
        "generation_key": "jl"
      },
      "market": "US",
      "start_year": 2024,
      "end_year": 2024,
      "configuration_refs": [
        "rigarchive_MY2024_edmunds_reconciliation|sha256:3dd67950ed426a9e5c575af68d3b4ce4807f879d95c0eed5f945a309aa03c6fb|JL24-01-edmunds-transcription|JL24-01-heading"
      ],
      "source_assertion_refs": [
        "rigarchive_MY2024_edmunds_reconciliation|sha256:3dd67950ed426a9e5c575af68d3b4ce4807f879d95c0eed5f945a309aa03c6fb|JL24-01-edmunds-transcription|JL24-01-heading"
      ],
      "finding_refs": []
    }
  ],
  "evidence_documents": [
    {
      "assertion_set_id": "JL24-01-edmunds-transcription",
      "assertions": [
        {
          "assertion_id": "JL24-01-correspondence",
          "attribute_key": "research_offering_correspondence",
          "raw_value": {
            "body_style": "2-door",
            "candidate_id": "JL24-01",
            "drivetrain": "4WD",
            "engine_code": "EC1",
            "engine_cylinders": 4,
            "engine_displacement_liters": "2",
            "engine_family": "2.0 I4 turbo ESS",
            "evidence_confidence": "high",
            "evidence_tier": "tier_1_edmunds_and_factory_order_guide",
            "factory_order_guide_page": "2024_JL_2D_OG_20240620:p.2",
            "fwp_usd": "32993",
            "generation": "JL",
            "manufacturer": "Jeep",
            "market": "US",
            "marketed_trim": "Sport",
            "model": "Wrangler",
            "model_code": "JLJL72",
            "model_year": 2024,
            "msrp_usd": "33890",
            "notes": "2024 2-Door Order Guide (04/26/2023 & 06/20/2024, p. 2; QOP 22B DFT 8-spd auto)",
            "outstanding_classification_questions": "fuel_type;electrification_type",
            "proposed_aspiration": "turbocharged",
            "proposed_electrification_type": "none",
            "proposed_fuel_type": "gasoline",
            "provisional_aspiration": "turbocharged",
            "provisional_electrification_type": "",
            "provisional_fuel_type": "",
            "quick_order_package": "22B",
            "reconciliation_classification": "matched_edmunds_and_factory",
            "source_id": "rigarchive_MY2024_edmunds_reconciliation",
            "status": "ACTIVE_CONSUMER",
            "transmission_code": "DFT",
            "transmission_speeds": 8,
            "transmission_type": "automatic"
          },
          "source_context": "Reconciled MY2024 configuration row JL24-01; trim Sport; QOP 22B"
        },
        {
          "assertion_id": "JL24-01-engine-column",
          "attribute_key": "engine_descriptor",
          "raw_value": "2.0L I4 DOHC DI Turbo Engine with Stop/Start (EC1)",
          "source_context": "Engine specification for JL24-01 (EC1): 2.0L I4 Turbo"
        },
        {
          "assertion_id": "JL24-01-heading",
          "attribute_key": "source_document_heading",
          "raw_value": "United States / MY2024 / Jeep Wrangler (2-door) / Sport [JLJL72 / 22B]",
          "source_context": "Edmunds features-specs selector; model year 2024; trim Sport"
        },
        {
          "assertion_id": "JL24-01-model",
          "attribute_key": "source_model_code",
          "raw_value": "JLJL72",
          "source_context": "Jeep Wrangler JL factory model code JLJL72"
        },
        {
          "assertion_id": "JL24-01-trans-column",
          "attribute_key": "transmission_descriptor",
          "raw_value": "8-speed shiftable automatic (850RE)",
          "source_context": "Transmission specification for JL24-01 (DFT): 8-SPD AUTO 850RE TRANS (MAKE)"
        }
      ],
      "extraction_mode": "manually_verified_transcription",
      "extractor_id": "MY2024_lightweight_edmunds_builder",
      "extractor_version": "1.0.0",
      "generation_normalizer": {
        "id": "explicit_generation_identity",
        "version": "1.0.0"
      },
      "publication_revision": "2024-reconciled-r1",
      "raw_artifact_hash": "sha256:3dd67950ed426a9e5c575af68d3b4ce4807f879d95c0eed5f945a309aa03c6fb",
      "raw_artifact_reference": "docs/implementation/handoffs/MY2024_JL/lightweight_ingestion_review_20261113/candidate_inventory.csv",
      "source_applicability": {
        "applicability_basis": "MY2024 US Jeep Wrangler JL candidate JL24-01 (Sport)",
        "applicability_scope": "model_year",
        "market": "US",
        "publisher_jurisdiction": null
      },
      "source_id": "rigarchive_MY2024_edmunds_reconciliation",
      "source_locator": "https://www.edmunds.com/jeep/wrangler/2024/features-specs/"
    }
  ],
  "evidence_raw_hashes": [
    "sha256:3dd67950ed426a9e5c575af68d3b4ce4807f879d95c0eed5f945a309aa03c6fb"
  ],
  "generation_evidence": [
    {
      "assertion_id": "JL24-01-model",
      "assertion_set_id": "JL24-01-edmunds-transcription",
      "document_hash": "sha256:3dd67950ed426a9e5c575af68d3b4ce4807f879d95c0eed5f945a309aa03c6fb",
      "identity_type": "model_code",
      "native_identifier": "JLJL72",
      "normalizer_id": "explicit_generation_identity",
      "normalizer_version": "1.0.0",
      "source_id": "rigarchive_MY2024_edmunds_reconciliation",
      "source_namespace": "source_model_code"
    }
  ],
  "normalized_assertions": [
    {
      "interpretation_id": "i-doors",
      "source_assertion_ref": "rigarchive_MY2024_edmunds_reconciliation|sha256:3dd67950ed426a9e5c575af68d3b4ce4807f879d95c0eed5f945a309aa03c6fb|JL24-01-edmunds-transcription|JL24-01-heading",
      "target_attribute_key": "factory_body.door_configuration",
      "normalized_concept": "two-door",
      "mapping_status": "mapped",
      "applicability_ref": "app",
      "normalization": {
        "id": "wrangler_door_taxonomy",
        "version": "1.0.0"
      },
      "finding_refs": []
    },
    {
      "interpretation_id": "i-make",
      "source_assertion_ref": "rigarchive_MY2024_edmunds_reconciliation|sha256:3dd67950ed426a9e5c575af68d3b4ce4807f879d95c0eed5f945a309aa03c6fb|JL24-01-edmunds-transcription|JL24-01-heading",
      "target_attribute_key": "make",
      "normalized_concept": "Jeep",
      "mapping_status": "mapped",
      "applicability_ref": "app",
      "normalization": {
        "id": "wrangler_selector_heading",
        "version": "1.0.0"
      },
      "finding_refs": []
    },
    {
      "interpretation_id": "i-market",
      "source_assertion_ref": "rigarchive_MY2024_edmunds_reconciliation|sha256:3dd67950ed426a9e5c575af68d3b4ce4807f879d95c0eed5f945a309aa03c6fb|JL24-01-edmunds-transcription|JL24-01-heading",
      "target_attribute_key": "market",
      "normalized_concept": "US",
      "mapping_status": "mapped",
      "applicability_ref": "app",
      "normalization": {
        "id": "wrangler_selector_heading",
        "version": "1.0.0"
      },
      "finding_refs": []
    },
    {
      "interpretation_id": "i-model",
      "source_assertion_ref": "rigarchive_MY2024_edmunds_reconciliation|sha256:3dd67950ed426a9e5c575af68d3b4ce4807f879d95c0eed5f945a309aa03c6fb|JL24-01-edmunds-transcription|JL24-01-heading",
      "target_attribute_key": "model",
      "normalized_concept": "Wrangler",
      "mapping_status": "mapped",
      "applicability_ref": "app",
      "normalization": {
        "id": "wrangler_selector_heading",
        "version": "1.0.0"
      },
      "finding_refs": []
    },
    {
      "interpretation_id": "i-model_year",
      "source_assertion_ref": "rigarchive_MY2024_edmunds_reconciliation|sha256:3dd67950ed426a9e5c575af68d3b4ce4807f879d95c0eed5f945a309aa03c6fb|JL24-01-edmunds-transcription|JL24-01-heading",
      "target_attribute_key": "model_year",
      "normalized_concept": 2024,
      "mapping_status": "mapped",
      "applicability_ref": "app",
      "normalization": {
        "id": "wrangler_selector_heading",
        "version": "1.0.0"
      },
      "finding_refs": []
    },
    {
      "interpretation_id": "i-trim_name",
      "source_assertion_ref": "rigarchive_MY2024_edmunds_reconciliation|sha256:3dd67950ed426a9e5c575af68d3b4ce4807f879d95c0eed5f945a309aa03c6fb|JL24-01-edmunds-transcription|JL24-01-heading",
      "target_attribute_key": "trim_name",
      "normalized_concept": "Sport",
      "mapping_status": "mapped",
      "applicability_ref": "app",
      "normalization": {
        "id": "wrangler_selector_heading",
        "version": "1.0.0"
      },
      "finding_refs": []
    }
  ],
  "canonical_powertrain": null,
  "factory_body": {
    "disposition": "pending",
    "identity": {
      "semantic_digest": "sha256:e12a446cdd441834252f1818ff6c17fb9ecfa81f014fe693e440a82964d77739",
      "preimage": {
        "identity_contract": "factory-body-semantic/2",
        "profile_family": "factory-body",
        "scope": {
          "manufacturer_key": "jeep",
          "model_key": "wrangler",
          "generation_key": "jl"
        },
        "dimensions": {
          "door_configuration": "two-door"
        }
      }
    },
    "support": {
      "applicability_ref": "app",
      "configuration_refs": [
        "rigarchive_MY2024_edmunds_reconciliation|sha256:3dd67950ed426a9e5c575af68d3b4ce4807f879d95c0eed5f945a309aa03c6fb|JL24-01-edmunds-transcription|JL24-01-heading"
      ],
      "interpretation_refs": [
        "i-doors"
      ],
      "equivalence_interpretation_ref": null
    }
  },
  "factory_series": null,
  "candidate_hash": "sha256:64957e82777a10cf672c805988b93db8980698dbaedc0d819a132621e2fd7061"
}
```

### C. 2024 Wrangler Sport 4-Door — authentic Unlimited Sport provenance, new illustrative v3 draft

The embedded source heading retains Unlimited Sport, while candidate_identity.trim_name is Sport. Four-door participates only in the sparse body identity. No real body parent UUID is claimed.

```json
{
  "envelope": {
    "artifact_type": "rigarchive.candidate_configuration.v3",
    "schema_version": "3.0.0",
    "$schema": "urn:rigarchive:contract:candidate_configuration:3.0.0"
  },
  "candidate_reference": "illustration-C",
  "candidate_identity": {
    "manufacturer_name": "Jeep",
    "vehicle_model_name": "Wrangler",
    "model_year": 2024,
    "market": "US",
    "trim_name": "Sport"
  },
  "canonical_scope": {
    "manufacturer_key": "jeep",
    "model_key": "wrangler",
    "generation_key": "jl"
  },
  "canonical_identity_contract": "vehicle-definition-body/2",
  "drivetrain": null,
  "configuration_refs": [
    "rigarchive_MY2024_edmunds_reconciliation|sha256:3dd67950ed426a9e5c575af68d3b4ce4807f879d95c0eed5f945a309aa03c6fb|JL24-11-edmunds-transcription|JL24-11-heading"
  ],
  "applicability": [
    {
      "applicability_id": "app",
      "scope": {
        "manufacturer_key": "jeep",
        "model_key": "wrangler",
        "generation_key": "jl"
      },
      "market": "US",
      "start_year": 2024,
      "end_year": 2024,
      "configuration_refs": [
        "rigarchive_MY2024_edmunds_reconciliation|sha256:3dd67950ed426a9e5c575af68d3b4ce4807f879d95c0eed5f945a309aa03c6fb|JL24-11-edmunds-transcription|JL24-11-heading"
      ],
      "source_assertion_refs": [
        "rigarchive_MY2024_edmunds_reconciliation|sha256:3dd67950ed426a9e5c575af68d3b4ce4807f879d95c0eed5f945a309aa03c6fb|JL24-11-edmunds-transcription|JL24-11-heading"
      ],
      "finding_refs": []
    }
  ],
  "evidence_documents": [
    {
      "assertion_set_id": "JL24-11-edmunds-transcription",
      "assertions": [
        {
          "assertion_id": "JL24-11-correspondence",
          "attribute_key": "research_offering_correspondence",
          "raw_value": {
            "body_style": "4-door",
            "candidate_id": "JL24-11",
            "drivetrain": "4WD",
            "engine_code": "EC1",
            "engine_cylinders": 4,
            "engine_displacement_liters": "2",
            "engine_family": "2.0 I4 turbo ESS",
            "evidence_confidence": "high",
            "evidence_tier": "tier_1_edmunds_and_factory_order_guide",
            "factory_order_guide_page": "2024_JL_4D_OG_20240514:p.2",
            "fwp_usd": "37458",
            "generation": "JL",
            "manufacturer": "Jeep",
            "market": "US",
            "marketed_trim": "Unlimited Sport",
            "model": "Wrangler",
            "model_code": "JLJL74",
            "model_year": 2024,
            "msrp_usd": "38390",
            "notes": "2024 4-Door Order Guide (04/26/2023 & 05/14/2024, p. 2; QOP 22B DFT 8-spd auto)",
            "outstanding_classification_questions": "fuel_type;electrification_type",
            "proposed_aspiration": "turbocharged",
            "proposed_electrification_type": "none",
            "proposed_fuel_type": "gasoline",
            "provisional_aspiration": "turbocharged",
            "provisional_electrification_type": "",
            "provisional_fuel_type": "",
            "quick_order_package": "22B",
            "reconciliation_classification": "matched_edmunds_and_factory",
            "source_id": "rigarchive_MY2024_edmunds_reconciliation",
            "status": "ACTIVE_CONSUMER",
            "transmission_code": "DFT",
            "transmission_speeds": 8,
            "transmission_type": "automatic"
          },
          "source_context": "Reconciled MY2024 configuration row JL24-11; trim Unlimited Sport; QOP 22B"
        },
        {
          "assertion_id": "JL24-11-engine-column",
          "attribute_key": "engine_descriptor",
          "raw_value": "2.0L I4 DOHC DI Turbo Engine with Stop/Start (EC1)",
          "source_context": "Engine specification for JL24-11 (EC1): 2.0L I4 Turbo"
        },
        {
          "assertion_id": "JL24-11-heading",
          "attribute_key": "source_document_heading",
          "raw_value": "United States / MY2024 / Jeep Wrangler (4-door) / Unlimited Sport [JLJL74 / 22B]",
          "source_context": "Edmunds features-specs selector; model year 2024; trim Unlimited Sport"
        },
        {
          "assertion_id": "JL24-11-model",
          "attribute_key": "source_model_code",
          "raw_value": "JLJL74",
          "source_context": "Jeep Wrangler JL factory model code JLJL74"
        },
        {
          "assertion_id": "JL24-11-trans-column",
          "attribute_key": "transmission_descriptor",
          "raw_value": "8-speed shiftable automatic (850RE)",
          "source_context": "Transmission specification for JL24-11 (DFT): 8-SPD AUTO 850RE TRANS (MAKE)"
        }
      ],
      "extraction_mode": "manually_verified_transcription",
      "extractor_id": "MY2024_lightweight_edmunds_builder",
      "extractor_version": "1.0.0",
      "generation_normalizer": {
        "id": "explicit_generation_identity",
        "version": "1.0.0"
      },
      "publication_revision": "2024-reconciled-r1",
      "raw_artifact_hash": "sha256:3dd67950ed426a9e5c575af68d3b4ce4807f879d95c0eed5f945a309aa03c6fb",
      "raw_artifact_reference": "docs/implementation/handoffs/MY2024_JL/lightweight_ingestion_review_20261113/candidate_inventory.csv",
      "source_applicability": {
        "applicability_basis": "MY2024 US Jeep Wrangler JL candidate JL24-11 (Unlimited Sport)",
        "applicability_scope": "model_year",
        "market": "US",
        "publisher_jurisdiction": null
      },
      "source_id": "rigarchive_MY2024_edmunds_reconciliation",
      "source_locator": "https://www.edmunds.com/jeep/wrangler/2024/features-specs/"
    }
  ],
  "evidence_raw_hashes": [
    "sha256:3dd67950ed426a9e5c575af68d3b4ce4807f879d95c0eed5f945a309aa03c6fb"
  ],
  "generation_evidence": [
    {
      "assertion_id": "JL24-11-model",
      "assertion_set_id": "JL24-11-edmunds-transcription",
      "document_hash": "sha256:3dd67950ed426a9e5c575af68d3b4ce4807f879d95c0eed5f945a309aa03c6fb",
      "identity_type": "model_code",
      "native_identifier": "JLJL74",
      "normalizer_id": "explicit_generation_identity",
      "normalizer_version": "1.0.0",
      "source_id": "rigarchive_MY2024_edmunds_reconciliation",
      "source_namespace": "source_model_code"
    }
  ],
  "normalized_assertions": [
    {
      "interpretation_id": "i-doors",
      "source_assertion_ref": "rigarchive_MY2024_edmunds_reconciliation|sha256:3dd67950ed426a9e5c575af68d3b4ce4807f879d95c0eed5f945a309aa03c6fb|JL24-11-edmunds-transcription|JL24-11-heading",
      "target_attribute_key": "factory_body.door_configuration",
      "normalized_concept": "four-door",
      "mapping_status": "mapped",
      "applicability_ref": "app",
      "normalization": {
        "id": "wrangler_door_taxonomy",
        "version": "1.0.0"
      },
      "finding_refs": []
    },
    {
      "interpretation_id": "i-make",
      "source_assertion_ref": "rigarchive_MY2024_edmunds_reconciliation|sha256:3dd67950ed426a9e5c575af68d3b4ce4807f879d95c0eed5f945a309aa03c6fb|JL24-11-edmunds-transcription|JL24-11-heading",
      "target_attribute_key": "make",
      "normalized_concept": "Jeep",
      "mapping_status": "mapped",
      "applicability_ref": "app",
      "normalization": {
        "id": "wrangler_selector_heading",
        "version": "1.0.0"
      },
      "finding_refs": []
    },
    {
      "interpretation_id": "i-market",
      "source_assertion_ref": "rigarchive_MY2024_edmunds_reconciliation|sha256:3dd67950ed426a9e5c575af68d3b4ce4807f879d95c0eed5f945a309aa03c6fb|JL24-11-edmunds-transcription|JL24-11-heading",
      "target_attribute_key": "market",
      "normalized_concept": "US",
      "mapping_status": "mapped",
      "applicability_ref": "app",
      "normalization": {
        "id": "wrangler_selector_heading",
        "version": "1.0.0"
      },
      "finding_refs": []
    },
    {
      "interpretation_id": "i-model",
      "source_assertion_ref": "rigarchive_MY2024_edmunds_reconciliation|sha256:3dd67950ed426a9e5c575af68d3b4ce4807f879d95c0eed5f945a309aa03c6fb|JL24-11-edmunds-transcription|JL24-11-heading",
      "target_attribute_key": "model",
      "normalized_concept": "Wrangler",
      "mapping_status": "mapped",
      "applicability_ref": "app",
      "normalization": {
        "id": "wrangler_selector_heading",
        "version": "1.0.0"
      },
      "finding_refs": []
    },
    {
      "interpretation_id": "i-model_year",
      "source_assertion_ref": "rigarchive_MY2024_edmunds_reconciliation|sha256:3dd67950ed426a9e5c575af68d3b4ce4807f879d95c0eed5f945a309aa03c6fb|JL24-11-edmunds-transcription|JL24-11-heading",
      "target_attribute_key": "model_year",
      "normalized_concept": 2024,
      "mapping_status": "mapped",
      "applicability_ref": "app",
      "normalization": {
        "id": "wrangler_selector_heading",
        "version": "1.0.0"
      },
      "finding_refs": []
    },
    {
      "interpretation_id": "i-trim_name",
      "source_assertion_ref": "rigarchive_MY2024_edmunds_reconciliation|sha256:3dd67950ed426a9e5c575af68d3b4ce4807f879d95c0eed5f945a309aa03c6fb|JL24-11-edmunds-transcription|JL24-11-heading",
      "target_attribute_key": "trim_name",
      "normalized_concept": "Sport",
      "mapping_status": "mapped",
      "applicability_ref": "app",
      "normalization": {
        "id": "wrangler_selector_heading",
        "version": "1.0.0"
      },
      "finding_refs": []
    }
  ],
  "canonical_powertrain": null,
  "factory_body": {
    "disposition": "pending",
    "identity": {
      "semantic_digest": "sha256:98f93c52c8c997ddc9e5c0af0df48c7e64a6a010d5d15b5cbc634e096728989d",
      "preimage": {
        "identity_contract": "factory-body-semantic/2",
        "profile_family": "factory-body",
        "scope": {
          "manufacturer_key": "jeep",
          "model_key": "wrangler",
          "generation_key": "jl"
        },
        "dimensions": {
          "door_configuration": "four-door"
        }
      }
    },
    "support": {
      "applicability_ref": "app",
      "configuration_refs": [
        "rigarchive_MY2024_edmunds_reconciliation|sha256:3dd67950ed426a9e5c575af68d3b4ce4807f879d95c0eed5f945a309aa03c6fb|JL24-11-edmunds-transcription|JL24-11-heading"
      ],
      "interpretation_refs": [
        "i-doors"
      ],
      "equivalence_interpretation_ref": null
    }
  },
  "factory_series": null,
  "candidate_hash": "sha256:16fa47436f17f64fa0664fcbbad38623690ac243166d23c007da3bf9c14472bb"
}
```

### D. Existing body parent — synthetic UUID/revision, exact supported roof basis

All parent/revision UUIDs and the binding hash in D are explicitly fictional. A future live resolver must fetch the real immutable revision and verify its hash/coverage; these values cannot resolve to project data.

```json
{
  "envelope": {
    "artifact_type": "rigarchive.candidate_configuration.v3",
    "schema_version": "3.0.0",
    "$schema": "urn:rigarchive:contract:candidate_configuration:3.0.0"
  },
  "candidate_reference": "illustration-D",
  "candidate_identity": {
    "manufacturer_name": "Ford",
    "vehicle_model_name": "Transit",
    "model_year": 2024,
    "market": "US",
    "trim_name": "Cargo"
  },
  "canonical_scope": {
    "manufacturer_key": "ford",
    "model_key": "transit",
    "generation_key": "example-generation"
  },
  "canonical_identity_contract": "vehicle-definition-body/2",
  "drivetrain": null,
  "configuration_refs": [
    "example_only_d|sha256:4cd3a253487f03365331d44a9904deecdfa7ced31d78c7a4cc6f9cbd0a901c22|example-set|configuration"
  ],
  "applicability": [
    {
      "applicability_id": "app",
      "scope": {
        "manufacturer_key": "ford",
        "model_key": "transit",
        "generation_key": "example-generation"
      },
      "market": "US",
      "start_year": 2024,
      "end_year": 2024,
      "configuration_refs": [
        "example_only_d|sha256:4cd3a253487f03365331d44a9904deecdfa7ced31d78c7a4cc6f9cbd0a901c22|example-set|configuration"
      ],
      "source_assertion_refs": [
        "example_only_d|sha256:4cd3a253487f03365331d44a9904deecdfa7ced31d78c7a4cc6f9cbd0a901c22|example-set|configuration"
      ],
      "finding_refs": []
    }
  ],
  "evidence_documents": [
    {
      "source_id": "example_only_d",
      "raw_artifact_hash": "sha256:4cd3a253487f03365331d44a9904deecdfa7ced31d78c7a4cc6f9cbd0a901c22",
      "raw_artifact_reference": "docs/examples/not-retained/D.json",
      "extractor_id": "example-only",
      "extractor_version": "1.0.0",
      "extraction_mode": "illustration",
      "assertion_set_id": "example-set",
      "assertions": [
        {
          "assertion_id": "configuration",
          "attribute_key": "configuration",
          "raw_value": {
            "make": "Ford",
            "model": "Transit",
            "model_year": 2024,
            "market": "US",
            "trim_name": "Cargo",
            "factory_body.roof_height_designation": "high"
          },
          "source_context": "Hypothetical positive configuration; not verified manufacturer evidence"
        }
      ]
    }
  ],
  "evidence_raw_hashes": [
    "sha256:4cd3a253487f03365331d44a9904deecdfa7ced31d78c7a4cc6f9cbd0a901c22"
  ],
  "generation_evidence": [],
  "normalized_assertions": [
    {
      "interpretation_id": "i-factory_body.roof_height_designation",
      "source_assertion_ref": "example_only_d|sha256:4cd3a253487f03365331d44a9904deecdfa7ced31d78c7a4cc6f9cbd0a901c22|example-set|configuration",
      "target_attribute_key": "factory_body.roof_height_designation",
      "normalized_concept": "high",
      "mapping_status": "mapped",
      "applicability_ref": "app",
      "normalization": {
        "id": "source_literal",
        "version": "1.0.0"
      },
      "finding_refs": []
    },
    {
      "interpretation_id": "i-make",
      "source_assertion_ref": "example_only_d|sha256:4cd3a253487f03365331d44a9904deecdfa7ced31d78c7a4cc6f9cbd0a901c22|example-set|configuration",
      "target_attribute_key": "make",
      "normalized_concept": "Ford",
      "mapping_status": "mapped",
      "applicability_ref": "app",
      "normalization": {
        "id": "source_literal",
        "version": "1.0.0"
      },
      "finding_refs": []
    },
    {
      "interpretation_id": "i-market",
      "source_assertion_ref": "example_only_d|sha256:4cd3a253487f03365331d44a9904deecdfa7ced31d78c7a4cc6f9cbd0a901c22|example-set|configuration",
      "target_attribute_key": "market",
      "normalized_concept": "US",
      "mapping_status": "mapped",
      "applicability_ref": "app",
      "normalization": {
        "id": "source_literal",
        "version": "1.0.0"
      },
      "finding_refs": []
    },
    {
      "interpretation_id": "i-model",
      "source_assertion_ref": "example_only_d|sha256:4cd3a253487f03365331d44a9904deecdfa7ced31d78c7a4cc6f9cbd0a901c22|example-set|configuration",
      "target_attribute_key": "model",
      "normalized_concept": "Transit",
      "mapping_status": "mapped",
      "applicability_ref": "app",
      "normalization": {
        "id": "source_literal",
        "version": "1.0.0"
      },
      "finding_refs": []
    },
    {
      "interpretation_id": "i-model_year",
      "source_assertion_ref": "example_only_d|sha256:4cd3a253487f03365331d44a9904deecdfa7ced31d78c7a4cc6f9cbd0a901c22|example-set|configuration",
      "target_attribute_key": "model_year",
      "normalized_concept": 2024,
      "mapping_status": "mapped",
      "applicability_ref": "app",
      "normalization": {
        "id": "source_literal",
        "version": "1.0.0"
      },
      "finding_refs": []
    },
    {
      "interpretation_id": "i-trim_name",
      "source_assertion_ref": "example_only_d|sha256:4cd3a253487f03365331d44a9904deecdfa7ced31d78c7a4cc6f9cbd0a901c22|example-set|configuration",
      "target_attribute_key": "trim_name",
      "normalized_concept": "Cargo",
      "mapping_status": "mapped",
      "applicability_ref": "app",
      "normalization": {
        "id": "source_literal",
        "version": "1.0.0"
      },
      "finding_refs": []
    }
  ],
  "canonical_powertrain": null,
  "factory_body": {
    "disposition": "existing",
    "identity": {
      "semantic_digest": "sha256:1b1b51e2c0ee22bf2679b95a1eccf151e3e8bda65d55a2593db65170bedcad28",
      "preimage": {
        "identity_contract": "factory-body-semantic/2",
        "profile_family": "factory-body",
        "scope": {
          "manufacturer_key": "ford",
          "model_key": "transit",
          "generation_key": "example-generation"
        },
        "dimensions": {
          "roof_height_designation": "high"
        }
      }
    },
    "support": {
      "applicability_ref": "app",
      "configuration_refs": [
        "example_only_d|sha256:4cd3a253487f03365331d44a9904deecdfa7ced31d78c7a4cc6f9cbd0a901c22|example-set|configuration"
      ],
      "interpretation_refs": [
        "i-factory_body.roof_height_designation"
      ],
      "equivalence_interpretation_ref": null
    },
    "parent_uuid": "11111111-1111-4111-8111-111111111111",
    "binding_revision": {
      "revision_uuid": "22222222-2222-4222-8222-222222222222",
      "content_hash": "sha256:5894e334463ae1abfdffa48c8a84b12fc6e9ca13654371422d58b78a60d61455",
      "applicability_ref": "app"
    }
  },
  "factory_series": null,
  "candidate_hash": "sha256:3023842810116dcad47684397a2287f060cc7c07c04d42755e677409e1a4bbc2"
}
```

### E. Pending body parent — supported sparse basis, no UUID

Pending disposition is unbound, not proven absent. Its parent support and identity are hash-bound; later read-only planning must check existing bodies before proposing creation.

```json
{
  "envelope": {
    "artifact_type": "rigarchive.candidate_configuration.v3",
    "schema_version": "3.0.0",
    "$schema": "urn:rigarchive:contract:candidate_configuration:3.0.0"
  },
  "candidate_reference": "illustration-E",
  "candidate_identity": {
    "manufacturer_name": "Ford",
    "vehicle_model_name": "Transit",
    "model_year": 2024,
    "market": "US",
    "trim_name": "Cargo"
  },
  "canonical_scope": {
    "manufacturer_key": "ford",
    "model_key": "transit",
    "generation_key": "example-generation"
  },
  "canonical_identity_contract": "vehicle-definition-body/2",
  "drivetrain": null,
  "configuration_refs": [
    "example_only_e|sha256:50a72149d9746fd753bf4b88c929ef438f6ae1f8f1b23493338f35fa567f6763|example-set|configuration"
  ],
  "applicability": [
    {
      "applicability_id": "app",
      "scope": {
        "manufacturer_key": "ford",
        "model_key": "transit",
        "generation_key": "example-generation"
      },
      "market": "US",
      "start_year": 2024,
      "end_year": 2024,
      "configuration_refs": [
        "example_only_e|sha256:50a72149d9746fd753bf4b88c929ef438f6ae1f8f1b23493338f35fa567f6763|example-set|configuration"
      ],
      "source_assertion_refs": [
        "example_only_e|sha256:50a72149d9746fd753bf4b88c929ef438f6ae1f8f1b23493338f35fa567f6763|example-set|configuration"
      ],
      "finding_refs": []
    }
  ],
  "evidence_documents": [
    {
      "source_id": "example_only_e",
      "raw_artifact_hash": "sha256:50a72149d9746fd753bf4b88c929ef438f6ae1f8f1b23493338f35fa567f6763",
      "raw_artifact_reference": "docs/examples/not-retained/E.json",
      "extractor_id": "example-only",
      "extractor_version": "1.0.0",
      "extraction_mode": "illustration",
      "assertion_set_id": "example-set",
      "assertions": [
        {
          "assertion_id": "configuration",
          "attribute_key": "configuration",
          "raw_value": {
            "make": "Ford",
            "model": "Transit",
            "model_year": 2024,
            "market": "US",
            "trim_name": "Cargo",
            "factory_body.door_configuration": "two-door"
          },
          "source_context": "Hypothetical positive configuration; not verified manufacturer evidence"
        }
      ]
    }
  ],
  "evidence_raw_hashes": [
    "sha256:50a72149d9746fd753bf4b88c929ef438f6ae1f8f1b23493338f35fa567f6763"
  ],
  "generation_evidence": [],
  "normalized_assertions": [
    {
      "interpretation_id": "i-factory_body.door_configuration",
      "source_assertion_ref": "example_only_e|sha256:50a72149d9746fd753bf4b88c929ef438f6ae1f8f1b23493338f35fa567f6763|example-set|configuration",
      "target_attribute_key": "factory_body.door_configuration",
      "normalized_concept": "two-door",
      "mapping_status": "mapped",
      "applicability_ref": "app",
      "normalization": {
        "id": "source_literal",
        "version": "1.0.0"
      },
      "finding_refs": []
    },
    {
      "interpretation_id": "i-make",
      "source_assertion_ref": "example_only_e|sha256:50a72149d9746fd753bf4b88c929ef438f6ae1f8f1b23493338f35fa567f6763|example-set|configuration",
      "target_attribute_key": "make",
      "normalized_concept": "Ford",
      "mapping_status": "mapped",
      "applicability_ref": "app",
      "normalization": {
        "id": "source_literal",
        "version": "1.0.0"
      },
      "finding_refs": []
    },
    {
      "interpretation_id": "i-market",
      "source_assertion_ref": "example_only_e|sha256:50a72149d9746fd753bf4b88c929ef438f6ae1f8f1b23493338f35fa567f6763|example-set|configuration",
      "target_attribute_key": "market",
      "normalized_concept": "US",
      "mapping_status": "mapped",
      "applicability_ref": "app",
      "normalization": {
        "id": "source_literal",
        "version": "1.0.0"
      },
      "finding_refs": []
    },
    {
      "interpretation_id": "i-model",
      "source_assertion_ref": "example_only_e|sha256:50a72149d9746fd753bf4b88c929ef438f6ae1f8f1b23493338f35fa567f6763|example-set|configuration",
      "target_attribute_key": "model",
      "normalized_concept": "Transit",
      "mapping_status": "mapped",
      "applicability_ref": "app",
      "normalization": {
        "id": "source_literal",
        "version": "1.0.0"
      },
      "finding_refs": []
    },
    {
      "interpretation_id": "i-model_year",
      "source_assertion_ref": "example_only_e|sha256:50a72149d9746fd753bf4b88c929ef438f6ae1f8f1b23493338f35fa567f6763|example-set|configuration",
      "target_attribute_key": "model_year",
      "normalized_concept": 2024,
      "mapping_status": "mapped",
      "applicability_ref": "app",
      "normalization": {
        "id": "source_literal",
        "version": "1.0.0"
      },
      "finding_refs": []
    },
    {
      "interpretation_id": "i-trim_name",
      "source_assertion_ref": "example_only_e|sha256:50a72149d9746fd753bf4b88c929ef438f6ae1f8f1b23493338f35fa567f6763|example-set|configuration",
      "target_attribute_key": "trim_name",
      "normalized_concept": "Cargo",
      "mapping_status": "mapped",
      "applicability_ref": "app",
      "normalization": {
        "id": "source_literal",
        "version": "1.0.0"
      },
      "finding_refs": []
    }
  ],
  "canonical_powertrain": null,
  "factory_body": {
    "disposition": "pending",
    "identity": {
      "semantic_digest": "sha256:182d22e6a33de7901382f57117c1b835da8f4c25244dafddccc7688391badbe8",
      "preimage": {
        "identity_contract": "factory-body-semantic/2",
        "profile_family": "factory-body",
        "scope": {
          "manufacturer_key": "ford",
          "model_key": "transit",
          "generation_key": "example-generation"
        },
        "dimensions": {
          "door_configuration": "two-door"
        }
      }
    },
    "support": {
      "applicability_ref": "app",
      "configuration_refs": [
        "example_only_e|sha256:50a72149d9746fd753bf4b88c929ef438f6ae1f8f1b23493338f35fa567f6763|example-set|configuration"
      ],
      "interpretation_refs": [
        "i-factory_body.door_configuration"
      ],
      "equivalence_interpretation_ref": null
    }
  },
  "factory_series": null,
  "candidate_hash": "sha256:2570d7f349b1cc9a63444ac6d582841b5ad7e6c26ce9718d7058bec42dabe877"
}
```

### F. Independent FactorySeries — hypothetical series 250 and sparse van body

Series 250 and its existing-parent UUID/revision are hypothetical, not actual Ford records or asserted availability. This shows an existing series independently of a pending body. One composite source configuration supports wheelbase, length, roof and independent series role; doors/body code remain absent with no missingness findings.

```json
{
  "envelope": {
    "artifact_type": "rigarchive.candidate_configuration.v3",
    "schema_version": "3.0.0",
    "$schema": "urn:rigarchive:contract:candidate_configuration:3.0.0"
  },
  "candidate_reference": "illustration-F",
  "candidate_identity": {
    "manufacturer_name": "Ford",
    "vehicle_model_name": "Transit",
    "model_year": 2024,
    "market": "US",
    "trim_name": "Cargo"
  },
  "canonical_scope": {
    "manufacturer_key": "ford",
    "model_key": "transit",
    "generation_key": "example-generation"
  },
  "canonical_identity_contract": "vehicle-definition-body/2",
  "drivetrain": null,
  "configuration_refs": [
    "example_only_f|sha256:7f64c168837fbf3dbd9f60fa9d14dd131610101a105fec60c382928491f871c0|example-set|configuration"
  ],
  "applicability": [
    {
      "applicability_id": "app",
      "scope": {
        "manufacturer_key": "ford",
        "model_key": "transit",
        "generation_key": "example-generation"
      },
      "market": "US",
      "start_year": 2024,
      "end_year": 2024,
      "configuration_refs": [
        "example_only_f|sha256:7f64c168837fbf3dbd9f60fa9d14dd131610101a105fec60c382928491f871c0|example-set|configuration"
      ],
      "source_assertion_refs": [
        "example_only_f|sha256:7f64c168837fbf3dbd9f60fa9d14dd131610101a105fec60c382928491f871c0|example-set|configuration"
      ],
      "finding_refs": []
    }
  ],
  "evidence_documents": [
    {
      "source_id": "example_only_f",
      "raw_artifact_hash": "sha256:7f64c168837fbf3dbd9f60fa9d14dd131610101a105fec60c382928491f871c0",
      "raw_artifact_reference": "docs/examples/not-retained/F.json",
      "extractor_id": "example-only",
      "extractor_version": "1.0.0",
      "extraction_mode": "illustration",
      "assertion_set_id": "example-set",
      "assertions": [
        {
          "assertion_id": "configuration",
          "attribute_key": "configuration",
          "raw_value": {
            "make": "Ford",
            "model": "Transit",
            "model_year": 2024,
            "market": "US",
            "trim_name": "Cargo",
            "factory_body.wheelbase_designation": "long",
            "factory_body.body_length_designation": "extended",
            "factory_body.roof_height_designation": "high",
            "factory_series.namespace": "example-series",
            "factory_series.designation": "250",
            "factory_series.identity_role": "independent_series"
          },
          "source_context": "Hypothetical positive configuration; not verified manufacturer evidence"
        }
      ]
    }
  ],
  "evidence_raw_hashes": [
    "sha256:7f64c168837fbf3dbd9f60fa9d14dd131610101a105fec60c382928491f871c0"
  ],
  "generation_evidence": [],
  "normalized_assertions": [
    {
      "interpretation_id": "i-factory_body.body_length_designation",
      "source_assertion_ref": "example_only_f|sha256:7f64c168837fbf3dbd9f60fa9d14dd131610101a105fec60c382928491f871c0|example-set|configuration",
      "target_attribute_key": "factory_body.body_length_designation",
      "normalized_concept": "extended",
      "mapping_status": "mapped",
      "applicability_ref": "app",
      "normalization": {
        "id": "source_literal",
        "version": "1.0.0"
      },
      "finding_refs": []
    },
    {
      "interpretation_id": "i-factory_body.roof_height_designation",
      "source_assertion_ref": "example_only_f|sha256:7f64c168837fbf3dbd9f60fa9d14dd131610101a105fec60c382928491f871c0|example-set|configuration",
      "target_attribute_key": "factory_body.roof_height_designation",
      "normalized_concept": "high",
      "mapping_status": "mapped",
      "applicability_ref": "app",
      "normalization": {
        "id": "source_literal",
        "version": "1.0.0"
      },
      "finding_refs": []
    },
    {
      "interpretation_id": "i-factory_body.wheelbase_designation",
      "source_assertion_ref": "example_only_f|sha256:7f64c168837fbf3dbd9f60fa9d14dd131610101a105fec60c382928491f871c0|example-set|configuration",
      "target_attribute_key": "factory_body.wheelbase_designation",
      "normalized_concept": "long",
      "mapping_status": "mapped",
      "applicability_ref": "app",
      "normalization": {
        "id": "source_literal",
        "version": "1.0.0"
      },
      "finding_refs": []
    },
    {
      "interpretation_id": "i-factory_series.designation",
      "source_assertion_ref": "example_only_f|sha256:7f64c168837fbf3dbd9f60fa9d14dd131610101a105fec60c382928491f871c0|example-set|configuration",
      "target_attribute_key": "factory_series.designation",
      "normalized_concept": "250",
      "mapping_status": "mapped",
      "applicability_ref": "app",
      "normalization": {
        "id": "source_literal",
        "version": "1.0.0"
      },
      "finding_refs": []
    },
    {
      "interpretation_id": "i-factory_series.identity_role",
      "source_assertion_ref": "example_only_f|sha256:7f64c168837fbf3dbd9f60fa9d14dd131610101a105fec60c382928491f871c0|example-set|configuration",
      "target_attribute_key": "factory_series.identity_role",
      "normalized_concept": "independent_series",
      "mapping_status": "mapped",
      "applicability_ref": "app",
      "normalization": {
        "id": "source_literal",
        "version": "1.0.0"
      },
      "finding_refs": []
    },
    {
      "interpretation_id": "i-factory_series.namespace",
      "source_assertion_ref": "example_only_f|sha256:7f64c168837fbf3dbd9f60fa9d14dd131610101a105fec60c382928491f871c0|example-set|configuration",
      "target_attribute_key": "factory_series.namespace",
      "normalized_concept": "example-series",
      "mapping_status": "mapped",
      "applicability_ref": "app",
      "normalization": {
        "id": "source_literal",
        "version": "1.0.0"
      },
      "finding_refs": []
    },
    {
      "interpretation_id": "i-make",
      "source_assertion_ref": "example_only_f|sha256:7f64c168837fbf3dbd9f60fa9d14dd131610101a105fec60c382928491f871c0|example-set|configuration",
      "target_attribute_key": "make",
      "normalized_concept": "Ford",
      "mapping_status": "mapped",
      "applicability_ref": "app",
      "normalization": {
        "id": "source_literal",
        "version": "1.0.0"
      },
      "finding_refs": []
    },
    {
      "interpretation_id": "i-market",
      "source_assertion_ref": "example_only_f|sha256:7f64c168837fbf3dbd9f60fa9d14dd131610101a105fec60c382928491f871c0|example-set|configuration",
      "target_attribute_key": "market",
      "normalized_concept": "US",
      "mapping_status": "mapped",
      "applicability_ref": "app",
      "normalization": {
        "id": "source_literal",
        "version": "1.0.0"
      },
      "finding_refs": []
    },
    {
      "interpretation_id": "i-model",
      "source_assertion_ref": "example_only_f|sha256:7f64c168837fbf3dbd9f60fa9d14dd131610101a105fec60c382928491f871c0|example-set|configuration",
      "target_attribute_key": "model",
      "normalized_concept": "Transit",
      "mapping_status": "mapped",
      "applicability_ref": "app",
      "normalization": {
        "id": "source_literal",
        "version": "1.0.0"
      },
      "finding_refs": []
    },
    {
      "interpretation_id": "i-model_year",
      "source_assertion_ref": "example_only_f|sha256:7f64c168837fbf3dbd9f60fa9d14dd131610101a105fec60c382928491f871c0|example-set|configuration",
      "target_attribute_key": "model_year",
      "normalized_concept": 2024,
      "mapping_status": "mapped",
      "applicability_ref": "app",
      "normalization": {
        "id": "source_literal",
        "version": "1.0.0"
      },
      "finding_refs": []
    },
    {
      "interpretation_id": "i-trim_name",
      "source_assertion_ref": "example_only_f|sha256:7f64c168837fbf3dbd9f60fa9d14dd131610101a105fec60c382928491f871c0|example-set|configuration",
      "target_attribute_key": "trim_name",
      "normalized_concept": "Cargo",
      "mapping_status": "mapped",
      "applicability_ref": "app",
      "normalization": {
        "id": "source_literal",
        "version": "1.0.0"
      },
      "finding_refs": []
    }
  ],
  "canonical_powertrain": null,
  "factory_body": {
    "disposition": "pending",
    "identity": {
      "semantic_digest": "sha256:92819ae77d91c6b71feb16c9ea385d44f8ed5667b2960bf8bcf247c03882d760",
      "preimage": {
        "identity_contract": "factory-body-semantic/2",
        "profile_family": "factory-body",
        "scope": {
          "manufacturer_key": "ford",
          "model_key": "transit",
          "generation_key": "example-generation"
        },
        "dimensions": {
          "wheelbase_designation": "long",
          "body_length_designation": "extended",
          "roof_height_designation": "high"
        }
      }
    },
    "support": {
      "applicability_ref": "app",
      "configuration_refs": [
        "example_only_f|sha256:7f64c168837fbf3dbd9f60fa9d14dd131610101a105fec60c382928491f871c0|example-set|configuration"
      ],
      "interpretation_refs": [
        "i-factory_body.body_length_designation",
        "i-factory_body.roof_height_designation",
        "i-factory_body.wheelbase_designation"
      ],
      "equivalence_interpretation_ref": null
    }
  },
  "factory_series": {
    "disposition": "existing",
    "identity": {
      "semantic_digest": "sha256:d75eefe3a7a18667cd879295788f52b1993ee85db9638f4d5ba559fdfea7f984",
      "preimage": {
        "identity_contract": "factory-series-semantic/1",
        "scope": {
          "manufacturer_key": "ford",
          "model_key": "transit"
        },
        "namespace": "example-series",
        "designation": "250"
      }
    },
    "support": {
      "applicability_ref": "app",
      "configuration_refs": [
        "example_only_f|sha256:7f64c168837fbf3dbd9f60fa9d14dd131610101a105fec60c382928491f871c0|example-set|configuration"
      ],
      "interpretation_refs": [
        "i-factory_series.designation",
        "i-factory_series.identity_role",
        "i-factory_series.namespace"
      ],
      "equivalence_interpretation_ref": null
    },
    "parent_uuid": "33333333-3333-4333-8333-333333333333",
    "binding_revision": {
      "revision_uuid": "44444444-4444-4444-8444-444444444444",
      "content_hash": "sha256:044f180ee0dccfd22229b043fc9b22c22ce541d20def8cf6df8f9a861565cde0",
      "applicability_ref": "app"
    }
  },
  "candidate_hash": "sha256:310737915dc3ea120c080ae4a15676403867fc15cd0875a3d14f75fa2cc81606"
}
```

### G. Partial evidence — roof reported, other six dimensions absent

With no demonstrated conflicting alternative, omitted wheelbase/length/doors/side-door/code/form values cause no body review. It is not a claim that no other body ever existed.

```json
{
  "envelope": {
    "artifact_type": "rigarchive.candidate_configuration.v3",
    "schema_version": "3.0.0",
    "$schema": "urn:rigarchive:contract:candidate_configuration:3.0.0"
  },
  "candidate_reference": "illustration-G",
  "candidate_identity": {
    "manufacturer_name": "Ford",
    "vehicle_model_name": "Transit",
    "model_year": 2024,
    "market": "US",
    "trim_name": "Cargo"
  },
  "canonical_scope": {
    "manufacturer_key": "ford",
    "model_key": "transit",
    "generation_key": "example-generation"
  },
  "canonical_identity_contract": "vehicle-definition-body/2",
  "drivetrain": null,
  "configuration_refs": [
    "example_only_g|sha256:4cd3a253487f03365331d44a9904deecdfa7ced31d78c7a4cc6f9cbd0a901c22|example-set|configuration"
  ],
  "applicability": [
    {
      "applicability_id": "app",
      "scope": {
        "manufacturer_key": "ford",
        "model_key": "transit",
        "generation_key": "example-generation"
      },
      "market": "US",
      "start_year": 2024,
      "end_year": 2024,
      "configuration_refs": [
        "example_only_g|sha256:4cd3a253487f03365331d44a9904deecdfa7ced31d78c7a4cc6f9cbd0a901c22|example-set|configuration"
      ],
      "source_assertion_refs": [
        "example_only_g|sha256:4cd3a253487f03365331d44a9904deecdfa7ced31d78c7a4cc6f9cbd0a901c22|example-set|configuration"
      ],
      "finding_refs": []
    }
  ],
  "evidence_documents": [
    {
      "source_id": "example_only_g",
      "raw_artifact_hash": "sha256:4cd3a253487f03365331d44a9904deecdfa7ced31d78c7a4cc6f9cbd0a901c22",
      "raw_artifact_reference": "docs/examples/not-retained/G.json",
      "extractor_id": "example-only",
      "extractor_version": "1.0.0",
      "extraction_mode": "illustration",
      "assertion_set_id": "example-set",
      "assertions": [
        {
          "assertion_id": "configuration",
          "attribute_key": "configuration",
          "raw_value": {
            "make": "Ford",
            "model": "Transit",
            "model_year": 2024,
            "market": "US",
            "trim_name": "Cargo",
            "factory_body.roof_height_designation": "high"
          },
          "source_context": "Hypothetical positive configuration; not verified manufacturer evidence"
        }
      ]
    }
  ],
  "evidence_raw_hashes": [
    "sha256:4cd3a253487f03365331d44a9904deecdfa7ced31d78c7a4cc6f9cbd0a901c22"
  ],
  "generation_evidence": [],
  "normalized_assertions": [
    {
      "interpretation_id": "i-factory_body.roof_height_designation",
      "source_assertion_ref": "example_only_g|sha256:4cd3a253487f03365331d44a9904deecdfa7ced31d78c7a4cc6f9cbd0a901c22|example-set|configuration",
      "target_attribute_key": "factory_body.roof_height_designation",
      "normalized_concept": "high",
      "mapping_status": "mapped",
      "applicability_ref": "app",
      "normalization": {
        "id": "source_literal",
        "version": "1.0.0"
      },
      "finding_refs": []
    },
    {
      "interpretation_id": "i-make",
      "source_assertion_ref": "example_only_g|sha256:4cd3a253487f03365331d44a9904deecdfa7ced31d78c7a4cc6f9cbd0a901c22|example-set|configuration",
      "target_attribute_key": "make",
      "normalized_concept": "Ford",
      "mapping_status": "mapped",
      "applicability_ref": "app",
      "normalization": {
        "id": "source_literal",
        "version": "1.0.0"
      },
      "finding_refs": []
    },
    {
      "interpretation_id": "i-market",
      "source_assertion_ref": "example_only_g|sha256:4cd3a253487f03365331d44a9904deecdfa7ced31d78c7a4cc6f9cbd0a901c22|example-set|configuration",
      "target_attribute_key": "market",
      "normalized_concept": "US",
      "mapping_status": "mapped",
      "applicability_ref": "app",
      "normalization": {
        "id": "source_literal",
        "version": "1.0.0"
      },
      "finding_refs": []
    },
    {
      "interpretation_id": "i-model",
      "source_assertion_ref": "example_only_g|sha256:4cd3a253487f03365331d44a9904deecdfa7ced31d78c7a4cc6f9cbd0a901c22|example-set|configuration",
      "target_attribute_key": "model",
      "normalized_concept": "Transit",
      "mapping_status": "mapped",
      "applicability_ref": "app",
      "normalization": {
        "id": "source_literal",
        "version": "1.0.0"
      },
      "finding_refs": []
    },
    {
      "interpretation_id": "i-model_year",
      "source_assertion_ref": "example_only_g|sha256:4cd3a253487f03365331d44a9904deecdfa7ced31d78c7a4cc6f9cbd0a901c22|example-set|configuration",
      "target_attribute_key": "model_year",
      "normalized_concept": 2024,
      "mapping_status": "mapped",
      "applicability_ref": "app",
      "normalization": {
        "id": "source_literal",
        "version": "1.0.0"
      },
      "finding_refs": []
    },
    {
      "interpretation_id": "i-trim_name",
      "source_assertion_ref": "example_only_g|sha256:4cd3a253487f03365331d44a9904deecdfa7ced31d78c7a4cc6f9cbd0a901c22|example-set|configuration",
      "target_attribute_key": "trim_name",
      "normalized_concept": "Cargo",
      "mapping_status": "mapped",
      "applicability_ref": "app",
      "normalization": {
        "id": "source_literal",
        "version": "1.0.0"
      },
      "finding_refs": []
    }
  ],
  "canonical_powertrain": null,
  "factory_body": {
    "disposition": "pending",
    "identity": {
      "semantic_digest": "sha256:1b1b51e2c0ee22bf2679b95a1eccf151e3e8bda65d55a2593db65170bedcad28",
      "preimage": {
        "identity_contract": "factory-body-semantic/2",
        "profile_family": "factory-body",
        "scope": {
          "manufacturer_key": "ford",
          "model_key": "transit",
          "generation_key": "example-generation"
        },
        "dimensions": {
          "roof_height_designation": "high"
        }
      }
    },
    "support": {
      "applicability_ref": "app",
      "configuration_refs": [
        "example_only_g|sha256:4cd3a253487f03365331d44a9904deecdfa7ced31d78c7a4cc6f9cbd0a901c22|example-set|configuration"
      ],
      "interpretation_refs": [
        "i-factory_body.roof_height_designation"
      ],
      "equivalence_interpretation_ref": null
    }
  },
  "factory_series": null,
  "candidate_hash": "sha256:932586e2f1cc7831781dead71ba117a85bbbd1ebb19338ee6ffbee4f141266a2"
}
```

### H. Actual ambiguity — same supported sparse roof observation before parent resolution

For the resolution scenario only, assume two supported existing bodies in this same example Scope: {roof_height_designation:high,wheelbase_designation:long} and {roof_height_designation:high,wheelbase_designation:short}. Both fit H; the result is resolution/BODY_AMBIGUOUS and execution-ineligible, regardless of iteration order. H remains structurally valid. No parent is selected or minted. Those hypothetical alternatives are explanatory context, not extra candidate members or a new resolution contract.

```json
{
  "envelope": {
    "artifact_type": "rigarchive.candidate_configuration.v3",
    "schema_version": "3.0.0",
    "$schema": "urn:rigarchive:contract:candidate_configuration:3.0.0"
  },
  "candidate_reference": "illustration-H",
  "candidate_identity": {
    "manufacturer_name": "Ford",
    "vehicle_model_name": "Transit",
    "model_year": 2024,
    "market": "US",
    "trim_name": "Cargo"
  },
  "canonical_scope": {
    "manufacturer_key": "ford",
    "model_key": "transit",
    "generation_key": "example-generation"
  },
  "canonical_identity_contract": "vehicle-definition-body/2",
  "drivetrain": null,
  "configuration_refs": [
    "example_only_h|sha256:4cd3a253487f03365331d44a9904deecdfa7ced31d78c7a4cc6f9cbd0a901c22|example-set|configuration"
  ],
  "applicability": [
    {
      "applicability_id": "app",
      "scope": {
        "manufacturer_key": "ford",
        "model_key": "transit",
        "generation_key": "example-generation"
      },
      "market": "US",
      "start_year": 2024,
      "end_year": 2024,
      "configuration_refs": [
        "example_only_h|sha256:4cd3a253487f03365331d44a9904deecdfa7ced31d78c7a4cc6f9cbd0a901c22|example-set|configuration"
      ],
      "source_assertion_refs": [
        "example_only_h|sha256:4cd3a253487f03365331d44a9904deecdfa7ced31d78c7a4cc6f9cbd0a901c22|example-set|configuration"
      ],
      "finding_refs": []
    }
  ],
  "evidence_documents": [
    {
      "source_id": "example_only_h",
      "raw_artifact_hash": "sha256:4cd3a253487f03365331d44a9904deecdfa7ced31d78c7a4cc6f9cbd0a901c22",
      "raw_artifact_reference": "docs/examples/not-retained/H.json",
      "extractor_id": "example-only",
      "extractor_version": "1.0.0",
      "extraction_mode": "illustration",
      "assertion_set_id": "example-set",
      "assertions": [
        {
          "assertion_id": "configuration",
          "attribute_key": "configuration",
          "raw_value": {
            "make": "Ford",
            "model": "Transit",
            "model_year": 2024,
            "market": "US",
            "trim_name": "Cargo",
            "factory_body.roof_height_designation": "high"
          },
          "source_context": "Hypothetical positive configuration; not verified manufacturer evidence"
        }
      ]
    }
  ],
  "evidence_raw_hashes": [
    "sha256:4cd3a253487f03365331d44a9904deecdfa7ced31d78c7a4cc6f9cbd0a901c22"
  ],
  "generation_evidence": [],
  "normalized_assertions": [
    {
      "interpretation_id": "i-factory_body.roof_height_designation",
      "source_assertion_ref": "example_only_h|sha256:4cd3a253487f03365331d44a9904deecdfa7ced31d78c7a4cc6f9cbd0a901c22|example-set|configuration",
      "target_attribute_key": "factory_body.roof_height_designation",
      "normalized_concept": "high",
      "mapping_status": "mapped",
      "applicability_ref": "app",
      "normalization": {
        "id": "source_literal",
        "version": "1.0.0"
      },
      "finding_refs": []
    },
    {
      "interpretation_id": "i-make",
      "source_assertion_ref": "example_only_h|sha256:4cd3a253487f03365331d44a9904deecdfa7ced31d78c7a4cc6f9cbd0a901c22|example-set|configuration",
      "target_attribute_key": "make",
      "normalized_concept": "Ford",
      "mapping_status": "mapped",
      "applicability_ref": "app",
      "normalization": {
        "id": "source_literal",
        "version": "1.0.0"
      },
      "finding_refs": []
    },
    {
      "interpretation_id": "i-market",
      "source_assertion_ref": "example_only_h|sha256:4cd3a253487f03365331d44a9904deecdfa7ced31d78c7a4cc6f9cbd0a901c22|example-set|configuration",
      "target_attribute_key": "market",
      "normalized_concept": "US",
      "mapping_status": "mapped",
      "applicability_ref": "app",
      "normalization": {
        "id": "source_literal",
        "version": "1.0.0"
      },
      "finding_refs": []
    },
    {
      "interpretation_id": "i-model",
      "source_assertion_ref": "example_only_h|sha256:4cd3a253487f03365331d44a9904deecdfa7ced31d78c7a4cc6f9cbd0a901c22|example-set|configuration",
      "target_attribute_key": "model",
      "normalized_concept": "Transit",
      "mapping_status": "mapped",
      "applicability_ref": "app",
      "normalization": {
        "id": "source_literal",
        "version": "1.0.0"
      },
      "finding_refs": []
    },
    {
      "interpretation_id": "i-model_year",
      "source_assertion_ref": "example_only_h|sha256:4cd3a253487f03365331d44a9904deecdfa7ced31d78c7a4cc6f9cbd0a901c22|example-set|configuration",
      "target_attribute_key": "model_year",
      "normalized_concept": 2024,
      "mapping_status": "mapped",
      "applicability_ref": "app",
      "normalization": {
        "id": "source_literal",
        "version": "1.0.0"
      },
      "finding_refs": []
    },
    {
      "interpretation_id": "i-trim_name",
      "source_assertion_ref": "example_only_h|sha256:4cd3a253487f03365331d44a9904deecdfa7ced31d78c7a4cc6f9cbd0a901c22|example-set|configuration",
      "target_attribute_key": "trim_name",
      "normalized_concept": "Cargo",
      "mapping_status": "mapped",
      "applicability_ref": "app",
      "normalization": {
        "id": "source_literal",
        "version": "1.0.0"
      },
      "finding_refs": []
    }
  ],
  "canonical_powertrain": null,
  "factory_body": {
    "disposition": "pending",
    "identity": {
      "semantic_digest": "sha256:1b1b51e2c0ee22bf2679b95a1eccf151e3e8bda65d55a2593db65170bedcad28",
      "preimage": {
        "identity_contract": "factory-body-semantic/2",
        "profile_family": "factory-body",
        "scope": {
          "manufacturer_key": "ford",
          "model_key": "transit",
          "generation_key": "example-generation"
        },
        "dimensions": {
          "roof_height_designation": "high"
        }
      }
    },
    "support": {
      "applicability_ref": "app",
      "configuration_refs": [
        "example_only_h|sha256:4cd3a253487f03365331d44a9904deecdfa7ced31d78c7a4cc6f9cbd0a901c22|example-set|configuration"
      ],
      "interpretation_refs": [
        "i-factory_body.roof_height_designation"
      ],
      "equivalence_interpretation_ref": null
    }
  },
  "factory_series": null,
  "candidate_hash": "sha256:085f3cf2dfd1743be5278b4605a86a00ceb476a6fc0797f3504e7932e7136afe"
}
```

## 12. Future validation and integration matrix

| Pure contract/evidence tests | Required assertions |
| --- | --- |
| Closed schemas | Every root/nested type, tag, field requirement, optional omission/null, typed value and prohibited extension; raw maps stay inert. |
| Sparse identity | No-body 4Runner, one-field Wrangler body and sparse van valid; no obligatory seven-status/body-form/series findings; no empty parent. Blank missing fields alone yield no review diagnostic. |
| Existing/pending parents | Independent digest reconstruction; no UUID in pending; UUID-only existing rejected; exact Scope and binding applicability references; pending descriptor checksum differs when evidence changes. |
| Qualified support | Broken refs, cross-document aliases, wrong year/market/positive grouping, unsupported raw claim and concealed source discriminator detected; one legitimate composite finding can support many fields. |
| Coexistence: alternatives versus positive grouping | Two assertions sharing a document, assertion set, table or extraction batch but describing alternative configurations must not be combined on that basis; reject the unsupported join as evidence/COEXISTENCE_NOT_ESTABLISHED. Positive qualified same-configuration grouping or demonstrated cross-reference supports legitimate coexistence without new mandatory fields. |
| Pending-parent unresolved relationship | No exact digest match plus insufficient evidence of distinct identity yields outcome C: no create/reuse disposition. A newly computed digest does not justify creating a parent. |
| Partial-parent ordering | A partial observation compatible with multiple existing parents is not arbitrarily assigned; reversing peer/source order preserves the ambiguity and no disposition. |
| Structural/hash versus evidence validity | A schema-conforming, correctly hashed candidate with an unsupported body projection passes structural/cryptographic checks but fails evidence validation; report PROJECTION_MISMATCH or the relevant evidence code, not schema/hash failure, approval or import eligibility. |
| Ordinary no-body path | No meaningful body distinction: no FactoryBodyConfiguration reference, placeholder, missingness review or parent-publication gate; validity and normal progression remain governed by existing non-body safeguards. |
| Wrangler review reuse | Authentic JL24 qualified headings map directly to two-door/four-door; same normalizer/finding can be reused across supported trims/engines without another human door review; raw Unlimited wording survives. |
| Series | Namespace/designation/independent role supported; null needs no not-separate finding; source grade cannot be duplicated as series. |
| Hashing/parser | Duplicate keys at every nesting level, unsupported dispatch triples, invalid decimal/nonfinite values and surrogate rejection; exact whole-candidate hash vectors, insertion-order invariance, deterministic set arrays, preserved raw-array order. |
| Semantic/artifact separation | Alias/evidence revision changes candidate hash without creating a different frozen body; different known doors change body and baseline digests. Timestamp/path changes are artifact changes. |
| Comparison | Equality versus compatibility; unique compatible result not equality; two compatible parents ambiguous regardless of iteration order; intermediate partial observation never merges known differing bodies; actual same-group contradiction preserved/reviewed. |
| Historical preservation | Fixed Candidate 2.1.0 bytes and old hashes/meaning, frozen /1 preimages, old adjudication/base guards and legacy reader rejection of v3. No fallback into unknown_fields execution. |

Later database-dependent tests separately cover genuine persisted parent/revision
snapshot verification, PROTECT/scope invariants, qualified whole-peer resolution,
legacy-null overlap without blanket blocking, exact create/reuse authorization,
concurrent/stale namespace changes, atomic parent+VD+receipt rollback, Matrix boundaries,
immutable historical slugs and actual-combination UI. Those tests and all operational
behavior are outside this design-only task; no Django tests are run for this document.

## 13. Design-only validation record

Documentation checks parse all eight complete candidate JSON blocks, validate their
specified closed shapes, required fields/tags, sorted arrays, QRefs, local references,
sparse preimage digests, applicability, normalized projections and whole-candidate
hashes. They also check Markdown structure, local links, terminology and Git whitespace.
Authentic B/C heading references are compared to retained source artifacts; synthetic
examples are not claimed byte-verifiable against files that do not exist. Preservation
fingerprints cover existing implementation, tests, candidate artifacts, database,
accepted architecture and governance records. Only RA-046 may be added/changed.
All eight JSON documents passed duplicate-key-aware parsing and checks of example
closed shapes, dispatch triples, reference ordering, qualified/local links, applicability,
normalization projections and semantic/artifact hash reconstruction. Authentic B/C
heading identifiers, all five primary source assertions and raw CSV hashes matched
the retained handoffs. Markdown headings/fences/local links/whitespace passed; all
6,144 existing baseline files remained unchanged and only RA-046 was added. The Git
index remained empty; no staging, commit or push occurred. These checks cover the example shapes used,
not every possible future optional payload. These documentation checks do not implement
or certify a JSON Schema, candidate builder or importer.

For the final clarification revision, all eight §11 JSON blocks and their hashes
are preserved byte-for-byte. The refinement changes only grouping semantics (§§3–4),
pending-parent outcomes (§§5–6), validation boundaries (§7), regression criteria (§12)
and this verification record. No wire member, hash algorithm, accepted architecture
or approval status changes. Fresh documentation checks passed for structure, links, example consistency and
semantic/artifact hash reconstruction. The eight JSON blocks remain byte-identical;
only RA-046 changed among 6,145 fresh baseline files, with no new repository paths
and an empty Git index. No application or database-dependent tests are run.

## 14. Approved decisions and remaining implementation prerequisites

**Project Owner approval recorded on 2026-11-13:** all exact wire selections in
this table are accepted for the current reviewed revision. RA-047 is separately
accepted as the conforming pure implementation, including its EvidenceReport API
correction and 837-test verification. No accepted architecture conflict or new ADR
is required. Missing-original-source, pending engine-classification, external dependency
verification and Generation-publication constraints are not waived.

| Decision | Approved choice | Rationale / governing architecture | Compatibility / approval |
| --- | --- | --- | --- |
| 1. Envelope | v3 artifact type, schema 3.0.0, required local URN; recursive closed objects | RA-011 explicit dispatch; ADR-0013/RA-045 version boundary | New reader only; old versions untouched. Owner approval recorded 2026-11-13. |
| 2. Existing parent | UUID + full frozen preimage/digest + immutable revision UUID/hash + exact qualified support/applicability | RA-045 protected reuse and source lineage; UUID/compatibility alone insufficient | Needs later persisted binding snapshot reader; no new body-review stage. Owner approval recorded 2026-11-13. |
| 3. Pending parent | No UUID; deterministic identity and support; disposition means unbound, not proven absent | ADR-0007 exact authorization and RA-045 read-only planning | Later plans pin exact create/reuse; unexpected namespace changes stale plans. Owner approval recorded 2026-11-13. |
| 4. Series | Independent model-scoped /1 semantic identity; same union lifecycle with supported role | ADR-0011 as amended by ADR-0013 | Null normal; no not-separate checklist, no duplicate trim discriminator. Owner approval recorded 2026-11-13. |
| 5. Evidence granularity | QRefs + reusable applicability/grouping + field interpretations; one composite assertion/finding can establish many fields | RA-011/025/044 provenance and coexistence; RA-045 sparse support | No manufacturer-source rewrite or source-count mandate. Owner approval recorded 2026-11-13. |
| 6. Human finding reuse | References to actual original reviewed findings; normal direct Wrangler rule needs no extra body approval | ADR-0007/0013 review authority and exact-base limits | Old candidate-bound adjudications cannot silently approve v3; reader/normalizer registry needs implementation fixtures. Owner approval recorded 2026-11-13. |
| 7. Artifact hash | Complete v3 root minus candidate_hash; schema/evidence/revisions included; canonical Python JSON | Existing SHA-256 convention; RA-045 semantic/evidence separation | Projection checksum and historical v2 hashes unchanged; new vectors required. Owner approval recorded 2026-11-13. |
| 8. Validation/resolution | Parse/shape, evidence support, actual conflicts, then live whole-set resolution and authorization | RA-045 no blank-field review; compatibility is not equality | Ambiguity is not an unknown-field/schema failure; no eligibility claim in candidate. Owner approval recorded 2026-11-13. |
| 9. Historical compatibility | Frozen old dispatch/readers/hashes/receipts; reject unsupported v3 | ADR-0002/0007/0012/0013 | No body semantics in v2 metadata; downstream successor contracts still needed. Owner approval recorded 2026-11-13. |
| 10. Prerequisites | Specification approved and RA-047 pure implementation accepted; separately scope later binding persistence/proof/execution contracts | RA-045 phased implementation and current design-only boundary | Binding-revision snapshot format and downstream proof/authorization schemas remain later dependencies, not hidden accepted schemas. Owner approval recorded 2026-11-13. |

The current reviewed contract choices are approved and RA-047 pure implementation
is accepted. Later source/review decoder coverage, canonical binding/proof consumers,
persistence, live resolution, authorization and execution remain separately scoped
prerequisites. This approval does not extend to those future milestones.
