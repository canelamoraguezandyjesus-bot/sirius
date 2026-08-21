"""``sirius-motor``: el comando que el propietario teclea para hablar con el motor.

M1 prometía «puedes hablar con Sirius y preguntarle por cualquier trabajo».
La interfaz v0 (:class:`~sirius_engine.session.SesionCLI`) estaba construida y
probada, pero no existía **ningún comando**: `[project.scripts]` no declaraba
ninguna entrada del motor y nadie fuera de `tests/` construía nunca una
sesión. Este módulo es esa cáscara y nada más: lee de la entrada, escribe en
la salida y monta las dependencias. Toda la lógica de un turno sigue viviendo
en `SesionCLI`, que no se toca (ADR-055).

**Este comando no puede crear trabajo, y eso es deliberado.** Conversar y
consultar no crean WorkItem: es la primera propiedad de A5 y hay pruebas que
la fijan. Dar órdenes exige arrancar trabajadores, que es Fase B/C y todavía
no existe, así que la cáscara **declina** las órdenes en vez de ejecutarlas.
La decisión no se toma aquí con una heurística propia: se le pregunta a la
MISMA puerta determinista (:func:`sirius_engine.gate.decidir`, sobre
:func:`~sirius_engine.intent_interpreter.interpretar_intencion_v0`) que
decidiría dentro de la sesión. Las dos son funciones puras del mensaje, así
que no pueden discrepar: lo que la cáscara admite es exactamente lo que la
sesión no convertiría en trabajo.

**Sin estado propio y sin red.** El estado durable es el diario de A2
(:class:`~sirius_engine.adapters.durable.store.DurableWorkEngineStore`), cuya
ruta se elige sin tocar código (``--diario`` o ``SIRIUS_MOTOR_DIARIO``).
``contexto.recuperar`` se cablea con sus dos proveedores locales -árbol del
repositorio e historial de ``git``-; el tercero, incidencias y PR, exigiría
red y queda fuera de v0: el comando lo **dice** en su salida en vez de dejar
que «no lo consulté» parezca «no hay nada» (ADR-036).
"""

from __future__ import annotations

import argparse
import os
import sys
from collections.abc import Callable, Mapping, Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import TextIO

from platformdirs import PlatformDirs

from sirius_engine.adapters.durable.store import DurableWorkEngineStore
from sirius_engine.adapters.fixture_mirror import FixedGitHubMirrorReader
from sirius_engine.context_recall import (
    LecturaHistorialGit,
    leer_historial_git_como_lectura,
)
from sirius_engine.domain.events import AggregateType
from sirius_engine.gate import ResultadoPuerta, decidir
from sirius_engine.intent_interpreter import interpretar_intencion_v0
from sirius_engine.ports.github_mirror import LecturaEstado
from sirius_engine.ports.store import WorkEngineStore
from sirius_engine.session import ContextoRecuperarConfig, SesionCLI

#: Nombre del comando, tal y como lo declara ``[project.scripts]``.
NOMBRE = "sirius-motor"

#: Variables de entorno con las que el propietario mueve el almacén y la raíz
#: del repositorio **sin tocar código** (requisito del encargo de ADR-055).
VARIABLE_DIARIO = "SIRIUS_MOTOR_DIARIO"
VARIABLE_RAIZ = "SIRIUS_MOTOR_RAIZ"

#: Repositorio que etiqueta el origen de una lectura de ``contexto.recuperar``.
#: Solo etiqueta: v0 no consulta incidencias (haría falta red).
REPO = "canelamoraguezandyjesus-bot/sirius"

_APP = "sirius"
_INDICADOR = "> "

_AYUDA = """Órdenes de la sesión:
  /trabajos  lista los trabajos que ya hay en el diario (solo lee)
  /ayuda     esto
  /salir     termina la sesión

Cualquier otra línea es un turno de conversación. Este comando conversa y
consulta; no crea trabajo."""

_SIN_TRABAJO = (
    "Esto es una orden, y este comando no crea trabajo: en v0 solo conversa y "
    "consulta (A5-P1, ADR-055). La puerta lo clasificó como {resultado}: {motivo}"
)

_SIN_INCIDENCIAS = (
    "  (contexto.recuperar v0 desde consola no consulta incidencias ni PR: "
    "haría falta red. No es que no haya nada ahí; es que no lo he mirado.)"
)


# --- Dónde vive lo que el comando necesita ------------------------------------


def diario_por_defecto() -> Path:
    """El diario vive en el directorio de datos de la plataforma, junto al de Sirius.

    Se elige ahí y no dentro del repositorio a propósito: el diario es estado
    del propietario, no del árbol de código, y un fichero de estado dentro del
    repositorio acaba en un `git status` sucio o, peor, confirmado. Es la misma
    raíz que ya usa la aplicación de escritorio
    (:mod:`sirius.infrastructure.paths`), en un subdirectorio propio del motor
    para no mezclarse con ella. **Esto no decide la representación física del
    almacén**, que es de D2 (ADR-019, ADR-029): decide un sitio por defecto.
    """
    datos = PlatformDirs(_APP, appauthor=False, roaming=False).user_data_dir
    return Path(datos) / "motor" / "diario.jsonl"


def resolver_diario(*, argumento: str | None, entorno: Mapping[str, str]) -> Path:
    """``--diario`` manda sobre ``SIRIUS_MOTOR_DIARIO``, y este sobre el defecto."""
    if argumento:
        return Path(argumento).expanduser()
    del_entorno = entorno.get(VARIABLE_DIARIO)
    if del_entorno:
        return Path(del_entorno).expanduser()
    return diario_por_defecto()


def resolver_raiz(*, argumento: str | None, entorno: Mapping[str, str]) -> Path:
    """``--raiz`` manda sobre ``SIRIUS_MOTOR_RAIZ``, y este sobre el directorio actual."""
    if argumento:
        return Path(argumento).expanduser()
    del_entorno = entorno.get(VARIABLE_RAIZ)
    if del_entorno:
        return Path(del_entorno).expanduser()
    return Path.cwd()


def _historial(raiz: Path) -> tuple[LecturaHistorialGit, str | None]:
    """Leer el historial local de ``git``; si no se puede, devolverlo dicho, no vacío.

    Ya no traduce la excepción a mano: ``leer_historial_git_como_lectura`` es el
    punto único donde ``EspejoIlegibleError`` se convierte en un dato que el
    motor puede transportar hasta ``proveedores_fallidos`` (H-5, ADR-050). Aquí
    solo se conserva el aviso que ve la persona, que el motor no da.
    """
    lectura = leer_historial_git_como_lectura(raiz)
    if lectura.estado is LecturaEstado.OK:
        return lectura, None
    return lectura, (
        f"  (no pude leer el historial de git en {raiz}: {lectura.error}. "
        "Las respuestas de abajo no lo incluyen: no es que no haya nada ahí.)"
    )


# --- Un turno ------------------------------------------------------------------


def _declinar(resultado: ResultadoPuerta, motivo: str) -> str:
    return _SIN_TRABAJO.format(resultado=resultado.value, motivo=motivo)


def _turno(
    sesion: SesionCLI,
    mensaje: str,
    *,
    numero: int,
    escribir: Callable[[str], None],
    aviso_historial: str | None,
) -> None:
    """Un turno: la puerta decide si el mensaje puede siquiera llegar a la sesión."""
    decision = decidir(interpretar_intencion_v0(mensaje))
    if decision.resultado is not ResultadoPuerta.NO_CREAR:
        escribir(_declinar(decision.resultado, decision.motivo))
        return

    respuesta = sesion.procesar_turno(
        mensaje, work_id=f"WI-CONSOLA-{numero}", now=datetime.now(UTC)
    )
    escribir(respuesta.mensaje)

    contexto = respuesta.contexto
    if contexto is None:
        return
    if aviso_historial is not None:
        escribir(aviso_historial)
    for proveedor in contexto.proveedores_fallidos:
        escribir(f"  (no pude leer {proveedor}: no es que no hubiera nada.)")
    escribir(_SIN_INCIDENCIAS)


def _listar_trabajos(store: WorkEngineStore, escribir: Callable[[str], None]) -> None:
    """Los trabajos que el diario ya contiene. Solo lee: no crea nada, ni el fichero."""
    vistos: list[str] = []
    for evento in store.list_events():
        if evento.aggregate_type is AggregateType.WORK_ITEM and evento.aggregate_id not in vistos:
            vistos.append(evento.aggregate_id)
    if not vistos:
        escribir("El diario no contiene ningún trabajo todavía.")
        return
    for work_id in vistos:
        item = store.get_work_item(work_id)
        if item is None:  # pragma: no cover - el diario no puede citar lo que no guarda
            continue
        escribir(f"  {work_id}  {item.estado.value}/{item.fase.value}  {item.objetivo}")


# --- El comando ----------------------------------------------------------------


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog=NOMBRE,
        description=(
            "Conversar y consultar contra el Sirius Work Engine. "
            "No crea trabajo: en v0 las órdenes se declinan."
        ),
    )
    parser.add_argument(
        "mensaje",
        nargs="*",
        help="un turno suelto; sin él, la sesión lee turnos de la entrada estándar",
    )
    parser.add_argument(
        "--diario",
        default=None,
        help=f"ruta del diario durable (por defecto, ${VARIABLE_DIARIO} o {diario_por_defecto()})",
    )
    parser.add_argument(
        "--raiz",
        default=None,
        help=(
            "raíz del repositorio que consulta contexto.recuperar "
            f"(por defecto, ${VARIABLE_RAIZ} o el directorio actual)"
        ),
    )
    return parser


def main(
    argv: Sequence[str] | None = None,
    *,
    entrada: TextIO | None = None,
    salida: TextIO | None = None,
    entorno: Mapping[str, str] | None = None,
) -> int:
    """Punto de entrada de ``sirius-motor``.

    Los cuatro parámetros existen para que una prueba pueda ejecutar el
    comando entero sin tocar ni el proceso ni el entorno reales; el instalador
    lo invoca sin ninguno.
    """
    entrada = sys.stdin if entrada is None else entrada
    salida = sys.stdout if salida is None else salida
    entorno = os.environ if entorno is None else entorno
    args = _parser().parse_args(None if argv is None else list(argv))

    def escribir(texto: str) -> None:
        print(texto, file=salida)

    raiz = resolver_raiz(argumento=args.raiz, entorno=entorno)
    diario = resolver_diario(argumento=args.diario, entorno=entorno)
    lectura_git, aviso_historial = _historial(raiz)
    store = DurableWorkEngineStore(diario)
    sesion = SesionCLI(
        store=store,
        contexto_recuperar=ContextoRecuperarConfig(
            raiz_repo=raiz,
            port=FixedGitHubMirrorReader(),
            repo=REPO,
            numeros_incidencias=(),
            lectura_historial_git=lectura_git,
        ),
    )

    if args.mensaje:
        _turno(
            sesion,
            " ".join(args.mensaje),
            numero=1,
            escribir=escribir,
            aviso_historial=aviso_historial,
        )
        return 0

    escribir(f"Sirius Work Engine — sesión de consola (v0). Diario: {diario}")
    escribir(f"Raíz consultada: {raiz}")
    if aviso_historial is not None:
        escribir(aviso_historial)
    escribir(_AYUDA)

    # Con terminal, el indicador se escribe ANTES de leer y lo que teclea el
    # propietario ya se ve; sin terminal (una tubería, o una prueba) hay que
    # escribir el turno para que la transcripción se entienda sola.
    interactiva = entrada.isatty()
    numero = 0
    while True:
        if interactiva:
            salida.write(_INDICADOR)
            salida.flush()
        linea = entrada.readline()
        if linea == "":
            break
        numero += 1
        mensaje = linea.strip()
        if not interactiva:
            escribir(f"{_INDICADOR}{mensaje}")
        if mensaje == "/salir":
            break
        if mensaje == "/ayuda":
            escribir(_AYUDA)
            continue
        if mensaje == "/trabajos":
            _listar_trabajos(store, escribir)
            continue
        _turno(sesion, mensaje, numero=numero, escribir=escribir, aviso_historial=aviso_historial)
    return 0


if __name__ == "__main__":  # pragma: no cover - lo cubre la entrada de consola
    raise SystemExit(main())
