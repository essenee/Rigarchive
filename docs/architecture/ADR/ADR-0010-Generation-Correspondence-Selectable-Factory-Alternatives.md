# ADR-0010: Generation Correspondence and Selectable Factory Alternatives

- **Status**: Accepted
- **Date**: 2026-11-03
- **Approval**: Accepted by the project director on 2026-11-03 after architectural review, without substantive changes; implementation requires separate authorization
- **Scope**: Architecture documentation only; no implementation or development-database write authorization
- **Supersession**: ADR-0005, Decision 2, only as specified below
- **Related decisions**: ADR-0001 through ADR-0009 remain historical records and are not edited by this decision

## Context

RigArchive distinguishes source evidence, normalized interpretation, transient candidate configurations, reviewed import plans, and canonical Reference records. The approved direction extends this architecture to resolve overlapping generations and describe selectable factory alternatives without multiplying canonical vehicle identities.

Repository inspection establishes these current limitations:

- `VehicleDefinition` identity uses generation, model year, trim, engine descriptor, generic drivetrain and market. Transmission and factory equipment availability are not persistent relationships.
- The canonical planner resolves Generation from model and year. More than one active matching Generation produces review; `CandidateIdentity.generation_name` is caller context and does not establish correspondence.
- Transmission descriptors exist in retained Toyota fixture assertions, but the normalizers do not project them into transmission offerings. The candidate builder sets its transmission projection to `None` and emits an empty `packages_and_options` list.
- The Generation funnel is Model Year → Trim → Configuration → Full Specifications. Full Specifications currently has no transmission/package selection or conditional factory-specification evaluator.
- Measurements remain Generation-anchored reports with controlled physical feature conditions. No configuration-to-feature mapping currently establishes their applicability from sales equipment.
- Population planning can create parent records; batch execution re-plans and authorizes by slug, omits receipts for some outcomes, and bootstrap paths can bypass the authorized receipt workflow. Acquisition manifest extraction provenance contains Toyota-specific constants. These are limitations, not approved precedents for the new workflow.

The 2018 Wrangler JK/JL overlap is a proposed validation case, not an assertion that retained repository evidence already establishes its generation correspondence. Toyota and Volkswagen data must continue to work without inferred alternatives or identity changes.

## Decision

### 1. Authority, supersession and preserved boundaries

This accepted decision supersedes the sentence in [ADR-0005, Decision 2](ADR-0005-Manufacturer-Grade-Taxonomy-Market-Applicability-Normalization.md) stating:

> Option packages and dealer accessories belong exclusively in Observation or Knowledge domains; the Reference domain models factory engineering configurations.

The supersession is limited to the exclusion of **manufacturer-offered factory packages and individual factory options** from Reference. Their catalogue, scoped offerings and evidence-backed engineering effects may be represented in Reference subordinate to `VehicleDefinition`.

The remainder of Decision 2 continues to distinguish factory grades from packages and accessories. Dealer/distributor accessories and owner modifications do not become selectable factory offerings under this decision. An ambiguous installation channel remains unclassified/review-required. A source calling an item a package does not establish that it is a factory offering.

ADR-0005 Decisions 1 and 3–8 remain in force: manufacturer taxonomy governs trim, commercial market is independently established, unsupported Cartesian construction is prohibited, attribute equality is not a join key, and source codes are evidence rather than canonical keys.

ADR-0004's create-only/no-op baseline promotion, ADR-0006's immutable evidence, ADR-0007's exact authorization and atomic receipts, ADR-0008's hard blockers, and ADR-0009's Measurements separation remain in force. This decision extends their contracts; it does not create a force-import or grade-adjudication exception.

Detailed models, migration operations and implementation tasks require separate approval. No new application, dependency, acquisition run or data population is authorized by this document.

### 2. Canonical baseline versus selectable alternatives

`VehicleDefinition` remains the canonical baseline. Preserve its UUID, existing hierarchy, immutable slug and public URL. Do not create a separate VehicleDefinition solely because a factory transmission differs or because packages/options are selected.

Continue handling two-door/four-door distinctions through approved, evidence-backed trim normalization. This decision does not authorize a new body-identity model or arbitrary body suffixes in trim strings. Where existing approved normalization cannot distinguish demonstrated factory baselines, block that case and seek a separately scoped decision.

A selection is a temporary specification-view context consisting of a baseline, an optional transmission offering, selected factory equipment offerings and the applicable reviewed catalogue revision. It is not a canonical vehicle identity, an individual vehicle build record, or proof that equipment was installed on a physical vehicle.

Do not materialize every transmission/package permutation as a VehicleDefinition. Preserve source-native configuration identities and raw coexistence groups even when several source rows enrich one baseline. Baseline deduplication must not discard their alternative-specific assertions.

### 3. Evidence-backed generation correspondence

Preserve legitimate overlapping Generation year ranges. Never shorten a range, select the latest generation, or prefer insertion order merely to obtain one planner match.

A reviewed generation correspondence relates a source-supported configuration/section identity to one canonical Generation. Its contract must include:

- Permanent correspondence identity and immutable revision identity/content hash.
- Source namespace and native identifier, or a source-local structural identity based on raw hash and document location.
- Raw document hashes/references, source assertion references, source locations, extractor version, normalized interpretation and mapping-rule version.
- Manufacturer/model, commercial market, model-year applicability and any source-supported configuration restrictions.
- Target Generation UUID, review finding, reviewer attribution, review time and supersession lineage.

Source codes are not assumed unique across years, models or publishers. A reviewed section heading may establish scope where the document explicitly groups its configurations. Joining several documents requires their demonstrated cross-reference; equality of trim/engine text is insufficient.

Resolution protocol:

1. Extract source terms and configuration grouping without inventing generation boundaries or identities.
2. Normalize generation correspondence evidence separately from caller context.
3. Resolve existing active Manufacturer/VehicleModel parents without creating them.
4. If correspondence is supplied, require exactly one supported target, consistent with all mapped evidence, parent relationships, market and model year. Do not fall back to year-only selection when supplied correspondence conflicts.
5. Without correspondence, retain the existing unique active model/year-range path as an explicit `unique_year_range` resolution basis. An overlap is review-required until correspondence establishes one target.
6. Produce `reviewed_source_correspondence` resolution only from valid reviewed evidence. `CandidateIdentity.generation_name`, caller IDs and operator selection alone never qualify.
7. Freeze resolution and its evidence in the exact review plan before execution authorization.

The planner must block missing correspondence in an overlap, ambiguous targets, contradictory assertions, inactive/mismatched parents and out-of-range evidence. Grade adjudication cannot override these blockers. Establishing correspondence is a semantic review finding, not import authorization.

For 2018 JK/JL, test both source-supported routes and a source that says only Wrangler/2018. The latter must remain unresolved when both generations match. This is a test requirement, not permission to invent production source facts.

### 4. Transmission offerings

Use a reusable transmission description with separately scoped offerings subordinate to exact VehicleDefinitions. The following are conceptual responsibilities, not final Django class names:

| Concept | Required responsibility |
|---|---|
| Transmission description | Manufacturer designation/code, namespace, normalized type, forward-speed count where supplied, and evidence-backed engineering characteristics |
| Transmission offering revision | Availability for an exact VehicleDefinition, source revision, restrictions, completeness status and provenance |
| Conditional specification assertion | A reported property/value/unit with explicit baseline and selection applicability |

A shared transmission description does not imply shared availability. Manufacturer codes require scoped identity; unknown codes remain unknown rather than fabricated. Do not merge transmissions solely because type and speed count match.

Availability must establish the correct vehicle, year, engine, normalized trim, drivetrain and market through the exact baseline association. Preserve any additional source restrictions. If a restriction cannot be represented or resolved, retain it as unresolved evidence and withhold an unrestricted offering claim.

Distinguish standard, optional, explicitly unavailable and unknown availability. Record whether the alternatives inventory is established, corroborated, incomplete or unverified. One recorded alternative does not establish exclusivity. Missing historical data means not recorded, not no alternative.

Transmission-specific specifications are independently sourced assertions. Do not generate mechanical ratings or numerical deltas from selection labels. Alternatives do not change the baseline engine/drivetrain identity; a source selection that requires another baseline must link to that baseline rather than silently replace identity fields.

Reuse `TransmissionDetails` for appropriate intermediate description fields and extend its contract to represent multiple scoped offerings. Reuse BaseModel identity/timestamps and protected relations where appropriate. Existing models do not provide persistent transmission availability; future persistence requires new schema and separately approved migrations.

### 5. Factory catalogue and historical revisions

Keep the following classifications distinct:

| Classification | Representation |
|---|---|
| Trim/grade | Existing approved baseline taxonomy |
| Factory package | Manufacturer-defined bundle of factory equipment |
| Individual factory option | Separately offered factory equipment item |
| Standard equipment | Evidence-backed equipment assignment in a baseline/selection scope; not an optional checkbox |
| Dealer/distributor accessory | Outside this factory catalogue |
| Owner modification | Observation of a physical vehicle; outside this catalogue |

Maintain reusable catalogue identity and immutable offering/content revisions. Preserve manufacturer names, option/package codes, code namespace, descriptions, included equipment, installation classification, source revision and review lineage. Names/codes may change or be reused; neither proves continuity or unchanged contents.

Associate offering revisions with explicit VehicleDefinitions and any supported temporal/configuration restrictions. Do not infer availability in adjacent model years. Preserve midyear document changes, effective production/order dates and earlier assertions where supplied; model year alone may not select one valid revision. Unknown revision applicability remains unverified.

Use source-local structural identity where no native code exists. Never manufacture an option code from a tuple of attribute values. Unknown-field preservation is not a substitute for validated identity, availability or compatibility semantics.

Corrections create reviewed revisions/supersession lineage without deleting source history or silently changing previously reviewed offerings. Source withdrawal does not delete historical factory availability.

### 6. Compatibility and coexistence

Represent compatibility as versioned declarative domain rules with exact applicability and evidence. Never execute rule text obtained from a publication.

Support requirements for a transmission/equipment selection, all-of and any-of prerequisites, exclusions, included equipment, replacements of standard equipment, cardinality restrictions and source-supported combination rules. Identify whether rules apply to the whole baseline, a document revision or a narrower scope. Validate references, inconsistent requirements and dependency cycles; unresolved rules cannot establish support.

Evaluate the complete selection, not only each pair:

| State | Meaning |
|---|---|
| Supported | Evidence establishes the whole combination within scope and all requirements are satisfied |
| Incompatible | Evidence establishes a violated prerequisite, exclusion or other restriction |
| Unverified | Evidence is missing, ambiguous, contradictory or insufficient to establish coexistence |

Report conflicting source findings as such; do not resolve them by global publisher precedence. A demonstrated violated restriction prevents a supported result even when other evidence is incomplete. Contradictory compatibility findings remain review-required and unverified rather than silently choosing one.

Absence of a prohibition is not proof of compatibility. Independently available items cannot be combined automatically. Supported coexistence requires an explicit combination or a source-supported rule set whose scope and completeness establish that combination. Pairwise compatibility does not establish higher-order compatibility. Individual offering completeness and combination-rule completeness are distinct.

Do not precompute a Cartesian catalogue of builds. Evaluate selected items with bounded rule processing and explicit unknown results. Do not silently select prerequisites, remove conflicting packages or calculate unsourced specifications.

### 7. Conditional factory specifications

Keep reported factory specifications separate from empirical measurement results and baseline identity fields. A specification assertion must preserve property identity, value/unit or categorical value, raw wording, evidence lineage, publication revision and a declarative applicability predicate.

Applicability can require a baseline, transmission, equipment combination and other established source restrictions. All required predicates must hold before showing a value as applicable. Missing selection, incomplete restrictions or conflicting evidence must not yield a definitive value.

Selection evaluation returns supported applicable assertions; it does not overwrite canonical fields. A conditional assertion must not silently supersede an unconditional or conflicting value. Retain their scopes and evidence, displaying unresolved conflicts as separate reports until reviewed reconciliation establishes the relationship.

Do not invent numerical adjustments or aggregate independent deltas. Ratings associated with a complete package/transmission combination require evidence for that combination. An incompatible/unverified overall selection cannot produce a definitive selected-build specification sheet; unconditional baseline information remains available.

### 8. Measurement feature-state mappings

Preserve [ADR-0009](ADR-0009-Measurements-Domain-Strategy.md): MeasurementResult stays anchored to Generation, units belong to each result, zero conditions mean Generation-wide, and multiple physical-feature conditions use AND. Preserve independent reports; no automatic canonical-result selection is introduced.

Add reviewed, evidence-backed mappings from baseline/transmission/equipment contexts to controlled `ApplicabilityFeature`/`ApplicabilityState` values. Do not make packages or sales trims measurement features. Preserve mapping revision, exact scope, evidence and conflict state.

Selecting a package establishes a physical state only where its scoped contents establish that state. An unchecked package does not prove absence: the feature may be standard or supplied by another option. Conflicting inferred states remain unknown/conflicting and cannot be used to match a conditional measurement.

For a conditional result, all known matching states establish applicability; a contradictory state makes it inapplicable; any unresolved required state leaves applicability unestablished. Label the applicability of the report, not independent verification of its value. Incompatible/unverified selections cannot establish definitive selected-build measurement applicability. Generation-wide reports remain visible.

This extends feature-state evaluation, not measurement protocol storage, source reconciliation or factory-dimension import into MeasurementResult. Those deferred boundaries remain separate.

### 9. Review authorization, stale state and audit

Preserve the lifecycle: extraction → normalization → candidate construction → semantic review → planning/re-planning → exact execution authorization → execution. Source correspondence review and offering review do not authorize database writes.

Planning must perform zero writes to parents, baselines, offerings, correspondence records, receipts and corrections. Parent creation and semantic catalogue publication are separately reviewed operations. Evidence acquisition may write explicitly authorized artifact files, but never canonical records.

Extend exact review manifests to include:

- Target entity type, exact operation, baseline/parent UUIDs and local execution IDs, target field snapshots and creation basis.
- Generation resolution basis, correspondence revision/hash and parent relationship/range snapshot.
- Exact offering, catalogue, compatibility-rule, specification and feature-mapping revisions involved in the operation.
- Complete supporting evidence-set hashes, assertion references, actual extractor/rule versions and review findings.
- Expected target state or absence and a deterministic full SHA-256 manifest hash.

At execution, verify parent activity and relationships, generation applicability, correspondence, target preconditions, evidence integrity and reviewed revision bindings. Material changes abort as stale. Never re-plan and execute a substitute under old authorization. An unrelated new Generation does not invalidate an explicit unchanged correspondence; a new overlapping Generation invalidates a year-only uniqueness premise. Exact idempotent target matches may return no-op only when all relevant content and evidence bindings match.

Persist an audit receipt for every authorized execution attempt that reaches the execution boundary, including create, no-op, stale and rejected domain outcomes. Capture operation/entity type, reviewed manifest, complete evidence references, resolved generation/correspondence, resulting revision identities and operator attribution. New canonical writes and their receipts must commit or roll back together. Infrastructure failures surface as failures, not successful or domain-rejected imports; no receipt can be guaranteed when storage itself fails.

Prefer the existing dedicated single-plan workflow as the starting boundary. Do not extend unsafe population/bootstrap paths or silently bless their existing behavior. Receipt storage for new entity types needs an explicit implementation design; VehicleDefinition-only receipt fields are not a generic evidence model. This decision does not approve batch execution or relaxing ADR-0007.

### 10. Full Specifications UX and accessibility

Preserve the Generation configurator and its URLs/selection behavior. Do not add transmission or package dimensions there.

On Full Specifications, use this order:

1. Transmission selection where recorded alternatives exist; display one recorded offering as text with coverage qualification where needed.
2. Factory package selection, with individual factory options distinguishable and standard equipment shown separately.
3. Compatibility status and concise explanations.
4. Specifications and measurement reports reflecting established applicability.

Multiple transmissions must not silently default to a particular alternative. No packages selected means no packages selected in this view, not a proven factory build with no optional equipment. An empty catalogue means not recorded, not unavailable.

Changing transmission retains selected packages for review and explains any resulting conflicts. Offer explicit corrective actions; never silently alter selections. Baseline fields remain visible for incompatible/unverified selections while unsupported conditional claims are withheld or clearly unresolved.

Keep many-option interfaces manageable with category groups, collapsed optional details, a selected-items summary and search when useful. Do not expand a combinatorial matrix. Show manufacturer labels/codes and availability reasons without exposing ingestion mechanics as ordinary user controls.

Use Django templates and server-side selection validation, GET-based shareable state, explicit submit/reset behavior and no-JavaScript fallback. URLs identify the baseline plus subordinate selections; they do not change the canonical baseline URL identity. Revision-dependent selections must retain their revision context or report that the historical context is unavailable; do not silently reinterpret old links against a new catalogue.

Minimal progressive JavaScript may refresh dependent content. Preserve keyboard order and focus; use labelled controls, fieldsets/legends for groups, text explanations for disabled/unavailable choices, and concise live announcements for updated status. Do not rely on color alone. Validate duplicate, malformed, foreign-baseline and incompatible query selections on the server; GET browsing must not write canonical data.

### 11. Contract versioning and migration implications

Extend source assertions, interpretations and candidate contracts with structured correspondence, offering alternatives, availability, compatibility, conditional specifications and feature mappings. Extraction preserves source language; normalization owns classification and rules; candidates remain transient until reviewed promotion.

`TransmissionDetails` and `PackageOrOption` are reusable starting structures, not sufficient final contracts. A singular transmission projection and free-text availability do not encode alternative inventories or compatibility. Keep raw source identity and all document-specific provenance when aggregating several alternatives under one baseline. Publisher ID alone is insufficient as a document lineage key.

Use semantic versioning based on actual compatibility. Optional descriptive additions may use a minor contract version. Changed meanings, cardinality or required authorization semantics require a breaking version or a distinct explicitly supported artifact type. Consumers must reject unsupported execution semantics rather than ignore unknown safety-critical fields. Exact numeric versions are assigned in implementation specifications, with reader/writer compatibility tests.

New overlap-aware execution manifests must carry validated resolution evidence. Legacy manifests remain readable for inspection. Continued execution is allowed only where their supported semantics and stale checks prove the original unambiguous plan; otherwise require a new review manifest and authorization. Never attach correspondence or offerings to an old authorization by inference.

Future persistence requires additive reviewed schema migrations. Preserve committed migrations, integer internal PKs, permanent UUIDs, immutable slugs and protected historical relationships. Do not infer offering rows in a schema migration, overwrite development data or perform automatic evidence backfills. Data enrichment is separately reviewed and authorized, with its own receipts. No migrations are created or run for this documentation task.

### 12. Existing Toyota and Volkswagen compatibility

Existing baselines, public URLs, Generation counts and selection funnels remain usable with zero offering records. Adding alternatives must not split, merge, rename or re-slug VehicleDefinitions. Existing measurements retain conditions and report semantics. Historical receipts retain their original meaning and are not rewritten to claim richer evidence.

Existing Toyota transmission strings are evidence to review, not permission to populate all possible alternatives. Missing Toyota values and a single transmission per retained fixture row do not establish historical exclusivity. Apply the same rule to Volkswagen: do not infer packages or transmissions from another model/year, labels or current drivetrain fields.

Legacy intermediate artifacts retain explicit reader support and round-trip preservation where specified. Legacy field absence means not recorded; do not synthesize empty inventories marked complete. Upgrade actual extraction provenance rather than copying Toyota metadata into other manufacturers' artifacts.

## Implementation sequencing and acceptance tests

These are three separate future milestones. Each needs its own approved implementation task, bounded migration/data authorization and verified completion record. No RA task numbers are allocated here.

### Milestone 1: Overlapping-generation resolution and ingestion protocol

Implement reviewed correspondence contracts, normalization/resolution, exact manifest bindings, stale checks and receipt linkage. Keep acquisition and semantic review separate from authorized canonical writes. Correct zero-write planning and exact-plan boundaries on any path used by this milestone; do not broaden into unrelated population refactoring.

Acceptance tests:

1. Two active Generations legitimately cover one year; explicit source-backed correspondences resolve each independently without modifying ranges.
2. Wrangler/2018 evidence without sufficient correspondence remains review-required; caller generation names/IDs cannot bypass it. Production cases use retained authoritative evidence; synthetic fixtures test protocol mechanics only.
3. Ambiguous, conflicting, inactive, cross-model, out-of-range and wrong-market mappings block promotion; failed explicit correspondence never falls back silently.
4. Source revision, mapping revision or parent relationship changes invalidate authorization. New overlap invalidates year-only resolution; unrelated taxonomy does not invalidate a valid explicit correspondence.
5. Empty-namespace planning changes no canonical tables. Mapping review is not execution permission. Tampered manifests fail; receipt failure rolls back writes; exact repeats are auditable no-ops.
6. Existing unambiguous Toyota/Volkswagen planning and legacy inspection remain supported without baseline identity changes. Unsafe legacy execution requires fresh review.

### Milestone 2: Transmission persistence and Full Specifications selection

Implement reviewed transmission descriptions/offerings, conditional specification primitives, evidence persistence and authorized enrichment. Add Full Specifications selection without changing the Generation funnel. Enable only conditions supported by this milestone's contract; package-dependent effects wait for Milestone 3.

Acceptance tests:

1. Two evidenced transmissions belong to one unchanged VehicleDefinition UUID/slug. No duplicate baseline or Generation selector choice is created.
2. Wrong year, trim, engine, drivetrain, market, baseline and unresolved body restrictions cannot leak availability. Reused codes do not merge distinct transmissions.
3. Partial or absent inventories remain qualified; one recorded transmission does not imply exclusivity. Legacy Toyota/Volkswagen records render without invented offerings.
4. Selected transmission changes only evidence-supported applicable specifications. Missing selection, conflicting assertions and changed source revisions do not produce definitive conditional values.
5. GET deep links, invalid selections, no-JavaScript submit/reset, keyboard/focus behavior and announcements work. Generation configurator regressions remain unchanged.
6. Authorized offering writes have exact manifest/evidence binding, stale-state checks, receipts and transaction rollback; backfills require separate authorization.

### Milestone 3: Factory package catalogue, compatibility and conditional specifications

Implement revisioned factory package/option offerings, equipment classification, complete-selection evaluation, conditional specification effects and evidence-backed physical-feature mappings. Add controls after transmission; preserve separate measurement report semantics.

Acceptance tests:

1. Trims, factory packages, options, standard equipment, dealer accessories and owner modifications remain distinct. Reused names/codes and midyear revisions preserve historical identity and evidence.
2. Multiple packages can be selected when coexistence is established. All-of/any-of prerequisites, exclusions, transmission requirements, replacements and higher-order restrictions are evaluated together.
3. Individually available or pairwise-compatible items without whole-selection proof remain unverified. Contradictory findings and incomplete rule sets never become supported by default.
4. Transmission changes expose conflicts without silently changing packages. Malformed/foreign selections fail safely; large catalogues remain keyboard-usable with no-JavaScript fallback.
5. Package/transmission-dependent values appear only with established applicability; no unsourced arithmetic or conflict overwriting occurs.
6. Physical states require scoped evidence. Unchecked packages do not prove absence; unknown/conflicting states retain unestablished measurement applicability. Generation-wide and independent reports remain intact.
7. Revised source/rule/feature mappings stale prior authorization; authorized publication is atomic with receipts. Historical links and legacy baselines are not silently reinterpreted.

For implementation milestones, run required system checks, migration-consistency checks and relevant/full tests under `venv/py313/bin/python`, using isolated test databases and temporary artifacts/media. Add security tests for rule parsing, selection validation, source text escaping and authorization boundaries. Actual commands/results belong in each future task record; none are claimed here.

## Required design and documentation amendments

The following is a change plan, not a claim that the listed designs have been amended. Historical accepted ADRs and completed implementation records remain intact; future amendments must cite this accepted decision. Acceptance is recorded in the architecture index in `CURRENT_STATE.md` and in `CHANGELOG.md`; the three implementation milestones remain future work requiring separate authorization.

| Document | Required coordinated amendment |
|---|---|
| [RA-010](../designs/RA-010-Reference-Ingestion-Source-Mapping-Architecture.md) | Baseline versus subordinate alternatives; evidence-backed generation resolution; factory equipment scope and preserved two-tier boundaries |
| [RA-011](../designs/RA-011-Ingestion-Schema-Intermediate-Serialization-Design.md) | Versioned correspondence/offerings, revision identity, structured availability/compatibility, conditional values and document-specific provenance; explicit legacy compatibility matrix |
| [RA-014](../designs/RA-014-Source-Assertion-Normalization-Mapping-Architecture.md) | Source-supported generation mapping, transmission normalization, factory classification, applicability and rule provenance; no context laundering |
| [RA-016](../designs/RA-016-Candidate-Configuration-Construction-Aggregation-Architecture.md) | Preserve source rows while aggregating alternatives under one baseline; explicit coexistence and unresolved restrictions; richer candidate projections |
| [RA-018](../designs/RA-018-Canonical-Reference-Matching-Import-Architecture.md) | Parent resolution bases, overlap correspondence, baseline matching versus offering enrichment and stale preconditions |
| [RA-020](../designs/RA-020-Trim-Grade-Market-Applicability-Source-Normalization-Architecture.md) | Cite narrow ADR-0005 supersession; catalogue/grade/standard/accessory distinction, scoped availability and compatibility evidence |
| [RA-022](../designs/RA-022-Production-Manufacturer-Evidence-Acquisition-Orchestration-Architecture.md) | Acquisition of restrictions, section identity, revisions and cross-document correspondence; no silent broad application |
| [RA-024](../designs/RA-024-Canonical-Reference-Import-Execution-Execution-Provenance-Workflow-Architecture.md) | New manifest operations/versions, exact resolution/evidence/revision authorization, zero-write planning, stale checks and receipts for new entities |
| [RA-025](../designs/RA-025-Production-Manufacturer-Extraction-Review-Adjudication-Architecture.md) | Review findings for correspondence/offerings; preserve grade-adjudication limits and representability blockers |
| [RA-042](../designs/RA-042-Measurements-Domain-Foundation-Architecture.md) | Evidence-backed physical-feature mapping/evaluation bridge; preserve Generation anchor, result units, AND conditions and independent reports |
| New Full Specifications design | Transmission then factory packages/options, three compatibility states, conditional display, shareable revision-aware selections and accessibility; unchanged Generation funnel |
| `docs/implementation/CURRENT_STATE.md` | Record architectural acceptance separately from implementation. Update implementation state only after verified work; acceptance alone does not implement future models, selectors or milestones |
| `CHANGELOG.md` and future task records | Record actual documentation/implementation changes with verification; preserve historical RA-012/015/017/019/021/023/024/026 records rather than rewriting completed history |

No historical accepted ADR is edited in place. A separate ADR amendment is unnecessary merely to restate this accepted decision; any future departure from these boundaries requires its own explicit decision. Exact Django schema, executable artifact versions and receipt storage design remain implementation specifications for review, not implicit authorizations.

## Rationale

Separating baselines from selectable offerings preserves stable archive identities and keeps the Generation funnel manageable. Explicit correspondence resolves real overlaps without corrupting historical ranges. Revision-scoped evidence prevents availability, compatibility and specifications from being inferred from labels, incomplete lists or caller selections. Physical-feature mappings connect factory equipment to measurements without duplicating sales taxonomy in Measurements.

## Consequences

### Positive

- Stable Toyota/Volkswagen identities and URLs coexist with incremental, evidence-backed enrichment.
- Future overlapping models use a general protocol rather than model-specific year hacks.
- Full Specifications can describe supported alternatives without multiplying baselines or claiming an individual vehicle build.
- Unknown compatibility and historical evidence remain visible and auditable.

### Costs and limitations

- New persistence, contracts, reviewed mappings and audit support require separately approved implementation and migrations.
- Complete availability/compatibility evidence may be absent; the interface must tolerate partial catalogues and unverified selections.
- Historical source reconstruction, conditional specification reconciliation and accessibility verification require explicit work; this document proves none of them complete.
- This direction does not resolve the broader engine/powertrain identity question, add body schema, approve arbitrary factory-build enumeration or implement measurement verification.

## Alternatives considered

- **Shorten overlapping generation ranges**: Rejected because it changes historical applicability to satisfy implementation convenience.
- **Use caller generation IDs or grade adjudication as overrides**: Rejected because neither establishes source correspondence.
- **Create VehicleDefinitions per transmission/package permutation**: Rejected because it changes baseline identity and expands the Generation funnel.
- **Keep all factory packages exclusively outside Reference**: Superseded narrowly because manufacturer-offered equipment and its engineering applicability are required subordinate factory reference data. Accessories/modifications remain separate.
- **Reuse Measurements as the equipment catalogue or factory specification store**: Rejected because physical feature conditions and independent reports have different responsibilities.
- **Assume compatibility unless forbidden**: Rejected because incomplete rules do not establish coexistence.
- **Silently enrich old manifests or backfill from labels**: Rejected because reviewed evidence and exact authorization cannot be inferred.
