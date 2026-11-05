# ADR-0011: Factory body configuration identity

- **Status**: Accepted
- **Date**: 2026-11-04
- **Approval**: Accepted by the project director through the W2 Phase A contract-corrections instruction on 2026-11-04. Architecture/documentation approval only; no implementation or database-write authorization.
- **Supersession**: Narrow extension of ADR-0010 Decision 2 as specified below; historical ADRs are unchanged.
- **Contracts**: [Domain architecture](../designs/W2-Full-Specifications-Domain-Architecture.md), [values/applicability](../designs/W2-Specification-Property-Applicability-Contract.md), [enrichment/publication](../designs/W2-Enrichment-Publication-Contract.md), [implementation plan](../designs/W2-Phase-A-Implementation-Plan.md).

## Concrete incompatibility

VehicleDefinition currently identifies generation/year/trim/engine/drivetrain/market and generates its initial slug from year/trim/engine/drivetrain/market. Manufacturer-distinct van bodies can share that tuple. The only current database uniqueness constraint is Generation plus slug; suffixing a collision would not establish correct semantic identity. Treating wheelbase, body length or roof as optional descriptive specifications would merge distinct factory baselines.

## Exact supersession

ADR-0010 Decision 2 states:

> Continue handling two-door/four-door distinctions through approved, evidence-backed trim normalization. This decision does not authorize a new body-identity model or arbitrary body suffixes in trim strings. Where existing approved normalization cannot distinguish demonstrated factory baselines, block that case and seek a separately scoped decision.

This decision supersedes only the prohibition/non-authorization of a body-identity model for the **reviewed van profile**. It supplies that separately scoped decision: a manufacturer-established van factory-body distinction participates in baseline identity through FactoryBodyConfiguration. It does not supersede the approved two-door/four-door Wrangler trim normalization, authorize arbitrary trim suffixes, or silently reclassify existing baselines. ADR-0010's transmission/package subordination, Generation funnel, evidence, compatibility, authorization and Measurements rules remain in force. Its narrow supersession of ADR-0005 remains exactly as recorded there.

## Decision

FactoryBodyConfiguration is a general Reference concept. Its initial profile is `van/1.0`, unrelated to commercial intent, size or modern roof conventions. Cargo, passenger, crew, cutaway and incomplete-chassis manufacturer configurations may use the profile. It accommodates historical conventional-roof vans without fabricated length/roof labels.

Each profile instance separately represents manufacturer body style/configuration, wheelbase designation, body-length designation, roof-height designation and body code where supplied. Series and grade remain separate when distinguished by the manufacturer. A dimension bears identity only where reviewed manufacturer evidence establishes a factory distinction. Labels are not numeric engineering measurements; no wheelbase-to-length inference or Cartesian construction is allowed.

A future VehicleDefinition may reference exactly one protected body identity and optional independent series identity. These are baseline discriminators, not selectable alternatives. Existing trim taxonomy remains the grade dimension and may represent series where the manufacturer actually uses series as that dimension. A separate series relationship must not duplicate an identical trim assertion.

Every body dimension has explicit `established`, `not_applicable`, `not_differentiated`, or `unknown` status. Unknown is not a wildcard or permission to merge. Evidence-supported not-differentiated/inapplicable dimensions are omitted from public labels. Unsupported roof/length values are not required for historical vans or incomplete chassis. Body code may be unknown without blocking an otherwise fully evidenced semantic identity; an unexplained code difference or missing evidenced distinguishing dimension blocks resolution.

Preserve all existing VehicleDefinition UUIDs, slugs and URLs. Legacy null body/series relationships mean unassessed, not a known universal body. No automatic reassignment, split, backfill or deduplication. Candidates potentially matching an unassessed existing baseline require review before another body-specific baseline is created. New van identities require the versioned body-aware matching and create-basis contract; old executors must reject those inputs rather than ignore new identity dimensions.

## Consequences and boundaries

Use additive schema changes only after separately authorized implementation. No models, migrations, ingestion or data changes are delivered by Phase A. New body-aware slugs use explicit stable body/series identity suffixes without altering old slugs. No sequential/random collision repair is a matching strategy.

The general identity infrastructure dispatches on a versioned body profile and stable body UUID; it does not assume all profiles have roofs/wheelbases. Pickup cab/bed and other profiles are future extensions, not designed here. No general body-profile plugin framework is required initially.

Acceptance requires independent dimension queries; distinct same-wheelbase bodies; historical missing-value behavior; no inferred combinations; stale body evidence checks; unchanged existing identities/receipts/navigation; and exact authorization for any future parent/body curation or baseline import. See the implementation plan for executable acceptance cases.

## Approved exact contract refinements

Domain §8 fixes the manufacturer-scoped semantic identity preimages, explicit missingness tokens, controlled-token normalization and cross-profile-version equivalence safeguards. UUIDs, display labels, provenance and serialization profile versions never manufacture a new semantic identity. Full body/series UUID suffixes apply only to new assessed records; full slug length over 180 characters blocks, without truncation or retry suffixes.

Candidate v3/schema 3.0.0 and body-aware import manifest 3.0 are approved future boundaries. Enrichment/publication v1 and predicate language 1.0 are separate, explicitly versioned contracts. Existing Candidate v2/manifest 2.0 and W1 Jeep records remain unchanged. Body/series curation publication manifests and receipts are explicitly deferred to B5; current approval authorizes no such writes. Pickup/bed profiles remain undesigned.
