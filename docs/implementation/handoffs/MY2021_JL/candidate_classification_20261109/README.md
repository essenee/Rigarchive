# MY2021 JL base construction and approved classifications

Created: 2026-11-09
Status: Draft — artifact stages complete; final five-field validation incomplete

This checkpoint retains **73 Candidate 2.1.0 bases**, applies the exact **88
owner-approved field decisions**, and indexes **73 current candidates**. It is
not a completed final-validation milestone: **72 current candidates have complete
five-field identities; JL21-70 / Unlimited Rubicon 392 retains null fuel_type**.

Both base and current scope are exactly **23 two-door / 50 four-door**, with all
24 approved body/trim labels and all 24 earlier-supported combinations absent
from the latest guides. The original 74-row discovery, its 27 guides/four technical
PDFs, 900 QOP observations, 106 powertrain excerpts, 312 package/option pages and
owner-review package are unchanged. Nine model codes remain in discovery; eight
participate in this consumer scope. JLUL74 is separately preserved and deferred.

## Deliverable map

| Artifact | Contents |
| --- | --- |
| `authorization.json` | Current owner approval, exact 88 decision IDs, approved names, scope and limits |
| `preservation_baseline.json` | All preexisting MY2021 handoff file hashes and live database hash |
| `scope_preflight.json` | Approval/scope verification at the beginning of construction; includes the known fuel-compatibility finding |
| `environment.json`, `dependency_check.txt` | Actual interpreter, pinned dependency versions and pip dependency check |
| `base_candidates/`, `base_candidate_index.json` | Exactly 73 retained bases, semantic content digests and serialized-file hashes |
| `assertion_sets/` | 317 retained SourceAssertionSet 1.1.0 artifacts, preserving authentic source references/bytes |
| `proposals/`, `adjudications/`, `cli_audit/` | 70 exact-base proposals, 70 approved adjudication 1.1 artifacts and original CLI transcripts |
| `approved_field_decisions/`, `approved_field_decision_index.json` | 88 individual approved field-decision records, each linked to its contract adjudication and base/current digest |
| `classified_candidates/` | 70 versioned approved candidate revisions |
| `current_candidate_index.json` | All 73 current references and hashes; three ECX entries point to unchanged, fully sourced bases |
| `approval_application_index.json`, `approval_application_report.md` | Exact applied counts and immutable base/proposal/approval/revision bindings |
| `superseded_artifact_index.json` | All 70 superseded bases retained in place, with exact hashes; ECX bases are current |
| `evidence_lineage_report.json` | Per-row manufacturer names/model codes, QOP/pairings, documents, assertion sets and digests |
| `sport_RHD_preservation.json` | Original RHD row and deferred CLASS-075, original preservation record/hash and unresolved semantics |
| `validation_results.json`, `validation_and_test_report.md` | Contract/evidence results, tests and the one final completeness failure |
| `build_artifacts.py` | Bounded artifact-only driver using the existing builder and classification CLI |
| `artifact_hashes.json` | All files in this checkpoint except the manifest itself |

## Sequence and decisions

The base checkpoint was fully retained and validated before any approval CLI ran.
Unresolved fields remained null. In addition to the 88 reviewed classification
fields, JL21-70's fuel value remained null under the task's unresolved-field rule:
the unchanged direct-source predicate cannot consume its premium-octane wording.
This permitted construction and the authorized classifications without pretending
that the final complete-identity requirement had passed.

Exactly 88 decisions were then applied using the existing human-adjudication
workflow. The established contract bundles fields per candidate, so **70 approved
contract artifacts contain 88 field decisions**, with **88 individually retained
decision records**. Eighteen candidates have two approved fields; 52 have one.
No duplicate or RHD adjudication was created. Human conclusions remain moderate
confidence, with the exact reviewed reasoning and limitations and candidate-bound
scope. Source observations remain manufacturer observations; human conclusions
are not relabeled as direct manufacturer statements.

Raw model headings, original column labels, normalized approved names, guide
revision applicability, exact engine/transmission pairings and positive QOP cells
remain in each base's `research_revision_lineage` and the final projection. Model
specific package pages remain unmapped evidence; general pages are retained by
source hash and page locator in the lineage. No conditional option catalogue,
transmission-only identity or extra package baseline is synthesized.

The base, source-set, adjudication and candidate serializers remain unchanged.
The driver narrows an engine column where a QOP token such as 22L would otherwise
be mistaken for displacement by the existing predicate; full original table and
segment evidence remain retained. This is a faithful transcription, not a new
engine classification or a validator change.

## Remaining issue and completion limit

For **JL21-70 / ESG**, aspiration and nonhybrid were applied exactly as approved.
`fuel_type` remains null. The retained 392 specification page 1 says “Premium 91
octane (R+M)/2 — required”; the existing `_supports` predicate requires a gasoline
or petrol term. The original source does not contain one. The general manual's
2.0L/3.6L gasoline section cannot be extended to 6.4L, nor can global market
boilerplate or a secondary transcription be relabeled as a US ESG manufacturer
assertion. No additional fuel adjudication belongs to the approved 88 decisions.

The exact final completeness error is **“Missing evidenced powertrain attribute:
fuel_type.”** The full task is therefore incomplete. Resolution requires separate
authorization for applicable manufacturer fuel evidence or a bounded correction
of the direct-source validator. Application code, contracts and migrations were
not changed. No correspondence preparation or publication was performed.

Sport RHD JL21-71 / JLUL74 remains in discovery with CLASS-075 deferred. There is
no consumer Candidate for it, no fleet-only/postal-only assertion and no invented
steering or visibility interpretation. This deferral does not remove any of the
73 approved consumer rows.

## Verification and workspace status

All 73 base/current contracts, evidence hashes, identities, uniqueness and
serialization round trips passed. All 88 decision bindings and the 70 approved
projection lineages passed. Complete five-field validation passed for **72/73**;
its single failure is retained explicitly, not bypassed.

- Python 3.13.1 via repository `.venv/bin/python`; Django 6.0.7 and pypdf 6.16.1
  match `requirements.txt`; pip reports no broken requirements.
- Full project suite: **713 tests passed** using an isolated test database and
  temporary media directory.
- Focused candidate/classification/structured-powertrain suite: **65 passed**.
- Original owner-review preservation/scope/evidence suite: **8 passed**.
- Django system checks and migration consistency checks passed; no migrations
  were applied. See the test report for commands and original logs.
- Database SHA-256 remains
  `ec1eb2adb8becf62a6d8ef18e5ae2dee37d5049620faaaeec51ab8c69b0ee4f9`,
  matching both the execution baseline and original owner-review baseline.

Files created are confined to this dated checkpoint. `CURRENT_STATE.md` and
`CHANGELOG.md` record completed artifact stages and the incomplete final gate.
Original discovery/review/preflight files, source PDFs and all superseded artifacts
are preserved. Initial construction/approval setup failures and the successful
resumed runs are retained in their respective build logs; no accepted artifact
was overwritten to resume.

No architectural decision or migration was introduced. No canonical records,
published correspondences, certified Matrix, executable import plans, backfills
or live database writes occurred. No commit or push. Git's preexisting modified
`db.sqlite3` and untracked MY2021 handoff tree remain; this task additionally
changes the two status documents and adds this checkpoint.
