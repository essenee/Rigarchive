# MY2019 JL minimum evidence acquisition and retention

Created: 2026-11-07
Status: Draft

## Finding

**All 18 original PDFs are not required.** The director accepts the historical inventory and manufacturer credibility. That acceptance supersedes the handoff's research-repeat instructions. No additional authenticity review or full dated-revision comparison is required for this task. The earlier blocked report's demand for 18 PDF binaries was too broad.

Nineteen genuine **preparatory** Candidate 2.1.0 documents and SourceAssertionSet 1.1.0 documents are now under `preparatory_candidates/`. They validate but have intentionally incomplete structured facts and are not import-eligible. `validation_results.json` records every row's actual outcomes. No executable Matrix 2.1 or approval was manufactured.

## Three distinct questions

- **Authenticity:** the published Jeep guides are accepted manufacturer evidence. A PDF hash is not an authenticity certificate and is not needed to repeat that decision.
- **Evidence sufficiency:** the 19-offering historical inventory is accepted. An offering label and engine code still do not establish every structured engine classification or a missing drivetrain assertion. The handoff's provisional classification columns are preserved in retained research but are not automatically normalized as proven facts.
- **Artifact integrity:** SHA-256 binds the exact retained bytes and downstream lineage. A retained research JSON/text representation can be honestly hashed without pretending it is an original PDF. A URL string alone does not retain the source claims.

## Actual requirements inspected

Paths below are repository-relative and identify existing accepted implementation, unchanged by this task.

| Requirement | Actual enforcement | Requires original PDF bytes? |
|---|---|---|
| SourceAssertionSet extraction provenance, when present | `validation.py:validate_extraction_provenance` requires a real-format SHA-256, nonempty raw reference, extractor ID/version and supported mode. Bare SourceAssertionSet permits absent extraction provenance. | No |
| Candidate 2.x retained lineage | `normalization/generation.py:generation_evidence_from_sets` requires extraction provenance and a source-local set identity. `validation.py:validate_candidate_configuration` binds hash inventory, generation projection and qualified interpretation lineage. | No; requires a retained representation |
| Source snapshot | `acquisition/snapshots.py:RawSnapshotManager.store_snapshot` hashes actual `raw_bytes`, stores content-addressed bytes and metadata. It supports JSON/HTML/XML/PDF, with a generic extension for other content. `local_file` is supported. | No |
| Document checks | `generation_correspondence.py:validate_documents` checks document metadata, qualified assertions and hash format. With `verify_bytes=True`, the referenced repository file must exist and match its SHA-256. | No; the file can be truthful JSON/text |
| Structured powertrain | `importing/powertrain_identity.py:candidate_powertrain` verifies exact projection and qualified raw claim support. `complete=False` permits unknowns in preparation; `complete=True` prohibits them. `identity_proof` requires completeness and retained bytes. | No; requires explicit applicable facts |
| Matrix 2.1 | `matrix.py:validate_matrix` requires all five nonnull controlled fields, candidate/evidence digests, exact target identity and resolution 1.1 binding. Review workflow separately re-plans actual candidates. | No separate PDF rule; downstream evidence must remain valid |
| Explicit model codes | `generation_correspondence.py:_resolve_generation` requires reviewed correspondence for every supplied explicit identity, exact evidence revision matching and consistent canonical target. Failed explicit resolution never falls back to year-only. | No; retained model-code evidence must be reviewed |

`docs/development/INGESTION_PROTOCOL.md` sections on generation correspondence and RA-044 retain these evidence and completeness boundaries. Its J.D. Power structured-inventory rule is source-specific; it was not generalized as a new architectural rule for Jeep. Here the director's explicit acceptance covers the Jeep research inventory, and the generic contracts support its honest retained representation. No source-specific 2018 PDF parser was relabeled as a 2019 extractor.

## Retention performed

Used the existing `RawSnapshotManager` with `content_type=application/json`, `acquisition_method=local_file` and a separate source ID `reviewed_jeep_order_guide_inventory`. The snapshot contains the supplied inventory/citation rows, handoff text and the exact director acceptance sentence, with explicit limits. Its publisher/source locator points to the local handoff, while assertion contexts retain the actual guide/index URLs and reported pages. It does not claim a live HTTP acquisition, original PDF, new guide quotation or verified printed revision date.

`preparatory_candidates/snapshot_reference.json` identifies the actual managed file and hash. The hash covers this assembled research representation, not any upstream guide. New local assertion IDs are assigned as part of construction, not asserted to be manufacturer-issued identifiers. The script retains all model codes and does not discard them to evade correspondence safeguards.

The normalized ERC facts are 3.6 liters and six cylinders. Aspiration, fuel and electrification remain null: ESS does not prove `none`. EC3 retains 2.0 liters, four cylinders, explicit turbo and eTorque terminology; the existing Jeep mapping supports turbocharged/MHEV, while fuel remains null. The accepted research inventory supplies these offered engines; no classification is inferred from code spelling. The raw CSV's other proposed classifications are not silently promoted.

## Minimum additional input

No bulk PDF download is necessary. A small retained, source-linked text or structured excerpt is sufficient if it explicitly establishes:

1. For **ERC**, naturally aspirated, gasoline and conventional/nonhybrid classification, applicable to the offered MY2019 US configurations. An ESS label alone does not satisfy the existing `none` claim validator.
2. For **EC3**, gasoline classification, applicable to the offered MY2019 US configurations. The accepted offering label already carries turbo/eTorque.
3. Explicit **drive classification** applicable to the proposed configurations. The retained inventory has no `generic_drive_classification` claim; no 4WD value was inferred from a model code or platform assumption.

Each excerpt should include document title/revision, retrievable URL, page/section and engine/body/year/market applicability. One shared technical source may cover both engine tuples and drive applicability; no per-row duplicate source is required. Source text must actually support the classifications; adding token words solely to pass a validator would not be legitimate. If source terminology cannot be represented by the accepted raw-claim validator, report that exact gap for direction rather than changing the parser here.

These missing facts can come from the existing research extracts if available. Supplying original PDF pages is an alternative, not a mandatory format. The full historical union need not be researched again.

**Separate operational gate:** once evidence is complete, prepare and separately authorize the reviewed generation-correspondence publication covering this retained model-code evidence. Actual read-only resolver result for all rows: `Missing reviewed generation correspondence.` Existing MY2018 correspondence cannot be silently reused for a new source revision. Publication would write the development database and was not performed or implicitly authorized here.

## Smaller guide selection

The accepted inventory already establishes the 19 historical combinations. June four-door research has page references for all 13 four-door rows (pages 2, 5 and 9). The six two-door rows retain the supplied archive index and reported pages; no new exact edition/page verification is claimed. Therefore an October/April/June six-guide set is not required to repeat the union. Two June guides or selected excerpts could provide sufficient offering representation if needed; the current task does not establish that those guides explicitly contain every missing classification. October or April is needed only if a specific missing fact requires it. No exact minimum PDF count can be certified without inspecting their missing-fact content; the minimum **required original PDF count is zero** when sufficient honest retained extracts are available.

## Actual validation and boundaries

- 19 SourceAssertionSets passed validation.
- 19 Candidate 2.1.0 documents passed validation, exact serialization round trips and `candidate_powertrain(..., verify_bytes=True)`.
- Completeness checking rejected each candidate as expected; unknowns were not defaulted.
- Read-only planner returns missing `generic_drive_classification`; independent read-only explicit generation resolution returns missing reviewed correspondence. Engine proof 2.0 is not certified before those gates and complete tuples are satisfied. Matrix 2.1 cannot truthfully authorize incomplete rows.
- Three existing focused RA-044 tests passed: complete source/round-trip handling, missing evidence without defaults, and ESS rejection/eTorque support.
- `manage.py check`: zero issues. `makemigrations --check --dry-run`: no changes detected. Both use an isolated in-memory default database.
- Environment: Homebrew Python 3.13.2 plus existing `venv/lib/python3.13/site-packages` (Django 6.1.3), explicitly permitted by this request. No software/environment installation or rebuild.
- First script invocation failed to import project settings because the script directory displaced the repository on Python's search path; rerun with the repository and existing package directory on `PYTHONPATH` succeeded. No source-contract failure was bypassed.
- Live Django queries used SQLite URI `mode=ro`. The database SHA-256 before and after construction is recorded unchanged in `validation_results.json`.

`construct_preparatory_candidates.py` is a task-local reproducibility script, not a new ingestion API. Run from the repository root with `PYTHONDONTWRITEBYTECODE=1`, `PYTHONPATH` containing that root and the existing Python 3.13 package directory, and `/opt/homebrew/bin/python3.13`. It refuses to overwrite a completed result set.

Only review artifacts and documentation changed. No application contract, model, migration, historical artifact or canonical identity changed. No backfill, publication, approval, canonical execution, staging, commit or push occurred. All pre-existing work is preserved. Full completion remains pending the narrow missing facts and separate correspondence review/publication, not acquisition of all 18 PDFs.
