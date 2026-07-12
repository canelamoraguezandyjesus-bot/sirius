"""Typed local filesystem paths for Sirius, resolved via platformdirs."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from platformdirs import PlatformDirs

_APP_NAME = "sirius"


@dataclass(frozen=True, slots=True)
class SiriusPaths:
    """Local directories Sirius reads from and writes to."""

    config_dir: Path
    data_dir: Path
    logs_dir: Path
    backups_dir: Path
    exports_dir: Path

    def all_dirs(self) -> tuple[Path, ...]:
        """Return every managed directory."""
        return (
            self.config_dir,
            self.data_dir,
            self.logs_dir,
            self.backups_dir,
            self.exports_dir,
        )


def resolve_paths() -> SiriusPaths:
    """Resolve the local directories Sirius uses, without creating them."""
    dirs = PlatformDirs(_APP_NAME, appauthor=False, roaming=False)
    data_dir = Path(dirs.user_data_dir)
    return SiriusPaths(
        config_dir=Path(dirs.user_config_dir),
        data_dir=data_dir,
        logs_dir=data_dir / "logs",
        backups_dir=data_dir / "backups",
        exports_dir=data_dir / "exports",
    )


def ensure_paths(paths: SiriusPaths) -> None:
    """Create every managed directory if it does not already exist."""
    for directory in paths.all_dirs():
        directory.mkdir(parents=True, exist_ok=True)
