"""``sirius-supervisar``: el interruptor que le faltaba al motor (D2, #296).

El motor tenía cerebro y no tenía interruptor. :func:`supervise_runs` —la pasada
que reconcilia el mundo, cierra como ``LOST`` lo que se perdió, reactiva o
sustituye, y escala lo que no se puede salvar— está construida y probada desde
C1, y **no la llamaba nadie**: cero llamadas en todo ``src/``, y ninguno de los
cuatro comandos del motor la invocaba. Sin este módulo no hay forma de pedirle
al motor que dé un turno, así que el cableado de D2 no tenía a qué enchufarse.

Es la tercera vez que este repositorio se encuentra lo mismo —una pieza correcta
y probada a la que nadie llama—: pasó con el despachador (C2 dejó su cableado
fuera a propósito, y lo cosió ``sirius-despachar``) y pasó con H-13. Aquí se
cierra la de la supervisión.

**Este módulo es una cáscara y nada más**, igual que ``sirius-motor``: resuelve
rutas, monta adaptadores, llama a :func:`supervise_runs` y cuenta lo que pasó.
Ninguna decisión vive aquí. En particular **el reloj se lee aquí y solo aquí**:
el motor es determinista porque nunca mira la hora, así que la hora entra desde
fuera, por esta puerta.

**Qué hace `--ensayo`, y qué no.** Con ``--ensayo`` se resuelve todo —rutas,
repositorio, diarios— y se informa, **sin llamar a la supervisión**. Sirve para
comprobar que un workflow recién cableado encuentra sus ficheros y sus
credenciales antes de dejarle actuar. Lo que NO es: un simulacro de la pasada.
:func:`supervise_runs` no separa planificar de actuar, y fingir que sí lo hace
sería peor que no tenerlo. Sin ``--ensayo``, la pasada actúa de verdad.

**Y no se protege solo.** Dos invocaciones simultáneas sobre el mismo diario se
pisan —está medido en ``tests/engine/test_exclusion_entre_invocaciones.py``— y
lo único que lo impide es el grupo de concurrencia del workflow que lo invoque
(ADR-082, D2). Quien llame a este comando desde otro sitio hereda ese deber.
"""

from __future__ import annotations

import argparse
import os
import sys
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import TextIO

from sirius_engine.adapters.durable.store import DurableWorkEngineStore
from sirius_engine.adapters.durable.supervisor_journal import DurableSupervisorJournal
from sirius_engine.adapters.github_actions_run_observer import GitHubActionsRunObserver
from sirius_engine.adapters.github_actions_run_probe import GitHubActionsRunProbe
from sirius_engine.cli import REPO, resolver_diario
from sirius_engine.supervisor import SupervisionSweepResult, supervise_runs

#: Nombre del diario del supervisor, hermano del diario del motor. Se deriva del
#: mismo directorio en vez de tener su propia opción: son dos mitades de la
#: misma memoria y separarlas por configuración solo crea formas de que no
#: coincidan.
NOMBRE_DIARIO_SUPERVISOR = "diario-supervision.jsonl"


def diario_de_supervision(diario_del_motor: Path) -> Path:
    """El diario del supervisor, junto al del motor."""
    return diario_del_motor.parent / NOMBRE_DIARIO_SUPERVISOR


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="sirius-supervisar",
        description=(
            "Dar un turno de supervisión: reconciliar el mundo, cerrar lo perdido "
            "y actuar sobre ello. Sin --ensayo, actúa de verdad."
        ),
    )
    parser.add_argument("--repo", default=REPO, help=f"Repositorio observado (por defecto {REPO}).")
    parser.add_argument("--diario", default=None, help="Ruta del diario durable del motor.")
    parser.add_argument(
        "--ensayo",
        action="store_true",
        help="Resolver y decir qué se usaría, sin supervisar nada.",
    )
    return parser


def _resumen(resultado: SupervisionSweepResult) -> list[str]:
    return [
        f"runs reconciliados: {len(resultado.recovery.reconciled_run_ids)}",
        f"acciones tomadas:   {len(resultado.acted)}",
        f"ajenos, no tocados: {len(resultado.skipped_foreign)}",
        f"aplazados:          {len(resultado.deferred)}",
        f"errores:            {len(resultado.errors)}",
    ]


def main(
    argv: Sequence[str] | None = None,
    *,
    salida: TextIO | None = None,
    entorno: Mapping[str, str] | None = None,
    ahora: datetime | None = None,
) -> int:
    """Punto de entrada de ``sirius-supervisar``.

    Los parámetros existen para que una prueba ejecute el comando entero sin
    tocar el proceso, el entorno ni el reloj reales; el instalador lo invoca sin
    ninguno. ``ahora`` es el único sitio del motor donde entra la hora real.
    """
    salida = sys.stdout if salida is None else salida
    entorno = os.environ if entorno is None else entorno
    args = _parser().parse_args(None if argv is None else list(argv))

    def escribir(texto: str) -> None:
        print(texto, file=salida)

    diario = resolver_diario(argumento=args.diario, entorno=entorno)
    diario_supervisor = diario_de_supervision(diario)

    escribir(f"repositorio:        {args.repo}")
    escribir(f"diario del motor:   {diario}")
    escribir(f"diario supervisión: {diario_supervisor}")

    if args.ensayo:
        escribir("")
        escribir("ENSAYO: no se ha supervisado nada. Quita --ensayo para dar el turno.")
        return 0

    diario.parent.mkdir(parents=True, exist_ok=True)

    resultado = supervise_runs(
        DurableWorkEngineStore(diario),
        GitHubActionsRunObserver(probe=GitHubActionsRunProbe(), repo=args.repo),
        DurableSupervisorJournal(diario_supervisor),
        now=datetime.now(UTC) if ahora is None else ahora,
    )

    escribir("")
    for linea in _resumen(resultado):
        escribir(linea)

    if resultado.errors:
        escribir("")
        for error in resultado.errors:
            escribir(f"ERROR: {error}")
        return 1
    return 0


if __name__ == "__main__":  # pragma: no cover - lo cubre la prueba del punto de entrada
    raise SystemExit(main())
