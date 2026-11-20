# ADR-0013 — Unified factory body identity

Created: 2026-11-13
Last Updated: 2026-11-19
Status: Accepted
Date: 2026-11-13
Accepted: 2026-11-13

**Design:** [RA-045 — Unified Factory Body Identity](../designs/RA-045-Unified-Factory-Body-Identity-Architecture.md).
**Approval:** Explicit Project Owner authorization on 2026-11-13 accepts this
decision and its narrow amendments to ADR-0010/0011/0012. A first bounded pure
identity/contract-foundation implementation phase is separately authorized. No
operational migration, parent publication, candidate regeneration or canonical write
is authorized.

## Scoped amendment — factory Transmission designation (2026-11-19)

A verified factory transmission difference may distinguish otherwise identical
VehicleDefinitions. This supersedes only the earlier prohibition against
transmission-only canonical distinctions. The manufacturer configuration and
its applicable transmission must be supported by evidence. An ordering code
alone does not establish that distinction. Unknown transmission is unresolved
for overlap checks. Equal designations establish neither hardware identity nor
parts interchangeability.

Store the controlled designation directly on VehicleDefinition. Keep Full
Specs hardware descriptions, ratios, manufacturer hardware codes and evidence
in their existing catalogue domain. Preserve existing PKs, UUIDs, immutable
slugs and the interpretation of historical identity and receipt contracts.
Transmission-aware authoring uses a successor contract. Factory packages remain
in Full Specs. Treat a package with an engine upgrade as a trim under the current
project rule, subject to applicable manufacturer evidence.

## Context

MY2024 Wrangler trim-only naming removes the historical Unlimited discriminator.
Current Candidate 2.1.0, VehicleDefinition, peer comparison and slugs lack canonical
body identity. The audited 31-row set collapses to 21 slug/identity representations,
with ten two-door/four-door collision pairs. A slug-only change cannot fix semantic
merging. Future van requirements also need series, wheelbase, length, roof and
side-door distinctions without multiplying unsupported option combinations.

ADR-0011 already proposes a reusable Generation-scoped FactoryBodyConfiguration,
separate FactorySeries, protected optional associations, explicit missingness and
future body-aware version dispatch. Its accepted scope is a reviewed van profile
with five dimensions; it preserves Wrangler's historical trim workaround. ADR-0012
requires a successor to the body/1 engine-name identity preimage before structured-
powertrain body-aware imports. These accepted documents remain unchanged today.

## Decision

Adopt RA-045's explicit sparse optional FactoryBodyConfiguration entity, scoped to
Generation and reusable across evidenced year/trim/engine combinations. Use an
optional PROTECT ForeignKey from VehicleDefinition; retain independent FactorySeries
where manufacturer series differs from trim. Represent seven explicit dimension
groups: body form, wheelbase designation, body-length designation, roof designation,
door configuration, side-door arrangement and body code. Do not use EAV or turn
measured dimensions/ordinary equipment into canonical body keys.

Only established identity-bearing dimensions contribute to the frozen sparse
semantic basis. Other fields remain null without fabricated statuses, missing-evidence
errors, ineligibility, placeholders or additional review. No body or series association
is required for ordinary vehicles or every new v3 record. Missing alone is neutral;
known differing bodies remain distinct. Compatibility is not transitive equality:
resolve against the relevant actual source/peer set, normalizing synonyms and reusing
existing supported identities. Review only actual ambiguity or conflicting evidence,
not hypothetical future differences. A caller cannot omit a known discriminator to
force a merge. Later real discriminators require reviewed correction/reconciliation,
not mutation of referenced historical identities or today's speculative blocking.

Reuse existing reviewed Wrangler Edmunds taxonomy/manufacturer reconciliation for
2-Door/4-Door directly in the normal candidate/import workflow, preserving Unlimited
wording as provenance and Sport as canonical trim. No second independent body review
or parent-publication approval stage is automatic. Planning resolves existing parents
or exact semantic pending-parent descriptors without writes or fabricated UUIDs.
Future canonical write authorization must explicitly cover parent/binding creation or
reuse; execution handles it atomically with VD/receipt, preserving stale-plan checks,
source attribution and rollback. New material classifications still require human review.

Approve new `factory-body-semantic/2` and `vehicle-definition-body/2` preimages,
with RA-044's five-field powertrain tuple and reviewed body/series semantics.
Coordinate the reserved Candidate v3 boundary with explicitly body-aware planning,
proofs, Matrix/manifest, adjudication, transactional uniqueness and receipt snapshots.
Do not add executable body meaning to existing 2.1.0 metadata or legacy proofs.

Derive presentation choices from actual active canonical combinations in a fixed
model/Generation/year/market root. Trim/parent filtering constrains available
options without hiding an already meaningful body distinction. Single-body roots
need no redundant selector or suffix. Store no independent visibility flag.

Use existing structured slug bases, concise readable body qualifiers when needed,
independent series where meaningful, then appropriate verified manufacturer model/body
codes if necessary. Prefer `-2-door`/`-4-door`, not full UUIDs. Pin deterministic
qualifier selection/order over the reviewed configuration family, not import order.
Code selection requires attributable namespace, exact applicability and stable meaning;
transmission-only QOP differences cannot split identities or become arbitrary suffixes.
Opaque fallback is reserved for unavoidable explicitly reviewed cases. No random repair
or truncation; retain the 180-character limit and ADR-0002 immutability. Full body/series
UUID suffixes are planned in ADR-0011, not implemented in current models/services/URLs.
Existing PKs/UUIDs/slugs, canonical labels, source assertions, receipts and
correspondences remain unchanged. Null legacy associations neither prove one body nor
automatically block matching; actual ambiguous overlap requires targeted reconciliation.

## Accepted scoped amendments

1. **ADR-0010 Decision 2 / ADR-0011 exact supersession:** replace the historical
   Wrangler trim-only body workaround for **new, explicitly body-assessed** MY2024+
   records. Do not supersede historical artifacts or rename imported MY2019–MY2023.
   Transmission/package subordination, Generation and authorization rules remain.
2. **ADR-0011 Decisions / W2 domain §§5/8 and deferred B5 lifecycle:**
   - Expand van-only five-dimension scope to unified seven-field sparse body identity,
     including doors/side doors, while retaining independent series and protected FKs.
   - Replace the universal four-state per-dimension checklist and mandatory missingness
     findings with optional sparse identity-bearing fields. Replace the closed /1
     preimage for new /2 records; do not reinterpret historical /1 artifacts.
   - Narrow the unassessed-legacy overlap gate: null alone is no review requirement;
     actual conflicting/ambiguous identity evidence still requires reconciliation.
   - Permit reviewed source evidence to establish parents within the normal authorized
     candidate/import workflow without independent duplicate curation/publication review.
     Retain explicit canonical write authorization covering any parent/binding creation,
     exact applicability, immutable evidence, stale checks and atomic receipts.
   - Replace planned full body/series UUID slug qualifiers with readable-first policy,
     scoped verified ordering-code criteria and reviewed unavoidable opaque fallback.
     Keep immutable old slugs, length limit, no random suffixes and no backfill.
3. **ADR-0012 / RA-044 reconciliation:** fulfill the required engine-aware body
   preimage successor without changing Candidate 2.1.0 or Engine Proof 2.0 semantics.
4. Coordinate proposed body-aware Candidate/Manifest/Matrix/Resolution/Proof and
   adjudication schema approval with W2 publication body/series snapshot consumers.
   An unchanged Generation correspondence 1.0 may still be reused; new unsupported
   restriction meanings require explicit versioning, not extra hidden fields.

These scoped amendments are accepted by the Project Owner; historical ADR text
and existing serialized artifacts retain their original meaning outside this scope.
ADR-0001 stable identity, ADR-0002 immutable slugs, ADR-0005 evidence/market rules,
ADR-0006 provenance, ADR-0007 exact authorization/atomic receipts, ADR-0008 bounded
adjudication and ADR-0009 measurements separation remain in force.

## Consequences and tradeoffs

A sparse shared body entity adds reusable parents/evidence bindings and one protected
join without requiring extra review for absent fields, but avoids duplicate dimension semantics across every engine/year and avoids
an unsupported Cartesian product of dimension entities. Explicit fields support
indexed independent van facets without a generic configuration engine. The nullable
association preserves legacy operation, while actual ambiguous legacy overlap still blocks
unsafe assessed creates; null associations alone do not. Versioned execution support and migration/preservation tests
must precede any operational use. Real bodies, series and applicability cannot be
seeded from this illustrative design.

## Alternatives considered

- Individual normalized dimension entities: more joins and curation, while still
  requiring a complete supported-combination entity; not justified at this stage.
- Direct VehicleDefinition body columns: simpler access but repeated body meaning
  and provenance across engines/years, less consistent with approved shared identity.
- Slug suffix or canonical trim/engine concatenation: rejected because it fails
  semantic identity or violates the owner naming decision.

## Approval and implementation boundary

The Project Owner accepted the scoped amendments, sparse comparison, successor
identity direction, readable slugs and visibility scope. Exact unresolved wire details
require review before implementation of those portions. The separately authorized
first phase is limited to pure identity/contract foundations and isolated tests.
Persistence, operational migrations, body/series publication, candidate regeneration,
correspondence publication and canonical imports require later explicit authorization.
