# Persistence testing strategy — implementation plan

Date: 2026-11-21
Status: Accepted
Scope: raise the trust the persistence test suite earns, guided by Fowler's
test-pyramid thinking. Introduces a DB-free unit/integration tier split, reusable
mock seams for the FastAPI/Strawberry stack, parameterized tests, and records
property-based testing and mutation testing as future options. No runtime
behavior changes; `app/` is untouched by most slices.

## Goal

Today every test except `test_config` and one `test_session` case touches a real
Postgres database. There is no fast, DB-free tier, which makes the suite slow,
container-coupled (AGENTS.md documents spurious failures when Postgres is down),
and unable to run on a fresh clone or CI box without the DB. This plan adds the
missing cheap floor of the pyramid and hardens the contract that the project's
core purpose depends on — the GraphQL schema surface colombus consumes.

## Approach

- **Tier split by the session boundary.** `def f(session, ...)` → integration;
  `def f(*, scalars...) -> Row` → unit. The single clean rule that decides tiers.
- **Mock = a boundary replacement, never the wiring under test.** Sessions,
  services, and the router context are seams; the pure builders get no mocks.
- **Ship parameterization now; record PBT + mutation testing as future options.**
  Both only earn their keep after the DB-free unit tier exists.
- **Method**: strict TDD where a new behavior is introduced (schema-contract);
  where it is a *reorganization* (tier split, moves), verify semantics are
  preserved by the existing suite plus a targeted DB-free run with Postgres down.
- **Conventional scoped commits**, each stage independently shippable.

## Stages

### Stage 1 — True unit tier extraction (`tests/unit/`, `tests/integration/`)

New layout; `tests/services/` splits by the session boundary:

```
tests/
  unit/                      # NEW — DB-free, no session/engine/client fixtures
    conftest.py              # empty/deliberately no DB fixtures
    test_profiles.py         # create_profile defaulting (moved, session removed)
    test_patterns.py         # create_pattern defaulting (moved, session removed)
  integration/               # renamed from tests/services/ + existing suites
    services/                # delete_profile / delete_pattern (session-bound)
    graphql/ api/ db/ alembic/ core/
```

- Pure builders `create_profile`, `create_pattern` move to
  `tests/unit/`, rewritten session-free.
- The FK-validity assertion that used `session.flush()` **moves** (not deletes)
  into the integration tier (DB round-trips already prove it).
- `delete_profile`/`delete_pattern` stay in integration unchanged.
- **Enforcement = convention only**: `tests/unit/conftest.py` defines no DB
  fixtures, so an accidental DB dependency fails loudly at call time ("fixture
  not found"). No rule engine.
- **Proof**: `uv run pytest tests/unit` passes with Postgres down.

### Stage 2 — Mock seams for FastAPI + Strawberry (`tests/unit/`)

Two shipped seams, each proving a distinct contract, all in the unit tier (no DB):

- **Session seam** — mock `info.context["session"]`: resolver reads context
  correctly, mutation write contract (add/commit/refresh), query output shape.
- **Service seam** — patch `app.services.*` where the resolver imported it:
  resolver→service delegation and the `ok: bool` / skip-commit envelope.
- Prefer returning **real in-memory `models.*` rows**, not bare `Mocks`, so the
  mapper's attribute reads don't produce Mock-chains that explode in nested
  resolution.

A router `context_getter` seam was prototyped and **dropped**: the shipped
`app.main` router resolves `Depends(context_getter)` at construction (so
monkeypatching its attribute can't rewire it), an ephemeral router diverges from
production wiring, and the integration API suite already covers the true HTTP
path against the DB. Testing the seam would re-verify upstream Strawberry/FastAPI
behavior — not our resolver logic.

### Stage 3 — Parameterized tests (ship now)

`pytest.mark.parametrize` on enumerable input→expected pairs, scoped to the
**critical pure business logic** (the unit-tier defaulting builders):

- Defaulting truth tables for `create_profile`/`create_pattern` — each
  `or`-fallback rule and its falsy edge: `json_profile` absent/`None`/`{}`/
  provided, `json_pattern` absent/`{}`/provided, `dsl_content` absent/`""`/
  provided.
- Deliberately **not** covered here: delete-returns-`False` (the `delete_*`
  services are session-bound → integration tier; the seam tests already pin the
  resolver's `ok`/skip-commit envelope).
- **Do not parameterize the mutation/DB suites**: per-resource setup is the
  value; flattening it loses isolation and hurts failure reproduction.

### Stage 4 — `assert_num_queries` fixture (`tests/integration/`)

Promote the hand-rolled `before_cursor_execute` count from
`test_matching_profile_loader.py` into a reusable fixture/helper. Assert bounded
queries on the read paths (nested profile graph, loaders) so N+1 regressions are
caught by convention, not one test.

### Stage 5 — GraphQL schema-contract tests (`tests/integration/` or `api/`)

Pin the exact schema shape colombus consumes — type names, field names, args,
nullability — via the schema object. Closes the `Schema Faithfulness to colombus`
gap the graph flagged as an isolated node. Ground truth = the shipped schema +
colombus's queries, confirmed with the partner before writing.

### Stage 6 — Coverage gate (contribution-level rule)

Purpose: make sure any new contribution is properly tested/covered. Two layers:

**Layer A — global floor (backstop).** `[tool.coverage.report] fail_under = 80`
in `pyproject.toml`. Enforced on every `coverage report` (incl. `scripts/test.sh`)
and CI. The suite as a whole cannot sink below 80 — protects against mass test
removal even if the hook is bypassed.

**Layer B — contribution gate (the real rule).** A `local` pre-commit hook that,
for **each `app/*.py` file in the staged diff**, runs the suite **once** and
requires that file's coverage ≥ 80%. New code added to `app/` is covered or the
commit is blocked. See the hook spec in `documents/plans` implementation details;
it mirrors the existing pyrefly/vulture/bandit hooks (`pass_filenames: false`,
`require_serial: true`) and exits early when no `app/*.py` changed (docs/config
commits skip it).

- Per-file floor is a deliberately pragmatic proxy for "new lines covered";
  true changed-lines-only gating (diff→line cross-reference) is noted as a
  stricter future option.
- Accepted costs: the hook is DB-bound and runs the full suite once per relevant
  commit (a real coverage number needs the real suite); file floor + global floor
  both set to 80.
- Added *last* so the tier/mock stages count their new DB-free tests before the
  gate is enforced.

**Shipped.** Layer A `fail_under = 80` in `pyproject.toml`; Layer B as a
`local-coverage-gate` hook (`scripts/coverage-gate.sh`) on the staged `app/*.py`
diff, one full-suite run per relevant commit, early exit when no `app/*.py` is
staged. Verified in both directions: an untested `app` file fails the gate (0%
< 80); a covered one passes.

## Deferred as future options (recorded, not shipped)

These are deliberately out of scope this phase. Both are only worthwhile once the
DB-free unit tier exists and are documented so they are added deliberately, not
reactively.

- **Property-based testing (Hypothesis)** — scoped to pure *shipped* logic only,
  where a real invariant exists (e.g. a pure derive function living in `app/`).
  Explicitly **not** for test-only helpers such as `encode_profile` (a
  `tests/profile_utils.py` harness asserting our own test code adds no trust),
  `ingest_profile` (re-implements ingestion to assert shape), resolvers, or DB
  state. Adds one pinned dev-dep (`hypothesis==…`).
- **Mutation testing (mutmut)** — proof that the defaulting rules are pinned, by
  flipping one line and requiring a test to catch it. The correct precondition is
  the **unit tier existing** (a fast, deterministic, DB-free test set to run
  mutants against), *not* "DB-up" — DB-up only enters if mutants are run against
  the all-integration suite, which would be slow and container-flaky. Scope, when
  adopted, to `app/services/` + pure logic; skip `config.py`/`session.py`/
  `models.py` (low-signal, noisy surviving-mutation targets).

## Verification

- Full suite + pre-commit green after each stage.
- `uv run pytest tests/unit` passes with Postgres **down** (proves DB-freedom).
- Schema-contract test written red first, then schema preserved.

## Sequencing note

Stages 1–3 share the unit-tier substrate and ship as one conventional-commit
batch scoped per concern (`test(unit): …`, `docs(adr): …`). Stages 4–6 are
independent hardening and ship when scheduled. ADR-0011 records the tier-split
decision and the PBT/mutmut deferrals.
