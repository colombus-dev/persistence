"""Typed shape of the JSON profile fixtures ingested by the domain tests.

The fixtures are plain JSON documents (``name``, ``metadata``, ``source``,
``outputs``, ``score``) as produced by colombus' profiler. Modelling them as
``TypedDict``s gives pyrefly exact index types (instead of ``Any``) so the
tests stay 100%-typed while reading nested structure.
"""

from typing import Any, TypedDict


class CodeJson(TypedDict, total=False):
    name: str
    tasks: list[CodeJson]


class MetaInstructionJson(TypedDict):
    id: str
    algoFamily: str | None
    algoName: str | None
    library: str | None
    function: str | None
    tasks: list[CodeJson]
    metadata: dict[str, Any]


class SourceStepJson(TypedDict):
    name: str
    tasks: list[MetaInstructionJson]
    outputs_ids: list[str]


class ProfileJson(TypedDict, total=False):
    name: str
    metadata: dict[str, Any]
    source: list[SourceStepJson]
    outputs: dict[str, str]
    score: float
