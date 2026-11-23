# ADR-0011: DB-free unit tier with session-boundary split

- Status: Accepted
- Date: 2026-11-21
- Plan: documents/plans/2026-11-21-testing-strategy.md

## Context

The persistence test suite (46 tests) is almost entirely integration-bound:
every test except `test_config` and one `test_session` case hits a real Postgres
database through the transactional `session` fixture. There is no fast, DB-free
tier. Consequences:

- The suite is container-coupled (AGENTS.md documents spurious failures when the
  Postgres container is down) and cannot run on a fresh clone or a CI box without
  a live DB.
- Unambiguous unit behavior — the pure defaulting rules of
  `create_profile`/`create_pattern` — is asserted only inside tests that also
  `session.flush()`, so a defaulting bug and a wiring bug are indistinguishable,
  and both require a DB to observe.
- The testing strategy (per Fowler's pyramid) lacks the cheap, deterministic
  floor that makes broad-stack tests catch wiring failures instead of unit logic.

The preferred fix is to classify tests by the one clean rule that already
separates persistence units from persistence wiring: whether the tested function
takes a `session`.

## Decision

Split the test tree into two tiers by the session boundary:

- **`tests/unit/`** — DB-free, fast, no DB fixtures. Holds the pure builders
  (`create_profile`, `create_pattern`), plus resolver tests that mock the session
  (see the plan's mock-seam stage).
- **`tests/integration/`** — everything that genuinely needs a live session:
  `delete_profile`/`delete_pattern`, GraphQL queries/mutations, DB round-trips,
  alembic parity, HTTP contract. `tests/services/` splits across the boundary.

The tier rule is: `def f(session, ...)` → integration; `def f(*, scalars...) ->
Row` → unit. Enforcement is by convention only — the unit `conftest.py` defines
no `session`/`engine`/`client` fixtures, so an accidental DB dependency fails
loudly at call time — not by a rule engine, keeping the tier cheap to maintain.

Parameterized tests (`pytest.mark.parametrize`) are added to the unit tier's
enumerable input→expected cases (defaulting truth tables, the delete-missing
`False` contract). The DB-bound suites are deliberately **not** parameterized:
their per-resource setup is the value, and flattening it would lose failure
isolation.

## Alternatives considered

- **Keep the single all-integration suite.** Rejected: the DB-coupling and the
  conflation of unit vs wiring bugs above are exactly the trust problem this
  strategy exists to fix.
- **`_unit` filename suffixes instead of `tests/unit/`+`tests/integration/`**
  directories. Rejected by the partner in favor of the directory convention as
  clearer and greppable.
- **Enforce "no DB in unit tier" with a pytest marker/bind-time guard.** Deferred
  by the partner; convention-only is sufficient now, with a cheap escalation if
  the tier drifts.

## Deferred future options (recorded, not shipped)

These are deliberately out of scope for this phase and are captured here so they
are added deliberately rather than reactively. Both are worthwhile only once the
DB-free unit tier exists.

- **Property-based testing (Hypothesis)**: a good fit for pure *shipped* logic
  with a real invariant, and a poor fit for test-only helpers such as
  `encode_profile` (testing our own test harness adds no trust), `ingest_profile`
  (asserting shape re-implements ingestion), resolvers, and DB state. Requires
  one pinned dev-dep.
- **Mutation testing (mutmut)**: proves the defaulting rules are pinned by
  flipping a line and requiring a test to catch it. The correct precondition is
  the **unit tier existing** (a fast, deterministic, DB-free test set to run
  mutants against).

## Consequences

- `tests/unit` passes with Postgres **down**, giving a sub-second, deterministic
  regression floor and CI portability.
- FK/persistence truth stays in integration, where it belongs; a defaulting bug
  and a wiring bug now fail in different tiers.
- One integration test that served two purposes (defaulting *and* FK) is split
  into two precise tests; the FK assertion moves, not deletes.
- No change to `app/` runtime behavior; pyrefly's 100% typing gate on `app/` is
  unaffected (tests are excluded).
- A contribution-level coverage gate makes "new code is covered" an enforced
  contract rather than a report: a global `fail_under = 80` floor plus a
  pre-commit hook requiring every changed `app/*.py` file to be ≥ 80% covered
  (see the testing-strategy plan, Stage 6).
