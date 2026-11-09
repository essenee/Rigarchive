# MY2021 JL construction preflight — blocked

Created: 2026-11-09
Status: Draft

The owner authorized 73 base Candidate 2.1.0 artifacts, followed by 88 approved
field decisions and final validation. Scope verification passed. Construction
stopped before emitting candidates because a retained manufacturer fuel
normalization cannot pass the unchanged direct-source validator. This is a
preflight checkpoint, not a completed construction or approval milestone.

## Verified approval scope

- 73 distinct US MY2021 consumer research rows: 23 two-door and 50 four-door.
- All 24 approved body/trim labels and all 24 earlier-only combinations retained.
- Exactly 88 approved field decisions across 70 rows: ERC 34, ERG 20, EC1 20,
  EXJ 12 and ESG 2. ECX adds no human decisions.
- CLASS-075, the EC1 electrification decision for JL21-71/JLUL74, stays deferred.
  Sport RHD and all manufacturer evidence remain in the original handoff. No
  fleet-only or postal-only restriction or steering/visibility solution is added.
- All 90 entries in the discovery manifest and all 33 entries in the owner-review
  manifest match. The eight original owner-review checks also verify the 91-file
  discovery preservation baseline, original research row digests, evidence bytes,
  new source extractions, completeness, applicability and read-only database counts.

Historical review artifacts still say approval pending; they are immutable
historical proposals. Approval authority is the owner's explicit current-chat
instructions and corrected prerequisite-order request, not a rewritten review.

## Blocking direct-source compatibility finding

JL21-70 / Unlimited Rubicon 392 / ESG has an approved reviewed normalization of
`fuel_type = gasoline`. The retained 392 manufacturer specification, PDF page 1,
says **“Fuel Requirement Premium 91 octane (R+M)/2 — required”**.

`reference/ingestion/importing/powertrain_identity.py::_supports` accepts gasoline
or petrol terminology for gasoline. It does not recognize premium/octane wording.
The existing predicate returns false for both the faithful fuel line and the
entire source page. The reproducible result is in `preflight_results.json`;
`verify_preflight.py` calls the existing predicate without changing it.

The retained 392 specification contains no gasoline/petrol term. The retained
manual's applicable gasoline sections identify 2.0L and 3.6L engines, not 6.4L.
The retained production release's gasoline/diesel boilerplate describes models
outside North America and cannot establish the US ESG fuel field. Secondary
research transcription cannot be presented as a direct manufacturer assertion.
Inserting the normalized enum into raw evidence would evade the required check.

The 88 approved decisions concern aspiration/electrification; none supplies a
separate gasoline adjudication. Adding one would exceed the exact approved scope.
Leaving gasoline null would prevent the required final complete five-field tuple.
The task explicitly prohibits application/contract changes and requires all 73
bases to succeed before approval application. Therefore no partial approval run
or substituted source assertion was attempted.

Resolution requires separate direction: authorize acquisition of applicable
manufacturer 392 fuel evidence with terminology supported by the existing
validator, or authorize a bounded validator correction for supported fuel
normalizations. No correction is implemented or implicitly approved here.

## Actual results and verification

**Constructed bases: 0. Applied decisions: 0. Candidate revisions: 0. Final
classified candidates delivered: 0.** Candidate identity, serialization and final
lineage validation remain outstanding. The approved scope is verified research;
it is not mislabeled as constructed Candidate artifacts.

Environment used: repository `.venv/bin/python`, Python **3.13.1**, Django
**6.0.7**, pypdf **6.16.1**. Both pinned requirements match `requirements.txt`.
`python -B -m pip check` returned “No broken requirements found.” No environment
was substituted and no dependency was installed or upgraded. The pip invocation
also reported its disabled, nonwritable user cache; dependency validation passed.
The documented `venv/py313/bin/python` is absent.

Executed from the repository root:

```text
.venv/bin/python -B docs/implementation/handoffs/MY2021_JL/preflight_20261109/verify_preflight.py
RIGARCHIVE_TEST_DB_PATH=:memory: .venv/bin/python -B manage.py test reference.tests.test_candidate_construction reference.tests.test_classification_adjudication reference.tests.test_structured_powertrain --noinput
RIGARCHIVE_TEST_DB_PATH=:memory: .venv/bin/python -B manage.py check
RIGARCHIVE_TEST_DB_PATH=:memory: .venv/bin/python -B manage.py makemigrations --check --dry-run
.venv/bin/python -B docs/implementation/handoffs/MY2021_JL/owner_review_20261108/validate_review.py
.venv/bin/python -B -m pip check
```

- Scope/hash verification passed; the separately reported source-compatibility
  gate blocks Stage 1. It is not a failed or bypassed test assertion.
- 65 focused Django tests passed using an isolated test database.
- Eight owner-review tests passed; their live SQLite connection is read-only.
- Django checks passed; migration consistency reported no changes. No migrations
  were applied. The full project test suite was not run.
- Live database SHA-256 before and after checks:
  `ec1eb2adb8becf62a6d8ef18e5ae2dee37d5049620faaaeec51ab8c69b0ee4f9`.
  This also matches the original owner-review baseline byte for byte.

Only this dated preflight directory was created. `CURRENT_STATE.md` and
`CHANGELOG.md` were left unchanged because no construction/approval milestone
completed. Application code, contracts, migrations, original discovery and review
artifacts remain unchanged. No correspondences, canonical records, Matrix
certification or executable import plans were created. No commit or push.

Git state remains the preexisting modified `db.sqlite3` and untracked MY2021
handoff tree, now including this report. The existing database modification
predates this task and was preserved.
