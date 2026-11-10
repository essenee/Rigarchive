# Discovery validation and completion record

Created: 2026-11-09
Status: Proposed

Discovery deliverables prepared for review on 2026-11-09. Completeness and
classification questions remain explicit; this is not ingestion certification.

## Checks actually executed

- `validate_discovery.py`: **6 tests passed**, including re-extraction and SHA-256
  of all PDFs, independent plain-text QOP inventory, exact row/source/page lineage,
  union uniqueness, scope/null boundaries, comparison/package lineage and read-only
  database preservation. Transcript: `source_validation.txt`.
- `verify_project.py check`: **passed**, no system-check issues.
- `verify_project.py migrations`: **passed**, no changes detected; dry run only.
- `verify_project.py test`: **724 tests passed**, 46.412 seconds, isolated Django
  memory database and temporary media/files. Transcript: `project_tests.txt`.
- Visual inspection: rendered February four-door p2 and checked the six QOP columns,
  blank High Tide cells and single 25D/ERG/DFT positive cell against transcription.
  Poppler emitted fontconfig/cache warnings but produced a readable page; no source
  PDF was edited. Other cells were checked through independent plain/layout text,
  not a claim of manual visual inspection of every page.
- Final preservation/hash manifest and `git diff --check` results are recorded in
  `discovery_validation.json` and `final_git_checks.txt`.

Commands used the explicitly owner-authorized `.venv/bin/python -B`: actual
Python 3.13.1, Django 6.0.7, pypdf 6.16.1. The prescribed venv/py313 interpreter
was absent. Initial PDF extraction used the bundled document runtime (pypdf
6.21.4); the final builder regenerated and verified all PDF extraction with the
approved local pypdf 6.16.1. No software was installed or upgraded.

The isolated verification wrapper sets RIGARCHIVE_TEST_DB_PATH=:memory:, rejects
SQLite connections outside memory or the system temporary directory, and assigns
temporary MEDIA_ROOT. First test launch failed before running because the wrapper
replaced Django's TEST options; corrected to update NAME only. The next run had two
errors because the guard rejected legitimate temporary-file snapshot/rehearsal
tests. Corrected the wrapper to permit system temporary files, with operational
SQLite still rejected, and reran all 724 successfully. No application/test behavior
was altered to obtain a pass. Existing fixture acquisition tests emit rotated-text
warnings; these did not cause failures.

## Preservation and Git

Read-only SQL confirmed 934 VehicleDefinitions, 3,148 receipts, 159 correspondence
revisions, the expected Generation 32 UUID and zero MY2022 definitions for that
generation. Hashes of db.sqlite3 and the pre-existing DATA_PRESERVATION.md change
match the retention-stage baseline. No database writes, migrations, backfills,
restores, sidecar removal or canonical import commands were issued. The baseline
was recorded after source acquisition began; it is not falsely represented as a
before-first-tool fingerprint. No MY2019–MY2021 artifact was intentionally modified.

Initial branch/HEAD matched main/bef7d76e3fe4f33990180694f845a436b7987da3. During
this session main advanced externally to 035bfcf3862f2c0f5e20d616d086218afd7e57d3.
The initial local DATA_PRESERVATION.md difference is no longer shown as a Git diff,
but its bytes still match this task's baseline. This task performed no commit,
push, checkout, reset, merge, rebase, stash or other Git mutation. Existing work
and the newer CURRENT_STATE/CHANGELOG contents were preserved before adding the
discovery entry. The task's source/contract changes are limited to new handoff
research artifacts; no production application or schema changes were needed.

## Remaining work / deviations

No scope expansion. Exact HTTP acquisition timestamps were not instrumented;
filesystem-derived acquisition and filesystem-derived acquisition and retention timestamps and their meaning are recorded explicitly. Original public
source bytes and hashes are retained. Complete historic revision coverage, Beach
identity/code linkage, RHD scope, source contradictions and five-field review remain
unresolved as documented. No Candidate construction or Matrix certification began.
Stop here and await discovery review.
