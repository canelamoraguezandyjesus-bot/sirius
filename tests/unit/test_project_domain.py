from datetime import UTC, datetime

import pytest

from sirius.domain.project import Project, is_configured


def _any_project(*, name: str = "", objective: str = "", blockers: str = "") -> Project:
    now = datetime.now(UTC)
    return Project(
        id=1,
        name=name,
        objective=objective,
        current_state="",
        blockers=blockers,
        next_step="",
        created_at=now,
        updated_at=now,
    )


def test_project_is_immutable() -> None:
    project = _any_project()

    with pytest.raises(AttributeError):
        project.name = "otro"  # type: ignore[misc]


def test_bootstrap_placeholder_is_not_configured() -> None:
    placeholder = _any_project(name="", objective="")

    assert is_configured(placeholder) is False


def test_project_with_name_and_objective_is_configured() -> None:
    project = _any_project(name="Sirius 0.1", objective="Cerrar B3a")

    assert is_configured(project) is True


@pytest.mark.parametrize(
    ("name", "objective"),
    [
        ("Sirius", ""),
        ("", "Cerrar B3a"),
        ("   ", "Cerrar B3a"),
        ("Sirius", "   "),
        ("   ", "   "),
    ],
)
def test_project_missing_either_field_is_not_configured(name: str, objective: str) -> None:
    project = _any_project(name=name, objective=objective)

    assert is_configured(project) is False


def test_project_includes_blockers_field() -> None:
    project = _any_project(name="Sirius", objective="Cerrar B3b", blockers="bloqueo 1")

    assert project.blockers == "bloqueo 1"


def test_empty_blockers_does_not_turn_a_configured_project_into_a_placeholder() -> None:
    project = _any_project(name="Sirius", objective="Cerrar B3b", blockers="")

    assert is_configured(project) is True


def test_non_empty_blockers_does_not_turn_a_placeholder_into_configured() -> None:
    placeholder = _any_project(name="", objective="", blockers="bloqueo huérfano")

    assert is_configured(placeholder) is False
