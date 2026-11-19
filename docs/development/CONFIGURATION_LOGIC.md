# Generation Configuration Logic

Run these commands from the repository root with the project’s Python 3.13 environment.
Install the optional workbook and Google client packages before the first export or
live publication.

```bash
.venv/bin/python -m pip install -r requirements-configuration-logic.txt
.venv/bin/python manage.py export_configuration_logic --manufacturer Toyota --model Tacoma --generation fourth-generation
.venv/bin/python manage.py publish_configuration_logic --manufacturer Toyota --model Tacoma --generation fourth-generation --dry-run
```

The export writes a new file under `scratch/`. Use `--output` to select another new
XLSX file. Existing files are preserved. The publisher uses the same draft data
directly. The offline dry run requires no optional packages or credentials.
The existing `--year` interface remains available.

## First Google publication

1. In Google Cloud Console, enable Google Sheets API for the project. The
   publisher uses the Sheets API with the per-file `drive.file` scope and does
   not call Drive API or search Drive by title.
2. Configure Google Auth Platform branding and audience. For an external app in
   testing, add the publishing Google account as a test user.
3. Create a **Desktop app** OAuth client. Save its downloaded JSON as
   `.configuration-logic/credentials.json` in this repository. Keep the file
   private and readable only by your local account. The entire directory is
   ignored by Git.
4. Run the authorization command and complete browser consent. The local token
   is stored in `.configuration-logic/token.json`. If access expires or is
   revoked, repeat the authorization command.
5. Confirm this generation has no existing managed spreadsheet before explicitly
   initializing it. Later publications use the same command without
   `--initialize`.

```bash
mkdir -m 700 -p .configuration-logic
.venv/bin/python manage.py publish_configuration_logic --manufacturer Toyota --model Tacoma --generation fourth-generation --authorize
.venv/bin/python manage.py publish_configuration_logic --manufacturer Toyota --model Tacoma --generation fourth-generation --publish --initialize
.venv/bin/python manage.py publish_configuration_logic --manufacturer Toyota --model Tacoma --generation fourth-generation --dry-run --check-remote
.venv/bin/python manage.py publish_configuration_logic --manufacturer Toyota --model Tacoma --generation fourth-generation --publish
```

[Google’s Desktop OAuth setup](https://developers.google.com/workspace/sheets/api/quickstart/python)

## Publication safeguards

Keep a private backup of the generation UUID’s publication registry alongside
the known spreadsheet ID. The registry stores the managed sheet IDs and
fingerprints for cell contents and supported sheet metadata. It records delivery
state for drafts. Approval and version history belong to a later milestone.

An unchanged publication issues no remote writes. During Milestone A
publication, added model years get a new tab. Managed tabs retain their IDs.
Missing or unexpected tabs, protected ranges, and non-draft registries stop
publication. Once a working revision exists, its content and structure must
match the registered snapshot. The presentation exceptions below apply only
to this working-revision path.
`--allow-shrink` permits clearing old cells when the trusted draft footprint
becomes smaller. A run never deletes a sheet.

### Recover an interrupted creation

Inspect the reservation locally first. This command does not contact Google.

```bash
.venv/bin/python manage.py publish_configuration_logic --manufacturer Toyota --model Tacoma --generation fourth-generation --inspect-reservation
```

Restore a trusted registry backup if one exists. Otherwise, if you positively
identify the intended spreadsheet, copy its ID from the Google Sheets URL and
explicitly authorize adoption.

```bash
.venv/bin/python manage.py publish_configuration_logic --manufacturer Toyota --model Tacoma --generation fourth-generation --recover-id SPREADSHEET_ID --confirm-recovery
```

Adoption reads Google and requires the expected spreadsheet title and tabs in
order. It accepts pristine empty tabs or an exact, unprotected copy of the
current draft. It refuses unknown contents and preserves existing trusted
fingerprints. An adopted empty spreadsheet remains empty until a separate
`--publish` command. Adoption does not write to Google or persist a refreshed
token.

If you checked Drive and explicitly confirm that no matching spreadsheet exists,
release the pending reservation locally.

```bash
.venv/bin/python manage.py publish_configuration_logic --manufacturer Toyota --model Tacoma --generation fourth-generation --release-no-spreadsheet --confirm-recovery
```

A manual Drive search cannot guarantee that no matching spreadsheet exists.
A registered spreadsheet cannot be released through this operation. Release
preserves a dated audit record with the previous reservation and owner
decision under `.configuration-logic/recovery-audit/`. Keep those records with
the local registry. The registry remains marked released until a separate
`--publish --initialize` command intentionally starts a new attempt. Release
does not contact Google or create a spreadsheet.

Google Sheets applies each publication batch atomically. Its API provides no
compare-and-swap precondition for this write. Avoid editing the spreadsheet
during publication. The command rechecks remote state just before writing and
verifies tab order, IDs and values afterward. The registry fingerprint covers
cell values, formulas, notes, formatting, and the requested grid metadata. It
does not cover Drive comments or sharing permissions. Keep separate protected
files or tabs for approved work. A spreadsheet status cell does not confer
approval.

`--dry-run --check-remote` checks the registered draft without writing to the
spreadsheet, registry, or token file. A remote match confirms synchronization of
a draft. It does not establish approval.

## Tacoma datasets

- MY2026 contains 24 active database-derived configurations for review. Model
  codes from the earlier standalone workbook lack receipt-linked mappings for
  these current definitions and are blank in the generation export.
- MY2025 contains 24 active database-derived configurations and three reviewed
  transmission alternatives. Codes and alternative details come from the
  retained receipt-pinned observation. Missing or invalid local evidence leaves
  those fields blank and adds a provenance gap.
- MY2024 is an empty research draft. Its existing sparse legacy database rows
  lack the registered Engine and factory body detail needed for this draft.

A supplied research dataset can construct a model-year draft through
`draft_year(..., authored_rows=...)` without creating VehicleDefinitions. The
publisher accepts a structured `GenerationDraft`. That boundary lets Milestone B
load locally approved immutable data independently of the ORM.

## Capture a Google Sheets working revision

Use this workflow after editing the registered review workbook in Google Sheets.
Inspection reads Google without persisting a refreshed token or writing local
state. Before the first capture, Milestone A fingerprints can detect a mismatch
but cannot reconstruct previous cell values. The first capture establishes a
comparison baseline. Afterward, inspection reports cell and source changes,
notes, added or removed rows, schema problems, and captured layout changes.

```bash
scope=(--manufacturer Toyota --model Tacoma --generation fourth-generation)
.venv/bin/python manage.py save_configuration_logic "${scope[@]}" --inspect
.venv/bin/python manage.py save_configuration_logic "${scope[@]}" --save --confirm
.venv/bin/python manage.py save_configuration_logic "${scope[@]}" --history
.venv/bin/python manage.py export_configuration_logic "${scope[@]}" --output scratch/tacoma-working-review.xlsx
.venv/bin/python manage.py publish_configuration_logic "${scope[@]}" --dry-run --check-remote
```

Review the inspection before confirming the save. The two invocations read
separately, so pause spreadsheet editing before saving. Save rechecks the
remote state immediately before registering; Google does not offer an atomic
read-and-register operation spanning Sheets and the local filesystem.

### Local revisions and recovery

Revisions live under
`.configuration-logic/revisions/<generation-uuid>/<revision-id>/`. Each
directory contains the structured Sheets cell and layout data in
`workbook.json`, a CSV per sheet, a manifest with content, structure and
individual file hashes, a predecessor pin, a structured change record, and a
capture receipt. CSV protects formula-like literal text with a leading quote.
JSON preserves original types, positions, and annotations. An empty research
draft keeps its title, status and column headers. Sheet identity, tab order,
and headers must be returned in full before capture is accepted.

The existing locked registry holds both the current manifest pin and the
remote fingerprints. Registration writes a complete new revision directory
before replacing that registry atomically. Interrupted registration leaves the
prior pointer usable. A complete directory left outside the registered history
is an orphan and is never selected automatically. Restore a damaged or missing
registry and revision history together from a trusted backup. If a network or
local error occurs after an agent write, inspect the workbook and explicitly
capture the resulting state. A retry from the old revision will fail the
fingerprint check if the remote write landed.

Back up the registry and revision directory together. Git ignores both, as well
as credentials and tokens. Track code, tests and this documentation. These
working artifacts contain human annotations and remain local by default. Release
of a working artifact into Git requires separate owner review. Registration
does not approve a snapshot, change evidence classification, or authorize any
Django reconciliation. The API does not reliably identify the editor of each
individual change. The receipt records the explicit local operation, not an
inferred editor. `--history` provides the local change log. A remote Change Log
worksheet is deferred.

### Resume from the registered working revision

Generation export and the publisher load the registered revision before
Django-derived data. With a working revision present, the model-year-only
export directs the operator to the generation export. A normal publication on
a matching registered revision is a no-op. Agent edits are an explicit cell
plan against the current revision ID.

```json
{
  "base_revision": "REVISION_ID_FROM_HISTORY",
  "edits": [
    {"sheet": "MY2025", "row": 5, "column": 12, "before": 31590, "value": 31600}
  ]
}
```

The example is illustrative. Use the current recorded value, and obtain
authorization for the actual edit before publication. Supply the reviewed JSON
plan with `publish_configuration_logic "${scope[@]}" --publish --edits PLAN.json`.
Plans target existing data cells and cannot change configuration numbers, PKs
or slugs. The publisher checks the baseline revision, prior cell values, the
registered content and structure, and the resulting schema. It sends only the
intended values and verifies the returned values and captured metadata before
registering the successor. Unregistered changes to values, source references,
or research notes block publication. Supported content changes must be
explicitly captured before preparing a new edit plan. Unsupported changes
such as reordering columns must be resolved in Sheets before capture.

Each comparison derives separate content, structure and presentation views
from the registered snapshot and the current remote grid. This works with
existing revision files and leaves their integrity hashes intact.
Presentation-only differences are reported and do not require a new revision.
A no-op leaves the working pointer and fingerprints intact. An explicit
`--save --confirm` may capture presentation alone. A successful targeted
value edit captures the preserved presentation in its successor revision.

| Surface | Working revision behavior |
|---|---|
| Text wrapping, fonts, colors, borders, alignment, padding, text rotation and direction | Nonblocking. Compared separately from content. Targeted writes preserve them. |
| Column widths and row heights | Nonblocking. Compared by dimension position independently of visibility. |
| Number formats, links, rich text, cell validation, and notes | Changes block publication. A targeted edit to a cell with rich-text runs is refused even when those runs were already registered. |
| Frozen panes | Changes block publication. The freeze boundary remains part of the registered layout. |
| Filters and sort specifications | Changes block publication. Physical row sorting can move data to different edit coordinates and also blocks. |
| Hidden or grouped dimensions | Changes block publication because rows or columns can disappear from review. |
| Conditional formatting | Rule changes block publication because rules can carry review cues. A previously unrecorded rule or hidden dimension on a legacy revision requires an explicit capture. |
| Merged cells | A change to any merge blocks publication. Decorative merges entirely above the column headers can be explicitly captured. Header or data merges are refused even during capture. |
| Headers, column order, rows, and worksheet identity | Missing, renamed, duplicated, or moved headers, changed row placement or count, and changed worksheet identity block publication. Capture still requires exact ordered headers and stable tab IDs. |
| Drive comments and sharing settings | Outside the comparison. Targeted writes do not change them. |

Milestone A setup and pre-capture publication still use their existing sheet
formatting requests. The value-only guarantees above apply to the captured
working-revision path. The publisher rechecks the remote state immediately
before writing. Concurrent edits can still land between the read and the write.
If post-write verification finds any unexpected captured change, the registry
does not advance. The generation XLSX is a data projection. It does not
reproduce the captured Google presentation or notes.

Continue to use Source Selection Protocol v1.0 for research. Human edits retain
the source and applicability cells supplied in the workbook, but are not
automatically manufacturer-direct. The current workbook has source references
and provenance notes. It does not yet encode a complete assertion-level evidence
graph or an approved-snapshot contract.
