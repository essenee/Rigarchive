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
- core/__init__.py
- core/apps.py
- core/models.py
- core/tests.py
- reference/models.py
- docs/implementation/CURRENT_STATE.md
- CHANGELOG.md
- docs/architecture/ADR/ADR-0003-Core-Infrastructure.md

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

Status: Completed

Completion date: 2026-08-04

Files changed:
- `config/settings.py` (Registered `core.apps.CoreConfig` in `INSTALLED_APPS`)
- `core/__init__.py` (Created package init)
- `core/apps.py` (Created AppConfig)
- `core/models.py` (Created abstract mixins `UUIDModel`, `TimestampedModel`, and `BaseModel`)
- `core/tests.py` (Created tests for mixin abstraction, table non-existence, and inheritance)
- `reference/models.py` (Refactored `Manufacturer`, `VehicleModel`, `Generation`, and `VehicleDefinition` to inherit from `BaseModel`)
- `docs/architecture/ADR/ADR-0003-Core-Infrastructure.md` (Created accepted ADR)
- `docs/implementation/CURRENT_STATE.md` (Updated status, apps, ADRs, test counts, structure)
- `CHANGELOG.md` (Recorded RA-003 completion under Unreleased)
- `docs/implementation/tasks/RA-003-core-foundation.md` (Updated task completion record)

Migrations created:
- None required (`No changes detected`). Moving field definitions to abstract base classes preserved exact field names and types.

Verification results:
- `.venv/bin/python manage.py check`: Passed (`System check identified no issues (0 silenced)`).
- `.venv/bin/python manage.py makemigrations --check`: Passed (`No changes detected`).
- `.venv/bin/python manage.py test`: Passed (`Ran 18 tests in 0.038s — OK`).

Documentation updated:
- `docs/implementation/CURRENT_STATE.md`
- `CHANGELOG.md`
- `docs/implementation/tasks/RA-003-core-foundation.md`

ADRs created or updated:
- `docs/architecture/ADR/ADR-0003-Core-Infrastructure.md` (Status: Accepted)

Deviations and follow-up work:
- None. Implementation adhered strictly to specification.


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