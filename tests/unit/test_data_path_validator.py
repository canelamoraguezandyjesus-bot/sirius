"""Unit tests for WindowsDataPathValidator (B2b, D-10).

Every write-access claim is proven with a real temporary file, never
``os.access()`` alone. Permission failures are simulated deterministically by
monkeypatching ``tempfile.mkstemp`` instead of relying on real Windows ACLs,
which would be flaky in CI.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from sirius.infrastructure.data_path_validator import WindowsDataPathValidator
from sirius.ports.data_location import DataPathInvalidError


@pytest.fixture
def validator() -> WindowsDataPathValidator:
    return WindowsDataPathValidator()


def test_validate_creates_and_reports_a_fresh_directory(
    validator: WindowsDataPathValidator, tmp_path: Path
) -> None:
    candidate = tmp_path / "Datos de Sirius"

    check = validator.validate(candidate, allow_create=True)

    assert check.path == candidate
    assert candidate.is_dir()
    assert check.has_existing_installation is False


def test_validate_accepts_a_directory_that_already_exists(
    validator: WindowsDataPathValidator, tmp_path: Path
) -> None:
    candidate = tmp_path / "ya-existe"
    candidate.mkdir()

    check = validator.validate(candidate, allow_create=False)

    assert check.path == candidate


def test_validate_rejects_relative_paths(validator: WindowsDataPathValidator) -> None:
    with pytest.raises(DataPathInvalidError):
        validator.validate(Path("carpeta-relativa"), allow_create=True)


def test_validate_rejects_a_missing_directory_when_creation_is_not_allowed(
    validator: WindowsDataPathValidator, tmp_path: Path
) -> None:
    candidate = tmp_path / "no-existe"

    with pytest.raises(DataPathInvalidError):
        validator.validate(candidate, allow_create=False)

    assert not candidate.exists()


def test_validate_rejects_a_path_blocked_by_a_regular_file(
    validator: WindowsDataPathValidator, tmp_path: Path
) -> None:
    candidate = tmp_path / "archivo-en-el-camino"
    candidate.write_text("no soy una carpeta", encoding="utf-8")

    with pytest.raises(DataPathInvalidError):
        validator.validate(candidate, allow_create=True)


def test_validate_rejects_windows_invalid_characters(
    validator: WindowsDataPathValidator, tmp_path: Path
) -> None:
    candidate = tmp_path / "carpeta:invalida"

    with pytest.raises(DataPathInvalidError):
        validator.validate(candidate, allow_create=True)


def test_validate_rejects_a_reserved_windows_device_name(
    validator: WindowsDataPathValidator, tmp_path: Path
) -> None:
    candidate = tmp_path / "CON"

    with pytest.raises(DataPathInvalidError):
        validator.validate(candidate, allow_create=True)


def test_validate_accepts_spaces_and_unicode_in_the_path(
    validator: WindowsDataPathValidator, tmp_path: Path
) -> None:
    candidate = tmp_path / "Carpeta de Andy — Ñoño 日本語"

    check = validator.validate(candidate, allow_create=True)

    assert check.path.is_dir()


def test_validate_does_not_leave_a_partial_directory_when_the_write_check_fails(
    validator: WindowsDataPathValidator, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    candidate = tmp_path / "sin-permiso"

    def _raise_permission_error(*args: object, **kwargs: object) -> tuple[int, str]:
        raise PermissionError("acceso denegado")

    monkeypatch.setattr(
        "sirius.infrastructure.data_path_validator.tempfile.mkstemp", _raise_permission_error
    )

    with pytest.raises(DataPathInvalidError):
        validator.validate(candidate, allow_create=True)

    assert not candidate.exists()


def test_validate_reports_an_existing_sirius_installation(
    validator: WindowsDataPathValidator, tmp_path: Path
) -> None:
    candidate = tmp_path / "instalacion-existente"
    candidate.mkdir()
    (candidate / "sirius.db").write_bytes(b"")

    check = validator.validate(candidate, allow_create=False)

    assert check.has_existing_installation is True


def test_peek_never_creates_a_missing_directory(
    validator: WindowsDataPathValidator, tmp_path: Path
) -> None:
    candidate = tmp_path / "todavia-no-existe"

    check = validator.peek(candidate)

    assert check.has_existing_installation is False
    assert not candidate.exists()


def test_peek_detects_an_existing_installation_without_writing_anything(
    validator: WindowsDataPathValidator, tmp_path: Path
) -> None:
    candidate = tmp_path / "instalacion-previa"
    candidate.mkdir()
    (candidate / "sirius.db").write_bytes(b"")

    check = validator.peek(candidate)

    assert check.has_existing_installation is True


def test_looks_like_onedrive_by_path_segment(
    validator: WindowsDataPathValidator, tmp_path: Path
) -> None:
    candidate = tmp_path / "OneDrive" / "Sirius"

    check = validator.peek(candidate)

    assert check.is_onedrive is True


def test_regular_folder_is_not_flagged_as_onedrive(
    validator: WindowsDataPathValidator, tmp_path: Path
) -> None:
    candidate = tmp_path / "Documentos" / "Sirius"

    check = validator.peek(candidate)

    assert check.is_onedrive is False
