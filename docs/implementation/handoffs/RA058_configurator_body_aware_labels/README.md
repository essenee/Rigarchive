# RA-058 — factory body-aware configurator labels

Created: 2026-11-14
Status: Proposed
Disposition: **Mandatory MY2024 Wrangler behavior implemented and verified;
ready for owner review. No operational records changed.**

## Root cause and exact changes

`reference/services.py` grouped the Trim column by `trim_name` alone. Its compact
Configuration formatter tried to distinguish the resulting otherwise-identical
records by appending market and then canonical slug. The template rendered raw
trim strings, so it could not express a trim/body group.

Changed:

- `reference/services.py`: actual-row trim/body groups, public body-dimension labels,
  exact membership filtering and compact technical Configuration labels. Body and
  Engine associations are fetched with the query. Existing year, exact-selection,
  invalid-filter and sibling-choice behavior remain supported.
- `templates/reference/generation_detail.html`: separate group key/label in the
  existing Trim column; public-attribute ambiguity notice; no added selection step.
- `reference/tests/test_configurator_body_groups.py`: new focused Wrangler group,
  four-option Willys, rendered Specs-link, exact-selection, no-expansion and blank-
  trim tests.
- `reference/tests/test_experimental_hub.py`: existing market/slug-fallback tests
  now require explicit ambiguity without exposing those values; missing-trim text
  uses a neutral presentation fallback.
- `CURRENT_STATE.md` and `CHANGELOG.md`: RA-058-only progress entries, retaining
  all earlier uncommitted content.

No model, importer, canonical identity, source, public slug, UUID, receipt or
JavaScript change. This is request-local presentation/query behavior.

## Grouping and labels

Within the selected Generation/model and year, only active published
VehicleDefinitions supply groups. Group membership is the exact canonical trim
(including the existing empty-string representation) plus the actual body FK.
No body combination is synthesized. Opaque body-specific query keys select exact
members; those keys are never rendered as choice labels. Historical bodyless trim
query keys, blank-trim selection and configuration-only deep links still work.

Labels use the populated body attributes that vary within the trim; otherwise they
use applicable attributes varying across the year. For the Wrangler this produces
`Willys · 2-Door`, `Willys · 4-Door`, equivalent Sport/Sport S/Rubicon/Rubicon X
choices, and applicable four-door-only groups without changing stored trim names.
Wheelbase, length, roof, style, doors, side-door arrangement and the paired public
manufacturer body code/namespace can be rendered from the existing sparse tuple.
Missing values are described as unspecified where needed. Attributes that do not
help distinguish available groups are not automatically repeated.

Configuration labels primarily use the existing short Engine formatter. Within a
selected trim/body group they omit trim and body repetition. Drive-only alternatives
retain compact drive labels; collisions can add differing drive, manufacturer Engine
code, aspiration, fuel or electrification descriptors where available. Market,
canonical slug and internal identifiers are never fallback text. If public attributes
still cannot distinguish records (for example, otherwise identical market-only
records), all choices and Specs links remain, with an explicit ambiguity warning.
No canonical record is silently removed or merged.

Specs and exact-configuration URLs retain their existing destinations. Slugs remain
in URLs as locators, not as user-facing Configuration text. The three columns remain
Model Year → Trim → Configuration; progressive enhancement still follows the
server-generated links and replaces the same panel.

## Published MY2024 Wrangler QA

Read-only URL-resolved Django views and their rendered templates were exercised
against the actual 31 published MY2024 JL rows. RequestFactory used an ephemeral
in-memory session rather than session-persisting middleware, avoiding operational
session writes. There are **20 actual trim/body choices** in MY2024.

| Trim-column choice | Published PKs | Configuration labels | Specs and exact selection |
| --- | --- | --- | --- |
| Willys · 2-Door | 1073, 1074 | 2.0L I4 · Turbocharged; 3.6L V6 ESS | Both correct, HTTP 200 |
| Willys · 4-Door | 1083, 1084 | 2.0L I4 · Turbocharged; 3.6L V6 ESS | Both correct, HTTP 200 |

Each choice returns exactly its two body-correct records. All four Specs links resolve
to the intended canonical VehicleDefinition, and all four exact-selection links select
the intended PK. Configuration link text contains no market/country, slug or redundant
door label. Stored Willys trim values remain `Willys`.
Detailed read-only results: [data/published_willys_qa.json](data/published_willys_qa.json).
This verifies actual view/template responses, not a screenshot-based browser session.

## Focused verification

**51 tests passed**: `test_configurator_body_groups` and `test_experimental_hub`.
Two initial regression failures identified historical default blank-trim ordering
and drive-only labels; both behaviors were preserved and the final focused run passed.
Bodyless historical configurators, separate engine choices, exact Specs routes,
unknown/inactive/cross-generation filters and blank trim selection remain covered.

Django system checks passed; migration-drift check reported no changes. Git whitespace
checks passed. No full suite was run. Attempted the existing JavaScript test command,
but `node` is unavailable; no JavaScript changed. No installation was attempted.
Used the previously authorized `.venv/bin/python` environment; prescribed
`venv/py313/bin/python` remains absent.

## Optional trim and future limitations

The domain permits a VehicleDefinition with **no manufacturer-marketed trim**:
the existing `trim_name` field already has `blank=True` and stores `""`; database
NULL is not supported. This task supports that existing representation without a
migration. Its Trim-column label uses body attributes; with neither trim nor body
information, neutral `Factory configuration` keeps the choice usable without
inventing Base, Standard or No Trim as marketed trim names.

The current bounded MY2024 3.1.0 importer still requires nonempty `TargetFields.trim_name`
(`Text`) and its retained reviewed trim inventory. Generic trimless ingestion therefore
needs a separately approved contract/profile and absence-of-trim evidence convention,
with identity/uniqueness and historical compatibility checks. No schema change is
needed merely to store the already-supported empty string; NULL semantics or any
contract expansion remain outside this task.

Generic body-dimension formatting is implemented, but representative van catalogs
were not ingested or fully validated. Sparse/missing descriptions can leave genuine
public-label ambiguity; the configurator reports it rather than adding internal
identifiers. Friendly manufacturer-specific designation vocabularies may need later
presentation refinement without interpreting tokens as measurements.

The intended future hierarchy is preserved: cargo, passenger and applicable
platform/chassis variants belong at VehicleModel level; within those models body
wheelbase/length/roof and marketed trim where applicable form groups. ProMaster may
have marketed trims; Sprinter may not. No van model, record, hierarchy change or
van-specific schema was introduced.

## Operational preservation

Database SHA-256 before and after:
`f1cf9de2f448711b2b445b959a0d5145a9cba4247409698b56cf488e194a755c`.
No operational vehicle, Engine, body, trim, slug, UUID, association, Approval1 or receipt
was created or modified. Prior ingestion/naming work and all unrelated working changes
are preserved. Nothing was staged, committed or pushed. Await owner review.
