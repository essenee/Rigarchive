# MY2020 JL generation correspondence verification — publication blocked

Created: 2026-11-08
Status: Proposed

**No correspondence was published.** Phase1 found a document-compatibility
blocker, so the owner's conditional authorization did not become executable.
No database backup was created because no publication/write was permitted.

## Scope and current coverage

| Manufacturer model code | US MY2020 body/family | Candidates |
|---|---|---:|
| JLJL72 | Two-door Sport family | 12 |
| JLJS72 | Two-door Rubicon family | 3 |
| JLJL74 | Unlimited Sport family | 18 |
| JLJP74 | Unlimited Sahara family, including approved High Altitude | 12 |
| JLJS74 | Unlimited Rubicon family | 4 |

All49 current Candidate2.1.0 artifacts, their semantic/file hashes, complete
powertrains, generation-evidence projections and actual retained-source bytes
were verified. Approved classifications, moderate-confidence EXJ limitations,
High Altitude naming and original evidence remain unchanged. The five native
model codes are positively present in the manufacturer-issued US MY2020 order
guides; all20 original guide PDFs used by generation selectors were inspected
by extraction. Source model/body/year lineage is consistent with existing JL
Generation PK32 / UUID38d3c3ac-f825-4406-abb5-c2d12b9129a4 and prior established
code mappings. The active canonical Jeep/Wrangler parents and target year range
were verified. No new correspondence finding was published on that basis alone.

The five MY2019 mappings PK9–13 / receipts2857–2861 were inspected and validated.
All target JL PK32, but start/end year are2019, and their source ID is
`reviewed_jeep_order_guide_inventory`, unlike the MY2020 per-revision source IDs.
**Zero existing mappings can be reused for these MY2020 candidate identities.**
There are no current US MY2020 applicable mappings or conflicting/duplicate
applicable publications. All49 current resolver calls correctly fail with
`Missing reviewed generation correspondence.`

## Why publication cannot provide complete coverage

This is an evidence-packaging mismatch, not a powertrain or marketed-trim dispute.

The candidates preserve **51 distinct source/model selector keys** across dated
guide source IDs, although there are only five manufacturer model codes. A key
is `(source_id, source_namespace, identity_type, native_identifier)`. The accepted
resolver requires every candidate generation key to have a reviewed mapping.
It also requires each applicable mapping's complete evidence documents to appear
**exactly** in the candidate's retained `evidence_documents`.

For every one of those51 groups, the candidates use candidate-specific assertion
set IDs and local assertion IDs. No valid selector document is common to all
candidates sharing the group key. A selector for one candidate therefore cannot
be used in a correspondence resolving all other candidates sharing that same key.

Concrete example, retained in `counterexample.json`:

- JL20-01 andJL20-02 both require source `MY2020-JL-2D-2019-08-15`, namespace
  `source_model_code`, type `model_code`, native identifier `JLJL72`.
- Both correctly retain the same authentic manufacturer PDF hash.
- Their assertion sets are respectively
  `JL20-01-MY2020-JL-2D-2019-08-15` and
  `JL20-02-MY2020-JL-2D-2019-08-15`, with similarly distinct assertion IDs.
- The first candidate's selector document is absent from the second candidate.
  The resolver would reject it with
  `Correspondence source revision does not match candidate evidence.`

The implementation requires `all(doc in documents for doc in row.evidence)` for
every applicable correspondence. Byte-identical PDFs do not make two differently
qualified assertion documents equal. Publishing parallel per-candidate mappings
for the same key does not solve this: all matching revisions would apply to each
candidate. Restrictions are checked as hard requirements, not used to silently
select a candidate-specific mapping. Omitting the evidence or ignoring unmatched
generation keys would weaken accepted validation and is not permitted.

Thus zero of the51 required key groups can currently receive one mapping with
complete group coverage. The full49-coverage condition fails before publication.
No partial set was published and no no-op/rejection audit receipts were generated.
The earlier classification-completeness reports did not test shared-selector
compatibility; their successful powertrain validation did not establish this
separate generation-resolution property.

## Smallest viable next task

Separately authorize versioned evidence-packaging revisions that add a shared,
immutable selector document for each required existing source/model key to every
candidate using that key. The original per-candidate evidence can be retained;
the shared selector must use the same existing source/model key so it does not
leave original required keys uncovered. Preserve approved classifications,
confidence, limitations, naming and original artifacts. For human-adjudicated
candidates, use the existing supported approved-projection workflow and retained
revision lineage; do not directly mutate an already-bound approved candidate.
Six EC3 candidates likewise need separately versioned evidence-enriched artifacts.

This is an artifact preparation repair using the existing contracts, not a
request for a new architecture milestone or application change. Do not collapse
source namespaces, drop generation assertions, or change accepted resolver rules
merely to obtain five publications. Under the present retained identities,51
source/model keys require coverage; the five-code count alone is not a valid
publication plan. Reassess minimal publication count and all49 exact-document
coverage after authorized preparation, then perform the conditional backup and
publication workflow only when all gates pass.

No repair was performed because this task explicitly prohibits modifying
candidate evidence. No new import plan, Matrix certification, canonical import,
VehicleDefinition, migration, backfill, application/contract change, commit or
push occurred.

## Verification and records

- `coverage_assessment.json`: all49 current candidate paths/hashes, required keys,
  current resolver failure and intended target.
- `identity_key_assessment.json`: all51 groups and empty shared-selector results.
- `existing_MY2019_correspondences.json`: exact five reviewed records, receipt
  PKs, hashes, year applicability and non-reuse reasons.
- `counterexample.json`: two real approved candidate identities demonstrating
  incompatible document qualification despite identical raw PDF bytes.
- `verification_results.json`: read-only database counts/checks.
- `preservation.json`: original artifact hashes and unchanged liveDB hash.
- `focused_test_results.txt`:57 isolated tests passed; Django system checks clean.

SQLite integrity is `ok`; foreign-key violations are zero. Django system checks
passed using a read-only SQLite URI plus `query_only=ON`. Counts remain812
VehicleDefinitions,2880 import receipts and13 correspondence revisions.
The liveDB SHA256 remains
`f0d32327e0d688b56711a572375e4e462a266ebb8fdb250b97965e392dff07ab`.
All preexisting MY2020 artifacts remain byte-identical. No publication was
attempted, and no backup or canonical data was modified.
