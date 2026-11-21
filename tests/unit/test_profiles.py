"""Unit tests for the profile builder defaulting rules (DB-free, ADR-0011).

The defaulting rule under test is ``json_profile or {}``: an absent, ``None``,
or empty document falls back to ``{}``. Pinned as a parameterized truth table
because the ``or`` fallback is the business logic that makes a bare wire-show
bug (``None`` leaking through) or a type bug (falsy ``{}`` kept) observable.
"""

from __future__ import annotations

import uuid

import pytest

from app.services import profiles

_PROJECT = uuid.UUID("00000000-0000-0000-0000-000000000001")


@pytest.mark.parametrize(
    ("json_profile", "expected"),
    [
        (None, {}),  # absent -> default {} (falsy fallback)
        ({}, {}),  # empty dict is falsy -> default {}
        ({"name": "kept", "source": []}, {"name": "kept", "source": []}),
    ],
)
def test_create_profile_json_profile_defaulting(
    json_profile: dict | None, expected: dict
) -> None:
    profile = profiles.create_profile(
        project_id=_PROJECT,
        name="p",
        score=1.0,
        encoded_profile="enc",
        json_profile=json_profile,
    )
    assert profile.json_profile == expected
