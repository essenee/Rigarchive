# Remaining Engine assignments — read-only analysis

Created: 2026-11-15
Status: Historical review snapshot; subsequent approved assignments recorded separately

## Current qualification (2026-11-15)

The 612-linked / 538-unlinked analysis below is an immutable historical scope,
not the remaining workload today. After subsequent owner changes and 52 approved
MY2021 JL assignments, read-only verification confirms 692 linked / 458 unlinked
of 1,150 definitions, ten Engines and all 73 MY2021 JL records linked.
See `../my2021_jl_engine_associations_20261115.md` for the bounded execution record.
The 81-row correspondence opportunity below must be reassessed against current
links before any further authorization; it is not an executable pending scope.
The Engine implementation checkpoint was committed as `92253b3`; the blocked
commit account below describes the earlier preparation only. Owner image changes
have subsequently been committed separately.

This README is the concise permanent research record. Companion JSON files remain
locally retained historical detail (including exact row pins and evidence hashes),
not current approvals. No unique artifacts have been deleted. The original hash
manifest predates this qualification; its README hash is therefore historical.

Owner-local date is 2026-11-15; capture filenames use UTC 2026-11-16. This report
regenerates `preview_engine_assignments` through SQLite `mode=ro` and query_only.
It does not execute assignments, create Engines, modify snapshots or expand the
manufacturer ingestion pipeline. Existing Engine facts remain authoritative only
for compatible, evidence-supported assignments.

## Historical database snapshot and intentional owner assignment

| Status | Rows |
| --- | ---: |
| Already linked | 612 |
| Unlinked CONFLICT | 61 |
| Unlinked INSUFFICIENT_EVIDENCE | 411 |
| Unlinked NO_REGISTERED_ENGINE | 66 |
| All unlinked | 538 |
| Total VehicleDefinitions | 1,150 |
| Registered Engines | 10 |

No linked conflicts or supported-receipt binding errors. There are no automatic
compatible proposals left under the existing implemented rules. Categories are
freshly computed, not copied from the 611-linked post-batch checkpoint.

The owner intentionally assigned **VehicleDefinition PK926**, UUID
`caca5d4e-e661-4309-b735-dde058ad46f4`, MY2021 US Jeep Wrangler JL Unlimited Willys,
historical descriptor `3.0L V6`, to **Engine PK7**, UUID
`16b0027f-72a9-49cb-9fd2-c55f064c88ed`, code EXJ, registered name
`3.0L V6 Turbo Diesel`. Tuple: 3L, six cylinders, turbocharged, diesel, none.
Current reconciliation classifies it ALREADY_LINKED and compatible. Its slug,
identity, FK and all fields are preserved. It was unlinked in the prior post-batch
preview, explaining the +1 linked / -1 insufficient shift. This owner action is
not treated as unapproved or propagated to any other row.

## Highest-leverage correspondence review: 81 Jeep rows

| Scoped historical descriptor / full classification | Target Engine | Rows |
| --- | --- | ---: |
| JL 2.0L I4, turbo gasoline, none | EC1 PK2 | 35 |
| JL 3.6L V6, NA gasoline, mild_hybrid | ERG PK5 | 23 |
| JL 3.0L V6, turbo diesel, none | EXJ PK7 | 19 |
| JL 2.0L I4, turbo gasoline, plug_in_hybrid | ECX PK6 | 3 |
| JL 6.4L V8, NA gasoline, none | ESG PK3 | 1 |

These five proposed rules are limited to the exact listed MY2020–2021 US Wrangler
JL PK/UUIDs. All five canonical attributes are already known and match one target
registered Engine, with manufacturer identity preserved. For every row, retained
MY2020/2021 planning/Candidate code correspondence, candidate digest, original
candidate file hash, successful receipt target tuple and authentic source bytes
were verified. See proposed_scoped_jeep_correspondences.json for individual pins.
The target is identified by Engine PK/UUID, not by code alone.

These are research recommendations, not newly implemented aliases or approval to
assign. A later task needs owner-approved scope plus validated stale-plan/model
execution. The current executor is pinned to the original 507-row artifact and
will not execute these new proposals; a separately authorized bounded workflow
update is required before a new set can run. PK926 is separate evidence of its own approved relationship; it does
not authorize the other 19 EXJ rows. Those 19 are 2020–2021 diesels with complete,
compatible tuples and their own retained source lineage, not a diesel-size guess.

## Insufficient evidence — 411 records in 21 scoped patterns

The JSON groups include manufacturer, model, Generation, year range, descriptor,
all five current fields, possible registered Engines, known-field conflicts and
receipt-source references. Unknown attributes do not establish compatibility-based
identity; compatible Engine candidates with all facts unknown are not assignments.

| Manufacturer / model / Generation | Years | Descriptor | Rows |
| --- | --- | --- | ---: |
| Toyota / Tacoma / Third Generation | 2016–2023 | 3.5L V6 | 74 |
| Toyota / 4Runner / Fourth Generation | 2003–2009 | 4.7L V8 | 42 |
| Toyota / Tacoma / Fourth Generation | 2024–2026 | 2.4L I4 | 33 |
| Toyota / Tacoma / Second Generation | 2005–2015 | 2.7L I4 | 33 |
| Toyota / Tacoma / Third Generation | 2016–2023 | 2.7L I4 | 32 |
| Toyota / Tacoma / First Generation | 1995–2004 | 3.4L V6 | 31 |
| Toyota / 4Runner / Third Generation | 1996–2002 | 3.4L V6 | 30 |
| Toyota / 4Runner / Sixth Generation | 2025–2026 | 2.4L Turbo I4 | 20 |
| Jeep / Wrangler / JL | 2020–2021 | 3.0L V6 | 19 |
| Toyota / Tacoma / First Generation | 1995–2004 | 2.7L I4 | 17 |
| Toyota / 4Runner / First Generation | 1984–1989 | 2.4L I4 | 14 |
| Toyota / 4Runner / Second Generation | 1990–1995 | 3.0L V6 | 12 |
| Toyota / 4Runner / Sixth Generation | 2025–2025 | 2.4L I4 | 12 |
| Toyota / 4Runner / Second Generation | 1990–1995 | 2.4L I4 | 10 |
| Toyota / 4Runner / Third Generation | 1996–2000 | 2.7L I4 | 10 |
| Toyota / Tacoma / First Generation | 1995–2004 | 2.4L I4 | 10 |
| Toyota / 4Runner / Sixth Generation | 2025–2026 | 2.4L Turbo Hybrid I4 | 8 |
| Jeep / Wrangler / JL | 2021–2021 | 6.4L V8 | 1 |
| Toyota / 4Runner / Fifth Generation | 2010–2010 | 2.7L I4 | 1 |
| Toyota / Tacoma / Second Generation | 2005–2005 | 2.7L V4 | 1 |
| Toyota / Tacoma / Third Generation | 2016–2016 | 2.7L V4 | 1 |

All 391 Toyota unresolved records have all five canonical snapshot facts unknown.
The 19 Jeep diesel plus one Jeep 392 record have complete facts and are descriptor
correspondence problems. This distinction avoids re-adjudicating established Jeep
classifications and avoids filling Toyota facts from names/displacement alone.

Toyota high-volume family work: Tacoma 3.5 V6 (74), later 2.7 I4 (66), cross-model
3.4 V6 (61), 4Runner 4.7 V8 (42), legacy 2.4 I4 (34), early 2.7 I4 (27), 4Runner
3.0 V6 (12). Similar names across generations are not equivalences; code/technical
variant review may split or merge prospective registrations.

Another 65 Toyota rows (45 generic 2.4L I4 + 20 2.4L Turbo I4) warrant a grouped
T24A-FTS investigation, not an approved alias. Generic groups include TRD Pro,
Trailhunter and Platinum labels; their retained source often records only size and
cylinders. Absence of Hybrid in a descriptor cannot establish gasoline/nonhybrid.
The existing gasoline T24A registry row is only a potential target for an evidenced
subset, not all 65. Eight further 4Runner rows explicitly say Turbo Hybrid I4 and
require the deferred genuine-code variant capability and source review; do not use
a made-up code suffix or force them into the existing nonhybrid Engine.

Two Toyota historical `2.7L V4` labels and one Touareg `V8` record need individual
source investigation. A future FK correspondence may preserve historical spelling;
this analysis does not rename, normalize or correct the rows. No new approved alias
is proposed for these three ambiguous descriptors.

## Conflicts — technical mismatches with the name-selected target

| Name-selected Engine | Field | Vehicle value | Registry value | Rows |
| --- | --- | --- | --- | ---: |
| EC3 PK4 | electrification_type | none | mild_hybrid | 35 |
| ERC PK1 | electrification_type | mild_hybrid | none | 23 |
| EC3 PK4 | electrification_type | plug_in_hybrid | mild_hybrid | 3 |

These are 61 real electrification conflicts with the Engines selected by exact
name, but no incorrect existing FK: all 61 records remain unlinked. Existing
canonical tuples instead support the distinct EC1/ERG/ECX variants above. No
registry-data error, incorrect canonical classification or mandatory fact overwrite
has been established. Therefore zero fact-correction cases are confirmed, not
zero mismatches or a claim that all history is unquestionably correct. Preserve
both variants and review name correspondence, rather than repairing either side.

## Missing registered Engine coverage — provisional authoring work list

NO_REGISTERED_ENGINE currently denotes Volkswagen's absent manufacturer registry
coverage, not a complete taxonomy of every missing engine in Toyota. Fifteen
scoped registration **research work items** could cover 381 rows (316 Toyota +
65 Volkswagen), plus one deferred shared-code hybrid work item for eight rows.
This is not a verified assertion that exactly 15/16 Engine records should be
created; authentic code and variant evidence can change that number.

| Work item | Prospective registration family | Years | Potential rows |
| --- | --- | --- | ---: |
| T01 | Tacoma third-generation 3.5L V6 family | 2016–2023 | 74 |
| T05 | Later Tacoma / 2010 4Runner 2.7L I4 family | 2005–2023 | 66 |
| T02 | Tacoma first / 4Runner third-generation 3.4L V6 family | 1995–2004 | 61 |
| T03 | 4Runner fourth-generation 4.7L V8 family | 2003–2009 | 42 |
| T06 | Legacy 4Runner/Tacoma 2.4L four-cylinder families | 1984–2004 | 34 |
| T04 | Early Tacoma/4Runner 2.7L I4 family | 1995–2004 | 27 |
| V02 | Touareg second-generation 3.6L VR6 | 2011–2017 | 21 |
| V04 | Touareg second-generation 3.0L TDI | 2011–2016 | 18 |
| T07 | 4Runner second-generation 3.0L V6 family | 1990–1995 | 12 |
| V06 | Touareg 4.2L V8 | 2004–2009 | 7 |
| V05 | Touareg Hybrid 3.0L V6 family (distinct from TDI) | 2011–2015 | 5 |
| V07 | Touareg 5.0L V10 TDI | 2004–2008 | 5 |
| V01 | Touareg first-generation 3.6L VR6 | 2007–2010 | 4 |
| V08 | Touareg 3.2L V6 | 2004–2006 | 3 |
| V03 | Touareg first-generation 3.0L TDI | 2009–2010 | 2 |

For each work item, the retained JSON lists every PK, descriptor, year range,
receipt-source path and computed source hash where retained. Available enumeration
can establish reported displacement/cylinders for a configuration, but does not
necessarily identify an authentic Engine code or all classifications. Before
Django Admin authoring, the owner needs manufacturer identity/code, variant scope,
short name and evidence for displacement, cylinders, aspiration, fuel and
electrification. No specific unverified engine code is invented in this report.

Touareg `3.0L V6` is especially unsafe to merge: 20 rows have TDI trim labels and
five are Hybrid. `3.6L V6` is VR6-labelled in retained trim context; generic V6
wording alone must not erase genuine code/generation differences. The one `V8`
row has no displacement; do not fold it into the 4.2L group until source evidence
establishes identity. Early and later Toyota 2.7 groups are also kept separate.

## Disjoint workload partition and recommendations

There are **16 distinct unresolved descriptor strings**, **32 scoped exception
patterns**, **five supported proposed Jeep aliases**, **15 provisional registration
work items**, one explicit hybrid-variant work item, and **three immediate
individual-investigation cases**. Future source review can reveal more exceptions.

| Priority | Work | Rows | Decision needed |
| --- | --- | ---: | --- |
| 1 | Five evidence-pinned Jeep correspondences | 81 | Approve exact new scoped rules/rows, then separately authorize validated assignment execution |
| 2 | High-volume Toyota registration families | 316 | Verify authentic codes/variants and complete facts, then human Admin authoring/correspondence approval |
| 3 | Existing T24A screening groups | 65 | Establish conventional/hybrid per-row applicability; do not map by size or generic names |
| 4 | Volkswagen registration families | 65 | Eight scoped family reviews; keep Hybrid and TDI separate; source-led code/variant splitting |
| 5 | Explicit T24A hybrid variant | 8 | Deferred shared-code Engine-variant milestone and subsequent human authoring |
| 6 | V4 / unspecified V8 cases | 3 | Inspect individual retained source lineage; preserve descriptors |
| Total | Non-overlapping unresolved rows | 538 | No execution in this task |

Prioritize the 81 already fully classified Jeep rows and the 74-row Tacoma V6
family review rather than 538 individual approvals. These numbers are opportunity
coverage, not guarantees of assignability. Avoid including broad Toyota 2.4 groups
in a gasoline alias just to inflate the near-term count.

## Verification and Git checkpoint status

The completed implementation re-passed 168 focused tests, Django system checks and
migration drift checks using .venv/bin/python (Python 3.13.1), with isolated memory
databases. The unavailable historical venv/py313 path was not recreated. The full
suite was not repeated; 25 previously documented failures remain historical limits.
SQLite integrity is ok, foreign keys have zero violations, Engine/VehicleDefinition
full fields and live DB bytes remain unchanged during this task. The pre-execution
backup was retained, not restored.

Phase A's 16-file isolated-index checkpoint is prepared but **not committed**:
automatic approval review rejected both attempts because attached-file instructions
were not accepted as trusted commit authorization. No workaround was attempted.
Direct in-chat owner approval is required before retrying that prepared commit.
The normal index remains byte-for-byte unchanged with the two owner JK image
operations. Database, images, unrelated research and unrelated shared-document
sections are excluded from the prepared checkpoint. No push/deployment.

Artifacts: summary.json, insufficient_evidence_groups.json, conflict_groups.json,
no_registered_engine_groups.json, prospective_engine_registration_work_items.json,
proposed_scoped_jeep_correspondences.json, variant_and_individual_review.json,
owner_manual_diesel_relationship.json and analysis_provenance.json. The fresh full
preview remains in ignored backups/review; no unnecessary second multi-megabyte
inventory is added to the proposed commit.
