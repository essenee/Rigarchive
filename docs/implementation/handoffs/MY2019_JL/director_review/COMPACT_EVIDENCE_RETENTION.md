# MY2019 JL compact evidence retention

Created: 2026-11-07
Status: Draft

## Implemented approach

The director accepts published order-guide authenticity. This task did not calculate a PDF hash, copy the PDF into managed storage, require it as a downstream evidence reference, or repeat the historical-union research. The provided guide was read directly from `source_pdfs/4 Door 6-4-19.pdf`.

A **3,621-byte JSON excerpt** retains selected manufacturer text and its title, URL, printed revision and page numbers. It is labeled as selected text, not original PDF bytes. The original accepted research snapshot (40,781 bytes) is copied byte-for-byte from ignored managed storage into the same Git-eligible review evidence directory. Its existing content hash is preserved. No original snapshot or earlier candidate is changed.

The two compact evidence files are:

- `compact_evidence_revision_2/evidence/accepted_research_snapshot.json`
- `compact_evidence_revision_2/evidence/jlu_2019_06_04_selected_excerpts.json`

All 19 new preparatory candidates reference only these review-directory evidence paths, not ignored storage files. The review directory is eligible for normal Git inclusion; nothing was staged or committed. This resolves the missing-file problem for a future checkout that includes the new review revision. It does not pretend that currently untracked work is already preserved in Git history.

The hash on each small retained representation verifies artifact consistency; it does not authenticate the manufacturer or stand in for a PDF hash. `validate_documents(..., verify_bytes=True)` accepts a retained file anywhere within repository BASE_DIR whose bytes match its hash. Managed `storage/raw_source_artifacts/` placement is not mandatory for this validator. No accepted contract was changed.

## New evidence established

The supplied guide is reissued June 4, 2019, originally issued September 11, 2018, and identifies US MY2019 Wrangler four-door scope on page 1.

- Pages 2, 5 and 9 contain the 13 four-door offering rows already accepted by the director. The excerpts retain the powertrain/quick-order tables, including Altitude and Moab columns. The guide is supporting evidence, not a repeated 18-revision union review.
- Those pages explicitly describe ERC as `3.6L V6 ... W/ESS` and EC3 as `2.0L I4 ... TURBO ETORQUE`.
- Page 15 has model-code columns JLJL74/JLJP74/JLJS74, Command-Trac part-time 4WD for Sport/Sahara and Rock-Trac part-time 4WD for Rubicon. Sahara-family optional Selec-Trac, also observed on page 5, is likewise 4WD. No transfer-case subtype is made a separate canonical identity. The retained standard-equipment evidence supports generic 4WD for the four-door model families.

The 13 four-door revised candidates now bind their engine facts to the actual guide excerpts and include an explicit 4WD interpretation. The six two-door candidates preserve their accepted research lineage and unknown drive evidence; this four-door guide is not generalized to them.

The guide text contains no explicit gasoline, naturally aspirated or nonhybrid classification. Fuel-tank or fuel-door equipment is not evidence of fuel type, and ESS is not evidence of `none` under the accepted powertrain contract. These missing classifications remain unknown rather than being filled from engineering assumptions.

## Remaining gates

- ERC: explicit applicable naturally aspirated, gasoline and nonhybrid evidence.
- EC3: explicit applicable gasoline evidence.
- Two-door: explicit applicable drive evidence.
- Reviewed generation correspondence for the retained model-code evidence before executable planning; no correspondence was published.

These facts may be supplied as small source-linked excerpts or existing research extracts with explicit applicability; more complete PDFs are not required for their own sake. A five-field complete engine proof or executable Matrix 2.1 is not certified yet.

Production does not need a duplicate original order guide to satisfy these revised candidate references. If this review revision is later used for planning/execution or peer-evidence reconstruction, its small referenced evidence files must be available to that ingestion environment. This task changes no deployment configuration and deletes no source material. Removing **all** retained evidence hashing would change the accepted lineage and transaction-time validation contract; it is unnecessary for the compact-excerpt approach implemented here.

## Validation and preservation

`compact_evidence_revision_2/validation_results.json` records successful contract validation, retained-byte validation and serialization round trips for all 19 revised preparatory candidates. Each completeness check correctly rejects missing fields. Read-only planning keeps all rows non-executable; four-door planning now reaches the missing reviewed-generation-correspondence gate, while two-door planning reports missing drive evidence.

The live database was accessed using SQLite URI `mode=ro`; its SHA-256 was unchanged before/after. This preservation hash is of the development database, not the PDF. Application code/contracts were not modified, so no further Django regression suite was run; actual artifact validators were executed against this revision. Prior focused tests and system/migration checks remain recorded in the earlier minimum-evidence report.

`retain_compact_guide_evidence.py` reproduces this task-local revision and refuses to overwrite an existing output. No canonical imports, historical-identity changes, backfills, publications, staging, commits or pushes occurred. Pre-existing changes and prior review artifacts remain preserved.
