# RA-049 — Final source review and acceptance preparation

Created: 2026-11-13
Last Updated: 2026-11-13
Status: Accepted
Disposition: **ACCEPTED** by explicit Project Owner decision on 2026-11-13; source verdict PASS WITH CORRECTIONS.

Architecture approval and the exact RA-046 §15 PendingBody exception remain in force.
The Project Owner has now formally accepted the reviewed implementation and
authorized one exact 21-path local commit. Operational deployment and publication
remain outside this acceptance.
Baseline: main / `29ff1b4a42c99c8ecf9c75b77cd5b2c0dfce706f`; index empty.
The supplied 59/335/930 test counts are historical implementation evidence only.

## Scope and method

Reviewed ADR-0013, RA-045, exact RA-046 and §15, accepted RA-047/048, approved RA-049,
the implementation handoff and CURRENT_STATE against all three successor modules,
shared dispatch/approval/import/receipt code and all RA-049 tests. Traced parse →
qualified evidence → correspondence → body namespace → complete family → peers →
plan → Matrix/approval → manifest → independent transactional reconstruction →
VD/receipt persistence. Inspected actual reads/inserts and tested adversarial inputs.

Corrections are confined to existing contract/runtime paths plus one new regression
module. No model, migration, FK, contract version, Candidate wire/hash primitive,
fixture, new approval infrastructure or operational data change. Unknown/deferred
operations were not implemented merely to make an assessment eligible.

## Material source findings and narrow corrections

| Finding / governing requirement | File and function | Observed defect and correction | Reproduction/regression |
| --- | --- | --- | --- |
| F1: RA-049 §7 rejects reordered selected plans | importing/body_import.py:validate_selection | build_matrix sorted execution inputs, silently accepting a reordered list. Require the supplied list order/membership to equal the authorized rows before rebuilding. Constructors may still produce canonical new matrices. | test_reordered_execution_plans_are_rejected_without_writes; extra/missing list tests |
| F2: §1/§3 explicit supported-version dispatch and whole-candidate validation | importing/planner.py:plan_candidate_import | A v3-looking dictionary with unsupported minor version fell into legacy attribute access and raised AttributeError. Route v3-looking input through the unchanged pure reader; reject malformed/mixed dispatch as validation errors. | test_unsupported_v3_dispatch_versions_raise_validation |
| F3: §2/§3 original typed source evidence | importing/body_identity.py:Release._evidence | Native JSON decoding accepted duplicate keys/IDs; Python dictionary equality treated 2024.0 as identical to 2024. Strict JSON decoding, unique assertion IDs and canonical JSON comparison now reject ambiguous source projections without coercion. | source_duplicate_json_keys, source_duplicate_assertion_ids, source_numeric_retyping tests |
| F4: §3 known identity distinctions cannot be omitted | body_identity.py:Release._evidence | A selected positive configuration explicitly containing a roof designation still produced a door-only create plan when its interpretation was omitted. Check all declared canonical body dimensions on that selected configuration against the frozen basis. Unreported and blank optional dimensions remain unspecified; a regression prevents new missingness requirements. | test_known_source_body_discriminator_cannot_be_omitted |
| F5: §2/§3 recognized original review readers | body_identity.py:Release._generation_findings / _evidence | Existing Generation review 1.0 files were not supplied to the pure evidence checker or decoded, so available supported findings were reported unavailable/unsupported. Decode and pin the original exact payload; require the current applied published revision, coverage, selector and locator; discharge only its Generation-scope dependencies. Other reader versions remain blocked. Also reject noncanonical JSON-pointer array indices rather than int() normalization. | recognized_generation_review_is_reused_and_pinned; unknown version; locator including +0/00/-1; body-scope misuse; byte drift; legacy exact-base finding tests |
| F6: §3 reviewed restrictions and one Generation for the complete family | body_identity.py:Release._resolve / load | engine_name was omitted from correspondence restriction checks, rejecting a valid matching restriction. Reuse the existing reviewed descriptor mapping in resolution. Separately, individually valid candidates could span two different Generation UUIDs named JL; require one exact resolved parent chain across all 31, even for subset planning. | supported_engine_restriction_is_resolved; complete_family_cannot_span_different_generation_uuids |
| F7: §§2/5/6/9 nested consistency, not hashes alone | body_import_contracts.py:_semantic | Self-rehashed objects could mislabel a four-door peer equal to a two-door baseline, approve no-op with unresolved overlap, use wrong correspondence year/market, claim an unperformed no-op FK assignment or omit another Matrix row from receipt revalidation. Validate available peer/baseline/target/applicability/complete revalidation relationships. Shapes and hash algorithms are unchanged. | false_equal_body_proof; noop_with_unresolved_overlap; correspondence_snapshot; noop_cannot_claim_unperformed_body_assignment; receipt_requires_revalidation_of_every_matrix_row |
| F8: §9 scalar receipt mirrors and correct outcome | body_identity.py:_peer | Altered target scalar columns were ignored; a no-op snapshot could be substituted into a scalar creation receipt. Check target columns, source selector, action/basis and creation outcome against the embedded snapshot. Mismatches cannot establish peer equality. | scalar_receipt_target_mirrors; created_scalar_cannot_disguise_noop_snapshot |
| F9: §§3/5/10 legacy meaning and recognized body evidence | body_identity.py:_peer | An old receipt's copied body annotations were promoted after only checking its raw source hash. The adversarial copied annotation said two doors while retained JSON said four, yielding a false no-op. Remove this unsupported legacy body-promotion fallback; a material legacy overlap without a recognized body-aware original receipt reader yields explicit UNSUPPORTED_REVIEW_VERSION. Unrelated legacy nulls remain neutral, v3-backed null-FK no-ops remain supported, and legacy Engine Proof 2.0 behavior is unchanged. | test_legacy_body_metadata_cannot_stand_in_for_versioned_evidence |

The initial review module reproduced 13 failing cases before correction, and separate
pre-fix logs reproduce scalar-outcome, legacy-promotion, unsupported-dispatch,
mixed-Generation and pointer defects. The added blank-dimension control ensures the strengthened
coverage rule does not invent a required body attribute. Logs are retained under
/private/tmp/ra049-review-*-reproduction.log. This is actual reproduction evidence,
not findings inferred from test names. The additional negative/transaction tests
check that the fixes do not relax scope or authorization.

## Contract compliance and source-reader support matrix

All existing RA-049 keys/nullability/version tags and root-minus-self-hash algorithms
are retained. Validation still rejects unknown keys, duplicate keys/IDs, noncanonical
ordering/timestamps, invalid UUID/Token/integer values and nonfinite numbers. New
semantic checks reject inconsistent nested statements even if all outer hashes were
recomputed. No cyclic hash reference is introduced. Candidate v3 A–H and historical
2.1.0 artifacts/hash behavior are unchanged.

| Input / reader | Readiness and actual behavior | Classification |
| --- | --- | --- |
| Native retained JSON assertion projection | Strict decoding and typed assertion match against actual bytes; duplicate IDs/keys and omitted known body discriminators reject | Supported source reader; integration corrected |
| Pinned MY2024 inventory CSV / trim audit | Exact pinned bytes and row/model-code/heading joins; proposed powertrain columns do not become approval | Supported, deliberately bounded source reader |
| Published Generation correspondence 1.0 | Current chain/content/applicability/restrictions checked; exact parent chain across release | Supported; matching engine restriction and family-scope defects corrected |
| Candidate FindingReference to original Generation review 1.0 | Original bytes, exact published payload, qualified selector, scope coverage and locator verified; original snapshot included in reviewed_artifacts | Supported reader integration corrected; permits Generation interpretations only |
| Body-import receipt 3.0.0 | Closed complete snapshot/row/scalar/source checks; supports evidenced current peer comparison, including a null FK with original v3 body evidence | Supported; nested/scalar validation corrected |
| Legacy Engine Proof 2.0 in its original importer | Original behavior preserved; it is not a successor body/receipt proof | Supported legacy contract, not authority for unknown body metadata |
| Material legacy peer without a recognized body-aware receipt reader | Explicit dependency assessment, not a manufactured body equality/difference or complete proof | Missing decoder/support dependency; not evidence acceptance |
| Candidate-bound legacy adjudication for a different v3 base | Reject original subject mismatch; no re-binding or new classification finding invented | Incompatible original authority, not missing source truth |
| Unknown review versions / unknown extraction formats | Explicit unsupported-reader dependency; no automatic decoder or hash-only approval | Unsupported reader contract/dependency, not silently treated as unavailable bytes |
| Genuine missing/changed retained bytes | UNAVAILABLE_ARTIFACT / changed-byte dependency or stale execution | Actual unavailable/drifted evidence, not a software-reader success |
| ExistingBody execution, Series, parent writes, other profiles | Explicitly excluded from the initial runtime profile | Deferred/excluded functionality, not review defects |

Original manufacturer PDFs or review formats without an implemented reader are not
claimed readable merely because they are present. Distinguish missing bytes from
unsupported decoding in actual production preparation. No research/acquisition or
second door-classification review was performed. No binding UUID/hash, source or
correspondence was fabricated. Test-only sources are explicitly synthetic and isolated.

## Identity and executable slug verification

The actual Release resolver/planner and existing structured model slug builder are
used by the acceptance tests. All 31 active members are independently joined to pinned
inventory and source evidence. A Matrix subset cannot reduce the family; mixed
Generation UUIDs now reject before planning. Body semantic digest participates in
baseline/2; descriptors/slugs never replace it. Same-body/five-field equality requires
attributable active support; different established doors cannot merge. Sparse compatible
bases, inactive equality and material unsupported/null overlap do not permit unsafe create.

Executable assertions independently compare every produced slug against the retained
expected outcomes: all 31 unique, all ten exact pairs receive -2-door/-4-door after
the complete structured base, and 11 single-body offerings retain their bases.
Permutation/subset/import-order tests, inactive occupancy, residual collision and
180/181-character tests pass. These are runtime tests, not a documentation-only string
check. Existing nonempty slugs and historical canonical identities are never rewritten.

## Human authorization and transaction conclusions

Matrix3 binds exact ordered subjects, candidate/plan hashes, actions, body UUIDs,
slugs, baseline and whole-family digest. Manifest3 binds exact Matrix/Approval1.
Execution rejects extra/missing/reordered/changed plans, approval drift and review-only
mode. The adversarial fabricated approval JSON is rejected without affirmative
confirmation. Generation/classification findings do not grant import authority.

Inherited limitation: Approval1 and confirmed=True attest a real operator action at
the existing trusted caller/CLI boundary; they are not signatures or technical human
actor authentication. A caller lying about confirmation is outside that existing
trust model. This review adds no authentication/approval system and makes no stronger
claim. Execution agent attribution remains separate from the human operator.

All selected rows are independently reconstructed inside the same transaction against
a common pre-batch state before the first insert. The executor creates only enumerated
VDs and receipts, with no parent/existing-row writes. No-op preserves the row and FK.
Receipt failure rolls back earlier inserts. Real SQLite threaded tests exercise exact
and body-distinct races; lock/uniqueness errors propagate for complete rollback without
retrying old approval. Fresh retries use fresh planning/confirmation. A separate real
TransactionTestCase verifies that an external reporting failure after successful executor
return leaves the committed VD/receipt intact; the executor does not call it rollback.

Receipts retain the exact body_import root and complete Manifest3/Plan3/Revalidation3,
actual row/fields, outcome, time, agent and hashes. Full Matrix revalidation coverage
and scalar/source/action mirrors now agree. A no-op cannot claim an FK assignment it
did not perform. Later authorized shared-body edits do not rewrite original snapshots.
The legacy Engine Proof 2.0 reader rejects v3 receipts explicitly.

## Final source-review verification (historical checkpoint)

Fresh runs on the final corrected executable bytes:

| Check | Result |
| --- | --- |
| All RA-049 focused modules, including 27 final-review regressions | **86 tests passed in 46.501 s** |
| Focused + evidence/legacy import/serialization/Matrix/approval + RA-048 + A–H/body foundations | **362 tests passed in 52.113 s** |
| Complete Django suite | **957 tests passed in 90.054 s**, zero failures/errors/skips |
| manage.py check | No issues |
| manage.py makemigrations --check | No changes detected |
| git diff --check and untracked-file whitespace checks | Passed |

Commands use the previously authorized .venv/bin/python fallback (Python 3.13.1 /
Django 6.0.7) with RIGARCHIVE_TEST_DB_PATH=/private/tmp/ra049-review.sqlite3. Source,
media, concurrency and migration tests use isolated databases/temporary roots; no
command targets operational db.sqlite3. Full logs are retained at:

- /private/tmp/ra049-review-focused-final.log
- /private/tmp/ra049-review-targeted-final.log
- /private/tmp/ra049-review-full-final.log

The prior 59/335/930 counts, and intermediate successful runs before the final locator
correction, remain historical evidence and are not substituted for final verification.

## Owner-authorized 21-path acceptance commit inventory

Whole files:

1. reference/ingestion/body_import_contracts.py
2. reference/ingestion/importing/body_identity.py
3. reference/ingestion/importing/body_import.py
4. reference/ingestion/importing/__init__.py
5. reference/ingestion/importing/importer.py
6. reference/ingestion/importing/workflow.py
7. reference/ingestion/importing/matrix_workflow.py
8. reference/ingestion/importing/planner.py
9. reference/ingestion/importing/powertrain_identity.py
10. reference/ingestion/manifest.py
11. reference/ingestion/matrix.py
12. reference/tests/body_import_support.py
13. reference/tests/test_body_import_contracts.py
14. reference/tests/test_body_aware_import.py
15. reference/tests/test_body_import_final_review.py
16. docs/architecture/designs/RA-049-Body-Aware-Candidate-v3-Import-Contract.md
17. docs/implementation/handoffs/RA049_body_aware_import_contract_20261113/README.md
18. docs/implementation/handoffs/RA049_body_aware_import_contract_20261113/FINAL_REVIEW.md

Shared/governing document boundaries:

19. RA-046 specification: only the already owner-approved appended §15 clarification;
    historical sections unchanged. No accepted ADR changes.
20. docs/implementation/CURRENT_STATE.md: only the RA-049 milestone section. Exclude
    pre-existing Version 1.6→1.9 and all other milestone sections.
21. CHANGELOG.md: only the single RA-049 milestone bullet under Unreleased → Changed.
    Exclude MY2023/MY2024 and all unrelated entries.

This inventory includes initial implementation and final corrections; the review itself
changes only the three new core modules, planner dispatch, new review tests and scoped
handoff/status documentation. Do not stage entire mixed shared files. The Project Owner has explicitly authorized this exact local commit boundary.

Explicit exclusions: db.sqlite3 and sidecars; MY2023_JL/MY2024_JL directories; research;
scratch; run_readonly_plans.py; RA-048 files/assignment inventory; historical Candidate
2.1.0 or A–H fixtures; every path not listed above. Original accepted RA-048 commit and
predecessors remain unchanged.

## Source-review preservation checkpoint

Operational database SHA-256 before review:
`be3b1cfe8f03feda457f2aa7ef397b96f2cd673971aaf6a999c171c5523b32a6`.
After review and tests the SHA-256 is identical:
`be3b1cfe8f03feda457f2aa7ef397b96f2cd673971aaf6a999c171c5523b32a6`.
Whole-file task-baseline checks preserve unrelated files, all authoritative historical
candidate/fixture/migration/assignment bytes, and every operational database byte.
Index remains empty; branch/HEAD remain main / 29ff1b4. The pre-existing modified
status of db.sqlite3 remains, not a new write. No SQLite sidecars were created.
The exact shared-only HEAD-relative patch is prepared for later review at
/private/tmp/ra049-final-review-shared-documents.patch and checked for applicability
without staging. The complete 21-path inventory above excludes unrelated work.
No operational migration, parent population, historical FK assignment, canonical
publication or production Matrix execution was attempted. No stage, commit, push,
reset, cleanup or unrelated data change.

Remaining prerequisites are actual operational authorizations/data: migration 0011,
reviewed existing body parents, complete real supported v3 release/source/finding
bytes and exact published correspondence coverage, any required missing reader,
and fresh exact affirmative production Matrix approval. Historical assignments remain
a separate authorized operation. No new door review is imposed. No new architectural
decision is required for these corrections; excluded features remain excluded.


## Formal acceptance checkpoint — 2026-11-13

The owner accepts RA-049 and all reviewed corrections. One local commit with the
exact inventory above is authorized. Fresh focused, targeted and full-suite results
and staged-content verification will be recorded before the commit. The historical
source-review results/no-commit statements remain accurate for their checkpoint.
No executable file, schema, fixture or historical contract is changed in acceptance.
The approval boundary remains inherited operator confirmation, not a human signature.
An operational-readiness assessment will be prepared separately after the local
commit and left unstaged/uncommitted. No operational writes or push are authorized.


Fresh acceptance verification: **86 focused tests passed in 44.699 seconds; 362 targeted tests in 50.513 seconds; 957 full-suite tests in 88.227 seconds**, with zero failures/errors/skips. System checks, migration drift and staged whitespace passed. All tests used isolated databases; reviewed executable bytes and historical artifacts remained unchanged.

Exact staged inventory and shared-only hunks are verified before the authorized local
commit. No operational data is included; no push is authorized.
