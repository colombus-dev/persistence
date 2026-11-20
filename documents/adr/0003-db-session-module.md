# ADR-0003: DB engine and per-request session live in `app/db/session.py`

- Status: Accepted
- Date: 2026-11-20
- Plan: documents/plans/2026-11-20-colombus-persistence-migration.md

## Context

Persistence's scaffold created its engine inline in `app/core/db.py` with a
no-op `init_db`. Colombus configures its engine with `pool_pre_ping=True` and a
per-connection `statement_timeout` so sluggish queries are aborted
(`QUERY_TIMEOUT_SECONDS`). We want the persistence service to use the same
behaviour and to expose a single testable session dependency for GraphQL and
the (transitional) REST paths.

## Decision

- Engine construction and the per-request session live in a dedicated
  **`app/db/session.py`**.
- `create_db_engine(url)` builds an engine with `echo=False`,
  `pool_pre_ping=True` and a `connect_args` carrying
  `-c statement_timeout=<QUERY_TIMEOUT_SECONDS * 1000>` ms — faithful to
  colombus. `engine` is the module-level instance built from
  `settings.DATABASE_URL`.
- `get_session()` is a generator yielding a `Session` bound to that engine,
  suitable for FastAPI/Strawberry dependency injection.
- `app/core/config.py` gains `QUERY_TIMEOUT_SECONDS: int = 10`, matching
  colombus's constant.

## Consequences

- Stale pooled connections are detected (pool_pre_ping) and runaway queries are
  time-boxed at the Postgres level.
- Tests inject their own engine (`app_test` on localhost) and can assert the
  engine carries the right flags without a real connection by recording the
  `create_engine` call.
- The legacy `app/core/db.py` engine/`init_db` remains only until the REST demo
  and GraphQL slices are wired onto this session (as is `app/api/deps.py`).
