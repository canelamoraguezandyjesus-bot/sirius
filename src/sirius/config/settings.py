"""Non-sensitive local configuration storage."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from platformdirs import user_config_dir

_CONFIG_DIR = Path(user_config_dir("sirius", appauthor=False))
_CONFIG_FILE = _CONFIG_DIR / "settings.json"


def load_settings() -> dict[str, Any]:
    """Load persisted non-sensitive settings, if any."""
    if _CONFIG_FILE.exists():
        result: dict[str, Any] = json.loads(_CONFIG_FILE.read_text(encoding="utf-8"))
        return result
    return {}


def save_settings(data: dict[str, Any]) -> None:
    """Persist non-sensitive settings to the local configuration file."""
    _CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    _CONFIG_FILE.write_text(
        json.dumps(data, indent=4, ensure_ascii=False),
        encoding="utf-8",
    )
