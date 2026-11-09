# MY2020 JL shared-selector evidence packaging repair

Created: 2026-11-08
Status: Accepted

The owner-authorized artifact-only repair is complete: **49 separate candidate
revisions**, **51 shared selector SourceAssertionSets**, and **43 evidence-only
revisions of existing approved classification declarations**. All60 approved
field decisions, their exact claim blocks, original approval attribution/time,
confidence, applicability, limitations and base-candidate bindings are preserved.
No new classification decision was made. All original artifacts remain unchanged.

Use this directory's `candidate_index.json` as the current49-candidate selection.
It identifies the new candidate/approved-declaration hashes and paths, superseded
artifacts, selector references and packaging authorization. The three approved
Unlimited High Altitude identities retain their Sahara-family provenance.

## Root cause and minimum repair

The old candidates shared source/model-code keys but used different candidate-local
assertion-set IDs. The resolver matches by source/namespace/type/native model code,
then requires each applicable mapping's evidence documents to occur exactly in the
candidate. Equal original PDF bytes did not make different qualified documents equal.

There are five manufacturer model codes but51 existing source/model keys because
source IDs distinguish retained guide revisions. The accepted contract requires
coverage of all these keys, not just one document or code per candidate. Nothing
was collapsed, removed, renamed or silently ignored to obtain fewer mappings.

The repair adds one shared selector per existing key to every candidate requiring
that key. Each selector preserves the original manufacturer source ID, exact
retained original PDF path/hash, source URL, US MY2020 applicability and model-code
page. Its only factual assertion is the same explicit manufacturer model-code
heading. No canonical generation target, engine availability or trim availability
is represented as manufacturer wording. The canonical target is a separate
unpublished review finding. Original candidate-specific trim, engine, body,
configuration and generation-selector assertions remain intact.

All51 selectors reuse20 authentic retained manufacturer PDFs. Their shared
assertion-set identifiers consistently bind source revision and native model code.
`selector_index.json` records original source hashes, source pages, shared
SourceAssertionSet paths/hashes and exact affected candidate references. Repeated
FCA publications are lineage support, not independent manufacturer corroboration.

## Approved-classification provenance

Directly appending evidence to a human-approved candidate would violate the exact
approved-projection guard. The existing Adjudication1.1 contract instead supports
nonhuman `supporting_documents`, and its existing projector incorporates them and
reprojects all generation identities.

For each of43 candidates, a separate approved-declaration evidence revision:

- retains the exact original approved `classifications` block, decision, reviewer,
  original approval timestamp, source identity and base-candidate path/hash;
- retains every prior supporting document and adds only relevant shared selectors;
- records the predecessor declaration path, raw-file hash, semantic hash and the
  current owner's evidence-packaging authorization in revision notes;
- is validated by the approved-only gate and projected through the unchanged
  `apply_classification_adjudication` workflow to create a new candidate artifact.

This carries forward existing approval; it does not impersonate a new human fact
review or extend approval to new configurations. The original declarations are
retained permanently. Exactly one current human declaration is projected per
candidate; old declarations remain referenced by revision lineage rather than
being inserted as a second competing current declaration. The projector retains
its original approval timestamp; packaging processing time is separately recorded
in `authorization.json`. No chained-human-approval or exact-projection check was
weakened. The six EC3 candidates have ordinary additive evidence-only revisions.

All source-based normalized assertions, technical details, identities and complete
five-field powertrain values are unchanged. EXJ retains moderate confidence and
its original derived-evidence limitations. `classification_provenance_carryforward.json`
records the43 predecessor/current declaration pairs and60 preserved decisions.

## Correspondence verification

| Manufacturer model code | Candidates resolving to existing JL PK32 in simulation |
|---|---:|
| JLJL72 | 12 |
| JLJS72 | 3 |
| JLJL74 | 18 |
| JLJP74 | 12 |
| JLJS74 | 4 |
| Total | 49 |

There are51 unique unpublished correspondence proposals, one per existing
source/model key. Each uses the exact common selector present in every candidate
matching its key, US MY2020 applicability and existing JL Generation PK32 / UUID
38d3c3ac-f825-4406-abb5-c2d12b9129a4. The active Jeep/Wrangler parents, target year
range, review contract, document hashes and unsaved model validation pass.
Manufacturer model-code/US-year/body headings and prior established code-to-JL
lineage support the review finding; naming resemblance alone is not the basis.
No existing applicable MY2020 correspondence, conflicting target or duplicate key
was found. Under unchanged identities51 is the minimum number of distinct keys
that must receive coverage; this is not51 generations or51 vehicle candidates.

`correspondence_proposals/` contains review artifacts, not import manifests or
executable canonical import plans. They are **unpublished** and convey no
publication authorization. `correspondence_proposal_index.json` pins all review
hashes, revision UUIDs, keys, intended target and coverage.

To verify unpublished coverage without writing the live DB, the accepted resolver
was called unchanged, supplying filtered unsaved proposed revision objects only
at `_applicable_revisions`, its DB lookup boundary. The resolver's actual
projection-completeness, all-key coverage, content hash, restriction, exact document
inclusion, active parent and target checks all executed. No guard or resolver was
stubbed to return success. The real parent objects were read through SQLite
`mode=ro` and `query_only=ON`.

All49 resolver calls produced `reviewed_source_correspondence` to PK32 with the
expected proposal UUID/hash set. The original unrepaired candidate still fails
exact-document inclusion against these same proposals. Removing a required mapping
still raises missing reviewed correspondence without a year-only fallback.
`coverage_verification.json` retains all49 row results and the simulation boundary.
Actual database-backed resolution remains unpublished pending separate publication
authorization; simulated coverage must not be described as published coverage.

## Validation and preservation

All49 revised candidates pass Candidate2.1.0, complete five-field powertrain,
source-byte, qualified lineage, generation-projection and serializer checks.
All51 SourceAssertionSets round-trip. All43 approved evidence revisions pass the
existing approved-only validation and preserve the exact previously approved
classification blocks. All49 final identity tuples remain unique.

**125 isolated focused tests passed**, including generation correspondence,
projection completeness, classification adjudication, structured powertrain,
serialization and candidate construction. Django system checks passed on a
read-only connection. SQLite integrity and foreign keys passed. Actual test
commands/output are summarized in `focused_test_results.txt`.

An initial artifact diagnostic referred to `technical_details` rather than the
actual `normalized_technical_details` dataclass field. It stopped after selector
creation and one evidence declaration; no original artifact or database changed.
The diagnostic was corrected and resumed using content-equality checks for partial
outputs. Partial artifacts were preserved and reused, never deleted or silently
overwritten. No application defect or application change was involved.

`preservation_baseline.json` pins every preexisting MY2020 file and the liveDB
hash. Database counts remain812 VehicleDefinitions,2880 receipts and13
correspondence revisions, byte-for-byte unchanged. Original candidates, approved
declarations, evidence, reports, migration state and canonical data are preserved.
No correspondence publication, Matrix certification, canonical import planning,
import, backfill, migration, application/contract change, commit or push occurred.

## Remaining boundary

The selector mismatch is resolved for all49 candidates. No evidence-packaging
blocker remains for review of the51 exact correspondence proposals. Publication
requires a separate owner authorization, fresh stale-evidence/duplicate/target
checks, consistent backup and accepted publication workflow. Thereafter verify
real database-backed resolution of all49 candidates. Matrix certification and
canonical import planning remain separate future tasks. Existing missing archive
and secondary-observation limitations remain documented and are unchanged by this
repair; no candidate relies exclusively on the missing two-door July2 revision.
