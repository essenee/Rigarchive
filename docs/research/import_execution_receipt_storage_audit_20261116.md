# ImportExecutionReceipt storage architecture audit

Created: 2026-11-16
Status: Research complete; optimization not authorized

## Executive finding

The database is **61.68 MiB** (64,679,936 bytes). Oversized receipts
are primarily an evidence-packaging/storage consequence: every generation-aware
candidate carries all supplied assertion sets, including full extracted table and
package-page text. Resolution preserves that collection unchanged, and execution
copies it into each receipt. Overlapping candidates repeatedly embed identical
documents, even when their complete document collections differ. These are JSON
assertions/provenance, not embedded PDF binaries.

**Recommendation:** retain historical receipts unchanged now. If growth warrants
an approved implementation, first evaluate a versioned, lossless compressed
snapshot representation behind a common receipt reader. This is simpler than
normalizing evidence relationships and preserves exact original bytes. Immutable
content-addressed **individual documents plus ordered bundle manifests** offer
substantial additional structural reuse, but whole-collection deduplication alone
has little benefit. Do not filter historical evidence or substitute mutable
correspondence references.

## Implementation and authority trace

Repository-relative paths below identify current source; line numbers refer to
this inspected checkout.

| Stage | Exact implementation | Behavior |
|---|---|---|
| Acquisition retention | `reference/ingestion/acquisition/snapshots.py:57`, `RawSnapshotManager.store_snapshot` at line 173 | Hashes and retains raw acquisitions independently of receipts. MY2021 also has specifically retained archival sources and transcriptions. |
| MY2021 evidence packaging | `docs/implementation/handoffs/MY2021_JL/candidate_classification_20261109/build_artifacts.py:195–241` | Joins row-specific positive observations to applicable revision/model-code tables, retains complete table text and all engine segments, adds model-specific package pages, relevant technical sets and owner's manual evidence. This historical operational script is in the intentionally ignored handoff tree. |
| Candidate construction | `reference/ingestion/candidate/builder.py:220`, especially line 246 | `construct_candidate_configuration` passes every supplied source assertion set to `generation_evidence_from_sets`. |
| Document projection | `reference/ingestion/normalization/generation.py:9`, `generation_evidence_from_sets`; line 33, `generation_evidence_from_documents` | Copies every assertion's ID/key/raw value/context and document provenance. Only the separate generation-identity projection is filtered to generation keys. |
| Resolution | `reference/ingestion/generation_correspondence.py:220`, `_resolve_generation` at 232; return at 258 | Validates explicit evidence, requires correspondence evidence to be contained in candidate documents, then returns the complete input `documents` array. No reduction before persistence. |
| Planning | `reference/ingestion/importing/planner.py:546` | `plan_candidate_import` passes `candidate.evidence_documents` directly to resolution, adding structured identity/proof metadata for 2.1.0. |
| Execution/persistence | `reference/ingestion/importing/workflow.py:124–148` | Nested `_build_and_save_receipt` writes `plan.generation_resolution` into the JSONField via `ImportExecutionReceipt.objects.create`. |
| Matrix execution | `reference/ingestion/importing/matrix_workflow.py:243`, lines 280–303 | Freshly plans each row inside an atomic transaction; writes receipt then adds its Matrix linkage before commit. |
| Model | `reference/models.py:924–942` | `ImportExecutionReceipt.resolution_snapshot_json` is a normal JSONField; there is no compressed/shared document storage layer. |
| Correspondence publication | `reference/ingestion/generation_correspondence.py:135–149`; `reference/models.py:904–918` | Publication receipt embeds the review payload, including evidence; the append-only correspondence revision independently stores evidence and its hash. |

The collection is **candidate-supplied evidence**, not a resolver-generated entire
Generation corpus or a guaranteed single batch corpus. Operational packaging often
makes it a broad model-family/revision union. Candidate, assertion-set, manifest
and planning files also retain evidence outside SQLite; raw acquisitions retain
source bytes. They are not a substitute for a guaranteed durable database bundle.
Of 1,479 unique receipt documents, **241** exactly match evidence documents in
correspondence revisions. The revision table is not a complete duplicate archive.

Governing sources inspected: CURRENT_STATE; accepted ADR-0006 (immutable raw
acquisitions), ADR-0007 decisions 5/9/10/13 and its Matrix amendment (exact review,
durable atomic receipts, separation from canonical evidence relationships),
ADR-0010 (reviewed correspondence, source-qualified projection and stale checks),
ADR-0012, and accepted RA-044 sections 5/Matrix execution. RA-044 line 105 explicitly
requires historical receipt fields/payload bytes untouched and exact new
resolution/proof retention. These require preserved historical meaning and exact
bindings, **not a physical copy of each identical document in every row**.
Current embedded shape is nevertheless an executable contract; changing it requires
approved compatibility/storage work, not a transparent data cleanup.

## Measurements

Read-only SQLite inspection, UTF-8 byte lengths, SHA-256, canonical JSON using
sorted keys/compact separators/UTF-8, and zlib level 9. MiB means 1,048,576 bytes.
Canonical measurements preserve array ordering but normalize object key order and
whitespace. They are not claims that original SQL text bytes are identical.

| Item | Measured result |
|---|---:|
| Receipts | 3,591 |
| Receipt table pages, including overflow | 60,297,216 bytes / 57.50 MiB |
| Correspondence table pages | 2,199,552 bytes / 2.10 MiB |
| VehicleDefinition table pages | 245,760 bytes / 0.23 MiB |
| Free pages | 75 × 4,096 = 307,200 bytes / 0.29 MiB |
| All resolution JSON text | 56,175,989 bytes / 53.57 MiB |
| Target-fields JSON / messages JSON | 462,185 / 239,593 bytes |
| Snapshots >100,000 bytes | 161, all original text byte-distinct |
| Those snapshots combined | 45,975,804 bytes / 43.85 MiB |
| All generation-resolution document occurrences | 5,963 |
| Unique canonical documents | 1,479; 5,520,610 bytes / 5.26 MiB |
| Documents reused in multiple occurrences | 383 unique documents; maximum reuse 73 |
| All canonical document object bytes, with repetition | 44,051,100 bytes / 42.01 MiB |
| Nonempty canonical document collections / unique bytes | 354 unique; 43,853,943 bytes |
| All canonical collection bytes, with repetition | 44,057,418 bytes |
| Assertion object bytes, repeated / unique | 38,167,999 / 3,821,156 bytes; 3,404 unique assertions |

All **362 distinct raw source paths** referenced by these generation documents
exist and match their recorded SHA-256. This verifies retained bytes, not the
truth or completeness of every source assertion. Canonical hashes were computed
for every collection, document and assertion in temporary analysis; no content was
rewritten. Table page measurements came from system SQLite `dbstat`; Python's
SQLite build lacks that virtual table.

### The 161 large snapshots are heterogeneous

| Operation/year | Receipts | Original snapshot bytes | Distinct manifest hashes |
|---|---:|---:|---:|
| Correspondence publication | 1 | 263,031 | 1 |
| MY2018 imports | 6 | 1,596,224 | 6 |
| MY2021 imports, JL Generation 32 | 73 | 32,170,852 | 73 |
| MY2022 imports, JL Generation 32 | 50 | 6,541,882 | 50 |
| MY2024 imports, body-import format | 31 | 5,403,815 | 1 |

129 large receipts have `generation_resolution.documents`; their **128 unique
collections** consume 38,215,491 canonical bytes versus 38,418,966 with repetition.
The exact extracted original array text also has 128 unique values: 38,597,013
unique bytes versus 38,802,330 repeated bytes. Thus whole-snapshot differences do
not conceal extensive identical *whole* document collections. Individual document
reuse is the larger opportunity: these 129 receipts contain 4,072 document
occurrences but only **540** unique canonical documents (3,250,456 bytes).
The other 32 snapshots use publication/body-specific structures; an empty/missing
`generation_resolution.documents` must not be counted as a shared evidence bundle.
MY2021 and MY2022 large collections are individually different, not simply one
shared array per year. Manifest hashes are mostly row-specific and cannot identify
an evidence bundle. Matrix and correspondence bindings are independently retained;
sharing a target or publication does not imply identical candidate evidence.
Large generation-aware imports have 1 distinct correspondence-binding array for
MY2018, 15 for MY2021 and 6 for MY2022; the largest shared group has 20 receipts.
Shared correspondence bindings therefore also do not establish shared collections.

### Receipt 3135

MY2021 Unlimited Sahara, historical engine descriptor `3.6L V6`, retains 61 documents:
14 JLJP74 powertrain-table sets (June 4, 2020 through August 6, 2021), 42 package-page
sets, four supporting technical/manual/secondary sets, and one human-adjudication
set. Canonical documents occupy **547,943 bytes**; generation evidence 5,727 bytes;
engine distinction 10,948 bytes; correspondence bindings 1,807 bytes.
Its canonical collection SHA-256 is
`4f7916735a3bfcfbfb4b4ce6d07fe142b8556120400f86e1b4217bc654f0a935`.

These are model-family-applicable documents, not 61 independent proofs of this
exact trim/engine. The first table includes ERC/EC1/ERG/EXJ and Sahara/Altitude/High
Altitude QOP alternatives. Package page 8 discusses Altitude/High Altitude equipment;
those pages were deliberately retained as unmapped context, not evaluated conditions.
Their presence is supported by the packaging code, not accidental attachment of an
entire unrelated Generation corpus. Some content exceeds the minimum positive
proof for ordinary Sahara, but determining what may be omitted must also consider
edition distinctions, rejected alternatives, provenance and exact candidate hashes.
This audit does not certify a safe minimal subset.

## Auditability and compatibility

Embedded evidence is actively read, not merely a log:

- `generation_correspondence.revalidate_resolution` at line 305 validates source
  bytes, parent state and exact current resolution against reviewed premises;
  `validate_generation_evidence` at 267 requires a complete identity projection.
- `reference/ingestion/importing/powertrain_identity.py:92–142` `assess_peer`
  validates creation-receipt identity/scope, source documents, human classification
  lineage and proof; `_variant_guard` around line 74 inspects horsepower/torque
  assertions. Evidence/receipt digests bind later peer assessments.
- `reference/ingestion/importing/engine_distinction.py:55–86` reads retained
  document assertions for legacy peer evidence.
- `reference/ingestion/importing/matrix_workflow.py:117–196` reconciles receipts,
  row/candidate bindings, parents and correspondence identities.
- Body-import paths have separate versioned readers (`body_identity.py:392`);
  Engine reconciliation has its own receipt projection reader. Admin displays JSON.

No generic historical database rollback is implemented by this snapshot: backups
and execution records support recovery analysis. Self-contained assertions improve
historical reconstruction but do not eliminate the need to retain raw artifacts,
extractor versions, approvals and canonical baselines. Current raw-byte checks
still depend on local retained files. Model-level append-only protection exists
for correspondence revisions; receipts use ordinary save operations, including
Matrix annotation. Logical historical immutability is a workflow requirement,
not a universal database trigger enforcing all receipt writes.

A shared bundle can preserve these guarantees only if immutable content is retained
locally/durably, its hash and ordered membership are pinned by each receipt, and
readers recover exactly the originally bound evidence. It must never resolve via
only a mutable/current correspondence, external URL or unavailable handoff file.

## Storage strategies and recommendation

| Strategy | Measured opportunity | Tradeoff |
|---|---|---|
| A. Existing embedded JSON | No savings; 53.57 MiB snapshot text | Simplest current verification and inspection; storage grows with repeated evidence × receipts. 61.68 MiB is operationally modest, not an emergency. |
| B. Candidate-specific filtering | Not quantified: no validated minimal dependency closure | Could reduce future candidates, but changes hashes/authorization and may remove negative/context evidence. Never retroactively filter receipts. |
| C. Whole immutable collection bundles | 203,475 bytes / 0.19 MiB canonical payload savings across current generation arrays, before references/indexes | Collections mostly differ; insufficient standalone benefit. |
| C. Individual immutable documents + ordered manifests | 38,530,490 bytes / 36.75 MiB repeated canonical document bytes | Payload-only opportunity; references, ordered membership, indexes and compatibility reduce net savings. Keep complete document provenance; assertion-only dedup risks identity/context loss. |
| D. Per-snapshot lossless compression | 56,175,989 → 6,907,672 bytes, saving 49,268,317 / 46.99 MiB (87.7%) | Measured in memory, including all snapshot formats. Exact original UTF-8 bytes round-trip for all 3,591. Needs versioned reader, bounded decompression and inspection tooling; JSON-path queries cannot operate on an opaque compressed blob. |

The 161 large snapshots alone compress from 45,975,804 to 4,542,953 bytes.
Unique canonical generation collections compress to 4,153,717 bytes; this is a
separate experiment, **not additive** to the full-snapshot compression savings.
None of these is a measured resulting SQLite database size: page allocation,
indexes, added metadata and free space change physical results. Updating storage
without rebuilding leaves reusable pages rather than immediately shrinking a file.
No compressed database was constructed and no VACUUM was run.

SQLite has no configured transparent compression here. Application-level lossless
storage is explicit and portable but changes the JSONField contract; do not put
compressed strings into it silently. A future PostgreSQL evaluation should measure
native storage behavior rather than carry SQLite byte projections over unchanged.
Compression is recommended for an approved prototype before a document-store
schema: it removes more measured payload with less evidence-relationship complexity.
Retain JSON querying for essential scalar Matrix/version bindings if storage changes.

## Future migration outline — proposal only

1. Approve explicit storage/version semantics and a common fail-closed reader;
   inventory every consumer, hash boundary and JSON-path query. Maintain old-format
   support. Prefer new receipts only initially; historical receipts remain untouched.
2. Snapshot and restore-test the complete database plus retained raw artifact store.
   Pin all 3,591 receipt IDs/UUIDs and original SQL JSON UTF-8 hashes, scalar fields,
   schema/migrations and canonical baselines. Keep the verified backup immutable.
3. Add separately authorized schema/storage support. For compression preserve the
   exact original UTF-8 payload, codec/version, uncompressed size and byte hash;
   also preserve canonical semantic hashes. For bundles preserve ordered document
   membership, complete objects and immutable per-document/bundle hashes.
4. Exercise old/new readers on isolated copies: exact byte round trips, semantic
   digests, Matrix resumption, legacy/structured/body peer assessment, classification
   lineage, Admin inspection, source verification, stale checks and failure rollback.
5. If historical optimization is later approved, preserve all receipts and original
   bytes, transactionally backfill a lossless shadow representation and compare
   every result before any cutover. Do not rewrite history to imply richer evidence.
   RA-044's historical-byte restriction requires explicit compatibility review.
6. Fail closed on missing/corrupt evidence, hash mismatch, unsupported codec/version
   or size-limit violation; never fall back to current records or network retrieval.
   Bundle references need protected integrity/no-delete semantics and backup closure.
7. Restore-test on SQLite and later PostgreSQL; verify canonical/reference rows,
   all receipts, migrations and relationships unchanged. Roll back readers to the
   preserved legacy representation if validation fails. Physical reclamation is a
   separate authorized maintenance operation, never part of a silent migration.

## Risks, limits and verification

No evidence-minimal subset or PostgreSQL physical savings were established. Bundle
or compression work is a future schema/contract decision, not approved by this
audit. Ignored operational handoffs need separate archival policy; their current
availability does not prove long-term portability. Source hashes verify identity,
not source correctness. Existing historical receipts must remain readable even if
current canonical rows or registry assignments have legitimately advanced.

Focused generation projection/correspondence tests: **44 passed**, isolated test
database; system checks report no issues. Read-only SQLite integrity is `ok`, zero
foreign-key violations. All compression experiments were memory-only. Temporary
scripts/metrics are under `/tmp/receipt_*`; they contain no authentication tables.
Live database SHA-256 before/after: `dd6e5d9bf4455ff9e20bc40249cf33034bb78b0a86b6c6f85f79d6ce918cb114`.
Final preservation comparison verifies live database and pre-existing repository
file hashes unchanged; the sole authorized repository addition is this report.
No migrations, assignments, imports, VACUUM, staging, commits, push or deployment.
