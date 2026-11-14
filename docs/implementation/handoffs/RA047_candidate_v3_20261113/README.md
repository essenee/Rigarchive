# RA-047 — Candidate v3 pure wire implementation handoff

Created: 2026-11-13
Last Updated: 2026-11-13
Status: Accepted
Accepted: 2026-11-13

## A. Repository baseline and preservation

HEAD: `b98f078ccf1d88344f3f94eab5467fc8707a946f` (unchanged).
At the initial implementation checkpoint, the assignment authorized reviewed RA-046
while its formal status remained Proposed. On 2026-11-13 the Project Owner explicitly
approved RA-046 and accepted this RA-047 revision, including the removal of the
misleading affirmative EvidenceReport property. See §H for the current acceptance
and commit plan. Accepted ADRs and RA-045 are untouched. No staging, commit or push
is authorized/performed.

Initial status (all entries pre-existing):

```text
 M CHANGELOG.md
 M db.sqlite3
 M docs/implementation/CURRENT_STATE.md
?? docs/architecture/designs/RA-046-Candidate-v3-Exact-Wire-Contract-Specification.md
?? docs/implementation/handoffs/MY2023_JL/
?? docs/implementation/handoffs/MY2024_JL/
?? docs/implementation/handoffs/RA045_phase1_20261113/
?? docs/research/
?? reference/body_identity.py
?? reference/ingestion/candidate/v3_foundations.py
?? reference/tests/fixtures/ingestion/historical_jl24_candidate_2_1_0.json
?? reference/tests/fixtures/ingestion/my2024_body_identity_projection.json
?? reference/tests/test_body_identity.py
?? run_readonly_plans.py
?? scratch/
```

The initial Git index was empty. A fresh 6,145-file baseline distinguishes existing
work from this assignment. The operational database remains byte-identical to that
baseline; its modified status relative to HEAD predates this work. All pre-existing
untracked phase-one implementation, candidate/handoff/research artifacts and reviewed
RA-046 are preserved. CURRENT_STATE/CHANGELOG receive additive task records only. Operational database
SHA-256 is unchanged: `be3b1cfe8f03feda457f2aa7ef397b96f2cd673971aaf6a999c171c5523b32a6`.

## B. Implementation inventory and responsibilities

| File | Assignment change / responsibility |
| --- | --- |
| [candidate_v3.py](../../../../reference/candidate_v3.py) | New pure typed document, exact recursive contract validation, duplicate-aware JSON parser, canonical serialization, stable contract diagnostics, local reference checking, semantic/whole-artifact/pending checksums and proposed baseline digest reconstruction |
| [candidate_v3_evidence.py](../../../../reference/candidate_v3_evidence.py) | New pure supplied-data support/applicability/coexistence/conflict/projection checks; dependency diagnostics, never live resolution or import approval |
| [powertrain_evidence.py](../../../../reference/powertrain_evidence.py) | Existing explicit RA-044 raw-support function extracted unchanged into a pure shared module; no new classification policy |
| [serialization.py](../../../../reference/ingestion/serialization.py) | Explicit new typed artifact dispatch; direct legacy reader/writer reject v3; old version serialization/hash branches remain unchanged |
| [validation.py](../../../../reference/ingestion/validation.py) | Explicit structural/cryptographic dispatch for the new typed document, not eligibility |
| [powertrain_identity.py](../../../../reference/ingestion/importing/powertrain_identity.py) | Imports shared support function under existing `_supports` name; legacy evidence behavior preserved |
| [test_candidate_v3_wire.py](../../../../reference/tests/test_candidate_v3_wire.py) | 60 pure contract/evidence/dispatch/compatibility tests; SimpleTestCase forbids database queries |
| [candidate_v3 fixtures](../../../../reference/tests/fixtures/ingestion/candidate_v3/) | Eight new test-only files A.json–H.json copied exactly from RA-046 §11, not regenerated MY2024 candidate artifacts |
| CURRENT_STATE / CHANGELOG | Additive verified scope/results/boundary records, preserving existing work |
| This handoff | New implementation, conformance, verification and next-phase report |

Existing `reference/body_identity.py` and `candidate/v3_foundations.py` remain unchanged.
The isolated phase-one projection checksum remains distinct from a whole-candidate
artifact hash. No new models, schema files, migrations, dependencies or architecture.

The legacy ingestion package eagerly imports model/planner modules. The new contract
therefore lives alongside the existing pure body module, avoiding ORM/bootstrap imports
for standalone use. An initial direct-import probe exposed that existing package behavior;
placing the pure modules outside that initializer resolved it. A subprocess regression
checks both new modules import without loading `reference.models` or `django.db`.

### Public pure API

- `parse_candidate(str|dict)` returns `CandidateV3Document`; it rejects duplicate keys,
  unknown fields, unsupported dispatch triples, malformed references, nonfinite values,
  surrogates, invalid preimages and mismatched hashes. No repairs/default insertion.
- `validate_structure(document)` performs structural and cryptographic validation.
  `CandidateV3Error.diagnostic` has stable stage/code/path/message and contract errors.
- `serialize_candidate(document)` produces exact canonical UTF-8 JSON text using the
  existing `canonical_json` primitive; set arrays must already be ordered. Ordered raw
  arrays, Unicode spelling, optional omission and metadata stay hash-bound.
- `candidate_hash(document)` computes the mathematical root-minus-candidate_hash digest;
  computing that value alone is not schema validation or evidence approval.
- `pending_parent_checksum(parent, kind=..., expected=...)` reconstructs/verifies a
  derived descriptor checksum; no new checksum wire member exists. Pending has no UUID.
- `baseline_identity_digest(document)` reconstructs proposed baseline/2 via existing
  five-field powertrain/body helpers when complete, otherwise returns None. It grants
  neither parent equality nor canonical eligibility.
- `validate_evidence(document, retained_artifacts={path:bytes})` performs supplied-data
  checks only. It never opens paths. Its report separates evidence failures from
  dependencies. `has_evidence_errors` reports detected evidence errors only; its
  negation does not establish evidence acceptance. Callers must inspect unresolved
  dependencies separately and must not infer source authenticity, publication
  eligibility or import authorization from the absence of detected evidence errors.

Body/series references retain their exact existing/pending unions. An existing UUID
and revision hash are structurally checked but never looked up. Pending descriptors
remain unbound; digest mismatch does not establish distinctness or a create action.
The whole relevant source set must establish coexistence; shared documents, tables,
assertion sets, extraction batches and independent alternative rows are insufficient.
A legitimate complete composite configuration can support many fields without one
human decision per field. Wrangler's exact existing two-/four-door headings are used
without a second body review; original Unlimited Sport wording remains in evidence.

### Evidence dependencies are explicit

RA-046 deliberately references existing source/review/binding authority rather than
inventing new approval formats. This phase checks only what supplied structures permit:

- Original bytes absent or changed: dependency/UNAVAILABLE_ARTIFACT, not SOURCE_CONFLICT.
- A declared qualified cross-source link cannot be accepted merely because it exists.
  Source-specific/review decoding remains a dependency; it is not a successful join.
- Workflow/adjudication formats without an implemented authorized decoder report
  dependency/UNSUPPORTED_REVIEW_VERSION. An arbitrary pointer/line or `approved` string
  cannot approve evidence. Historical 1.1 candidate-bound findings cannot bless v3.
- The two Sport source-label pairs explicitly given in RA-046 are checked directly;
  broader reviewed trim mappings require their retained mapping. No generic Unlimited
  stripping, source-code inference, missing-fuel default or ESS-to-hybrid inference.
- Registry/Generation correspondence, live immutable bindings, whole-peer identity
  relationship and actual A/B/C pending-parent resolution remain later dependencies.

This is intentional scope separation, not a claim of complete source acceptance or
implementation of a publication/eligibility engine. No specification conflict or hash
vector discrepancy was found. No architecture policy was invented to fill dependencies.

## C. RA-046 conformance matrix

| Section | Status | Implemented / boundary |
| --- | --- | --- |
| 1 Scope/continuity | Implemented within bounded phase | Pure functions/dispatch; no operational integration |
| 2 Primitive/closed types | Implemented | Tokens, scope, IDs, hashes, UUIDs, paths, dates, raw JSON, duplicate handling |
| 3 Envelope/root | Implemented | Exact type/version/URN, required/nullable members, no inferred parents |
| 4 Evidence shapes/grouping | Implemented wire; partial semantic source decoding | Closed evidence/interpretation/finding/applicability shapes and qualified refs; direct support/coexistence checks; unknown source/review decoders explicit dependencies |
| 5 Body parent | Implemented wire/crypto | Seven sparse fields, frozen body/2, existing refs/pending descriptors/checksums; live identity/binding resolution explicitly deferred |
| 5.1 A/B/C outcomes | Preserved; resolution deferred by scope | No automatic create/reuse disposition; partial compatibility/new digest never proves equality/distinctness |
| 6 Series | Implemented wire/crypto | Model-scoped /1 identity, independent supported role, existing/pending union; no absent-series finding |
| 7 Validation boundaries | Implemented pure layers | contract/evidence/dependency diagnostics; source support independent of schema/hash; no resolution/publication eligibility |
| 8 Technical/review/lineage | Implemented wire | Closed retained types, inert raw maps and local refs; direct technical contradiction checks; no equipment/tuning identity expansion |
| 9 Hashing | Implemented | Exact body, series, baseline, descriptor and candidate digest purposes remain separate; exact eight vectors reproduced |
| 10 Compatibility | Implemented dispatch/guards | Old 2.1 round-trip/hash unchanged; no new proof/adjudication/manifest/Matrix/receipt semantics |
| 11 Examples | Implemented test fixtures | A–H copied byte-for-byte from document blocks, expected hashes fixed in tests; synthetic records remain synthetic |
| 12 Test matrix | Implemented within pure scope | Negative/parser/hash/support/coexistence/identity-boundary/historical tests; live database integration deferred |
| 13 Preservation/checks | Verified | Specification/examples and all unrelated baseline files preserved; no source/canonical regeneration |
| 14 Prerequisites | Remaining phases recorded | RA-046 approved and RA-047 accepted by owner on 2026-11-13; later persistence/proof/planning/execution authorizations not assumed |

## D. Verification results

Interpreter: existing authorized `.venv/bin/python`, Python 3.13.1, Django 6.0.7.
`venv/py313/bin/python` remains absent; no environment/package changes. This initial
bounded verification used targeted tests; the fresh full-suite closeout is recorded
in §G below. All final targeted tests for that stage passed; zero failures and zero skips.

Final combined command:

```text
RIGARCHIVE_TEST_DB_PATH=/private/tmp/rigarchive-ra047-isolated.sqlite3 .venv/bin/python manage.py test reference.tests.test_candidate_v3_wire reference.tests.test_body_identity reference.tests.test_structured_powertrain reference.tests.test_ingestion_serialization reference.tests.test_candidate_construction reference.tests.test_engine_distinction reference.tests.test_classification_adjudication --verbosity 1
```

| Verification | Actual result |
| --- | --- |
| New v3 wire/evidence/compatibility tests | 60 passed |
| Existing body identity tests | 35 passed |
| Existing structured-powertrain/ingestion/candidate/engine/adjudication regressions | 98 passed |
| Combined run | 193 passed in 3.474 seconds; isolated test DB created/destroyed |
| `RIGARCHIVE_TEST_DB_PATH=/private/tmp/rigarchive-ra047-check.sqlite3 .venv/bin/python manage.py check` | No issues |
| `RIGARCHIVE_TEST_DB_PATH=/private/tmp/rigarchive-ra047-drift.sqlite3 .venv/bin/python manage.py makemigrations --check --dry-run` | No changes detected; no migration created/applied |
| All eight RA-046 vectors | Exact structural, semantic digest, canonical round-trip and artifact hash checks pass, with unchanged documentation |
| Historical Candidate 2.1.0 fixture | Byte SHA-256 `2f341d71c8cc7aee323ad5fadedbdf6422b409c87f06f068986f6f15716d7c6a` unchanged; old round-trip semantics preserved |
| Preservation / Git whitespace | Passed: all 6,145 baseline files accounted for, only five authorized existing files changed and 13 expected new files; prior governance content preserved; HEAD unchanged, index empty, `git diff --check` clean |

Tests distinguish a structurally valid/hash-correct unsupported body from a schema
failure, verify same-document/alternative-row nonjoins and source-linkage dependencies,
retain ordinary no-body behavior, reject known discriminator suppression, exercise
existing/pending/independent-series references, and preserve peer-order invariance and
nontransitive compatibility. They do not create/import real MY2024 candidates.

## E. Next bounded work

A subsequent authorization may add source/profile and reviewed-artifact decoders where
needed, with actual retained evidence and authority fixtures. Live implementation still
requires separately scoped additive body/series persistence and immutable binding
snapshot contracts, existing/pending parent resolution, read-only whole-peer planning,
coordinated proof/resolution/adjudication/manifest/Matrix/receipt versions, exact write
authorization and atomic execution tests. MY2024 regeneration, pending classification
approval/correspondence publication, canonical import and actual-combination UI are
later owner-authorized work. No work proceeds into those phases here.

## F. Safety and authority confirmation

No database schema/model changes, operational data reads/writes by the contract layer,
canonical records, parent persistence, historical backfills, approvals, receipt creation,
correspondence publication, canonical imports, public UI changes or unauthorized
architecture changes. Historical source/identity/proof/receipt contracts are not
rewritten. No files are staged, committed or pushed. Existing uncommitted work remains
intact; the requested implementation is left for review.

## G. Final verification and documentation closeout

### Repository state and task boundary

Verification/documentation only; no implementation change or next milestone.
Branch `main`; HEAD `b98f078ccf1d88344f3f94eab5467fc8707a946f`, unchanged.
Initial and final Git status are identical (all paths were already modified/untracked):

```text
 M CHANGELOG.md
 M db.sqlite3
 M docs/implementation/CURRENT_STATE.md
 M reference/ingestion/importing/powertrain_identity.py
 M reference/ingestion/serialization.py
 M reference/ingestion/validation.py
?? docs/architecture/designs/RA-046-Candidate-v3-Exact-Wire-Contract-Specification.md
?? docs/implementation/handoffs/MY2023_JL/
?? docs/implementation/handoffs/MY2024_JL/
?? docs/implementation/handoffs/RA045_phase1_20261113/
?? docs/implementation/handoffs/RA047_candidate_v3_20261113/
?? docs/research/
?? reference/body_identity.py
?? reference/candidate_v3.py
?? reference/candidate_v3_evidence.py
?? reference/ingestion/candidate/v3_foundations.py
?? reference/powertrain_evidence.py
?? reference/tests/fixtures/ingestion/candidate_v3/
?? reference/tests/fixtures/ingestion/historical_jl24_candidate_2_1_0.json
?? reference/tests/fixtures/ingestion/my2024_body_identity_projection.json
?? reference/tests/test_body_identity.py
?? reference/tests/test_candidate_v3_wire.py
?? run_readonly_plans.py
?? scratch/
```

The full suite left every one of the 6,158 fresh baseline files and the repository
path inventory unchanged. Closeout subsequently edits only this handoff, CURRENT_STATE
and CHANGELOG. The operational database SHA-256 remains
`be3b1cfe8f03feda457f2aa7ef397b96f2cd673971aaf6a999c171c5523b32a6`.
The database's existing Git modification predates RA-047; it is excluded from proposed
RA-047 commit scope. Source code, tests, all candidate fixtures, accepted architecture,
RA-046, original handoffs, receipts/correspondences and persisted slugs remain unchanged.

### Fresh verification commands and results

Used the previously authorized existing `.venv/bin/python` (Python 3.13.1 / Django
6.0.7), since the designated py313 environment remains absent. The configuration
selects an isolated database; the Django runner creates/destroys its test database.
No operational management command or migration application was run.

```text
RIGARCHIVE_TEST_DB_PATH=/private/tmp/rigarchive-ra047-closeout-suite.sqlite3 .venv/bin/python manage.py test --verbosity 1
RIGARCHIVE_TEST_DB_PATH=/private/tmp/rigarchive-ra047-closeout-check.sqlite3 .venv/bin/python manage.py check
RIGARCHIVE_TEST_DB_PATH=/private/tmp/rigarchive-ra047-closeout-drift.sqlite3 .venv/bin/python manage.py makemigrations --check
git diff --check
git status --short
```

| Check | Fresh result |
| --- | --- |
| Complete Django suite | 837 discovered and run; 837 passed in 40.890 seconds; zero failures, errors or skips; exit 0 |
| Targeted RA-047 suite | Not separately rerun during closeout; all 193 targeted tests, including 60 v3 tests, are included in the successful full suite; earlier targeted results remain recorded above |
| System checks | No issues, zero silenced; exit 0 |
| Migration drift | No changes detected; no migrations created/applied; exit 0 |
| Git whitespace | `git diff --check` clean; exit 0 |
| Historical fixture | SHA-256 remains `2f341d71c8cc7aee323ad5fadedbdf6422b409c87f06f068986f6f15716d7c6a`; full-suite round-trip checks pass |
| Legacy shared terminology | AST comparison confirms the extracted function is unchanged apart from its name/recursive reference; full legacy tests pass |
| Final preservation/status | Only the three authorized documentation files changed from closeout baseline; HEAD/branch unchanged, index empty, initial/final status identical |

No failure required attribution to a regression, environment or unrelated work. No
behavioral correction was made. Test-generated promotion/publication/snapshot output
belongs to isolated regression fixtures, not operational canonical execution.

### Architecture boundary inspection

| Boundary | Verified finding |
| --- | --- |
| Historical compatibility | Existing 2.1 parsing/serialization/hash behavior and bytes preserved; the added v3 branch and direct legacy guards are explicit. Reader implementation files do have RA-047 changes, but old supported-version semantics do not. |
| Version dispatch and modeled schema | Exact v3 artifact type / 3.0.0 / local schema URN; closed objects and duplicate-key rejection. Unknown old metadata is not silently promoted into new identity. |
| Hashing and identity | Existing canonical JSON/SHA-256 representation; root-only candidate_hash exclusion; body/series/baseline semantic meaning, pending checksum and full evidence-bound artifact hash remain distinct. All eight fixed examples pass. |
| Sparse body | No required body/series association, defaults, synthetic parent or seven-state checklist for blank dimensions. Known source distinctions cannot be hidden by omission. |
| Coexistence | Shared document/table/assertion-set/extraction-batch proximity and separate alternative rows are insufficient; qualified positive grouping is required. |
| Evidence versus dependencies | Negative `has_evidence_errors` and dependency diagnostics remain separate; no affirmative evidence-acceptance, resolution-approved, eligible or authorized property exists. |
| Removed property | Definition absent; repository search finds only the regression test asserting API absence. No operational consumer relies on it. |
| Existing parents | UUID/revision/preimage validation only; no live binding fetch or parent matching. |
| Pending parents | Descriptors/checksums only; no automatic creation/reuse or digest-only distinctness decision. |
| Operational boundary | No new database models/schema, persistence, import/publication/authorization workflow or UI. No next binding-architecture milestone begun. |

These five boundaries remain independent: (1) contract/cryptographic validity,
(2) supplied-evidence validation, (3) unresolved external dependencies, (4) live
canonical resolution, and (5) human authorization/import eligibility. Passing the
first two does not supply the other three, complete evidence acceptance or canonical
import readiness. A lack of detected evidence errors is not affirmative support.

### Documentation and governance recommendation

**Historical closeout recommendation, superseded by §H:** BLOCKED — GOVERNANCE
DECISION REQUIRED. At that checkpoint technical verification passed with no
identified correction blocker. RA-046 was `Status: Proposed`; formal specification
approval was outstanding and required Project Owner action. The earlier explicit
implementation assignment is not silently converted into a formal documentation
status change or final milestone acceptance. Owner action was required for governance
closeout at that checkpoint. The subsequent explicit acceptance is recorded in §H;
no next milestone is authorized.

Substantive closeout documentation changes: fresh full-suite/check commands and
results; confirmation of the corrected EvidenceReport API; explicit five-way boundary;
formal-approval dependency/recommendation; preserved working-tree baseline/status; and
the commit grouping below. Earlier initial-phase test history remains identified as
such. Source-specific reviewed mappings/decoders, live binding/peer verification and
all later persistence/planning/execution phases remain deferred as recorded in §E.

### Proposed eventual owner-authorized commit scope

No staging or commit is executed. Dependencies and unrelated work must be separated;
whole-file staging of CURRENT_STATE/CHANGELOG would include prior unrelated records.

**RA-047 implementation and closeout (18 files):**

```text
reference/candidate_v3.py
reference/candidate_v3_evidence.py
reference/powertrain_evidence.py
reference/ingestion/serialization.py
reference/ingestion/validation.py
reference/ingestion/importing/powertrain_identity.py
reference/tests/test_candidate_v3_wire.py
reference/tests/fixtures/ingestion/candidate_v3/A.json
reference/tests/fixtures/ingestion/candidate_v3/B.json
reference/tests/fixtures/ingestion/candidate_v3/C.json
reference/tests/fixtures/ingestion/candidate_v3/D.json
reference/tests/fixtures/ingestion/candidate_v3/E.json
reference/tests/fixtures/ingestion/candidate_v3/F.json
reference/tests/fixtures/ingestion/candidate_v3/G.json
reference/tests/fixtures/ingestion/candidate_v3/H.json
docs/implementation/handoffs/RA047_candidate_v3_20261113/README.md
docs/implementation/CURRENT_STATE.md (RA-047 hunks only)
CHANGELOG.md (RA-047 hunks only)
```

**Pre-existing RA-045 phase-one foundation dependency (separate scope, six files):**

```text
reference/body_identity.py
reference/ingestion/candidate/v3_foundations.py
reference/tests/test_body_identity.py
reference/tests/fixtures/ingestion/historical_jl24_candidate_2_1_0.json
reference/tests/fixtures/ingestion/my2024_body_identity_projection.json
docs/implementation/handoffs/RA045_phase1_20261113/README.md
```

Associated phase-one CURRENT_STATE/CHANGELOG hunks belong with that foundation scope,
not silently in RA-047. RA-047 depends on these pre-existing uncommitted files: the
owner should authorize their earlier/separate commit or explicitly review a combined
scope so a clean checkout remains testable.

**Pre-existing specification/governance dependency (separate owner decision):**
`docs/architecture/designs/RA-046-Candidate-v3-Exact-Wire-Contract-Specification.md`.
Tests compare its eight examples directly, so that document must also be present in
a clean checkout. Formal approval was outstanding at that checkpoint and is now recorded in §H;
RA-046 is approved but still uncommitted. Nothing is staged. ADR-0013/RA-045 acceptance
is already in HEAD.

**Exclude unrelated pre-existing work:** `db.sqlite3`, MY2023_JL/MY2024_JL handoffs,
`docs/research/`, `run_readonly_plans.py`, `scratch/`, and unrelated governance hunks.
No reset, cleanup, branch change, staging, commit, amendment or push occurred.

## H. Formal owner acceptance and commit preparation

### Acceptance record — 2026-11-13

By explicit Project Owner decision, **RA-046 is Approved** as the governing exact
Candidate v3.0.0 wire-contract specification and **RA-047 is Accepted** as its conforming
pure implementation. This includes the final contract clarifications and removal of
`EvidenceReport.supplied_projection_supported`. These decisions cover only the current
reviewed revisions; they do not approve future contracts, new bindings/persistence,
resolution or execution phases. The prior RA-046 governance blocker in §G is resolved.

Final accepted technical verification remains 837 full-suite tests passed in 40.890
seconds, zero failures/errors/skips, including all 193 targeted tests; system checks,
migration-drift checks and Git whitespace checks passed. Historical 2.1 compatibility,
exact v3 hashing/dispatch, evidence/dependency separation and database preservation
remain verified. The removed property has no operational consumer. The full suite
is not rerun for this documentation-only finalization; no executable file changes.

There are six separate stages: (1) contract/cryptographic validation, (2) supplied-
evidence validation, (3) external dependency verification, (4) live canonical parent
resolution, (5) human authorization, and (6) canonical import execution/publication.
RA-047 implements only the first two within their specified limits. Acceptance is
not complete evidence acceptance, canonical readiness or authorization for later stages.

Current branch/HEAD: main / `b98f078ccf1d88344f3f94eab5467fc8707a946f`.
The index is empty and unchanged. Initial/final status remains the §G listing;
all differences are still unstaged/uncommitted. No branch/history operation occurred.
No independent milestone index tracking these RAs was found beyond CURRENT_STATE;
no additional index is created. Historical changelog/checkpoint records remain intact.

### Commit boundary inventory — Groups A–D

The earlier 18-file RA-047 scope in §G consists of **16 exclusive Group C files plus
two shared Group D files**, not 18 files safe to stage wholesale. Group A and Group B
are pre-existing uncommitted dependencies and are not absorbed into Group C.

**Group A — earlier foundation work, six exclusive files:**

```text
reference/body_identity.py
reference/ingestion/candidate/v3_foundations.py
reference/tests/test_body_identity.py
reference/tests/fixtures/ingestion/historical_jl24_candidate_2_1_0.json
reference/tests/fixtures/ingestion/my2024_body_identity_projection.json
docs/implementation/handoffs/RA045_phase1_20261113/README.md
```

Technical tests cover these foundations, but the current owner decisions approve
RA-046 and accept RA-047 only. They do not independently establish formal acceptance
or commit readiness of this earlier phase. Owner must confirm foundation acceptance/
readiness or explicitly authorize a reviewed combined scope before committing it.
Its phase-one governance hunks are identified under Group D below.

**Group B — approved specification, one exclusive file:**

```text
docs/architecture/designs/RA-046-Candidate-v3-Exact-Wire-Contract-Specification.md
```

This task changes governance metadata/status and approval wording only. Technical
sections, wire members, eight JSON examples, hash vectors and diagnostics are unchanged.
No other file is exclusively attributable to the standalone design milestone; the
combined approval/acceptance record is a Group D hunk retained with the final RA-047
commit after the specification commit.

**Group C — accepted RA-047 implementation/handoff, 16 exclusive files:**

```text
reference/candidate_v3.py
reference/candidate_v3_evidence.py
reference/powertrain_evidence.py
reference/ingestion/serialization.py
reference/ingestion/validation.py
reference/ingestion/importing/powertrain_identity.py
reference/tests/test_candidate_v3_wire.py
reference/tests/fixtures/ingestion/candidate_v3/A.json
reference/tests/fixtures/ingestion/candidate_v3/B.json
reference/tests/fixtures/ingestion/candidate_v3/C.json
reference/tests/fixtures/ingestion/candidate_v3/D.json
reference/tests/fixtures/ingestion/candidate_v3/E.json
reference/tests/fixtures/ingestion/candidate_v3/F.json
reference/tests/fixtures/ingestion/candidate_v3/G.json
reference/tests/fixtures/ingestion/candidate_v3/H.json
docs/implementation/handoffs/RA047_candidate_v3_20261113/README.md
```

The three already-tracked code files contain only the reviewed RA-047 changes relative
to HEAD; other exclusive files are currently untracked. RA-047 needs Group A's body
module and foundation fixtures, and its test reads Group B's example blocks. Commit
them in a dependency-safe order so a clean checkout is self-contained and testable.

**Group D — shared governance files, partial staging required:**

```text
docs/implementation/CURRENT_STATE.md
CHANGELOG.md
```

| Shared file region | Intended commit allocation / exclusion |
| --- | --- |
| CURRENT_STATE section “Unified factory body identity — pure foundations completed; v3 wire contract bounded” | Foundation commit with Group A, only after owner confirms that phase's acceptance/readiness |
| CURRENT_STATE sections “RA-046 approved / RA-047 accepted — commit preparation”, “RA-047 final verification — historical checkpoint before acceptance”, and “RA-047 — Candidate 3.0.0 pure wire contract implemented” | Final RA-047 commit with Group C; retain the combined RA-046 approval/RA-047 acceptance paragraph together rather than splitting its meaning across commits |
| CURRENT_STATE Last Updated header | Shared metadata crossing milestone/unrelated updates; owner must assign it once during partial-hunk review, not treat the whole file as RA-047 |
| CURRENT_STATE MY2024 continuation and MY2023 operational/handoff sections | Unrelated pre-existing work; exclude from A/B/C commits |
| CHANGELOG Changed bullet beginning “Completed ADR-0013’s first bounded pure foundations” | Foundation commit with Group A, subject to its separate owner decision |
| CHANGELOG Changed bullets beginning “Recorded explicit Project Owner approval of RA-046 and acceptance of RA-047”, “Completed RA-047 documentation-only final verification”, and “Implemented the bounded RA-047 Candidate 3.0.0 pure wire layer” | Final RA-047 commit with Group C; includes approval, accepted implementation and verification history |
| CHANGELOG MY2023 Added entries and MY2024 continuation/other Changed entries | Unrelated pre-existing work; exclude from A/B/C commits |
| Existing ADR-0013/RA-045 architecture-acceptance records | Already in HEAD; do not stage duplicate/reordered context as new foundation or RA-047 work |

Some additions are contiguous in the raw diff and may form one large hunk. If an
interactive split cannot separate them, use an owner-reviewed edited patch/index
patch. Do not accept the combined hunk or stage whole governance files. This task
prepares no index mutation and runs no partial staging operation.

### Proposed dependency-respecting commit sequence

| Step | Purpose / suggested commit message | Exact scope | Dependency / remaining owner requirement |
| --- | --- | --- | --- |
| 1 | Retain earlier pure foundations: `Implement RA-045 pure body identity foundations` | All six Group A paths plus only its two Group D phase-one regions; header metadata allocation reviewed separately | Foundation acceptance/readiness and this commit scope still need explicit owner decision; current RA-046/047 acceptance does not supply it |
| 2 | Record approved specification: `Approve RA-046 Candidate v3 exact wire contract` | The single Group B path, whole file; no shared governance hunks | Preferred after step 1; RA-046 is approved, but staging/commit execution still needs separate authorization |
| 3 | Record verified implementation: `Implement accepted RA-047 Candidate v3 wire contract` | All 16 Group C paths plus only the Group D RA-047/combined-acceptance regions listed above | Depends on foundation/specification present in committed checkout; mixed governance patch and final staged-file review must be resolved; execution still separately authorized |

No exact step-1 or step-3 staging/commit commands are supplied while foundation
acceptance and mixed-hunk allocation are outstanding. Their file sets and messages
are explicit above; blindly staging CURRENT_STATE/CHANGELOG would include unrelated
work. An owner-authorized combined foundation/implementation commit is an alternative
only after explicit acceptance/scope review; it is not inferred here.

The **only fully unambiguous standalone file boundary is step 2**. For owner use after
separate staging/commit authorization, foundation sequencing is settled and the index
is confirmed empty:

```bash
git diff --cached --name-status
git add -- docs/architecture/designs/RA-046-Candidate-v3-Exact-Wire-Contract-Specification.md
git diff --cached --name-status
```

Stop if the index was not empty before staging, or if the second inspection lists
anything except that one specification file. Only after that owner review:

```bash
git commit -m "Approve RA-046 Candidate v3 exact wire contract"
```

These commands are a proposal, **not executed or currently authorized**. Never use
indiscriminate staging. Exclude `db.sqlite3`, MY2023_JL/MY2024_JL handoffs, research,
`run_readonly_plans.py`, `scratch/` and unrelated governance hunks from these commits.

### Final disposition and verification

**READY WITH COMMIT-BOUNDARY DECISION REQUIRED.** RA-046 approval and RA-047 acceptance
are complete for the current reviewed revisions. Remaining owner decisions concern
earlier foundation acceptance/readiness, shared-header/hunk allocation and eventual
staging/commit authorization, not a change to the accepted wire contract.

Documentation-only verification uses the existing authorized `.venv/bin/python` with
isolated database paths for system/migration checks. The full 837-test result in §G
remains applicable because all executable files/fixtures are unchanged. No migration,
historical contract alteration, unrelated work change, staging, commit, push or next
milestone is introduced. Fresh finalization results:

| Command/check | Result |
| --- | --- |
| `RIGARCHIVE_TEST_DB_PATH=/private/tmp/rigarchive-ra047-acceptance-check.sqlite3 .venv/bin/python manage.py check` | No issues; exit 0 |
| `RIGARCHIVE_TEST_DB_PATH=/private/tmp/rigarchive-ra047-acceptance-drift.sqlite3 .venv/bin/python manage.py makemigrations --check` | No changes detected; exit 0; no migration created/applied |
| `git diff --check` / `git status --short` | Clean whitespace; status identical to task start; index empty |
| Preservation and documentation checks | Only four documentation files changed among 6,158 baseline files; all eight examples and semantic/artifact vectors unchanged; links/fences valid; historical changelog entries preserved; branch/HEAD unchanged |

No full-suite rerun was needed or performed; the accepted 837-test result remains
recorded as the prior actual run, not a newly executed test claim.
