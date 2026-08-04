# RigArchive Project Instructions

## Governing documents

RigArchive follows the approved Project Blueprint and Engineering Handbook.

Core architecture:

Presentation
→ Application Services
→ Domain Models
→ Infrastructure

Views stay thin.
Business workflows belong in services.
Models protect domain invariants.
Infrastructure details must remain replaceable.

## Engineering Authority

The project authority is, in order:

1. Current implementation task
2. Architectural Decision Records (ADRs)
3. CURRENT_STATE.md
4. Engineering Handbook
5. Project Blueprint

When these sources appear to conflict, stop and explain the conflict before
making changes.

Do not resolve architectural conflicts by assumption.

## Current stack

- Python 3.14
- Django 6.0.x
- SQLite for local development
- Local media storage
- Django templates
- Vanilla HTML, CSS, and JavaScript
- No React
- GitHub is the source of truth

## Development rules

- Preserve existing Django conventions.
- Do not introduce abstractions without a current use.
- Do not change architecture or model terminology unless the task explicitly requires it.
- Do not alter existing migrations after they have been committed.
- Generate new migrations for model changes.
- Use protected deletion for preserved reference records where appropriate.
- Keep UUIDs separate from Django integer primary keys.
- Keep public slugs stable after creation.
- Add or update tests for every behavioral change.
- Run:
  - python manage.py check
  - python manage.py makemigrations --check
  - python manage.py test
- Do not commit changes unless explicitly instructed.
- Summarize every modified file and any assumptions made.

## Current domains

- accounts
- reference

Future domains must follow the Project Blueprint and Engineering Handbook.

## Task execution

Before editing:

1. Inspect the relevant existing files.
2. Restate the proposed change briefly.
3. Identify whether a migration is required.
4. Make only changes required by the supplied task.
5. Run the complete verification commands.
6. Report failures without hiding or bypassing them.

## Documentation maintenance

Repository documentation is part of the implementation, not a separate manual task.

After successfully implementing and verifying a task, update the relevant
documentation before reporting completion.

For every completed implementation task:

1. Update `docs/implementation/CURRENT_STATE.md` to reflect the repository as
   it exists after the change.
2. Update `CHANGELOG.md` under an `Unreleased` heading.
3. Create or update an ADR only when the task makes or changes a significant
   architectural decision.
4. Update the task file with its final status, completion date, verification
   results, and any deviations from the specification.
5. Do not document planned behavior as implemented behavior.
6. Do not mark a task complete when tests or required checks fail.
7. Keep documentation changes in the same working tree as the implementation,
   but do not commit unless explicitly instructed.

### CURRENT_STATE.md rules

`docs/implementation/CURRENT_STATE.md` must describe only the current,
verified implementation.

Update, as applicable:

- current technology versions;
- installed Django applications;
- implemented models and relationships;
- URL and template structure;
- service-layer workflows;
- tests and verification status;
- completed milestones;
- next approved task;
- repository documentation and tooling.

Do not turn `CURRENT_STATE.md` into a chronological log. Replace outdated
statements rather than appending contradictory information.

### CHANGELOG.md rules

Use this structure:

- Added
- Changed
- Fixed
- Removed
- Security

Record user-visible, developer-visible, architectural, schema, workflow, and
documentation changes. Do not include trivial formatting or temporary debugging
steps.

### ADR rules

Create an ADR when a decision:

- affects multiple applications or future development;
- changes domain or dependency boundaries;
- establishes a persistent identity, storage, migration, security, API, or
  infrastructure strategy;
- adopts a shared architectural abstraction;
- would reasonably cause a future contributor to ask why the approach was
  chosen.

Do not create ADRs for routine implementation details.

Use the next available four-digit ADR number and the standard ADR template.
An ADR must include:

- Status
- Date
- Context
- Decision
- Rationale
- Consequences
- Alternatives considered

New ADRs begin with status `Accepted` only when the implementation task has
successfully completed and the decision is in effect.

### Task completion rules

At the end of a task, append or update a completion section in the task file:

- Status
- Completion date
- Files changed
- Migrations created
- Verification commands
- Verification results
- Documentation updated
- ADRs created or updated
- Deviations and follow-up work

Preserve the original objective, scope, acceptance criteria, and restrictions.

## Repository Boundary

The repository root is the maximum permitted workspace.

The agent may inspect and modify files located inside the repository as
required to complete the current task.

The agent must never intentionally inspect, modify, or execute commands that
target files or directories outside the repository.

If a task appears to require leaving the repository, stop immediately and ask
for confirmation before proceeding.

Never infer permission from previous conversations. Only explicit instructions
given in the current session may override these restrictions.

### Shell Command Policy

Execute only the shell commands that are directly required to complete the
current task.

Do not explore the repository unnecessarily.

Do not inspect unrelated files or directories.

Do not inspect hidden directories unless they are directly relevant to the
current task.

Before executing any command that modifies files, ensure the target is within
the repository workspace.

### Operating System Safety

Never:

- modify operating system configuration;
- install, remove, or upgrade software;
- modify shell startup files;
- modify Git configuration;
- change filesystem permissions;
- use `sudo` or elevated privileges;
- access user secrets, credentials, SSH keys, keychains, or browser data.

If any of these actions appear necessary, stop and explain why before
requesting explicit approval.

### Git Safety

Never:

- commit;
- push;
- merge;
- rebase;
- rewrite Git history;
- delete branches;
- modify Git remotes;

unless explicitly instructed in the current session.

Repository changes should remain uncommitted for human review.

### Security Principles

Operate with the principle of least privilege.

Make the smallest change necessary to satisfy the task.

Prefer modifying existing files over creating new ones unless the task requires
new files.

Do not broaden the scope of a task.

If instructions are ambiguous, ask for clarification rather than making
architectural assumptions.

If any requested action appears unsafe, destructive, or inconsistent with the
Project Blueprint, Engineering Handbook, CURRENT_STATE.md, or the current task
specification, stop and explain the concern before proceeding.

## Protected Project Files

Do not modify, rename, truncate, replace, or delete:

- `Gemini.md`

unless the user explicitly instructs you to do so in the current session.

Treat this file as read-only project governance.