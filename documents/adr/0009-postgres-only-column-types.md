# ADR-0009: Postgres-only column type for long-text columns

- Status: Accepted
- Date: 2026-11-21
- Plan: documents/plans/2026-11-21-persistence-maintainability.md

## Context

`app/db/models.py` defines a module-level alias
`LongString = String().with_variant(mysql.LONGTEXT(), "mysql", "mariadb")` used
by `Code.content` and `dsl_content`. The `LONGTEXT` variant is a ported
colombus artifact: the persistence runtime and test suite target Postgres
exclusively (`postgresql+psycopg`), there is no MySQL/mariaDB deployment, and no
code path selects that dialect. The variant is dead branching that obscures the
actual column type.

## Decision

Drop the MySQL variant. Replace the `LongString` alias with a Postgres-native
long-text type (selling the value domain `LONGTEXT` provides on Postgres), and
remove the now-unused `from sqlalchemy.dialects import mysql` import.

This is a type-metadata change only — it does not alter the rendered schema on
the Postgres target, so the Alembic baseline migration is untouched and the
migration-parity tests continue to pass unchanged.

## Consequences

- Positive: the column definition states the real type instead of a dialect
  fork that never fires.
- Positive: one fewer dead import in a schema that is the single Postgres source
  of truth.
- Negative: none functional. If a MySQL dialect is ever re-introduced, the
  variant can be restored deliberately alongside real MySQL support.
