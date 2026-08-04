# Changelog

All notable changes to RigArchive will be documented in this file.

## Unreleased

### Added

- Reusable `core` Django application (`core.apps.CoreConfig`).
- Abstract model mixins (`UUIDModel`, `TimestampedModel`, `BaseModel`) providing shared UUID identity and timestamp capabilities.
- Unit test suite for core abstract model mixins (`core/tests.py`).
- Architecture Decision Record `ADR-0003-Core-Infrastructure.md`.
- Django project foundation using Python 3.14 and Django 6.0.
- Custom user model (`accounts.User`).
- Reference Domain models (`Manufacturer`, `VehicleModel`, `Generation`, `VehicleDefinition`).
- UUID-based external identities for reference entities.
- Automatically generated stable, immutable slugs.
- Django Admin interfaces for Reference Domain records.
- Public reference vehicle browser with nested URL routing and breadcrumb navigation.
- Shared base template, navigation, and core CSS stylesheet.
- Complete test suite covering models, views, core mixins, and URLs (18 tests passing).
- Gemini CLI project instructions (`GEMINI.md`).
- Task-based implementation workflow specification.
- Architecture Decision Records (`ADR-0001-Entity-Identity-Strategy.md`, `ADR-0002-Immutable-Automatic-Slugs.md`).

### Changed

- Refactored Reference Domain models (`Manufacturer`, `VehicleModel`, `Generation`, `VehicleDefinition`) to inherit from `core.models.BaseModel`.
- Reference slugs are generated automatically and are non-editable (`editable=False`) to guarantee public URL stability.
- Reference records retain integer database primary keys for performance while exposing UUIDs as stable external identifiers.

### Fixed

- Consolidated documentation hierarchy and populated initial Architecture Decision Records.

### Removed

- Removed obsolete `docs/decisions.md` script file containing duplicate model definitions.

### Security

- Enforced protected deletion (`on_delete=models.PROTECT`) on reference model relationships.