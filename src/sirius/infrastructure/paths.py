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


def resolve_paths(data_dir: Path | None = None) -> SiriusPaths:
    """Resolve the local directories Sirius uses, without creating them.

    ``config_dir`` always comes from the platform-default directory,
    regardless of ``data_dir``: it must stay fixed and independent of the
    data location so a pre-bootstrap component (B2b) can record *where* the
    data directory is before the data directory itself is known or created.
    ``data_dir`` defaults to that same platform directory when omitted,
    preserving prior behavior for every caller that has no chosen location
    yet.
    """
    dirs = PlatformDirs(_APP_NAME, appauthor=False, roaming=False)
    resolved_data_dir = data_dir if data_dir is not None else Path(dirs.user_data_dir)
    return SiriusPaths(
        config_dir=Path(dirs.user_config_dir),
        data_dir=resolved_data_dir,
        logs_dir=resolved_data_dir / "logs",
        backups_dir=resolved_data_dir / "backups",
        exports_dir=resolved_data_dir / "exports",
    )


def ensure_paths(paths: SiriusPaths) -> None:
    """Create every managed directory if it does not already exist."""
    for directory in paths.all_dirs():
        directory.mkdir(parents=True, exist_ok=True)
