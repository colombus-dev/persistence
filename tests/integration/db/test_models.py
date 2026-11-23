"""Contract tests for the domain SQLModel tables ported from colombus.

These pin the schema (table names, composite PK, cascade FKs) and the nested
round-trip of a JSON profile fixture through the ORM. Written against the
real models, seeded from the JSON profile resources.
"""

from sqlmodel import SQLModel, select

from app.db.models import (
    MatchingProfile,
    Pattern,
    Profile,
    Project,
)
from tests.profile_utils import ingest_profile

DOMAIN_TABLES = {
    "project",
    "profile",
    "step",
    "celloutput",
    "metainstruction",
    "code",
    "pattern",
    "matchingprofile",
}


def test_metadata_defines_all_domain_tables() -> None:
    assert DOMAIN_TABLES <= set(SQLModel.metadata.tables)


def test_matching_profile_composite_primary_key() -> None:
    table = SQLModel.metadata.tables["matchingprofile"]
    pk_columns = set(table.primary_key.columns.keys())
    assert pk_columns == {"pattern_hash", "profile_id"}


def test_step_to_profile_foreign_key_is_cascade_delete() -> None:
    table = SQLModel.metadata.tables["step"]
    profile_col = table.columns["profile_id"]
    assert profile_col.foreign_keys
    assert all(fk.ondelete == "CASCADE" for fk in profile_col.foreign_keys)


def test_profile_nested_round_trip(session, mini_profile) -> None:
    project = Project(name="test-project")
    session.add(project)
    session.flush()
    project_id = project.id

    ingest_profile(session, project_id, mini_profile)
    session.commit()

    profile = session.exec(
        select(Profile).where(Profile.name == mini_profile["name"])
    ).one()
    assert profile.project_id == project_id
    assert profile.json_profile == mini_profile
    assert profile.score == mini_profile.get("score")

    steps = sorted(profile.steps, key=lambda s: s.position)
    assert [s.name for s in steps] == [se["name"] for se in mini_profile["source"]]
    assert profile.encoded_profile == "-".join(
        ss["name"] for ss in mini_profile["source"]
    )

    first_step = steps[0]
    assert first_step.number_children == len(mini_profile["source"][0]["tasks"])
    assert len(first_step.meta_instructions) == len(mini_profile["source"][0]["tasks"])
    mi = first_step.meta_instructions[0]
    assert mi.algoFamily == mini_profile["source"][0]["tasks"][0]["algoFamily"]
    assert [c.content for c in sorted(mi.codes, key=lambda c: c.position)] == [
        t["name"] for t in mini_profile["source"][0]["tasks"][0]["tasks"]
    ]

    step_with_outs = steps[1]
    assert sorted(c.image for c in step_with_outs.cell_outputs) == [
        mini_profile["outputs"][out] for out in mini_profile["source"][1]["outputs_ids"]
    ]


def test_full_fixture_ingests(session, full_profile) -> None:
    """The real 150KB colombus profile must ingest and reload losslessly."""
    project = Project(name="p-full")
    session.add(project)
    session.flush()
    ingest_profile(session, project.id, full_profile)
    session.commit()

    profile = session.exec(select(Profile).where(Profile.name == "student_0")).one()
    assert profile.json_profile == full_profile
    assert len(profile.steps) == len(full_profile["source"])
    # every meta-instruction position is monotonic across the whole profile
    positions = [mi.position for mi in profile.meta_instructions]
    assert positions == sorted(positions)


def test_pattern_and_matching_profile_round_trip(session) -> None:
    project = Project(name="patproj")
    session.add(project)
    session.flush()

    pattern = Pattern(
        project_id=project.id,
        name="my.pattern",
        dsl_content="pattern my.pattern { ... }",
        json_pattern={"name": "my.pattern", "groups": []},
    )
    session.add(pattern)
    session.flush()

    profile = Profile(
        project_id=project.id,
        name="prof",
        score=0.5,
        encoded_profile="abc",
        json_profile={"name": "prof"},
        steps=[],
        meta_instructions=[],
        codes=[],
    )
    session.add(profile)
    session.flush()

    mp = MatchingProfile(pattern_hash="deadbeef", profile_id=profile.id)
    session.add(mp)
    session.commit()

    saved_mp = session.get(MatchingProfile, ("deadbeef", profile.id))
    assert saved_mp is not None
    assert saved_mp.profile_id == profile.id

    saved_pattern = session.exec(
        select(Pattern).where(Pattern.project_id == project.id)
    ).one()
    assert saved_pattern.json_pattern == {"name": "my.pattern", "groups": []}
