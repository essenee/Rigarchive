# ADR-0001: Entity Identity Strategy

- **Status**: Accepted
- **Date**: 2026-08-04

## Context

RigArchive entities (such as Manufacturers, Vehicle Models, Generations, and Vehicle Definitions) require stable public references while preserving efficient internal database performance and join operations. Standard Django models rely on auto-incrementing integer primary keys, which excel at relational indexing and foreign key lookup speeds but expose sequential sequential IDs that can be fragile or guessable when exposed externally.

## Decision

Adopt a dual identity strategy for domain entities across RigArchive:

1. **Internal Primary Key**: Use auto-incrementing integer primary keys (`id = models.BigAutoField(primary_key=True)`) for database joins, internal foreign key indexing, and Django ORM relationships.
2. **External Public Identity**: Assign a universally unique identifier (`uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)`) to every entity.

Public APIs, integration contracts, and external references will consume UUIDs, while internal database tables maintain integer foreign key relationships.

## Rationale

- **Performance**: Integer foreign key joins in SQLite and PostgreSQL are smaller and faster than 128-bit UUID join indexes.
- **Stable Identity**: UUIDs provide globally unique, non-sequential, and unguessable external identifiers for integrations and API consumers.
- **Django Compatibility**: Preserves default Django ORM conventions and admin integrations while exposing UUIDs where external persistence is needed.

## Consequences

### Positive
- Relational joins and index lookups remain highly performant.
- External systems can reference entities via UUIDs without coupling to internal database row IDs.
- Avoids exposing database sequence counts to public clients.

### Negative
- Models store both an integer primary key and a UUID field, slightly increasing storage footprint per row.
- Developers must explicitly choose whether internal service logic queries by integer PK or external UUID.

## Alternatives Considered

- **UUID as Primary Key**: Replaces integer primary keys entirely with UUID fields. Rejected to preserve small foreign key index sizes and standard Django relationship conventions.
- **Integer Primary Keys Only**: Exposes integer primary keys publicly. Rejected because sequential integer IDs leak scale and are vulnerable to enumeration attacks.
