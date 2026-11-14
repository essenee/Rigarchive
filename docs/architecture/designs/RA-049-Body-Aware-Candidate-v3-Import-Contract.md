# RA-049 — Body-Aware Candidate v3 Import Contract

Created: 2026-11-13
Last Updated: 2026-11-13
Status: Approved
Implementation: Accepted by the Project Owner on 2026-11-13

The Project Owner approved this exact contract and its §11 runtime clarification
on 2026-11-13 and authorized implementation and isolated verification only.
The Project Owner subsequently accepted the implementation, including all final
review corrections and 27 regressions, and authorized one reviewed local RA-049
commit on 2026-11-13. Operational migration, canonical publication, historical
assignments and push remain unauthorized.
RA-048 was accepted and committed as `29ff1b4a42c99c8ecf9c75b77cd5b2c0dfce706f`.
ADR-0013, RA-045, RA-046 and accepted RA-047 remain unchanged. The approval explicitly includes the scoped RA-046 clarification in §11.

## 1. Problem, scope and decisions

The existing slug builder and engine peer proof omit body. Thirty-one active MY2024
JL proposals collapse to 21 slugs, including ten two-door/four-door collision pairs.
Appending a suffix alone leaves semantic merging possible. Use an explicitly
versioned v3 import path, with exact body identity and readable new-record slugs.

Initial executable profile is `my2024-wrangler-jl-consumer/1`: Generation JL, model
Wrangler (4xe remains Wrangler), MY2024 US consumer offerings, complete reviewed
five-field powertrain, null/omitted FactorySeries and established door evidence.
The input release contains exactly the retained 31 active candidates; quarantine,
RHD and speculative offerings are excluded. Those retained 2.1.0 documents are
historical inputs, not executable v3 candidates. Produce new v3 artifacts only in a
separately authorized implementation/preparation task, preserving the originals.

Use the seven approved body dimension groups and eight RA-048 columns. Initial
plans **reuse existing, separately authorized body rows only**. No parent creation,
body update or historical FK assignment occurs in this executor. The two supported
JL door tuples must exist operationally before executable planning; absence gives
`BODY_PARENT_UNAVAILABLE`, not fabricated UUIDs or an implicit creation approval.
No global Scope registry, binding table, additional model/FK, review round or new
approval system. Explicit independently reviewed correspondence plus source scope
maps candidate Scope to the actual parent UUIDs; names, slugs or PK alone do not.

Candidate factory_body must be a supported **PendingBody**, not null, in this known
body-distinct profile. It remains pending/unbound in the candidate even after a plan
resolves reuse. ExistingBody remains a valid RA-046 wire shape but is unsupported
by this initial executor because its real immutable binding dependency is absent.
Do not manufacture its revision UUID/hash. No Candidate wire or hash changes.

## 2. Closed types, serialization and hashes

Every object defined here is closed, with all shown members required. Null is allowed
only where stated. Reject unknown fields, duplicate keys/IDs, booleans as numbers,
nonfinite numbers, noncanonical ordering and unsupported versions; never repair inputs.
Use RA-046 Hash, Token, UUID, Text, QRef, RefPath, Scope, Timestamp and Powertrain.
Positive `Int` means JSON integer >=1. Timestamp is canonical UTC with Z. Decimal
liters in Powertrain use existing canonical decimal strings. Object-valued body_code
in a semantic preimage maps to the two scalar tuple columns, without changing either.

All examples below are **shape templates**: angle-bracket strings denote types,
not literal accepted values, fabricated hashes, UUIDs or executable artifacts.
`T[]` denotes an array of T; `T|null` is explicit nullability. Reused RA-046 nested
types retain their exact closed shapes and validation. No arbitrary metadata objects.

Canonical bytes C(x) are UTF-8 of existing body_identity.canonical_json(x): sorted
object keys, compact separators, ensure_ascii=False, allow_nan=False, no trailing
newline in hashed bytes, no Unicode normalization. SHA(x) is `sha256:` plus lowercase
SHA-256(C(x)). Raw retained artifact hashes instead hash exact original bytes.
Candidate and semantic digests retain their existing algorithms, never this wrapper's
root hash. New objects use their specific discriminator/version for domain separation.

For a root with X_hash, compute SHA(root with **only** X_hash removed). Remove no
nested hashes or nulls. On validation reconstruct every nested digest first. Objects
without a self-hash are hashed in full. These definitions prevent cycles: evidence,
body and Generation states → family/peer states → proof → plan → Matrix → approval
→ manifest → execution report → receipt. Nothing in a plan points to its manifest.

Set arrays reject duplicates and sort as follows: UUID lists lexically by canonical
UUID; artifact pins by (reference, byte_hash); review artifacts by reference;
correspondences by revision_uuid; families by candidate_reference; peers by uuid;
slug occupancy by slug then UUID; matrix rows by candidate_reference; plans/hashes
by candidate_reference. QRef/Hash/string sets sort lexically. Diagnostics are ordered
by (stage, code, path). Objects preserve original source strings through delegated
RA-046 canonical serialization; order-sensitive source arrays are not resorted.

### Common states (exact keys)

`Parent = {pk:Int, uuid:UUID}`.

`ScopeResolution = {manufacturer:Parent, vehicle_model:Parent, generation:Parent,
canonical_scope:Scope, model_year:2024, market:"US"}`. Resolve chain and active flags
independently; this profile must resolve the reviewed Wrangler JL Generation.

`BodyTuple = {body_style:Token|null, wheelbase_designation:Token|null,
body_length_designation:Token|null, roof_height_designation:Token|null,
door_configuration:Token|null, side_door_arrangement:Token|null,
body_code:Token|null, body_code_namespace:Token|null}`.
All eight keys are present. Apply RA-048 presence/pairing/token rules. Reconstruct the
RA-046 body/2 preimage from non-null fields and Scope. No tuple compatibility merging.

`BodyState = {pk:Int, uuid:UUID, generation_uuid:UUID, attributes:BodyTuple,
updated_at:Timestamp, semantic_preimage:BodyPreimage, semantic_digest:Hash}`.
Validate every scalar/preimage correspondence and recompute semantic_digest.
The state hash is SHA(BodyState), not a binding revision or persisted identity digest.
Body namespaces include every body row in the resolved Generation, sorted by UUID.
Creation/deletion/change of relevant parents is independently re-resolved, not hidden
by supplying only the selected row.

`TargetFields = {model_year:2024, trim_name:Text, engine_name:Text,
drivetrain:"4WD", market:"US", canonical_powertrain:Powertrain,
factory_body_configuration_uuid:UUID|null}`.
Trim length <=100; engine_name <=100; complete five-field Powertrain required.
The body UUID is non-null for create, equal to resolved BodyState.uuid. It may be
null only for an evidenced no-op preserving an existing null FK; the separately
resolved proof body does not authorize changing that FK.
This is a successor projection, not the legacy target_fields_json closed schema.
Translate the powertrain fields to existing columns and resolve the UUID to FK PK
only inside the authorized executor. No new identity columns.

`ArtifactPin = {reference:RefPath, byte_hash:Hash}`.
`ReviewedArtifact = {reference:RefPath, byte_hash:Hash, reader:Token,
reader_version:Text, snapshot:ReviewedPayload}`. ReviewedPayload is exactly the
recognized original review contract for reader/version; unknown readers block with
UNSUPPORTED_REVIEW_VERSION. Never treat arbitrary JSON as an accepted finding.
Include original complete payloads for every used finding; validate exact original
subject/field scope. Old candidate-bound powertrain adjudication does not approve a
new v3 artifact; independent applicable source findings can be reused honestly.

`EvidenceState = {artifact_pins:ArtifactPin[], reviewed_artifacts:ReviewedArtifact[]}`.
Candidate evidence_documents, applicability, configuration_refs and interpretations
are retained in the complete candidate snapshot, not replaced by these pins.
Pins cover every raw/review artifact used by the candidate, Generation, family or
peer assessments; exact paths/bytes are verified within the authorized repository,
rejecting escape/symlink paths. No network acquisition. Missing bytes/readers block;
known source unavailability is not waived by offering-level agreement.

`CorrespondenceState = {revision_uuid:UUID, review_payload:CorrespondenceReview1,
content_hash:Hash, successor_uuid:UUID|null}`. CorrespondenceReview1 is exactly the existing
GenerationCorrespondenceRevision.review_payload() shape validated by current
review_version=1.0 rules. content_hash is SHA(review_payload); compare the actual
published revision chain, leaf/supersession state and applicable restrictions.
Require a current established finding with no successor; no nonexistent is_active
column is assumed on correspondence revisions.

`GenerationState = {scope:ScopeResolution, parent_state:ParentState,
correspondences:CorrespondenceState[]}`. ParentState is exactly the existing
parent_snapshot(vehicle_model,generation) shape, including identity, active flags
and Generation year bounds. Hash it in full, preserving existing field meanings.

## 3. Identity and evidence resolution algorithm

1. Parse complete v3 with the accepted pure reader, verify candidate_hash and all
   semantic preimages. Require non-null Scope, supported PendingBody, complete engine
   tuple, supported market/drive and null series. Reject unsupported dispatch/profile.
2. Verify retained bytes, qualified assertions, original findings, applicability and
   positive same-configuration membership. Reuse established door interpretations;
   source model-code suffix or Unlimited spelling alone never establishes doors.
   No unresolved evidence/dependency diagnostic that affects these premises may pass.
   Negating has_evidence_errors is not evidence acceptance or authority.
3. Resolve Generation through published reviewed correspondences and current chain.
   Require candidate Scope, body Scope, source applicability, model year and resolved
   parents to agree. A candidate-bound legacy finding must not be silently rebound.
4. Compare the whole relevant body set in that Generation. Exact complete normalized
   tuple + independently supported exact applicability permits reuse, subject to the
   §11 approved exception. A different digest alone does not prove distinctness.
   Differing established overlapping dimensions (two-door vs four-door) prove body
   distinction. Compatible sparse subsets/supersets do not: return BODY_AMBIGUOUS
   when the relationship affects reuse/create. Do not enrich the candidate then hash.
5. Compare all VD peers in (Generation, MY2024, US), including inactive rows, using
   baseline/2 semantic identity: Scope, year, exact marketed trim, drive, five-field
   powertrain, body semantic digest, series=null. Engine label is a descriptor.
   Exact body/engine semantics means equal even if the UUID locator differs; different
   proven bodies remain distinct with identical trim/engine. No transmission/QOP split.

| Peer relationship | Plan consequence |
| --- | --- |
| Exactly one active same baseline with valid attributable support | NO_OP; target current canonical fields/slug and existing UUID, never overwrite descriptive labels or provenance |
| Multiple equal peers, inactive equal baseline, contradictory sources | BLOCKED; no new duplicate, no revival/update |
| Same body + different established five-field powertrain | May CREATE with source-backed distinct powertrain evidence |
| Different body tuples with established differing dimensions | May CREATE with body distinction evidence |
| Different sparse tuples with no differing established shared dimension | Compatibility/unresolved, not automatically different physical bodies; block unsafe creation |
| Legacy null body FK | Neither equal nor different. Assess retained exact evidence without mutating FK; if it establishes body, compare that supported projection and pin it. Otherwise block only actual overlapping trim/drive/powertrain ambiguity; unrelated trim/year peers are not a universal null-body gate |
| Inactive different baseline | Not an equal peer, but its slug remains occupied; no recycling |
| Cross-Generation body/source/candidate | Reject; never use scope inequality as a local creation basis |

No-op may preserve an existing descriptor differing from a source alias only when
reviewed equivalence establishes the same baseline. Candidate snapshot retains its
original projection; plan target_fields explicitly pins the existing unchanged row.
All comparisons require appropriate evidence, not merely field matching.

## 4. Complete family and deterministic new-record slugs

A planning release supplies all 31 reviewed active v3 candidates as exact artifacts.
Their identifiers and mapping to retained JL24 rows are pinned; no Cartesian expansion.
`FamilyMember = {candidate_reference:Text, candidate_hash:Hash,
baseline_preimage:Baseline2, baseline_digest:Hash, body_attributes:BodyTuple,
target_fields:TargetFields, legacy_base_slug:Text}`.
Baseline2 is the existing vehicle-definition-body/2 shape. Verify its body digest and
all members against their actual candidates, reviewed evidence and current parents.
Canonical duplicates across release members block the release; no arbitrary winner.
FamilyMember.target_fields is the proposed new-record projection with non-null body
UUID, not a permission to backfill an evidenced no-op peer. A no-op plan instead
pins the actual preserved stored fields, possibly including a null legacy body FK.

`FamilyState = {profile:"my2024-wrangler-jl-consumer/1",
release_members:FamilyMember[], release_evidence:EvidenceState}`.
Exactly the 31 active retained row identities after independently verified mapping;
not merely a caller assertion of completeness. Compare against the pinned retained
active inventory and scope decisions. All 31 artifacts must be available and valid
when computing/revalidating any plan, even if a later authorized matrix selects a subset.
The family digest is SHA(FamilyState). Missing known alternatives invalidates completeness.

For **new** records only:

1. Compute legacy_base_slug using existing year/trim/engine-label/drive/market base
   plus existing complete structured powertrain qualifier rules exactly once. The
   legacy builder and old imports remain unchanged; call a separate v3 helper.
2. Group full release members by (resolved Generation, legacy_base_slug), regardless
   of import order, approval subset or current active status. Group members are the
   reviewed new offerings, not arbitrary source options. Existing records cannot be
   renamed to make this release fit.
3. Where a group contains established two-door and four-door alternatives, append
   `-2-door` or `-4-door` **after** the complete structured base for every member of
   that group. Otherwise keep the base. All body/powertrain identities still compare
   independently of the slug. Do not append doors to every single-body root.
4. Recompute uniqueness across the whole release after qualification. Reject residual
   collisions, unsupported needed qualifiers and length >180. No UUID suffix, code
   inference, random suffix or truncation. Same-door richer sparse alternatives do
   not obtain arbitrary suffixes. A future policy extension requires review.
5. Check each proposed slug against every existing active/inactive VD in the Generation,
   across years/markets. An occupied slug only permits the proven exact active no-op
   with that immutable slug. Otherwise SLUG_OCCUPIED blocks; do not repair on execution.
   An exact equal existing row found by semantic assessment keeps its original slug
   even if a new-record algorithm would spell it differently.

For Sport EC1 the new slugs are exactly:
`2024-sport-20l-i4-turbo-4wd-us-turbo-2-door` and
`2024-sport-20l-i4-turbo-4wd-us-turbo-4-door`.

Known required pair vector set (two-door / four-door):
JL24-01/11, 02/12, 03/13, 04/14, 05/15, 06/16, 07/19, 08/20, 09/21, 10/22.
These cover Sport, Sport S, Willys, Rubicon and Rubicon X with EC1/ERC. The remaining
11 single-body offerings keep structured bases unless the full release reveals a
further genuine collision, which must block rather than silently alter this policy.
Changing any family artifact, engine classification, membership or qualifier decision
stales affected plans; unchanged mathematical baseline does not preserve artifact approval.

## 5. Semantic proof 3.0.0

`VehicleState = {pk:Int, uuid:UUID, generation_uuid:UUID, is_active:boolean,
slug:Text, fields:StoredFields, body:BodyState|null}`.
StoredFields has exactly model_year (RA-046 Year), trim_name (string <=100, may be
blank on legacy rows), engine_name (string <=100, may be blank), drivetrain (existing
2WD/4WD/AWD/UNK), market (US/CA/OT), canonical_powertrain (the exact five-key
Powertrain shape with nullable legacy values). These broader stored types are needed
for Generation-wide slug owners outside MY2024. They do not relax executable
TargetFields or allow incomplete candidate identity. Snapshot all current values.

`PeerAssessment = {vehicle:VehicleState, body_basis:BodyPreimage|null,
powertrain_basis:Powertrain|null, relation:"equal|distinct|unresolved|irrelevant",
receipt_uuid:UUID|null, receipt_snapshot_hash:Hash|null,
supporting_candidates:CandidateV3[], evidence:EvidenceState}`.
For an existing new-path peer, supporting_candidates contains its original full
receipted candidate, validated against its receipt hash and canonical row. For legacy
peers use retained exact applicable findings/documents through evidence plus original
receipt snapshot; pin the complete original resolution_snapshot_json as a recognized
legacy review artifact, never rewrite it. A missing receipt/evidence reader leaves
assessment unresolved when material. receipt_snapshot_hash=SHA(original snapshot)
and UUID must be both null or both populated. A current FK alone is not body support.
Where body_basis differs from current sparse row, no automatic enrichment/equivalence;
resolve applicable exact evidence or return unresolved.

`SlugOccupancy = {slug:Text, owners:VehicleState[]}`. Include an entry for every
release target slug and every pinned exact no-op slug, including owners=[] for empty
slots. Also snapshot the entire Generation slug→UUID map in `generation_slugs`, below,
so unexpected occupancy anywhere in the reviewed locator family cannot be hidden.
`SlugOwner = {slug:Text, uuid:UUID, is_active:boolean}`.

```json
{
  "proof_version": "3.0.0",
  "profile": "my2024-wrangler-jl-consumer/1",
  "candidate_hash": "<Hash>",
  "generation_state_hash": "<Hash>",
  "body_state_hash": "<Hash>",
  "body_namespace": ["<BodyState object>"],
  "evidence_state_hash": "<Hash>",
  "baseline_preimage": "<Baseline2 object>",
  "baseline_digest": "<Hash>",
  "family": "<FamilyState object>",
  "peers": ["<PeerAssessment object>"],
  "slug_occupancy": ["<SlugOccupancy object>"],
  "generation_slugs": ["<SlugOwner object>"],
  "conclusion": "create",
  "existing_vehicle_uuid": null,
  "proof_hash": "<Hash>"
}
```

conclusion is exactly create, no_op or blocked. existing_vehicle_uuid is UUID only
for no_op, null otherwise. Peer list includes the entire relevant namespace sorted
by UUID; Generation slug map sorts by (slug,uuid) and includes inactive rows. Verify
relations independently, not from supplied conclusions. Create needs no equal or
material unresolved peer, supported candidate identity and distinctness from actual
alternatives. A family/source change cannot be hidden by caller-provided empty peers.

## 6. Import plan 3.0.0

```json
{
  "plan_version": "3.0.0",
  "profile": "my2024-wrangler-jl-consumer/1",
  "candidate_reference": "<Text>",
  "candidate_snapshot": "<complete CandidateV3 object>",
  "candidate_hash": "<Hash>",
  "generation": "<GenerationState object>",
  "body": "<BodyState object>",
  "body_action": "reuse",
  "evidence": "<EvidenceState object>",
  "target_fields": "<TargetFields object>",
  "target_slug": "<Text>",
  "action": "create",
  "existing_vehicle_uuid": null,
  "proof": "<Proof3 object>",
  "diagnostics": [],
  "plan_hash": "<Hash>"
}
```

Actions exactly create, no_op, blocked. Reuse body is the only authorized body action.
No UUID allocated by planning. proof candidate, Generation/body/evidence state hashes,
semantic preimage, body_namespace and action must agree with plan; existing_vehicle_uuid follows the
proof rule. Diagnostics reuse RA-047 `{stage,code,path,message}` shape; executable
plans have no material unresolved diagnostic. Blocked plans are reviewable output,
never manifest-executable. target_slug must match pinned family decision or exact
no-op locator. Plan has no timestamp, author or approval flag to infer authority.
Evidence and live resolution remain separate from structural validity.

If Generation/body dependencies are unavailable, do not manufacture a Plan3/Proof3
requiring nonexistent UUIDs. Return only this closed non-executable report:
`{assessment_version:"3.0.0", candidate_reference:Text, candidate_hash:Hash|null,
diagnostics:Diagnostic[+]}`. Hash is null only if parsing/hash verification failed.
Blocked Plan3/Proof3 is available only after their required snapshots can honestly
be populated (e.g. actual peer ambiguity); otherwise use the report. Neither output
can appear in an authorization Matrix.

## 7. Exact Matrix/manifest human authorization

Reuse the existing explicit operator confirmation mechanism and standalone approval
record 1.0; no new human approval system. Extend Matrix digest dispatch for the new
closed shape instead of passing it to old readers.

`AuthorizationRow = {candidate_reference:Text, candidate_hash:Hash, plan_hash:Hash,
action:"create|no_op", existing_vehicle_uuid:UUID|null, target_slug:Text,
baseline_digest:Hash, body_uuid:UUID}`.

```json
{
  "matrix_version": "3.0.0",
  "profile": "my2024-wrangler-jl-consumer/1",
  "scope": "<ScopeResolution object>",
  "family_hash": "<Hash>",
  "body_writes": false,
  "rows": ["<AuthorizationRow object>"]
}
```

Rows are a nonempty exact subset of the complete release, uniquely sorted by reference.
No wildcards, authorization for future rows, or mutable file pointers. Matrix digest
is SHA(entire Matrix3). All selected rows share Scope, family, original peer snapshot
and body namespace state; plan hashes bind complete evidence/decision premises.

`Approval1 = {approval_version:"1.0", matrix_digest:Hash, decision:"approved",
operator:Text, approved_at_utc:Timestamp}` — unchanged existing fields/semantics.
Approval construction requires an actual explicit affirmative owner/operator action
for this exact Matrix digest after review. A user-supplied object/hash is not proof of
that action or authentication. Use existing authorized execution/confirmation boundary;
review-only mode cannot execute. An old approval or candidate classification review
cannot authorize this Matrix. Approval hash is SHA(entire Approval1).

```json
{
  "manifest_version": "3.0.0",
  "matrix": "<Matrix3 object>",
  "matrix_digest": "<Hash>",
  "approval": "<Approval1 object>",
  "approval_hash": "<Hash>",
  "manifest_hash": "<Hash>"
}
```

Manifest includes exact scope/decision, not the full plans again; the executor must
load hash-matching full plans for every row. Reject extra/missing/reordered/changed
plan subjects. Record CLI/execution-agent attribution separately from human approval.
Any Matrix/plan/body/family change requires fresh review and affirmative approval;
never recompute a hash while retaining an old approval. Existing approval1 validator
must gain explicit Matrix3 digest support; historical approval behavior is unchanged.

## 8. Execution revalidation 3.0.0 and atomic behavior

`RevalidatedRow = {candidate_reference:Text, plan_hash:Hash, proof_hash:Hash,
baseline_digest:Hash, body_state_hash:Hash}`.

```json
{
  "revalidation_version": "3.0.0",
  "manifest_hash": "<Hash>",
  "matrix_digest": "<Hash>",
  "approval_hash": "<Hash>",
  "family_hash": "<Hash>",
  "rows": ["<RevalidatedRow object>"],
  "result": "valid",
  "diagnostics": [],
  "revalidation_hash": "<Hash>"
}
```

result is valid or stale. All execution input plans must be reconstructed from exact
candidate bytes and independently re-resolved, not merely compared to caller-supplied
snapshots. Recompute family, original evidence/dependency readers, current parent
chain, body tuple/update timestamp, all peers and Generation slug map. Validate exact
Matrix/approval membership before any write. A changed source byte/ref/finding, candidate,
correspondence/supersession, shared body row, relevant peer, active state, family,
slug owner or authorization causes stale and no canonical writes. Missing required
support blocks. Diagnostic paths identify the stale premise; no silent plan repair.

Execute the complete selected Matrix atomically using existing transaction.atomic
infrastructure. Inside the same database transaction, perform **all** revalidation
against the common pre-batch state **before** inserting any selected row. Then create
only enumerated VDs and receipts. Planned rows are jointly checked for equality and
slug conflicts before writes; rows inserted earlier in this transaction are recognized
as these exact planned outputs, never unexpected peers. This avoids staling the next
row on this batch's own insert. No parent creation/update or existing VD update/delete.
A no-op writes a new execution receipt only; it preserves existing row bytes.

SQLite: SELECT FOR UPDATE is not a row-lock guarantee. Read/revalidate/write in the
same transaction; SQLITE_BUSY, SQLITE_BUSY_SNAPSHOT, locked writes or uniqueness
conflicts roll back the **entire** batch. Do not catch an error and continue rows or
retry writes against old premises. Re-plan and obtain new exact approval outside the
failed transaction. Other supported backends must serialize the same namespace or
provide equivalent conflict detection; this milestone is SQLite only. The deterministic
slug plus existing Generation/slug unique constraint is the final insert race guard;
no claim of a newly persisted semantic vehicle digest constraint.

Concurrent identical batches: at most one create commits; the other aborts stale/locked
or unique conflict and may replan an evidenced no-op. Concurrent body-distinct batches:
never merge; independent old snapshots may require one to replan/reapprove after peer
or namespace drift. A single approved two-body batch commits both atomically. Import
order does not choose slugs. Automatic success of stale concurrent approvals is not
promised. Any VD/receipt failure rolls back all selected VD/receipts. Failure diagnostics
may be retained as external attempt artifacts; no successful receipt for rolled-back
writes. Post-commit reporting failure must report committed state, not claim rollback.

## 9. Receipt snapshot 3.0.0 (existing receipt model)

```json
{
  "receipt_version": "3.0.0",
  "profile": "my2024-wrangler-jl-consumer/1",
  "manifest": "<Manifest3 object>",
  "plan": "<Plan3 object>",
  "revalidation": "<Revalidation3 object>",
  "outcome": "created",
  "vehicle": {"pk": "<Int>", "uuid": "<UUID>", "slug": "<Text>"},
  "persisted_fields": "<TargetFields object>",
  "execution_agent": "<Text>",
  "executed_at_utc": "<Timestamp>",
  "snapshot_hash": "<Hash>"
}
```

Only created/no_op outcomes receive success snapshots. A no_op vehicle is the exact
pinned existing UUID. A create UUID is minted only in the transaction. Snapshot_hash
excludes only itself; all nested candidate, evidence, body, peer, family, exact approval
and revalidation content is embedded and hash-checked. This is a historical decision
snapshot, **not** an immutable RA-046 binding revision or ongoing authority over an
editable body row. It reconstructs the approved decision and original body state even
if a later authorized Admin correction changes current row attributes.

Matrix AuthorizationRow.body_uuid always denotes the resolved semantic parent, even
for an evidenced no-op preserving a null stored FK. persisted_fields records the
actual unchanged null and must not claim that assignment occurred.

Store as `resolution_snapshot_json = {"body_import": ReceiptSnapshot3}`; no other root
keys for this new path. Do not rewrite historical receipt JSON. Existing scalar columns
remain ordinary mirrors: operation_type vehicle_definition_import; candidate_reference,
manifest_hash, resolved_generation_id, target_* and target_fields_json agree with plan;
operator_label=approval.operator; execution agent remains distinct. Populate existing
created/existing FK and PK/UUID/slug snapshot columns according to outcome.
For this path target_fields_json is exactly TargetFields above. create_basis is
`body_aware_identity` for create and empty for no_op; it means source-supported complete
baseline distinction, not every difference being a body difference. Unknown old readers
must reject receipt_version 3.0.0 rather than applying Engine Proof 2.0 semantics.

Multi-source scalar attribution uses the candidate's first configuration_ref in its
existing canonical order; resolve its document's source_id/raw hash/reference and
source identity tuple. Retain **all** qualified attribution in the embedded candidate.
Source identity selects the candidate's generation_evidence item with that same document
and assertion grouping, sorted by (source_id, document_hash, assertion_set_id,
assertion_id); require an actual matching item, otherwise block. Do not invent a primary
source or reuse a receipt from an unrelated configuration. Correspondence_revision FK
may remain null because complete applied revisions are pinned in GenerationState;
its scalar optionality does not discard that evidence.

Receipt model UUID/timestamps/PK remain unchanged. No signature, cryptographic actor
identity, new audit model or live evidence acceptance flag is introduced.

## 10. Compatibility, implementation inventory and acceptance tests

No operational migration or data writes are authorized by this implementation task. Historical assignment
inventory remains 260 reviewed MY2019–MY2023 JL proposals, 15 unresolved MY2018 joins,
80 out-of-scope JK records. FK-only assignments require separate explicit authorization;
do not combine them with new MY2024 publication. Reuse door findings without a second
classification review. Current labels, immutable slugs, UUIDs, receipts and sources stay.

Authorized implementation inventory (actual verification and complete paths are in the handoff):

| Files | Bounded change |
| --- | --- |
| reference/ingestion/importing/body_identity.py (new) | Live exact resolution, peer states and isolated readable slug helper |
| reference/ingestion/importing/body_import.py (new) | Exact authorization, independent transactional reconstruction and batch/receipt persistence |
| reference/ingestion/body_import_contracts.py (new) | Closed Plan3/Proof3/Manifest3/Revalidation3/Receipt3 canonical serializers and hashes |
| reference/ingestion/importing/planner.py; importing/__init__.py | Explicit v3 dispatch; new closed plans, preserve old branches |
| reference/ingestion/manifest.py; matrix.py; matrix_approval.py | Explicit version dispatch and reuse affirmative approval1 with Matrix3 hashing |
| reference/ingestion/importing/importer.py; workflow.py; matrix_workflow.py | Versioned revalidation/atomic executor/receipt mapping; reject unsupported paths |
| reference/tests/test_body_aware_import.py; test_body_import_contracts.py; body_import_support.py (new) | Exact vectors, synthetic temporary evidence, concurrency, identity, execution and preservation coverage |
| reference/ingestion/importing/powertrain_identity.py | Explicit receipt-v3 rejection only; legacy equality unchanged |
| MY2024 artifacts | Preserved; production v3 release preparation/publication remains separately authorized |

No models/migrations/legacy slug builder/pure v3 wire changes. Reuse body_identity,
candidate_v3 and candidate_v3_evidence without altering their contracts. Existing
powertrain_identity remains legacy; reuse vocabulary, not its body-blind equality.

| Acceptance test | Required result |
| --- | --- |
| All 31 active reviewed offerings / ten pair vectors | 31 supported baselines and unique new slugs; every listed pair uses exact readable suffix placement |
| Sport doors with identical five-field engine | Same Sport trim, distinct bodies/identities; preserved Unlimited source provenance |
| Same body and engine repeated / descriptor alias | Evidenced exact no-op; no duplicate or mutable-label rewrite |
| Sparse richer/subset and two compatible alternatives | Never auto-merge or create from digest difference; material ambiguity blocks |
| Null historical body FK | No inference of equal/distinct; attributable evidence comparison or targeted overlap block; unrelated nulls do not block |
| Cross-Generation candidate/parent/correspondence | Reject; no FK writes |
| Full-family permutation/subset approval | Byte-identical family decisions/slugs; omitting known alternative invalidates completeness |
| Inactive equal peer / occupied inactive slug | No resurrection, no duplicate, no locator recycling |
| 180-character and 181-character slugs / residual collisions | Exact boundary accepted; overflow/residual collision rejected, never repaired |
| Candidate/evidence/finding/Generation/body row/peer/active/slug drift | Revalidation stale; zero writes |
| Missing byte or reader / unsupported ExistingBody | Explicit unresolved dependency; no forged revision/acceptance |
| Plan/Matrix/approval/manifest mismatch or review-only execution | Reject before writes; affirmative exact human scope required |
| Concurrent identical creates | One creation at most; loser rolls back and requires new plan/approval |
| Concurrent distinct-body creates / joint batch | Never merge; retry requires refreshed exact review; joint approved batch creates both |
| Failure at any VD/receipt write | Entire selected batch rolls back; no orphan success receipts |
| Receipt replay and later Admin body correction | Original decision independently reconstructible; later state cannot rewrite prior snapshot |
| Legacy slugs and approved historical assignment inventory | Unchanged; no automatic FK backfill or identity reinterpretation |
| Candidate A–H hashes/bytes and historical Candidate 2.1.0 | Exact existing vectors and all legacy regressions unchanged |
| Hash vectors/closed recursive shapes/set ordering | Reconstruct all hashes; reject unknown keys, duplicate IDs and noncanonical inputs |

These obligations are exercised by the isolated RA-049 tests. Fresh verification:
59 focused tests, 335 targeted tests and 930 full-suite tests passed (full suite
70.746 seconds). See the implementation handoff for exact coverage and dependencies.
The earlier RA-048 871-suite result remains historical, not successor verification.

## 11. Owner-approved scoped RA-046 runtime clarification

The Project Owner approved the following scoped exception, now recorded verbatim in
RA-046 §15. Historical clauses and accepted ADRs were not rewritten. It affects:

- §5 BindingRevision paragraph: independently fetched immutable persisted revision
  and frozen parent chain as mandatory support for reuse.
- §5.1 outcome A and subsequent execution paragraph: immutable binding on exact
  pending-parent reuse, and parent+binding creation in the future atomic lifecycle.
- §7.2 existing-parent reuse row: immutable binding/current-state revalidation wording.
- §10 Future proof 3.0/Resolution 2.0 and Manifest/Matrix/receipt coordination rows:
  immutable parent/binding snapshots and parent-write scope for future execution.
- §14 approved decisions 2, 3 and 10: binding snapshot reader/lifecycle prerequisite
  references, only insofar as the new narrow PendingBody execution profile is concerned.

Exact clarification approved by the Project Owner on 2026-11-13:

> For the my2024-wrangler-jl-consumer/1 downstream import profile only, a valid
> PendingBody may resolve exact reuse of an existing RA-048 body row through the
> RA-049 versioned plan/proof/Matrix/authorization/receipt state snapshots and
> independent evidence, applicability and transactional stale-state checks. This
> replaces the mandatory persisted immutable binding-revision prerequisite for
> this reuse operation only; it is not equivalent to such a revision. The body row
> remains editable under RA-048. No parent creation or update is authorized by this
> executor. Candidate ExistingBody retains its unchanged BindingRevision wire
> requirements and remains unsupported here without its real dependency. No
> source support, whole-set ambiguity, human authorization or atomic receipt
> safeguard is relaxed. Other profiles, existing-mode contracts and historical
> artifacts retain their prior meaning.

The owner approved this exact downstream contract, including reuse-only initial
scope, full-family slug policy, batch atomicity and refreshed approval after drift. These choices are fixed by that approval; no mechanism is delegated to a new
architectural decision.
Body row population/migration, candidate readiness, Generation publication and canonical
execution still require their separate operational authorizations. Missing original
MY2024 source bytes and unresolved powertrain/finding dependencies are not resolved
by this design or by offering-level agreement.

The approved successor implementation is delivered for review using existing
persistence and versioned JSON only. No operational migration, historical assignment
or MY2024 publication was performed. Runtime entry points and source-reader boundaries
are documented in the implementation handoff.


## 12. Readable-slug acceptance vectors (diagnostic, not publication)

Derived from the retained active trim-normalization inventory and its proposed engine
classifications. This document check confirms 31 unique strings and all ten paired
suffixes, not evidence acceptance, executable successor tests or candidate readiness.

| Two-door row | Four-door row | Expected two-door new slug | Expected four-door new slug |
| --- | --- | --- | --- |
| JL24-01 | JL24-11 | `2024-sport-20l-i4-turbo-4wd-us-turbo-2-door` | `2024-sport-20l-i4-turbo-4wd-us-turbo-4-door` |
| JL24-02 | JL24-12 | `2024-sport-36l-v6-ess-4wd-us-2-door` | `2024-sport-36l-v6-ess-4wd-us-4-door` |
| JL24-03 | JL24-13 | `2024-sport-s-20l-i4-turbo-4wd-us-turbo-2-door` | `2024-sport-s-20l-i4-turbo-4wd-us-turbo-4-door` |
| JL24-04 | JL24-14 | `2024-sport-s-36l-v6-ess-4wd-us-2-door` | `2024-sport-s-36l-v6-ess-4wd-us-4-door` |
| JL24-05 | JL24-15 | `2024-willys-20l-i4-turbo-4wd-us-turbo-2-door` | `2024-willys-20l-i4-turbo-4wd-us-turbo-4-door` |
| JL24-06 | JL24-16 | `2024-willys-36l-v6-ess-4wd-us-2-door` | `2024-willys-36l-v6-ess-4wd-us-4-door` |
| JL24-07 | JL24-19 | `2024-rubicon-20l-i4-turbo-4wd-us-turbo-2-door` | `2024-rubicon-20l-i4-turbo-4wd-us-turbo-4-door` |
| JL24-08 | JL24-20 | `2024-rubicon-36l-v6-ess-4wd-us-2-door` | `2024-rubicon-36l-v6-ess-4wd-us-4-door` |
| JL24-09 | JL24-21 | `2024-rubicon-x-20l-i4-turbo-4wd-us-turbo-2-door` | `2024-rubicon-x-20l-i4-turbo-4wd-us-turbo-4-door` |
| JL24-10 | JL24-22 | `2024-rubicon-x-36l-v6-ess-4wd-us-2-door` | `2024-rubicon-x-36l-v6-ess-4wd-us-4-door` |


## 13. Verified implementation status — 2026-11-13

**READY FOR IMPLEMENTATION REVIEW.** Exact closed contracts, full-family planning,
readable slugs, reuse-only parent resolution, approval1 integration, common pre-batch
revalidation, atomic create/no-op receipts and SQLite conflict rollback are implemented.
No models, FKs, migrations, pure Candidate v3 wire/hash changes or operational data
writes. Runtime source extraction is deliberately bounded: directly retained native
JSON assertion projections and the pinned MY2024 inventory/heading join are checked;
unknown source/review readers remain explicit dependencies, not assumed acceptance.
Provisional CSV powertrain columns do not become approval evidence. Historical
Candidate 2.1.0 documents and A–H fixtures remain byte-identical.

[Implementation handoff](../../implementation/handoffs/RA049_body_aware_import_contract_20261113/README.md).


Final source-review checkpoint (2026-11-13): **PASS WITH CORRECTIONS — READY FOR
OWNER ACCEPTANCE**. Fresh verification passed 86 focused, 362 targeted and 957
full-suite tests (90.054 seconds full suite). The implementation results above are
historical checkpoints; exact findings, reader dependencies and proposed acceptance
boundary are recorded in [FINAL_REVIEW](../../implementation/handoffs/RA049_body_aware_import_contract_20261113/FINAL_REVIEW.md).
No approved shape/hash algorithm, Candidate wire, model or operational data changed.
Architecture remains Approved; the Project Owner has now formally accepted the
reviewed implementation. Acceptance does not authorize operational deployment or
production publication.
