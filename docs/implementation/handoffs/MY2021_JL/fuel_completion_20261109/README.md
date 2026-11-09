# MY2021 JL consumer candidate completion

Created: 2026-11-09
Status: Accepted

**All 73 current consumer Candidate 2.1.0 artifacts have complete five-field
structured powertrain identities: 23 two-door and 50 four-door, retaining all 24
approved body/trim labels.** The owner-approved `fuel_type = gasoline` decision
for JL21-70 resolves the sole outstanding classification gap.

The other 72 candidate artifacts and their exact digests are unchanged. All 88
earlier decisions, source evidence, original bases and superseded artifacts remain
preserved. The three ECX candidates retain direct technical classifications.
Sport RHD JL21-71 / JLUL74 and CLASS-075 remain separately preserved and deferred;
no consumer candidate, fleet/postal-only restriction or steering/visibility
interpretation was created for them.

## Fuel classification and original failure

RA-044 §2 and `reference/powertrain.py` define broad fuel categories `gasoline`
and `diesel`. Octane grade is not one of the five identity fields. The manufacturer
392 specification page 1 says **“Fuel Requirement Premium 91 octane (R+M)/2 —
required”**. Its original PDF, full page assertion
`FCA_MY2021_Wrangler_392_specifications-p1` and exact wording are preserved.

The previous candidate had null fuel_type and failed complete validation with
`Missing evidenced powertrain attribute: fuel_type.` The direct-source parser
requires a literal gasoline/petrol term and cannot normalize the premium-octane
line by itself. The line does not literally say gasoline or unleaded; no such
wording was fabricated. Premium 91 (R+M)/2 is recorded as **required**, not merely
recommended, and remains distinct from the approved broad gasoline category.

The new claim is explicitly **human adjudicated, moderate confidence**, with
reasoning, engine/candidate applicability, source references and limitations. It
does not present a derived classification as a direct manufacturer enum assertion.
No octane field, taxonomy extension, parser change or new ADR was necessary.

## Existing workflow and resulting revision

The unchanged workflow validates exactly one human-classification document per
candidate projection and rejects chaining on an already-adjudicated base. The
new cumulative finding therefore binds the **original unclassified base**. It
carries the exact two previously approved ESG claims forward and adds one new
fuel claim, using the existing `adjudicate_canonical_import --classification-review`
CLI, `--operator project_owner`, and owner-authorized `APPROVE CLASSIFICATIONS`.

There are **89 distinct approved field decisions** across the current consumer
scope: the original 88 plus one fuel decision. The new envelope contains three
claims, including two unchanged carry-forwards; those are not counted as new
decisions. All original 70 approved envelopes and 88 individual decision records
remain byte-for-byte intact. Only one new approved envelope and one new candidate
revision were created.

Current Rubicon 392 identity:

```json
{
  "engine_displacement_liters": "6.4",
  "engine_cylinders": 8,
  "engine_aspiration": "naturally_aspirated",
  "fuel_type": "gasoline",
  "electrification_type": "none"
}
```

Candidate content digest:
`sha256:d080dbd70cd54daa4d827114d72afb7127b34fbda95e89c0cf7582ac3f8086bd`.

The superseded candidate digest remains
`sha256:37e84a45f8d4a92bfbeada248af7bd03238defce30af1e0f41716996acbfb30c`;
the original base digest remains
`sha256:624f892484d1c8408ab4a4142859fa669c19196fb325ee2818d83a7403cdd622`.
The base's historical unresolved-fuel note is retained as original lineage; the
new approved projection and current index establish the resolved current value.

## Deliverables

- `JL21-70.fuel-r2.approved.adjudication.1.1.json`: approved cumulative finding.
- `JL21-70.fuel-r2.candidate.2.1.0.json`: new, fully classified candidate revision.
- `JL21-70.fuel-r2.proposed.adjudication.1.1.json`, `adjudication_cli.txt`:
  candidate-bound proposal and actual approval transcript.
- `current_candidate_index.json`: complete 73-candidate current index, semantic
  content digests and serialized-file hashes; replaces the previous current view.
- `superseded_artifact_reference.json`: original base, prior adjudication,
  superseded candidate and new revision hashes.
- `contract_and_evidence_review.json`, `authorization.json`: contract, original
  failure, premium-octane source wording, approval, scope and limitations.
- `validation_results.json`, `prior_88_approval_verification.json`: all 73 complete
  identities and exact preservation of every original approved claim.
- `evidence_lineage_report.json`, `sport_RHD_preservation_reference.json`:
  source-byte lineage and unchanged RHD deferral.
- `environment.json`, `test_and_environment_report.md`, original test/check logs:
  actual environment and verification results.
- `preservation_baseline.json`, `artifact_hashes.json`: original handoff/code/DB
  preservation and hashes for this completed checkpoint.
- `resolve_fuel.py`: bounded artifact driver using existing application APIs;
  no application code or accepted contract is modified.

## Final validation and limits

All 73 candidate contracts, complete identities, source hashes, approval/base
lineage, uniqueness and serialization round trips pass. The other four 392 fields
are unchanged. All 88 prior claims remain exact in active projections, including
the two carried forward for ESG. The other 72 candidate/index entries are unchanged.

Verification used `/Users/cosmo/dev/Rigarchive/.venv/bin/python`, **Python 3.13.1**,
with **Django 6.0.7** and **pypdf 6.16.1**, matching requirements. **713 full project
tests and 65 focused tests passed**, as did Django system checks, migration
consistency and dependency checks. Tests used isolated databases and temporary
media. No dependency was installed or upgraded.

Live database SHA-256 remains
`ec1eb2adb8becf62a6d8ef18e5ae2dee37d5049620faaaeec51ab8c69b0ee4f9`,
matching both this task's baseline and the original owner-review baseline. Every
preexisting MY2021 handoff file and inspected application/accepted contract file
matches its preservation hash. `CURRENT_STATE.md` and `CHANGELOG.md` record the
completed classification and validation milestone. Earlier dated checkpoint
READMEs remain unchanged historical records; this README supplies current status.

**No consumer classification blocker remains before generation-correspondence
preparation. Separate owner authorization is still required for that work.**
RHD representation remains deferred outside the approved consumer scope.

No application, taxonomy, validator, schema, migration, live database, canonical
record, correspondence, Matrix certification, executable import plan or backfill
was changed or created. No commit or push occurred. The preexisting modified
database and other unfinished work were preserved; this task adds only this dated
checkpoint and targeted updates to the two status documents.
