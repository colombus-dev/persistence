"""Integration test for the pattern deletion service (DB-bound, ADR-0011)."""

import uuid

from sqlmodel import Session

from app.services import patterns


def test_delete_pattern_returns_false_when_missing(session: Session) -> None:
    assert patterns.delete_pattern(session, uuid.uuid4()) is False
