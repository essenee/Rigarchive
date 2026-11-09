RigArchive Project Status Document
Version: 1.3
Last Updated: 2026-11-08
Purpose: Current implementation status and development roadmap

## Configurator default trim selection (2026-11-08)

For a selected model year with more than 10 active configurations, the existing
hub context selects the first trim in its displayed order unless explicit trim or
configuration state already resolves a selection. Invalid/stale parameters retain
their existing error fallback. Lists of 10 or fewer and all-years views retain
their previous behavior. Existing templates render the selection and filtered
third column; native links and progressive JavaScript navigation are unchanged.
`AUTO_SELECT_TRIM_THRESHOLD = 10` is defined in `reference/services.py`.
All 44 focused hub tests, Django system checks and migration consistency checks
passed using `.venv/bin/python` with an isolated in-memory database. No schema,
canonical data or ingestion changes. Task: [configurator default trim](tasks/configurator-default-trim-selection.md).

## MY2020 US Wrangler JL — certified canonical import completed (2026-11-08)

The owner authorized the exact reviewed 49-row Matrix 2.1 digest
`sha256:a624e23a03e47491f86f8a417a86768e91aa8269213101a8d0dff08f1b3c9e0c`.
Fresh pre-execution checks and a consistent verified SQLite backup passed. The
accepted human-approval workflow certified the exact digest/scope, and one durable
model-year transaction freshly planned and created all 49 US MY2020 JL records.
[Execution checkpoint](handoffs/MY2020_JL/canonical_execution_20261108/README.md)
retains approval, backup pin, CLI output, fresh manifests, receipts and reconciliation.

Exactly **49 VehicleDefinitions, PK 828–876, and 49 creation receipts, PK 2932–2980**,
were added. Current totals are **861 VehicleDefinitions, 2,980 receipts and 64
correspondences**. All new records belong to existing active Wrangler JL Generation
PK 32 / UUID `38d3c3ac-f825-4406-abb5-c2d12b9129a4`, with model-code coverage
JLJL72 12, JLJS72 3, JLJL74 18, JLJP74 12 and JLJS74 4. All 60 approved human
classification decisions, 43 approved declaration revisions, six EC3 sourced
identities and three Unlimited High Altitude names/Sahara-family provenance remain
preserved in their exact candidate/source lineage.

Execution used only permitted bases: one first representation, 20 source-established
grades and 28 mechanical distinctions. Actual execution manifests record evolving
namespace counts 0–48; old standalone snapshot manifests were not executed unchanged.
All new UUIDs/slugs, ten target fields, parent FKs, resolution 1.1, engine proof 2.0,
source/candidate/approval/published-mapping bindings and Matrix receipt links verify.
Read-only reconciliation confirms all 49 rows complete.

Every preexisting row in every application table, including all original 812
VehicleDefinitions, historical receipts and all 64 correspondence revisions, matches
the consistent pre-import backup. Only 49 definitions, 49 receipts and normal
sequence advances were added. Schema/migrations and all 1,348 prior MY2020 artifacts
are unchanged. SQLite integrity/foreign keys, Django checks and 157 isolated focused
tests passed. An independent verifier's receipt-accessor error was corrected using
read-only inspection; no import retry or canonical data/scope deviation occurred.

The [published correspondence checkpoint](handoffs/MY2020_JL/generation_publication_20261108/README.md)
and [final planning package](handoffs/MY2020_JL/final_planning_20261108/README.md)
remain preserved historical stages. The planning package's then-pending approval/
execution status is superseded by this certified execution record. No backfill,
correspondence revision, application/contract change, migration, other-year import,
commit or push occurred. No work remains for this exact MY2020 import task.

## MY2019 JL canonical import — certified and completed (2026-11-08)

The owner authorized the exact reviewed 19-row Matrix 2.1 after conditional gates.
All gates passed; the accepted approval workflow certified Matrix digest
`sha256:d8f11301e230b8485dfd2d15c0b9342aaa0cc778aa7418052ce8da7b10cf6896`.
The [execution record](handoffs/MY2019_JL/director_review/canonical_execution_20261108/README.md)
retains the approval, verified consistent pre-import backup, CLI logs, fresh
per-row manifests, receipts and read-only reconciliation.

One accepted model-year transaction created exactly 19 active US MY2019 JL
VehicleDefinitions, PK 809–827, and 19 receipts, PK 2862–2880. All resolve to
Generation PK 32 / UUID `38d3c3ac-f825-4406-abb5-c2d12b9129a4` through the five
existing published mappings. MY2019 completion totals were **812 VehicleDefinitions, 2,880
receipts, 13 correspondences**. The six two-door/thirteen Unlimited offerings
retain ten approved ERC human-adjudicated tuples and nine original EC3 tuples.
Each row was freshly planned inside the transaction using only its Matrix-permitted
creation bases; old standalone snapshot plans were not executed sequentially.

Post-import reconciliation verifies all 19 complete, deterministic slugs, unique
UUIDs, ten target fields and exact resolution 1.1 / engine proof 2.0 / candidate /
evidence / correspondence / receipt / Matrix bindings. Every preexisting row in
every application table remains unchanged versus backup; only 19 definitions,
19 receipts and their normal sequence advances were added. Schema, migrations,
correspondences and prior review artifacts are unchanged. SQLite integrity and
foreign keys, Django checks and 98 isolated focused tests passed. Post-import DB
SHA-256: `bde5218712398f0c7b5251abaefa3182f99ea43fd037c442c04518f01b59f410`.

No technical blockers remain for this set. No backfill, application/contract
change, schema migration, additional publication, adjudication repeat, commit or
push occurred. The prior review `.venv/bin/python` environment was used unchanged
(Python 3.13.1, Django 6.0.7, pypdf 6.16.1); documented `venv/py313/bin/python`
remains absent. The original [planning records](handoffs/MY2019_JL/director_review/final_planning_20261108/README.md)
are preserved as their pre-import checkpoint, not current pending authorization.

## MY2019 JL generation correspondence — five mappings published (2026-11-08)

The owner authorized the five existing proposals after validation. The accepted
workflow created immutable correspondence revisions 9–13 and publication receipts
2857–2861 for JLJL72, JLJL74, JLJP74, JLJS72 and JLJS74, narrowly scoped to US
MY2019. All target existing Wrangler JL Generation PK 32 / UUID
`38d3c3ac-f825-4406-abb5-c2d12b9129a4`. No pre-existing publication was duplicated.
[Publication records](handoffs/MY2019_JL/director_review/generation_publication_20261108/README.md)
retain exact proposal/receipt UUIDs, hashes, command output and coverage.

All 19 completed candidate artifacts resolve through exactly one published
mapping to that target, with per-code coverage 4, 6, 5, 2 and 2. VehicleDefinitions
remain 793; receipts increased from 2,856 to 2,861; correspondences from 8 to 13.
A consistent pre-publication backup and all-table row hashes confirm every
pre-existing record is unchanged. Only five correspondence rows, their five
receipts and normal sequence advances were added. SQLite integrity/foreign keys
and read-only Django checks passed. Original proposals/evidence and all 19
candidate classifications remain unchanged. No application change, migration,
canonical planning/import or historical backfill occurred. Final planning, certification and the separately authorized canonical import are
now complete as described above.

## Human classification adjudication — implemented; MY2019 ERC findings approved (2026-11-08)

The owner's current policy prefers manufacturer specifications without requiring
exact internal terminology. Evidence-backed human adjudication is the normal
fallback. [Adjudication 1.1](tasks/MY2019-erc-classification-adjudication.md) reuses
the existing adjudication artifact and command for proposed/approved classifications.
The initial consumer fills unknown controlled powertrain categories, with exact
candidate/source binding, explicit human provenance and confirmation, and no
changes to direct-source rules or Candidate/Manifest/Matrix versions. Existing
planning/execution and receipt lineage support the approved revised candidate;
generation review and import authorization remain independent. No schema change,
development migration, canonical write or historical backfill was performed.

Verification: 100 focused adjudication/powertrain/lineage/serialization tests
passed, including 13 new classification regressions. Django system checks,
migration consistency dry-run and Git whitespace checks passed. All database
tests used isolated resources; development database bytes remain unchanged.

The owner approved the ten reviewed US MY2019 ERC offerings' naturally aspirated
and nonhybrid classifications as derived conclusions. The existing adjudication
workflow created [ten separate approved findings and candidate revisions](handoffs/MY2019_JL/director_review/erc_approved_classifications_20261108/README.md),
retaining moderate confidence, all reasoning, exact candidate/source bindings and
limitations. Original proposals and candidates remain unchanged. Combined with
the nine unchanged EC3 artifacts, all 19 now pass complete structured powertrain
and retained-evidence validation. Forty-four focused approval/lineage/serialization
tests passed using isolated resources. No actual import plan, canonical write or
generation publication occurred. Broader MY2019 3.6L hybrid documentation remains
a scope caveat: approval covers only the ten exact ERC candidates and their
documented evidence. Earlier source-audit reports remain historical records.



## RA-044 structured powertrain implementation — accepted; development migrations applied (2026-11-07)

[Accepted RA-044](../architecture/designs/RA-044-Structured-Powertrain-Identity-Implementation-Architecture.md) has been implemented under separate director authorization. The [implementation record](tasks/RA-044-structured-powertrain-identity-implementation.md) lists the delivered scope and verification. Five nullable VehicleDefinition fields now have model validation and database constraints: marketed `engine_displacement_liters` Decimal(5,2), positive `engine_cylinders`, controlled `engine_aspiration`, `fuel_type`, and `electrification_type`. Migration `reference.0010_vehicledefinition_electrification_type_and_more` is additive and contains no data operations. It is applied to the development database. Read-only inspection on 2026-11-07 confirms reference migrations 0007–0010 are recorded, 793 VehicleDefinitions and 2,856 import receipts exist, and all five structured fields remain null on every historical VehicleDefinition. SQLite integrity and foreign-key checks pass. The director reports the pre/post-migration comparison verified unchanged historical PKs, UUIDs, slugs and receipts; that backup comparison was not independently repeated in this task.

Candidate schema 2.1.0, Manifest 2.1 and Matrix 2.1 explicitly bind the five structured attributes and qualified evidence. Resolution 1.1 and engine proof 2.0 bind current canonical peer state and retained successful-receipt evidence. One source can establish several attributes; multiple applicable sources can jointly establish the tuple. Incomplete/unknown attributes do not default to conventional values. Semantic equality precedes locator matching; established engine distinctions support mechanical creation. Fixed new-record slug qualifiers are independent of occupancy and ingestion order, and occupied conflicting slugs block. Existing UUIDs, immutable slugs and legacy contract serialization remain preserved. Central long and short hybrid labels feed descriptions and configurator choices.

Verification: 39 new RA-044 tests pass in the full suite, including isolated additive-migration preservation, both engine orders, stale evidence/peer rejection, nullable legacy assessment, Matrix rollback and receipt-idempotent retry. The final focused ingestion regression selection passed 129 tests. The complete isolated Django suite passed **691 tests, 0 failures, 0 errors, 0 skips**. Django system checks, migration consistency (`makemigrations --check --dry-run`) and `git diff --check` passed. The documented `venv/py313/bin/python` is absent in this checkout; verification used the existing Homebrew Python 3.13.2 executable (Django 6.1.3) with the existing `venv/lib/python3.13/site-packages` dependency path and `RIGARCHIVE_TEST_DB_PATH=:memory:`. No environment was rebuilt. The development database SHA-256 matches its pre-work baseline.

Implementation is accepted by the director, who confirms development migration completion. MY2019 candidate construction and read-only director-review preparation are authorized; historical backfill, correspondence publication and canonical imports remain separately controlled. This task performed no database writes or historical artifact/receipt rewrites. Earlier W2 entries below describe their original verification checkpoints; their statements that reference 0007–0009 were unapplied are superseded by the live migration inspection above. The completed RA-043 Measurements milestone remains preserved. The [W2 domain addendum](../architecture/designs/W2-Full-Specifications-Domain-Architecture.md#future-resolved-configurations-and-production-variation--compatibility-requirements) remains forward compatibility only; no W2 models, URLs, specification ingestion or revision administration were implemented.

## MY2019 US Wrangler JL preparation — historical evidence checkpoint

The director-accepted inventory remains 19 offerings (six two-door, thirteen
Unlimited). The [initial review](handoffs/MY2019_JL/director_review/evidence_review_20261108/README.md)
retains its 19 preparatory candidates, 32 assertion sets and original unresolved
ERC findings. Ten later separate approved ERC revisions completed the tuples;
the nine EC3 revisions remained unchanged. Five correspondence proposals were
subsequently published. Final Matrix certification and canonical execution are
now complete as recorded above. Earlier blocked reports, null-field candidates,
planning snapshots and database hashes describe their historical checkpoints and
have not been overwritten or treated as current blockers. No historical backfill
was performed.

## Structured powertrain identity and hybrid terminology — documentation approved (2026-11-07)

[ADR-0012](../architecture/ADR/ADR-0012-Structured-Powertrain-Identity-And-Hybrid-Terminology.md) records director-approved JL-D19 (manufacturer-neutral structured displacement/cylinders/aspiration/fuel/electrification), JL-D20 (review tuning-only differences with paired sourced output alternatives), and centralized hybrid labels for VehicleDescription and the Generation Configurator. RA-018, the W2 domain/property contracts and navigation architecture are cross-referenced with explicit supersession boundaries.

This earlier documentation milestone introduced no code or data changes. Its approved direction is now implemented in the separately authorized RA-044 milestone recorded above. Candidate v1 compatibility, historical artifact hashes, existing UUIDs/slugs and prior import outcomes remain intact. Noncombustion/multi-fuel applicability and historical backfill remain deferred.

## MY2018 US Wrangler JL canonical import completed (2026-11-06 local)

Matrix v2 `sha256:f8386d4a98892ddcbd096c375a72ece93b15a99ee951a4b71cbcc8e1d8bdf241` completed in one model-year transaction under JL Generation PK `32`, UUID `38d3c3ac-f825-4406-abb5-c2d12b9129a4`. The final scope contains 15 active configurations. VehicleDefinitions `795–808` and execution receipts `2843–2856` were created. Existing Sport V6 PK `715` retained its UUID, slug, and canonical fields. SQLite integrity and foreign-key checks passed. Comparison with the pre-import snapshot found no changes to existing application records, including JK and generation correspondence.

The idempotent retry reported 14 previously completed rows and one reviewed existing row with zero additional definitions or receipts. The database SHA-256 remained `554ad78185062eca135c49a934fb4c4eeba423dd9c4b3dd325f9d93f292e9eab` across the retry. The private artifact directory is `backups/review/jeep_jl_my2018_jdpower_pilot/live-import-20261107T013404Z/`. It contains `pre-import.sqlite3`, `approval.json`, `reconciliation.json`, the execution result and manifests under `matrix-2018-bawfg0jb/`, and the retry result under `matrix-2018-qz845cju/`.

## W2 B4 factory equipment and compatibility — corrections verified, pending independent architectural acceptance (2026-11-04)

Factory equipment items/offerings and compatibility rules retain their immutable revisions, exact catalogue membership, evidence links and atomic publication workflow. F1–F3 corrections resolve equipment effects simultaneously from three-valued premises rather than sequential rule order; demonstrably inactive rules/triggers/dates do not create replacement uncertainty, while unknown/conflicting premises and unresolved effect cycles remain conservative. Factory package constituent and replacement edges reject exact accessory revisions, including nested packages; legitimate accessory catalogue-only offerings remain supported. Includes/replaces do not establish coexistence or alter selected offering revisions. No models, migrations, dependencies or B5 implementation were added.

Corrective verification: 19 focused new regressions passed; the specification selection passed 136 tests before three additional boundary regressions, all included in the final 227-test passing combined specification/reference/ingestion/acquisition selection. System check passed, migration-consistency dry-run reported no changes, and whitespace check passed. Existing migrations remain unchanged and were not applied to development. Persistent database SHA-256 before/after: `09754fa3a988df19c984e5a492d4e869ae3f0921ee44517fe7f1113df417e873`, authorized as the preservation baseline for this task only. The historical difference from `4e1dff5fcdcfceef1099eb7e88b6ed6bf60665ce0fab5e1a50a42af66a7d0f49` remains unexplained; no SQLite/WAL cause is established. All 71 retained storage files have unchanged paths and SHA-256 values. B4 remains pending independent architectural acceptance; B5 has not begun. See [B4 task record](tasks/W2-B4-factory-equipment-compatibility.md).

## W2 B3 transmission domain — verified, ready for architectural acceptance (2026-11-04)

Transmission logical descriptions, immutable description and offering revisions, engineering assertion/evidence links, exact catalogue membership, and B2 publication/dependency/replay integration are fully implemented and verified. Multiple alternatives remain subordinate to one canonical VehicleDefinition; B1 wire/selection semantics are reused unchanged. Additive migration 0008 depends on 0007; both were successfully tested against isolated databases and remain UNAPPLIED to the development database. Verification passed 6 B3 tests, 20 B2 publication tests, 86 B1 contract tests, and 21 reference regressions (133 total). System checks and migration-consistency dry runs passed. Persistent development database and retained storage baseline hashes were preserved byte-for-byte. No UI, equipment/body persistence, acquisition, real publication, or B4 work. See [B3 task record](tasks/W2-B3-transmission-implementation.md). B1's historical hash discrepancy remains deferred.

## W2 B2 specification persistence/publication (2026-11-04)

Implemented append-only Reference persistence for evidence documents/assertion references, unit registries, logical property definitions and their revisions, typed assertions, exact catalogue revisions/memberships, independent coverage and ordered evidence links. Dedicated specification publication receipts avoid fabricated VehicleDefinition-import fields. `reference.specifications.publication` provides zero-write planning, explicit exact-manifest authorization, live target/dependency/source revalidation, atomic publication/receipt insertion, deterministic current-only replay and supersession. B2 rejects transmission/equipment/feature/body persistence; existing baseline executors and identities are unchanged.

Additive migration 0007 was tested in isolated databases, including a 0006→0007 preservation check; it remains UNAPPLIED to development. Twenty B2 tests and 107 B1/directly affected regression tests passed (127 total); system/migration-consistency checks passed. No full-suite run, real catalogue publication or development writes. Retained storage and development bytes were preserved during B2 verification. The earlier B1 database-hash discrepancy remains unresolved and deferred; it was not investigated. See [B2 completion record](tasks/W2-B2-specification-persistence-publication.md). B3 and deployment/data-publication require separate authorization.

## W2 B1 contract implementation (2026-11-04)

Implemented pure-Python W2 serializers/validators under `reference/specifications/`, independent of the eager Django imports in the legacy ingestion package. Includes closed typed values and provenance, exact categorical qualifier definition revisions, dimensional/unit checks, predicate 1.0 with shared budgets, independent selections, whole-selection compatibility, complete snapshot membership, enrichment/publication v1 hashing and validation, immutable canonical-byte round trips and pure exact-current replay/stale checks. No ORM, filesystem acquisition, publication, receipts, models, migrations or UI in the new package. Existing Candidate v2/manifest 2.0 and W1 identities remain unchanged. Body/series references only; curation and Candidate v3 execution remain deferred.

The director resolved the categorical-qualifier gap by approving an exact definition revision reference (`categorical_definition`, null for noncategories); approved W2 contract text is updated accordingly. There are 86 new standalone tests. See the [B1 verification record](tasks/W2-B1-full-specifications-contract-primitives.md) for final focused/full results and preservation qualifications. The first full-suite run exposed legacy tests retaining four fixture-copy artifacts in persistent acquisition storage; temporary-root isolation was corrected in the multi-source and canonical-execution test classes, with final write/deletion guards and complete inventory verification. Those incidental files remain preserved and are not acquisition evidence for ingestion. Development database hash changed during the broader work interval for an unestablished reason; final test runs preserve their own baseline. All historical Reference/Measurements rows still match the verified pre-0006 snapshot, apart from previously authorized Jeep/W1 additions. Do not claim task-wide byte preservation. No restoration, database write command, Git mutation or B2 work occurred.

## W2 Phase A architecture contracts (2026-11-04)

Director-approved contract corrections are incorporated. [ADR-0011](../architecture/ADR/ADR-0011-Factory-Body-Configuration-Identity.md) is accepted architecture and narrowly extends ADR-0010 Decision 2 for evidence-backed van body identity; earlier accepted ADRs remain unchanged. [Domain architecture](../architecture/designs/W2-Full-Specifications-Domain-Architecture.md), [property/applicability](../architecture/designs/W2-Specification-Property-Applicability-Contract.md), [enrichment/publication](../architecture/designs/W2-Enrichment-Publication-Contract.md) and [implementation plan](../architecture/designs/W2-Phase-A-Implementation-Plan.md) now specify exact semantic digest preimages, cross-profile safeguards, closed serialized schemas, independent selection knownness, predicate accounting, immutable complete snapshots and exact-current-only replay. New normalized quantities use canonical decimal strings; original/legacy artifacts and historical hashes remain untouched.

These are architecture contracts, not implemented models/executors or migration approval. Candidate v3/schema 3.0.0, body-aware baseline manifest 3.0, enrichment/publication v1 and predicate 1.0 are approved future boundaries. Existing Candidate v2/manifest 2.0 and W1 Jeep identities remain unchanged. Full-UUID suffixes apply to new assessed body/series-aware records only; >180-character slugs block. Body/series curation publication contracts remain deferred to B5. B1 serializers/validators are implemented as recorded above; B2 requires separate implementation authorization; no development writes, migrations, acquisition or UI changes are authorized by Phase A. Pickup/bed profiles and accessory-dependent evaluation remain deferred.

## Wrangler JK J.D. Power evidence policy (2026-11-05)

J.D. Power can independently establish explicit core configuration identities under the [ingestion protocol](../development/INGESTION_PROTOCOL.md#jd-power-core-configuration-evidence). Historical Wrangler JSON extraction and normalization are bounded to explicit US MY2007–2017 core rows. Web enumeration found 74 core grade/body/drive listings. Reviewed structured JSON is sufficient and retains its own integrity digest. Webpage bytes, webpage hashes and HTML selectors are optional. MY2007 X 4WD and Unlimited X 2WD have trim-specific engine evidence for candidate preparation. Other rows remain pending explicit engine review. Matrix v2 may bind an unambiguous unique-year result directly under Stage 6C. Existing equipment authority and canonical authorization boundaries apply.

## Stage 6C matrix Generation binding (2026-11-05)

Matrix v2 supports a reviewed explicit correspondence or a unique active year-range resolution bound to the exact approved Generation. Review and execution revalidate Candidate v2 resolution. Matrix v1 retains its correspondence requirement. The two MY2007 J.D. Power candidates passed read-only draft review for JK PK 31 with its canonical UUID. The draft is unapproved and unexecuted. The other six MY2007 rows are outside the pilot.

## Attribution privacy Phase 1 (2026-11-06)

New canonical import and matrix approval/execution commands resolve declared attribution from overrides, ignored project-local TOML or nonpersonal defaults. Human roles, execution agent and CLI interface are recorded separately. Configuration does not authorize execution. Approval v1 serialization and historical receipts remain intact. Historical attribution cleanup requires separate authorization.

## MY2008–2017 Wrangler JK preparation (2026-11-06)

All 66 defined US core rows passed read-only planning and review across ten separate, unapproved Matrix v2 drafts. Year-specific Jeep specifications support the 3.8L V6 through MY2011 and the 3.6L V6 starting MY2012. Every row binds the exact JK Generation PK 31 and UUID through unique year-range resolution. The local review index is in `backups/review/jeep_jk_2008_2017_20261106T122928674474Z/index.json`. Preparation performed no canonical execution.

**Approval checkpoint (2026-11-06).** MY2008, MY2009 and MY2010 each have a validated eight-row approval. MY2011, MY2012, MY2013, MY2014, MY2015, MY2016 and MY2017 each have a validated six-row approval. Each year has its own `approval.json` under the review index directory and is separately attributed to `legacy_cli_operator`. All ten years are prepared and approved. At the approval checkpoint, execution was still pending separate authorization. Live reference tables matched the pre-approval snapshot, with 713 VehicleDefinitions and 2,771 receipts.

**Execution checkpoint (2026-11-06).** All ten approved model years, MY2008 through MY2017, committed in ascending order in separate atomic model-year transactions. Read-only reconciliation verified 66 new VehicleDefinitions and 66 matching receipts. Counts rose from 713 to 779 VehicleDefinitions and from 2,771 to 2,837 receipts. All pre-existing reference rows matched the pre-execution backup, including the MY2007 and MY2018 JK records. SQLite integrity, foreign keys and Django system checks passed. The full inventory and ten execution result paths are in `backups/review/jeep_jk_2008_2017_20261106T122928674474Z/execution-summary.json`.

## MY2007 Wrangler JK matrix execution completed (2026-11-06)

The authorized eight-row US MY2007 Matrix v2, digest `sha256:8acf17c0ffdfb0fa467d881df43063c5656529057e0f86754532f9e6d3072e6a`, committed atomically under JK PK 31. VehicleDefinitions 721–728 and receipts 2764–2771 reconcile to the approved rows. Both approval and execution were separately attributed as `legacy_cli_operator`. Read-only reconciliation confirms MY2007 complete. Existing reference rows, including all six MY2018 JK configurations, matched the verified pre-execution backup. SQLite integrity and foreign-key checks and the Django system check passed. MY2008–2017 remain pending evidence preparation and separate authorization.

## MY2007 Wrangler JK final pre-approval verification (2026-11-05)

All eight US MY2007 Wrangler JK Candidate v2 rows passed fresh read-only review of the existing Matrix v2 digest `sha256:8acf17c0ffdfb0fa467d881df43063c5656529057e0f86754532f9e6d3072e6a`. All resolved by `unique_year_range` to JK PK 31, UUID `a053766b-d5da-4ea2-9e90-365d0e79110d`. At the pre-approval checkpoint, the matrix was ready for exact human approval.

The full isolated Django suite passed 634 tests after two W1 regressions were decoupled from obsolete rejection wording. Django system checks, migration dry-run and Git whitespace checks passed. The prior live database difference was confined to an existing session whose payload changed and expiration advanced. Its writer was not established. Canonical records and receipts matched the prior snapshot, and fresh planning left its read-only snapshot byte-identical.

## Stage 6A Generation Trim Matrix architecture approved (2026-11-05)

[ADR-0007's Stage 6A amendment](../architecture/ADR/ADR-0007-Explicit-Human-Authorization-Execution-Audit-Receipts-Canonical-Promotion.md#accepted-stage-6a-amendment) and the [ingestion protocol](../development/INGESTION_PROTOCOL.md#generation-trim-matrix-stage-6a) approve exact matrix-level authorization, model-year transactions, backed-up local approval artifacts and individual receipt linkage. Stage 6B implements exact matrix review and approval, read-only status, one-year transactional execution, receipt-based replay checks and durable attempt reports. The existing single-plan workflow remains supported. Stage 6B is ready for human review after isolated verification. No canonical imports were executed.

Stage 6B hardening distinguishes initial artifact failures, rollback and committed-but-incomplete reporting. Reconciliation rejects ambiguous or inconsistent completion receipts. Attempt artifacts preserve separate approval and execution attribution and distinguish completion order from numerical model-year order. Isolated verification passed 167 relevant tests, Django system checks, migration-consistency dry-run and Git whitespace checks. Ready for final human acceptance.

Stage 5E verified all six defined MY2018 US Jeep Wrangler JK core configurations under Generation PK 31. The 74 remaining defined configurations span MY2007–2017. Stage 6A architecture approval does not authorize those imports.

## Jeep Wrangler JK Stage 5B remaining-grade evidence (2026-11-05)

The retained MY2018 US JK brochure now yields separate validated assertion sets and normalized interpretations for Sahara, Unlimited Sahara, Rubicon and Unlimited Rubicon. The exact reviewed page 9 rows retain grade, body, engine, 4x4 system and JK provenance. Stage 5B stopped at normalization. See the [completion record](tasks/JK-stage-5B-remaining-grade-evidence.md).

## Stage 4A historical slug integrity (2026-11-05)

Canonical import planning and create preflight check all VehicleDefinitions in the target Generation's slug namespace. An inactive owner produces a historical slug conflict during planning or a stale-plan abort during create preflight. Active exact matches retain no-op behavior. The existing unconditional Generation/slug constraint remains the final guard. See the [Stage 4A completion record](tasks/JK-stage-4A-historical-slug-integrity.md).

## Jeep Wrangler JK Stage 3 offline integration (2026-11-04)

Authentic Stage 1/2 Unlimited Sport evidence produces an eligible Candidate v2 plan for JK with `source_established_grade` in isolated tests. The existing W1 correspondence resolves when the original W1 assertions accompany the Unlimited evidence in the exact reviewed order. Only Unlimited assertions supply the eight normalized interpretations. A synthetic new correspondence also resolves in isolation, while two current chains with the same selector require both exact evidence sets. Stage 4 still requires review of evidence assembly, an all-status slug collision preflight, and live resolution revalidation. No correspondence was published and no import was executed. See the [Stage 3 completion record](tasks/JK-stage-3-offline-integration.md).

## Jeep Wrangler JK Stage 2 normalization (2026-11-04)

The reviewed Stage 1 assertion set for the 2018 US JK Wrangler Unlimited Sport maps to the eight existing canonical ingestion concepts, including `Unlimited Sport`, 3.6 L, six cylinders and `4WD`. Publication provenance and the complete reviewed assertion set gate admission. Original source terms, assertion references and JK evidence remain available for later review. Synthetic fixtures exercise early-year aliases and mechanical combinations. Early-year production admission awaits reviewed retained assertion sets. Stage 2 stops at normalized interpretations. See the [Stage 2 completion record](tasks/JK-stage-2-evidence-scoped-normalization.md).

## Jeep Wrangler W1 closeout (2026-11-04)

Completed the bounded authentic MY2018 JK/JL Sport two-door pilot, not full Wrangler year/trim ingestion. Existing JK 31 and JL 32 parents now have VehicleDefinitions 714 and 715 respectively (Sport, 3.6L V6, 4WD, US). Three reviewed correspondence revisions were published with receipts 2754–2756; exact authorized imports produced receipts 2757–2758. Migration 0006 is applied; earlier “unapplied/no Jeep population” checkpoints below are historical. Counts: 700 VehicleDefinitions, 14 Generations, 2,758 receipts, three correspondence revisions, 31 corrections.

Retained JK/JL manufacturer PDFs plus the original Stellantis/Mopar release support reviewed applicability; release accessories were excluded under the permanent brochure-governed equipment policy. Publication/import regression runs passed 141 tests each; closeout passed 144 relevant isolated tests, system/migration checks, read-only actual-page renders, integrity/FK checks and evidence preservation. Pages list only imported MY2018/Sport records; Generation dates do not generate missing configurations. No closeout UI or database changes. A later database hash differs from the import report; current-task hash is unchanged, cause of the intervening difference unresolved. Historical PNG-test and database-hash qualifications remain.

See [W1 closeout and catalogue roadmap](../development/JEEP_W1_CLOSEOUT.md) for exact source hashes, correspondence/import identities, manifests, test scope, preservation qualifications and the proposed catalogue wording correction. Full Wrangler population, permanent Full Specs, transmissions and packages remain incomplete and separately authorized.


Quiet contour and compact-control revision (2026-11-01): implemented experimentally, awaiting visual approval. Restored the earlier subtle contour source exactly (SHA-256 9d725fed…), retained as topographic-subtle-original.png; active transparent map preserves its geometry and adds only two tangent-aligned labels plus three faint dotted arcs. Palette #f7f4ee and approved desktop controls remain. Tablet/phone visible faces are 36px with 44px interactive boxes; header heights, search widths, Vehicle Platforms positions and all other homepage imagery/layout are unchanged. All five requested browser sizes passed; 358 isolated Django and 31 JavaScript tests passed, system/migration-consistency/whitespace checks passed. Final browser-pass database hash stayed 73b83740…48c5d; all row counts and 11 reference/measurement table content fingerprints were unchanged throughout this task. Earlier in this task, file hash changed with session-expiry metadata, consistent with session writes rather than reference-data edits. No database restore/overwrite or Git mutation. See tasks/RA-EXP-homepage-quiet-contours-compact-controls.md. Earlier denser terrain descriptions below are historical.

Homepage map/paper/Garage refinement (2026-11-01): implemented experimentally, awaiting visual approval. Homepage uses the existing #f7f4ee CSS paper color plus independent transparent3072px contour PNG. Terrain is irregular/domain-warped with decorative6800/7200 labels; photo-edge wear/grain is border-concentrated. Homepage desktop search/Garage are both36px high/top-aligned; tablet/mobile header and diagram layout unchanged. Diagram, photograph, tagline/base template, source wireframe and settings fingerprints preserved. Development database fingerprint changed during the task; cause unestablished, no direct development database write command or generation-detail visit issued. Database was not restored; preservation review remains open. All358 isolated Django and29 JavaScript tests passed; system/migration-consistency/whitespace checks passed. Previous browser viewport issue was resolved by calibrating supported viewport/screenshot dimensions against DOM measurements: all1440x1000,768x1024,390x844,375x812,320x700 sizes verified, with desktop/390px approval captures. No overflow, broken eager images or console errors; More/Vehicle keyboard dismissal/focus restoration passed. See tasks/RA-EXP-homepage-background-paper-garage-refinements.md. Earlier incomplete verification notes below are historical; no commit/push.

Approved homepage PNG asset production (2026-11-01): experimental implementation awaiting completed responsive verification and visual approval. Authoritative reference is docs/design/wireframes/homepage_hero_diagram_&background_approved.png (the manually staged source is preserved). User authorized extracting its exact dimensioned diagram. Homepage now uses separate approved-diagram, neutral photo-paper and seamless contour PNGs; original photograph, source illustration and prior SVG retained. Existing grid, header/tagline, navigation, photo label and responsive placements remain. Pixel-level diagram preservation and original-photo equality verified. All 358 isolated Django and 28 JavaScript tests passed, system/migration-consistency/whitespace checks passed. Initial1440px integration inspected; subsequent managed-browser viewport control stopped applying sizes, leaving an actual762x529 view. Final five-size and390px screenshot acceptance remains incomplete. See tasks/RA-EXP-homepage-approved-paper-assets.md. The earlier SVG experiment below is historical and no longer the active homepage image.

Decorative drafting illustration experiment (2026-11-01): revised after the first annotation composition was not approved. Derived SVG now uses a 1200x1340 expanded paper canvas, unchanged native raster artwork, translated lower views and exactly five spaced dimensions: side length/overall height/wheelbase, front outer-tire width, rear roofline-to-hatch-bottom height. Larger filled arrowheads and empty numerical-label gaps; no numerical values or added diagonal lines. Mobile/tablet frame fits the full canvas (104x116px phone, 180x201px tablet), with width/overlap/1deg rotation and 320px suppression preserved. Header/photo/tagline/data unchanged. All 357 isolated Django and 25 JavaScript tests passed; system/migration-consistency checks passed. Managed-browser full-resolution and all five requested viewport inspections completed without observed clipping/overflow/errors. Mobile strokes remain subtle. Awaiting visual approval. See tasks/RA-EXP-homepage-sketch-drafting-annotations.md.

Trimmed sketch paper (2026-11-01): tablet/mobile frame aspect ratio is now 1.09, genuinely shortening the visible paper without moving or shrinking drawings. Phone frame 104x95px with approximately 4.4-4.9px margins; tablet 180x165px. Prior 50% image position, 1deg outer rotation, width/placement, desktop and 320px suppression preserved. All 356 isolated Django tests and five managed-browser viewport checks passed; visual approval pending. See responsive task record for measurements.

Sketch paper rotation (2026-10-31): outer tablet/mobile sketch frame rotates 1 degree clockwise; crop/placement unchanged, desktop unrotated and 320px hidden. Verified all five sizes, no overflow or clipping; 356 isolated Django tests passed again. Visual approval pending.

Responsive detail follow-up (2026-10-31): existing responsive layout is user-approved; final sketch-margin/More-label details await visual approval. The unchanged sketch frame now uses 50% vertical positioning for balanced paper margins and complete drawings. More ▾ replaces the ellipsis with an approximately 47x44px native button; layout, tagline and Vehicles caret remain unchanged. All five viewport and keyboard checks passed; full 356 Django/25 JavaScript tests passed again.

Sketch accent follow-up (2026-10-31): enlarged crop now includes complete lower front/rear views at 375/390/768px, with 28px clearance before Vehicle Platforms. Desktop and <=360px suppression unchanged. All 356 isolated Django tests passed again. See the responsive task record for superseding accent dimensions.

Responsive shared header/homepage refinement (2026-10-31): implemented experimentally, awaiting visual approval. The exact manually selected tagline is preserved. Collapsed phone headers measure 171.4px; tablet 123.4px and desktop 87.4px. Vehicles retains its 36x44px caret target/6px glyph gap; More holds existing secondary navigation on narrow screens with visible no-JavaScript fallback. Mobile/tablet hero keeps photo dominance and a small cropped sketch accent, hidden at <=360px. All 356 isolated Django tests and 25 JavaScript tests passed, plus system/migration-consistency/syntax/whitespace checks. Managed-browser checks covered all five requested sizes, disclosures, keyboard/skip focus and selector/model listings. Generation-detail pages were not revisited to avoid session writes; their templates/layout are unchanged. See tasks/RA-EXP-responsive-header-homepage-hero.md. No commit or push.

Vehicle navigation visual continuity (2026-10-31): implemented and user-approved after desktop/mobile visual review and final mobile initial-load/skip-link checks; not committed. Approval applies to this refinement task, not the overall experiment. Photographic Generation listings are scoped away from the legacy manufacturer directory; desktop detail composition is preserved, mobile identity precedes a 3:2 photo, unavailable Overview topics are plain text, selector cards remain two-up at 390px, breadcrumbs return to Explore Vehicles, and the Vehicles caret gap is 6px. All 354 isolated Django tests and 17 JavaScript tests passed, plus system/migration-consistency/whitespace checks. Managed-browser desktop/mobile and native keyboard checks completed; screen-reader and zoom acceptance were not tested. Session writes from authorized browser visits are permitted and preserved. See tasks/RA-EXP-vehicle-navigation-visual-continuity.md. Earlier browser-blocked statements below are historical.

1. Project Overview

Documentation reconciliation (2026-10-27): current local baseline is Python 3.13.2 via `venv/py313/bin/python`, Django 6.0.7 and pypdf 6.16.1. Latest recorded implementation verification is 350 passing Django tests and 17 passing JavaScript tests after the Vehicles quick selector, with system/migration-consistency and whitespace checks passing. Earlier 339/340/346-test results and Python 3.14 commands below are historical task checkpoints, not current environment instructions. No tests or database commands were run for this documentation reconciliation. The Vehicles link/disclosure and photographic directory are implemented; the five-category contextual shell, model category destinations and optional selector dialog remain deferred. Browser responsive, keyboard/focus, zoom/reflow and screen-reader acceptance remain pending.

Documentation-task preservation limitation (2026-10-27): file-only fingerprint comparison detected a change to `db.sqlite3` during this documentation interval (initial SHA-256 `53c1b8f18445c373b9e0faad3ac1f11a39e85adbedb995043267a9909c23cf63`; observed SHA-256 `1d412a7e7a355b918c35223ea713abaf2cc1a37a681c91126f9235017a00b082`). No database command, application/browser request or database write was issued by this task. The cause is unestablished; byte-for-byte database preservation across this interval cannot be confirmed. The database was not restored or otherwise modified to reconcile the mismatch. This is a separate observation from the unresolved historical B-1 database/IDE discrepancy and is not explained or authorized by the new snapshot policy.

SQLite development/public-staging policy (approved 2026-10-27): `db.sqlite3` is intentionally tracked. Local development is authoritative for authored vehicle reference data; deliberate database snapshot commits/pushes feed PythonAnywhere staging through the existing Git deployment workflow. Staging is not independently authoritative. Database changes must not be bundled automatically into unrelated code commits, and Codex must preserve local data absent explicit authorization. Deployment precautions and the required future production boundary are documented in `docs/development/DATA_PRESERVATION.md`; this task changes neither tracking nor deployment configuration and authorizes no database or Git operations.

Vehicles navigation quick selector (2026-10-27): Vehicles remains a normal link to `/select-vehicle/?destination=generations`, with a separate progressively enhanced “Choose a vehicle” chevron disclosure. The server-rendered compact panel uses shared active manufacturer/model discovery, includes models without Generations or definitions, and links to existing canonical model pages. It has scrollable manufacturer/model columns, a Browse all vehicles footer, empty-state text, native keyboard controls, Escape/outside-click/focus-exit dismissal, and focus restoration. Desktop uses two columns; narrow mobile uses stacked columns with bounded scroll areas and wrapping names. No API, routes, schema, images, session selection, contextual shell, search or Generation configurator changes. The header adds two bounded queries; the unfiltered full selector now totals six (four directory queries plus two header queries), independent of model count. Verification: all 350 Django tests and 17 JavaScript tests passed, system check and migration-consistency dry-run passed, and `git diff --check` passed. Isolated memory databases, temporary media/files and a runtime SQLite connection guard preserved the development database hash and absent sidecars. Browser Use remains blocked by managed policy; real desktop/mobile rendering, keyboard/focus, zoom/reflow and screen-reader acceptance remain unverified. Completion record: `docs/implementation/tasks/RA-EXP-vehicles-navigation-quick-selector.md`.

Vehicles selector compact thumbnails: the selector grid now uses four fixed desktop columns within a 1008px maximum width, reducing to three at 1024px, two at 768px, and one at 380px. Sparse manufacturer groups no longer expand cards across a row. Thumbnails reserve a 3:2 aspect ratio with cover sizing (approximately 160px high at the desktop grid maximum); captions have compact padding/type. Image selection and navigation behavior are unchanged. Verification: 346 isolated Django tests passed, system check and migration-consistency dry-run passed, whitespace check passed; database SHA-256 `90e56453d157afb2cb26f4c7393b620246ffb06a591704da7719b372f82c2482` unchanged and sidecars absent before/after. Actual browser visual acceptance remains unverified.

Vehicles selector visual integration (2026-10-27): the global Vehicles link now opens `/select-vehicle/?destination=generations`. The existing GET selector presents Explore Vehicles with manufacturer filters, selected-filter indication, name search, clear controls, and responsive photographic model cards. Each card opens the existing canonical model page for Generation selection; the newest active Generation is selected by descending canonical `start_year`, independent of definition coverage or insertion order. The existing presentation image helper resolves that Generation only; missing images and models without active Generations receive a neutral placeholder, with no older-Generation fallback. Discovery/prefetch remains in reference services; image resolution remains in presentation. A sliced windowed prefetch avoids per-card database queries (historically four queries for the unfiltered selector before the quick selector; the current rendered total is six, including two header queries, verified with additional models). Header search wording is accurate; routing is unchanged. Canonical routes, active-model eligibility, pending destination contracts, Generation design and configuration selector remain intact; the deferred five-category shell is not implemented. Verification: 31 focused tests and all 346 full-suite Django tests passed under Python 3.13, plus 11 JavaScript tests, system check, migration-consistency dry-run and whitespace check. Tests asserted memory database configuration and used temporary media/files plus a runtime SQLite connection guard. Database SHA-256 before/after: `90e56453d157afb2cb26f4c7393b620246ffb06a591704da7719b372f82c2482`; no SQLite sidecars existed. Browser automation could not start, so desktop/mobile appearance and real keyboard/accessibility acceptance remain unverified. Completion record: `docs/implementation/tasks/RA-EXP-vehicles-selector-visual-integration.md`.

Generation empty-state presentation (2026-10-27): Builds and Mods and Service Guides reuse the shared `generation_domain_placeholder.html` partial with the approved `images/generation-builds-placeholder-baja.png` for Builds and Mods and the unchanged Homepage service photograph. A Builds-only left-centered crop retains the rear storage equipment without changing the 210px frame, proportions, empty alt text or shared placeholder architecture. Captions contain only "No Builds documented yet" and "No service guides added yet."; no generation-specific or explanatory paragraphs remain. Photographs fill dedicated full-width, non-shrinking 210px media frames with `object-fit: cover`, inside modest .5rem card padding; compact captions follow immediately without an expanding text area. Existing headings, unavailable links, two-column layout and mobile stacking are preserved. Generation Page Community Contributions is planned in `docs/implementation/ROADMAP.md`, with priority after Vehicle navigation tab model-selection work. Its existing planning entry now distinguishes empty placeholders from future populated grids supporting multiple Builds and Mods entries and multiple Service Guide entries, to be designed alongside contributions. No populated layouts, UI prompts, models, routes, uploads or contribution infrastructure are implemented. All 340 isolated Django tests, system/migration and whitespace checks passed; exact captions, decorative assets and unavailable links were verified for Fourth/Fifth Generation. Development database unchanged. Browser visual verification unavailable.

Homepage drafting-panel correction (2026-10-27): supersedes the transparent panel/portrait drawing slot described in the provisional integration record below. A continuous site-surface paper background, neutral 16px technical grid, subtle border and shadow are restored. Desktop panel margins match the mounted photo within the unchanged 2:1 stretched grid; the photograph determines row height and the approved image is proportionally contained in the centered panel area. The artificial portrait aspect ratio and hidden caption spacer are removed. At the existing 1024px stacking breakpoint the image returns to natural sizing with its existing 380px cap. No image assets, other Homepage content or other pages changed. All 339 isolated Django tests, system/migration, rendered-HTML, preservation and whitespace checks passed; database hashes unchanged. Actual browser alignment remains unverified because browser tooling is unavailable.

Homepage provisional illustration integration (2026-10-27): the hero references `static/images/homepage/Toyota 4Runner Technical Blueprint.png` instead of `vehicle-study.svg` (filename corrected against the tracked template on 2026-10-27; the earlier record incorrectly included “Views”). The new image is contained proportionally within the prior drawing footprint, preserving the existing panel padding, border space and responsive cap. Redundant outer grid/background/shadow and visible border were removed; the duplicate caption is hidden with its spacing retained because the artwork includes the disclaimer. Alt text describes the fifth-generation Toyota 4Runner side/front/rear elevations and states illustrative/not to scale. Image files, other Homepage components and Generation pages are unchanged. All 339 isolated Django tests and system/migration/asset-resolution/rendered-HTML/whitespace checks passed; database and image hashes unchanged. Browser visual acceptance remains unverified; the approved asset is provisional and does not establish technical measurements or complete the broader experiment.

Final Homepage Explore icon adjustment (2026-10-27): icons now render at 33px (1.5× the previous 22px), with explicit white `#FFFFFF` strokes, shared 1.75-unit stroke width, transparent containers and unchanged 10px lower-left offsets. Exactly one SVG remains per card. All photographs, texture, other presentation and database hashes are preserved. All 339 isolated Django tests, system/migration, rendered-HTML and whitespace checks passed. Browser visual verification unavailable.

Homepage Explore icon repair (2026-10-27): supersedes the incomplete transparent-overlay state recorded below. The four cards use new `factory-clean.png`, `measurements-clean.png`, `builds-clean.png` and `service-clean.png` assets with the old raster icons removed through localized photographic reconstruction. Original PNGs remain intact; crop dimensions and pixels outside the repair areas are preserved. Exactly one 22px SVG per card has explicit HTML/CSS sizing, shared black strokes and transparent containers 10px from the lower-left corner. No backing rectangles, borders or shadows. Topographic styling, other illustrations/photos, content and layout unchanged. All 339 isolated Django tests and system/migration/whitespace checks passed. Rendered HTML and localized image repairs were inspected; database and original image hashes unchanged. Real-browser visual verification remains unavailable.

Homepage contrast/transparent-overlay correction (2026-10-27): current contour CSS opacity is 13.5%, a 25% reduction from 18%, with scale, geometry and palette preserved. SVG icon overlays now have transparent backgrounds and black strokes; sizes and positions are unchanged. The retained photo crops still contain the original white raster icons, exposed by removing the opaque badges. SVG-only presentation remains incomplete pending direction on localized image retouching. All 339 isolated Django tests and system/migration checks passed; database, image and Homepage template hashes unchanged. Browser visual verification unavailable.

Homepage contour visibility correction (2026-10-27): current contour styling supersedes the earlier 4.5% opacity settings below. Opaque neutral-gray SVG strokes (`#666666`, width 1.5) render at the unchanged `576 × 432px` scale with a single 18% CSS opacity layer. Contour geometry, page palette, Homepage template and other image assets are preserved. System/migration checks and all 339 isolated Django tests passed; SVG inspection confirms no internal transparency; database hashes unchanged. Browser visual acceptance remains unverified.

Homepage follow-up (2026-10-27): contour rendering now uses 40% of the previous scale (`576 × 432px`) with unchanged 4.5% opacity and palette. Four independent inline SVG Explore icons use shared strokes and smaller dimensions; responsive surface-color badges conceal the blurry icons baked into the retained photographic crops. Photographs, technical illustration, layout, text, links and card dimensions are preserved. All 339 isolated Django tests, system/migration checks, SVG parsing and whitespace checks passed. Database and existing Homepage image hashes unchanged. Browser visual verification remains unavailable.

Homepage background refinement (2026-10-27): the Homepage-only beige paper overlay was replaced with a transparent synthetic contour SVG at 4.5% opacity and a fixed desktop/mobile tile scale. Existing global page (`#f7f4ee`) and surface (`#fdfcf9`) colors are retained; Homepage photo-frame, schematic and card beige overrides were removed. Layout, content, image assets, tape, photo labels and other pages are unchanged. Verification: 339 isolated Django tests passed; system check, migration-consistency check, SVG opposing-edge endpoint check and whitespace check passed. Development database hashes unchanged. Desktop/mobile browser visual acceptance remains unverified because browser tooling is unavailable. No schema, dependency or architectural changes.

RigArchive is a long-term engineering project whose purpose is to build the world's most trusted technical archive of vehicles and their modifications, maintenance, compatibility, measurements, and supporting evidence.
The Project Blueprint defines the architectural vision.
The Engineering Handbook defines implementation standards.
The GitHub repository is the authoritative implementation.
This document summarizes the current implementation status.

2. Project Authority

Repository authority, highest to lowest:

   1. Current implementation task
   2. Architectural Decision Records (ADRs)
   3. CURRENT_STATE.md
   4. Engineering Handbook
   5. Project Blueprint

Conflicts between these documents should never be resolved by assumption.

3. Current Technology Stack
Backend
Python 3.13 (verified local interpreter: Python 3.13.2)
Django 6.0.x

Local development environment: `venv/py313`, using `venv/py313/bin/python` explicitly from the repository root for local development, Codex CLI, and Codex Desktop. `requirements.txt` pins Django 6.0.7 and pypdf 6.16.1. SQLite 3.53.4 is available. The legacy `.venv` is preserved; its Python 3.14 package-directory workaround is no longer the development convention. Historical verification records below retain their original Python versions.

Python 3.13 migration verification (2026-10-27): all 340 discovered Django tests passed, as did the affected adjudication test-module import, Django system checks, migration consistency (`makemigrations --check --dry-run`), `pip check`, all 11 JavaScript tests, and `git diff --check`. Missing `Any` and `Optional` imports were corrected in the ingestion workflow and its adjudication tests without changing workflow semantics or test behavior. Verification used the standard DiscoverRunner, asserted the configured database was `:memory:` and the SQLite test database was a shared-memory URI, set temporary media and temporary-file locations, and installed a runtime SQLite connection guard allowing only memory or the dedicated temporary directory. The restoration command's subprocesses explicitly target temporary databases. No migrations ran against the development database. Before/after SHA-256 was `347781aef4d74cf4f0fe5931f9a8542b759e211c193be9f97cc1b053cdf20143`; no SQLite sidecars existed at either check.

To select the environment in PyCharm, use Settings → Project → Python Interpreter → Add Interpreter → Add Local Interpreter → Existing environment and select `venv/py313/bin/python`. PyCharm and Codex configuration were not modified. PythonAnywhere production already runs Python 3.13 (user-confirmed); production configuration was not changed or independently inspected. Development-server startup was not verified in this migration continuation.

Database
Development and public staging: SQLite with deliberate Git-tracked snapshots from the authoritative local development database (temporary policy approved 2026-10-27; see `docs/development/DATA_PRESERVATION.md`).
Future Production: PostgreSQL remains the stated direction; before real production users or independently authored production data, an approved data-promotion mechanism must replace database-file deployment and preserve operational records. That mechanism is not designed or implemented here.

Storage
Development: Local filesystem
Future: Cloud object storage (AWS S3 or Cloudflare R2)

Frontend
Django Templates
Vanilla HTML
Vanilla CSS
Minimal JavaScript
No React or SPA framework is planned.

4. Architectural Principles
RigArchive follows the Engineering Handbook architecture:

Presentation
↓
Application Services
↓
Domain Models
↓
Infrastructure

Views remain thin.
Business workflows belong in services.
Models enforce domain invariants.
Infrastructure remains replaceable.

Reference Domain
The Reference Domain is the canonical factory configuration model for supported vehicles.
It models stable engineering identities and factory configuration logic.
It is intentionally distinct from observations, evidence, maintenance history, compatibility knowledge, and other derived information.

5. Current Django Apps
Implemented:
- core (Shared abstract infrastructure mixins: UUIDModel, TimestampedModel, BaseModel)
- accounts (Custom user identity)
- reference (Canonical vehicle reference domain)
- observation (Observation Domain foundation: recorded statements and capture context)
- measurements (Physical measurement definitions/results and applicability conditions; recorded results are not automatically verified)

Inventory reconciliation (2026-10-27): `measurements` was already installed; its omission from this list was documentation drift, not a new application added by this task.

Future application boundaries remain intentionally undecided.

Candidate future domains include:

- Evidence
- Knowledge
- Media / Assets
- Compatibility
- Maintenance
- Projects

The final application structure will be determined through incremental implementation rather than fixed in advance.

6. Completed Milestones
Milestone 1 — Project foundation (Completed)
- Django project
- Git & GitHub repository
- Development environment
- SQLite configuration
- Custom User model
- Initial migrations
- Test infrastructure

Milestone 2 — Reference Domain (Completed)
- Models: Manufacturer, VehicleModel, Generation, VehicleDefinition
- Features: UUID identity, Integer DB PKs, Automatic immutable slug generation, Protected foreign keys, Validation rules, Django Admin, Unit tests

Milestone 2A — Public Reference Browser (Completed)
- Views: Homepage, Manufacturer list/detail, Vehicle model detail, Generation detail, Vehicle definition detail
- Features: Nested URLs, Breadcrumb navigation, Responsive layout, Base template, Shared CSS, Public navigation
- Example URL: /vehicles/toyota/4runner/fourth-generation/2007-sr5-40l-v6-4wd-us/

Milestone 3 — Core Infrastructure (Completed — RA-003)
- App: core (`core.apps.CoreConfig`)
- Shared abstract model mixins: `UUIDModel`, `TimestampedModel`, `BaseModel`
- Refactored `reference` domain models to inherit from shared `core` mixins
- Added unit tests for abstract core mixins and inherited behavior

Milestone 3A — Application Shell & UX Foundation

Implementation Task:
RA-005 — Application Shell & UX Foundation (Completed)
- Views: Project-level presentation views (`about`, `custom_404`, `custom_500`) in `config/views.py`
- Shell: Accessible header, skip link (`<a class="skip-link" href="#main-content">`), main target (`<main id="main-content" tabindex="-1">`), non-numeric footer description
- Navigation: Primary nav linking Home, Vehicles, About, and Admin
- Error handling: Resilient custom 404 (`templates/404.html`) and custom 500 (`templates/500.html`) pages
- CSS: Accessible focus rings, breadcrumb list styles, hero/button styling, responsive 320px support in `static/css/site.css`

Milestone 5 — Development Data Preservation & Recovery Implementation

Implementation Task:
RA-009 — Development Data Preservation and Recovery Implementation (Completed)
- Management commands in `core/management/commands/`: `snapshot_db` (Layer 1 SQLite `VACUUM INTO` physical recovery snapshot with integrity verification), `export_dev_data` (Layer 2 natural-key JSON logical export), `verify_dev_data` (isolated OS temporary database restoration verification)
- Isolation: `RIGARCHIVE_TEST_DB_PATH` environment variable support in `config/settings.py` for isolated temporary database test execution
- Ignored storage: Local `backups/` directory (`backups/snapshots/` and `backups/logical/`) with `backups/.gitignore`
- Historical RA-009 Git hygiene record: Reported untracking `db.sqlite3` and all 26 compiled `.pyc` / `__pycache__` files while preserving local development files. This is historical milestone reporting, not the current database tracking state: Git currently tracks `db.sqlite3`, with a pre-existing unstaged modification; see EXP-01 checkpoint status.
- Preserved Database State: 2 Users, 1 Manufacturer, 1 VehicleModel, 1 Generation, 1 VehicleDefinition, 3 Observations
- Documentation: `docs/development/DATA_PRESERVATION.md` developer guide
- Design document: `docs/architecture/designs/RA-008-Development-Data-Preservation-Architecture.md`

Milestone 6 — Reference Data Ingestion Source & Mapping Architecture

Architecture/Research Task:
RA-010 — Reference Data Ingestion Source & Mapping Architecture (Approved Architecture)
- Design document: `docs/architecture/designs/RA-010-Reference-Ingestion-Source-Mapping-Architecture.md`
- Ingestion Pipeline Architecture: Decouples Source Acquisition -> Preserved Source Assertions -> Token-Based Normalization -> Candidate Configurations -> Reconciliation / Validation -> Human Review -> Approved Canonical Import -> Reference Domain
- Manufacturer Taxonomy Rule: Manufacturer's own market-specific configuration taxonomy governs trim/grade identity. Sub-grades (`SR5 Premium`, `Trail Premium`) are preserved as distinct trims. Packages/options not recognized by the manufacturer as distinct trims/grades do not independently create `VehicleDefinition` records
- Non-Lossy Normalization: Preserves rich technical specificity across 7 conceptual drivetrain dimensions (Classification, Architecture, Components, Operating Modes, Mode-Specific States, Capabilities, Manufacturer Terminology) regardless of primary model choice field bounds
- Source Authority & Reconciliation: Attribute-specific source precedence hypotheses (Manufacturer, EPA, NHTSA, J.D. Power) with categorical reconciliation status states (`corroborated`, `single_source`, `conflicting`, `ambiguous`, `incomplete`, `requires_review`)
- Idempotency & Protection: Future canonical import must be deterministic, duplicate-safe, and idempotent without creating duplicate records or overwriting manually validated Reference data (exact matching key/mechanism unresolved)
- Code / Schema Status: Architecture and research only. No Django models, migrations, acquisition tools, scrapers, DB records, or ingestion artifacts created

Milestone 7 — Ingestion Schema & Intermediate Serialization Design

Architecture/Research Task:
RA-011 — Ingestion Schema & Intermediate Serialization Design (Approved Architecture)
- Design document: `docs/architecture/designs/RA-011-Ingestion-Schema-Intermediate-Serialization-Design.md`
- Serialization Format & Versioning: JSON logical contracts with mandatory self-describing envelope (`artifact_type`, `schema_version` SemVer) supporting controlled schema evolution
- Two-Tier Serialization Architecture: Tier 1 `SourceAssertionSet` (<ingestion-runtime-root>/<source-artifacts>/) and Tier 2 `CandidateConfigurationDocument` (<ingestion-runtime-root>/<candidate-artifacts>/)
- Embedded Interpretation Layer: Traceable transformation from raw source assertion → normalized interpretation → candidate attribute
- Decoupled Candidate Context: Real-world vehicle context (`candidate_identity`) and source-specific configuration IDs preserved without mirroring database columns or fixing a canonical import matching key
- High-Fidelity Technical Representation: 7-dimension drivetrain contract, standard units + raw source strings, and preserved `factory_technical_features` (A-TRAC, CRAWL Control, KDSS, X-REAS) carrying both source presentation and unresolved classification status
- Separated Reconciliation & Review: Primary attribute evidence states (`corroborated`, `single_source`, `conflicting`, `ambiguous`, `incomplete`) logically separated from workflow review dispositions (`not_required`, `pending_review`, `resolved`, `rejected_excluded`)
- Deterministic Conventions: Alphabetical key sorting, ISO-8601 UTC timestamps, 2-space indentation, UTF-8 encoding for diffability
- Code / Schema Status: Architecture and research only. No Django models, migrations, serializers, acquisition tools, scrapers, DB records, or ingestion artifacts created

Milestone 8 — Intermediate Serialization Contract Implementation & Fixture Validation

Implementation Task:
RA-012 — Intermediate Serialization Contract Implementation & Fixture Validation (Completed)
- Package Location: `reference/ingestion/` (`__init__.py`, `contracts.py`, `serialization.py`, `validation.py`)
- Executable Contracts: Pure Python dataclasses representing Tier 1 `SourceAssertionSet` and Tier 2 `CandidateConfigurationDocument` with embedded `normalized_assertions`, 7-dimension drivetrain, preserved `factory_technical_features`, and separated reconciliation/review states
- Deterministic Serialization: `serialize_artifact` and `deserialize_artifact` enforcing alphabetical key sorting, 2-space indentation, UTF-8 encoding, ISO-8601 UTC timestamps, and lossless round-trips
- Unknown Field Preservation: Forward-compatible parser preserving unmodeled JSON fields in `unknown_fields` container without data loss upon re-serialization
- Contract Validation: `validate_artifact`, `validate_envelope`, `validate_source_assertion_set`, `validate_candidate_configuration`, and `validate_semantic_missing_value` with actionable error reporting
- Documentation & Task Record: `docs/implementation/tasks/RA-012-intermediate-serialization-implementation.md`

Milestone 9 — Public Source Acquisition Adapters (NHTSA & EPA)

Implementation Task:
RA-013 — Public Source Acquisition Adapters (Completed)
- Package Location: `reference/ingestion/acquisition/` (`__init__.py`, `base.py`, `nhtsa.py`, `epa.py`, `smoke_test.py`)
- Adapters Implemented: `NHTSAAdapter` (NHTSA vPIC REST API `GetModelsForMakeYear`) and `EPAAdapter` (EPA FuelEconomy.gov REST API `vehicle/{id}`)
- Transport Isolation & Security: `default_http_transport` using standard library `urllib.request` with strict TLS certificate verification (`ssl.create_default_context()`), finite timeouts, and explicit User-Agent headers (`RigArchive-Ingestion/0.1.0`); unit tests use mock transport loading test fixtures with zero network calls
- Tier 1 Payload Construction: Converts acquired raw source payloads into valid RA-012 `SourceAssertionSet` objects preserving provenance (`source_id`, `source_type`, `source_locator`, `retrieved_at`, `native_record_id`, `target_context`) and raw factual assertions without candidate normalization. FuelEconomy.gov `city08` and `highway08` map to Tier 1 keys `city_mpg_epa_rating` and `highway_mpg_epa_rating`.
- Response Fixtures: 2 acquisition response fixtures in `reference/tests/fixtures/acquisition/` (`nhtsa/get_models_toyota_2020.json`, `epa/vehicle_42101.json`)
- Live Smoke Test Utility: `smoke_test.py` (`run_all_live_smoke_tests`) for on-demand live API connectivity verification
- Zero ORM / Migration Impact: Pure Python data structures; 0 Django ORM staging models, 0 migrations, 0 database writes, 0 production storage path decisions
- Documentation & Task Record: `docs/implementation/tasks/RA-013-public-source-acquisition-implementation.md`

Milestone 10 — Source Assertion Normalization & Mapping Architecture

Architecture Task:
RA-014 — Source Assertion Normalization & Mapping Architecture (Approved Architecture)
- Design Document Location: `docs/architecture/designs/RA-014-Source-Assertion-Normalization-Mapping-Architecture.md`
- Source-Specific Normalization Ownership: Logic partitioned by source behind shared normalization contract (`NHTSANormalizer`, `EPANormalizer` in `reference/ingestion/normalization/`)
- Evidence-Bounded Normalization Rule: Normalization may only add semantic specificity supported by source assertions + explicit mapping rules; manufacturing unsupported drivetrain modes, ratios, lock states, or capabilities is prohibited
- Transformation Taxonomy: 6 explicit categories (`direct_copy`, `exact_mapping`, `parsed`, `converted`, `interpreted`, `unmapped`)
- Concept Key Strategy: Stable lower_snake_case keys decoupled from Django ORM field names; current concept set treated as provisional
- Semantic Qualifier Preservation: Technical qualifiers (`epa_rating`, `unadjusted`, `measured`, `estimated`) must not be stripped during normalization
- Redesigned Unmapped Behavior: Explicit separation of Case A (known concept, unmapped value) from Case B (unknown concept) without pseudonormalizing raw values
- Drivetrain & Feature Boundaries: 7-dimension drivetrain boundary enforced; unclassified features (KDSS, A-TRAC) remain under `factory_technical_features` as unresolved
- Category C Mappings Authorized for RA-015: 12 empirically validated mappings (`nhtsa_make_id`, `make`, `nhtsa_model_id`, `model`, `model_year`, `generic_drive_classification`, `drivetrain_architecture`, `engine_displacement_liters`, `engine_cylinders`, `city_mpg_epa_rating`, `highway_mpg_epa_rating`)

Milestone 11 — Source Assertion Normalization Implementation & Fixture Validation

Implementation Task:
RA-015 — Source Assertion Normalization Implementation & Fixture Validation (Completed)
- Package Location: `reference/ingestion/normalization/` (`__init__.py`, `base.py`, `nhtsa.py`, `epa.py`, `rules/__init__.py`, `rules/nhtsa_rules.py`, `rules/epa_rules.py`)
- Source Normalizers Implemented: `NHTSANormalizer` (`source_id: "nhtsa_vpic"`) and `EPANormalizer` (`source_id: "epa_fueleconomy"`) extending `BaseSourceNormalizer` and dispatched via top-level function `normalize_source_assertions(assertion_set)`
- Implemented Mappings: Strictly the 12 Category C mappings authorized by RA-014 (NHTSA: `make_id` -> `nhtsa_make_id`, `make_name` -> `make`, `model_id` -> `nhtsa_model_id`, `model_name` -> `model`; EPA: `model_year` -> integer, `make` -> direct copy, `drive_descriptor` -> `generic_drive_classification: "4WD"` & `drivetrain_architecture: "part_time_4wd"`, `engine_displacement_liters` -> `TechnicalValue`, `engine_cylinders` -> integer, `city_mpg_epa_rating` -> integer, `highway_mpg_epa_rating` -> integer)
- Evidence Safety Enforcement: Zero unsupported drivetrain modes (`2H`, `4H`, `4L`), low-range ratios, lock states, or capabilities manufactured; zero Category B mappings implemented
- Unmapped & Error Handling: Case A (known concept, unmapped value) preserves target concept key with `mapping_status: "unmapped"`; Case B (unknown attribute key) emits no `NormalizedInterpretation` while preserving the `SourceAssertion` unchanged in `SourceAssertionSet`; parsing failures fail gracefully into `unmapped` status; unsupported sources raise `UnsupportedSourceError`

- Testing & Offline Validation: 9 comprehensive automated test methods in `reference/tests/test_normalization.py` verifying contract dispatch, Category C mappings, drivetrain safety, unmapped handling, parsing failure handling, determinism, and offline adapter integration (67 total tests passing)
- Zero ORM / Migration Impact: Pure Python dataclasses; 0 Django ORM models, 0 migrations, 0 database writes
- Documentation & Task Record: `docs/implementation/tasks/RA-015-source-assertion-normalization-implementation.md`
Milestone 12 — Candidate Configuration Construction & Aggregation Architecture

Architecture Task:
RA-016 — Candidate Configuration Construction & Aggregation Architecture (Approved Architecture)
- Design Document Location: `docs/architecture/designs/RA-016-Candidate-Configuration-Construction-Aggregation-Architecture.md`
- Candidate Configuration Boundary: Transient, non-canonical, JSON-serializable artifact (`CandidateConfigurationDocument`) representing an evidence-backed hypothesis; completely separate from persistent canonical database entities (`VehicleDefinition`)
- Hybrid Context/Evidence Grouping Model: Caller-supplied `CandidateIdentity` provides workflow aggregation context, but is NOT source evidence and NOT canonical truth; normalized source evidence may support, contradict, or leave context unverified
- Separation of Evidence Reconciliation from Context Verification: `reconciliation_state = "conflicting"` is strictly reserved for evidence-to-evidence conflicts (2+ independent lineages disagreeing); candidate-context contradiction does not alter or manufacture evidence states, while context contradiction triggers top-level human review
- Lineage-Based Corroboration: `corroborated` requires 2+ independent evidence lineages (e.g. `nhtsa_vpic` vs `epa_fueleconomy`); repeated retrieval of the same source record yields `single_source`; multiple interpretations derived from one assertion represent one lineage
- No Tier 1 Normalization Bypass: Candidate attributes and `factory_technical_features` are projected ONLY from approved mapped `NormalizedInterpretation` objects emitted by RA-015; current RA-015 mappings yield `factory_technical_features = []`
- Conflict-Safe Projection & No Winner Selection: Under evidence conflict, scalar projected fields are left UNSET (`None`) while ALL conflicting interpretations, provenance links, and `conflicting` states are retained; winner selection is strictly prohibited
- Review Policy Consistency: `incomplete` state alone does NOT trigger human review (`requires_human_review = False`); automatic review is triggered strictly by evidence conflict (`conflicting`), evidence ambiguity (`ambiguous`), or context contradiction (`contradicted`)
- Transient Non-Semantic `candidate_reference`: Opaque, non-semantic workflow identifier; no semantic hashing from identity fields
- Semantic Determinism: Identical semantic inputs produce identical projected attributes, evidence states, provenance maps, and deterministic array ordering; artifact-generation metadata (`created_at`) may vary per instantiation
- Outcome B Contract Support: Existing RA-011/RA-012 contract is 100% sufficient using implementation conventions; zero contract modifications required for RA-017; formal context-verification enum persistence remains deferred
Milestone 13 — Candidate Configuration Construction & Aggregation Implementation

Implementation Task:
RA-017 — Candidate Configuration Construction & Aggregation Implementation (Completed)
- Package Location: `reference/ingestion/candidate/` (`__init__.py`, `builder.py`)
- Candidate Builder Implemented: Pure Python `construct_candidate_configuration` transforming caller `CandidateIdentity` workflow context, Tier 1 `SourceAssertionSet` artifacts, and Tier 2 `NormalizedInterpretation` objects into transient, non-canonical `CandidateConfigurationDocument` artifacts
- Context vs Evidence Separation: Caller-supplied `CandidateIdentity` is aggregation context, not source evidence; evidence (`make`, `model`, `model_year`) verifies or contradicts context without overwriting `CandidateIdentity`
- Lineage & Corroboration Boundary: `corroborated` requires 2+ independent `source_id` authorities; repeated retrieval of same record yields `single_source`; multiple records from same source yield `single_source` (same-source multi-record independence deferred)
- Conflict-Safe Projection & No Winner Selection: Under true independent-source conflict, scalar projected fields (`engine.cylinders`, `drivetrain.architecture`) are left UNSET (`None`), all evidence is preserved, and human review is required
- Concept Handling: Category A projected concepts receive typed destinations, `attribute_provenance`, and `attribute_states`; Category B mapped-but-not-projected concepts (`city_mpg_epa_rating`, `highway_mpg_epa_rating`) and Category C unmapped concepts remain preserved in `normalized_assertions` without fake candidate fields
- Tier 1 Bypass Prohibition: Consumes only approved mapped interpretations; raw Tier 1 descriptor strings (KDSS, A-TRAC) produce `factory_technical_features = []`
- Context Contradiction & Review Workflow: Contradictory evidence flags `requires_human_review = True`, sets `review_workflow_disposition = "pending_review"`, and records notes in `reconciliation_notes` without altering evidence reconciliation states
- Provenance & Serialization: Transitive assertion lookup verifies all `source_assertion_ref` links across multi-source payloads; includes `TechnicalValue` serialization interoperability fix in `reference/ingestion/serialization.py`
- Testing & Offline Validation: 13 comprehensive test methods in `reference/tests/test_candidate_construction.py` (80 total project tests passing)
- Zero ORM / Migration Impact: Pure Python dataclasses; 0 Django ORM models, 0 migrations, 0 database writes
Milestone 14 — Canonical Reference Matching & Import Architecture

Architecture Task:
RA-018 — Canonical Reference Matching & Import Architecture (Approved Architecture)
- Design Document Location: `docs/architecture/designs/RA-018-Canonical-Reference-Matching-Import-Architecture.md`
- Architectural Decision Record: `docs/architecture/ADR/ADR-0004-Canonical-Reference-Matching-Import-Promotion-Strategy.md`
- Candidate-to-Canonical Promotion Boundary: Two-tier architecture separating transient non-canonical `CandidateConfigurationDocument` artifacts from persistent database `VehicleDefinition` records
- Strict Evidence Trust Boundary: Source evidence governs canonical data; caller `CandidateIdentity` context cannot be written into canonical fields as source evidence. `CandidateIdentity.trim_name = "SR5"` without normalized evidence requires review and blocks auto-creation
- Database Representation Key vs Identity: `(generation_id, slug)` is current storage uniqueness key and deterministic representation key for identical current representations; it is not universal real-world identity
- Trim Sufficiency Policy: `trim_name = ""` represents missing trim evidence; candidates lacking normalized trim on multi-trim model years require human review (`REQUIRES_HUMAN_REVIEW`)
- Initial Create-Only & No-Op Policy: Automated importer creates proven-distinct new records and executes no-ops on exact existing matches; NEVER updates existing records, NEVER deletes records, and NEVER automatically creates parent `Manufacturer`, `VehicleModel`, or `Generation` entities
- Plan-First Architecture: Transient in-process `CanonicalImportPlan` handles read-only eligibility and parent resolution prior to transactional execution
- Controlled 2020 4Runner Assessment: Current NHTSA/EPA evidence lacks normalized trim, planning cleanly into `REQUIRES_HUMAN_REVIEW` (no-write), safely protecting canonical Reference data
- Zero ORM / Migration Impact: Architecture and design document pass; 0 Django ORM models, 0 migrations, 0 database writes, 0 application code changes
Milestone 15 — Canonical Reference Import Planning & Create-Only Execution Implementation

Implementation Task:
RA-019 — Canonical Reference Import Planning & Create-Only Execution Implementation (Completed)
- Package Location: `reference/ingestion/importing/` (`__init__.py`, `planner.py`, `importer.py`)
- Promotion Pipeline: Implemented pure Python read-only planning `plan_candidate_import(candidate)` and transactional create-only execution `execute_candidate_import(plan)` promoting `CandidateConfigurationDocument` artifacts into canonical `VehicleDefinition` records
- Transient Import Types: `ImportEligibilityStatus`, `ImportPlannedAction`, `ImportExecutionOutcome`, `ImportCreateBasis`, `CanonicalImportPlan`, `CanonicalImportResult` re-exported in `reference/ingestion/__init__.py`. `CanonicalImportPlan` remains transient, non-persistent, and in-process
- Strict Evidence Trust Boundary: Canonical facts are derived strictly from mapped `candidate.normalized_assertions` across 8 required concepts (`make`, `model`, `model_year`, `generic_drive_classification`, `engine_displacement_liters`, `engine_cylinders`, `trim`, `market`). Caller-supplied `CandidateIdentity` context (`manufacturer_name`, `vehicle_model_name`, `trim_name`, `market`) is checked ONLY for contradiction signaling and does NOT supply missing canonical evidence
- Direct Evidence Consistency: Evaluates mapped values directly as sets (`len(distinct)`). Multiple unequal normalized values for any concept flag `REQUIRES_REVIEW` (`FLAG_REVIEW`). Zero source precedence or winner selection
- Parent Resolution: Deterministic lookup against active database records (`Manufacturer`, `VehicleModel`, `Generation`). Exactly 1 match resolves; 0 or >1 matches trigger `INELIGIBLE` or `REQUIRES_REVIEW`. Importer NEVER automatically creates parent entities
- Target Field & Engine Representation: Target dictionary contains ONLY current `VehicleDefinition` fields (`model_year`, `trim_name`, `engine_name`, `drivetrain`, `market`). Engine display string formatted via `_format_engine_name` (e.g. `"4.0L V6"`). Free-text `engine_name` string inequality is NOT used as proof of mechanical distinctness
- Mechanical Dimension: Candidate v1 retains the legacy drivetrain comparison, including mixed-drive namespaces used by the historical bootstrap. It cannot establish an engine-based create from display labels. Candidate v2 uses the drivetrain basis when no same-drive peer exists. When a same-drive peer exists, the candidate must supply structured displacement and cylinder count linked to retained descriptor evidence, and every active same-trim, same-drive peer must have a matching creation receipt with retained engine evidence. Different displacement or cylinder count can establish the distinction. Equal, missing, or conflicting dimensions remain review-required. Manifest 2.0 binds the proof, and the importer recomputes it inside the create transaction. The JL rehearsal and live import verified sequential mechanical creates.
- Controlled Production 4Runner Behavior: Default production NHTSA/EPA candidates (lacking mapped `trim` and `market`) plan to `REQUIRES_REVIEW` / `FLAG_REVIEW` performing ZERO database writes
- Stale-Plan Revalidation: Inside `transaction.atomic()`, `FIRST_REPRESENTATION` plans verify namespace `(generation_id, model_year, market)` remains empty. `MECHANICAL_DIMENSION` plans verify `mechanical_basis_existing_id` record remains unchanged in generation, model_year, market, trim_name, drivetrain, and namespace count. Changed namespaces or modified basis records return `ABORTED_STALE_PLAN`
- Transaction & IntegrityError Safety: Execution runs inside `transaction.atomic()` with pre-save `full_clean()`. `IntegrityError` caught outside failed atomic block after rollback completes: exact field match yields `NO_OP_EXACT_MATCH`; conflicting fields yield `REJECTED`
- Create-Only Policy: Zero automatic `VehicleDefinition` updates, zero deletes, zero parent auto-creations
- Testing & Verification: 26 focused test methods in `reference/tests/test_canonical_import.py` (106 total project tests passing)
- Zero ORM / Migration Impact: Pure Python import engines; 0 Django ORM schema changes, 0 migrations

Milestone 16 — Trim/Grade & Market Applicability Source and Normalization Architecture

Architecture Task:
RA-020 — Trim/Grade & Market Applicability Source and Normalization Architecture (Approved Architecture)
- Design Document Location: `docs/architecture/designs/RA-020-Trim-Grade-Market-Applicability-Source-Normalization-Architecture.md`
- Architectural Decision Record: `docs/architecture/ADR/ADR-0005-Manufacturer-Grade-Taxonomy-Market-Applicability-Normalization.md`
- Manufacturer Grade Taxonomy: Defines `trim` as manufacturer-recognized factory grade/trim identity (`SR5`, `SR5 Premium`, `TRD Off-Road`, `Limited`). Disambiguates factory grades from dealer accessory packages (e.g. `XP Predator`) which belong in Observation/Knowledge domains
- Commercial Sales Market Definition: Defines `VehicleDefinition.market` as manufacturer commercial sales/applicability market (`US`, `CA`, `OT`), distinguishing commercial market from regulatory jurisdiction
- Source-Independence Test: Enforces that market applicability may become normalized evidence ONLY when independently established by the source artifact or acquisition definition. Prohibits laundering caller request context (`CandidateIdentity` or `target_context`) into canonical facts
- Explicit Source Applicability Provenance: Recommends `source_applicability` provenance metadata structure (`market`, `applicability_basis`, `publisher_jurisdiction`) attached to `SourceMetadata`
- Preserved-Only Candidate Projection: Retains `trim` and `market` as preserved-only mapped normalized assertions in `normalized_assertions` (Category B), satisfying RA-019 promotion without requiring contract changes
- Cross-Source JOIN Rule & Cartesian Prohibition: Attribute equality alone is NOT a configuration join key. Candidate construction MUST NOT generate unsupported Cartesian combinations (8 grades x 3 EPA records != 24 candidates). Requires evidence-backed configuration correspondence
- Manufacturer Acquisition Abstraction: Recommends reusable `ManufacturerSpecificationAdapter` / `StructuredDatasetAdapter` decoupling generic acquisition from manufacturer-specific mapping/taxonomy rules
- Controlled 2020 4Runner Study: Verified 8 U.S. factory grades, Toyota terminology ("Grade"), and 4-digit order model codes (`8666`) providing source-native configuration identity (`SourceConfigurationIdentity`)

Milestone 17 — Manufacturer Specification Evidence Acquisition & Normalization Implementation

Implementation Task:
RA-021 — Manufacturer Specification Evidence Acquisition & Normalization Implementation (Completed)
- Task Record Location: `docs/implementation/tasks/RA-021-manufacturer-specification-evidence-acquisition-normalization-implementation.md`
- Package Components: `reference/ingestion/acquisition/manufacturer.py`, `reference/ingestion/normalization/manufacturer.py`, `reference/ingestion/normalization/rules/toyota_rules.py`, `reference/tests/fixtures/acquisition/toyota/2020_4runner_specs.json`, `reference/tests/test_manufacturer_ingestion.py`
- SourceApplicability Contract: Implemented `SourceApplicability` dataclass (`market`, `applicability_basis`, `publisher_jurisdiction`, `unknown_fields`) attached to `SourceMetadata`. Decoupled from `target_context` with zero automatic context-to-applicability conversion
- Schema Backward Compatibility: Retained major `schema_version = "1.0.0"`. Optional metadata field addition is 100% backward-compatible with legacy deserialization (`source_applicability = None`) and positional constructor safety
- Controlled Toyota USA Fixture: Added `2020_4runner_specs.json` containing 12 official Toyota US model-code configurations (`8664`–`8692`) and complete first-party pressroom provenance metadata
- One SourceAssertionSet Per Configuration: `ManufacturerSpecificationAdapter` emits one `SourceAssertionSet` per model-code configuration row, preserving `provenance.native_record_id` and attribute coexistence without list-order inference
- SourceConfigurationIdentity Preservation: Candidate builder extracts `SourceConfigurationIdentity` (`source_id = "toyota_usa"`, `identity_type = "record_id"`, `native_identifier = "8666"`)
- Manufacturer Normalization & Toyota Rules: `ManufacturerNormalizer` and `toyota_rules.py` enforce exact uppercase factory grade lookup (`SR5`, `TRD Off-Road`, `Limited`, `TRD Pro`). Dealer option packages (`XP PREDATOR`, `PREMIUM AUDIO`) default safely to `mapping_status = "unmapped"`
- Source-Independence Test Enforcement: Mapped `market` normalized assertion (`"US"`) is emitted ONLY when `source_applicability` is present and matches the market assertion. `target_context` market alone is rejected
- Concept & Drivetrain Reuse: Reuses standard `make`, `model`, `model_year`, `generic_drive_classification`, `drivetrain_architecture` (`Full-Time 4WD` $\rightarrow$ `AWD`), `engine_displacement_liters` (`TechnicalValue`), and `engine_cylinders`. `transmission_descriptor` remains raw/unmapped
- Preserved-Only Projection & Candidate Building: `construct_candidate_configuration` aggregates mapped `trim` and `market` as preserved-only mapped assertions (Category B) with zero candidate builder contract changes
- Zero Cross-Source Joins & Cartesian Safety: Zero automatic Toyota/EPA/NHTSA joins. 12 configuration rows produce exactly 12 candidate documents without Cartesian expansion
- RA-019 Downstream Planning Reachability: Fully evidenced candidates supply all 8 required concepts (`make`, `model`, `model_year`, `generic_drive_classification`, `engine_displacement_liters`, `engine_cylinders`, `trim`, `market`), reaching `ImportEligibilityStatus.ELIGIBLE` / `ImportPlannedAction.CREATE` / `ImportCreateBasis.FIRST_REPRESENTATION` under `plan_candidate_import`
- Context Contradiction Correction: Extended `planner.py` to check `CandidateIdentity.trim_name` and `CandidateIdentity.market` against mapped evidence. Contradictions trigger `REQUIRES_REVIEW` / `FLAG_REVIEW`
- Test Baseline: 16 focused tests in `reference/tests/test_manufacturer_ingestion.py` (122 total project tests passing)
- Zero ORM / Migration Impact: Pure Python ingestion adapters and normalizers; 0 Django ORM schema changes, 0 migrations, 0 database writes

Milestone 18 — Production Manufacturer Evidence Acquisition & Orchestration Architecture

Architecture Task:
RA-022 — Production Manufacturer Evidence Acquisition & Orchestration Architecture (Approved Architecture)
- Design Document Location: `docs/architecture/designs/RA-022-Production-Manufacturer-Evidence-Acquisition-Orchestration-Architecture.md`
- Architectural Decision Record: `docs/architecture/ADR/ADR-0006-Immutable-Raw-Acquisition-Snapshots-Layered-Manufacturer-Profiles.md`
- Empirical Cross-Manufacturer Validation: RA-022A research study validated profile layering across Toyota USA, Ford Motor Company, Jeep/Stellantis, and Mercedes-Benz USA, confirming that publication structures and taxonomy vocabulary vary across and within manufacturer ecosystems
- Layered Profile Architecture: Separates `ManufacturerProfile` (taxonomy mappings, package classification, identity semantics) from `PublicationSourceProfile` (locators, fetch options, snapshot capture, extractors). Rejects monolithic per-manufacturer adapters
- Immutable Raw Source Snapshots: Requires all production acquisition operations to retain acquired raw source payloads (HTML, JSON, PDF, CSV, XLS) immutably in raw source artifact storage (`storage/raw_source_artifacts/`) before extraction occurs. Changed locators/content generate new snapshots
- Full SHA-256 Content Hashing & Revisions: Uses full 64-character SHA-256 hex digest for durable content hashing and revision tracking. Shortened hashes are display-only
- Source-Native & Structural Row Identity: Explicit codes (Toyota `8666`, Ford `E5B`, Jeep `JLJL74`) populate `SourceConfigurationIdentity` (`identity_type = "model_code"`). Uncoded sources (Mercedes-Benz `media.mbusa.com`) use source-local structural row identity (`identity_type = "structural_row"`). Rejects synthetic attribute-derived `composite_row` identity
- Explicit Multi-Document Linking: Cross-document configuration joins require explicit, evidence-backed manufacturer cross-reference keys. Joining unlinked documents via matching string names is strictly prohibited
- Plan-First Production Orchestration Boundary: Production acquisition orchestration stops automatically at `plan_candidate_import()`, producing an in-memory `CanonicalImportPlan` dry-run report. Zero automatic database writes (`execute_candidate_import`) are performed
- Initial Operating Mode: Operator-invoked CLI execution. Schedulers, crawlers, and dynamic headless browsers are excluded from initial scope
- Proposed Next Milestone: RA-024 — Canonical Reference Import Execution & Execution Provenance Workflow Architecture & Implementation

Milestone 20 — Canonical Reference Import Execution & Execution Provenance Workflow Implementation

Implementation Task:
RA-024 — Canonical Reference Import Execution & Execution Provenance Workflow Implementation (Completed)
- Design Document: `docs/architecture/designs/RA-024-Canonical-Reference-Import-Execution-Execution-Provenance-Workflow-Architecture.md`
- Architectural Decision Record: `docs/architecture/ADR/ADR-0007-Explicit-Human-Authorization-Execution-Audit-Receipts-Canonical-Promotion.md`
- Review Manifest Contract: Pure-Python dataclasses (`CanonicalImportReviewPlan`, `CanonicalImportReviewManifest`, `v1.0`) for serializing, validating, and reconstructing operator-reviewed import plans prior to execution dispatch (`reference/ingestion/manifest.py`)
- Deterministic Compact SHA-256 Hashing: `compute_manifest_hash()` computes a deterministic digest (`sha256:<64_hex>`) over sorted UTF-8 JSON key canonicalization (`separators=(",", ":")`). File indentation does not invalidate parsed dictionary hash; payload modification invalidates hash
- Strict Validation & Type Safety: `dict_to_manifest()` rejects unknown top-level and per-plan fields, duplicate candidate references, and invalid enum values. Integer fields (`namespace_snapshot_count`, `mechanical_basis_existing_id`, `resolved_manufacturer_id`, `resolved_vehicle_model_id`, `resolved_generation_id`, `existing_vehicle_definition_id`) accept strictly `int` or `None`, explicitly rejecting `bool` (`True`, `False`), `float` (`1.0`), and numeric strings (`"1"`)
- Exact Plan Reconstruction: `reconstruct_plan_from_manifest()` instantiates `CanonicalImportPlan` directly from reviewed manifest fields with **ZERO** dynamic re-planning calls (`plan_candidate_import`)
- Execution Audit Receipts: Created `ImportExecutionReceipt` ORM model (`reference/models.py`) and migration `0002_importexecutionreceipt.py`. Captures `executed_at`, `operator_label`, `manifest_hash`, evidence anchors (`source_id`, `raw_artifact_hash`, `raw_artifact_reference`, `source_identity_type`, `native_identifier`), target configuration snapshot, actual outcome (`CREATED`, `NO_OP_EXACT_MATCH`, `ABORTED_STALE_PLAN`, `REJECTED`), output messages, and `on_delete=models.SET_NULL` FKs + primary identity snapshots (`pk_snapshot`, `uuid_snapshot`, `slug_snapshot`) guaranteeing audit log survival
- Read-Only Django Admin Viewer: `ImportExecutionReceiptAdmin` (`reference/admin.py`) sets `has_add_permission = False`, `has_change_permission = False`, `has_delete_permission = False`, with all fields read-only
- Transactional Workflow Engine: `execute_canonical_import_workflow()` (`reference/ingestion/importing/workflow.py`) wraps `CREATE` operations inside `transaction.atomic()`, ensuring `VehicleDefinition` creation and `ImportExecutionReceipt` persistence succeed together or roll back cleanly
- Explicit Human Authorization CLI: `execute_canonical_import` management command (`reference/management/commands/execute_canonical_import.py`) enforces mandatory interactive operator confirmation (`input("Do you authorize... [y/N]")`) on every run. Intentionally omits `--no-input` flag to guarantee human confirmation
- Production Acquisition Dry-Run Manifest Output: Extended `acquire_manufacturer_specs` (`reference/management/commands/acquire_manufacturer_specs.py`) with `--output-manifest <path>` to emit executable review manifests during production dry-runs with guaranteed **ZERO** canonical database writes
- Test Baseline: 16 focused tests in `reference/tests/test_canonical_import_execution.py` (164 total project tests passing)

Milestone 21 — Production Manufacturer Extraction & Review-Adjudication Architecture

Architecture Task:
RA-025 — Production Manufacturer Extraction & Review-Adjudication Architecture (Approved Architecture)
- Design Document Location: `docs/architecture/designs/RA-025-Production-Manufacturer-Extraction-Review-Adjudication-Architecture.md`
- Architectural Decision Record: `docs/architecture/ADR/ADR-0008-Deterministic-Extraction-Review-Adjudication-Adjudicated-Grade-Promotion.md`
- Deterministic Extraction Boundary: Eliminates runtime sidecar JSON file (`2020_4runner_specs.json`) from production candidate construction path, operating deterministically from retained raw publisher snapshots via versioned strategy extractors (e.g. `ToyotaPressroomHtmlTableStrategy`)
- Golden Test Fixture Strategy: Retains `2020_4runner_specs.json` in `reference/tests/fixtures/` strictly as golden test benchmarks to validate extractor `SourceAssertionSet` outputs against raw publisher snapshots
- Review-Adjudication Boundary: Formalizes `CanonicalImportAdjudication` contract as a durable human domain finding (`adjudication_hash = "sha256:<64_hex>"`) for bounded adjudicable review conditions (`distinct_factory_grade`, `special_edition_grade`)
- Five-Stage Promotion Lifecycle: Establishes explicit lifecycle (`Planning` -> `Adjudication` -> `Re-planning` -> `Execution Authorization` -> `Execution`). Adjudication does NOT execute directly and does NOT inherit old authorizations
- Third Epistemic Basis (`ADJUDICATED_DISTINCT_GRADE`): Introduces `ImportCreateBasis.ADJUDICATED_DISTINCT_GRADE` to represent human-reviewed proof of a legitimate factory grade in a populated namespace, preserving existing `FIRST_REPRESENTATION` and `MECHANICAL_DIMENSION` semantics
- Exact-Plan Preservation: Execution NEVER converts one `create_basis` into another. Stale database conditions abort with `ABORTED_STALE_PLAN`, requiring fresh planning and a NEW review manifest
- Stale Revalidation Rules: An `ADJUDICATED_DISTINCT_GRADE` plan is stale if parent entities become inactive or a same-trim canonical row appears prior to execution. Unrelated trim growth is non-material
- Review Manifest Versioning (v1.1): Supports optional per-plan `adjudication_reference` and `adjudication_hash` while maintaining 100% executable backward compatibility for v1.0 manifests
- Execution Receipt Linkage: Extends `ImportExecutionReceipt` with optional `adjudication_hash` to record complete audit lineage from raw snapshot to canonical creation
- Controlled 2020 Toyota Study: Establishes that populating 12 2020 4Runner configurations requires **12 separately authorized executions** under RA-024 (`[y/N]`), of which **7 require human domain adjudications** and 5 derive from automated bases (1 `FIRST_REP` + 4 `MECH_DIM`)
- Next Planned Milestone: RA-026 — Deterministic Toyota Extraction & Review-Adjudication Implementation

Milestone 31 — Complete Fifth Generation & Add Sixth Generation Toyota 4Runner

Implementation Task:
RA-039 — Complete Fifth Generation & Add Sixth Generation Toyota 4Runner (Completed)
- Completed US-market Toyota 4Runner archive population across 5th Generation (2010–2024, 137 active canonical `VehicleDefinition` records) and 6th Generation (2025–2026, 28 active canonical `VehicleDefinition` records).
- Established `Sixth Generation` (`slug="sixth-generation"`, `start_year=2025`, `end_year=None`) taxonomy in Wikipedia extractor and database models, preserving ongoing generation status (`2025–present`).
- Created 15 evidence-backed J.D. Power configuration fixtures for 2010–2018, 2021–2024, 2025, and 2026.
- Preserved existing 2019/2020 5th Gen canonical records and 1st–4th Gen inventories 100% intact without unintended overwrite or duplicate creation.
- Updated `JDPowerExtractor` and `JDPowerNormalizer` to extract and process `engine_name` assertions, and `planner.py` to prefer explicit mapped `engine_name` concepts, correctly distinguishing non-hybrid (`2.4L Turbo I4`) and hybrid (`2.4L Turbo Hybrid I4`) powertrain identities.
- Executed `CanonicalRecordCorrection` supersession workflow (`correction_reason="SOURCE_EVIDENCE_CORRECTION"`) linking 13 imprecise 2025 rows to evidence-backed replacement rows.
- Generated temporary presentation image asset (`static/images/generations/toyota-4runner-sixth-generation.jpg`).

Powertrain Display / Identity Semantics — Deferred
- RA-039 Sixth Generation Toyota 4Runner ingestion exposed a future modeling question concerning the relationship between engine identity and overall powertrain identity.
- The current implementation composes characteristics such as displacement, forced induction, and electrification into a user-facing `engine_name` description (for example, terminology containing "Turbo" and "Hybrid").
- This is acceptable for current populated data but is NOT yet an approved long-term domain standard.
- Future architecture should determine whether characteristics including:
  - engine displacement;
  - cylinder/configuration architecture;
  - aspiration / forced induction;
  - combustion engine identity;
  - hybrid/electrification type;
  - electric motor configuration;
  - overall manufacturer powertrain/system identity;
  should remain represented in a composite engine description or instead be stored as independent structured technical attributes and composed into presentation labels.
- The design should anticipate powertrain types beyond the current Toyota example, including:
  - naturally aspirated ICE;
  - turbocharged/supercharged ICE;
  - conventional hybrids;
  - mild hybrids;
  - plug-in hybrids;
  - battery-electric vehicles;
  - multi-motor electrified systems.
- **Semantic Boundary**: This is a DEFERRED modeling decision. Current Sixth Generation 4Runner populated data is not being declared incorrect, RA-039 does not need to be reopened, no schema change or migration is authorized, no normalization redesign is authorized, and existing canonical records remain unchanged. The principal unresolved question is whether `engine_name` should represent a complete powertrain description or whether engine identity, forced induction, and electrification should be independent structured concepts composed for public display.

Milestone 32 — Operator Workflow Hardening

Implementation Task:
RA-040 — Operator Workflow Hardening: Eliminate Routine Ad-Hoc `python -c` Django Operations (Completed)
- Implemented `plan_generation_population` management command (`reference/management/commands/plan_generation_population.py`) to build, summarize, and optionally save deterministic `PopulationBatchManifest` JSON files without executing canonical database writes.
- Extended `inspect_reference_state` management command with `--by-year` flag to group matching `VehicleDefinition` records by `model_year` cleanly in text and JSON formats while preserving strict read-only guarantees.
- Standardized canonical routine generation ingestion sequence: `inspect_reference_state --by-year` -> `plan_generation_population -o <file>` -> `execute_population_batch --manifest <file>` -> `inspect_reference_state` -> verification commands, eliminating routine dependency on ad-hoc `.venv/bin/python -c` inline scripts.
- Preserved existing batch authorization boundaries, manifest hash verification, stale-plan revalidation, receipt audit provenance, and execution atomicity.
- Added comprehensive unit tests in `reference/tests/test_operator_workflow.py` bringing test suite to **272/272 tests passing cleanly**.

Milestone 33 — Compact Multi-Column Archive Navigation Cards

Implementation Task:
RA-041 — Compact Multi-Column Archive Navigation Cards (Completed)
- Converted `.archive-nav-grid` and `.generation-card-grid` navigation containers in `static/css/site.css` into responsive CSS Grid layouts (`grid-template-columns: repeat(3, minmax(0, 1fr))`) displaying 3 cards across desktop viewports.
- Responsive scaling collapses to 2 columns on tablet (`@media (max-width: 58rem)`) and 1 column on mobile (`@media (max-width: 38rem)`).
- Refined `.card-thumbnail-wrap` dimensions to 7.5rem (120px) x 4.5rem (72px) maintaining identical representative image aspect ratio and framing.
- Preserved 100% of existing semantic links, focus indicators, typography, and card click targets without requiring model-specific CSS or JavaScript dependencies.
- Added regression tests in `reference/tests/test_views.py` (`test_06_ra041_compact_multi_column_card_contracts`) bringing test suite to **273/273 tests passing cleanly**.

Milestone 34 — Measurements Domain Foundation Architecture

Implementation Task:
RA-042 — Measurements Domain Foundation Architecture (Approved Architecture — RA-042 / ADR-0009)
- Established approved foundation architecture for the Measurements domain ([ADR-0009](../architecture/ADR/ADR-0009-Measurements-Domain-Strategy.md) & [RA-042 Architectural Design Document](../architecture/designs/RA-042-Measurements-Domain-Foundation-Architecture.md)).
- Defined top-level domain boundary (`measurements/` app) decoupled from factory reference configurations (`reference`).
- Anchored physical vehicle measurements at `reference.Generation` level (`on_delete=models.PROTECT`).
- Separated reusable `MeasurementDefinition` (WHAT is measured) from `MeasurementResult` (measured numeric value and unit in a Generation context).
- Established result-owned unit policy (`MeasurementDefinition` specifies no canonical unit).
- Established controlled feature applicability model (`ApplicabilityFeature` + `ApplicabilityState`) to represent physical vehicle option factors without database schema changes or manufacturer trim/package duplication.
- Defined condition semantics: zero conditions = Generation-wide / All configurations; multiple conditions = conjunctive AND.
- Preserved multi-result evidence architecture (no uniqueness constraint across Generation + Definition + applicability; multiple independent measurements permitted).
- Defined provisional v1 cargo-height taxonomy (*Cargo Opening Height*, *Cargo Height Behind Second Row*, *Maximum Cargo Interior Height*).
- Specified vehicle-first public browser presentation (`GenerationMeasurementsView` at `/vehicles/<mfr>/<model>/<gen>/measurements/`) and designated RA-043 as the implementation milestone.

Milestone 35 — Measurements Domain Foundation Implementation

Implementation Task:
RA-043 — Measurements Domain Foundation Implementation (Completed)
- Created top-level `measurements` Django application (`measurements/`) and registered `measurements.apps.MeasurementsConfig` in `config/settings.py`.
- Implemented models (`MeasurementDefinition`, `ApplicabilityFeature`, `ApplicabilityState`, `MeasurementResult`, `MeasurementResultCondition`) with `BaseModel` dual identity (Integer PK + UUID) and timestamps.
- Implemented result-owned unit representation (`MeasurementResult.unit`) and protected deletion references to `reference.Generation`.
- Implemented controlled feature applicability key-value state structure (`ApplicabilityFeature` + `ApplicabilityState`).
- Implemented zero-condition Generation-wide applicability semantics and conjunctive multi-condition (AND) evaluation (`applicability_summary`).
- Enforced domain validation rejecting multiple states of the same `ApplicabilityFeature` on a single `MeasurementResult`.
- Confirmed multi-result coexistence policy (zero uniqueness constraints across `Generation + Definition + applicability`).
- Registered Django Admin interfaces in `measurements/admin.py` with inline condition and state editors.
- Created initial database migration `measurements/migrations/0001_initial.py`.
- Implemented `GenerationMeasurementsView` (`/vehicles/<mfr>/<model>/<gen>/measurements/`) and template `templates/measurements/generation_measurements.html` with empty-state handling and condition badge tags.
- Added Measurements link in Overview infobox sidebar on `templates/reference/generation_detail.html`.
- Added comprehensive semantic test suite in `measurements/tests/` bringing total test suite count to **295/295 tests passing cleanly**.

Mobile Archive Card Density & Generation Scrolling — Deferred
- RA-041 established a compact multi-column desktop layout (`grid-template-columns: repeat(3, minmax(0, 1fr))`) for archive and generation navigation cards.
- On mobile/narrow viewports, cards stack vertically at full width (`grid-template-columns: 1fr`). This remains functional and readable, but card/image height can produce excessive vertical scrolling for models with many generations (such as Toyota 4Runner) and manufacturers with many populated models.
- Future mobile UX work should evaluate a more compact card treatment optimized for scanability and reduced vertical travel.
- Potential approaches to evaluate later include:
  - reduced mobile thumbnail height;
  - controlled aspect-ratio cropping;
  - more compact title/year typography and spacing;
  - horizontally scrollable card rows/carousels where appropriate;
  - two-column compact cards on sufficiently wide mobile viewports;
  - progressive disclosure of generation lists;
  - alternate mobile-only card composition;
  - responsive image focal-point/crop handling once proper Asset/Media architecture exists.
- **Semantic Boundary**: This is a DEFERRED UX optimization. Current mobile behavior is acceptable and not considered broken, RA-041 does not need to be reopened, no immediate mobile-specific image assets are required, no CSS one-offs are authorized, no manufacturer/model-specific layout rules are authorized, and future optimization should remain generic and responsive.


Experimental Milestone EXP-01 — Experimental Vehicle Knowledge Hub & Homepage Redesign
Status: Work in progress / Pending final evaluation on `experiment/vehicle-hub-ui`; not complete or approved and not merged into `main`.
- **Boundary:** Presentation, navigation, and service-layer query coordination; no experiment model or migration changes. RA-EXP-02 vehicle-contextual navigation decisions are not implemented by this checkpoint.
- **Implemented:** Homepage photo/schematic hero, data-driven vehicle platform cards, Explore the Archive category cards, manufacturer/model-name search, and session-backed Recently Viewed generations. The former positioning headline, global statistics counter, Measured Reality showcase, and Four Pillars status presentation are absent from the current template; they remain earlier design intent, not current features.
- **Implemented:** Generation photo/identity panel, computed generation statistics, GET year/trim filters, service support for exact configuration slugs, measurement queries, and a year → trim → matching-configuration browser. Canonical routes and separate model-year/configuration destinations remain available. Task 1 relabels the third column Configuration and exposes exact canonical choices; no package schema is introduced. The intended grouped multi-year matrix and powertrain-chip overview remain absent.
- **Implemented:** Configuration specification sheet with identity, engine/drivetrain, notes, generation-wide measurement summaries, receipt information, return link, and same-year sibling links. Application services coordinate queries, but import the image helper from `reference.views`; full separation from presentation is not achieved.
- **Task 1 functional repair (verified):** Generation notes remain stored and available through the model/backend; the standalone Notes panel was intentionally removed in final cleanup. The single three-step configurator retains year, trim and exact-configuration selection, unnamed-trim support (`trim=`), selected-state styling, compact collision-safe labels, sibling choices and canonical Specs links. Configuration-only URLs resolve the year before choices are derived; explicit invalid/blank/mismatched years are not overridden. Trims/years never silently select an exact configuration. Upper dropdowns, Apply Filters and the selected-configuration summary were removed with the redundant Explore panel; GET fallback is now through the three-step links and its reset. Invalid-selection notices remain within the configurator. Canonical identity is available on the linked specification page, not an upper summary.

- **Task 2 technical integrity repair (verified):** Removed unsupported numerical dimensions from the Generation SVGs; remaining outlines are explicitly illustrative, not to scale or generation-specific geometry. Cargo-opening width is distinguished from wheel-well clearance. Generation, specification and dedicated measurement pages use recorded/report terminology, show all feature conditions with AND semantics, and preserve independent results as separate rows/cards with values, units, notes and applicability; UUIDs remain internal, not visible. Specification pages separate Generation-wide results from conditional reports whose exact-configuration applicability is not established. Receipt UI preserves source/native identifiers, hashes, creation basis and execution outcome without claiming independent verification; missing metadata is not fabricated. Approved Task 1 layout, labels, selection and scroll behavior are unchanged.
- **Remaining technical limits:** Measurement records have no structured source/evidence or verification-status fields, and configurations have no physical-feature-state mapping. Conditional applicability cannot be inferred from year/trim. Evidence-backed generation-specific illustrations, source reconciliation and definitive-result selection require future architecture/data. The separate homepage decorative schematic remains outside Task 2's Generation/configuration repair; no sitewide evidence-backed imagery claim is made.
- **Planned but unavailable:** Builds, service guides, Garage, generation history, platform/design articles, powertrain articles, model-year change articles, and production-number content. Some links target missing anchors; Measurements links use an ignored `view=measurements` parameter. Search prompts exceed the implemented manufacturer/model-name search. Empty future-domain sections do not establish that those domains exist.
- **Sitewide presentation repair:** Missing shared CSS components were restored in `static/css/site.css` for Vehicles, manufacturers, models, model years, specifications, measurements, About, and custom 404. Restoration includes directories, navigation cards/thumbnails, record details, applicability badges, empty states, prose, recovery buttons, wrapping, and responsive table containment. The project director visually confirmed the restoration as satisfactory. Django admin and standalone 500 presentation were not redesigned.
- **Final Task 1 layout refinement (provisional):** Removed Explore This Generation because it duplicated the three-step configurator. Moved the existing configurator, without duplication, immediately after the photograph/Generation overview and before Key Dimensions (the standalone notes panel was subsequently removed). Heading: Configurations & Specs; introductory text: “Explore available factory configurations by model year and trim. Select a configuration to view its detailed technical specifications.” The existing `#configurations` fragment, filter hooks and reset remain. The page-local script now replaces only that section; obsolete Explore form/change handlers were removed. In-place filtering, viewport/focus/history behavior, stale-response protection and native GET-link fallback are retained. Removed only the Service Guides subtitle/wrapper so Builds and Mods and Service Guides use matching heading rows; empty-state functionality is unchanged.
- **Provisional placement consideration:** As Generation pages accumulate more substantive measurements, builds, and maintenance content, the Configurations & Specs section may be reconsidered for placement below Key Dimensions or farther down the Generation page. This is future design consideration, not authorization to move it again. RA-EXP-01 remains WIP, not complete or approved; RA-EXP-02 navigation is not implemented.

- **Final Task 1 cleanup:** Removed the standalone Generation Notes panel without altering `Generation.notes`, stored values, backend access, schema or routes. Useful platform information (such as N180) is a future consideration for Generation Overview → Platform & Design, not implemented here. Removed the bottom-of-page visible update status. A visually hidden, polite/atomic live announcer now lives within Configurations & Specs outside the replaceable `#configuration-content` wrapper; the script updates only that wrapper so the announcer remains mounted. Focus, keyboard navigation, in-place selection, scrolling, compact labels, canonical Specs links and GET fallback are retained. Placement remains provisional and RA-EXP-01 remains WIP.
- **Task 1 verification:** Latest full suite after final cleanup: **307 executed, 307 passed, 0 failed** (initial Task 1: 297/297; compact refinement: 303/303; navigation correction: 305/305) using `RIGARCHIVE_TEST_DB_PATH=:memory:`. System check passed; `makemigrations --check --dry-run` detected no changes; `git diff --check` passed. Existing Python 3.14 and virtualenv site-packages were used because the virtualenv launcher cannot load its framework library. Tests now cover backend notes retention/panel absence, hidden persistent announcements, dependent controls, exact identity, unnamed/shared trims, invalid/mismatched/inactive/cross-generation choices, deterministic ordering, reset and empty states. Six additional UX tests cover fragments, GET/reset state, compact choices, label disambiguation, and canonical links; Prior compact-refinement run: 30 focused tests passed. Final cleanup: 53 focused Django tests and 11 executable Node DOM/Fetch-boundary behavior tests passed; JavaScript syntax check passed. Stale homepage/infobox/whitespace assertions were reconciled with the experimental presentation while preserving content and applicability requirements. Historical checkpoint result: 286 executed, 273 passed, 13 failed, with two CSS contract failures resolved by the earlier styling repair. RA-EXP-01 remains WIP pending final evaluation; Task 1 passing does not resolve technical-content or navigation limitations.
- **Task 2 final presentation cleanup:** The Generation measurement panel is Additional Measurements. Removed the long illustrative/result subtitles and visible measurement-result UUIDs, retaining concise Illustrative/not-to-scale labeling and separate records with original values/units/notes/conditions. Manufacturer-publication notes remain visible where recorded, without fabricated source metadata or verification claims. Photographs of physical measurements (including tape-measure location/value images) and manufacturer technical publications must eventually be distinguishable evidence forms; this is deferred architecture, not an implemented source classification or photographic capability.
- **Task 2 verification:** Latest final-presentation run: 91 focused Django tests, **319 full-suite Django tests** and 11 configurator JavaScript behavior tests passed with isolated resources. System check passed, migration-consistency dry-run found no changes, and whitespace checks passed. Added 12 tests covering unsupported diagrams, report/empty-state terminology, AND/unknown applicability, independent duplicates/units, receipt attribution/outcomes, escaping, and preserved ordering/selection. Task 1's 307-test result above is historical. Task record: `docs/implementation/tasks/RA-EXP-01-task-2-technical-information-integrity.md`. No model/schema, import or RA-EXP-02 changes.
- **Unverified:** Actual desktop/mobile browser scrolling and rendering, zoom/keyboard coverage, and outstanding functional fixes. JavaScript behavior tests execute the script with an instrumented DOM/Fetch boundary, not a real browser; they do not establish visual scroll correctness. Director visual confirmation is limited to styling restoration and is not comprehensive browser verification.
- **Database preservation:** Git currently tracks `db.sqlite3`; it has a pre-existing unstaged modification. Keep it outside the UI checkpoint, preserve its contents and tracking status, and use explicit file selection. No database inspection of record-level changes or database write was performed for this reconciliation.
- **Design document:** `docs/architecture/designs/RA-EXP-01-Filterable-Vehicle-Generation-Hub-And-Homepage-Redesign.md` distinguishes architectural intent from the WIP implementation.


6A. RA-EXP-02B-1 — Vehicle-contextual navigation foundations

Historical checkpoint clarification (2026-10-27): this section records B-1's original scope/results. Subsequently authorized photographic selector, thumbnail and compact Vehicles disclosure work is recorded in section 1 and the linked task records. The original “global navigation not implemented” boundary below refers to the B-1 checkpoint; the current compact disclosure is implemented, while the five-category contextual shell and B-2–B-5 remain deferred. The historical database/IDE fingerprint discrepancy below remains unresolved; later task-local matching hashes do not establish preservation across B-1 or explain the discrepancy.

- Implemented on `experiment/vehicle-hub-ui`: `/select-vehicle/` (`reference:vehicle-selector`), server-rendered GET search/filter/model selection, allowlisted pending destination tokens, and shared reference discovery queries. Missing destination defaults to Generations; invalid tokens produce HTTP 400 with a validation error; unknown/inactive manufacturer or mismatched model ancestry returns 404. No arbitrary redirect target is accepted.
- `VehicleContext` in `reference/services.py` supplies manufacturer/model and optional Generation/exact definition from objects already validated by model, Generation, model-year, exact specification and Generation measurement views. Templates can consume `vehicle_context.manufacturer`, `.vehicle_model`, `.generation`, `.vehicle_definition`. Query year/trim filters do not establish exact route identity. Existing service `selected_config` remains independently available for a future validated Full Specs shortcut. No session-selected vehicle state; Recently Viewed behavior is unchanged.
- Selector discovery includes active models without definitions. Shared search predicates retain manufacturer/model substring semantics. Existing populated-only directory/homepage rules remain unchanged, including legacy directory manufacturer grouping and filtered model prefetch behavior.
- `VEHICLE_DESTINATIONS` records approved token/label/name/path/availability contracts. `resolve_vehicle_destination` returns an existing canonical model URL for Generations, and None for the four unimplemented model category routes. No deferred route is registered. Pending category selection stays on the selector with allowlisted intent and validated manufacturer/model GET values; it explicitly identifies the destination as not implemented and offers a separately labeled Generations alternative. No fake category pages or broken category links.
- Existing canonical URLs/reversals remain unchanged. Reference URL inclusion now owns its `vehicles/` prefix within a single reference namespace, allowing the selector outside the arbitrary manufacturer slug tree. Measurements inclusion order and existing canonical path ordering remain intact.
- Verification: 20 new focused tests passed; 99 combined navigation/reference/hub/measurement tests passed; final full Django suite **339 passed, 0 failed**. System check passed, migration-consistency dry-run detected no changes, 11 unchanged configurator JavaScript tests passed, and whitespace check passed. Tests/checks used `RIGARCHIVE_TEST_DB_PATH=:memory:` and existing Python 3.14/site-packages. No application request used the development database. No upload/media fields or media writes were introduced.
- No new models, migrations, dependencies or ADRs. Global navigation, category destination experiences and dialog are not implemented. RA-EXP-02B-2 through RA-EXP-02B-5 require separate director authorization. Real-browser/visual/accessibility acceptance remains deferred to the approved later checkpoints; baseline keyboard operation uses native form controls and links.
- Preservation limitation: an intermediate fingerprint check matched the baseline, but final inspection detected changes to the development database and IDE workspace metadata. No development-database writes or IDE edits were intentionally issued; all Django checks/tests used an in-memory database. The cause remains unestablished; byte-for-byte preservation across the task cannot be confirmed. Neither file was restored. Staging, probes, the architecture document and other unrelated files remained unchanged.
- Task record: `docs/implementation/tasks/RA-EXP-02B-1-context-services-route-contracts-baseline-selector.md`. The approved architecture remains unchanged from RA-EXP-02A; its implementation-not-authorized wording records that milestone's authorization boundary, superseded only for B-1 by the current explicit task.


7. Architectural Decision Records (ADRs)
Implemented and Accepted:
- ADR-0001: Entity Identity Strategy (Dual Integer PK + UUID)
- ADR-0002: Immutable Automatic Slugs (Non-editable, auto-generated on creation)
- ADR-0003: Core Infrastructure Application (Shared abstract base models in `core`, domain isolation)
- ADR-0004: Canonical Reference Matching & Import Promotion Strategy (Candidate-to-canonical tiers, Evidence Trust Boundary, Create-Only initial policy)
- ADR-0005: Manufacturer Grade Taxonomy and Market Applicability Normalization Strategy (Factory grade taxonomy, Source-Independence Test, commercial sales market, Cartesian prohibition)
- ADR-0006: Immutable Raw Acquisition Snapshots and Layered Manufacturer Profile Architecture (Immutable raw snapshots, full SHA-256 hashing, layered profiles, structural-row identity, explicit-key multi-document linking, plan-first dry-run orchestration)
- ADR-0007: Explicit Human Authorization & Execution Audit Receipts for Canonical Promotion (Review manifest contract, exact-plan authorization boundary, stale plan aborts, durable execution audit receipts, transactional atomicity)
- ADR-0008: Deterministic Extraction, Review Adjudication & Adjudicated Grade Promotion (Deterministic extraction strategies, golden fixture testing, 5-stage lifecycle, bounded human domain adjudications, `ADJUDICATED_DISTINCT_GRADE` basis, exact-plan preservation, same-trim stale checks, manifest v1.1 linkage, audit receipt linkage)
- ADR-0009: Physical Vehicle Measurements & Feature Applicability Domain Strategy (Decoupled top-level `measurements` domain, `reference.Generation` scope anchor, definition vs result separation, result unit ownership, controlled feature/state applicability, zero conditions means Generation-wide, conjunctive AND conditions, multi-result evidence preservation)

Accepted architecture — implementation status:
- [ADR-0010: Generation Correspondence and Selectable Factory Alternatives](../architecture/ADR/ADR-0010-Generation-Correspondence-Selectable-Factory-Alternatives.md) — Accepted 2026-11-03 after project-director review, without substantive changes. Establishes reviewed generation correspondence and transmission/factory package offerings subordinate to VehicleDefinition, preserving immutable slugs, approved body distinctions through trim normalization, the Generation configurator, and Generation-anchored measurements. Supersedes only the ADR-0005 Decision 2 exclusion of manufacturer-offered factory packages and individual factory options from Reference; historical ADRs remain unchanged.
- [ADR-0011: Factory body configuration identity](../architecture/ADR/ADR-0011-Factory-Body-Configuration-Identity.md) — Accepted architecture on 2026-11-04 under director-approved contract corrections; not implemented. Narrow van-profile extension; see W2 design contracts above.
- ADR-0010 Milestone 1 is implemented in the working tree and Django-verified: append-only `GenerationCorrespondenceRevision`, candidate v2/manifest 2.0, reviewed source resolution, exact single-plan authorization, two receipt operation types, and pre-write legacy guards. Planning no longer seeds parents. Bootstrap preflight includes proposed and existing taxonomy ranges; retained review evidence includes generation normalizer identity/version. The permanent [ingestion protocol](../development/INGESTION_PROTOCOL.md) and RA-010/011/014/016/018/022/024/025 amendments document the implemented boundary. See the [Milestone 1 verification record](tasks/ADR-0010-milestone-1-overlapping-generation-resolution.md).
- The closeout generation-projection blocker is corrected: v2 projections must exactly cover all retained generation-identifying assertions using document-qualified identity. Empty projection requires verifiable absence; incomplete source inventories fail closed. Resolver, serialization, reconstruction and execution reject omission/downgrade attempts without inferring or filling evidence. The v2 contract and schema are unchanged. Acceptance recommendation is PASS WITH QUALIFICATIONS for the separately documented limitations.
- Migration `reference/0006_generationcorrespondencerevision_and_receipt_resolution` is created and tested only in isolated databases; development remains at 0005 and needs separate migration authorization. No Jeep evidence acquisition or development Jeep/Wrangler population occurred. Transmission and factory-package milestones remain unimplemented. Legacy guards are bounded protections, not a repair of batch re-planning, slug-only authorization, receipt suppression or ordinary legacy correction semantics.




8. Current Testing
Current Milestone 1 blocker-correction verification (2026-11-04): system check passed; migration-consistency dry-run found no changes; 133 focused and all 402 Django tests passed using isolated memory databases, temporary media/raw artifacts and a connection guard rejecting non-isolated ORM connections. The correction adds 15 regression tests; earlier 145/387 results are historical. Synthetic Wrangler cases establish protocol behavior only. Last recorded JavaScript verification remains 33/34; the unchanged homepage length-corrected PNG is 1239×1269 while its unchanged regression test expects the original 502×514 size. Project-wide verification is therefore not fully clean; no UI asset/test was altered to conceal that failure.

Preservation limitation: public UI files, historical ADRs and `config/settings.py` match implementation-start fingerprints. The development database hash at final-verification start differs from the implementation-start hash (see task record); no development write/migration was issued by this work, and the cause is unestablished. Generation UUIDs/ranges and model-level active counts match the earlier inspected inventory, but whole-implementation byte preservation and every individual VehicleDefinition identity cannot be proven from those aggregate observations. During final verification, the database file and all six reference-table fingerprints remained unchanged; no SQLite sidecars, restore or overwrite occurred.

Implemented:
- Development Data Preservation tests (`core/tests.py`)
- Observation Domain tests (`observation/tests.py`)
- Application Shell & UX tests (`config/tests.py`)
- Core mixin & inheritance tests (`core/tests.py`)
- Reference Model tests (`reference/tests/test_models.py`)
- Public Reference View & URL tests (`reference/tests/test_views.py`)
- Intermediate Serialization tests (`reference/tests/test_ingestion_serialization.py`)
- Public Source Acquisition Adapter tests (`reference/tests/test_acquisition_adapters.py`)
- Source Assertion Normalization tests (`reference/tests/test_normalization.py`)
- Candidate Configuration Construction tests (`reference/tests/test_candidate_construction.py`)
- Manufacturer Specification Ingestion tests (`reference/tests/test_manufacturer_ingestion.py`)
- Production Manufacturer Acquisition & Orchestration tests (`reference/tests/test_production_manufacturer_acquisition.py`)
- Canonical Reference Import tests (`reference/tests/test_canonical_import.py`)
- Canonical Import Execution & Execution Provenance tests (`reference/tests/test_canonical_import_execution.py`)
Current status (reconciled 2026-10-27):
- Latest recorded full verification: 350 Django tests and 17 JavaScript tests passed under the Python 3.13 baseline; system check, migration-consistency dry-run and whitespace checks passed. See `docs/implementation/tasks/RA-EXP-vehicles-navigation-quick-selector.md`. Tests used isolated memory databases and temporary files/media with a runtime SQLite connection guard. No new execution occurred during this documentation task.
- The rendered unfiltered selector totals six queries: four selector/discovery queries plus two global header queries, independent of model count. The earlier four-query result predates the header disclosure.
- Browser Use is blocked by managed policy. Real desktop/mobile rendering, responsive overflow, zoom/reflow, native keyboard/focus and screen-reader acceptance remain unverified.

Historical B-1 verification (2026-10-26):
- RA-EXP-02B-1 verification: all 339 Django tests passing, including 20 new navigation-foundation tests; 99 combined focused tests and 11 unchanged JavaScript behavior tests passed.
- Verification command: `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=.venv/lib/python3.14/site-packages RIGARCHIVE_TEST_DB_PATH=:memory: python3 -B manage.py test --noinput`. This historical command used Homebrew Python 3.14 and the then-authorized virtualenv workaround; it is not the current development command. Use `venv/bin/python` without that `PYTHONPATH` workaround.



9. Current Coding Standards
The four Reference Domain models and the Observation Domain model inherit shared UUID and timestamp infrastructure through `core.models.BaseModel`.
Domain entities requiring both UUID identity and timestamps should normally inherit from `BaseModel`. Specialized models may inherit directly from the focused mixins (`UUIDModel`, `TimestampedModel`) where appropriate.
Public URLs use stable slugs.
UUIDs are permanent external identities.
Database relations use integer primary keys.
Reference and Observation data relationships use PROTECT deletion.
Views remain thin; business logic resides in services when coordination complexity mandates it.
Project-level presentation views reside in `config/views.py`; domain views belong in domain applications.

10. Git & Gemini CLI Workflow
- Instructions defined in GEMINI.md.
- Task specs stored under docs/implementation/tasks/.
- Completed tasks: RA-003 — Core Foundation, RA-005 — Application Shell & UX Foundation, RA-007 — Observation Domain Foundation, RA-009 — Development Data Preservation and Recovery Implementation, RA-012 — Intermediate Serialization Contract Implementation & Fixture Validation, RA-013 — Public Source Acquisition Adapters, RA-015 — Source Assertion Normalization Implementation & Fixture Validation, RA-017 — Candidate Configuration Construction & Aggregation Implementation, RA-019 — Canonical Reference Import Planning & Create-Only Execution Implementation, RA-021 — Manufacturer Specification Evidence Acquisition & Normalization Implementation, RA-023 — Production Manufacturer Artifact Acquisition & Dry-Run Orchestration Implementation, RA-024 — Canonical Reference Import Execution & Execution Provenance Workflow Implementation.




11. Current Repository Structure
RigArchive/
│
├── accounts/
├── backups/
│   ├── .gitignore
│   ├── logical/
│   └── snapshots/
├── core/
│   ├── apps.py
│   ├── management/
│   │   ├── __init__.py
│   │   └── commands/
│   │       ├── __init__.py
│   │       ├── export_dev_data.py
│   │       ├── snapshot_db.py
│   │       └── verify_dev_data.py
│   ├── models.py
│   └── tests.py
├── reference/
│   ├── admin.py
│   ├── apps.py
│   ├── ingestion/
│   │   ├── __init__.py
│   │   ├── acquisition/
│   │   │   ├── __init__.py
│   │   │   ├── base.py
│   │   │   ├── epa.py
│   │   │   ├── manufacturer.py
│   │   │   ├── nhtsa.py
│   │   │   ├── profiles.py
│   │   │   ├── smoke_test.py
│   │   │   └── snapshots.py
│   │   ├── candidate/
│   │   │   ├── __init__.py
│   │   │   └── builder.py
│   │   ├── importing/
│   │   │   ├── __init__.py
│   │   │   ├── importer.py
│   │   │   └── planner.py
│   │   ├── normalization/
│   │   │   ├── __init__.py
│   │   │   ├── base.py
│   │   │   ├── epa.py
│   │   │   ├── manufacturer.py
│   │   │   ├── nhtsa.py
│   │   │   └── rules/
│   │   │       ├── __init__.py
│   │   │       ├── epa_rules.py
│   │   │       ├── nhtsa_rules.py
│   │   │       └── toyota_rules.py
│   │   ├── orchestration/
│   │   │   ├── __init__.py
│   │   │   └── manufacturer.py
│   │   ├── contracts.py
│   │   ├── serialization.py
│   │   └── validation.py
│   ├── management/
│   │   ├── __init__.py
│   │   └── commands/
│   │       ├── __init__.py
│   │       ├── acquire_manufacturer_specs.py
│   │       └── execute_canonical_import.py
│   ├── migrations/
│   │   ├── migrations/
│   │   │   ├── 0001_initial.py
│   │   │   ├── 0002_importexecutionreceipt.py
│   │   │   └── 0003_importexecutionreceipt_adjudication_hash.py
│   │   ├── models.py
│   │   ├── tests/
│   │   │   ├── __init__.py
│   │   │   ├── fixtures/
│   │   │   │   ├── acquisition/
│   │   │   │   │   ├── epa/
│   │   │   │   │   │   └── vehicle_42101.json
│   │   │   │   │   ├── nhtsa/
│   │   │   │   │   │   └── get_models_toyota_2020.json
│   │   │   │   │   └── toyota/
│   │   │   │   │       ├── 2020_4runner_pricing.pdf
│   │   │   │   │       ├── 2020_4runner_specs.pdf
│   │   │   │   │       └── 2020_4runner_specs.json
│   │   │   │   └── ingestion/
│   │   │   │       ├── candidate_configuration_4runner_2010_i4_2wd.json
│   │   │   │       ├── candidate_configuration_4runner_2020_trd_offroad.json
│   │   │   │       ├── candidate_configuration_4runner_2020_trim_conflict.json
│   │   │   │       └── source_assertion_set_4runner_2020.json
│   │   │   ├── test_acquisition_adapters.py
│   │   │   ├── test_adjudication_workflow.py
│   │   │   ├── test_candidate_construction.py
│   │   │   ├── test_canonical_import.py
│   │   │   ├── test_canonical_import_execution.py
│   │   │   ├── test_ingestion_serialization.py
│   │   │   ├── test_manufacturer_ingestion.py
│   │   │   ├── test_models.py
│   │   │   ├── test_normalization.py
│   │   │   ├── test_production_manufacturer_acquisition.py
│   │   │   ├── test_toyota_extractor.py
│   │   │   └── test_views.py
│   ├── urls.py
│   └── views.py
├── observation/
│   ├── admin.py
│   ├── apps.py
│   ├── models.py
│   ├── tests.py
│   └── migrations/
│       └── 0001_initial.py
├── config/
│   ├── settings.py
│   ├── urls.py
│   ├── views.py
│   ├── tests.py
│   └── wsgi.py
│
├── storage/
│   └── raw_source_artifacts/
├── templates/
│   └── urls.py
├── docs/
│   ├── architecture/
│   │   ├── ADR/
│   │   └── designs/
│   ├── development/
│   │   └── DATA_PRESERVATION.md
│   ├── handbook/
│   └── implementation/
│       ├── CURRENT_STATE.md
│       └── tasks/
│           ├── RA-003-core-foundation.md
│           ├── RA-005-application-shell-ux-foundation.md
│           ├── RA-007-observation-domain-foundation.md
│           ├── RA-009-development-data-preservation-implementation.md
│           ├── RA-012-intermediate-serialization-implementation.md
│           ├── RA-013-public-source-acquisition-implementation.md
│           ├── RA-015-source-assertion-normalization-implementation.md
│           ├── RA-017-candidate-configuration-construction-aggregation-implementation.md
│           ├── RA-019-canonical-reference-import-planning-create-only-execution-implementation.md
│           ├── RA-021-manufacturer-specification-evidence-acquisition-normalization-implementation.md
│           ├── RA-023-production-manufacturer-artifact-acquisition-dry-run-orchestration-implementation.md
│           ├── RA-024-canonical-reference-import-execution-execution-provenance-workflow-implementation.md
│           └── RA-026-deterministic-toyota-extraction-review-adjudication-implementation.md
│
├── tests/
│
├── CHANGELOG.md
├── GEMINI.md
├── README.md
├── requirements.txt
└── manage.py

12. Planned Milestone Map
- Milestone 1: Project foundation (✅ Complete)
- Milestone 2: Reference Domain (✅ Complete)
- Milestone 2A: Public Reference Browser (✅ Complete)
- Milestone 3: Core Infrastructure (✅ Complete — RA-003)
- Milestone 3A: Application Shell & UX Foundation (✅ Complete)
- Milestone 4: Observation Domain Foundation (✅ Complete — RA-007)
- Milestone 5: Development Data Preservation & Recovery (✅ Complete — RA-009)
- Milestone 6: Reference Data Ingestion Source & Mapping Architecture (✅ Approved Architecture — RA-010)
- Milestone 7: Ingestion Schema & Intermediate Serialization Design (✅ Approved Architecture — RA-011)
- Milestone 8: Intermediate Serialization Contract Implementation & Fixture Validation (✅ Complete — RA-012)
- Milestone 9: Public Source Acquisition Adapters (✅ Complete — RA-013)
- Milestone 10: Source Assertion Normalization & Mapping Architecture (✅ Approved Architecture — RA-014)
- Milestone 11: Source Assertion Normalization Implementation & Fixture Validation (✅ Complete — RA-015)
- Milestone 12: Candidate Configuration Construction & Aggregation Architecture (✅ Approved Architecture — RA-016)
- Milestone 13: Candidate Configuration Construction & Aggregation Implementation (✅ Complete — RA-017)
- Milestone 14: Canonical Reference Matching & Import Architecture (✅ Approved Architecture — RA-018 / ADR-0004)
- Milestone 15: Canonical Reference Import Planning & Create-Only Execution Implementation (✅ Complete — RA-019)
- Milestone 16: Trim/Grade & Market Applicability Source & Normalization Architecture (✅ Approved Architecture — RA-020 / ADR-0005)
- Milestone 17: Manufacturer Specification Evidence Acquisition & Normalization Implementation (✅ Complete — RA-021)
- Milestone 18: Production Manufacturer Evidence Acquisition & Orchestration Architecture (✅ Approved Architecture — RA-022 / RA-022A / ADR-0006)
- Milestone 19: Production Manufacturer Artifact Acquisition & Dry-Run Orchestration Implementation (✅ Complete — RA-023)
- Milestone 20: Canonical Reference Import Execution & Execution Provenance Workflow Architecture & Implementation (✅ Complete — RA-024 / ADR-0007)
- Milestone 21: Production Manufacturer Extraction & Review-Adjudication Architecture (✅ Approved Architecture — RA-025 / ADR-0008)
- Milestone 22: Deterministic Toyota Extraction & Review-Adjudication Implementation (✅ Complete — RA-026 / ADR-0008)
- Milestone 23: Scalable Reference Population Source Model (✅ Complete — RA-028)
- Milestone 24: Drivetrain Semantic Preservation, Public Display & Canonical Record Correction Lifecycle (✅ Complete — RA-029)
- Milestone 25: Public Vehicle Navigation Hierarchy (✅ Complete — RA-030)
- Milestone 26: US-Market Generation Bootstrap & Full Configuration Population (✅ Complete — RA-031)
- Milestone 27: Generation Landing Pages, Model-Year Overview & Detailed Specs Navigation (✅ Complete — RA-032)
- Milestone 28: Canonical Import Receipt Coverage Audit & Batch Execution Atomicity Hardening (✅ Complete — RA-034)
- Milestone 29: Multi-Model Generation Bootstrap & Complete Configuration Population for Toyota Tacoma & Volkswagen Touareg (✅ Complete — RA-036)
- Milestone 30: Complete Remaining Toyota 4Runner Generations Bootstrap & Population (✅ Complete — RA-038)
- Milestone 31: Complete Fifth Generation & Add Sixth Generation Toyota 4Runner (✅ Complete — RA-039)
- Milestone 32: Operator Workflow Hardening (✅ Complete — RA-040)
- Milestone 33: Compact Multi-Column Archive Navigation Cards (✅ Complete — RA-041)
- Milestone 34: Measurements Domain Foundation Architecture (✅ Approved Architecture — RA-042 / ADR-0009)
- Milestone 35: Measurements Domain Foundation Implementation (✅ Complete — RA-043)


13. Current Repository Status
The repository currently contains:
- Functional Django project
- Task 2 final presentation: 319 Django tests passed using isolated resources, plus 11 JavaScript behavior tests (Task 1 final cleanup: 307/307) (initial Task 1: 297/297; compact refinement: 303/303). Historical checkpoint: 286 executed, 273 passed, 13 failed. Earlier completed-milestone results remain historical.
- Shared core infrastructure (`core` app with `UUIDModel`, `TimestampedModel`, `BaseModel`)
- Reference Data Ingestion package (`reference/ingestion/` with contracts, serialization, validation, `acquisition/` adapters, profiles & extractors including `JDPowerProfile`, `JDPowerExtractor`, `WikipediaExtractor`, `normalization/` normalizers including `JDPowerNormalizer`, `rules/` for `toyota_rules.py` and `volkswagen_rules.py`, `candidate/` builder, `importing/` importer, planner, & `correction.py` correction workflow, `manifest.py` review manifest & `PopulationBatchManifest`, and `orchestration/` `MultiSourceOrchestrator` & `GenerationBootstrapOrchestrator`)
- Safe read-only inspection, planning, and batch execution tooling (`inspect_reference_state`, `plan_generation_population`, `execute_population_batch`, `snapshot_db`, `export_dev_data`, `verify_dev_data`)
- Accessible application shell and UX foundation (`templates/base.html`, `about.html`, `404.html`, `500.html`)
- Observation Domain foundation (`observation` app with `Observation` model)
- Measurements Domain foundation (`measurements` app with `MeasurementDefinition`, `ApplicabilityFeature`, `ApplicabilityState`, `MeasurementResult`, `MeasurementResultCondition` models, admin interfaces, and public browser integration)
- Public reference browser (`templates/reference/`) with manufacturer/model generation cards, breadcrumbs, experimental Generation hub with in-place year/trim filters, and separate model-year/configuration routes. Shared component styling is restored; the old infobox is absent, while Task 1 retains backend notes and exact-configuration selection in the single three-step Configurations & Specs section; no upper selector remains. See EXP-01 for limitations.
- Admin interface with read-only audit log viewers (`ImportExecutionReceiptAdmin`, `CanonicalRecordCorrectionAdmin`) and Measurements management
- Stable migration history (0001_initial, 0002_importexecutionreceipt, 0003_importexecutionreceipt_adjudication_hash, 0004_alter_vehicledefinition_drivetrain, 0005_canonicalrecordcorrection, measurements/0001_initial)
- Populated Architectural Decision Records (ADR-0001 through ADR-0011; ADR-0011 accepted architecture only, with W2 implementation milestones requiring separate authorization)
- Approved Architecture Design Documents (RA-006, RA-008, RA-010, RA-011, RA-014, RA-016, RA-018, RA-020, RA-022, RA-024, RA-025, RA-042)
- Gemini CLI project instructions (GEMINI.md)
- Task-based implementation workflow (docs/implementation/tasks/)
- Completed implementation tasks: RA-003, RA-005, RA-007, RA-009, RA-012, RA-013, RA-015, RA-017, RA-019, RA-021, RA-023, RA-024, RA-026, RA-027, RA-028, RA-029, RA-030, RA-031, RA-032, RA-034, RA-036 — Multi-Model Generation Bootstrap, RA-037 — Generation Image Correction, RA-038 — Complete Remaining Toyota 4Runner Generations, RA-039 — Complete Fifth Generation & Add Sixth Generation Toyota 4Runner, RA-040 — Operator Workflow Hardening, RA-041 — Compact Multi-Column Archive Navigation Cards, RA-043 — Measurements Domain Foundation Implementation
- Approved Architecture/Research tasks: RA-010, RA-011, RA-014, RA-016, RA-018, RA-020, RA-022, RA-024, RA-025, RA-042 — Measurements Domain Foundation Architecture
