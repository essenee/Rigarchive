# Python 3.13 and Experimental Vehicles Documentation Finalization

Date: 2026-10-27.
Branch: `experiment/vehicle-hub-ui`.
Status: Documentation reconciled; no application or deployment implementation performed.

## Changes

- Reconciled CURRENT_STATE's date, current Python 3.13 environment, latest recorded 350 Django/17 JavaScript results, and installed measurements application. Earlier Python 3.14 commands and 339/340/346-test results remain historical checkpoints; no tests were rerun.
- Distinguished the implemented photographic selector, compact thumbnails and Vehicles disclosure from the deferred five-category contextual shell, model category destinations and optional selector dialog.
- Added dated RA-EXP-02A/B-1 implementation-status clarifications without changing original architectural decisions or approval requirements. Corrected historical RA-EXP-01 uncommitted-work wording with dated Git-history references: Task 1 `54ada80`, Task 2 `1764499`, provisional Homepage `5859745`.
- Corrected the Homepage blueprint filename to `static/images/homepage/Toyota 4Runner Technical Blueprint.png`, explicitly identifying the earlier erroneous “Views” wording. No asset/template was changed.
- Distinguished historical four-query selector measurements from the current six-query rendered-page total (four selector/discovery plus two header queries).
- Preserved the unresolved historical B-1 database/IDE fingerprint discrepancy. Later task-local matching hashes do not resolve it. Browser desktop/mobile, keyboard/focus, zoom/reflow and screen-reader acceptance remain pending under managed Browser Use restrictions.
- Recorded the director-approved temporary SQLite development/public-staging policy in `docs/development/DATA_PRESERVATION.md`, with a summary in CURRENT_STATE and dated cross-references. Local authored reference data is authoritative; intentional Git-tracked snapshots may be deliberately committed/pushed to PythonAnywhere staging through the existing Git workflow. Database changes must not be bundled automatically with unrelated code. Precautions cover staging modifications, quiesced access, recoverable backup/stash, no automatic stale-stash reapplication, WAL consistency and public-repository sensitive-data exclusion. Before real production users or independently authored production data, an approved data-promotion mechanism must replace file deployment and preserve operational records. No mechanism was designed or implemented.

## Documentation files changed

- `docs/implementation/CURRENT_STATE.md`
- `CHANGELOG.md`
- `docs/architecture/designs/RA-EXP-01-Filterable-Vehicle-Generation-Hub-And-Homepage-Redesign.md`
- `docs/architecture/designs/RA-EXP-02-Vehicle-Contextual-Navigation-Architecture.md`
- `docs/implementation/tasks/RA-EXP-02B-1-context-services-route-contracts-baseline-selector.md`
- `docs/implementation/tasks/RA-EXP-vehicles-selector-visual-integration.md`
- `docs/development/DATA_PRESERVATION.md`
- This record.

## Verification and preservation

Documentation consistency checks verified current environment/results, application inventory, blueprint asset/template reference, query-count distinction, historical Git commit references, unresolved preservation/acceptance statements, policy coverage and referenced documentation paths. `git diff --check` passed. No Django tests, database commands or browser requests were run; implementation verification counts above come from existing task records.

SHA-256 comparisons against a pre-edit baseline confirm that existing tracked/untracked application code, tests, dependencies, governance files, images, Codex probes and other files outside this documentation scope are unchanged, except for an unexplained development-database fingerprint change. Initial database SHA-256: `53c1b8f18445c373b9e0faad3ac1f11a39e85adbedb995043267a9909c23cf63`; observed SHA-256: `1d412a7e7a355b918c35223ea713abaf2cc1a37a681c91126f9235017a00b082`. No database commands, writes or application/browser requests were issued by this task. The cause is unestablished; database preservation across this interval cannot be confirmed. No restoration or database modification was attempted. This observation is separate from the historical B-1 discrepancy. The only new repository file is this record. Git's staged diff and branch are unchanged. The two previously staged Generation images remain staged; existing unstaged/untracked work is preserved. No tracking configuration or deployment infrastructure changed. No staging, commits, pushes, reset, restore, clean or stash operations were performed.

No scope deviations. Remaining limitations are the historical B-1 fingerprint discrepancy, the unexplained database fingerprint change during this documentation interval, and pending real-browser acceptance; this documentation task does not resolve or reclassify them.
