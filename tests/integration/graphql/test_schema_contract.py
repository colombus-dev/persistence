"""GraphQL schema-stability tests (ADR-0011 Stage 5).

Pins the public GraphQL surface of the persistence API — type names, field
names, args, and nullability — by introspecting the shipped schema object
directly (no DB, no client). Ground truth is the shipped schema itself.

This is a stability contract, not a consumer contract: it guards the schema
against silent drift so a breaking change to a field's name, args, or a
column's nullability fails loudly here instead of surfacing only when a
downstream consumer breaks. (The colombus client calls the legacy REST API,
not these GraphQL types.)
"""

from __future__ import annotations

from typing import Any

from app.graphql import schema


def _type_ref(ref: dict[str, Any]) -> str:
    """Render a GraphQL type reference as a compact non-null-aware string.

    ``{kind, name, ofType}`` → e.g. ``"String"``, ``"String!"``, ``"[Project!]!"``
    (wrappers applied innermost-out, non-null as a trailing ``!``).
    """
    kind = ref["kind"]
    if kind == "NON_NULL":
        return _type_ref(ref["ofType"]) + "!"
    if kind == "LIST":
        return "[" + _type_ref(ref["ofType"]) + "]"
    return ref["name"]  # SCALAR | OBJECT | ENUM | UNION | INPUT_OBJECT


def _field_signature(field: dict[str, Any]) -> str:
    args = ",".join(f"{a['name']}:{_type_ref(a['type'])}" for a in field["args"])
    args_suffix = f"({args})" if args else ""
    return f"{field['name']}{args_suffix}:{_type_ref(field['type'])}"


def _introspect() -> dict[str, dict[str, str]]:
    """Return ``{type_name: {field_name: signature}}`` for every object type."""
    result: dict[str, dict[str, str]] = {}
    for ty in schema.introspect()["__schema"]["types"]:
        if ty["kind"] != "OBJECT" or ty["fields"] is None:
            continue
        result[ty["name"]] = {f["name"]: _field_signature(f) for f in ty["fields"]}
    return result


_SCHEMA = _introspect()


def test_query_root_pins_colombus_read_surface() -> None:
    query = _SCHEMA["Query"]
    assert query == {
        "projects": "projects:[ProjectType!]!",
        "project": "project(id:UUID!):ProjectType",
        "profiles": "profiles:[ProfileType!]!",
        "profile": "profile(id:UUID!):ProfileType",
        "patterns": "patterns:[PatternType!]!",
        "matchingProfiles": "matchingProfiles:[MatchingProfileType!]!",
    }


def test_mutation_root_pins_write_surface() -> None:
    mutation = _SCHEMA["Mutation"]
    assert mutation == {
        "createProject": "createProject(name:String!):ProjectType!",
        "deleteProject": "deleteProject(id:UUID!):MutationResult!",
        "createProfile": (
            "createProfile("
            "projectId:UUID!,name:String!,score:Float!,encodedProfile:String!,"
            "jsonProfile:JSON"
            "):ProfileType!"
        ),
        "deleteProfile": "deleteProfile(id:UUID!):MutationResult!",
        "savePattern": (
            "savePattern("
            "projectId:UUID!,name:String!,jsonPattern:JSON,dslContent:String"
            "):PatternType!"
        ),
        "deletePattern": "deletePattern(id:UUID!):MutationResult!",
    }


def test_domain_type_field_sets_pin_nullability() -> None:
    # Only pins the scalar/FK leaf fields colombus actually reads; relationship
    # list fields carry mapper-generated connection args and are not guarded here.
    expected = {
        "ProjectType": {"id": "id:UUID!", "name": "name:String!"},
        "ProfileType": {
            "id": "id:UUID!",
            "projectId": "projectId:UUID!",
            "name": "name:String!",
            "score": "score:Float!",
            "jsonProfile": "jsonProfile:JSON!",
            "encodedProfile": "encodedProfile:String!",
        },
        "Step": {
            "id": "id:UUID!",
            "name": "name:String!",
            "position": "position:Int!",
            "numberChildren": "numberChildren:Int!",
            "previousStepId": "previousStepId:UUID",
        },
        "PatternType": {
            "id": "id:UUID!",
            "projectId": "projectId:UUID!",
            "name": "name:String!",
            "jsonPattern": "jsonPattern:JSON!",
            "dslContent": "dslContent:String!",
        },
        "MatchingProfileType": {
            "patternHash": "patternHash:String!",
            "profileId": "profileId:UUID!",
        },
    }
    for type_name, fields in expected.items():
        assert type_name in _SCHEMA, f"missing type {type_name}"
        actual = {k: v for k, v in _SCHEMA[type_name].items() if k in fields}
        assert actual == fields, f"{type_name} drift: {actual}"


def test_colombus_read_fieldnames_are_camel_cased() -> None:
    # colombus QUERY surface is consumed by camelCase field names + camelCase
    # relationship list fields; assert none leak snake_case onto the wire.
    for type_name in (
        "Query",
        "Mutation",
        "ProjectType",
        "ProfileType",
        "PatternType",
        "Step",
        "MatchingProfileType",
    ):
        for field in _SCHEMA[type_name]:
            assert "_" not in field, f"snake_case field leaked on {type_name}.{field}"
