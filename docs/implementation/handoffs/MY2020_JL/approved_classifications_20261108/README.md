# MY2020 JL approved human classifications and High Altitude naming

Created: 2026-11-08
Status: Accepted

The project owner approved the exact consolidated MY2020 review. Preflight
verified the complete reviewed artifact hash manifest, all49 candidate identities,
43 proposal records containing60 field decisions, qualified evidence references,
confidence, limitations and the three current naming revisions before any approval.
There were no scope/hash discrepancies. The source observations and reviewed
derived conclusions remain distinct; no direct manufacturer assertion was invented.

## Completed approvals

| Engine | Approved field | Value | Candidate count |
|---|---|---|---:|
| ERC | engine_aspiration | naturally_aspirated | 17 |
| ERC | electrification_type | none | 17 |
| ERG | engine_aspiration | naturally_aspirated | 3 |
| EC1 | electrification_type | none | 15 |
| EXJ | electrification_type | none | 8 |

Exactly **60 field decisions were applied to43 candidates**, producing43 separate
approved Adjudication1.1 records and43 separate Candidate2.1.0 revisions. The six
already validated EC3 candidates are referenced unchanged. All49 now have complete,
validated five-field structured powertrain identities. No other supported field
or classification was changed. Approval scope remains US MY2020 Wrangler JL only.

Every approval used the existing `adjudicate_canonical_import --classification-review`
CLI, explicit human operator `project_owner` and the owner-authorized response
`APPROVE CLASSIFICATIONS`. This recorded a human domain finding and projected a
new candidate; it did not run a canonical import. Each subprocess used an isolated
in-memory Django DB configuration and skipped unrelated command checks. Source and
candidate validators ran in the workflow and again after output. Full per-record
CLI audit output and zero exit codes are retained under `cli_audit/` and indexed in
`approval_execution_index.json`.

Approved evidence anchors are exactly equal to their proposed predecessors.
Reasoning, confidence, applicability, limitations and qualified source references
were not rewritten. Only adjudication decision, reviewer, recording timestamp and
adjudication hash changed. The retained proposal language about pending sign-off
is historical context; the separate approved declaration records the current
owner decision. EXJ retains **moderate confidence**, the alternator/manual linkage
as a human-derived conclusion, the secondary-source and gasoline-family manual
applicability limitations, and the lack of a single explicit OEM nonhybrid statement.
This approval does not convert that conclusion into manufacturer wording or extend
it to another year, market, engine or configuration. Reused MY2019 evidence does
not propagate MY2019 approvals.

## High Altitude

The owner approved **Unlimited High Altitude** as a distinct marketed trim for
JL20-33, JL20-34 andJL20-35. The exact three naming revisions were verified against
the previous review hashes, manufacturer marketed-edition evidence and source
model family **Wrangler Unlimited Sahara / JLJP74**. That relationship, raw guide
labels, original candidates and predecessor hashes are preserved.

JL20-33 (EC3) keeps its existing naming revision without another candidate copy.
JL20-34 (ERG) andJL20-35 (EXJ) receive classification revisions built on their
reviewed naming revisions. All three final names are Unlimited High Altitude.
The grade/name approval is pinned in `authorization.json` to the exact reviewed
naming identities; no import-manifest-bound grade finding or executable plan was
fabricated. Any later planning workflow must consume the appropriate accepted
review controls in its separately authorized scope.

## Current artifact selection and preservation

- `candidate_index.json`: authoritative49-row final selection for the next task,
  with current semantic/file hashes, complete tuples, approved declaration links,
  High Altitude approval references and superseded candidate paths/hashes.
- `approval_execution_index.json`: exact proposal-to-approved-record-to-candidate
  lineage and CLI audit paths;43 records/60 field decisions.
- `authorization.json`: exact owner scope, reviewed table/hash manifest and
  current naming/proposal bindings.
- `preflight_verification.json`: verification completed before approval execution.
- `validation_results.json` and `final_verification.json`: actual validation,
  isolated tests, database preservation and remaining publication work.
- `preservation_baseline.json`: preexisting MY2020 artifact hashes and liveDB hash.
- `artifact_hashes.json`: hashes of this completed approval checkpoint.

Original proposals, candidates, evidence, discovery/review reports and naming
artifacts are untouched. Earlier reports correctly describe their historical
unapproved state; do not select their incomplete candidates for future work.
The final index retains predecessor chains instead of overwriting those reports.

## Verification and next boundary

All49 final candidates pass Candidate2.1.0 validation, complete structured
powertrain checks, retained source byte validation, approved-human lineage
validation and serializer round trips. All43 approved adjudications pass the
approved-only gate and preserve their exact proposed evidence anchors. Final
semantic identity tuples are unique across all49 rows. Six EC3 artifacts and
all preexisting work remain unchanged. Focused isolated tests and final database
counts/hash verification are recorded in `final_verification.json`.

No classification/naming blocker remains for this exact49-candidate set.
Generation correspondence review/publication remains a separate task: source
identities, source namespaces, MY2020 applicability, intended canonical target
and full final-candidate coverage must be reviewed using the accepted workflow
before publication is authorized. Existing MY2019 mappings cannot be extended
by this classification approval. The source archive's missing two-door July2
revision and retained secondary-observation limitations remain documented; none
is sole offering evidence for a candidate in this set. Exhaustive discovery of
all possible unretained revisions is not certified by these approvals.

No correspondence was published; no Matrix was certified; no import plan or
canonical import, database write, backfill, migration, application/contract change,
commit or push occurred. The liveDB intentionally continues to differ from the
sanitized tracked snapshot and was never replaced or staged.
