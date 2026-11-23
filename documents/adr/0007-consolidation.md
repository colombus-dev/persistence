# ADR-0007: Consolidation — remove demo scaffold, pin deps

- Status: Accepted
- Date: 2026-11-20
- Plan: documents/plans/2026-11-20-colombus-persistence-migration.md

## Context

The real domain layer (models, engine/session, Alembic baseline, GraphQL query +
mutation surface) has landed across slices 2–6. The FastAPI scaffolding
inherited from the template — `User`/`Item` models and the REST CRUD routes —
still sits alongside it and must not ship.

## Decision

- Delete the demo `User`/`Item` scaffold and every module that only served it:
  `app/models.py`, `app/crud.py`, `app/initial_data.py`, `app/utils.py`,
  `app/core/db.py`, `app/core/security.py`, and the whole `app/api/` router
  tree (`main.py`, `deps.py`, `routes/items.py`, `routes/graphql.py`).
- `app/main.py` mounts only the GraphQL router at `/graphql`; the demo REST
  route include is removed.
- Empty test package stubs (`tests/crud/`, `tests/utils/`) are removed. The
  JSON fixture helpers already live in `tests/` (`profile_utils.py`,
  `profile_types.py`).
- Dependency hygiene: `strawberry-graphql[fastapi]` is pinned to the exact
  version `==0.341.2` (it had been `>=`), matching the project's reproducibility
  rule of exact pins; `uv.lock` is regenerated.
- Correct a plan-header formatting glitch (`Status: In progressScope`).

## Consequences

- The package now contains only the domain/persistence surface; no demo REST
  endpoints, no dead CRUD code, and no orphaned test stubs.
- `app/main.py` has just two exported symbols of note: the `app` and the
  mounted router — plus the schema/context helpers in `app/graphql.py`.
- The 100% typing gate is unaffected; `app/core/config.py` stays at 94%
  (the only uncovered line is the psycopg-driver validator's fallback
  `return`, unreachable since every test DB URL already uses the
  `postgresql+psycopg` scheme), so total app coverage sits at ~99%.
