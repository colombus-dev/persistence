# AGENTS.md

Conventions for agents in `persistence` repo. Follow these unless human says otherwise.

## Non-negotiables

- **Ask before committing.** Never run `git commit` (or `--amend`, `push`, etc.)
  without explicitly asking first and showing what will be committed. Wait for go-ahead.
- **Document your code when necessary.** Non-self-evident public modules/classes/functions
  get concise docstrings. Keep docs true to code.
- **Run pre-commit before finishing.** Pass `pre-commit run --all-files` (or `pre-commit
  run` on staged files) and fix everything it flags before claiming done. Config in
  `.pre-commit-config.yaml`: ruff import sorting + formatting, pyrefly type checking (100%
  typing coverage of shipped code in `app/`; `tests/` and `alembic/` excluded), coverage
  gate (below), and Whitespace/EOF/YAML-TOML/merge-conflict/debug-statement checks.

## Engineering workflow

- **Test-Driven Development.** New feature/bugfix: write failing test first, watch it fail
  for the right reason (feature missing, not typo), then minimal code to pass. Run full
  suite before finishing.
- **Tests live in dedicated `tests/` directory**, named `test_*.py`, not inline in source.
- **FastAPI and Strawberry stack for `app/`.** Single FastAPI app (`app.main:app`) serving
  Strawberry `GraphQLRouter` at `/graphql`; no REST surface. Read types generated with
  `strawberry-sqlalchemy-mapper` (`always_use_list=True`); `MatchingProfile` mapped manually
  (composite PK). Resolvers read SQLAlchemy session from request context
  (`info.context["session"]`) and use mapper's dataloader
  (`info.context["sqlalchemy_loader"]`). Be conservative about `async def` — only for truly
  async work.
- **Conventional Commits with mandatory scope.** Messages: `type(scope): description` (e.g.
  `feat(db): ...`, `test(alembic): ...`, `docs(adr): ...`). Scope always required; use `core`
  when no component fits. Short, lowercase imperative description. Logically distinct changes
  in separate commits (e.g. a test and the doc wording it substantiates get two commits).
- **Atomic commits per implementation slice.** Each stage of the testing-strategy plan
  (`documents/plans/2026-11-21-testing-strategy.md`) ships as its own logically distinct
  commit (or next-of-kin scoped commits). Don't bundle multiple stages. A stage isn't done
  until its tests are committed alongside the code they substantiate.

## Testing strategy

Test tree split by session boundary (ADR-0011):

- `tests/unit/` — DB-free, fast, no DB fixtures in `conftest.py`. Holds pure builders
  (`create_profile`, `create_pattern`) and any resolver/contract tests that mock the session.
  Must pass with Postgres **down**.
- `tests/integration/` — needs live session: `delete_*` services, GraphQL queries/mutations,
  DB round-trips, alembic parity, HTTP contract.
- Tier rule: `def f(session, ...)` → integration; `def f(*, scalars...) -> Row` → unit.
  Convention-only enforcement — unit `conftest.py` defines no `session`/`engine`/`client`
  fixtures, so accidental DB dependency fails loudly at call time.
- Use `pytest.mark.parametrize` for enumerable input→expected unit cases (defaulting truth
  tables, delete-`False` contract). Do **not** parameterize DB-bound mutation suites — their
  per-resource setup is the value.
- **Every test must earn its place.** Each test pins a distinct piece of business logic.
  Reject tests that merely re-verify the same wire/boundary with a different label, edge
  cases with no distinct logic, or tests of test-only helpers. If a test adds no clear
  code-quality benefit, drop it rather than commit for coverage's sake.
- Mock = boundary replacement, never the wiring under test: mock the session or service
  layer; never mock `app/services/`'s pure builders into "testing" them. Prefer returning
  real in-memory `models.*` rows over bare `unittest.mock.Mock`s in resolver tests. Unit tier
  ships **two** resolver mock seams (session + service). Router `context_getter` seam is **not**
  shipped: real `app.main` router resolves `Depends(context_getter)` at
  construction (can't rewire), ephemeral router diverges from production, and integration API
  suite already covers the true HTTP path.

### Coverage gate (contribution rule)

New contributions must be tested/covered; two layers:

- **Layer A — global floor.** `[tool.coverage.report] fail_under = 80` in `pyproject.toml`;
  enforced on every `coverage report` and CI. Suite cannot sink below 80.
- **Layer B — contribution gate (pre-commit).** For each `app/*.py` file in staged diff, suite
  runs **once** and that file's coverage must be ≥ 80%, else commit blocked. Shipped as
  `local-coverage-gate` hook (`scripts/coverage-gate.sh`, mirrors pyrefly/vulture/bandit
  hooks). Skips when no `app/*.py` changed (docs/config commits). Requires Postgres up (full
  suite run).

Deferred future options (recorded, not shipped pending unit tier): PBT (Hypothesis, scoped to
pure *shipped* logic — not test-only helpers like `encode_profile`) and mutation testing
(mutmut, precondition = unit tier exists, not "DB-up").

## graphify

Knowledge graph at `graphify-out/` (`graph.html` to browse, `graph.json` raw data,
`GRAPH_REPORT.md` audit report). Surfaces god nodes, community clusters, surprising
connections — cross-cutting structure greps can't reveal.

**Before implementing/debugging/refactoring, consult the graph** to see how a symbol relates
to the system. When graph.json exists, run `graphify query "<question>"` before first
grep/search/source-file read for a codebase question; put this rule in every subagent prompt
that explores code. Read raw files only for lines the graph or an earlier read already
located. Use `graphify path "<A>" "<B>"` for relationships, `graphify explain "<concept>"`
for focused concepts. Under a Markdown heading, `graphify section "<heading>"` prints that
section's text — no need to open the .md. These return a scoped subgraph, far smaller than
GRAPH_REPORT.md or raw grep. If `graphify-out/wiki/index.md` exists, use it for broad
navigation instead of raw source browsing. Read GRAPH_REPORT.md only for broad architecture
review or when query/path/explain don't surface enough context.

**Hard rule: never open a source file before running `graphify query`.** Grep/file-read only
after a query fails or a subgraph already located the lines. When dispatching a subagent to
explore, its prompt must start with a run of `graphify query "<subject>"` — don't let it cold-
grep from scratch.

Trace surprising connections and community bridges before changing shared abstractions
(`app/db/models.py`, `app/db/session.py`, `ingest_profile()`) — they typically wrap multiple
subsystems.

**Keep graph current, but watch cost.** Two update modes:

- **Code-only change → `graphify update .` (AST-only, cheap, no subagents, no API cost).**
  Use this for any change touching only `.py` files. This is the default for code edits.
- **Full semantic re-extract** (docs/ADRs/skills changed, needs subagent extraction + model
  tokens) is expensive. Do it only when you judge it required. **When you think semantic
  re-extraction is needed, ask the reviewer first** — don't trigger it unprompted.

When a graph exists, answer corpus questions from it rather than rebuilding. Rebuild only
when corpus changed materially.

- Dirty graphify-out/ files expected after hooks or incremental updates; dirty graph files are
  not a reason to skip graphify. Skip only if the task is about stale/incorrect graph output,
  or the user explicitly says not to use it.
- A committed graphify-out/graph.json is rewritten whole on every build, so a large diff in a
  PR is expected. Don't flag it as churn or suggest skipping the graph rebuild or its hooks.

## Reproducibility

- Pin dependencies to **exact** versions (`==`), never `>=`, in `pyproject.toml`. Regenerate
  `uv.lock` via `uv lock` when deps change.
- Python requires `==3.14.*` (see `.python-version`); use `uv` to manage the env.
- Test suite needs running Postgres on `127.0.0.1:5432` with `app_test` and `app_mig_test`
  databases. If `persistence_db` container is down, suite fails with `connection refused`
  errors that masquerade as a code regression. Before triaging test failures, confirm DB is up
  (`docker compose up -d persistence_db`). (Observed: SIGKILL'd db container produced 23
  spurious errors; suite green again once DB restarted — no code change.)

## Documentation layout

- **Implementation plans** → `documents/plans/YYYY-MM-DD-<topic>.md`
- **Architecture decisions (ADRs)** → `documents/adr/<NNNN>-<slug>.md`
- Plan docs written for **human reviewers**, not subagents. Concise, high-signal summary (goal,
  approach, key decisions, deferred items) readable in ~a minute — not verbose task-by-task
  breakdown. If human already explained an approach, mirror that summary.
- `AGENTS.md` holds project-wide rules; `README.md` documents how to run/test the API.
- Keep ADRs truthful with shipped code. **ADR policy (Martin Fowler): never amend.** Once an
  ADR is accepted, never reopened/edited/amended. When a later decision changes a past one,
  record new ADR and mark old "superseded" (link to new). Append-only log of what governed code
  and when.

## Repo orientation

- `app/` — installed package (importable as `app.*`):
  - `app/main.py` builds FastAPI app and mounts GraphQL router at `/graphql`.
  - `app/graphql/` Strawberry schema as a package: `types.py` (auto-mapped read types + manual
    `MatchingProfileType`), `queries.py` (`Query` root), `mutations.py` (`Mutation` root),
    `context.py` (context helpers `build_schema_context`, `get_graphql_context`), and `schema.py`
    (`finalize_schema`, assembled `schema`). `app/graphql/__init__.py` re-exports stable public
    symbols. Organized **by concern** (ADR-0012).
  - `app/services/` — thin application service layer (`profiles.py`, `patterns.py`,
    `projects.py`) owning creation/defaulting rules; mutation resolvers delegate to it.
  - `app/db/models.py` — 8 domain SQLModel tables (Postgres schema authority).
  - `app/db/session.py` — `create_db_engine` (`pool_pre_ping`, `statement_timeout` from
    `QUERY_TIMEOUT_SECONDS`) and per-request `get_session()` generator.
  - `app/core/config.py` — DB + app settings.
  - `app/alembic/` — Alembic config and baseline migration (`versions/19aacbaabe42_*`), single
    schema source of truth.
- `tests/` — dedicated test package, split into `tests/unit/` (DB-free) and
  `tests/integration/` (needs live session). See "Testing strategy" above; e.g. `tests/db/`,
  `tests/graphql/test_mutations.py`, `tests/alembic/test_migrations.py`,
  `tests/fixtures/profiles/`.
- `documents/` — plans and ADRs.
- `.agents/skills/` — project skills (e.g. FastAPI) and `skills-lock.json`.

## Schema/migration testing notes (learned)

- **Migration vs. model parity** enforced per column, not just per table. Assert column **name
  and nullability** against models via `inspector.get_columns`, and **primary-key membership**
  via `inspector.get_pk_constraint(..."constrained_columns")`. Don't compare SQL type strings:
  SQLModel's `AutoString`/`Uuid` render as Postgres `VARCHAR`/`UUID` in inspector, so raw type
  comparison fails spuriously.
- **Proof the test catches drift.** When hardening a test, deliberately introduce drift it
  should detect (e.g. flip column to `nullable=False` in migration), watch it fail for right
  reason, revert, confirm green. If green on mutation, test isn't guarding the behavior.
- **Verify with DB up.** Green suite isn't evidence if Postgres container was down during run;
  restart and re-run before deciding code is the problem.
