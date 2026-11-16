# Engine registry reconciliation and Configurator display normalization

Created: 2026-11-15
Status: Implemented and verified; pre-assignment results below are historical
Disposition: Initial display/preview work implemented. The owner subsequently approved and executed
the exact 507 proposals; see `engine-registry-assignment-execution.md`. Counts and
non-execution statements below describe the original pre-assignment milestone.

## Implemented presentation boundary

`reference/services.py::_label_configuration_choices` now selects Engine.name for a
linked row and the existing engine_name otherwise. `reference/powertrain.py::engine_label`
accepts an explicit optional display_name; its default remains snapshot-based.
Existing turbo/diesel/electrification formatting is reused, not duplicated in templates.
Labels are computed once per choice and reused by drive-only choice handling.
The hub already selects related Engines, so the new name lookup adds no query there.

The linked name change affects Configurator choice text and associated aria/Specs-link
labels. `generation_detail.html` renders choice_label, and generation_configurator.js
replaces server-rendered HTML; it has no separate engine-name algorithm to change.
No template or JavaScript changes were needed. Model __str__, long engine_description,
Full Specs engine descriptors/sibling labels and model-year overview descriptors retain
historical behavior. Existing engine-option statistics still use snapshot descriptors;
this task does not silently deduplicate counts or canonical configurations.

The current registry already names ERC “3.6L V6”; no registry edit was needed. Read-only
live verification finds 43 linked ERC JL choices without ESS. Their stored descriptors
remain one “3.6L V6” and 42 “3.6L V6 ESS”. eTorque/MHEV distinctions remain. No ESS
substring stripping or year/model exception was introduced in the display formatter.

## Read-only inventory artifact and command

Complete artifact:
`docs/research/engine_registry_reconciliation_20261115/assignment_preview.json`

Command: `.venv/bin/python manage.py preview_engine_assignments`

The command prints JSON only; no execute option exists. The service
`reference/engine_reconciliation.py::preview_engine_assignments` inventories every
stored definition, including inactive and hidden records, without model saves.
The artifact contains all 1,150 PKs/UUIDs, hierarchy/year/market/trim, lifecycle/public
state, historical descriptor, existing/proposed Engine identities, five-field values,
compatibility conflicts/unknown completions, correspondence method, recognized
binding evidence and receipt references. It also includes all 10 Engines, 110
hierarchy/year groups, 49 scoped descriptor/powertrain patterns and 32 exception groups.

The directory/report use the owner's local task date 2026-11-15. The artifact's
inventory_date is 2026-11-16 because Django's configured timezone is UTC. The final
snapshot digest is
`sha256:7ab06c7f7afa590ff7bcd4172e196b5e4b19e596305987467c76ed2b3676bbb8`.
This is a preview artifact identifier, not execution authorization.

| Classification | Count |
| --- | ---: |
| ALREADY_LINKED | 104 |
| EXACT_MATCH | 485 |
| APPROVED_ALIAS_MATCH | 22 |
| EXPLICIT_BINDING_MATCH, currently unlinked | 0 |
| AMBIGUOUS, currently | 0 |
| CONFLICT | 61 |
| INSUFFICIENT_EVIDENCE | 412 |
| NO_REGISTERED_ENGINE | 66 |
| Total | 1,150 |

There are 1,046 unlinked definitions and 507 compatible proposals: 502 active and
five archived. All proposals still require owner approval of their correspondence
scope; no match was executed. All 104 linked rows have compatible current snapshots;
no recognized binding errors were found. Ninety-seven rows have recognized retained
registry binding receipts; their targets are already linked.

| Manufacturer | Already linked | Compatible proposals | Conflict | Insufficient | No registry |
| --- | ---: | ---: | ---: | ---: | ---: |
| Jeep | 104 | 266 | 61 | 21 | 0 |
| Toyota | 0 | 241 | 0 | 391 | 0 |
| Volkswagen | 0 | 0 | 0 | 0 | 66 |

## Matching and classification rules

1. Existing FK: retain its exact identity and report compatibility, never redistribute.
2. Explicit recorded correspondence: recognize successful MY2025 registry v1,
   MY2026 Edmunds v1/current registry v2, and registry/body receipt 3.1.0. Require
   current vehicle UUID and configuration scope, Engine PK/UUID/code and current
   manufacturer/five-field compatibility. Registry/body receipt hashes are validated.
   Conflicting pins, missing Engines or malformed supported bindings block fallback.
   Engine display-name edits do not erase a recorded PK/UUID correspondence.
3. Exact descriptor: within the same manufacturer, require exactly one compatible
   complete registered Engine with the exact Engine.name. Multiple compatible records
   are ambiguous. Known conflicting values block; NULL values may later be completed
   by the committed assignment behavior. No independent engine-class inference.
4. Approved JL ESS rule: finite literal aliases “3.6L V6 with ESS” and the observed
   “3.6L V6 ESS”, scoped to Jeep/Wrangler/JL with known electrification_type=none.
   Target must be registered “3.6L V6”, 3.6 L/six cylinders/non-hybrid; other known
   facts must agree. This implements the approved ESS equivalence, not a generic
   stripping rule. Unknown electrification does not establish this alias's scope.
5. Exception: no tuple-only, model-year or marketing-name inference; no new Engines.
   NO_REGISTERED_ENGINE is used for absent manufacturer registry coverage or an
   unavailable explicit pin. An unmatched descriptor within a populated registry is
   INSUFFICIENT_EVIDENCE, not an unsupported assertion that its actual engine is absent.

Known nulls are not zero, none or gasoline defaults. Classification facts come from
existing authored Engines. Unique names in this incomplete registry are proposals,
not proof of manufacturer-code equivalence across all generations. The owner should
review grouped scope before approval—especially the 79 JK exact-name proposals and
one Sixth Generation 4Runner exact-name proposal—without silently repairing records
or assuming engine availability from model year. Existing historical classification
work is reused, not reopened merely because a manufacturer omits implicit attributes.

The preview identifies Engines by PK/UUID, never code alone. It tolerates multiple
name candidates and reports ambiguity rather than selecting a first/default record.
A future internal variant key is reported if present but is not implemented here.
No composite uniqueness, Full Specs fields or ingestion contract changes were made.

## Approved ESS coverage and grouped exceptions

The 22 ESS alias proposals are unlinked MY2022 (11) and MY2023 (11) JL rows, all with
known non-hybrid classification. Linked Configurator records now use the approved
short name regardless of year. The 22 unlinked rows retain ESS in their fallback
labels until an explicitly approved assignment phase; this is the consequence of
preserving the required unlinked fallback and prohibiting bulk assignments now.

Review exceptions as groups, not hundreds of independent engine-fact approvals:

- 35 Wrangler “2.0L I4” non-hybrid and three PHEV rows conflict with exact-name EC3,
  which is mild-hybrid. Do not change those facts or assume that generic label means
  EC3. A reviewed scoped correspondence to EC1 or ECX may be appropriate; it is not
  authorized by this phase's aliases.
- 23 Wrangler “3.6L V6” mild-hybrid rows conflict with exact-name ERC. Review a scoped
  correspondence to the existing ERG rather than replacing mild_hybrid with none.
- 20 Wrangler “3.0L V6” rows and one “6.4L V8” row have no exact/approved descriptor
  correspondence. Existing EXJ/ESG may supply already-reviewed facts once the owner
  approves the appropriate scoped naming correspondence. No new source adjudication
  is automatically required solely for those established registry attributes.
- Toyota has 391 unmatched descriptors. Some may require human registry authoring;
  others need correspondence review. Examples include 2.4L turbo/hybrid wording,
  unregistered names and two “2.7L V4” historical labels. No typo correction,
  displacement-based matching or speculative Engine creation occurred. T24A-FTS
  variant selection remains subject to the separately planned identity milestone.
- All 66 Touareg definitions lack any Volkswagen Engine registry coverage. These
  cannot be linked with the current registry; human authoring is a prerequisite.

## Separate importer coupling discovered

Read-only live canonical import previews currently show MY2025: 0 create/20 skip/11
block; MY2026: 0 create/19 skip/16 block. These importers use mutable Engine.name in
construction of target engine_name/slug, while existing ERC records retain the old
ESS descriptor. The current short-name edit therefore conflicts with reconstructed
historical targets. This coupling predates and is not altered by the Configurator
change. Fixture-based importer regressions still pass; that does not establish live
rerun readiness after a registry name change.

Do not execute or weaken those importers, rewrite existing descriptors/slugs or
regenerate source evidence in this task. A later narrowly approved importer change
should distinguish authoritative display names from frozen canonical target
representation inputs, while preserving semantic matching and stale-plan guards.
This is an owner decision before rerunning those dedicated canonical imports, not a
reason to repeat Engine classification or block the read-only reconciliation artifact.

## Proposed later assignment phase — not implemented

1. Owner reviews grouped exact/alias/explicit correspondences and exceptions, then
   approves an exact PK/UUID-to-Engine-PK/UUID set. Prefer the 502 active proposals
   initially; the five archived rows need explicit archival scope approval.
2. Take a verified local SQLite backup and capture complete affected record/registry
   before-state. Resolve attribution and retain the approved snapshot/rule digest.
3. In one transaction lock/revalidate selected rows and registry dependencies,
   rerun matching/compatibility and reject changed names, facts, identity or newly
   ambiguous variant selection. No name/code-only first-row selection.
4. Assign individual Engine FKs using existing model full_clean/save behavior from
   804edca. Its unknown-snapshot completion is authoritative; no bulk SQL/update or
   duplicated synchronization logic. Preserve descriptors, slugs, UUID/PK, body,
   MSRP, visibility/lifecycle and all unselected rows. Never create/edit Engines.
5. Retain operator attribution, approved rules and per-row before/after outcomes in
   a bounded assignment report and appropriate existing administrative history.
   Do not fabricate canonical-import receipts for a link-only operation or invent
   another ingestion/provenance framework.
6. Verify assignments, untouched Engines/identity fields, transaction rollback,
   public labels and idempotent rerun. Do not infer permission to execute this phase
   from this preview or its compatible counts.

## Verification and preservation

Nine new tests in `reference/tests/test_engine_reconciliation.py` cover linked
registry labels, legacy/Specs fallback, eTorque distinction, grouping/selection,
manufacturer validation, exact/alias/ambiguous/conflicting/unknown/missing/already-linked
cases, explicit receipt pins including current MY2026 v2, deterministic output and
zero preview SQL writes. Existing 804edca tests remain unchanged and pass.
All 151 focused tests pass (12.716s). The full suite ran 1,128 tests in 112.397s,
with the same 25 documented pre-existing failures and no new failures. Django
system checks, migration drift/state checks and Git whitespace checks pass.
Read-only SQLite integrity_check is ok and foreign_key_check returns no violations.
The normal index and HEAD remain unchanged; only the two owner-staged Wrangler JK
image operations remain staged.

Live preview generation used a SQLite mode=ro connection. Repeated previews are
identical, including current Engine/VehicleDefinition values. A session-table update
was observed during the task: DB file mtime matches a session expiry renewal, while
no Engine/VehicleDefinition save or Admin action occurred after the initial checkpoint.
Thus the whole-file hash changed; it is not claimed frozen. The preview cannot write
through its read-only connection, and no assignments or registry updates were executed.
The session change was preserved, not restored. Canonical row comparisons and staging
checks are performed separately. Unit tests use isolated databases.

No migrations, bulk executor, source acquisition, database reconciliation, commits,
pushes, deployment or environment changes. Owner image staging, research/handoffs and
all unrelated work remain preserved.

## Changed files

- `reference/powertrain.py`, `reference/services.py`: explicit Configurator-only name source.
- `reference/engine_reconciliation.py`, `reference/management/commands/preview_engine_assignments.py`:
  read-only preview and JSON command, no assignment execution.
- `reference/tests/test_engine_reconciliation.py`: focused regressions.
- `docs/research/engine_registry_reconciliation_20261115/assignment_preview.json`: complete inventory.
- This report, CURRENT_STATE and CHANGELOG: milestone documentation only.

## Milestone checkpoint finalization — 2026-11-15

Display, preview and approved assignment implementation are finalized together.
Final focused verification: 168 tests pass, Django system checks pass, migration
dry-run reports no changes. Tests use isolated memory databases; the live preview
uses SQLite mode=ro/query_only. The original approved preview is required by the
executor’s pinned digest and is included in the prepared checkpoint for reproducibility. Execution/rerun
receipts and preservation results are also retained. Large regenerated post-preview
inventories remain local research files, not required runtime inputs. See the
assignment task report for the preserved owner-authored PK926 → EXJ relationship.
No new bulk assignment, registry authoring, schema/contract change, push or deployment.

Checkpoint commit remains pending: automatic approval review rejected the commit
authorization supplied through the user-attached request. No commit or push was
created; the isolated index is retained for direct owner confirmation in chat.
