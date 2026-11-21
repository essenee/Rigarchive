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

Configuration Logic identifies factory configurations and the dimensions that
distinguish them. Product Data is the detailed attribute layer associated with
those configurations. The generation workbook uses one **Body Configuration**
column for registered body variants. Cab and nominal bed remain canonical
attributes and manufacturer evidence, and have no separate columns in new
generation workbooks. Where the generation has no meaningful registered body
variation, Body Configuration stays blank and is hidden in the initial
worksheet. Later visibility and formatting belong to the owner.

Transmission sits immediately before Base MSRP. Canonical trim groups stay
contiguous and are ordered by their lowest Base MSRP. Within each group,
configurations are ordered by individual Base MSRP.

In newly published model-year tabs, **#** is calculated presentation. It
shows the current physical order of configuration rows and carries no
canonical identity. A single Sheets formula in the header displays `#` and
spills sequential numbers below it. It scans the whole columns for the trim
and linked-alternative fields, counts populated rows, and leaves blank rows
empty. It recalculates after complete-row moves, insertion, deletion or sorting.
Number-column cells are reserved for the formula output. The XLSX export
projects the displayed numbers as values.

### Configuration provenance

Write Provenance as `Assertion: Source-ID locator; Assertion: Source-ID locator`.
Use the smallest set of citations that establishes the distinguishing
configuration. Group assertions that use the same source and locator.
For example, MY2024 Tacoma SR code 7162 uses
`Model code/body/drivetrain/transmission: T24-S p. 1; MSRP: T24-L p. 6; Engine output by transmission: T24-P p. 1`.
The sourcebook names the order code, XtraCab, long bed, 2WD and 8AT. The
pricing schedule lists that order code and MSRP. The output table describes
the SR automatic powertrain group.

Use page or table numbers for PDFs, named sections for web pages, and a
section plus selection or model code for interactive specifications. Clearly
label grade-level or powertrain-family support when a source does not
identify the exact code. Use `Evidence gap: …` for an unsupported assertion
and `Lineage: …` for the corresponding authoring receipt or internal
observation. An internal receipt records an authoring action.

Source References resolves each readable ID to one document or document
revision. A document reused across model years has one alias entry, with each
year's applicability, review date, notes, and observation hash in Notes. A
shared alias with a different publisher, title, locator, or edition is
rejected. Keep the retrieved-byte hash, observation hash, and receipt
where they are verified. When replacing a hash in Evidence ID with a readable
alias, retain the exact previous hash in Notes and preserve the verification
status. B3 retains the source's stable working-row ID for this alias change
and rejects duplicate aliases.

Source Type is the expandable document descriptor. Include the applicable
model year or year range, manufacturer, model or scope, document name, and
format when useful. For example, `T24-P` resolves to
`2024 Toyota Tacoma Product Information PDF`, so
`Engine output: T24-P p. 1` can expand to
`Engine output: 2024 Toyota Tacoma Product Information PDF, p. 1`.
Use the actual applicable year range and distinguish mirrored text from
retained PDF bytes. Preserve the actual title in Source and keep acquisition
details and evidence limitations in Verification Status and Notes. Internal
records use RigArchive descriptors.

New generation drafts render explicitly reviewed `citations` on selected or
alternate offers using `assertion`, `source_id` and `locator`. The pinned
review's source entries declare their readable `evidence_id` values and can
supply a verified `descriptor`. Otherwise, CL derives Source Type from the
reviewed title, year, known publisher and document URL. The renderer combines
shared locators and flags missing or unresolved support.

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

A human handoff can explicitly authorize Codex to inspect and register the
latest workbook for a named generation in one workflow. Include the expected
edits or the scope of acceptable differences. Codex can proceed from inspection
to capture when the observed changes match that authorization. This also allows
the enabled Change Log to synchronize. Targeted agent publication, manufacturer
Configuration Logic approval, and canonical database changes require separate
authorization.

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
inferred editor. `--history` provides the local history. The separate Change Log
projection below is available after explicit enablement.

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
explicitly captured before preparing a new edit plan. Whole-column reordering is supported after layout enrollment. Unsupported
column changes must be resolved in Sheets before capture.

Each comparison derives separate content, structure and presentation views
from the registered snapshot and the current remote grid. This works with
existing revision files and leaves their integrity hashes intact.
Presentation-only differences are reported and do not require a new revision.
A no-op leaves the working pointer and fingerprints intact. An explicit
`--save --confirm` may capture presentation alone, including widths, alignment,
wrapping, and number formats. Presentation alone creates no semantic Change Log
entry. A successful targeted
value edit captures the preserved presentation in its successor revision.

| Surface | Working revision behavior |
|---|---|
| Cell formatting, including wrapping, fonts, colors, borders, alignment, padding, rotation, direction and number formats | Nonblocking for enrolled B3 revisions. Targeted writes preserve it. Legacy B2 publication still checks number formats. |
| Column widths and row heights | Nonblocking. Compared by dimension position independently of visibility. |
| Links, rich text, cell validation, and notes | Changes block publication. A targeted edit to a cell with rich-text runs is refused even when those runs were already registered. |
| Frozen panes | Changes block publication. The freeze boundary remains part of the registered layout. |
| Filters and sort specifications | Changes block publication. Physical row sorting can move data to different edit coordinates and also blocks. |
| Hidden or grouped dimensions | User visibility of Body Configuration is preserved and does not block B3. Other hidden or grouped dimensions remain structural safeguards. |
| Conditional formatting | Rule changes block publication because rules can carry review cues. A previously unrecorded rule or hidden dimension on a legacy revision requires an explicit capture. |
| Merged cells | A change to any merge blocks publication. Decorative merges entirely above the column headers can be explicitly captured. Header or data merges are refused even during capture. |
| Headers, column order, rows, and worksheet identity | Enrolled revisions accept complete same-tab column moves that preserve field-bound content and the paired removal of Cab and Nominal Bed. Other missing, renamed, duplicated or unknown headers, changes to row placement or count, and changed worksheet identity block publication. Legacy coordinate plans require the registered column order. |
| Drive comments and sharing settings | Outside the comparison. Targeted writes do not change them. |

Milestone A setup and pre-capture publication still use their existing sheet
formatting requests. The value-only guarantees above apply to the captured
working-revision path. The publisher rechecks the remote state immediately
before writing. Concurrent edits can still land between the read and the write.
For enrolled B3 revisions, preflight and post-write verification ignore
presentation-only differences. Unexpected value, structural or behavioral
changes prevent the registry from advancing. The generation XLSX projects data in the registered column order and retains
cell notes, supported number-format patterns, and approximate column widths.
Other Google presentation is not reproduced exactly.

Continue to use Source Selection Protocol v1.0 for research. Human edits retain
the source and applicability cells supplied in the workbook, but are not
automatically manufacturer-direct. The current workbook has source references
and provenance notes. It does not yet encode a complete assertion-level evidence
graph or an approved-snapshot contract.

## B3 layout enrollment and logical publication

After reviewing the existing registered draft, an owner can enroll it without
writing Sheets values. Use the same scope arguments above.

```bash
.venv/bin/python manage.py save_configuration_logic "${scope[@]}" --inspect
.venv/bin/python manage.py save_configuration_logic "${scope[@]}" --save --confirm --enroll-layout
```

The enrolled successor pins a versioned `layout.json` alongside the captured
grid. Old B2 manifests and CSVs remain readable and are never rewritten.
The descriptor maps logical field IDs to the required unique headers, sheet IDs,
physical columns, row IDs, and parent relationships. It records logical content,
structure, and presentation hashes. CSV files retain observed display order.
An enrolled generation XLSX exports that registered order; compatible remote
moves appear in the XLSX after capture. Google-specific protections, filters,
conditional rules and rich text are not reproduced by the XLSX projection.

Enrolled model-year tabs also support compact headers on row 1 after deletion
of the three preamble rows. Both `VehicleDefinition PK` and
`Vehicle Definition PK` resolve to the same field. Register this layout change
separately from any data edits. Capture checks that data and supported grid
bindings shift together, preserves working-row IDs, and records the new physical
row addresses. Source References retains its row-4 header.

Move whole columns within their original tab. The move must carry every value,
note, validation and noncosmetic property with its header. Unknown populated
columns, column copies, header renames or deletions, cross-tab moves and
header/data merges are refused. Unregistered semantic edits combined with a
move on the same tab are refused during capture. Capture those changes separately.
During capture and targeted-publication preflight, a move must preserve the
logical fields covered by filter ranges and frozen columns, and the field
bindings of supported sort keys and filter criteria. A raw column index that
now points to a different logical field fails this check. Unverifiable metadata,
such as charts, groups, and formula-based filter criteria, blocks a column move.

Working-row IDs are opaque. Continuity compares exact configuration witnesses
using trim, body, cab, bed, drivetrain, Engine and market. For alternatives,
the witness includes the parent and factory alternative fields. For sources,
it uses year, organization, title, locator and evidence identifier. IDs carry
forward when a unique witness matches. On numbered model-year tabs, a
complete-row permutation also has to preserve each model code, PK, value,
and behavioral metadata. A schema 2 edit resolves its stable row ID against
the verified live position. Move a parent and its linked alternatives as a
contiguous block so their relationship is retained.

On an enrolled workbook, Cab and Nominal Bed may be removed together.
B3 checks that the consolidated Body Configuration still distinguishes the
former cab and bed combinations and carries the existing working-row IDs
forward. The pair can be retired during capture or a logical value publication
without adding the columns back. Pickup authoring resolves the consolidated
label to one registered body and verifies its underlying cab and nominal bed
against the retained manufacturer evidence. Older revisions and their receipt
interpretation remain readable.
A capture may add or remove unambiguous rows. A mixture of unmatched old and
new identities, duplicate witnesses, or reordering combined with changes to
configuration identity is refused for owner adjudication. Legacy static-number
revisions retain their original row-continuity rules. A correction to a witness can require such review. There is no
automatic identity override. Human-visible numbers, Toyota codes and canonical
database identifiers remain separate from the opaque IDs.

The numbering migration changes only entered values in the number column.
It verifies the live grid against the enrolled baseline with row order and
number values projected out, then registers the verified formula-bearing
successor and re-reads it for verification. Tabs with registered calculated
numbering are skipped. Preview under `migrate_configuration_logic_numbering`
using the same manufacturer, model and generation arguments as the publisher.

```bash
.venv/bin/python manage.py migrate_configuration_logic_numbering --manufacturer Toyota --model 4Runner --generation 30 --dry-run
.venv/bin/python manage.py migrate_configuration_logic_numbering --manufacturer Toyota --model 4Runner --generation 30 --apply PREVIEW_HASH
```

Use the exact hash from the dry run. If a migration is interrupted, inspect
the live formula and registered revision before issuing any further write.

For a logical edit, use schema 2 and pick a row ID and field ID from the
registered layout. The numbers below are illustrative only.

```json
{
  "schema": 2,
  "base_revision": "REGISTERED_REVISION_ID",
  "edits": [
    {"sheet_id": 1, "row_id": "WORKING_ROW_ID", "field_id": "configuration.base_msrp", "before": 31590, "value": 31600}
  ]
}
```

Use the existing `--publish --edits PLAN.json` command only with authorization
for the exact edit. For example, if Base MSRP moves from L to H, the publisher
resolves the field to H immediately before writing. It checks the registered
base revision, logical contents, row order, field identity and typed expected
prior value. The post-write comparison verifies the complete expected entered
values and unchanged structural and behavioral metadata. Legacy schema 1 physical coordinates still
work only in the exact registered column order. A compatible move or cosmetic
edit by itself causes no publication and does not advance the revision.
A move after the final read remains a race; pause collaborative editing.

## B3 editable Change Log projection

Enable this feature separately after inspecting the live workbook. This command
can create the fifth worksheet, so it requires owner authorization.

```bash
.venv/bin/python manage.py save_configuration_logic "${scope[@]}" --sync-change-log --confirm
```

`Change Log` is appended after Source References. Existing configuration tab
IDs stay intact. The first six columns contain machine-managed revision ID,
recorded date, operation origin, affected worksheets, generated summary and
author. Unrecorded attribution or timestamps display as such. The last two
columns, Description and Additional notes, are free text and stay editable.
Machine fields have a warning-only protection request in Sheets and are
verified independently. Use Description for an explanation or a summary override.

The projection reads verified local revision manifests, change records and
receipts. It appends one entry per meaningful revision and summarizes larger
diffs. Cell changes, source changes, research notes and record additions or
removals appear in it. Initial captures without a comparison and layout-only
revisions have no semantic entry. A matching entry is reused by revision ID.
Existing human-created descriptions and notes are preserved.

After enablement, a successful save or agent edit automatically attempts
synchronization. Failure leaves the committed working revision usable and
reports projection staleness. The isolated local `<generation-uuid>.change-log.json`
records the managed sheet ID, generated entries, last synchronized revision,
and the observed and intended machine-managed states for pending operations.
Include it when backing up local state.
The projection is excluded from content capture; log updates create no
working revision. A missing, stale, or conflicting log does not prevent work
on the registered configuration tabs.

Retry with the same explicit synchronization command after inspecting an
interruption. A pending operation is acknowledged without another write when
the exact intended managed entries are already present. The same reserved
sheet ID is reused for a creation retry only when the observed state shows
no applied change. A pending repair retries when the machine-managed fields
still match the recorded pre-operation state. If they match neither state,
synchronization stops for reconciliation. Retries update only machine-managed
fields and preserve newer edits to Description and Additional notes.
The publisher does not
adopt a conflicting tab named Change Log. To repair edited machine fields on
the registered tab, review its entries and add `--rebuild-change-log` to the
explicit synchronization command. Rebuild requires the existing entry IDs to
match uniquely and repairs only verified machine columns. Deleted tabs, missing
or duplicate IDs and unknown entries require owner reconciliation or recovery
from a trusted workbook copy to protect human annotations.

Local revisions remain the authority. A Change Log annotation does not change
the underlying diff, evidence classification, approval state, or canonical data.
Source Selection Protocol v1.0 continues to apply.

## Tacoma Inactive migration and refresh

`Inactive` is the operational field `configuration.inactive`. It reflects
Django Admin's canonical VehicleDefinition activation state. A verified inactive
configuration displays `Yes`. Active configurations and rows without a
canonical PK link stay blank. Refresh verifies the PK within the generation and
cross-checks model year, market, slug, trim, body, drivetrain, and Engine.
Missing or conflicting explicit PK links stop the operation for review.

Preview the one-time migration while collaborative edits are paused.

```bash
.venv/bin/python manage.py refresh_configuration_inactive --migrate
.venv/bin/python manage.py refresh_configuration_inactive --migrate --apply REVIEWED_PREVIEW_HASH
```

Use the second command only after explicit owner approval of the current
preview. It inserts a column after Base MSRP on each model-year tab and
appends the three missing inactive MY2026 canonical configurations (PKs 1170,
1178 and 1181). Their manufacturer model code and transmission claims remain
blank. The migration preserves prior row IDs and records the new inventory
rows as one Change Log entry. Those additions are canonical inventory context,
with no manufacturer approval. The successor layout is versioned and
historical revision files remain intact.

For subsequent refreshes, preview and explicitly approve the new hash.

```bash
.venv/bin/python manage.py refresh_configuration_inactive
.venv/bin/python manage.py refresh_configuration_inactive --apply REVIEWED_PREVIEW_HASH
```

Refresh resolves the registered logical field even after a supported column
move and updates only status values. Status-only changes are excluded from
manufacturer-semantic hashes and Change Log entries. Revision snapshots still
pin the displayed status. Admin saves cause no Sheets writes. Ordinary
working-revision capture and agent edit plans refuse direct status edits.

The hash binds the registered revision, captured grid, and exact batch.
After applying, inspect the workbook and export the new working revision.
If Sheets returns an ambiguous response or post-write verification fails,
stop and inspect the grid and registry before making any further writes. A
request with a stale base or a workbook changed outside the registry is refused.
Verify whether the batch landed before separately authorizing reconciliation.
Google Sheets has no atomic preflight-and-write comparison across requests.

### Standalone trim continuity and canonical correspondence

An enrolled capture retains a standalone row ID through a trim-only edit
when the row's unique manufacturer model code, model-year worksheet,
correspondence and remaining configuration fields agree with the baseline.
This also supports a standalone row with both correspondence cells empty.
Existing PK and slug links are protected during capture.

A schema 2 targeted publication can supply `canonical_correspondences` in
place of `edits`. Each entry supplies `sheet`, the stable `row_id`, and
the committed `receipt_pk`. B3 verifies the receipt against the base revision,
row identity, model code, canonical generation, market and configuration.
It fills the empty PK and slug pair, removes exact obsolete missing-match
notes, and records the receipts in the successor change record. A linked row
or stale revision is refused. After a publication failure, verify the live
grid and registry before retrying the receipt plan. The committed SQLite
identities carry forward.

## Transmission-aware canonical authoring

The worksheet Transmission cell can preserve Toyota's full designation.
VehicleDefinition stores the controlled factory label (for example
`8-spd Auto`, `6-spd Man`, `CVT`, or `eCVT`). The factory label does not identify
hardware, ratios, or interchangeability. Detailed data remains under Full Specs.

Use `prepare_b3_authoring` against a pinned registered revision and retained
reviewed evidence. It reads the registered field map and expands only the
linked alternative rows. Each alternative inherits verified shared attributes
and must supply its own transmission, order code, price and Engine variant.
The Toyota order code remains model-code evidence. The helper projects
proposals and observations without writing. Retain those observations, review
the exact scope and peer snapshot from `reviewed_transmission_manifest`, and
supply the expressly approved digest to the existing authoring service.
The `human-body-authoring/2` path revalidates scope, workbook revision and source
evidence and records transmission in the canonical identity, slug and receipt.
Older authoring and importer wire contracts retain their previous meaning and
defer a potential transmission-aware overlap to review.

Factory-body identity is required where body is a distinguishing generation
dimension. The reviewed sixth-generation 4Runner U.S. configuration scope
has one implicit body, so its offers and receipts can carry a null body
reference. The generation rule is pinned by UUID and B3 checks the retained
offer evidence for implicit applicability. An empty body registry alone
does not establish this rule. Pickup and other body-distinguished workflows
still require the appropriate registered body.

Do not rewrite historical workbook revisions or normalize Tacoma's three
worksheet representations. Preparing a candidate does not authorize writing
SQLite, adopting a manufacturer approval, or replacing legacy records.

### MY2025 Tacoma standalone conversion

The targeted publisher supports a dedicated schema 2 conversion plan for the
three reviewed Tacoma alternatives. The plan uses the current
`base_revision` and a `standalone_conversions` list. Each entry supplies
`row_id`, `vehicle_pk`, `vehicle_uuid`, and `receipt_pk` from the canonical
creation transaction. The publisher checks the creation receipt against the
registered revision, Toyota model code, source row and former parent. It derives
the replacement values and the 1–27 numbering from the registered rows. The
successor retains the working-row IDs and records the former parent links in
its change record. Ordinary edit plans retain their existing field protections.

First reconcile and register any reviewed workbook drift. Run a remote
preflight and rehearse the approved database transaction from a verified
backup. Commit the canonical Transmission updates and the three creations
with their receipts in one SQLite transaction. Retain the committed receipt
and identity pins, then publish the dedicated conversion plan using
`publish_configuration_logic --publish --edits` with the Tacoma scope.
Verify the successor revision and the unchanged contents of the other tabs.

If Sheets rejects or ambiguously acknowledges the publication, retain the
committed database records and inspect the live workbook and registry before
retrying. If the old revision is still pinned and the live worksheet is still
at the exact baseline, the same verified plan can be published using the
existing receipts. If the cells already changed or the grid has diverged,
reconcile the verified live state with the pending plan before advancing the
registry. Do not rerun canonical creation.
