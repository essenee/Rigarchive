# W2 Phase A: Validation and phased implementation plan

**Status**: Approved architecture contracts, incorporating director-approved Phase A corrections on 2026-11-04. Not implemented; no migration or canonical-write authorization.

Contracts: [ADR-0011](../ADR/ADR-0011-Factory-Body-Configuration-Identity.md), [domain](W2-Full-Specifications-Domain-Architecture.md), [properties/applicability](W2-Specification-Property-Applicability-Contract.md), [enrichment/publication](W2-Enrichment-Publication-Contract.md).

## 1. Expressiveness validation

These examples validate contracts, not source acquisition, factory availability, production boundaries or permission to create records. No historical van dimensional status is assigned without manufacturer evidence. Evidence hypotheses remain drafts until reviewed.

| Case | Contract result / required test |
| --- | --- |
| Existing Jeep JK714 and JL715 | Enrichment targets exact existing UUIDs; generation correspondence/evidence remain distinct; same Sport/engine words cannot join sources automatically. No body backfill or canonical identity change. |
| Jeep transmissions | Two explicitly supported transmissions can enrich one baseline; incomplete alternative inventory remains partial. No offering/ratio is asserted by this architecture document. |
| Jeep equipment/release | Brochure-controlled factory assignments; retained Mopar release supports reviewed identity only. No accessory catalogue ingestion or accessory effects. |
| Transit same wheelbase, different length | Same wheelbase designation plus Long versus Extended body can produce distinct body UUIDs and body-aware baseline keys/slugs. Roof, body style and independent series remain separately queryable. |
| Transit passenger/cargo | Manufacturer body style is a discriminator, not commercial-use intent. A cargo source cannot establish passenger availability; no passenger/cargo cross-product. |
| Sprinter standard/extended | Wheelbase, length, roof and series independently bind identity. A manufacturer label combining “170” and “extended” must be parsed into separately evidenced dimensions, not treated as longer wheelbase. |
| Chevrolet Express / GMC Savana | Historical van profile can preserve evidenced body/series/wheelbase while roof or length is not differentiated, inapplicable or unknown as established by the source. Related brands are not automatically equivalent. |
| Ford Econoline / E-Series | Conventional-roof publication need not be relabelled low roof; historical names require scoped source identity, not inferred continuity or year coverage. Cutaway may have inapplicable roof/complete-body length. |
| Dodge Ram Van / B-Series | Retain historical nomenclature and source identity; do not infer body length from series/code or invent modern roof distinctions. |
| Incomplete chassis | Not-applicable roof/length omitted in presentation if evidenced; unknown is not not-applicable. Exact manufacturer configuration still bears identity. |
| Future pickup/other profile | General FK/profile discriminator contains no van-only matching assumptions. Cab/bed schema and rules remain undefined/deferred. |

Supporting expressiveness references from prior W2 review (not retained acquisition artifacts or population authority): [Ford 2026 technical specifications](https://www.fromtheroad.ford.com/content/dam/fordmediasite/us/en/library/2026/specs/2026_Ford_Transit_Specs.pdf), body and dimension sections; [Mercedes-Benz MY2024 brochure](https://www.mbvans.com/content/dam/mb-vans/us/brochures/MY24_Brochure_VAN_Final_11524.pdf), Sprinter Cargo section. Historical family rows deliberately establish no actual manufacturer boundaries, values or missingness findings.

## 2. Future milestones and acceptance gates

### B1 — Property, evidence and enrichment contract primitives (implemented 2026-11-04)

Implement explicit serializers/validators and controlled initial definitions/units for reviewed scope, plus isolated fixtures. No new development data or publication yet. Acceptance: duplicate-key rejection; canonical hashes/decimals; units/method distinctions; document-qualified duplicate local IDs; original evidence/order preserved; zero and all missing states; predicate bounds/type errors; inventory accounting; unknown versions rejected. Existing Candidate v2 and manifest hashes/readers unchanged. No comprehensive engine entity or new Django application.

### B2 — Specification persistence and exact catalogue publication

Separately authorize additive migrations, persistent evidence/definition/assertion/catalogue models and dedicated enrichment service/command. Acceptance: exact baseline/revision bindings; coherent partial snapshots; no latest-member adoption; zero writes across all affected tables during planning; exact tampering rejection; stale evidence/parents/dependencies/current leaf; first-revision/successor concurrency; atomic rollback on receipt failure; durable domain attempt receipts where possible; idempotent no-op receipts; historical snapshot replay; no old record/receipt alteration. Database deployment requires separately verified preservation and authorization; no automatic backfill.

### B3 — ADR-0010 Milestone 2: transmission persistence and presentation

Persist descriptions/offerings and conditional facts; introduce only transmission-supported selection semantics. Acceptance: two transmissions share unchanged baseline; scoped codes do not merge; wrong market/year/engine/trim/body/date cannot leak; partial inventories labelled; only sourced conditional values; invalid/foreign selections rejected; GET/no-JavaScript, keyboard/focus and announcements; Generation configurator unchanged; Toyota/VW no fabricated offerings.

### B4 — ADR-0010 Milestone 3: equipment, compatibility and feature mappings

Persist items/contents/offerings/rules and physical mappings, selection controls after transmission. Acceptance: brochure package/option/accessory distinctions and explicit exceptions; absent-brochure accessories categorically excluded; accessory effects rejected; package cycles blocked; standardness scoped; all/any requirements and higher-order incompatibility; independently available/pairwise-supported sets remain unverified without whole-set evidence; no unsourced capacities/deltas; physical-state conflicts/unknowns; unchanged Generation measurements and reports.

### B5 — Body/series identity integration (separately authorized)

Under accepted ADR-0011, and only after separate B5 authorization, implement van profile, reviewed identity/evidence publication, candidate v3 and import manifest 3.0. Body/series curation is an explicit separately reviewed data operation; define its exact manifest/receipt contract before any such write. This milestone may proceed alongside B2 but does not block baseline-preserving Jeep enrichment. Acceptance: same-wheelbase/different-length distinction; independent series/grade; body-code aliases versus genuine distinctions; unknown blocks rather than merges; historical/cutaway missingness; no synthesized combinations; legacy unassessed collision blocks; new body create basis; transaction-safe assessed identity uniqueness; immutable old slugs/UUIDs/URLs; overlength new slug blocks; old executors refuse whole invocation before mutation; manifests/receipts pin all bindings. Preserve Wrangler trim handling.

### B6 — Bounded authentic enrichment and coverage verification

Separately authorize acquisition if needed, semantic extraction and reviewed publications for exact existing Jeep baselines first. Account for every relevant acquired source segment, unresolved extraction and exclusions; no completeness claim for missing sources. Additional van/historical baselines require separately evidenced curation and body-aware implementation. Acceptance: catalogue reproduced from retained bytes; conflicts visible; exact manifests authorized; evidence/database preservation; no adjacent-year/trim inference; coverage qualified independently from published status.

For implementation: approved Python 3.13 environment; isolated test databases and temporary media/acquisition storage with deletion guards. Run targeted/full Django tests, system and migration-consistency checks; add selection/rule security and UI tests where relevant. Phase A does not claim these implementation checks ran.

## 3. Required documentation coordination

| Existing document | Amendment when implementing approved scope |
| --- | --- |
| RA-010 | Manufacturer facts versus enrichment; body identity versus subordinate offerings; equipment scope unchanged |
| RA-011 | Typed values, qualified persistent evidence, candidate v3, separate enrichment/version compatibility matrix |
| RA-014 | Controlled property mapping, unit/method provenance, unresolved restrictions, source-specific profiles |
| RA-016 | Separate enrichment drafts and source-supported body/series construction; no Cartesian generation |
| RA-018 | Body-aware semantic matching, legacy-unassessed collisions and factory identity create basis |
| RA-020 | Independent series/grade and body taxonomy; brochure equipment classification |
| RA-022/025 | Corpus/visual extraction inventory, truthful extraction review and unsupported restrictions |
| RA-024 | Separate exact publication operation, dependency snapshots, concurrency and receipt outcomes |
| RA-042 | Reviewed physical mappings only; no change to Generation-anchored reports or manufacturer/empirical separation |
| INGESTION_PROTOCOL | Add operational commands only after implementation; current Phase A cross-reference is design-only |

Do not rewrite completed task records or accepted historical ADRs. Approved contract documents supplement older designs without claiming their future behavior already exists. Historical architecture decisions remain preserved; ADR-0011 records the explicit narrow supersession.

## 4. Approved exact rules and explicitly deferred work

The director approved the focused review and exact corrections on 2026-11-04. Candidate v3/schema 3.0.0, body-aware manifest 3.0, enrichment/publication v1 and predicate 1.0 are approved future boundaries. Full-UUID body/series suffixes and 180-character overflow rejection apply only to new assessed baselines. Domain §8 fixes canonical manufacturer-scoped identity preimages and cross-profile safeguards. Properties §7 and Publication §9 are closed normative schemas, not optional examples. Selection knownness is independent for transmission/equipment, at most one transmission is permitted, and duplicate/foreign/unavailable inputs fail strictly. Predicate budgets use root depth 1 and structural operator-node reservation across the whole requested evaluation. Complete immutable catalogue snapshots and exact-current-only replay are mandatory. Original legacy/raw numeric artifacts remain byte/hash preserved; new normalized quantities use canonical decimals.

No director-level contradiction remains open in these rules. B1 implementation was separately authorized and supplies serializers/validators and isolated fixtures only. Add golden preimages and full-member hash vectors, all closed-schema rejection cases, independent selection/unknown cases, boundary/aggregate-budget cases, catalogue carry-forward/removal invariants and exact-current replay validation fixtures. Preserve Candidate v2/manifest 2.0 readers, hashes and baseline semantics; do not route body/enrichment artifacts into existing executors. Raw legacy floats must remain referenced or verbatim, not silently reserialized as new decimals.

Body/series curation publication contracts (exact manifests, authorization and receipts) remain explicitly deferred to B5 before ANY such write; neither enrichment v1 nor generation correspondence is a substitute. Manufacturer-specific controlled identity scope/designation tokens and equivalences require evidence-backed curation, not guessed defaults. Initial seeds/index names/field widths are implementation details subject to these contracts, not permission for population. Pickup/bed profiles, accessory-dependent evaluation, unsupported derived ratings and permanent measurement protocols remain deferred.

B1 is delivered; the next milestone is separately authorized B2 persistence/publication work, with its own migration, preservation and write-authorization gates. Body/series curation publication remains B5, not an implicit part of B2.

## 5. Phase A documentation verification

2026-11-04: inspected the actual model, intermediate contract, candidate, generation-resolution, baseline-execution and Full Specifications presentation boundaries and reconciled the permanent protocol/W1 closeout. Documentation validation resolved 38 relative links across the five new documents and three updated index/protocol/changelog files; fenced Markdown was balanced, new-document whitespace checks and repository `git diff --check` passed. The development database and all ten pre-existing historical ADRs matched pre-task SHA-256 fingerprints. No application code, migrations, UI, acquisition files or canonical records were changed. Existing unrelated working-tree changes remain preserved. No Django tests/checks or migrations were run for this documentation-only task; implementation acceptance tests above are proposed, not executed. No staging, commit, push or branch change. That earlier checkpoint preceded the director-approved corrections recorded below; no implementation was performed.


## 6. Director-approved correction checkpoint (2026-11-04)

Incorporated the approved final-review corrections without reopening the architecture. ADR-0011 is accepted architecture; all exact version boundaries, semantic identity/normalization/missingness preimages, profile equivalence safeguards, closed value/evidence/predicate/member/publication shapes, independent selection status, complexity accounting and deterministic current-only replay are now normative. Specification catalogue revisions carry complete current-state membership with exact pins and four independent coverage reports. Original source text and legacy numeric artifacts retain original hashes. Body/series curation publication schemas remain explicitly B5 work.

Documentation verification checks local cross-references, JSON examples, closed-schema consistency, supersession wording, legacy compatibility and whitespace. Protected file fingerprints include application code, migrations, retained evidence, W1 records/artifacts, the development database and historical ADR-0001 through ADR-0010. No Django tests/migrations or database writes are part of this documentation task. B1 remains separately authorized serializers/validators work only; no models, executors or UI are implemented here.


Final correction verification: 33 local relative links resolved; the normative JSON preimage example parsed successfully; canonical decimal/replay/version consistency checks and `git diff --check` passed. All 480 protected pre-task files matched SHA-256 fingerprints, including the development database, retained source/evidence artifacts, application code/migrations and ADR-0001–0010. Eight documentation files changed in this task (ADR-0011, four W2 designs, CURRENT_STATE, INGESTION_PROTOCOL, CHANGELOG). No remaining concrete contradiction was identified; B5 curation publication contracts remain intentionally deferred. No application test pass is claimed from documentation checks.


## 7. B1 implementation checkpoint (2026-11-04)

B1 pure contracts are implemented under `reference/specifications/`; see the [task record](../../implementation/tasks/W2-B1-full-specifications-contract-primitives.md) for the exact test results and preservation qualifications. Director clarification binds each categorical qualifier to an exact categorical definition revision/hash, null for other kinds; Publication §9 and Properties §7 are updated. Existing baseline contracts are unchanged. B2 persistence/publication and B5 body/series curation publication contracts remain future separately authorized work. Pure validation against supplied snapshots is not live authorization or database execution.
