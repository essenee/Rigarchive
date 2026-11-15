# ADR-0002: Immutable Automatic Slugs

- **Status**: Accepted
- **Date**: 2026-08-04

## Context

RigArchive relies on human-readable, SEO-friendly URL patterns for public navigation (e.g., `/vehicles/toyota/4runner/fourth-generation/2007-sr5-40l-v6-4wd-us/`). Slugs are generated from canonical names and configuration fields. If slugs change whenever a record's name or metadata is edited, public URLs break, causing link rot and disrupting search engine indexing.

## Decision

Enforce automatic, immutable slug generation for domain entities:

1. **Automatic Generation**: Slugs are automatically computed from entity naming attributes (e.g., `name` or configuration fields) upon initial record creation.
2. **Immutability**: Slugs are non-editable (`editable=False`) and populated only if the `slug` field is empty (`if not self.slug:`). Once populated and saved, subsequent updates to entity attributes will not change or re-generate the slug.

## Rationale

- **URL Stability**: Ensures public URLs remain stable over the entire lifecycle of a reference entity, preventing broken links.
- **Data Integrity**: Prevents administrative or accidental edits in Django Admin from silently breaking public URL structures.
- **Simplicity**: Avoids complex URL redirect infrastructure for routine field updates.

## Consequences

### Positive
- Public vehicle reference URLs are stable and permanent after creation.
- Eliminates administrative error where slugs are manually mistyped or modified.
- Simplifies caching and canonical URL resolution.

### Negative
- Initial typos in an entity's name at creation time will freeze into the slug unless manually overridden via low-level database operations or custom migrations.
- Rename operations do not automatically update the public URL.

## Alternatives Considered

- **Mutable Slugs (Re-slugify on Save)**: Re-calculates slugs whenever names change. Rejected because it breaks existing public links and causes link rot.
- **Manually Editable Slugs**: Allows Django Admin users to edit slug fields freely. Rejected to protect URL stability and ensure uniform slug formatting.

## Owner-approved amendment — VehicleDefinition corrections

Last Updated: 2026-11-15

The owner explicitly approved this narrow exception on 2026-11-15. The original
rationale and general policy above remain in force for automatic updates and all
other models.

- VehicleDefinition stored slugs never change automatically when other attributes
  are edited. Initial creation retains automatic slug generation.
- Active staff administrators with VehicleDefinition change permission may
  deliberately correct an existing stored slug through Admin, preserving slug
  formatting and generation-scoped uniqueness.
- Admin warns that corrections may invalidate existing public URLs and records
  the old and new values in normal Django Admin change history.
- Primary keys and UUIDs remain immutable. Automated imports cannot correct existing
  slugs; no bulk correction, redirect, alias or slug-history table is introduced.

This exception permits deliberate correction despite the original rejection of
freely editable slugs. It accepts the warned URL-breakage risk for an explicit,
authorized correction while preserving stable URLs under ordinary edits.
