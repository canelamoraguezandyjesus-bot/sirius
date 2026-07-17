"""Infrastructure implementation of ``DataPathValidator`` for Windows (B2b, D-10).

Every check that claims a candidate directory is writable actually creates
and deletes a small, content-free temporary file: ``os.access()`` alone is
not a reliable proof of write access on Windows (ACL-restricted directories
can report accessible and still reject a real write).
"""

from __future__ import annotations

import contextlib
import os
import re
import tempfile
from pathlib import Path

from sirius.ports.data_location import DataPathCheck, DataPathInvalidError

_INSTALLATION_MARKER = "sirius.db"

_INVALID_CHARS = re.compile(r'[<>:"|?*\x00-\x1f]')

_RESERVED_NAMES = frozenset(
    {"CON", "PRN", "AUX", "NUL"}
    | {f"COM{i}" for i in range(1, 10)}
    | {f"LPT{i}" for i in range(1, 10)}
)

_ONEDRIVE_ENV_VARS = ("OneDrive", "OneDriveConsumer", "OneDriveCommercial")


class WindowsDataPathValidator:
    """Concrete ``DataPathValidator`` for a Windows local filesystem."""

    def peek(self, candidate: Path) -> DataPathCheck:
        path = self._check_syntax(candidate)
        return DataPathCheck(
            path=path,
            has_existing_installation=self._has_existing_installation(path),
            is_onedrive=self._looks_like_onedrive(path),
        )

    def validate(self, candidate: Path, *, allow_create: bool) -> DataPathCheck:
        path = self._check_syntax(candidate)

        if path.exists() and path.is_file():
            raise DataPathInvalidError(f"'{path}' ya existe como un archivo, no como una carpeta.")

        created_now = False
        if not path.exists():
            if not allow_create:
                raise DataPathInvalidError(f"La carpeta '{path}' no existe.")
            try:
                path.mkdir(parents=True)
            except OSError as exc:
                raise DataPathInvalidError(
                    f"No se pudo crear la carpeta '{path}': {exc.strerror or exc}."
                ) from exc
            created_now = True

        try:
            self._check_writable(path)
        except DataPathInvalidError:
            if created_now:
                with contextlib.suppress(OSError):
                    path.rmdir()
            raise

        return DataPathCheck(
            path=path,
            has_existing_installation=self._has_existing_installation(path),
            is_onedrive=self._looks_like_onedrive(path),
        )

    def _check_syntax(self, candidate: Path) -> Path:
        if not candidate.is_absolute():
            raise DataPathInvalidError(f"La ruta '{candidate}' debe ser una ruta absoluta.")

        normalized = Path(os.path.normpath(str(candidate)))
        for part in normalized.parts[1:]:  # skip the drive/anchor, e.g. "C:\\"
            if _INVALID_CHARS.search(part):
                raise DataPathInvalidError(
                    f"La ruta contiene caracteres no permitidos en Windows: '{part}'."
                )
            if part.split(".")[0].upper() in _RESERVED_NAMES:
                raise DataPathInvalidError(
                    f"'{part}' es un nombre reservado de Windows y no puede usarse."
                )
            if part != part.rstrip(" ."):
                raise DataPathInvalidError(
                    f"'{part}' no puede terminar en espacio o punto en Windows."
                )
        return normalized

    @staticmethod
    def _has_existing_installation(path: Path) -> bool:
        return (path / _INSTALLATION_MARKER).is_file()

    @staticmethod
    def _check_writable(path: Path) -> None:
        tmp_name: str | None = None
        try:
            fd, tmp_name = tempfile.mkstemp(dir=path, prefix=".sirius-write-check-", suffix=".tmp")
            os.close(fd)
        except OSError as exc:
            raise DataPathInvalidError(
                f"No se puede escribir en '{path}': {exc.strerror or exc}."
            ) from exc
        finally:
            if tmp_name is not None:
                with contextlib.suppress(OSError):
                    os.remove(tmp_name)

    @staticmethod
    def _looks_like_onedrive(path: Path) -> bool:
        resolved = os.path.normcase(str(path))
        for env_var in _ONEDRIVE_ENV_VARS:
            root = os.environ.get(env_var)
            if root and resolved.startswith(os.path.normcase(os.path.normpath(root))):
                return True
        return any("onedrive" in part.lower() for part in path.parts)


def build_data_path_validator() -> WindowsDataPathValidator:
    return WindowsDataPathValidator()
