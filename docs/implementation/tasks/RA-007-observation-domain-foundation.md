# RA-007 — Observation Domain Foundation

## Purpose

Implement the Observation domain foundation as specified in the approved **RA-006 — Observation Foundation Architecture** design document. This introduces the `Observation` model to record statements about vehicle configurations alongside capture context, establishing the architectural boundary between canonical reference data and empirical archive entries.

## User Story

> **As an archive administrator**,  
> **I can record a statement about a specific canonical `VehicleDefinition`**  
> *(including observation details, event date, archive recorder, and contextual source notes)*  
> **so that information entering the archive can be associated with the correct factory configuration without modifying canonical reference data.**

## Scope

### Included
- Create the Observation domain application (`observation` app registered in `config/settings.py`).
- Implement the `Observation` model in `observation/models.py` inheriting from `core.models.BaseModel`.
- Enforce dual identity (Integer database PK + UUIDField external identifier) and timestamp mixins inherited from `BaseModel`.
- Connect `Observation` to `reference.VehicleDefinition` via `ForeignKey` with `on_delete=models.PROTECT`.
- Connect `Observation` to `accounts.User` (`recorded_by`) via `ForeignKey` with `on_delete=models.PROTECT`.
- Implement `title` (`CharField(max_length=255)`), `description` (`TextField`), `observed_on` (`DateField(null=True, blank=True)`), and `source_notes` (`TextField(blank=True)`).
- Register `ObservationAdmin` in `observation/admin.py` for administrator CRUD operations.
- Generate initial database migration `observation/migrations/0001_initial.py`.
- Write unit tests using repository test organization conventions (`observation/tests.py` or `observation/tests/`), calling `full_clean()` to verify model validation, `PROTECT` deletion, non-mutation of reference models, and admin accessibility.
- Update repository documentation (`CURRENT_STATE.md`, `CHANGELOG.md`, and this task completion record).

### Not Included
- Public contribution or submission forms.
- Public views, templates, or URL routes for observations on Reference pages.
- Custom model validation rules beyond standard Django model field constraints.
- Application service layer (`observation/services.py`), unless demonstrated workflow complexity requires it beyond standard Django model validation and Admin forms.
- Additional models (such as separate Observer, Contributor, Source, Evidence, Asset, or Measurement models).
- Any mutation or modification of `reference` models or canonical reference data.

## Implementation Notes

> User accounts referenced by observations are protected from deletion (`recorded_by` uses `on_delete=models.PROTECT`) so archive authorship remains intact. Operational account removal should use deactivation unless a future approved privacy or retention design establishes another policy.

## Repository Changes

Expected files to be created or modified during implementation:

- `config/settings.py` (Register `observation.apps.ObservationConfig` in `INSTALLED_APPS`)
- `observation/__init__.py` (Package initializer)
- `observation/apps.py` (Application configuration)
- `observation/models.py` (`Observation` model definition)
- `observation/admin.py` (`ObservationAdmin` registration)
- `observation/migrations/0001_initial.py` (Initial database migration)
- `observation/tests.py` or `observation/tests/` (Unit test suite following repository conventions)
- `docs/implementation/CURRENT_STATE.md` (Update project status, installed apps, test counts, structure)
- `CHANGELOG.md` (Record unreleased changes under `Unreleased`)
- `docs/implementation/tasks/RA-007-observation-domain-foundation.md` (Update completion record)

## Acceptance Criteria

1. The `observation` app is created and registered in `INSTALLED_APPS` within `config/settings.py`.
2. `Observation` inherits from `core.models.BaseModel` and provides an integer primary key `id`, immutable `uuid` external identity, `created_at`, and `updated_at` timestamps.
3. `Observation.vehicle_definition` is a `ForeignKey` referencing `reference.VehicleDefinition` with `on_delete=models.PROTECT`.
4. `Observation.recorded_by` is a `ForeignKey` referencing `accounts.User` with `on_delete=models.PROTECT`.
5. Under Django model validation:
   - `title` (`CharField(max_length=255)`) and `description` (`TextField`) are required;
   - `observed_on` (`DateField(null=True, blank=True)`) accepts valid dates or `None`;
   - `source_notes` (`TextField(blank=True)`) accepts text or an empty string;
   - no custom validation rules are invented.
6. Unit tests verifying required field constraints explicitly call `full_clean()` because Django model `save()` does not automatically run full model validation.
7. Creating, editing, or deleting an Observation does not save, update, or delete the referenced VehicleDefinition and does not alter any of its persisted field values.
8. Admin integration meets objective access criteria:
   - `Observation` is registered with the Django Admin site;
   - a superuser can access the `Observation` changelist and add view;
   - an unauthenticated request is redirected to the admin login page;
   - no custom permissions or public interfaces are introduced.
9. Attempting to delete a `VehicleDefinition` or `User` referenced by an `Observation` raises a `django.db.models.ProtectedError`.
10. All verification commands pass cleanly without warnings.

## Verification Commands

Executing the following commands must succeed cleanly:

```bash
.venv/bin/python manage.py check
.venv/bin/python manage.py makemigrations --check
.venv/bin/python manage.py migrate --check
.venv/bin/python manage.py test
```

Every command must exit successfully. Any warnings must be investigated and documented, and RA-007 must not introduce new warnings.

## Documentation Requirements

Upon successful implementation and verification:

1. Update `docs/implementation/CURRENT_STATE.md` to reflect:
   - Milestone 4 — Observation Domain Foundation (Completed — RA-007).
   - Registration of `observation` app.
   - Implemented `Observation` model and domain standards.
   - Updated test suite count and repository structure.
2. Update `CHANGELOG.md` under `Unreleased` recording the addition of the Observation domain application and model.
3. Update the **Completion Record** section of this document.

*(No ADR update is required unless implementation causes an architectural deviation from RA-006).*

## Out of Scope

RA-007 explicitly does **not** implement or define the following deferred concepts:

- **Evidence**
- **Assets / Media**
- **Measurements**
- **Compatibility**
- **Knowledge**
- **Maintenance**
- **Vehicle Instances**
- **Public Contribution Workflows**

These concepts are deferred because:
- the initial Observation workflow does not require them;
- their architecture and application boundaries remain unresolved;
- RA-007 must not define them indirectly.

## Completion Checklist

For code review upon task completion:

- [ ] `observation` Django application created and registered in `config/settings.py`.
- [ ] `Observation` model inherits from `core.models.BaseModel`.
- [ ] Dual identity (Integer PK + UUIDField) and timestamp mixins verified.
- [ ] `vehicle_definition` foreign key set to `reference.VehicleDefinition` with `PROTECT`.
- [ ] `recorded_by` foreign key set to `accounts.User` with `PROTECT`.
- [ ] Model validation rules verified: `title` and `description` required; `observed_on` and `source_notes` optional.
- [ ] Tests verifying required fields explicitly call `full_clean()`.
- [ ] Non-mutation criterion verified: creating/editing/deleting an `Observation` leaves target `VehicleDefinition` persisted fields unchanged.
- [ ] `ObservationAdmin` registered in `observation/admin.py`, accessible to superusers, redirecting unauthenticated requests.
- [ ] Migration `0001_initial.py` created and verified via `makemigrations --check` and `migrate --check`.
- [ ] Comprehensive unit tests added following repository conventions covering model constraints, `PROTECT` deletion, and admin registration.
- [ ] `.venv/bin/python manage.py check` passes cleanly without warnings.
- [ ] `.venv/bin/python manage.py test` passes cleanly.
- [ ] `docs/implementation/CURRENT_STATE.md`, `CHANGELOG.md`, and task completion record updated.

---

## Completion Record

Status: Completed

Completion date: 2026-08-04

Files changed:
- `config/settings.py` (Registered `observation.apps.ObservationConfig` in `INSTALLED_APPS`)
- `observation/__init__.py` (Package initializer)
- `observation/apps.py` (Created AppConfig)
- `observation/models.py` (Created `Observation` model inheriting from `BaseModel` with `PROTECT` foreign keys to `VehicleDefinition` and `User`)
- `observation/admin.py` (Registered `ObservationAdmin` for administrator observation record management)
- `observation/migrations/0001_initial.py` (Created initial database migration)
- `observation/tests.py` (Created unit test suite covering validation, dual identity, `PROTECT` deletion, reference non-mutation, and admin access)
- `docs/implementation/CURRENT_STATE.md` (Updated project apps, milestone status, test count, and repository tree)
- `CHANGELOG.md` (Recorded RA-007 completion under `Unreleased`)
- `docs/implementation/tasks/RA-007-observation-domain-foundation.md` (Updated task completion record)

Migrations created:
- `observation/migrations/0001_initial.py`

Verification results:
- `.venv/bin/python manage.py check`: Passed (`System check identified no issues (0 silenced)`).
- `.venv/bin/python manage.py makemigrations --check`: Passed (`No changes detected`).
- `.venv/bin/python manage.py migrate --check`: Passed (`No unapplied migrations`).
- `.venv/bin/python manage.py test`: Passed (`Ran 32 tests in 2.577s — OK`).
- `git diff --check`: Passed (No whitespace or formatting errors).
- `git status --short`: Verified cleanly.

Documentation updated:
- `docs/implementation/CURRENT_STATE.md`
- `CHANGELOG.md`
- `docs/implementation/tasks/RA-007-observation-domain-foundation.md`

ADR status:
- None required (implementation strictly adheres to approved RA-006 design document).
