"""Infrastructure implementation of ``LocationStore`` (B2b, D-10).

A minimal JSON pointer file — ``{"version": 1, "data_dir": "<absolute path>"}``
— stored in the platform-stable configuration directory
(``sirius.infrastructure.paths.resolve_paths().config_dir``, which never
moves when a custom data directory is chosen: see that function's
docstring). Deliberately separate from ``sirius.config.settings``
(non-sensitive provider/UI settings), SQLite, and the secret store: this file
holds nothing but the chosen data directory, never secrets, conversation
data, or provider configuration.

Writes are atomic (write to a temp file in the same directory, ``fsync``,
then ``os.replace``): a failure partway through writing can never destroy the
last valid configuration or leave a partial file as the active one.
"""

from __future__ import annotations

import contextlib
import json
import os
import tempfile
from pathlib import Path
from typing import Any

from sirius.infrastructure.paths import resolve_paths
from sirius.ports.data_location import LocationFileCorruptedError

_FILE_NAME = "data_location.json"
_SCHEMA_VERSION = 1


def _location_file() -> Path:
    return resolve_paths().config_dir / _FILE_NAME


class BootstrapLocationStore:
    """Reads and atomically writes the external data-directory pointer file."""

    def load(self) -> Path | None:
        location_file = _location_file()
        if not location_file.exists():
            return None

        try:
            raw: Any = json.loads(location_file.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise LocationFileCorruptedError(
                "El archivo de ubicación de datos no se pudo leer."
            ) from exc

        data_dir = self._parse(raw)
        if data_dir is None:
            raise LocationFileCorruptedError(
                "El archivo de ubicación de datos tiene un formato no reconocido."
            )
        return data_dir

    @staticmethod
    def _parse(raw: Any) -> Path | None:
        if not isinstance(raw, dict) or raw.get("version") != _SCHEMA_VERSION:
            return None
        data_dir_value = raw.get("data_dir")
        if not isinstance(data_dir_value, str) or not data_dir_value.strip():
            return None
        candidate = Path(data_dir_value)
        if not candidate.is_absolute():
            return None
        return candidate

    def save(self, data_dir: Path) -> None:
        location_file = _location_file()
        location_file.parent.mkdir(parents=True, exist_ok=True)
        payload = {"version": _SCHEMA_VERSION, "data_dir": str(data_dir)}

        fd, tmp_name = tempfile.mkstemp(
            dir=location_file.parent, prefix=f".{_FILE_NAME}.", suffix=".tmp"
        )
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                handle.write(json.dumps(payload, indent=2, ensure_ascii=False))
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(tmp_name, location_file)
        except BaseException:
            with contextlib.suppress(OSError):
                os.remove(tmp_name)
            raise


def build_bootstrap_location_store() -> BootstrapLocationStore:
    return BootstrapLocationStore()
