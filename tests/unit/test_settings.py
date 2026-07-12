from pathlib import Path

import pytest

from sirius.config.settings import load_settings, save_settings
from sirius.infrastructure.paths import resolve_paths


@pytest.fixture(autouse=True)
def isolated_local_appdata(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("WIN_PD_OVERRIDE_LOCAL_APPDATA", str(tmp_path))


def test_load_settings_returns_empty_dict_when_nothing_is_stored() -> None:
    assert load_settings() == {}


def test_save_settings_persists_to_the_resolved_config_directory() -> None:
    save_settings({"user_name": "Ada", "data_path": "datos"})

    config_file = resolve_paths().config_dir / "settings.json"
    assert config_file.is_file()


def test_load_settings_round_trips_saved_data() -> None:
    save_settings({"user_name": "Ada", "data_path": "datos"})

    assert load_settings() == {"user_name": "Ada", "data_path": "datos"}
