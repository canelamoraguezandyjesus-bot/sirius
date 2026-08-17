#!/usr/bin/env python3
"""Calcula el número del siguiente ADR y crea el archivo desde la plantilla.

El número es **el máximo existente más uno**, nunca un hueco histórico
(ADR-029). El registro tiene hoy dos `ADR-016` y ningún 017 ni 018: el hueco es
inofensivo —nadie busca un ADR por su posición—, pero el número repetido hace
que dos decisiones distintas se citen igual.

Esto es un ayudante, **no una puerta**. No impide crear un ADR a mano, y solo
ve el árbol de trabajo local: dos ramas abiertas a la vez sobre el mismo `main`
pueden obtener ambas el mismo número. Lo que sí cierra el agujero es la prueba
que recorre `docs/decisions/` y falla si dos archivos comparten número; el
guion quita fricción, la prueba es la garantía, y conviene no confundirlas.

La fecha se inyecta en vez de leerse del reloj para que el resultado sea
función únicamente de los argumentos: una prueba que dependiera del día en que
corre mediría la máquina, no el código.
"""

from __future__ import annotations

import argparse
import re
import sys
import unicodedata
from collections.abc import Callable
from datetime import date
from pathlib import Path

# Insensible a mayúsculas a propósito: en Windows `adr-030-x.md` y
# `ADR-030-x.md` son el mismo archivo, así que ignorar la primera forma dejaría
# proponer un número ya ocupado. El título es opcional para que un
# `ADR-030.md` suelto también cuente como ocupado.
PATRON_ADR = re.compile(r"^ADR-(\d+)(?:-.*)?\.md$", re.IGNORECASE)

NOMBRE_PLANTILLA = "PLANTILLA.md"


def numeros_por_archivo(directorio: Path) -> dict[str, int]:
    """Número declarado por cada archivo de ADR del directorio."""
    if not directorio.is_dir():
        raise NotADirectoryError(f"no existe el registro de decisiones: {directorio}")
    encontrados: dict[str, int] = {}
    for ruta in sorted(directorio.iterdir()):
        if not ruta.is_file():
            continue
        casa = PATRON_ADR.match(ruta.name)
        if casa is not None:
            encontrados[ruta.name] = int(casa.group(1))
    return encontrados


def siguiente_numero(directorio: Path) -> int:
    """Máximo existente más uno; 1 si el registro está vacío.

    Deliberadamente NO devuelve el primer hueco libre: reutilizar 017 haría que
    un mismo número apuntara a decisiones distintas según la fecha del clon.
    """
    numeros = list(numeros_por_archivo(directorio).values())
    if not numeros:
        return 1
    return max(numeros) + 1


def duplicados(directorio: Path) -> dict[int, list[str]]:
    """Números usados por más de un archivo. Diagnóstico, no bloquea nada."""
    por_numero: dict[int, list[str]] = {}
    for nombre, numero in numeros_por_archivo(directorio).items():
        por_numero.setdefault(numero, []).append(nombre)
    return {
        numero: sorted(nombres)
        for numero, nombres in sorted(por_numero.items())
        if len(nombres) > 1
    }


def normalizar_titulo(titulo: str) -> str:
    """Título -> segmento del nombre de archivo, según el convenio del registro.

    Una sola regla, no una lista de casos: se descomponen los diacríticos y se
    conserva `[a-z0-9.]`; **todo** lo demás separa. Añadir una regla por cada
    carácter que aparezca —una tilde, luego una eñe, luego unas comillas— es la
    familia «reconstruir por fuera una semántica ajena» que costó quince
    defectos en la PR #139, y el criterio de parada de ADR-029 la prohíbe.

    Los puntos se conservan porque el convenio ya los usa: ADR-012 termina en
    `sirius-0.1`.
    """
    sin_diacriticos = "".join(
        caracter
        for caracter in unicodedata.normalize("NFKD", titulo)
        if not unicodedata.combining(caracter)
    )
    limpio = re.sub(r"[^a-z0-9.]+", "-", sin_diacriticos.lower()).strip("-.")
    if not limpio:
        raise ValueError(f"el titulo no deja ningun caracter utilizable: {titulo!r}")
    return limpio


def nombre_de_archivo(numero: int, titulo: str) -> str:
    """`ADR-NNN-titulo-normalizado.md`, con NNN a tres dígitos como mínimo."""
    if numero < 1:
        raise ValueError(f"el numero de un ADR empieza en 1: {numero}")
    return f"ADR-{numero:03d}-{normalizar_titulo(titulo)}.md"


def _indice_de_linea(lineas: list[str], criterio: Callable[[str], bool], descripcion: str) -> int:
    for indice, linea in enumerate(lineas):
        if criterio(linea):
            return indice
    raise ValueError(
        f"{NOMBRE_PLANTILLA} ya no contiene {descripcion}. El guion no rellena a ciegas: "
        "escribir el archivo igualmente dejaria un ADR con la cabecera sin poner, "
        "que es peor que no crearlo"
    )


def rellenar_plantilla(plantilla: str, numero: int, titulo: str, fecha: date) -> str:
    """Pone número, título y fecha en la plantilla; el resto queda para el autor."""
    lineas = plantilla.splitlines()
    encabezado = _indice_de_linea(
        lineas, lambda linea: linea.startswith("# ADR-"), "el encabezado «# ADR-...»"
    )
    lineas[encabezado] = f"# ADR-{numero:03d} — {titulo}"
    fecha_puesta = _indice_de_linea(
        lineas, lambda linea: linea.startswith("- Fecha:"), "la linea «- Fecha:»"
    )
    lineas[fecha_puesta] = f"- Fecha: {fecha.isoformat()}"
    return "\n".join(lineas) + "\n"


def crear_adr(directorio: Path, titulo: str, fecha: date) -> Path:
    """Crea el ADR siguiente y devuelve su ruta. Nunca sobrescribe."""
    numero = siguiente_numero(directorio)
    destino = directorio / nombre_de_archivo(numero, titulo)
    if destino.exists():
        raise FileExistsError(f"ya existe {destino.name}; este guion no sobrescribe nunca")
    plantilla = directorio / NOMBRE_PLANTILLA
    if not plantilla.is_file():
        raise FileNotFoundError(f"falta la plantilla: {plantilla}")
    contenido = rellenar_plantilla(plantilla.read_text(encoding="utf-8"), numero, titulo, fecha)
    destino.write_text(contenido, encoding="utf-8")
    return destino


def _avisar_de_duplicados(directorio: Path) -> None:
    for numero, nombres in duplicados(directorio).items():
        print(
            f"aviso: ADR-{numero:03d} lo usan {len(nombres)} archivos: {', '.join(nombres)}",
            file=sys.stderr,
        )


def main(argv: list[str] | None = None) -> int:
    analizador = argparse.ArgumentParser(
        description="Crea el siguiente ADR (maximo existente + 1) desde PLANTILLA.md.",
    )
    analizador.add_argument("titulo", nargs="?", help="titulo del ADR, en imperativo")
    analizador.add_argument(
        "--directorio", type=Path, default=Path("docs/decisions"), help="registro de decisiones"
    )
    analizador.add_argument("--fecha", default=None, help="AAAA-MM-DD; por defecto, hoy")
    analizador.add_argument(
        "--solo-numero", action="store_true", help="imprime el numero siguiente sin crear nada"
    )
    args = analizador.parse_args(argv)
    directorio: Path = args.directorio

    try:
        _avisar_de_duplicados(directorio)
        if args.solo_numero:
            print(siguiente_numero(directorio))
            return 0
        if not args.titulo:
            print("error: hace falta un titulo (o --solo-numero)", file=sys.stderr)
            return 2
        fecha = date.fromisoformat(args.fecha) if args.fecha else date.today()
        print(crear_adr(directorio, args.titulo, fecha))
    except (OSError, ValueError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
