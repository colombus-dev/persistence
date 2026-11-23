# Persistence API

The persistence layer for Colombus — a FastAPI service exposing the domain
PostgreSQL schema through a Strawberry GraphQL API at `/graphql`, plus a
lightweight `GET /health` liveness probe.

## Requirements

* [Docker](https://www.docker.com/).
* [uv](https://docs.astral.sh/uv/) for Python package and environment management.

## Local Development

We use [prek](https://github.com/j178/prek) for pre-commit:

```console
$ uv run prek install  # one time to init pre-commit
$ uv run prek run
$ uv run prek run --all-files  # on a clean tree (otherwise hooks skip everything)
```

Start PostgreSQL and run the app:

```console
$ docker compose up -d persistence_db
$ uv sync
$ uv run bash scripts/prestart.sh   # runs alembic upgrade head
$ uv run fastapi dev --port 8187
```

The API is available at `http://localhost:8187` with the GraphQL endpoint at
`/graphql` and a health check at `/health`.

## Running the app in Docker Compose

```console
$ docker compose up --build
```

The app is served on `http://localhost:8187` (see `compose.override.yml`).

## Tests

The test tree is split into two tiers ([ADR-0011](./documents/adr/0011-testing-tier-split.md)):

- `tests/unit/` — DB-free: pure builder/defaulting rules and mocked-session
  resolver tests. Runnable **without** Postgres running:
  ```console
  $ uv run pytest tests/unit
  ```
- `tests/integration/` — needs the real database: session-bound services,
  GraphQL query/mutation round-trips, DB round-trips, migration-vs-model parity,
  and the HTTP contract.

The integration tier needs the `app_test` and `app_mig_test` databases on a
running Postgres (see `docker compose up -d persistence_db`). Then:

```console
$ uv run bash scripts/test.sh        # full suite (unit + integration) + coverage
$ uv run pytest tests/integration    # integration tier only
```

The full suite exercises the real database, including migration-vs-model parity
and GraphQL query/mutation round-trips.

## Migrations

The Alembic baseline migration is the single authority for the DB schema. After
changing a model, create a revision and apply it:

```console
$ uv run alembic revision --autogenerate -m "Describe the change"
$ uv run alembic upgrade head
```

## Layout guidance

- Models and schema authority: `app/db/models.py` and `app/alembic/`.
- Engine/session setup: `app/db/session.py`.
- GraphQL schema (queries, mutations, context wiring): `app/graphql/`
  (`types.py`, `queries.py`, `mutations.py`, `context.py`, `schema.py`).
- Domain creation/defaulting rules: `app/services/`.
- FastAPI entrypoint and routing: `app/main.py`.
- Settings (`.env` at the repo root): `app/core/config.py`.
