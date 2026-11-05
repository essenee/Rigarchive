# W2: Specification property and applicability contract

**Status**: Approved architecture contracts, incorporating director-approved Phase A corrections on 2026-11-04. B1 pure serializers/validators are implemented; persistence/publication execution is not implemented. No migration or canonical-write authorization.

## 1. Structural contract

The closed wire schemas in §7 are normative. All listed keys are required; explicitly nullable values must be present as null, never omitted. Unknown keys are rejected, including arbitrary extension keys in execution-critical objects. Raw unsupported material remains in retained source artifacts or inventory records, not undeclared executable fields. Required unknown information uses explicit status.

A valid normalized quantity is `{"status":"reported","kind":"quantity","amount":"123.4","unit":"mm"}`. Its original source text may remain `123.40`; formatting is not discarded from provenance. Examples of UUIDs/references in prose are placeholders, not publishable evidence. Scope is constrained by exact baseline catalogue membership; `true` does not expand a claim across models/years. Review findings and evidentiary reconciliation remain independent.

## 2. Property taxonomy and identity

Property key is stable and globally unique; label is not identity. Keys express meaning, not arbitrary source field names. Definitions require dimensional family/value kind and permitted component/qualifier schema. Quantity definitions allow compatible result units, never an obligatory/default unit. Method-specific concepts that are not comparable use separate keys or mandatory distinguishing method qualifiers. A changed semantic meaning creates a new key; compatible descriptive revision preserves key and pins definition revision.

Initial controlled vocabulary (illustrative supported concepts, not assertions):

| Category | Property keys / required distinction |
| --- | --- |
| Engine | `engine.displacement`, `engine.power`, `engine.torque`, `engine.cylinder_count`, `engine.induction`, `engine.fuel_type`; power/torque RPM and rating standard |
| Transmission | `transmission.forward_gear_ratio`, `transmission.reverse_gear_ratio`, `transmission.speed_count`; gear/component index and selected offering |
| Drivetrain | `drivetrain.transfer_case`, `drivetrain.low_range_ratio`, `drivetrain.operating_mode`, `drivetrain.locking_capability`; mode, axle/component and operating restrictions |
| Exterior | `dimensions.exterior.overall_length`, `dimensions.exterior.wheelbase`, `dimensions.exterior.height`, `dimensions.exterior.width`; mirrors, load and body context |
| Interior/cargo | `dimensions.cargo.floor_length`, `dimensions.cargo.wheelhouse_clear_width`, `dimensions.cargo.opening_height`, `capacity.cargo.volume`; seating, doors, floor reference and method |
| Mass/ratings | `mass.curb`, `rating.gvwr`, `rating.gawr`, `rating.gcwr`, `rating.payload`, `rating.towing`; axle, load, trailer, equipment and rating method |
| Chassis | `suspension.type`, `brakes.rotor_diameter`, `steering.turning_diameter`, `axle.ratio`; front/rear and curb/wall turning method |
| Wheels/tires | `wheel.diameter`, `wheel.width`, `tire.designation`, `tire.load_rating`; axle, spare and fitment |
| Fuel | `capacity.fuel`, `economy.city`, `economy.highway`, `economy.combined`; US/Imperial gallon, fuel and test-cycle/year |

This vocabulary is extensible by reviewed definition publication. Membership in a category does not authorize assigning a value. Drivetrain capabilities/modes remain richer assertions rather than expanding baseline `4WD` into guessed hardware or modes. Preserve existing EngineDetails/DrivetrainDetails/TransmissionDetails intermediate concepts; new contracts support repeated scoped offerings without changing the old singular field's meaning.

## 3. Typed value tagged union

`status` is exactly `reported`, `unknown`, `not_published`, `not_applicable`, or `explicitly_unavailable`. Non-reported status has a nonempty reason and no numeric/categorical value. `not_published` is a finding about the inspected corpus, not proof that no publication exists. Explicit unavailable requires affirmative source evidence; zero is a reported numeric value, not missing.

Reported `kind` is one of:

- `quantity`: decimal-string amount plus unit; optional published uncertainty/bound qualifier.
- `range`: decimal lower/upper, common unit and inclusive/exclusive flags; lower <= upper.
- `integer`: integer value with property-validated domain.
- `boolean`: true/false only with explicit source semantics; absence is never false.
- `category`: controlled term identifier and original manufacturer term.
- `text`: source-backed unresolved/descriptive text, not a numeric substitute.
- `ordered_values`: homogeneous typed values with explicit indices, only for definitions permitting sequences (e.g. ratios); per-element provenance where source cells differ.

Quantities serialize as canonical finite decimal strings without exponent, leading plus, insignificant trailing fractional zeros or negative zero; `0` is valid where the property's domain permits it. Original source formatting remains intact. No float, NaN, infinity, ambiguous unit or assumed uncertainty. Unit tokens come from reviewed registry version; record conversion rule/version, input/output unit, exact factor/offset and rounding. A unit conversion does not establish method or scope equivalence. Do not equate US/Imperial gallon, SAE/DIN power or different economy cycles. Dimensions in published profile labels remain designations, not automatically converted measurements.

Qualifiers preserve minimum/maximum/approximate claims, RPM, load state, seating, position, measurement method/version, standard/test cycle, source footnote and uncertainty if stated. Unknown method is explicitly recorded; never claim two methods equivalent by default. Free wording is retained alongside controlled interpretation. Unsupported interpretation stays unresolved.

## 4. Bounded applicability language 1.0

JSON AST nodes only; no code, SQL, regex, arbitrary paths, scripting, arithmetic or network calls. Maximum depth 8, nodes 128, children per logical node 32, list members 64, UTF-8 predicate size 32 KiB. A catalogue may have at most 1,000 rules and evaluation traverses at most 100,000 nodes per request; exceeding bounds returns a validation/review-required error, never partial supported output. Root depth is 1. Count each AST object carrying `op` as one operator node; scalar operands, UUIDs and lists are not extra operator nodes. Child depth is parent depth + 1. Measure size over canonical compact UTF-8 JSON of the predicate node itself (not the applicability wrapper), at most 32,768 bytes. The rule count includes all compatibility rules in the pinned catalogue. Before evaluation, reserve the complete structural node count for each predicate invocation, including assertions, offerings, rules and feature mappings, against one shared 100,000-node budget for the complete requested sheet/selection; repeated invocations count repeatedly. No per-property reset, short-circuiting or caching may evade accounting. Bounds are inclusive. Limits are versioned contract decisions; increasing them requires explicit compatibility review.

Allowed nodes:

| Node | Shape / semantics |
| --- | --- |
| `true`, `false` | No operands; restricted to explicit scoped assertions |
| `all`, `any` | Nonempty `args` list of predicates; three-valued AND/OR |
| `eq` | `field`, typed `value`; exact known-context equality |
| `in` | `field`, nonempty same-type `values`; exact known membership |
| `date_between` | `field`, nullable inclusive `start`/`end` (at least one); ISO date, start <= end |
| `selected` | `offering_revision_uuid`; membership in explicitly known selection |
| `feature_is` | `feature_uuid`, `state_uuid`; state must belong to feature |

Allowed context fields: `baseline_uuid`, `market`, `model_year`, `body_uuid`, `series_uuid`, `production_date`, `order_date`. Market/year/baseline are pinned from canonical context, not user overrides. Offering references identify exact members of pinned catalogue. Physical context requires reviewed feature mappings or explicit separately attributed context; no arbitrary caller state becomes reviewed factory evidence. Optional context has known/unknown status. The independent selection envelope in §7 determines `selected`: unknown in the relevant unspecified group, true for explicit inclusion, false for nonmembership in that group’s known selection. The other group’s knownness has no effect; false selection still does not prove physical equipment absence. A catalogue with incomplete choice inventory cannot treat that set as a complete physical build.

There is no generic NOT in v1; explicit negative factory facts are represented by reviewed exclusions or an explicitly established physical state. Unknown enum values/operators/fields, wrong member kinds, missing dependencies, impossible dates and malformed/cyclic references fail validation. Unsupported source restrictions are retained but cannot be omitted to publish unrestricted offerings. Model-year applicability and production/order dates are separate; none is inferred from another.

Three-valued predicates return true/false/unknown. `all`: false if any false, true if all true, else unknown. `any`: true if any true, false if all false, else unknown. This does not reconcile contradictory evidence: conflicting contexts remain unknown with conflict details. No optimizer may erase an unresolved restriction.

## 5. Compatibility and assertion evaluation

Evaluate full selection against exact catalogue revision, effective scope, offerings and required rules. Rule operands are typed exact offering/item revision references, cardinality bounds and predicate conditions; inclusion/replacement targets are exact equipment revisions. Dependencies cannot create new baseline choices. Detect cycles in prerequisite and inclusion graphs; contradictory rules remain review-required.

- **Supported**: availability established for every selection, all applicable restrictions satisfied, and evidence establishes whole-selection coexistence through an explicit supported combination or a reviewed complete rule scope covering this selection.
- **Incompatible**: an established applicable exclusion/prerequisite violation exists without unresolved contradictory findings about that restriction. Preserve reasons even when other checks are incomplete.
- **Unverified**: no decisive consistent prohibition but missing/ambiguous/conflicting availability, dates, restrictions or whole-selection proof. Contradictory findings about a restriction remain unverified/review-required, not silently selected by publisher priority.

Independent availability and pairwise support never imply higher-order support. Cardinality, required-all/any, inclusion, exclusion and replacements apply to the whole set, not checkbox pairs. Do not auto-select prerequisites, remove packages or infer supported combinations.

An assertion is **applicable** when its scope/predicate is true and any required full-selection support is established; **inapplicable** when scope is demonstrably false; otherwise **unestablished**. For incompatible/unverified selections, baseline-unconditional assertions remain available, but no definitive selected-build sheet or conditional rating is produced. A consistent false predicate may still identify an assertion as inapplicable. Scope-independent conflicts remain visible as separate reports. Reviewed supersession preserves old claims; no specificity or publisher ordering silently picks a winning value.

Never calculate payload as GVWR minus a differently scoped curb weight, derive towing from GCWR, add independent package deltas, average conflicts or transfer ratings between wheelbase/roof/transmission contexts without separately evidenced and authorized derivation semantics. Such derived-rating semantics are not part of v1.

## 6. Physical Measurements and accessories

Mappings establish controlled physical states only with exact scoped evidence. An unchecked package does not establish absence; another option or standard assignment may supply the feature. Unresolved/incompatible contexts cannot prove conditional measurement applicability. Generation-wide reports remain visible. User reports remain independent; no new measurement protocol storage or automatic result selection is introduced.

Brochure-listed accessories remain catalogue-only; accessory-dependent predicates, compatibility operands, specification effects and physical feature inference are prohibited in v1. Raw release retention is allowed without ingesting its accessory catalogue. Other authoritative manufacturer publications remain acceptable for technical/identity assertions.

## 7. Closed wire schemas (normative)

Token uses the reviewed grammar in Domain §8. CanonicalMarket and CanonicalDrivetrain mean the existing model-supported enums; changing them requires separate approval. EvidenceLink is the closed role/reference shape below.

Notation: `{key:Type,...}` specifies EXACT required keys; `T|null` permits explicit null; `[T]` is an array; `Enum(...)` is a literal choice. No implicit optional keys. `String` is valid Unicode text, `Text` is nonempty String, `Integer` is a JSON integer excluding Boolean, `PositiveInt` >=1, `Hash` is `sha256:` plus 64 lowercase hex, `UUID` is lowercase hyphenated, `Date` is a valid ISO date, `Time` is UTC `+00:00`. `Decimal` is finite canonical `-?(0|[1-9][0-9]*)(\.[0-9]*[1-9])?`, excluding `-0`; no exponent/plus/leading zeros. Canonicalization rejects rather than silently rewrites incoming execution artifacts. Producer normalization occurs before review/hash. All arrays are bounded by their declared contract; nonempty means length >=1.

### Values

`Value` is exactly one tagged shape:

| Tag | Exact shape |
| --- | --- |
| missing | `{status:Enum(unknown,not_published,not_applicable,explicitly_unavailable), reason:Text}` |
| quantity | `{status:"reported",kind:"quantity",amount:Decimal,unit:Token}` |
| range | `{status:"reported",kind:"range",lower:Decimal,upper:Decimal,unit:Token,lower_inclusive:Boolean,upper_inclusive:Boolean}` |
| integer | `{status:"reported",kind:"integer",value:Integer}` |
| boolean | `{status:"reported",kind:"boolean",value:Boolean}` |
| category | `{status:"reported",kind:"category",term:Token,manufacturer_term:Text}` |
| text | `{status:"reported",kind:"text",value:Text}` |
| ordered_values | `{status:"reported",kind:"ordered_values",element_kind:Enum(quantity,range,integer,boolean,category,text),elements:[SequenceElement]}` |

`SequenceElement = {index:Integer,value:ScalarValue,evidence_refs:[EvidenceRef]}`; index >=0, unique strictly increasing order, values all reported and match element_kind, no nested sequence/missing member. Elements 1..64; evidence nonempty. ScalarValue excludes ordered_values and missing. Definition determines whether indices are contiguous, units/dimensional family and legal domain; default is explicit indices without assumed completeness. Range lower <= upper; equal endpoints require both inclusive. Units/terms resolve to the pinned reviewed registry, with exact definition compatibility. Zero is reported, never missing.

`Original = {label:Text,value:String,unit:String|null}`. Source numbers are kept as verbatim text or referenced artifact content, not parsed floats. `Qualifier = {key:Token,value:ScalarValue,evidence_refs:[EvidenceRef]}`; nonempty evidence, unique key in one assertion; indexed repeated qualifiers require separate assertion/component, not duplicate keys. Each qualifier key/value kind and unit is permitted by the pinned definition. Unparsed qualifier text is retained as kind text and cannot establish a stronger condition. `method` below explicitly records unknown methods rather than inventing one.

`Method = {status:"established",identifier:Text,version:String|null,evidence_refs:[EvidenceRef]}` or `{status:"unknown",reason:Text}`. No default protocol is inferred.

`Conversion = {rule_id:Text,rule_version:Text,input_value:Decimal,input_unit:Token,output_value:Decimal,output_unit:Token,factor_numerator:Decimal,factor_denominator:Decimal,offset:Decimal,rounding:Enum(exact,half_even,half_up),decimal_places:Integer|null}`. Denominator nonzero; exact rational factor, offset and rounding must reproduce output. exact requires decimal_places null and representable exact result; rounded mode requires decimal_places >=0. Output must equal normalized value; conversion is not source-method equivalence. No unsupported conversion or rating calculation is authorized.

`Normalization = {method:Enum(direct_copy,exact_mapping,parsed,converted,interpreted,unmapped),rule_id:Text,rule_version:Text,conversion:Conversion|null,notes:String}`. Converted requires conversion; other methods require null. Non-quantity/nonlinear conversions are not supported by this quantity conversion shape.

### Evidence, review and assertions

`EvidenceRef = {source_id:Text,document_hash:Hash,document_reference_hash:Hash,extractor_id:Text,extractor_version:Text,extraction_mode:Text,assertion_set_id:Text,local_assertion_id:Text,assertion_hash:Hash}`. All fields resolve together to one retained document/acquisition reference and immutable assertion reference; matching local ID alone is invalid. The document_reference_hash differentiates honest acquisition identities for identical bytes. Arrays preserve primary evidence order and reject duplicate complete references. Role links are `{role:Enum(supports,contradicts,qualifies,excludes),reference:EvidenceRef}`; no dropped contradictory/qualifying evidence.

`Review = {finding:Enum(established,unresolved,withdrawn),reviewer:Text,reviewed_at:Time,notes:String}`. `Reconciliation = Enum(single_source,corroborated,conflicting,ambiguous,incomplete)`; publication of conflict requires explicit unresolved finding, not a fabricated winner.

`SpecificationAssertion = {artifact_type:"rigarchive.specification_assertion.v1",schema_version:"1.0.0",assertion_uuid:UUID,definition_revision_uuid:UUID,definition_revision_hash:Hash,value:Value,original:Original,qualifiers:[Qualifier],method:Method,component:Text|null,applicability:Applicability,evidence_links:[EvidenceLink],normalization:Normalization,reconciliation:Reconciliation,review:Review,supersedes_assertion_uuid:UUID|null,content_hash:Hash}`. At least one supporting evidence link; qualifiers may be empty. Content hash excludes only its own content_hash; definition and registry constraints resolve against exact pinned publication dependencies. Same-lineage correction preserves predecessor with a single successor; independent conflicting claims remain distinct. The shape replaces the earlier illustrative envelope, not historical SourceAssertionSet/Candidate v2 serialization.

### Predicate node shapes and typed fields

`Applicability = {language_version:"1.0",predicate:Predicate}`. Predicate is exactly one shape:

- `{op:"true"}` or `{op:"false"}`.
- `{op:Enum(all,any),args:[Predicate]}`; 1..32 children.
- `{op:"eq",field:Field,value:FieldValue}`.
- `{op:"in",field:Field,values:[FieldValue]}`; 1..64 unique values, sorted by canonical JSON bytes.
- `{op:"date_between",field:Enum(production_date,order_date),start:Date|null,end:Date|null}`; at least one bound, inclusive ordered interval.
- `{op:"selected",offering_revision_uuid:UUID}`.
- `{op:"feature_is",feature_uuid:UUID,state_uuid:UUID}`.

`Field` and FieldValue types: baseline/body/series UUID fields => UUID; market => existing canonical market enum; model_year => Integer within supported canonical year validation; production/order date => Date. eq/in must use exactly the field's type, not coercion. No arbitrary field paths or null comparisons. Unknown optional contexts evaluate unknown. body/series explicitly not-applicable/not-separate contexts give false for eq/in to any UUID, while legacy-unassessed/unknown remains unknown. Feature state must belong to feature, and offering must belong to pinned catalogue/baseline and be a factory/transmission member of the permitted kind.

### Independent selection envelope

`Selection = {language_version:"1.0",baseline_uuid:UUID,catalogue_revision_uuid:UUID,transmission:TransmissionSelection,equipment:EquipmentSelection,production_date:KnownDate,order_date:KnownDate}`.

`TransmissionSelection` is `{status:"unknown"}` or `{status:"known",offering_revision_uuid:UUID|null}`. Exactly zero or one UUID is representable; null is explicit no transmission selection, not proof that a physical vehicle has no transmission. It does not authorize a complete selected-build claim where a transmission must be established. More than one transmission or extra array/keys is invalid.

`EquipmentSelection` is `{status:"unknown"}` or `{status:"known",offering_revision_uuids:[UUID]}`. Known empty array means no optional factory offerings selected, not equipment physically absent. UUIDs are sorted; duplicates are rejected, never deduplicated silently. `KnownDate` is `{status:"unknown"}` or `{status:"known",value:Date}`.

Validate all UUIDs before evaluation. Foreign/wrong-kind/nonmember/stale revision references, accessory/standard-assignment references in optional selection, and explicitly unavailable offerings produce selection validation errors; do not drop them, switch revisions or fall back. An offering of unknown/conditional availability may be selected as a hypothesis but yields unverified support until established. Evidence-established mutual exclusions/cardinality violations among otherwise valid selections yield incompatible, not a syntactic validation error. Contradictory restrictions remain unverified. Duplicate equipment UUID and multiple transmission attempts are validation errors even if their semantic combination would be incompatible.

`selected(T)` consults only transmission status for transmission offerings; `selected(P)` consults only equipment status for packages/options. Unknown => unknown; known included => true; known not included => false. Neither group is inferred from the other. Global compatibility may remain unverified even when a predicate is true. Standard/include effects are evaluated through pinned rules and never silently inserted into the selected UUID arrays. Accessories cannot participate. No NOT or arithmetic is added.


Categorical qualifier clarification (director-approved 2026-11-04): each categorical QualifierRule pins `categorical_definition:Ref` as defined in Publication §9; noncategorical rules carry explicit null. Resolve its exact definition revision/hash and controlled terms before accepting qualifier values. Parent property categorical_terms never supplies a qualifier's vocabulary. This introduces no generic expression vocabulary or legacy artifact change.
