"""Regression test for N+1 in the MatchingProfile.profile resolver.

The ``profile`` field of ``MatchingProfileType`` must resolve through the
mapper's dataloader so a ``matchingProfiles { profile { ... } }`` query batches
profile lookups into a single SELECT instead of one query per match row
(ADR-0010). This test counts profile-table SELECTs issued during the query and
asserts the load stays constant regardless of how many match rows exist.
"""

import asyncio
import re

from sqlalchemy import event
from sqlmodel import Session

import app.db.models as M
from app.graphql import build_schema_context, finalize_schema

_PROFILE_FROM_RE = re.compile(r"\bfrom\s+profile\b", re.IGNORECASE)


def _execute(session: Session, query: str) -> dict:
    schema = finalize_schema()

    async def run() -> dict:
        ctx = build_schema_context(session)
        result = await schema.execute(query, context_value=ctx)
        assert result.errors is None, result.errors
        assert result.data is not None
        return result.data

    return asyncio.run(run())


def _count_profile_selects(engine, session: Session) -> list[int]:
    """Return a list appending the number of profile-table SELECTs per call."""
    counts: list[int] = []
    # Drop identity-map hits so each lookup must query the database.
    session.expunge_all()

    def _before_cursor_execute(
        _conn, _cursor, statement, _parameters, _context, _executemany
    ) -> None:
        if _PROFILE_FROM_RE.search(statement):
            if counts:
                counts[-1] += 1
            else:
                counts.append(1)

    event.listen(engine, "before_cursor_execute", _before_cursor_execute)
    return counts


def test_matching_profile_loads_batch_relationship(session: Session) -> None:
    project = M.Project(name="batch-parent")
    session.add(project)
    session.flush()

    # Three profiles, each with one match row.
    for i in range(3):
        profile = M.Profile(
            project_id=project.id,
            name=f"batch-{i}",
            score=float(i),
            encoded_profile=f"enc-{i}",
            json_profile={},
        )
        session.add(profile)
        session.flush()
        session.add(M.MatchingProfile(pattern_hash=f"h-{i}", profile_id=profile.id))
    session.flush()

    data = _execute(
        session,
        "{ matchingProfiles { patternHash profile { name } } }",
    )

    names = sorted(mp["profile"]["name"] for mp in data["matchingProfiles"])
    assert names == ["batch-0", "batch-1", "batch-2"]

    # The profile lookup must be a single batched SELECT, not one per match.
    counts = _count_profile_selects(session.get_bind(), session)
    _execute(
        session,
        "{ matchingProfiles { patternHash profile { name } } }",
    )
    assert counts, "expected at least one profile SELECT"
    assert counts[0] == 1, f"expected 1 batched profile SELECT, got {counts[0]}"
