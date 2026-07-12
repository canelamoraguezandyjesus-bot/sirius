"""Non-sensitive local configuration storage."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from sirius.infrastructure.paths import resolve_paths

_CONFIG_FILE_NAME = "settings.json"


def _config_file() -> Path:
    return resolve_paths().config_dir / _CONFIG_FILE_NAME


def load_settings() -> dict[str, Any]:
    """Load persisted non-sensitive settings, if any."""
    config_file = _config_file()
    if config_file.exists():
        result: dict[str, Any] = json.loads(config_file.read_text(encoding="utf-8"))
        return result
    return {}


def save_settings(data: dict[str, Any]) -> None:
    """Persist non-sensitive settings to the local configuration file."""
    config_file = _config_file()
    config_file.parent.mkdir(parents=True, exist_ok=True)
    config_file.write_text(
        json.dumps(data, indent=4, ensure_ascii=False),
        encoding="utf-8",
    )
