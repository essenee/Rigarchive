# RA-017 — Candidate Configuration Construction & Aggregation Implementation

## Purpose

Implement deterministic pure Python candidate configuration construction and aggregation, transforming caller-supplied `CandidateIdentity` workflow context, Tier 1 `SourceAssertionSet` artifacts, and Tier 2 `NormalizedInterpretation` objects into validated, transient, non-canonical `CandidateConfigurationDocument` artifacts in strict compliance with the approved [RA-016 Candidate Configuration Construction & Aggregation Architecture](file:///Users/esse/dev/Rigarchive/docs/architecture/designs/RA-016-Candidate-Configuration-Construction-Aggregation-Architecture.md).

## Governing Architecture

Governed by the approved [RA-016 Candidate Configuration Construction & Aggregation Architecture](file:///Users/esse/dev/Rigarchive/docs/architecture/designs/RA-016-Candidate-Configuration-Construction-Aggregation-Architecture.md) and operating over [RA-012 Intermediate Serialization Contracts](file:///Users/esse/dev/Rigarchive/docs/implementation/tasks/RA-012-intermediate-serialization-implementation.md), [RA-013 Public Source Acquisition Adapters](file:///Users/esse/dev/Rigarchive/docs/implementation/tasks/RA-013-public-source-acquisition-implementation.md), and [RA-015 Source Assertion Normalization Implementation](file:///Users/esse/dev/Rigarchive/docs/implementation/tasks/RA-015-source-assertion-normalization-implementation.md).

## Implementation Design & Module Placement

The Python candidate construction package is organized under `reference/ingestion/candidate/`:

```text
reference/ingestion/candidate/
├── __init__.py         # Package exports (construct_candidate_configuration, CandidateConstructionError)
└── builder.py          # Candidate construction engine & internal context verification
```

### Public API Signature

```python
class CandidateConstructionError(ValueError):
    """Raised when candidate construction input fails validation or structural routing."""
    pass

def construct_candidate_configuration(
    candidate_identity: CandidateIdentity,
    source_assertion_sets: List[SourceAssertionSet],
    normalized_assertions: List[NormalizedInterpretation],
    candidate_reference: Optional[str] = None,
    created_at: Optional[str] = None,
) -> CandidateConfigurationDocument:
```

Exported through `reference/ingestion/candidate/__init__.py` and re-exported in [`reference/ingestion/__init__.py`](file:///Users/esse/dev/Rigarchive/reference/ingestion/__init__.py).

## Candidate Context Boundary

* **CandidateIdentity is Context**: Caller-supplied `CandidateIdentity` defines the workflow/aggregation target (`Toyota 4Runner 2020 US`). It is NOT source evidence and does not count toward corroboration.
* **No Evidence Overwriting**: Source-derived normalized evidence (`make`, `model`, `model_year`) is preserved in `normalized_assertions` and evaluated internally against `CandidateIdentity` for context verification. Evidence never overwrites or mutates `CandidateIdentity`.
* **Internal Context Verification**: Internal context statuses (`supported`, `partially_supported`, `contradicted`, `unverified`) are calculated transiently. Contradiction triggers top-level human review (`requires_human_review = True`, `review_workflow_disposition = "pending_review"`) and records notes in `reconciliation_notes` without altering evidence reconciliation states or serializing new contract fields.

## Evidence Reconciliation Semantics

* `single_source`: Mapped evidence available from 1 source authority, or multiple records from the same source authority.
* `corroborated`: Compatible mapped evidence supported across 2+ currently mechanically established independent source authorities (`source_id` values).
* `conflicting`: Incompatible mapped evidence across 2+ currently mechanically established independent source authorities (`source_id` values). Leaves scalar projection unset (`None`) and requires human review.
* `ambiguous`: Unresolved applicability or ambiguous grade context.
* `incomplete`: Assigned ONLY when an expected/projectable concept is represented by evidence but cannot be projected (Case A unmapped or parsing failure). Optional absent fields do NOT receive `incomplete` entries.

## Record Identity vs. Evidence Independence

* `source_id + native_record_id` identifies and distinguishes source-native records for provenance and duplicate detection.
* Repeated retrieval of the same source-native record (`same source_id + same native_record_id`) yields `single_source`.
* Multiple different records from the same source (`same source_id + different native_record_id`) yield `single_source`. RA-017 does NOT treat different records from the same source as independently corroborating merely because `native_record_id` differs. Same-source multi-record independence remains architecturally deferred.
* Independent `source_id` values (e.g. `nhtsa_vpic` vs `epa_fueleconomy`) are the current mechanically established independence boundary for corroboration.

## Same-Source Value Variance

If multiple records from the same source authority provide incompatible values (e.g. EPA record 42101 asserts 6 cyl while EPA record 42102 asserts 4 cyl):
* Both interpretations remain preserved in `normalized_assertions`.
* Provenance references for both interpretations are retained in `attribute_provenance`.
* Cross-source `conflicting` state is NOT manufactured (`attribute_states` receives `single_source`).
* No winner selection occurs; affected scalar fields in `normalized_technical_details` are left unset (`None`).

## Projection vs. Preservation

1. **Category A: Mapped & Projected**: Concepts with explicit candidate document destinations (`generic_drive_classification`, `drivetrain_architecture`, `engine_displacement_liters`, `engine_cylinders`, `nhtsa_make_id`, `nhtsa_model_id`, `make`, `model`, `model_year`). Receive `attribute_provenance` and `attribute_states` entries.
2. **Category B: Mapped & Preserved**: `city_mpg_epa_rating` and `highway_mpg_epa_rating`. Preserved in `normalized_assertions` without populating `attribute_provenance` or manufacturing fake fields.
3. **Category C: Unmapped Case A Preserved**: Deferred concepts (`transmission_descriptor`, `vehicle_class`, `engine_description`, composite `model: "4Runner 4WD"`). Preserved in `normalized_assertions` with `mapping_status = "unmapped"`.

## Typed Technical Projections

* **Drivetrain Details**: `generic_classification` (`"4WD"`), `architecture` (`"part_time_4wd"`).
* **Engine Details**: `displacement` (`TechnicalValue(4.0, "L", "4.0")`), `cylinders` (`6`).
* **Transmission Details**: Currently unmapped in RA-015; left `None`.

Under true independent-source conflict, scalar fields remain unset (`None`), all evidence is preserved, attribute state becomes `conflicting`, and human review is flagged.

## Factory Technical Features Boundary

Candidate construction consumes only approved mapped `NormalizedInterpretation` objects. It never independently parses Tier 1 raw `SourceAssertion` strings (such as KDSS, A-TRAC, CRAWL Control, MTS, X-REAS) to infer feature semantics. Current RA-015 mappings yield `factory_technical_features = []`.

## Source Configuration Identities

Source-native identifiers (`nhtsa_make_id`, `nhtsa_model_id`, `epa_vehicle_id`) populate `source_configuration_identities`. They are source-scoped context descriptors and are not canonical matching or deduplication keys.

## Provenance Validation

* Builds a combined assertion lookup dictionary across all input `SourceAssertionSet` artifacts.
* Verifies every `NormalizedInterpretation.source_assertion_ref` resolves to a known `assertion_id`. Broken transitive references raise `CandidateConstructionError`.
* Constructed documents pass existing `validate_candidate_configuration(doc)` validation cleanly.

## Determinism & Timestamp Handling

* **Semantic Determinism**: Input list ordering (shuffled assertion sets or interpretations) produces identical candidate document outputs.
* **Sorting**: Applies explicit sorting to `normalized_assertions`, `factory_technical_features`, `source_configuration_identities`, and `attribute_provenance`.
* **Transient Reference**: `candidate_reference` is an opaque UUID string (`cand_ref_<hex>`) unless caller-specified.
* **Timestamp Handling**: Optional `created_at` parameter allows injecting deterministic timestamps for testing. Production calls default to live UTC ISO timestamp strings (`datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")`).

## Serialization Interoperability Correction

A pre-existing RA-012/RA-015 interoperability defect was exposed during RA-017 candidate round-trip serialization testing. RA-015 legitimately emits `TechnicalValue` inside `NormalizedInterpretation.normalized_concept` for engine displacement, while `serialization.py` omitted calling `technical_value_to_dict` / `technical_value_from_dict`.

The reviewed correction in [`reference/ingestion/serialization.py`](file:///Users/esse/dev/Rigarchive/reference/ingestion/serialization.py):
* Converts `TechnicalValue` to dict in `normalized_interpretation_to_dict`.
* Deserializes dict back to `TechnicalValue` in `normalized_interpretation_from_dict`.
* Introduces zero contract changes, preserves primitive scalar serialization, and adds no unbounded recursive behavior.

## Test Suite Summary

Created [`reference/tests/test_candidate_construction.py`](file:///Users/esse/dev/Rigarchive/reference/tests/test_candidate_construction.py) containing 13 focused test methods (80 total project tests passing):
1. `test_scenario_1_normal_controlled_aggregation`: Validates controlled 2020 Toyota 4Runner aggregation over real NHTSA + EPA fixtures.
2. `test_scenario_2_context_contradiction_single_lineage`: Validates context contradiction handling without false evidence conflict.
3. `test_scenario_3_true_evidence_conflict_plus_context_contradiction`: Validates true evidence conflict + context contradiction.
4. `test_repeated_acquisition_same_lineage_no_false_corroboration`: Validates repeated retrieval of same record yields `single_source`.
5. `test_same_source_different_records_same_value_not_corroborated`: Validates different records from same source yield `single_source`.
6. `test_same_source_different_records_different_values_not_conflicting`: Validates same-source value variance yields `single_source`.
7. `test_no_automatic_incomplete_for_absent_optional_attributes`: Validates absent optional fields receive no fabricated state.
8. `test_preserved_but_not_projected_concepts`: Validates Category B concepts remain in assertions without fake provenance.
9. `test_prohibit_tier_1_normalization_bypass`: Validates raw Tier 1 strings are not parsed bypass-style.
10. `test_evidentiary_contradiction_preservation_not_exception`: Validates manufacturer context disagreement is preserved as evidence.
11. `test_broken_transitive_provenance_raises_error`: Validates broken `source_assertion_ref` raises `CandidateConstructionError`.
12. `test_input_ordering_determinism`: Validates array shuffling yields byte-identical candidate structures.
13. `test_candidate_serialization_round_trip`: Validates JSON round-trip serialization and deserialization.

## Scope Restrictions (Explicit Non-Goals)

* Zero canonical entity matching or import (Manufacturer, VehicleModel, Generation, VehicleDefinition).
* Zero source precedence rules or winner selection logic.
* Zero human adjudication UI or review queues.
* Zero persistent ORM staging models or Django migrations created.
* Zero database mutations.
* Zero live network test dependencies.

CandidateConfigurationDocument remains the strict STOP boundary.

## Completion Record

Status: Completed / Verified

Completion date: 2026-08-15

Files created:
- `reference/ingestion/candidate/__init__.py`
- `reference/ingestion/candidate/builder.py`
- `reference/tests/test_candidate_construction.py`
- `docs/implementation/tasks/RA-017-candidate-configuration-construction-aggregation-implementation.md`

Files modified:
- `reference/ingestion/__init__.py`
- `reference/ingestion/serialization.py`
- `docs/implementation/CURRENT_STATE.md`
- `CHANGELOG.md`

Migrations created:
- None (0 ORM changes).

Verification results:
- `.venv/bin/python manage.py check`: Passed (`System check identified no issues (0 silenced)`).
- `.venv/bin/python manage.py makemigrations --check`: Passed (`No changes detected`).
- `.venv/bin/python manage.py test`: Passed (`Ran 80 tests in 3.405s — OK`).
- `git diff --check`: Passed cleanly with exit code 0.
- `git status --short`: Verified clean state across all modified and newly created files.
