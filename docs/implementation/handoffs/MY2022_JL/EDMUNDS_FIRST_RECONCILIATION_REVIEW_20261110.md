# MY2022 Wrangler JL — W2 Edmunds-first reconciliation review

Created: 2026-11-10  
Status: Preliminary read-only review; **no candidate revisions or approvals**

## Scope and actual evidence

This review reads the retained 56-row `edmunds_comparison_20261109/row_comparison.csv` and the existing 55-candidate checkpoint; it **does not** independently retrieve live Edmunds pages, validate current selector behavior, or upgrade the research transcriptions to archived original Edmunds HTML. The 56-row comparison includes the deferred RHD row `JL22-53 / JLUL74 / 22A`; the candidate checkpoint excludes it. All 56 rows have an offering counterpart, but offering agreement is not five-field classification proof. No eligibility is inferred from W2 source acceptance.

## Evidence inventory

| Engine code | Compared offerings | Existing consumer candidates | Working interpretation |
| --- | ---: | ---: | --- |
| `EC1` | 15 | 14 | Retain source-specific identity and powertrain evidence; no cross-code equivalence inferred |
| `ERC` | 13 | 13 | Retain source-specific identity and powertrain evidence; no cross-code equivalence inferred |
| `ERG` | 15 | 15 | Retain source-specific identity and powertrain evidence; no cross-code equivalence inferred |
| `EXJ` | 9 | 9 | Retain source-specific identity and powertrain evidence; no cross-code equivalence inferred |
| `ECX` | 3 | 3 | Retain source-specific identity and powertrain evidence; no cross-code equivalence inferred |
| `ESG` | 1 | 1 | Retain source-specific identity and powertrain evidence; no cross-code equivalence inferred |

The existing comparison marks **53/56** rows as insufficient for explicit complete five-field corroboration and **3/56** ECX rows as having explicit family-level gas/electric turbo PHEV descriptions but with the mapping not applied. These flags describe the earlier strict-evidence assessment, **not** a new W2 decision that values may be invented or that an Engine Proof is now supported. The existing candidate checkpoint reports 112 unresolved field instances (29 aspiration, 46 fuel, 37 electrification), 13 ERC/eTorque peer pairs, 72 missing correspondence keys and zero Engine Proofs. Counts must be remeasured after any authorized revision.

## Eight existing Edmunds transmission/QOP observation gaps

The comparison recorded the following manufacturer-observed QOPs not observed in Edmunds for the corresponding offering. Under W2, **do not delete the manufacturer observation or fabricate an Edmunds match**. Carry them as review items, with targeted checking only if the discrepancy affects a proposed identity or import eligibility.

| Discovery row | QOP not observed in Edmunds |
| --- | --- |
| `JL22-02` | `24B` |
| `JL22-05` | `24S` |
| `JL22-08` | `24W` |
| `JL22-11` | `24K` |
| `JL22-17` | `24L` |
| `JL22-30` | `24W` |
| `JL22-38` | `24L` |
| `JL22-45` | `24G` |

## Recommended next implementation checkpoint (not performed)

1. Map the existing 55 candidate IDs to their retained Edmunds comparison rows and assertion sets; verify which fields have an **explicit** Edmunds-supported statement versus a derived classification requiring owner adjudication. Preserve the exact source/transcription status.
2. Review the five-field classification groups, especially fuel and electrification for ESS/eTorque, and the 13 ERC/eTorque peer pairs. Do not infer fuel/electrification from engine code alone; record an attributable, reviewable inference if source language supports one.
3. For the eight gaps above, retain manufacturer QOP observations separately from Edmunds-backed links. Do not manufacture a QOP/engine/transmission relationship from co-listed options.
4. Assess the existing Candidate 2.1.0 and Engine Proof 2.0 validators against **actual proposed Edmunds-backed values**. Report exact blocker/predicate/contract, rather than weakening eligibility implicitly.
5. Resolve the 72 source/model generation-correspondence keys through the existing review/publication workflow, subject to separate approval. This is not an Edmunds taxonomy field.
6. Rebuild candidate revisions deterministically only after the applicable source/classification and human authorization boundaries are established. No Matrix certification, import, database writes or Git publication are authorized by this review.

See [W2 decision and historical experiment](WORKFLOW_EXPERIMENT_20261109.md), [Edmunds comparison](edmunds_comparison_20261109/README.md), [candidate checkpoint](lightweight_candidates_20261109/README.md), and [coverage register](../../CANONICAL_COVERAGE_AND_DEFERRALS.md).
