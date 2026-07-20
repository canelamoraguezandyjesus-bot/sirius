#!/usr/bin/env python3
"""Validador estructural del cuerpo de una incidencia de trabajo de Sirius.

La incidencia de trabajo es la fuente de verdad de cada bloque (ver
``docs/implementation/AUTOMATION_OPERATING_CONTRACT.md`` y
``docs/implementation/SIRIUS_GENERIC_ROUTINES_0.1.md``). Antes de que una Routine
actúe sobre una incidencia debe comprobar que el cuerpo recuperado está completo:
una respuesta truncada de la API (por ejemplo tras un 502/503 de GraphQL) nunca
puede aceptarse como cuerpo válido.

Este módulo no depende de red ni de GitHub: recibe texto y comprueba que
contienen todas las secciones obligatorias del contrato. Se usa tanto desde la
biblioteca ``scripts/automation/sirius_issue.sh`` como desde las pruebas
automatizadas.
"""

from __future__ import annotations

import argparse
import sys
import unicodedata

# Secciones obligatorias del contrato de trabajo. Cada entrada es el prefijo
# normalizado (sin acentos, en minúsculas) que debe aparecer como encabezado
# Markdown. Se usa coincidencia por prefijo para tolerar variantes como
# "Requisitos y pruebas de aceptación" o "Validaciones obligatorias".
REQUIRED_SECTIONS: tuple[str, ...] = (
    "work id",
    "bloque",
    "objetivo",
    "base y dependencias",
    "alcance permitido",
    "fuera de alcance",
    "requisitos y pruebas",
    "validaciones",
    "rama base",
    "condiciones de parada",
    "salvaguardas",
)

# Longitud mínima defensiva: un cuerpo de contrato real siempre supera este
# tamaño; un fragmento truncado muy corto se rechaza aunque, por casualidad,
# contuviera algún encabezado.
MIN_BODY_LENGTH = 200


def _normalize(text: str) -> str:
    """Minúsculas sin acentos, para comparar encabezados de forma tolerante."""
    decomposed = unicodedata.normalize("NFKD", text)
    without_accents = "".join(c for c in decomposed if not unicodedata.combining(c))
    return without_accents.casefold().strip()


def _heading_titles(body: str) -> list[str]:
    """Devuelve los títulos normalizados de las líneas de encabezado Markdown.

    Acepta encabezados ATX (``#`` .. ``######``) y también líneas en negrita
    usadas como encabezado (``**Título**``), porque las incidencias reales de
    Sirius mezclan ambos estilos.
    """
    titles: list[str] = []
    for raw_line in body.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if line.startswith("#"):
            titles.append(_normalize(line.lstrip("#").strip()))
            continue
        if line.startswith("**") and line.endswith("**") and len(line) > 4:
            titles.append(_normalize(line.strip("*").strip()))
    return titles


def missing_sections(body: str | None) -> list[str]:
    """Lista de secciones obligatorias ausentes; vacía si el cuerpo es completo."""
    if body is None:
        return list(REQUIRED_SECTIONS)
    if len(body.strip()) < MIN_BODY_LENGTH:
        # Demasiado corto para ser un contrato completo: se trata como truncado y
        # se reportan todas las secciones como ausentes.
        return list(REQUIRED_SECTIONS)
    titles = _heading_titles(body)
    missing: list[str] = []
    for section in REQUIRED_SECTIONS:
        if not any(title.startswith(section) for title in titles):
            missing.append(section)
    return missing


def is_complete(body: str | None) -> bool:
    """True solo si el cuerpo contiene todas las secciones obligatorias."""
    return not missing_sections(body)


def _main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Valida que el cuerpo de una incidencia de trabajo de Sirius contiene "
            "todas las secciones obligatorias. Sale con 0 si es completo, 1 si no."
        )
    )
    parser.add_argument(
        "path",
        nargs="?",
        help="Ruta al archivo con el cuerpo; si se omite, se lee de la entrada estándar.",
    )
    args = parser.parse_args(argv)

    if args.path:
        with open(args.path, encoding="utf-8") as handle:
            body = handle.read()
    else:
        body = sys.stdin.read()

    missing = missing_sections(body)
    if missing:
        sys.stderr.write(
            "Cuerpo de incidencia incompleto o truncado. Secciones ausentes: "
            + ", ".join(missing)
            + "\n"
        )
        return 1
    sys.stdout.write("Cuerpo de incidencia completo: todas las secciones presentes.\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
