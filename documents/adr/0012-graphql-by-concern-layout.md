# ADR-0012: GraphQL module structured by concern, not by domain

- Status: Accepted
- Date: 2026-11-21

## Context

The persistence API exposes a single GraphQL surface served by FastAPI at
`/graphql`. On the wire the schema is shaped by layer, not by domain: there is
one `Query` root (all read fields) and one `Mutation` root (all writes), and
read types are mapper-generated over the domain tables.

colombus partitions its adapter layer **by domain** into one router per resource
(`profiles`, `patterns`, `projects`, ...), because each router grew many
endpoints. persistence was asked whether `app/graphql/` should mirror that
(one `profile/`, `pattern/`, `project/` subpackage), or stay a thin adapter
organized **by concern** (`types.py`, `queries.py`, `mutations.py`,
`context.py`, `schema.py`).

The whole `app/graphql/` package is ~360 lines across six small files, and it
is deliberately thin: read resolvers pull from the request-scoped session,
mutation resolvers delegate create/delete to `app/services/` (ADR-0008). Domain
logic lives one level down in `app/services/`, split by domain already.

## Decision

Keep `app/graphql/` organized **by concern**, as it is today:

- `types.py` — all GraphQL object types (mapper-generated read types + the
  manual `MatchingProfileType`).
- `queries.py` — the `Query` root and its read resolvers.
- `mutations.py` — the `Mutation` root and its write resolvers.
- `context.py` — context builders for the request-scoped session/loader.
- `schema.py` — schema assembly (`finalize_schema`, the packaged `schema`).
- `__init__.py` — the stable public surface.

Domain separation is deliberately **not** re-introduced at this layer. Each
mutation resolver is a thin delegate over a domain service in `app/services/`
(`profiles.py`, `patterns.py`, `projects.py`), so a domain's read/write/type
surface is already co-located one directory down, where it can be unit-tested
in isolation (ADR-0011).

## Alternatives considered

- **Split `graphql/` by domain**, mirroring colombus' routers — one subpackage
  per resource, roots assembled by Strawberry class inheritance
  (`class Query(ProfileQuery, PatternQuery, ProjectQuery)`). Rejected: the
  adapter is ~360 lines and thin; the by-domain split adds a folder per domain
  plus inheritance indirection to hold a handful of resolvers, and the coupling
  it would dissolve (the shared session-context resolver plumbing) is shared by
  every resolver regardless. colombus split routers because each grew many
  endpoints; persistence's `mutations.py` is ~110 lines. Domain co-location is
  deferred to where the write/read surface grows materially.

## Consequences

- The adapter layout mirrors the GraphQL shape (one Query root, one Mutation
  root), so "where are the queries/writes/types" has a single obvious file.
- A new domain feature touches `types.py` + one file in `app/services/` + one
  resolver in `queries.py`/`mutations.py` — the domain logic stays reachable
  and testable without the schema.
- Mutation resolvers stay thin delegates; `app/services/` remains the home of
  domain rules. Any domain whose create/delete is still inlined in
  `mutations.py` (rather than a service) is drift from this decision and should
  be extracted to a matching service.
