from pathlib import Path

import pytest

from sirius.infrastructure.paths import ensure_paths, resolve_paths


@pytest.fixture
def isolated_local_appdata(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setenv("WIN_PD_OVERRIDE_LOCAL_APPDATA", str(tmp_path))
    return tmp_path


def test_resolve_paths_are_rooted_under_the_platform_directory(
    isolated_local_appdata: Path,
) -> None:
    paths = resolve_paths()

    root = isolated_local_appdata / "sirius"
    assert paths.config_dir == root
    assert paths.data_dir == root
    assert paths.logs_dir == root / "logs"
    assert paths.backups_dir == root / "backups"
    assert paths.exports_dir == root / "exports"


def test_resolve_paths_does_not_create_directories(isolated_local_appdata: Path) -> None:
    paths = resolve_paths()

    assert not any(directory.exists() for directory in paths.all_dirs())


def test_ensure_paths_creates_every_managed_directory(isolated_local_appdata: Path) -> None:
    paths = resolve_paths()

    ensure_paths(paths)

    assert all(directory.is_dir() for directory in paths.all_dirs())
