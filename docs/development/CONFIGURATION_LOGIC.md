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

An unchanged publication issues no remote writes. Added model years get a new
tab. Managed tabs retain their IDs. A missing managed tab, external edits,
unexpected tabs, protected ranges, or a non-draft registry stop publication.
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
