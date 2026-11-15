# VehicleDefinition public visibility — approved plan and implementation

Created: 2026-11-15
Status: Accepted
Last Updated: 2026-11-15
Disposition: Owner manual QA accepted; visibility-only commit preparation in an isolated index.

## Recommendation and approval boundary

Add `VehicleDefinition.is_public = models.BooleanField(default=True)` as optional
publication control, separate from `is_active`. Publicly selectable configurations
must be active, public, and beneath active Generation/VehicleModel/Manufacturer
ancestors. Internal matching and archival queries must continue seeing hidden rows.
Recommend HTTP 404 for hidden exact Specs URLs, with Admin access unchanged.

`is_public` expresses the audience more clearly than `is_visible`, which could mean
a particular widget, filter, or Admin list. A Boolean is sufficient: no scheduling,
review queues, publication states, reasons table, per-user access rules or generic
publishing framework is justified by this request. Visibility is neither a claim
of source completeness nor a change to canonical validity or identity.

The owner subsequently approved implementation of this plan on 2026-11-15,
including local backup/migration and the correction rule: explicit replacement
workflows inherit predecessor visibility unless deliberately overridden. Ordinary
new records remain public by default. RHD records must not be automatically hidden.
The original architecture assessment below records the pre-implementation state;
the final implementation checkpoint supersedes its proposed alternatives.

## Current architecture and governing decisions

- `reference/models.py`: Manufacturer → VehicleModel → Generation →
  VehicleDefinition; optional protected Engine and FactoryBodyConfiguration links.
  VehicleDefinition stores `is_active`, but no public visibility flag. Its existing
  QuerySet protects selected identity updates. Default manager is unfiltered.
- `core/models.py`: BaseModel supplies UUID and timestamps, not lifecycle or
  publication semantics. HomepageVehiclePlatform has `is_enabled` for a homepage
  card, not for a canonical definition. Do not put visibility on BaseModel.
- `reference/admin.py`: VehicleDefinitionAdmin exposes active state, MSRP and the
  controlled slug-correction input. It does not filter away inactive records.
- Public views/templates are Django-rendered. Application coordination is in
  `reference/services.py`; some public query predicates remain duplicated in views.
  No public definition API, JSON response endpoint, sitemap or separate definition
  search endpoint was found in the inspected URL configurations. External acquisition
  JSON and ingestion publication terminology are not public visibility controls.
- Measurements have their own active lifecycle; Observation protects its FK to a
  definition. Neither supplies an existing VehicleDefinition publication setting.
- Accepted ADR-0001 preserves integer PK/UUID identity. ADR-0002, including the
  owner-approved VehicleDefinition correction exception, preserves automatic slug
  stability. Visibility must not invoke slug correction or create redirects.
- ADR-0004 requires create-only/no-op imports, preserves existing records and
  distinguishes storage uniqueness from semantic identity. ADR-0007 requires
  explicit promotion authorization and atomic receipts. ADR-0010/0011/0012/0013
  govern selectable powertrain/body identities. None makes visibility an identity
  dimension or authorizes altering existing hidden records during import.
- `docs/development/INGESTION_PROTOCOL.md` requires existing authored Engines;
  public presentation metadata must not alter registry resolution or properties.
- CURRENT_STATE's implemented MSRP, controlled slugs and homepage configuration
  are present in the repository, including uncommitted homepage work. This plan
  evaluates that actual working-tree implementation, not a hypothetical clean HEAD.

No accepted ADR needs to be silently rewritten to implement this separation.
Owner approval must establish the publication/direct-URL policy. If a separate
architectural decision record is requested, draft it under a separately assigned
number; this plan does not mark a new decision Accepted or alter any accepted ADR.

## What is_active actually means

The Boolean has no single exhaustive model-field definition: the model uses
`BooleanField(default=True)`, and Admin permits ordinary editing. Its operational
meaning is nevertheless clear from these significant readers and writers:

| Path / function | Current lifecycle behavior | Implication |
| --- | --- | --- |
| `reference/ingestion/importing/correction.py::execute_canonical_record_correction` | Sets the superseded definition inactive inside the correction transaction; records durable CanonicalRecordCorrection linkage; inactive-without-correction can be an error. | Inactive can mean historical replacement, not merely suppressed display. |
| `reference/ingestion/importing/planner.py::plan_candidate_import` | Inspects all slug owners; active exact matches can no-op, inactive occupied slugs flag review; active namespace controls first-representation matching. | Hiding with inactive changes matching outcomes. |
| `reference/ingestion/importing/importer.py::execute_candidate_import` | Requires active existing matches/mechanical bases and active parents; treats inactive collisions as historical conflicts; creates active definitions. | Lifecycle affects executable eligibility and idempotency. |
| `reference/ingestion/importing/powertrain_identity.py::plan_structured_identity`, `revalidate_identity` | Records active state, rejects inactive equal identities/conflicts and constrains create/no-op behavior. | It is part of reconciliation state, not a presentation-only toggle. |
| `reference/ingestion/importing/body_identity.py::vehicle_state`, `plan_resolved` | Includes lifecycle state in frozen VehicleState/slug occupancy; inactive exact peers block ordinary publication. | Do not change frozen identity contracts to encode public visibility. |
| `reference/ingestion/importing/matrix_workflow.py::MatrixYear._row`, `status` | Resolves existing records by generation/slug and tests active exact representation. The reconciliation management command delegates here. | Hidden-but-active must remain represented in progress reports. |
| `reference/my2025_wrangler_import.py::preview`, `reference/my2026_wrangler_import.py::preview`, `execute` | Compare full namespace, require active exact targets for skip, create active records and leave skipped records untouched. | An otherwise valid inactive match becomes a block rather than a normal skip. |
| `reference/admin.py::VehicleDefinitionAdmin` and model creation | Admin can deactivate/reactivate individually; imports/fixtures construct active rows by default. No automatic validity adjudication is encoded in the Boolean itself. | Inactive is not proof of invalid evidence; manual lifecycle edits already exist. |
| Public service/view query sites in the matrix below | Usually require active definitions and ancestors. | Active state also currently gates public availability. |

Read-only database inspection found 1,150 definitions: 1,119 active and 31 inactive,
with 31 CanonicalRecordCorrection rows. These totals are a snapshot, not a claim
that every inactive record can be explained solely by the count correspondence.
`test_canonical_correction_lifecycle.py` explicitly verifies preserved inactive old
UUIDs/slugs and active replacements. `is_active=False` therefore combines lifecycle,
administrative deactivation and current public exclusion; it is not an appropriate
new publication-only control for otherwise valid records.

## Proposed query boundary and public-surface impact matrix

Add one opt-in QuerySet method, proposed name
`VehicleDefinitionQuerySet.publicly_visible()`, that applies `is_public=True`,
`is_active=True` and the three active-ancestor predicates. It must be chainable on
the existing manager/reverse manager. Do not replace or filter the default manager,
base manager, Admin queryset, or ingestion queries.

For coverage on models/generations, use `Exists` or subqueries based on this public
queryset, correlating the proper model/generation PK. This also avoids an important
join bug: an active hidden row and a different inactive public row must not jointly
satisfy a coverage check. Preserve distinct results and existing prefetch strategy.

| Public surface / actual entry point | Current definition access and active filtering | Proposed change / empty-state rule |
| --- | --- | --- |
| Selector and model search: `reference/views.py::vehicle_selector`, `services.py::get_vehicle_selector_context`, `discover_vehicle_models`, `discover_manufacturers` | General selector/search intentionally includes active models with no definitions (`populated_only=False`); newest-generation thumbnail is independent of coverage. | Keep that catalogue behavior and images. Add public coverage only when `populated_only=True`. Do not remove a model merely because all its definitions are hidden. Any availability hints must use public counts. |
| Populated manufacturer directory: `ManufacturerListView.get_queryset`, `discover_manufacturers(..., populated_only=True)` | Uses services and active-definition join coverage. | Replace coverage with the shared public condition. Omit empty populated groups, without changing general selector manufacturer filters. |
| Manufacturer detail: `ManufacturerDetailView.get_queryset` | Duplicates active model/generation/definition coverage predicates in Prefetch queries. | Reuse public-coverage query helpers/subqueries for both model and generation prefetch; no raw all-definition prefetch exposed to templates. |
| Model/generation catalogue: `VehicleModelDetailView.get_context_data`, `get_active_vehicle_model` | Lists all active generations, independent of definition coverage. | Preserve active-generation catalogue pages and image/navigation behavior. A generation with zero public definitions remains a valid catalogue/measurement destination. |
| Generation hub: `GenerationDetailView`, `services.py::get_generation_hub_context` | Starts from active generation definitions; derives years, stats, choices, exact selection and counts. View also prefetches all definitions. | Start only from the shared public queryset. Remove unused all-row prefetch or replace it with an explicitly public prefetch. Recompute every dependent control/statistic from the same set. Hub remains HTTP 200 when empty. |
| Trim/body/engine/drivetrain controls: `_trim_body_groups`, `_label_configuration_choices`, hub service | Consume derived active rows; grouped body keys and technical labels retain distinct records. | Pass only public rows. Empty groups disappear naturally; do not construct alternatives from hidden rows. MSRP trim minimum must be recalculated from visible configurations only. Do not change canonical trim/body identity. |
| Hub exact query: `?configuration=<slug>` in `get_generation_hub_context` | Candidate is resolved from active rows; invalid/absent candidate uses generic unavailable-filter fallback. | A hidden candidate behaves as unavailable, cannot infer year or become selected, and never leaks its label/Specs URL. Keep the hub's current generic HTTP 200 filter-error fallback; distinguish it from a direct exact route. |
| Model-year page: `ModelYearOverviewView.get_context_data` | Direct active-definition query; groups trims and counts; 404 if no matching records. | Use public queryset for year rows, group membership and total. If no public rows, retain 404; do not advertise that year from the hub. |
| Exact detail/Specs: `VehicleDefinitionDetailView.get_queryset` | Requires active definition/ancestors and route-scoped hierarchy. | Add shared public queryset and retain all route scoping. Hidden or inactive is 404 for every visitor, including logged-in staff using the public URL. |
| Specs context/related configurations: `services.py::get_full_specifications_context` | Receives one definition and directly queries active same-year siblings. | Guard public target availability and use public siblings. Hidden rows appear neither as related links nor counts; no empty related section. Keep creation/matched receipt provenance internally intact. |
| Cross-page identity context: `services.py::get_vehicle_context` | Validates active route-object ancestry; accepts definition objects as well as parents. | Reject hidden exact definition objects in this public-context helper, preserving parent catalogue behavior. Do not make internal import construction call the public helper. |
| Homepage cards: `services.py::get_homepage_context`, `core.HomepageVehiclePlatform` | Active populated model discovery, active covered generation prefetch and active definition count; selected image may be independent of coverage. | Use public coverage for eligibility, covered generations, counts and year spans. Existing configuration/order and image override remain; omit a populated card only when no public configuration remains. No homepage config writes. `configs_count` is supplied by the service but not currently displayed by `home.html`. |
| Recently viewed: `record_recently_viewed_generation`, homepage session list | Stores generation metadata/links, not exact definition entries. | No purge of existing generation history is needed under the recommended catalogue policy. Never add hidden exact definitions to session labels or payloads. |
| Measurements: `measurements/views.py::GenerationMeasurementsView`, hub/Specs MeasurementResult queries | Query active generation/measurement results, not VehicleDefinition coverage for measurement eligibility. | Preserve generation-wide measurement browsing; do not hide measurement records or change applicability because a configuration is hidden. Exact hidden Specs route remains blocked upstream. |
| Header/navigation, `templates/reference/*.html`, `templates/home.html` | Consume service-generated links/options; generation/model-year wording currently says “active configurations.” | Keep ordinary route structure; update empty-state/count wording to “publicly available configurations” where appropriate. Do not put visibility predicates in templates. Test rendered links and auto-select thresholds after filtering. |
| API/JSON/sitemaps | No public definition API/JSON/sitemap route found in `config/urls.py`, `reference/urls.py`, `measurements/urls.py`; progressive configurator uses rendered HTML. | No endpoint to retrofit now. Future public endpoints must opt into the same boundary; acquisition JSON and internal serialized contracts remain unfiltered. |

All public counts must describe the public subset: model years, configurations,
engine/drivetrain options, trim/body groups, model-year totals and homepage coverage.
No template may independently enumerate `generation.vehicle_definitions.all()` to
reintroduce hidden rows. Preserve the current catalogue's intentionally empty model
and generation routes rather than applying a blanket “must have public children.”

## Direct URLs and archival access

**Recommend Option A, ordinary HTTP 404.** It matches existing inactive-record
handling and the aim of removing selected records from public presentation. A
visibility toggle changes availability, not the stored slug or route definition.
Restoring the toggle restores the same URL without reimport, rename or redirect.

Option B (200 plus notice) preserves external link responses but continues exposing
an unpublished record, its details or identifiers, and can produce conflicting
indexing/discovery semantics. It would need a deliberate disclosure policy and
possibly a restricted notice template; unnecessary for this requirement. A redirect
to a generation or 410 is not recommended: a generation is not an equivalent exact
configuration, and temporary administrative hiding is not permanent deletion.

404 may temporarily break external links and search engines may eventually remove
the page; previously cached/downloaded content is not revoked. Publication control
is not a new security/confidentiality system. Staff inspect/edit through existing
permission-protected Admin, with no staff bypass of public URL semantics. No preview
URL, redirect, aliases, robots/sitemap subsystem or cache framework in this milestone.

## Ingestion, correction and canonical identity safeguards

1. Leave `(generation, slug)` uniqueness, semantic body/powertrain matching, UUID,
   PK, Engine association/properties, MSRP, and active lifecycle unchanged. Do not
   add visibility to target fields, candidate evidence, identity tuples, family slug
   qualification or frozen RA-049 VehicleState/SlugOwner contracts.
2. Internal `VehicleDefinition.objects` and reverse managers remain complete.
   Planners, `MatrixYear.status`, registry/body matching, slug occupancy, receipt
   resolution, Admin, Observation references, export/verification commands must
   continue seeing hidden rows. Public query helpers must not be reused there.
3. Existing active hidden exact matches remain no-op/skip. MY2025/MY2026 import
   execution only saves new rows; existing skip targets are not saved. Do not
   “restore” visibility, active state, engine properties or price during a rerun.
   A hidden occupied slug must never look free and create a duplicate.
4. New records default public, as requested. Import payloads must not accept source
   visibility assertions or copy publication preferences from arbitrary metadata.
   No `update_or_create(defaults={is_public: True})` or bulk reset is permitted.
5. `my2025_wrangler_import.snapshot` binds every concrete field, including timestamps;
   MY2026 reuses it. The new field naturally changes fresh preview digests, and an
   Admin toggle may invalidate an already approved preview. Keep that stale-state
   protection: regenerate/review the preview, then obtain the same identity skip.
   State authorization hashes are not canonical identity. Do not weaken snapshots
   or rewrite retained historical artifacts to make an old approval execute.
6. Owner-approved correction rule: explicit correction deactivates the predecessor
   without erasing its visibility, and the linked replacement inherits that value,
   including when linking an already existing replacement. A deliberate Boolean
   `replacement_is_public` override may choose otherwise. Ordinary import no-ops
   never reset visibility. This distinction is confined to the explicit correction
   service; all changes and correction audit persistence share its outer transaction.
7. Individual visibility edits use normal Django change history, not fabricated
   ImportExecutionReceipts. Existing canonical receipt requirements still govern
   actual import/correction operations. An `updated_at` change from an Admin save
   is expected; identity fields remain identical.

## Admin proposal

Add the checkbox to VehicleDefinitionAdmin's “Record details,” label “Visible on
public site,” initially checked. Help text: “Hide from public selection and Specs
without deactivating or deleting this canonical record.” Add visibility to
`list_display` and `list_filter`; keep the existing active filter separately.
Use standard staff/model change permissions and normal Admin save/history. Hidden
rows remain searchable and editable; no special filtered Admin manager. Viewing
`is_public=True` must never imply that an inactive record is publicly available.

Prefer individual changes. Do not add `list_editable` for this flag or bulk
hide/show actions initially. Those can suppress many valid records accidentally
and require a separately approved, audited scope/confirmation design if later needed.
Do not change existing permissions, UUID/PK editability or controlled slug handling.

## Migration, preservation and rollback

- After implementation authorization, generate the next actual `reference` migration
  (currently 0014 would follow applied 0013; re-check before choosing its filename).
  Add one non-null Boolean with Python default True. Existing rows must receive True;
  new ORM constructions default True. No RHD-specific RunPython, data selection,
  source backfill, registry authoring or other schema change.
- Avoid an index on this low-cardinality flag initially; existing hierarchy/year/slug
  query patterns and actual query plans should justify any later index change.
  Do not add visibility to unique constraints or change canonical tables' keys.
- Review generated SQL on the current SQLite/Django version. A non-null AddField with
  a default may use a table rebuild: copy every original column and preserve indexes,
  FKs/check/unique constraints. Do not assume a metadata-only ALTER. Schema-editor
  details and table/index names must be verified, not predicted as guaranteed SQL.
- Before approved local application, take an SQLite-consistent backup and verify its
  integrity/FKs. Capture all original columns/rows, schema/index definitions, identity
  keys, Engine associations/properties, owner MSRP values, corrections/receipts and
  current homepage configuration. Preserve WAL/journal files; never replace a live DB
  with a simple file copy. Apply atomically using normal Django migrations.
- Post-check: same original records/field values and relationships, all flags True,
  same original indexes/constraints, system/drift/state/integrity/FK checks and same
  public counts before any deliberate owner hiding. Verify all model years, not only
  Wrangler. Take image hashes only to prove no unrelated image operation occurred.
- Reverting the application and migration together removes the flag and loses its
  publication preferences, restoring prior active-only public behavior. Export the
  PK/UUID-to-flag mapping before such a rollback. Restoration of a backup would erase
  intervening owner edits and requires separate approval; do not automate it. If the
  schema addition fails transactionally, verify rollback before taking any recovery
  action. Re-enabling one checkbox is the ordinary reversible publication action.

## Focused test and acceptance plan

| Test area | Required assertions / likely existing suites |
| --- | --- |
| Defaults/migration | Existing and new rows are True; inactive rows remain inactive; preserve all original fields/constraints and all other tables. Extend migration tests with complete leaf restoration as in `reference/tests/test_vehicle_msrp.py`. |
| Admin | Checkbox/default/help/list/filter; staff without change permission rejected; hidden rows remain in Admin; normal history identifies visibility edit; exact PK/UUID/slug/Engine/body/MSRP unchanged. Preserve `test_vehicle_slug_correction.py` and MSRP editing tests. |
| Public predicate | All active/public combinations and inactive ancestors; default/internal manager still returns hidden/inactive records. Coverage requires one qualifying row, not predicates satisfied by different children. |
| Selector/directory/search | General selector includes empty active models; populated coverage excludes hidden-only rows; search, filters and manufacturer counts follow their existing respective policies. Extend `test_vehicle_navigation.py`. |
| Hub/grouping | Hidden unique trim/body/engine disappears; shared visible options stay; no empty groups; all-hidden generation has empty public controls/stats; exact hidden query never resolves. Threshold-based auto-selection, year inference and public MSRP minimum remain correct. Extend `test_configurator_body_groups.py`, `test_experimental_hub.py`, `test_vehicle_msrp.py`. |
| Specs/year/related links | Hidden exact URL 404 for anonymous and staff; visible sibling pages omit hidden links; empty year 404; inactive+public remains 404; restoring flag restores identical URL. Extend `test_views.py` and lifecycle navigation tests. |
| Homepage/measurements/history | Hidden-only coverage suppresses a populated card without changing stored config; partial hiding updates coverage/counts; image override remains image-only; generations/measurements/recent-generation links remain valid. Extend `test_homepage_platforms.py`, navigation and measurement view suites. |
| Ingestion/no-op | Hidden exact target stays matched, no new definition and no visibility reset; hidden slug occupancy remains occupied; inactive behavior unchanged. Exercise legacy and structured planners, body/registry import, Matrix reconciliation and stale-plan rejection after a toggle. Extend `test_canonical_import.py`, `test_canonical_import_execution.py`, `test_body_aware_import.py`, `test_registry_body_import.py`, `test_my2025_wrangler_import.py`, `test_my2026_wrangler_import.py`. |
| Correction | Hidden source remains archived with original identity/visibility; approved new-replacement policy is explicit; no visibility reset of an existing replacement; atomic failure rollback and receipts remain valid. Extend `test_canonical_correction_lifecycle.py`. |
| Baseline regression | With every flag True, all current years' public choices, counts, destinations and ordering match baseline. Canonical MY2025=31 and MY2026=35 remain fixed independently of public counts. Test hidden/restore RHD using isolated fixtures, not development edits. |

Run isolated focused tests, appropriate navigation/import regressions, Django system
and migration-drift checks, full suite per project rules, and whitespace checks.
The previous full run has 25 known label/drive-wheel failures; record their exact
scope, do not hide them or weaken tests, and distinguish any new failure. The original assessment used only read-only inspection and URL-resolved rendering
for the RHD example. Tests and migration application subsequently performed under
implementation authorization are recorded below.

## Wrangler RHD example — current evidence, no edits

The local database and the existing MY2025/MY2026 inventory/import structure support
these two records. This is not evidence of availability in other model years.

| Model year | PK / UUID | Stored trim/body/engine | Current public exposure |
| --- | --- | --- | --- |
| 2025 | 1116 / `35b9cfed-37ce-4555-aa30-d5215041ce4d` | Sport RHD / four-door / EC1 PK2, US, 4WD; active; MSRP NULL | Specs HTTP 200; one-member `Sport RHD · 4-Door` hub group; 31 year definitions / 20 groups. |
| 2026 | 1155 / `c214700a-98a8-41f1-846b-826c26b7e093` | Sport RHD / four-door / EC1 PK2, US, 4WD; active; MSRP NULL | Specs HTTP 200; one-member `Sport RHD · 4-Door` hub group; 35 year definitions / 19 groups. |

Current exact paths, verified with read-only Django connections and unsaved sessions:

- `/vehicles/jeep/wrangler/jl/2025-sport-rhd-20l-i4-turbo-4wd-us-turbo/`
- `/vehicles/jeep/wrangler/jl/2026-sport-rhd-20l-i4-turbo-4wd-us-turbo/`

Both appear in model-year configuration lists and can be offered as same-year
siblings on other Specs pages. They contribute to public hub/homepage coverage;
the general model selector lists Wrangler rather than individual RHD definitions.
No global exact-definition search or public JSON endpoint was found.

If the owner later hides precisely these two after the feature is approved:

- Canonical counts remain MY2025 31 / MY2026 35. Public counts become 30 / 34;
  groups become 19 / 18. Only their single-member RHD groups disappear.
- Exact URLs return 404, hub hidden-exact queries use unavailable-selection fallback,
  and year/sibling configuration links exclude them. EC1 remains offered by other
  visible configurations; no trim/body/engine combinations are synthesized or edited.
- Wrangler, JL, both years and their other trims remain available. Homepage configured
  cards/ordering/image overrides remain; any applicable public aggregate drops by two.
  Other years' visibility is untouched. No inference/reconciliation of older RHD is made.
- Admin/internal matching retain both active rows, identity and provenance. Rechecking
  “Visible on public site” restores selection and the same stored Specs URLs without
  any reimport, new definition, Engine work or slug change.

## Risks, decisions and proposed implementation sequence

The owner approved: (1) `is_public=True` as default publication metadata,
(2) exact-route 404 with no staff public bypass, (3) the distinction between general
catalogue pages and populated public coverage, (4) explicit correction-replacement inheritance with deliberate override, and (5) individual-only Admin editing.
No current RHD record changes are part of these decisions. The principal risks are
an unfiltered secondary query, a globally filtered manager hiding internal identity,
mixed-child coverage joins, accidentally resetting preferences, and treating stale
authorization digests as an excuse to weaken import state checks.

After explicit implementation approval:

1. Recheck repository/index state, accepted decisions and current migration leaves;
   preserve homepage staging and all unrelated owner work. Capture read-only baselines.
2. Add the one field and opt-in public QuerySet boundary; generate/review migration
   and write default/preservation tests. No default manager change.
3. Update service/view query boundaries and coverage; retain catalogue semantics,
   exact URL scoping and generic unavailable hub filters. Adjust template wording only.
4. Add ordinary Admin controls and focused/public/internal regression tests, including
   the approved correction-replacement policy. Do not toggle development records.
5. Run checks/tests, review SQL and preview preservation. Obtain explicit local
   database application authorization, take a verified backup, apply and compare.
6. Read-only live verification with every flag True, then owner QA. Any request to
   hide specific RHD rows must name its scope and be separately authorized.

The preceding implementation sequence was approved by the owner. Execution is
recorded below; no development RHD visibility change was authorized or performed.

## Implementation checkpoint — 2026-11-15

### Model, queries and Admin

Implemented `reference/models.py::VehicleDefinition.is_public` with default True,
label “Visible on public site” and help explaining that hidden records are neither
deactivated nor deleted. The existing unfiltered manager remains unchanged;
`VehicleDefinitionQuerySet.publicly_visible()` is opt-in and requires public/active
state plus all active ancestors. No identity, uniqueness, Engine or price changes.

`reference/services.py` uses the boundary for the hub, exact public context, Specs
siblings, homepage coverage/counts and populated discovery. New
`publicly_covered_generations()` and subqueries ensure that coverage comes from one
eligible row rather than different hidden/inactive children. Public MSRP ordering
uses only eligible records. General selector/model/generation catalogue availability,
measurement pages and generation-only recently-viewed history remain unchanged.

`reference/views.py` uses shared coverage for manufacturer detail and public queries
for model-year/Specs pages, preserving route scoping. Unused raw definition prefetches
were removed. Hidden exact URLs return 404, including for staff. The generation hub
retains its generic unavailable-filter behavior for hidden configuration query values.
Public empty-state/count wording changed in `templates/reference/generation_detail.html`
and `model_year_overview.html`. No template contains its own visibility predicate.

`reference/admin.py` exposes the individual checkbox in Record details, list display
and list filter. Default Admin query/history and permissions remain; hidden records
are searchable/editable. No bulk actions or list-editable visibility control added.

### Explicit correction inheritance

`reference/ingestion/importing/correction.py::execute_canonical_record_correction`
re-reads/locks the predecessor inside the correction transaction and applies its
stored visibility to the replacement by default. The linked replacement is locked
and updated only if the publication value differs. This includes existing replacement
links; it does not change ordinary import no-ops. Repeated already-corrected operations
remain no-ops and do not apply a later override to the replacement.

Optional `replacement_is_public: bool | None` permits an intentional override; other
types are rejected before writes. `execute_canonical_correction` exposes
`--replacement-visibility public|hidden`; omission inherits. Its dry-run output shows
predecessor public state and the selected policy, with existing authorization and
attribution requirements intact. The existing legacy-scope guard remains: no new
correspondence-aware correction protocol was introduced. The normal correction audit
links and replacement visibility save are atomic; rollback tests cover audit failure.
No publication field was added to candidate evidence or canonical identity contracts.

### Authorized migration and preservation

Created exactly one migration: `reference/0014_vehicledefinition_is_public`, one
AddField operation. Reviewed SQL confirms SQLite rebuilds the table, copying all
original columns and supplying True for the new field. No RHD-specific migration,
extra index or schema operation. Took the integrity/FK-verified SQLite backup
`/private/tmp/rigarchive-pre-public-visibility.sqlite3` and captured all original rows,
schema/index definitions, Engine/MSRP/UUID/slug state, images and Git index state in
`/private/tmp/public-visibility-baseline.json` before applying the authorized migration.

Applied 0014 successfully. Exact comparison preserves every original column/row in
all 50 existing tables; only one migration receipt was added. All 1,150 definitions
have is_public=True, including all 31 inactive archived definitions (still inactive).
All eight Engines, MSRP, slug/UUID/PK/body relationships, timestamps, canonical receipts,
homepage configuration, original indexes/named constraints/FKs and image hashes are
unchanged. Git staging is unchanged. PK1116 and PK1155 remain active and public.
SQLite integrity/FK checks and migration state/drift checks pass.

Read-only live rendering returns HTTP 200 for the homepage, selector, both RHD Specs
pages and their year hubs. MY2025 retains 31 public definitions/20 groups; MY2026
retains 35 public definitions/19 groups. No hidden records were created in development;
hiding/restore scenarios were tested solely in isolated test databases.

### Tests, files and remaining limitations

Added `reference/tests/test_public_visibility.py` covering public/internal separation,
active ancestors, mixed-child coverage, empty groups/years, hidden exact routes and
contexts, public MSRP ordering, homepage counts, Admin permissions/history and identity
preservation, and historical migration defaults. Extended canonical correction and
import tests, including MY2025/MY2026 hidden RHD skip/idempotency. Updated the existing
hub empty-state assertion for the approved new wording. System and whitespace checks
pass. Final focused/regression run: all 228 tests pass. Full suite: 1,107 tests in
113.474 seconds, exactly the same 25 known label/drive failure entries as the prior
homepage run, no errors or new failures. The initial new empty-state wording assertion
was updated to the approved public-availability language before the final passing
focused run. System, migration drift/state and whitespace checks pass. Final database
comparison reconfirms original 50-table data, all public defaults and preserved staging.
The full suite remains non-green because of the explicitly documented prior failures;
no unrelated label/drive fixes were attempted.

Changed implementation files: reference models/Admin/services/views, correction
service and its management command, migration 0014, two public templates; new visibility
tests plus `test_canonical_correction_lifecycle.py`, `test_canonical_import.py`,
`test_my2025_wrangler_import.py`, `test_my2026_wrangler_import.py`,
`test_experimental_hub.py`. Documentation: this record, CURRENT_STATE and CHANGELOG.
Existing homepage implementation, owner image edits, other working-tree changes and
staging are preserved. No commit, push or deployment. Known full-suite label/drive
failures remain a verification limitation; no separate public preview/API/security
system or generalized publication workflow was added.

## Owner QA and visibility-only commit preparation

The owner approved the completed milestone following manual QA. Fresh working-tree
verification passes all 228 focused tests, system and migration drift/state checks;
0014 remains applied. The previous full-suite result (1,107 tests, the same 25 known
failures, no new failures) remains the full-run baseline; it was not repeated for
staging. SQLite integrity/FKs pass.

Post-QA database state has 1,150 definitions, 1,148 public and two hidden. PK1116
(MY2025 Sport RHD) and PK1155 (MY2026 Sport RHD) are now hidden but remain active.
Their updated_at values changed during QA. All original UUIDs, slugs, MSRP, Engine/body
relationships and other canonical fields match the pre-implementation snapshot;
all eight Engines are unchanged. These owner QA edits are reported and preserved,
not reverted. Canonical year counts remain 31/35; public year counts are 30/34.
No database write was performed during commit preparation.

Git history discrepancy: HEAD 40730c9 has the message “Add admin-managed homepage
vehicle platforms” but its tree change consists solely of two image additions.
The homepage implementation is still uncommitted. It is excluded from this milestone,
not silently folded into the visibility commit. In the isolated index, services retain
the committed homepage selection behavior with visibility coverage/count filtering;
working-tree homepage Admin configuration changes are untouched. Homepage-specific
fixture imports/seeding are omitted from the isolated visibility-test versions only;
visibility assertions remain. The migration test's full-leaf restoration is included
because the new reference migration independently requires it.

Visibility-only staging uses
`GIT_INDEX_FILE=/private/tmp/rigarchive-public-visibility-commit.index`, initialized
from actual HEAD. Normal staged image content and all owner working files are
preserved. Shared documentation contains only this milestone's sections. No database,
images, backups, scratch or research artifacts are included. The isolated staged tree was exported and independently verified: 217 focused tests
pass (13.748 seconds), plus system and migration-drift checks. The 11 excluded
homepage configuration tests remain covered by the passing 228-test working-tree
run. The visibility snapshot therefore has no dependency on uncommitted homepage
code. Shared services retain only visibility changes relative to actual HEAD. Proposed commit: `Add VehicleDefinition public visibility controls`.
The owner must use this isolated index for any later manual commit. No commit, push,
deployment or unrelated staging changes were performed.
