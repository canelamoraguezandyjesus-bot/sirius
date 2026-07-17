"""Pre-bootstrap data-location use case (B2b, D-10).

Resolves, validates, and persists the folder Sirius uses for SQLite, logs,
backups, and exports — entirely before ``initialize_persistence()`` runs.
Presentation only ever talks to this module: it never imports platformdirs,
the pointer-file format, or a physical filesystem operation directly
(AGENTS.md: "No accedas a SQLite ... desde la interfaz" — the same boundary
applies to any infrastructure detail; see ``sirius.ports.data_location`` for
why the underlying contracts avoid ``SiriusPaths``/SQLite altogether).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from sirius.ports.data_location import (
    DataLocationError,
    DataPathCheck,
    DataPathHasExistingInstallationError,
    DataPathInvalidError,
    DataPathValidator,
    LocationFileCorruptedError,
    LocationStore,
)

__all__ = [
    "DataLocationError",
    "DataLocationResolution",
    "DataLocationUseCase",
    "DataPathCheck",
    "DataPathHasExistingInstallationError",
    "DataPathInvalidError",
    "LocationFileCorruptedError",
]


@dataclass(frozen=True, slots=True)
class DataLocationResolution:
    """Outcome of resolving the data location without any user interaction yet."""

    path: Path
    needs_selection: bool
    default_path: Path


class DataLocationUseCase:
    """Load, validate, propose, and persist the chosen Sirius data directory."""

    def __init__(
        self,
        location_store: LocationStore,
        validator: DataPathValidator,
        default_data_dir: Path,
    ) -> None:
        self._location_store = location_store
        self._validator = validator
        self._default_data_dir = default_data_dir

    @property
    def default_path(self) -> Path:
        return self._default_data_dir

    def resolve(self) -> DataLocationResolution:
        """Resolve the data directory to use for this run.

        Only asks for a first choice when one is genuinely required (a
        brand-new install with no installation yet at the default path).
        Every other case resolves silently:

        - a previously saved location (default or custom) is validated and
          reused, never re-prompted;
        - a default-path installation that predates the pointer file is kept
          in place and the location is persisted, with no migration screen.

        Raises ``LocationFileCorruptedError`` if the pointer file exists but
        cannot be trusted, and ``DataPathInvalidError`` if a previously saved
        location can no longer be validated. Both are safe to surface
        directly to the user; neither is handled silently here, so no
        existing data can be hidden behind an automatic fallback.
        """
        saved = self._location_store.load()
        if saved is not None:
            check = self._validator.validate(saved, allow_create=False)
            return DataLocationResolution(
                path=check.path,
                needs_selection=False,
                default_path=self._default_data_dir,
            )

        default_check = self._validator.peek(self._default_data_dir)
        if default_check.has_existing_installation:
            confirmed = self._validator.validate(self._default_data_dir, allow_create=False)
            self._location_store.save(confirmed.path)
            return DataLocationResolution(
                path=confirmed.path,
                needs_selection=False,
                default_path=self._default_data_dir,
            )

        return DataLocationResolution(
            path=self._default_data_dir,
            needs_selection=True,
            default_path=self._default_data_dir,
        )

    def validate_candidate(
        self, candidate: Path, *, is_default: bool, allow_create: bool = True
    ) -> DataPathCheck:
        """Validate (and, if allowed, create) a candidate path chosen by the user.

        Does not persist anything: the caller must still call ``confirm``
        (for example after acknowledging a OneDrive warning). Raises
        ``DataPathHasExistingInstallationError`` if a *non-default* candidate
        already contains a Sirius installation — B2b never adopts or
        migrates existing data outside the default path.
        """
        check = self._validator.validate(candidate, allow_create=allow_create)
        if not is_default and check.has_existing_installation:
            raise DataPathHasExistingInstallationError(
                f"La carpeta '{check.path}' ya contiene datos de Sirius. "
                "Este paso no reutiliza ni migra datos existentes: elige otra carpeta."
            )
        return check

    def confirm(self, check: DataPathCheck) -> None:
        """Persist the already-validated candidate as the chosen data directory."""
        self._location_store.save(check.path)
