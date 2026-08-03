"""Inspección de las entradas de un ZIP de B13, antes de extraerlo.

Existe como módulo de Python, y no como código dentro de
``scripts/verify_windows_package.ps1``, por una razón concreta: aquí vivía un
fallo real que convivió con CI en verde. El verificador partía los nombres de
entrada solo por ``/``, pero
``System.IO.Compression.ZipFile.CreateFromDirectory`` de .NET Framework —el que
corre bajo Windows PowerShell 5.1— los escribe con ``\\``, incumpliendo lo que
pide APPNOTE. Cada ruta completa quedaba entonces como un único segmento y por
tanto como una raíz distinta: un ZIP correcto de 109 archivos daba 109 raíces.
Nada en el repositorio podía detectar esa regresión, porque la lógica estaba
dentro de un ``.ps1`` que ninguna prueba ejecuta.

Sacándola aquí, la misma implementación que usa el verificador queda cubierta
por ``tests/unit/test_zip_package_inspector.py``. No es una copia del algoritmo:
es el algoritmo.

Todas las rutas se manipulan con ``ntpath``, no con ``os.path``. Este código
solo se ejecuta en Windows, pero sus pruebas corren en Linux (la comprobación
de calidad es Ubuntu); con ``ntpath`` la semántica es la de Windows en cualquier
plataforma, así que la prueba en Linux ejercita exactamente lo que hará en
Windows. Con ``os.path`` no probaría nada útil: en Linux, ``C:\\evil.dll`` no
es una ruta absoluta.

Uso desde PowerShell, que consume el JSON de la salida estándar::

    python scripts/zip_package_inspector.py <ruta-del-zip> <raiz-de-extraccion>
"""

from __future__ import annotations

import json
import ntpath
import sys
import zipfile
from collections.abc import Iterable
from dataclasses import dataclass

__all__ = ["ZipInspection", "inspect_entry_names", "inspect_zip", "main"]


@dataclass(frozen=True)
class ZipInspection:
    """Lo que hace falta saber de un ZIP para decidir si se extrae.

    ``roots`` son los primeros segmentos distintos de todas las entradas
    seguras, ordenados. ``unsafe`` describe, en texto, cada entrada rechazada;
    nunca está vacío sin motivo. ``file_count`` cuenta solo archivos: las
    entradas de directorio no cuentan.
    """

    roots: tuple[str, ...]
    unsafe: tuple[str, ...]
    file_count: int

    def as_dict(self) -> dict[str, object]:
        return {
            "roots": list(self.roots),
            "unsafe": list(self.unsafe),
            "file_count": self.file_count,
        }


def _is_directory_entry(name: str) -> bool:
    return name.endswith("/") or name.endswith("\\")


def inspect_entry_names(entry_names: Iterable[str], *, extract_root: str) -> ZipInspection:
    """Analiza nombres de entrada sin tocar el disco.

    Acepta indistintamente ``/`` y ``\\`` como separador. Rechaza toda entrada
    que pudiera escribir fuera de ``extract_root``: rutas absolutas, prefijos
    de unidad, UNC, segmentos ``..``, y cualquier destino que, ya resuelto,
    caiga fuera de esa raíz. Esa última comprobación es la que de verdad
    manda; las anteriores solo dan mensajes más útiles.
    """
    boundary = ntpath.normpath(extract_root).rstrip("\\") + "\\"

    roots: set[str] = set()
    unsafe: list[str] = []
    file_count = 0

    for original_name in entry_names:
        normalized = original_name.replace("\\", "/")

        if (
            normalized.startswith("/")
            or ntpath.isabs(original_name)
            or ntpath.splitdrive(original_name)[0] != ""
        ):
            unsafe.append(f"ruta absoluta o con unidad: {original_name}")
            continue

        segments = [segment for segment in normalized.split("/") if segment != ""]
        if not segments:
            continue

        if ".." in segments:
            unsafe.append(f"segmento '..': {original_name}")
            continue

        destination = ntpath.normpath(ntpath.join(extract_root, "\\".join(segments)))
        if not destination.casefold().startswith(boundary.casefold()):
            unsafe.append(f"escaparia de la carpeta de extraccion: {original_name}")
            continue

        roots.add(segments[0])
        if not _is_directory_entry(original_name):
            file_count += 1

    return ZipInspection(
        roots=tuple(sorted(roots)),
        unsafe=tuple(unsafe),
        file_count=file_count,
    )


def inspect_zip(zip_path: str, *, extract_root: str) -> ZipInspection:
    """Abre el ZIP en modo lectura y analiza sus nombres de entrada."""
    with zipfile.ZipFile(zip_path) as archive:
        return inspect_entry_names(
            (info.filename for info in archive.infolist()), extract_root=extract_root
        )


def main(argv: list[str]) -> int:
    if len(argv) != 3:
        print("uso: zip_package_inspector.py <ruta-del-zip> <raiz-de-extraccion>", file=sys.stderr)
        return 2
    inspection = inspect_zip(argv[1], extract_root=argv[2])
    print(json.dumps(inspection.as_dict()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
