"""Unit tests for the project builder service (DB-free, ADR-0011).

``create_project`` is a pure builder with no defaulting rule — unlike the
profile/pattern builders — so a single name-assignment case pins the
service-surface contract (a real ``models.Project`` is returned with the
supplied name). The delete path takes a ``session`` and is therefore covered in
the integration tier; the resolver delegation is pinned by the service seam in
``test_service_seam.py``.
"""

from __future__ import annotations

import app.db.models as M
from app.services import projects


def test_create_project_builder_returns_project_with_name() -> None:
    project = projects.create_project(name="acme")
    assert isinstance(project, M.Project)
    assert project.name == "acme"
    assert project.id is not None
