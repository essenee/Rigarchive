# Human classification adjudication and MY2019 ERC proposal preparation

Created: 2026-11-08
Status: Proposed

Implementation was delivered for review with ten unapproved ERC findings. The
owner subsequently approved the exact classifications in a separate task; that
approval and its separate candidate revisions are recorded below. Policy or
implementation authorization alone did not approve the facts.

## Authority and decisions

The current owner task approves the general operating policy: manufacturer
specifications are preferred, not mandatory; supported human adjudication is the
normal fallback; direct source text and inferred conclusions must remain distinct.
This explicitly extends the earlier grade-only adjudication restriction for the
current task. Accepted ADRs, governance files and historical contracts were not
edited. No ADR, new application, engine entity, database migration or general
classification framework was introduced.

The smallest implementation reuses CanonicalImportAdjudication's existing fields,
serializer/hash, CLI attribution/confirmation and evidence document lineage.
Version 1.0 remains the existing grade contract. Explicit version 1.1 binds
classification review metadata within its typed evidence anchors. The initial
consumer is bounded to filling unknown existing controlled powertrain categories
for any manufacturer. Unsupported attributes and replacement of established facts
are rejected; further domain consumers require their own authorized implementation.

Candidate 2.1.0, Manifest/Matrix 2.1, resolution 1.1 and engine proof 2.0 retain
their wire shapes and identity meaning. Human declarations are qualified evidence
documents, not executable unknown-field payloads or falsely attributed manufacturer
statements. Their structured raw values are deliberately rejected by the unchanged
direct-source parser. Only an exact approved human projection can supply them.

## Files changed in this task

- New `reference/ingestion/classification_adjudication.py`: proposal/approval
  validation, retained-path confinement, exact original candidate/source binding,
  explicit human declaration projection, and peer-receipt revalidation. No DB work.
- `reference/ingestion/contracts.py`: documents the adjudication version split;
  no dataclass field or old serialization change.
- `reference/ingestion/validation.py`: dispatches adjudication 1.1 validation;
  legacy grade validation remains intact.
- `reference/ingestion/importing/powertrain_identity.py`: separately validates
  approved human evidence before using it, retaining direct-source checks and
  checking retained human provenance on canonical peer assessments.
- `reference/management/commands/adjudicate_canonical_import.py`: existing command
  gains classification review mode, declared human operator, explicit confirmation,
  exclusive new output paths and separate candidate revision. Legacy grade mode
  retains its required arguments and behavior.
- New `reference/tests/test_classification_adjudication.py`: synthetic regression
  coverage of proposals versus approvals, scope/hash/source/projection tampering,
  unsupported/contradictory values, no established-value override, cyclic-base
  rejection, source-type laundering, CLI confirmation, generation gates, planning,
  execution receipts, stale approval rejection, Matrix replay and peer lineage.
- MY2019 `erc_classification_proposals_20261108/`: ten unapproved adjudications,
  index/CSV, source dossier and supporting documents, contrary-scope original
  PDFs, preservation manifest and review README. Existing evidence is preserved.
- `docs/development/INGESTION_PROTOCOL.md`, `CURRENT_STATE.md`, `CHANGELOG.md`
  and this task report document verified behavior and pending human findings.

## Authorization and audit boundaries

The review command creates no database records. Decline/EOF writes nothing.
Confirmation approves only the displayed fact finding; future import execution
still requires exact human authorization under existing manifest/matrix controls.
Hashes and declared roles provide integrity and attribution, not cryptographic
human identity. No stronger identity-authentication system is claimed or added.

An approved declaration pins the original candidate digest and artifact path,
qualified support documents, field decisions, reasoning, scope, limitations,
confidence and contradiction status. The independent approved candidate digest
then binds that declaration through the existing normal workflow. Candidate and
approval changes are rechecked during validation/execution and peer assessment.
Existing receipt resolution documents retain the semantic adjudication hash,
actual byte hash, reviewer/time and original supporting lineage. The historical
grade-specific receipt hash field and old receipts are not repurposed or rewritten.

## Verification

All tests use `.venv/bin/python` (Python 3.13.1, Django 6.0.7, pypdf 6.16.1),
`PYTHONDONTWRITEBYTECODE=1`, `RIGARCHIVE_TEST_DB_PATH=:memory:`, and isolated test
evidence/media. Synthetic execution tests exercise receipts and matrix behavior
only in Django's disposable test database; no development import or migration ran.

The final focused selection comprises classification adjudication, legacy
adjudication workflow, structured powertrain, generation-projection completeness
and ingestion serialization. The full suite was intentionally not run under the
task's focused-test instruction. System and migration consistency checks use the
isolated in-memory default database. Final actual results are appended below.

Initial focused testing exposed a test expectation mismatch: stale human evidence
is rejected by the existing workflow's manifest preflight before its stale-plan
result branch. The regression now specifically requires that rejection and zero
canonical rows; application validation was not loosened. Earlier intermediate
selections passed 96/99 tests while the security regressions were being added.

Ten actual ERC proposals validate and are rejected by approval-required validation.
They have moderate confidence, explicit derived reasoning and per-candidate scope.
No actual ERC fact is approved, and no real candidate revision/import plan was
created. Remaining work is human review of those proposals, followed only under
separate authorization by generation publication and final canonical review.

No commit, push, staging, backfill, development migration or live database write.
Existing uncommitted work and backups remain preserved. No task scope deviation.

### Final actual results

- Final focused selection: **100 tests passed**, zero failures/errors, including
  13 new classification regressions. Earlier test expectation mismatch is resolved
  as described above. No full-suite result is claimed.
- `manage.py check`: zero issues.
- `manage.py makemigrations --check --dry-run`: no changes detected.
- `git diff --check`: passed.
- Ten real proposals validate and all ten reject approval-required consumption.
  All original real ERC classifications remain null.
- Development database SHA-256 remains
  `b045601a33811b44a443b7c0cc78ce916e9af476cb3c5f4c5b94dc2fdf18e26f`.
- Changes remain uncommitted on `main`; pre-existing modifications/untracked work
  are preserved. No commit or push performed.

## Subsequent owner classification approval (2026-11-08)

The owner explicitly approved `engine_aspiration=naturally_aspirated` and
`electrification_type=none` for the exact ten reviewed US MY2019 ERC candidates,
preserving the evidence, limitations and moderate confidence. Ten successful
invocations of the existing classification adjudication workflow created new
approved findings and separate candidate files. Original proposals and candidates
were not altered. The [approval report](../handoffs/MY2019_JL/director_review/erc_approved_classifications_20261108/README.md)
and indices record the exact scope, candidate/proposal/approval hashes and paths.

All 19 selected MY2019 artifacts now pass complete five-field validation, retained
source/approval lineage checks and serialization round trips. The nine EC3
artifacts are unchanged. Forty-four focused approval/lineage/serialization tests
passed using isolated resources. No application code changed in this approval
task. All 184 prior handoff files and the development database retain their before
hashes. No canonical planning, correspondence publication, import, backfill,
development migration, commit or push occurred.
