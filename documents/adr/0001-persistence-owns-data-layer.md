# ADR-0001: Persistence owns the data layer; colombus consumes it via GraphQL

- Status: Accepted
- Date: 2026-11-20
- Plan: documents/plans/2026-11-20-colombus-persistence-migration.md

## Context

The colombus platform currently keeps its persistence inline: SQLModel tables, engine
and a hand-rolled `get_session` dependency live in `colombus/app`, and colombus creates
tables itself via `SQLModel.metadata.create_all`. A dedicated `persistence` repo exists
as a scaffold (FastAPI + Strawberry + Alembic) whose stated purpose is "the persistence
layer for Colombus", but it only carries a demo `User`/`Item` model.

We want a single service that owns the PostgreSQL schema and the domain tables, and
present its content to colombus through a well-defined interface.

## Decision

- The `persistence` project becomes the **single owner** of the PostgreSQL schema for
  the colombus domain tables, managed via Alembic migrations (the current `create_all`
  approach is retired).
- Persistence exposes the database content to colombus over a **Strawberry
  GraphQL API** (read queries + mutations). The persistence API is GraphQL-only;
  the template REST scaffold is dropped once the real surface lands (ADR-0007).
- Ownership moves incrementally (**strangler**): persistence gains the schema and
  GraphQL surface first; colombus drops its own table creation; colombus endpoints
  migrate from direct ORM imports to GraphQL one at a time. The colombus repo is left
  untouched during this implementation.
- Stage 1 covers the data layer + GraphQL only. Domain logic that is not "persistence"
  (colombus's routers/services, the `ppm_to_regex` function, raw-SQL PPM execution)
  stays in colombus and reads persisted data over GraphQL.

## Consequences

- One schema authority (Alembic in persistence); drift between code models and the
  database is caught by migrations and migration-verification tests.
- Colcolombus switches from ORM-in-process to a network API, decoupling deployment and
  versioning of the two services.
- GraphQL is a new public contract that needs contract tests and, later, authN/AuthZ.
- Transition risk during the strangler period: both services must not fight over schema
  creation — colombus stops `create_all` before persistence takes over writers.
