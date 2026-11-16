Current milestone

RA-003
Core Infrastructure

Milestone 4
Knowledge & Evidence Architecture Design

Milestone 5
Knowledge / Evidence implementation

Future

Evidence

Media

Compatibility

Maintenance

Generation Page Community Contributions

Status: Planned, not implemented.
Priority: After the upcoming higher-priority Vehicle navigation tab model-selection work.

The Builds and Mods and Service Guides cards will eventually invite contributions associated with the selected vehicle generation.
Planned calls to action: Builds and Mods — "Click to add a build or mod"; Service Guides — "Click to add a service guide".

Generation pages must eventually support multiple Builds and Mods entries and multiple Service Guide entries, displayed as individual content cards. Empty-state placeholders and populated-state content grids are distinct presentation states; the current placeholders do not impose a permanent one-card-per-section constraint. The populated-state design will be addressed alongside the future contribution workflow, after the higher-priority Vehicle navigation model-selection task.

Future design work must address contribution workflows, content ownership, moderation, permissions, media uploads, and the distinction between user-submitted content and canonical vehicle reference data.
No contribution prompts, submission interfaces, models, migrations, views, forms, routes, or upload infrastructure are implemented by this planning entry. Detailed architecture and domain decisions remain open.

MY2024 Wrangler JL — Receipt Snapshot Compaction

Status: Deferred — not authorized.
Priority: Low; optional storage optimization.

Scope: MY2024 Jeep Wrangler JL, Generation PK 32; 31 successful Body3.1 canonical import receipts containing 5,403,815 bytes (approximately 5.15 MiB) of measured snapshot JSON. These snapshots embed body-aware plans, manifests, and review/baseline dependencies. Preliminary potential database savings are approximately 4.5–5.0 MiB; this estimate has not been verified by simulation and is distinct from the measured JSON size.

Reason for deferral: The completed MY2021 and MY2022 receipt cleanups reduced the development SQLite database from approximately 61.68 MiB to 24.69 MiB. The current size is acceptable; additional cleanup is not presently necessary. This task is neither approved nor scheduled or in progress, and does not change current project priorities.

Future prerequisites:

1. Verify the exact MY2024 receipt scope and current database baseline.
2. Audit Body3.1-specific consumers and evidence dependencies.
3. Preserve complete original receipt snapshots and historical proof material in verified external archives.
4. Authenticate the applicable approval, Matrix, plan, and manifest evidence.
5. Design a separately bounded MY2024 revalidation and compact-record profile; do not assume MY2021/MY2022 compact-record semantics apply directly.
6. Verify that body-aware import history and canonical identity remain intact.
7. Run an isolated replacement and SQLite compaction simulation.
8. Request separate human authorization before any live database modification.

Reconsideration trigger: Database size, deployment storage limits, backup costs, or another demonstrated operational need justifies further optimization.

Reference: [Receipt snapshot storage audit — MY2024 ranking and Body3.1 findings](../research/next_import_receipt_snapshot_cleanup_audit_20261116.md).
