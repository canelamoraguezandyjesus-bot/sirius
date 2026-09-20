"""¿Hay otra sesión viva tocando mis mismos ficheros? (ADR-206).

EL COSTE QUE ESTO QUITA, medido en el paso 4 de la auditoría de la forma de
trabajar. El 10-08-2026 el propietario tenía cuatro sesiones abiertas a la vez.
Una encargó al motor construir un bloque que otra había cerrado cuatro días
antes (#165, una tarde entera en balde); otra escribió un ADR que invalidó las
ediciones que una tercera estaba haciendo sobre los mismos documentos. En los
dos casos cada sesión leía bien y aun así no podía ver a la otra.

QUÉ DECIDE ESTE MÓDULO, Y NADA MÁS. Una sola pregunta: **de los ficheros que
voy a tocar, ¿cuáles está tocando ya otra obra viva?** No decide si se puede
empezar, no abre nada, no escribe nada. Devuelve el solape y quién lo tiene.

POR QUÉ RECIBE LAS OBRAS Y NO LAS BUSCA. Leer GitHub es de quien llama, que es
donde vive la disciplina de reintento y el token. Aquí solo se compara, y así
esta decisión se prueba de verdad en `tests/automation/test_obra_en_curso.py`
en vez de quedarse como texto pegado en un YAML que nadie ejecuta (la lección
de H-14, incidencia #282).

NO ES UN CERROJO. No guarda estado y no hay nada que soltar. Si la sesión que
declaró una obra muere, su pull request sigue ahí y se cierra como cualquier
otra; no queda ningún turno pillado esperando a que alguien se acuerde
—`regla-que-depende-de-que-alguien-se-acuerde`, la familia que esta casa cierra
desde ADR-174—.

FAIL-CLOSED, SIN EXCEPCIONES. Cualquier cosa que impida AFIRMAR que no hay
solape sale como «no lo sé» (código 2), nunca como «adelante». Un listado vacío
por un error de lectura es indistinguible de «no hay nadie más», y confundirlos
es exactamente lo que produjo la #165.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from pathlib import Path

#: Sin solape: se puede empezar.
LIBRE = 0
#: Hay solape: otra obra viva toca los mismos ficheros.
SOLAPE = 1
#: No se puede afirmar nada. Fail-closed: no es un permiso.
NO_SE_SABE = 2


@dataclass(frozen=True)
class Obra:
    """Una obra viva: una pull request abierta, con los ficheros que toca."""

    pull_request: str
    titulo: str
    ficheros: frozenset[str]


@dataclass(frozen=True)
class Solape:
    """Los ficheros que una obra viva comparte con la que se quiere empezar."""

    obra: Obra
    ficheros: tuple[str, ...]


def _normalizar(ruta: str) -> str:
    """Una ruta es la misma escrita con barras de Windows o de POSIX."""
    return ruta.strip().replace("\\", "/").lstrip("./")


def leer_obras(texto: str) -> list[Obra]:
    """Convierte el listado de obras vivas, y falla si no puede afirmarlo.

    El formato es el que produce la API de GitHub para las pull requests
    abiertas, reducido a lo que aquí importa: una lista de objetos con
    ``pull_request``, ``titulo`` y ``ficheros``. Cualquier desviación es un
    `ValueError`, no un listado vacío: un vacío se leería como «no hay nadie
    más» y esa es justo la confusión que este módulo existe para impedir.
    """
    try:
        crudo = json.loads(texto)
    except json.JSONDecodeError as error:
        raise ValueError(f"el listado de obras no es JSON válido: {error}") from error
    if not isinstance(crudo, list):
        raise ValueError("el listado de obras tiene que ser una lista")
    obras: list[Obra] = []
    for indice, entrada in enumerate(crudo):
        if not isinstance(entrada, dict):
            raise ValueError(f"la obra {indice} no es un objeto")
        pull_request = entrada.get("pull_request")
        ficheros = entrada.get("ficheros")
        if not isinstance(pull_request, str) or not pull_request.strip():
            raise ValueError(f"la obra {indice} no declara su pull_request")
        if not isinstance(ficheros, list) or not all(isinstance(f, str) for f in ficheros):
            raise ValueError(f"la obra {pull_request} no declara sus ficheros como lista de texto")
        titulo = entrada.get("titulo")
        obras.append(
            Obra(
                pull_request=pull_request.strip(),
                titulo=titulo.strip() if isinstance(titulo, str) else "",
                ficheros=frozenset(_normalizar(f) for f in ficheros if f.strip()),
            )
        )
    return obras


def solapes(
    ficheros_propios: Iterable[str], obras: Sequence[Obra], *, excluir: str = ""
) -> list[Solape]:
    """Qué obras vivas tocan alguno de mis ficheros, y cuáles.

    ``excluir`` es la pull_request de la obra propia, para que una sesión que ya
    abrió su pull request no se detecte a sí misma.
    """
    mios = {_normalizar(f) for f in ficheros_propios if f.strip()}
    encontrados: list[Solape] = []
    for obra in obras:
        if excluir and obra.pull_request == excluir.strip():
            continue
        comunes = sorted(mios & obra.ficheros)
        if comunes:
            encontrados.append(Solape(obra=obra, ficheros=tuple(comunes)))
    return encontrados


def _explicar(encontrados: Sequence[Solape]) -> str:
    lineas = ["Hay obra viva sobre los mismos ficheros. No empieces sin resolverlo:"]
    for solape in encontrados:
        titulo = f" — {solape.obra.titulo}" if solape.obra.titulo else ""
        lineas.append(f"  {solape.obra.pull_request}{titulo}")
        for fichero in solape.ficheros:
            lineas.append(f"    {fichero}")
    return "\n".join(lineas)


def main(argv: Sequence[str] | None = None) -> int:
    analizador = argparse.ArgumentParser(
        description=(
            "Dice si otra obra viva toca los ficheros que esta sesión va a tocar (ADR-206)."
        )
    )
    analizador.add_argument(
        "--obras",
        required=True,
        help="fichero JSON con las obras vivas; '-' para leerlo de la entrada estándar",
    )
    analizador.add_argument(
        "--fichero",
        action="append",
        default=[],
        metavar="RUTA",
        help="un fichero que esta sesión va a tocar; se puede repetir",
    )
    analizador.add_argument(
        "--excluir",
        default="",
        metavar="PULL_REQUEST",
        help="la pull_request de la obra propia, para no detectarse a uno mismo",
    )
    args = analizador.parse_args(argv)

    if not args.fichero:
        print("No has declarado ningún fichero: no puedo afirmar que no haya solape.")
        return NO_SE_SABE

    try:
        texto = sys.stdin.read() if args.obras == "-" else Path(args.obras).read_text("utf-8")
        obras = leer_obras(texto)
    except (OSError, ValueError) as error:
        print(f"No he podido leer las obras vivas ({error}); no digo que no haya solape.")
        return NO_SE_SABE

    encontrados = solapes(args.fichero, obras, excluir=args.excluir)
    if encontrados:
        print(_explicar(encontrados))
        return SOLAPE
    print(f"Sin solape con las {len(obras)} obras vivas declaradas.")
    return LIBRE


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
