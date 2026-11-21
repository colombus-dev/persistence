"""Unit tests for the profile builder defaulting rules (DB-free, ADR-0011)."""

import uuid

from app.services import profiles


def test_create_profile_defaults_json_profile_to_empty() -> None:
    project_id = uuid.UUID("00000000-0000-0000-0000-000000000001")
    profile = profiles.create_profile(
        project_id=project_id,
        name="no-json",
        score=2.0,
        encoded_profile="enc",
    )
    assert profile.json_profile == {}
    assert profile.project_id == project_id
    assert profile.name == "no-json"
    assert profile.score == 2.0


def test_create_profile_keeps_provided_json_profile() -> None:
    project_id = uuid.UUID("00000000-0000-0000-0000-000000000002")
    payload = {"name": "with-json", "source": []}
    profile = profiles.create_profile(
        project_id=project_id,
        name="with-json",
        score=3.0,
        encoded_profile="enc",
        json_profile=payload,
    )
    assert profile.json_profile == payload
    assert profile.name == "with-json"
    assert profile.score == 3.0
