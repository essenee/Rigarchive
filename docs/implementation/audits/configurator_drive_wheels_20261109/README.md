# Configurator drive-wheel audit and A/B review

Created: 2026-11-09
Status: Complete

The owner visually verified Toyota Tacoma, Volkswagen Touareg and Jeep Wrangler JL
labels and authorized the completed implementation commit on
`feature/configurator-drive-wheel-display`, starting at local
`764389b986ec37a58a6b3b7d579409fea382f314`. Remote main was independently verified
at `ab1984b4cb50be115669d602aab5fa915a3ea22e` before branching. Main is unchanged;
the owner-authorized commit remains on the feature branch only. No push, merge,
deployment, migration or canonical import was performed.

## Complete canonical audit

[All 934 rows (JSON)](all_configurations.json) and [CSV](all_configurations.csv)
include identities, canonical field, visibility, exact URLs, before/after labels
for year and trim views, receipt references and evidence limitations.
[Grouped audit](grouped_audit.json) covers 105 manufacturer/model/generation/year
groups, with record PKs and counts. [Summary](summary.json) provides exact totals.

| Manufacturer | All records | Publicly eligible | Hidden drive in year view before | Hidden drive in trim view before |
| --- | ---: | ---: | ---: | ---: |
| Toyota | 632 | 602 | 14 | 36 |
| Volkswagen | 66 | 65 | 65 | 0 |
| Jeep | 236 | 236 | 204 | 147 |
| Total | 934 | 903 | 283 | 183 |

Every canonical record has a recognized `VehicleDefinition.drivetrain`: **283 2WD,
581 4WD, 70 AWD**. No canonical blank/UNK/unsupported values, indirect-only values,
or recognized drive tokens embedded in trim/engine names were found. `4xe` is an
electrification marketing name, not a driven-wheel token. The only nonempty canonical
notes value is a model-year applicability note; no canonical mode/axle assertions
are stored there. Thirty-one inactive records are intentionally excluded from the
public configurator, not misreported as display omissions.

After the change, all **903 eligible records** show the canonical category in
both audited label contexts. The 283/183 counts describe explicit year/trim contexts,
not the default landing page: automatic first-trim selection can narrow that page.
No missing canonical categories were discovered. Lack of front/rear specificity is
a representational limitation, not evidence that any existing 2WD category is wrong.

### Source limitations and conflicts

No discrepancy was found between current canonical drive categories and applicable
creation-receipt target fields or resolution fields. This checks normalized retained
lineage, **not** a fresh manufacturer-source adjudication for all 934 records.

- 93 records have no linked creation receipt (92 active, one inactive).
- 605 receipt-backed records have no resolution snapshot (575 active, 30 inactive).
- 236 records have a nonempty creation-resolution snapshot.

Per-record PKs and receipt evidence coverage are in the audit. Absence of a resolution
snapshot does not mean no manufacturer evidence exists elsewhere; this audit does
not infer evidence absence or contradict accepted canonical values. Raw manufacturer
statements were not exhaustively re-adjudicated. Unbound raw document/operating-mode
mentions are not treated as candidate-specific conflicting classifications.

The sole canonical driven-wheel field is the broad enum. Accepted ingestion
`DrivetrainDetails` can retain architecture, components, operating modes, capabilities
and manufacturer terminology in artifacts; these are not additional persisted
VehicleDefinition axle/mode fields. Such evidence, notes and all receipts/artifacts
remain untouched. No mode is converted into an AWD/4WD classification or discarded.

## Proposed display standard

Every configuration choice ends with its existing authoritative broad category,
once: **2WD**, **4WD** or **AWD**. These remain distinct accepted enum values. Keep
compact varying trim/engine descriptors, market and canonical-slug disambiguation.
If only drive differs, show the drive alternatives without redundant engine text.
Never derive or override a category from a trim name, engine label, operating mode,
manufacturer marketing name or free-text note.

- Unknown/blank/None: **Drive wheels not specified**.
- Unsupported/combined values: **Drive wheels require review**; never guess.
- 2WD does not establish FWD versus RWD. None of the 934 records has a dedicated
  authoritative front/rear field, so neither is invented here. If future source
  adjudication establishes axle layout, owner-approved representation is needed
  before adding that specificity. FWD/RWD are not silently added to the enum.
- 4WD remains 4WD even with selectable 2WD/2H, full-time operation, low range or a
  lockable center differential. These are capabilities/modes, not synonyms for AWD.
  This change neither rewrites nor removes any detailed evidence or specification.

This standard requires no schema or ingestion-contract change. It is implemented
only in the existing presentation label service. No receipt queries are added to
the public request path, and no canonical identities, ordering or URLs change.

## Before/after examples

| Context | Before | After |
| --- | --- | --- |
| Toyota Tacoma 1998 PreRunner, trim selected | 2.7L I4 | 2.7L I4 · 2WD |
| VW Touareg 2004, year-wide label | V10 TDI · 5.0L V10 | V10 TDI · 5.0L V10 · AWD |
| VW Touareg 2004 V10 TDI, trim selected | 5.0L V10 · AWD | Unchanged; AWD appears once |
| Jeep JL 2021 80th Anniversary Edition, trim selected | 2.0L I4 · Turbocharged | 2.0L I4 · Turbocharged · 4WD |
| Drive-only alternatives | 2WD / 4WD | Unchanged |

## Validation and preservation

Full Django suite: **724 passed**, including nine new unit/page regressions for
shared 2WD/4WD/AWD categories, unknowns, unsupported/conflicting tokens, front/rear
non-inference, multiple modes, duplicate avoidance, markets and trim/exact deep links.
An initial focused run passed 54 tests; the additional integration test passed in
the full suite. Django system checks and migration dry-run passed. SQLite integrity
is ok, foreign-key violations zero. [Verification record](verification.json).

**31 existing frontend callbacks passed**, including scroll preservation, changed
years, deep links, focus, race/fallback behavior, header and quick-selector tests.
The Node CLI is absent; existing CommonJS tests ran via the bundled Node runtime's
VM/callback collector using their original assertions. No dependency was installed.
Selector JS/CSS/template are unchanged from the eight-row/scroll fix. Existing
>10-configuration first-trim selection, ordering and native links remain covered.

[Rendered-page verification](rendered_page_verification.json) covers 15 real canonical
requests across Toyota, Volkswagen and Jeep, including MY2021 JL, in year/trim/exact
modes. RequestFactory used a memory-only session and a read-only/query_only SQLite
connection, so Recently Viewed never wrote to the operational database. Its initial
harness used a plain dict without a `modified` attribute; the corrected in-memory
session supports it and all 15 requests passed. No browser was pointed at the live
site/database in this task. Real browser scroll/height results from the unchanged
starting implementation remain in the trim-selector task record; this task reran
frontend regression assertions, not a new physical browser session.

Operational SHA-256 before/after:
`sha256:7a4661e3ddfadfd7970af235d2d761fc9471189b14a9bf41595373ed569f8868`.
Counts: **934 definitions / 3,148 receipts / 159 correspondences**. The operational
file remains intentionally different from the sanitized Git checkpoint. No secret,
session content, password or authentication value is included in this audit.

## Local A/B launch

Use the already verified `.venv/bin/python` (Python 3.13.1, Django 6.0.7). The
historical `venv/py313/bin/python` path is absent; no alternate packages were installed.
Keep the feature branch separate from main. To avoid preview browsing
changing operational sessions, first create a separate local database copy:

```bash
.venv/bin/python -B - <<'PY'
from pathlib import Path
import sqlite3
preview = Path('/tmp/rigarchive-drive-wheel-review.sqlite3')
assert not preview.exists(), 'Choose another fresh preview filename; do not overwrite an existing copy'
source = sqlite3.connect('file:' + str(Path('db.sqlite3').resolve()) + '?mode=ro', uri=True)
copy = sqlite3.connect(preview)
source.backup(copy)
copy.close()
source.close()
PY
RIGARCHIVE_TEST_DB_PATH=/tmp/rigarchive-drive-wheel-review.sqlite3 .venv/bin/python manage.py runserver 127.0.0.1:8766 --noreload
```

This copies operational private state locally; keep it outside Git and do not
upload it. Browse anonymously. Only the preview copy may receive session writes.
Stop the server after review; do not replace the operational database with it.

Compare these relative paths on `http://127.0.0.1:8766` and the configured production
host `https://rigarchives.pythonanywhere.com`:

- `/vehicles/toyota/tacoma/first-generation/?year=1998&trim=PreRunner#configurations`
- `/vehicles/toyota/4runner/fifth-generation/?year=2010&trim=Limited#configurations`
- `/vehicles/volkswagen/touareg/first-generation/?year=2004#configurations`
- `/vehicles/jeep/wrangler/jk/?year=2007&trim=Unlimited%20Sahara#configurations`
- `/vehicles/jeep/wrangler/jl/?year=2021&trim=80th%20Anniversary%20Edition#configurations`
- `/vehicles/jeep/wrangler/jl/?configuration=2021-80th-anniversary-edition-20l-i4-4wd-us-turbo#configurations`

VW's automatic first-trim narrowing may already show AWD; the audit also preserves
its year-wide pre-narrowing label context, not a claim every VW landing page changes.
Production was not queried/deployed; its current data/code are unverified. The local
sanitized Git checkpoint has the MY2021 milestone, but that alone does not prove
production contains it. A production 404/missing year may be a data/deployment
difference, not this feature. Local code includes the unpushed `764389b` trim-scroll/
height fix; the published Git baseline `ab1984b` does not. The actual deployment is unknown. Compare drive labels
separately from those existing selector differences. An exact code-only baseline
can be reviewed with `git show 764389b:reference/services.py` without switching,
resetting or stashing this branch.

Review nearby trims, year changes, deep links, keyboard focus and scroll retention.
Unknown/conflict cases are synthetic test fixtures only; no current row needs a
fabricated production demonstration.

## Owner decisions

No blocking decision is needed for consistently displaying existing broad categories.
The owner approved this presentation correction after visual verification. Optional future
work: source verification of legacy provenance gaps, and an approved representation
for front/rear axle layout or detailed modes if those should become separate visible
attributes. Neither is implemented or silently inferred. No source adjudication or
canonical correction is proposed solely from label differences.

## Commit validation (2026-11-09)

The owner authorized committing this feature after visually verifying Tacoma,
Touareg and Wrangler JL. Fresh checks reconfirmed all 934 audit identities against
canonical records, 903 public-label coverage, 934/3148/159 totals and unchanged main
at 764389b. 55 relevant Django tests and 31 existing frontend callbacks passed, with
Django system checks, migration dry-run, SQLite integrity and foreign keys. The
prior 724-test full-suite result above remains the broader verification; it was not
rerun for this documentation/commit-only step.

The operational SQLite SHA-256 was unchanged throughout this commit task; see
[commit validation](commit_validation.json). This is a new task-local baseline,
separate from the historical audit hash above. Only implementation/tests/docs are
staged; operational db.sqlite3 is excluded. The authorized commit message is
`fix: consistently display canonical drive-wheel categories`. No push, merge,
deployment or main modification is authorized/performed.
