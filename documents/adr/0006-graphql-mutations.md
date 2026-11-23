# ADR-0006: GraphQL mutations for project/profile/pattern lifecycle

- Status: Accepted
- Date: 2026-11-20
- Plan: documents/plans/2026-11-20-colombus-persistence-migration.md

## Context

Slice 5 delivered the read-only query surface. Colombus also needs to create and
delete projects and profiles, and save/delete patterns, through the same GraphQL
endpoint.

## Decision

- `app/graphql.py` adds a `Mutation` root type with `createProject`,
  `createProfile`, `savePattern` and `deleteProject`/`deleteProfile`/
  `deletePattern`.
- Creates and saves return the mapped Strawberry type after `commit()` +
  `refresh()` so the client gets persistent ids and server defaults back.
- Deletes return a small `MutationResult { ok }` envelope; a delete of a
  non-existent row reports `ok: false` rather than raising.
- JSON payloads (`json_profile`, `json_pattern`) are annotated as Strawberry's
  `JSON` scalar; the resolver casts them to `dict[str, Any]` before passing them
  to the SQLModel constructors so the 100% typing gate on `app/` is preserved
  (the scalar is a `JSON`-intersection type pyrefly won't accept as a
  `Mapping[str, Any]` directly).
- All mutations run on the single per-request session already mounted as the
  router context getter, so the commit is atomic with the request.

## Consequences

- The full project/profile/pattern lifecycle can be driven over HTTP.
- Step/metadata writes are intentionally not yet exposed; the colombus endpoint
  migration (cutover slice) owns orchestrating multi-model writes.
- Subsequent slices retain the same request-scoped transaction model.
