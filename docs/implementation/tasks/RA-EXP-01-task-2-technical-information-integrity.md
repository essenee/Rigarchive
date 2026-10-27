# RA-EXP-01 Task 2 — Technical Information Integrity

## Objective and authority

Correct misleading technical-information presentation using existing models and applicability rules (ADR-0009 / RA-042), preserving the approved Task 1 layout/configurator and canonical import semantics. Distinguish canonical reference attributes, reported measurements, source identifiers, execution records and unknown applicability. No schema, data, route, verification workflow or illustration-generation changes are authorized. RA-EXP-01 remains WIP pending final evaluation.

## Inspection findings

- Generation Key Dimensions SVG text hardcoded 109.8 in (wheelbase), 189.6 in (overall length), 72.2 in (side height), 66.0 in (rear width/track illustration), 42.5 in (rear height), 46.0 in (cargo-opening width) and 30.5 in (cargo-opening height). No service/model/evidence binding supported those labels. Cargo-opening width was also labeled between wheel wells, conflating different concepts. SVG coordinate numbers are drawing instructions, not dimensional observations.
- `MeasurementResult` stores a Generation, definition, value, unit, notes and active flag, plus inherited identifiers/timestamps. It has no verification/review status, source type or structured source/evidence relationship. Notes can preserve textual context; their presence does not establish verification.
- Conditions are controlled feature/state pairs. Zero conditions means Generation-wide; multiple conditions are conjunctive (AND). The canonical configuration has no mapping establishing these physical states. A year or trim cannot establish them.
- Multiple independent results are deliberately permitted. Selecting a single authoritative value, reconciling conflicts or averaging would exceed existing architecture.
- `ImportExecutionReceipt` records source identifiers, raw/manifest/adjudication hashes and execution metadata/outcome. It is an execution/provenance record, not independent verification of every specification. The old page labels Audited & Verified, Source Authority and durable verification receipt overstated that meaning.

## Corrections

- Removed all numeric dimension text from Generation diagrams and the conflated wheel-well label. Retained generic outlines/location lines, explicitly labeled illustrative, not to scale, and not generation-specific geometry. Recorded results are shown separately; no numerical values are substituted or inferred from drawings. Topic labels do not imply recorded coverage.
- Replaced automatic verified/manual/ongoing-field-collection wording with recorded/report terminology and accurate empty states. No verified/unverified status was invented. UI text explains the absence of model-level independent verification/structured evidence metadata.
- Shared applicability presentation now lists every condition with AND semantics on Generation, configuration and dedicated measurement pages. It explicitly states that configuration applicability is not established. This is not a finding that a conditional result is inapplicable.
- Specification service retains Generation-wide results separately and additionally exposes conditional reports. Conditional-only coverage is not presented as no measurement records. No feature state is inferred from sales taxonomy.
- Preserved all independent active results, original values/units/notes and UUIDs. Separate rows/cards preserve even equal-valued duplicates; UUIDs remain internal and are not displayed after final presentation cleanup. Stable ordering adds a primary-key tie-breaker, without choosing or aggregating results.
- Receipt UI preserves recorded source IDs, native identifiers, hashes, creation basis and execution outcomes, with neutral wording. Missing receipt/basis is described as unavailable/not recorded. One receipt is explicitly not a full lifecycle history. No citations, review events, evidence documents or verification decisions are fabricated.
- The configurator is unchanged. Applicability caveats are valid in all filter states, avoiding a claim that selection establishes features or requiring updates outside the approved configurator content replacement.

## Architectural limits and deferred work

- Existing measurement records cannot distinguish empirical reports from manufacturer assertions through structured provenance fields, or establish independent verification. New source/evidence relationships and review capabilities require separate design approval.
- Exact feature applicability cannot be evaluated without an approved configuration/feature-state mapping. Missing information is not evidence that conditions are satisfied.
- Evidence-backed generation-specific illustrations, measurement protocols, source reconciliation, canonical result selection and conflict resolution remain deferred. No new illustration infrastructure or measurement data was created.
- Scope is Generation/configuration/dedicated measurement presentation. The homepage's separate decorative schematic remains outside this repair; this task does not claim that all sitewide technical imagery is evidence-backed.
- Real-browser and assistive-technology rendering were not verified locally.

## Completion record

- Status: Task 2 implemented and checks passing; overall RA-EXP-01 remains WIP.
- Completion date: 2026-10-26.
- Files: `reference/services.py`; Generation, Vehicle Definition and dedicated measurements templates; new `templates/measurements/includes/applicability.html` and `result_card.html`; `static/css/site.css`; new `reference/tests/test_technical_information_integrity.py`; the empty-state assertion in `reference/tests/test_views.py`; `CURRENT_STATE.md`, `CHANGELOG.md`, RA-EXP-01 design document and this record.
- Models/migrations/import behavior: unchanged. No migration generated or applied. No new dependencies, routes or RA-EXP-02 navigation.
- Isolated verification environment: existing Python 3.14 with `PYTHONDONTWRITEBYTECODE=1`, `PYTHONPATH=.venv/lib/python3.14/site-packages`, `RIGARCHIVE_TEST_DB_PATH=:memory:`. No application requests against the development database.
- `python3 -B manage.py check`: passed.
- `python3 -B manage.py makemigrations --check --dry-run`: no changes detected.
- Focused integrity, experimental hub, reference view and measurements tests: **90 passed** (including 11 new integrity tests).
- `python3 -B manage.py test --noinput`: **318 passed, 0 failed**.
- `node --test reference/tests/js/generation_configurator.test.cjs`: **11 passed**, unchanged configurator behavior suite.
- `git diff --check`: passed.
- No staging, commits, pushes, database writes or canonical-data changes intentionally performed. Fingerprint preservation outcome is recorded after final inspection.
- Final preservation inspection: Git index and unrelated source/probe fingerprints match the initial snapshot. The development database fingerprint changed during the turn despite isolated verification and no intentionally issued development-database writes. The cause was not established; no restoration, reset or tracking change was attempted. Byte-for-byte database preservation across this task cannot be confirmed.


## Final presentation cleanup

- Status: Implemented with passing checks; overall RA-EXP-01 remains WIP pending final evaluation.
- Renamed Recorded Measurements from Archive to **Additional Measurements**. Replaced the long illustrative-diagram paragraph with “Illustrative · not to scale.” Generic accessible labels remain; hardcoded numerical dimensions remain absent.
- Removed the verbose independent-result subtitles and visible MeasurementResult UUIDs from Generation, specification-card and dedicated measurement presentation. UUIDs remain unchanged in models/internal processing. Independent records remain separate rows/cards; values, units, notes and feature conditions remain displayed, with no aggregation or definitive-result selection.
- The director identifies the two existing fourth-generation 4Runner measurements as manufacturer-published technical measurements derived from a Toyota mechanical publication. Existing values and source notes are retained without reading/writing or reclassifying development records, inventing citations/source metadata, or implying independent verification. These supplemental technical measurements remain accessible through the existing pages.
- **Deferred evidence architecture requirement:** Future physical measurements may be supported by photographs, including tape-measure images showing the measured location and value. Manufacturer technical publications provide a different form of evidence. The eventual architecture must preserve that distinction and supporting context; current structured measurement provenance cannot express it. No photographic support, source classifications, evidence relationships, schemas or verification capabilities are implemented or authorized here.
- Unchanged: Generation section order, configurator placement/labels, selection, scroll behavior, JavaScript/GET fallback, canonical identity/links, applicability semantics and import receipt corrections. No new routes, migrations or RA-EXP-02 navigation.
- Files modified: Generation, Vehicle Definition, dedicated measurements and result-card templates; `static/css/site.css` (removed unused identifier styling); `reference/tests/test_technical_information_integrity.py`; current-state/changelog/design documentation and this record.
- Verification: **91 focused Django tests**, **319 full-suite Django tests**, and **11 unchanged JavaScript behavior tests** passed using isolated resources. System check, migration-consistency dry-run and whitespace checks passed. Initial Task 2 results above remain historical. Tests assert compact titles, absent long subtitles/visible UUIDs, preserved publication notes/values/units and model UUIDs, separate duplicate entries, conditions, and no automatic verification claim.
- Limitations: No real-browser or screen-reader execution locally. Structured source distinctions, photographic evidence and independent verification remain deferred. No packages, application logic or data were changed in this cleanup; no staging, commit or push performed.
- Final presentation preservation check: Development database, Git index and all unrelated source/probe fingerprints match the starting snapshot. The pre-existing database modification was preserved. No staging, commits, pushes, restoration or tracking changes occurred.
