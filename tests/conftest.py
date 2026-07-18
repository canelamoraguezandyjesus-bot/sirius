"""Shared test configuration."""

from pathlib import Path

import pytest


@pytest.fixture(autouse=True)
def _isolate_platform_dirs(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    # Aísla platformdirs en Windows y Linux: en Windows redirige mediante
    # WIN_PD_OVERRIDE_LOCAL_APPDATA y en Linux mediante XDG_CONFIG_HOME/
    # XDG_DATA_HOME, para que resolve_paths() apunte a tmp_path en cada prueba.
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))
    monkeypatch.setenv("WIN_PD_OVERRIDE_LOCAL_APPDATA", str(tmp_path))
