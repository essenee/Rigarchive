# MY2019 Wrangler JL — evidence checkpoint (2026-11-07)

These files are **review scaffolding**, not source-certified ingestion artifacts. No canonical imports are authorized.

- `MY2019_JL_candidate_inventory_PROVISIONAL.csv`: 19 rows based on prior discussion, with proposed five-field classifications. The values are **not yet bound to page-level evidence** and must not be imported as Candidate 2.1.0.
- `MY2019_JL_revision_evidence_ledger_TEMPLATE.csv`: 18 placeholder document slots (two body styles × nine approximate revision periods). Actual dates and number of revisions **must be verified**; blank URL/hash/page means no source was examined for that row.

Manufacturer-guide archive entry points previously identified:

- 2-door: https://www.jlwranglerforums.com/forum/threads/2019-jeep-wrangler-2-door-jl-order-guide-and-pricing-u-s.15025/
- 4-door: https://www.jlwranglerforums.com/forum/threads/2019-jeep-wrangler-4-door-jlu-order-guide-and-pricing-u-s.15026/

## Certification gates

1. Obtain and hash authentic PDFs for all actual dated revisions; capture exact document identity and page numbers.
2. Extract each offered model-code + quick-order-package + engine combination; differentiate a genuine ordering entry from a mere restriction mention.
3. Compute the dated-revision union and identify any additional or removed trim/engine combination.
4. Bind all five structured identity fields to applicable evidence. One document may prove multiple fields.
5. Resolve existing-peer proof and versioned Candidate 2.1.0, Manifest 2.1, Matrix 2.1 with transaction-time revalidation.
6. Obtain separate human authorization before import.

**Important:** The two model-code families used for Sport/Altitude and Sahara/Altitude are context-dependent. Quick-order package suffixes alone are not globally unique.
