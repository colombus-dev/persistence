# ADR-0010: MatchingProfile.profile uses the dataloader for batching

- Status: Accepted
- Supersedes: ADR-0005
- Date: 2026-11-21
- Plan: documents/plans/2026-11-21-persistence-maintainability.md

## Context

ADR-0005 states the request context carries a
`StrawberrySQLAlchemyLoader(bind=session)` "for relationship batching", and that
`MatchingProfileType` has a `profile` resolver. In the shipped code that
resolver did not actually use the loader: it called
`session.get(models.Profile, self.profile_id)` once per row, so a
`matching_profiles { profile { … } }` query issued one SELECT per match result —
an N+1 that contradicted ADR-0005's own batching intent.

The mapper's dataloader keys on SQLAlchemy `RelationshipProperty` instances, and
`MatchingProfile` held only a bare FK column (`profile_id`) with no relationship,
so the loader could not batch the lookup until a relationship existed.

## Decision

Add a one-directional `MatchingProfile.profile` SQLAlchemy relationship
(no back-populates, no column added) so the loader has a relationship to batch
on. `MatchingProfileType.profile` resolves the profile through
`info.context["sqlalchemy_loader"]`, mirroring the mapper's own relationship
resolver; the per-row `session.get` path is removed. A regression test (written
red first, asserting a single profile-table SELECT) guards the batching.

The `# type: ignore[bad-return]` on that resolver is preserved: the loader
returns mapper-generated runtime types pyrefly cannot prove statically.

## Alternatives considered

- Keep the per-row `session.get`. Rejected: leaves the N+1 and contradicts the
  documented batching design in ADR-0005.
- Add a dedicated `Profile` lookup helper on the type. Rejected: the mapper's
  loader already exists in the context for this exact purpose; a parallel path
  would duplicate it.

## Consequences

- The `matching_profiles` list now loads nested profiles with a constant number
  of queries instead of one per match, matching ADR-0005's batching intent.
- No change to the public GraphQL schema shape or to the database schema (a
  relationship is mapper-only and adds no column); migration-parity tests are
  unaffected.
- This ADR supersedes ADR-0005 (status: superseded) — per the project's ADR
  policy, ADR-0005 is not amended.
