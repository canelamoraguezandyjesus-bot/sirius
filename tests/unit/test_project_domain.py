from datetime import UTC, datetime

import pytest

from sirius.domain.project import Project


def _any_project() -> Project:
    now = datetime.now(UTC)
    return Project(
        id=1,
        name="",
        objective="",
        current_state="",
        next_step="",
        created_at=now,
        updated_at=now,
    )


def test_project_is_immutable() -> None:
    project = _any_project()

    with pytest.raises(AttributeError):
        project.name = "otro"  # type: ignore[misc]
