# MY2019 Wrangler JL director-review preparation

Created: 2026-11-07
Status: Draft

**Latest:** [compact retention report](COMPACT_EVIDENCE_RETENTION.md) records the supplied June four-door guide inspection and 19 revised preparatory candidates. These reference Git-eligible compact evidence files; no PDF hash/copy is required. Explicit 4WD is now supported for the 13 four-door rows.

**Superseded acquisition assessment:** the director accepts the 19-offering inventory. See [minimum evidence report](MINIMUM_EVIDENCE_REPORT.md) and `preparatory_candidates/` for 19 validated, incomplete Candidate 2.1.0 artifacts. Original PDFs for all 18 editions are not required, and the Homebrew runtime is now operational. The remainder below preserves the earlier checkpoint.

Candidate construction was **blocked** at that checkpoint, not complete. These materials are an evidence-gap review and are not an executable Matrix 2.1, candidate, manifest, authorization or importer proof.

## Materials

- `director_review_19_rows_BLOCKED.csv`: all 19 supplied combinations, proposed engine descriptors and provisional slugs, model codes, reported source links/pages, five proposed attributes and explicit blocked eligibility. Original research columns remain historical scaffolding; new live assessment columns supersede the uploaded peer snapshot. All proposed classifications remain unverified. Altitude and Moab remain distinct; ERC and EC3 remain separate proposals. No transmission or quick-order code is used as independent identity.
- `source_evidence_ledger_BLOCKED.csv`: all 18 supplied editions, no invented raw hashes or assertion IDs, acquisition status and unverified printed dates. Revision dates and filenames are inherited research metadata, not certified document dates. In particular, March filename versus printed-date discrepancy remains unresolved.
- `live_database_assessment.json`: current read-only migration/count/integrity inspection and the 15 MY2018 JL peers. This replaces reliance on the older uploaded database snapshot.

## Precise blockers and smallest remedies

1. **Authentic source bytes unavailable.** Download of the supplied June four-door guide at https://www.jlwranglerforums.com/forum/attachments/4-door-6-4-19-pdf.190918/ failed with `Network access ... was blocked: domain is not on the allowlist for the current sandbox mode`. An escalated retry returned the same restriction. Other editions were not attempted after this blocker. No original PDF binaries are supplied in the handoff. Remedy: supply the original 18 guide PDFs inside the repository, or enable approved acquisition of these exact archive attachments. Do not bypass the network restriction. Hash actual bytes and verify printed dates/pages before certifying the dated-revision union.
2. **Assertion-level evidence not established.** Research tables do not establish document-qualified claims for marketed trim, model-code applicability, engine offering and all five structured attributes. In particular, ESS alone cannot prove nonhybrid status; missing turbo/gasoline wording cannot establish naturally aspirated/gasoline. After acquisition, identify explicit applicable claims (and any necessary additional manufacturer technical source), retain bytes and build reviewed assertions. No broad unrelated research was performed.
3. **Required validation runtime unavailable.** `venv/py313/bin/python` does not exist. `venv/bin/python --version` fails because its Python 3.13 framework cannot be loaded. `/opt/homebrew/bin/python3.13` is 3.13.2 but cannot directly import Django. Remedy: restore the approved Python 3.13/Django environment or explicitly authorize an available supported environment. No dependency install, environment rebuild or Python-path workaround was performed.

## Contract and live-state findings

The accepted ADR-0012/RA-044 and RA-018 require source evidence before canonical promotion. `candidate_powertrain()` validates the exact five-field projection and qualified raw claims; `validate_documents(..., verify_bytes=True)` requires retained repository source files matching actual SHA-256 values. Existing Jeep acquisition/extraction is bounded to reviewed 2018 publications and cannot silently certify 2019. No contract was modified and no new extractor was implemented.

SQLite was opened with URI `mode=ro`. Reference migrations 0007–0010 are applied; 793 definitions and 2,856 receipts exist; all five structured fields are null on historical rows. Integrity returns `ok`; foreign-key check returns no violations. All 15 current JL definitions under generation PK 32 are MY2018. No MY2019 JL peer exists. The 19 provisional slugs are distinct and have no current occupied slug match. These are SQL inventory checks, **not** resolution 1.1, engine proof 2.0 or Matrix 2.1 validation. Those mechanisms were not invoked without valid source-backed candidates. Historical unknown engine fields were not inferred or populated.

Proposed slugs follow the inspected descriptor/engine-fields/1 recipe: ERC uses `36l-v6`, EC3 uses `20l-i4` and `-turbo-mhev`. They remain conditional on validated evidence and actual planner output. Quick-order codes remain scoped by model code. No union is certified and no Moab EC3 proposal is added.

## Focused validation actually performed

- Parsed the supplied readiness inventory: 19 rows; revision ledger: 18 rows.
- Verified 19 unique provisional slugs and zero occupied matches with current definitions.
- Read live migrations, counts and JL peers; ran SQLite integrity/foreign-key checks read-only.
- Development database SHA-256 before/after assessment: `b045601a33811b44a443b7c0cc78ce916e9af476cb3c5f4c5b94dc2fdf18e26f`.
- Runtime probes failed as described above. No Django checks, candidate validations, focused Django tests or full regression suite were executed in this follow-up. Prior RA-044 tests are historical results, not new executions.

No application code, migrations, existing canonical identities or historical artifacts were changed. Documentation records the director-confirmed RA-044 acceptance and live migration completion. Pre-existing working-tree changes were preserved; no staging, commit, push, import, correspondence publication or approval artifact creation occurred.

Resume source acquisition and candidate validation after the blockers are resolved. Director import authorization must follow review of a genuinely validated Matrix 2.1; these files cannot authorize execution.
