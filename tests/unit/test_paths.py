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


def test_resolve_paths_with_explicit_data_dir_derives_every_data_path_from_it(
    isolated_local_appdata: Path, tmp_path: Path
) -> None:
    """B2b: a custom data directory drives logs/backups/exports, never the
    platform default."""
    custom = tmp_path / "Carpeta de Sirius"

    paths = resolve_paths(custom)

    assert paths.data_dir == custom
    assert paths.logs_dir == custom / "logs"
    assert paths.backups_dir == custom / "backups"
    assert paths.exports_dir == custom / "exports"


def test_resolve_paths_config_dir_stays_fixed_regardless_of_data_dir_override(
    isolated_local_appdata: Path, tmp_path: Path
) -> None:
    """B2b: config_dir must stay independent of data_dir — the pointer file
    that records the chosen data directory lives there, so it cannot itself
    depend on the data directory it points to."""
    default_paths = resolve_paths()
    custom_paths = resolve_paths(tmp_path / "custom-data")

    assert custom_paths.config_dir == default_paths.config_dir
    assert custom_paths.config_dir == isolated_local_appdata / "sirius"
