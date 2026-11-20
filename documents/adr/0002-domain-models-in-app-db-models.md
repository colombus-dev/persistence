# ADR-0002: Domain SQLModel tables live in a dedicated `app/db/models.py`

- Status: Accepted
- Date: 2026-11-20
- Plan: documents/plans/2026-11-20-colombus-persistence-migration.md

## Context

Persistence owns the colombus data layer. The previous scaffold kept a single
demo `app/models.py` (`User`/`Item`) with no separation between model
declarations and DB wiring. We need the 8 domain tables ported from colombus
(`Project`, `Profile`, `Step`, `CellOutput`, `MetaInstruction`, `Code`,
`Pattern`, `MatchingProfile`) to become the single schema authority, faithful to
colombus's definitions.

## Decision

- All table definitions live in a dedicated **`app/db/models.py`** module. The
  demo `User`/`Item` scaffold is dropped (removed in the cleanup slice).
- Tables are ported **schema-faithfully** from `colombus/app/models/sql_model.py`:
  JSON columns via `Field(sa_type=JSON)`, `code.content` as `LongString`,
  `ondelete="CASCADE"` foreign keys, the `ix_step_profile_id_position` index and
  per-column `index=True`, and `MatchingProfile`'s composite primary key
  (`pattern_hash`, `profile_id`) with no scalar `id`.
- Engine/session/settings stay out of this module — they live in `app/db/session.py`
  and `app/core/config.py` (see ADR-0003).

## Consequences

- SQLAlchemy can resolve the self-referential `Step.previous_step`/`next_step`
  mapper only when the forward reference stays the runtime string
  `Optional["Step"]`; ruff's UP037/UP045/UP007 rewrites are therefore
  per-file-ignored for this module so `ruff check --fix` cannot corrupt it.
- `app/alembic/env.py` will point at `app/db.models.SQLModel` as the
  `target_metadata` (Slice 4).
- The domain schema is validated by model tests seeded from real JSON profile
  fixtures (full `student_0.json` + trimmed `mini_profile.json`).
