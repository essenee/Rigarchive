## 2026-08-04

### Added
- Reference Domain public browser.
- UUID identity for reference entities.
- Automatic immutable slug generation.

### Changed
- Slugs are now generated automatically and are no longer editable.
- Vehicle definitions retain integer primary keys while exposing UUIDs for stable external identity.

### Planned
- Introduce `core` app with shared model mixins.

# Changelog

All notable changes to RigArchive will be documented in this file.

## Unreleased

### Added

- Django project foundation using Python 3.14 and Django 6.0.
- Custom user model.
- Reference Domain models for manufacturers, vehicle models, generations, and vehicle definitions.
- UUID-based external identities.
- Automatically generated stable slugs.
- Django Admin interfaces for Reference Domain records.
- Public reference vehicle browser.
- Shared templates, breadcrumb navigation, and base stylesheet.
- Model and public-view tests.
- Gemini CLI project instructions.
- Task-based implementation workflow.

### Changed

- Reference slugs are generated automatically and are not editable through Django Admin.
- Reference records retain integer database primary keys while exposing UUIDs as stable external identifiers.