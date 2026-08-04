# RA-003 — Core Foundation

## Objective

Create a reusable core application for shared model infrastructure.

## Scope

- Create the Django-generated `core` app.
- Add abstract UUID and timestamp model mixins.
- Refactor the Reference Domain to use them.
- Preserve all existing behavior.
- Do not introduce soft deletion yet.

## Files expected to change

- config/settings.py
- core/apps.py
- core/models.py
- reference/models.py
- reference/tests/test_models.py
- relevant migration files

## Acceptance criteria

- Existing UUID values remain intact.
- Existing timestamps remain intact.
- Public URLs and slugs do not change.
- No concrete database table is created for abstract mixins.
- All existing tests continue to pass.
- New tests verify inherited UUID and timestamp behavior.

## Verification

Run:

python manage.py check
python manage.py makemigrations --check
python manage.py test

## Restrictions

- Do not commit.
- Do not rename existing domain models.
- Do not add soft-delete behavior.
- Do not change public URL patterns.

## Documentation requirements

After the implementation and all verification commands succeed:

- Update `docs/implementation/CURRENT_STATE.md`.
- Update `CHANGELOG.md` under `Unreleased`.
- Create or update any ADR required by this task.
- Update this task's completion record.

Do not describe incomplete or failing behavior as implemented.

## Completion record

Status: Planned

Completion date: Not completed

Files changed: Not completed

Migrations created: Not completed

Verification results: Not completed

Documentation updated: Not completed

ADRs created or updated: Not completed

Deviations and follow-up work: Not completed


## Architecture decision record

If the task is completed successfully, create:

`docs/architecture/ADR/ADR-0003-Core-Infrastructure.md`

The ADR must record:

- why a shared `core` app was introduced;
- what may and may not belong in `core`;
- why the shared model classes are abstract;
- why domain-specific behavior remains in domain applications;
- the risks of turning `core` into a miscellaneous utility package;
- the decision not to introduce soft deletion as part of this task.

Do not mark the ADR as accepted unless the refactor is implemented and all
verification commands pass.