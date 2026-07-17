"""Unit tests for BootstrapLocationStore (B2b, D-10).

The pointer file lives in the platform-stable config directory, independent
of any data directory it might point to; every test isolates that directory
via ``WIN_PD_OVERRIDE_LOCAL_APPDATA`` (same convention as ``test_paths.py``).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from sirius.infrastructure.bootstrap_location_store import BootstrapLocationStore
from sirius.infrastructure.paths import resolve_paths
from sirius.ports.data_location import LocationFileCorruptedError


@pytest.fixture(autouse=True)
def isolated_local_appdata(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    appdata = tmp_path / "appdata"
    monkeypatch.setenv("WIN_PD_OVERRIDE_LOCAL_APPDATA", str(appdata))
    return appdata


@pytest.fixture
def store() -> BootstrapLocationStore:
    return BootstrapLocationStore()


def _location_file() -> Path:
    return resolve_paths().config_dir / "data_location.json"


def test_load_returns_none_when_no_file_exists(store: BootstrapLocationStore) -> None:
    assert store.load() is None


def test_save_then_load_round_trips_the_data_dir(
    store: BootstrapLocationStore, tmp_path: Path
) -> None:
    chosen = tmp_path / "Mis Datos de Sirius"

    store.save(chosen)

    assert store.load() == chosen


def test_save_writes_the_documented_schema(store: BootstrapLocationStore, tmp_path: Path) -> None:
    chosen = tmp_path / "datos"

    store.save(chosen)

    payload = json.loads(_location_file().read_text(encoding="utf-8"))
    assert payload == {"version": 1, "data_dir": str(chosen)}


def test_save_overwrites_a_previous_valid_location(
    store: BootstrapLocationStore, tmp_path: Path
) -> None:
    store.save(tmp_path / "primero")
    store.save(tmp_path / "segundo")

    assert store.load() == tmp_path / "segundo"


@pytest.mark.parametrize(
    "raw_content",
    [
        "{not valid json",
        "[]",
        json.dumps({"version": 2, "data_dir": "C:\\x"}),
        json.dumps({"version": 1}),
        json.dumps({"version": 1, "data_dir": ""}),
        json.dumps({"version": 1, "data_dir": "relative\\path"}),
        json.dumps({"version": 1, "data_dir": 12345}),
    ],
)
def test_load_raises_on_a_corrupted_file_without_any_silent_fallback(
    store: BootstrapLocationStore, raw_content: str
) -> None:
    location_file = _location_file()
    location_file.parent.mkdir(parents=True, exist_ok=True)
    location_file.write_text(raw_content, encoding="utf-8")

    with pytest.raises(LocationFileCorruptedError):
        store.load()


def test_a_failed_write_never_destroys_the_last_valid_configuration(
    store: BootstrapLocationStore, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    good = tmp_path / "ubicacion-buena"
    store.save(good)

    def _raise_on_replace(*args: object, **kwargs: object) -> None:
        raise OSError("fallo simulado durante la escritura")

    monkeypatch.setattr(
        "sirius.infrastructure.bootstrap_location_store.os.replace", _raise_on_replace
    )

    with pytest.raises(OSError):
        store.save(tmp_path / "ubicacion-nueva")

    assert store.load() == good


def test_a_failed_write_leaves_no_partial_file_as_the_active_configuration(
    store: BootstrapLocationStore, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def _raise_on_replace(*args: object, **kwargs: object) -> None:
        raise OSError("fallo simulado durante la escritura")

    monkeypatch.setattr(
        "sirius.infrastructure.bootstrap_location_store.os.replace", _raise_on_replace
    )

    with pytest.raises(OSError):
        store.save(tmp_path / "nunca-se-guarda")

    assert not _location_file().exists()
