"""Validacion comun de rutas relativas destinadas a un filesystem Windows.

ZIP y manifiesto se validan en Ubuntu durante CI, pero se extraen y consumen en
Windows. Este modulo aplica por adelantado las reglas que pueden producir alias,
alternate data streams o nombres de dispositivo en NTFS/Win32.
"""

from __future__ import annotations

import ntpath

__all__ = ["WindowsPathError", "split_safe_windows_relative_path"]

_FORBIDDEN_CHARS = frozenset('<>:"|?*')
_RESERVED_COMPONENTS = frozenset(
    {
        "aux",
        "clock$",
        "con",
        "conin$",
        "conout$",
        "nul",
        "prn",
        *(f"com{number}" for number in range(1, 10)),
        *(f"lpt{number}" for number in range(1, 10)),
        "com¹",
        "com²",
        "com³",
        "lpt¹",
        "lpt²",
        "lpt³",
    }
)


class WindowsPathError(ValueError):
    """La ruta no tiene una representacion relativa, unica y segura en Windows."""


def _validate_component(component: str) -> None:
    if component in {"", ".", ".."}:
        raise WindowsPathError("segmento vacio, '.' o '..' no permitido")
    if component.endswith((" ", ".")):
        raise WindowsPathError("segmento terminado en espacio o punto")
    if any(ord(character) < 32 for character in component):
        raise WindowsPathError("caracter de control no permitido")
    forbidden = sorted({character for character in component if character in _FORBIDDEN_CHARS})
    if forbidden:
        raise WindowsPathError(
            "caracter Win32 no permitido: " + " ".join(repr(character) for character in forbidden)
        )

    # Win32 reserva estos nombres incluso con extension (por ejemplo NUL.txt).
    stem = component.split(".", 1)[0].rstrip(" .").casefold()
    if stem in _RESERVED_COMPONENTS:
        raise WindowsPathError(f"nombre de dispositivo Windows reservado: {component}")


def split_safe_windows_relative_path(
    raw_path: str,
    *,
    directory_entry: bool = False,
) -> tuple[str, ...]:
    """Devuelve componentes seguros o rechaza cualquier ambiguedad Win32.

    Se prohiben rutas absolutas/UNC/con unidad, segmentos vacios o de traversal,
    caracteres invalidos, dos puntos que abririan alternate data streams,
    nombres de dispositivo y terminaciones que Win32 recorta silenciosamente.
    """

    normalized = raw_path.replace("\\", "/")
    drive, _ = ntpath.splitdrive(raw_path)
    if normalized.startswith("/") or drive or ntpath.isabs(raw_path):
        raise WindowsPathError("ruta absoluta, UNC o con unidad")

    components = normalized.split("/")
    if directory_entry and components and components[-1] == "":
        components = components[:-1]
    if not components:
        raise WindowsPathError("ruta vacia")

    for component in components:
        _validate_component(component)
    return tuple(components)
