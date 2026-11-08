# ADR-0012 — Structured powertrain identity and hybrid terminology

**Created:** 2026-11-07
**Status:** Accepted
**Approval:** Human director instructions approving JL-D19, JL-D20 and hybrid terminology. Documentation approval only. Implementation, migrations, backfill and imports require separate authorization.
**Related decisions:** [ADR-0001](ADR-0001-Entity-Identity-Strategy.md), [ADR-0002](ADR-0002-Immutable-Automatic-Slugs.md), [ADR-0010](ADR-0010-Generation-Correspondence-Selectable-Factory-Alternatives.md), [ADR-0011](ADR-0011-Factory-Body-Configuration-Identity.md).

## Context and current implementation

VehicleDefinition currently persists generation, year, trim, free-text engine_name, generic drivetrain and market. Factory-body and series architecture is separately approved by ADR-0011. Candidate v1/v2 EngineDetails carries optional code, displacement, cylinders and horsepower in intermediate artifacts. These do not create persisted structured engine identity.

The implemented MY2018 JL Candidate v2 mechanical proof verifies normalized displacement/cylinders against retained engine descriptors and successful peer creation receipts. Its manifest-bound engine_distinction proof is recomputed inside the create transaction. It admits differences in displacement or cylinder count and conservatively leaves equal dimensions unresolved. Candidate v1 retains its legacy drivetrain compatibility rule. This ADR extends future identity architecture beyond those implemented rules.

## JL-D19 — Canonical structured engine attributes

Future VehicleDefinition exposes these manufacturer-neutral, first-class attributes. Names below are the proposed model interface for implementation review.

| Proposed field | Representation and meaning |
|---|---|
| engine_displacement_liters | Nullable positive Decimal quantity in liters for a combustion engine. Preserve the reported precision and source unit in evidence. Zero must not represent unknown or absence of an engine. |
| engine_cylinders | Nullable positive integer. Count is independent of layout. Non-piston powertrains cannot be coerced into a cylinder count. |
| engine_aspiration | Nullable controlled token for established induction classification. |
| fuel_type | Nullable controlled token identifying the supported fuel or energy carrier. Electricity is an energy carrier and does not imply a combustion engine. |
| electrification_type | Nullable controlled token for established electrification classification. |

engine_name remains a human-readable descriptor and compatibility field. Manufacturer technology names remain available as source-specific descriptions. Manufacturer engine codes are optional supporting evidence. Code changes, including California/federal emissions certification codes, cannot independently create canonical distinctions.

### Initial controlled vocabulary

Store lowercase machine values. Domain/application metadata defines presentation labels centrally.

| Dimension | Values and labels |
|---|---|
| Aspiration | naturally_aspirated → Naturally aspirated; turbocharged → Turbocharged; supercharged → Supercharged; twincharged → Twincharged; other → Other |
| Fuel / energy | gasoline → Gasoline; diesel → Diesel |
| Electrification | none → None; mild_hybrid → Mild hybrid (MHEV); hybrid → Hybrid (HEV); plug_in_hybrid → Plug-in hybrid (PHEV) |

Null means unassessed or unknown in the proposed additive model. It must never default to naturally_aspirated, gasoline or none. other requires an established classification outside the vocabulary and explanatory evidence. It must never stand in for missing evidence.

The fuel taxonomy must accommodate electricity, hydrogen and mixed/alternative fuels. The electrification taxonomy must accommodate battery-electric and fuel-cell powertrains. Their final tokens and cross-field applicability rules remain an implementation prerequisite. Hydrogen combustion and hydrogen fuel-cell systems need different applicability even though they share an energy carrier. For vehicles with no combustion engine, displacement, cylinder count and aspiration are inapplicable, with that fact explicitly represented in the eventual applicability contract. Null alone cannot distinguish verified inapplicability from unknown. Do not fabricate combustion values or use numeric zero to represent electric propulsion. Do not authorize such a new baseline until these semantics can be represented safely.

### Canonical comparison

Retain generation, model year, market, trim, drivetrain and any separately authorized body/series identity. Compare the structured engine attributes with explicit evidence and common units.

A verified difference in displacement, cylinder count, aspiration, fuel type or electrification type may establish a mechanical distinction. The relevant candidate and existing-record values must both be supported for that comparison. Conflicting, unknown or inapplicable values cannot be treated as unequal conventional values, wildcards or permission to merge. Other unresolved identity-bearing facts must be surfaced for review before admitting a create.

Equality of displacement and cylinder count does not prove engine equivalence. Matching manufacturer codes or matching display labels do not prove equivalence across applicability scopes. Different codes do not prove distinctness. Complete assessed equality routes to existing-record reconciliation; verified output tuning differences follow JL-D20. Unsupported differences remain review-required.

Retained assertions, source applicability and successful import receipts can establish existing-record premises without changing that record. Where those premises cannot be verified, keep requires_review. Execution independently revalidates the approved structured proof, existing canonical identity, source revision and bytes, and all relevant peers. Changed evidence or canonical premises stale the plan.

### Existing records and additive rollout

Add nullable fields without inferred defaults or automatic label parsing backfill. An unassessed existing baseline is not an established universal engine variant. Its PK, UUID, slug, history and current attributes remain unchanged. Any evidence-based assignment requires separately reviewed backfill or correction authorization and audit linkage. This task authorizes no data migration.

No automatic merge, split, relabel, deactivation or replacement of existing baselines is permitted. Initially, coexistence with legacy rows requires explicit duplicate and uncertain-overlap review. A schema migration must not adjudicate historical source disagreements.

### Serialization, plans and slugs

Candidate v1 and v2 retain their original versions, validators, serialization and digest semantics. A v2 artifact without the new dimensions does not implicitly assert their values. The currently implemented engine proof remains readable and retains its conservative meaning. Candidate v1 keeps its existing drivetrain compatibility behavior for its established legacy scope. Legacy readers/executors cannot consume new engine-aware identity payloads by dropping unfamiliar fields. Such payloads require their own approved version dispatch and fail-closed execution.

Implementation must define an explicitly versioned candidate/plan/manifest path that binds the assessed engine values, their missingness/applicability, qualified evidence and peer proof. The existing optional engine_distinction proof cannot silently acquire a different meaning under version 1.0. Previously approved candidates, matrices, approvals, manifests and receipts must not be regenerated or reinterpreted. Matrix review must bind the exact new identity semantics and permitted creation bases before execution.

Current slugs include engine_name and omit the new structured dimensions. A real structured distinction can therefore collide with the same display-derived slug. Preserve all existing slugs under ADR-0002 and continue checking occupancy across active and inactive rows. A collision blocks creation until a reviewed deterministic new-record slug contract can represent the distinction. Do not append random or sequential suffixes, rewrite existing URLs or silently merge rows. The slug and semantic identity contract versions must be settled before implementation of affected creates.

## JL-D20 — Factory tuning variants

When standard canonical identity dimensions match, horsepower or torque alone cannot establish another VehicleDefinition. Flag verified tuning differences for review and retain each sourced horsepower/torque pairing, its RPM, units, rating method/standard, applicability and conditions. Do not combine the power from one claim with torque from another claim.

Future Full Specifications can associate multiple verified output figures with one baseline, using the existing sourced assertion/catalogue design. Numerical values remain separate numerical quantities with evidence and qualifiers. A slash-separated display such as 270 / 285 hp is a presentation of alternatives and must not be stored as one numeric value. Only combine compatible units and clearly identified rating contexts in that display. Contradictory claims remain explicitly unresolved. No horsepower or torque persistence is implemented or authorized here.

## Hybrid terminology and presentation

| Stored value | VehicleDescription label | Generation Configurator label |
|---|---|---|
| mild_hybrid | Mild hybrid (MHEV) | MHEV |
| hybrid | Hybrid (HEV) | HEV |
| plug_in_hybrid | Plug-in hybrid (PHEV) | PHEV |
| none | No hybrid label required | Omit electrification abbreviation |
| null | Unknown/unassessed as context requires | No guessed classification; retain uncertainty |

One central controlled-value metadata definition supplies both labels. Templates, JavaScript and services consume it through presentation context. Neither UI text nor manufacturer names establish canonical classification.

For Wrangler JL, eTorque is Jeep's system name and maps to mild_hybrid where applicable evidence supports it. Conventional ESS is stop/start and cannot establish MHEV. Wrangler 4xe maps to plug_in_hybrid. Preserve the technology name separately from the normalized classification.

Illustrative VehicleDescription rendering is “2020 Jeep Wrangler Unlimited Sahara — 3.6L V6 eTorque, Mild hybrid (MHEV)”. Illustrative Configurator rendering is “3.6L V6 · MHEV”. These examples do not assert availability for a particular retained record or authorize renaming it. The current engine_name-based configurator services and VehicleDefinition description remain implemented behavior until separately updated.

## Explicit supersession and compatibility

- Extends ADR-0010's baseline engine-descriptor premise to future structured powertrain identity. Its generation, transmission, equipment and authorization boundaries remain in force.
- Extends RA-018 §9 beyond the implemented displacement/cylinder evidence proof. Its label-only and stale-state safeguards remain.
- Supersedes the engine_name-only engine component of the future W2 vehicle-definition-body/1 semantic preimage for the forthcoming engine-aware path. Existing serialized vehicle-definition-body/1 artifacts retain their original meaning. Define a successor contract before combining assessed body and assessed engine identity. ADR-0011 body/series identities remain intact.
- Extends W2 Full Specifications engine-output treatment with JL-D20 pairing and review rules. Closed W2 schemas cannot accept new fields through undeclared keys.
- ADR-0001 stable identities, ADR-0002 immutable slugs, ADR-0007 authorization/receipts and ADR-0008 category restrictions remain in force.

## Decisions required before implementation

1. Approve Decimal storage precision and normalization/comparison tolerances, including rounded liter labels versus exact displacement measurements.
2. Approve final alternative-fuel/electricity/hydrogen tokens and the explicit unknown/inapplicable representation, including multi-fuel powertrains and non-piston engines.
3. Approve the exact versioned wire contracts, semantic identity preimages and new-record slug rules, coordinated with the already proposed body-aware Candidate v3.
4. Approve migration/backfill/correction scope and how verified field assignments are audited without changing historical receipt content. Newly discovered historical ambiguities need individual review.
5. Approve the display integration scope and the paired-output assertion linkage in the existing closed specifications contracts.

No shared engine entity, new Django application, new source hierarchy or generalized ingestion framework is implied. This ADR records approved direction and its remaining implementation contracts.
