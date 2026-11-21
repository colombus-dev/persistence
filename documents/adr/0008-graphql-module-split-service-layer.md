# ADR-0008: GraphQL module split and thin service layer

- Status: Proposed
- Date: 2026-11-21
- Plan: documents/plans/2026-11-21-persistence-maintainability.md

## Context

`app/graphql.py` (276 lines) mixes four distinct responsibilities in one file:
schema type definitions (`@_mapper.type` classes and the manual
`MatchingProfileType`), the read `Query` root, the `Mutation` root, and the
request-context/schema wiring (`build_schema_context`, `get_graphql_context`,
`finalize_schema`). Each of those changes for a different reason, so a single
commit touching one concern churns all of them.

Independent of that, the mutation resolvers embed domain decisions inline —
`create_profile` defaults `json_profile` to `{}`, `save_pattern` defaults
`json_pattern` to a fabricated `{"name": ..., "groups": []}` structure. These
rules are only reachable through GraphQL, so they are untestable in isolation
and hard to reuse if a non-GraphQL caller (a script, a future CLI) ever needs to
build a pattern.

## Decision

Split `app/graphql.py` into single-responsibility modules:

- `app/graphql/types.py` — the mapped `@_mapper.type` classes and the manual
  `MatchingProfileType`.
- `app/graphql/queries.py` — the `Query` root.
- `app/graphql/mutations.py` — the `Mutation` root (thin, delegating to the
  service layer).
- `app/graphql/context.py` — `build_schema_context`, `get_graphql_context`.
- `app/graphql/schema.py` — mapper wiring (the `Uuid`/`AutoString` type map),
  `finalize_schema`, and the module-level `schema`.

Re-export the stable public symbols from `app/graphql/__init__.py` so existing
imports (`from app.graphql import schema, get_graphql_context`) and the current
test imports do not churn.

Add a small service layer:

- `app/services/profiles.py` — `create_profile`, `delete_profile`.
- `app/services/patterns.py` — `save_pattern`, `delete_pattern`.

Each service function owns the creation/defaulting rules currently inline in the
resolvers and returns the built `SQLModel` instance. Resolvers become thin
delegates: pull `info.context["session"]`, call the service, return the mapped
type.

## Consequences

- Positive: each module has one reason to change; domain rules are unit-testable
  without GraphQL; non-GraphQL callers can reuse the same creation logic.
- Positive: schema shape and public imports are unchanged — no API churn.
- Negative: more files for a small package; a light import-graph cost. Given the
  package is expected to grow toward the full colombus persistence surface, the
  upfront split is cheaper than retrofitting later.
- The service layer is intentionally not a repository pattern — DB access stays
  in the models/session; services own only creation/defaulting rules.
