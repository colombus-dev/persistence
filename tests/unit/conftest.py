"""Unit-tier conftest.

Deliberately defines no DB fixtures (``session``/``engine``/``client``). The
testing strategy (ADR-0011) enforces this by absence: an accidental DB
dependency in a unit test fails loudly at call time with "fixture not found".
"""
