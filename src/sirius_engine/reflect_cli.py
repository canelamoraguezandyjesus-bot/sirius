"""``sirius-reflejar``: cablea C1 al almacén real (incidencia #529).

Cáscara y nada más, igual que ``sirius-supervisar`` (D2, #296) y
``sirius-racha`` (D1, #268): resuelve rutas, monta los mismos Adapters de
producción que ya usa ``sirius-racha`` -``DurableWorkEngineStore``,
``DurableDispatchJournal``, ``GitHubCliMirrorReader``-, y por cada ``WorkItem``
despachado y no terminal calcula y aplica el plan de
:func:`sirius_engine.reflect.reflejar_desenlace`. Ninguna decisión vive aquí:
el plan lo calcula ``reflect.py``; aplicarlo es una llamada mecánica a
:func:`sirius_engine.reflect.aplicar_pasos`.

**Qué hace ``--ensayo``, y qué no.** Con ``--ensayo`` se resuelven rutas y
Adapters, se lee el espejo de cada incidencia y se imprime el plan que se
aplicaría -sin llamar a ``aplicar_pasos``-. Sin ``--ensayo``, cada paso se
aplica de verdad, uno a uno, contra el almacén durable.

**Dónde enganchar esto de verdad (recomendación para C1b, ADR-002: fuera de
alcance de este módulo).** El propietario debería llamar a
``uv run sirius-reflejar`` justo después de cada cambio de etiqueta que
``advance-sirius-after-quality.yml``, ``review-sirius-work.yml``,
``repair-sirius-work.yml`` y ``complete-sirius-after-merge.yml`` ya aplican
hoy -mismo punto en el ciclo donde ``sirius-racha`` lee el espejo, así que
compartir ese momento no añade una lectura nueva-. Cablearlo pertenece a
``.github/**`` y es una decisión del propietario, no de esta incidencia.
"""

from __future__ import annotations

import argparse
import os
import sys
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from pathlib import Path

from sirius_engine.adapters.durable.dispatch_journal import DurableDispatchJournal
from sirius_engine.adapters.durable.store import DurableWorkEngineStore
from sirius_engine.adapters.github_cli_mirror import GitHubCliMirrorReader
from sirius_engine.cli import resolver_diario
from sirius_engine.domain.authority import Autoridad, autoridad_de_clase
from sirius_engine.domain.events import AggregateType
from sirius_engine.domain.mirror import EspejoIlegibleError
from sirius_engine.domain.work_item import TERMINAL_STATES
from sirius_engine.mirror_projection import leer_y_proyectar_work_item
from sirius_engine.ports.dispatch_journal import DispatchJournal
from sirius_engine.ports.github_mirror import GitHubMirrorPort
from sirius_engine.ports.store import WorkEngineStore
from sirius_engine.reflect import ResultadoReflejo, aplicar_pasos, reflejar_desenlace

COMANDO = "sirius-reflejar"


def _diario_de_despacho(diario_del_motor: Path) -> Path:
    """El diario del despachador, hermano del diario del motor.

    Misma regla que ``sirius_engine.seven_day_streak_cli._diario_de_despacho``
    y ``sirius_engine.dispatch_cli._diario_de_despacho`` (ADR-064): cada
    punto de entrada la resuelve por sí mismo, sin importarla de otro
    módulo, para no acoplar dos puntos de entrada por un detalle de un
    carácter.
    """
    return diario_del_motor.with_name(f"{diario_del_motor.stem}-despacho.jsonl")


def _work_ids_conocidos(store: WorkEngineStore) -> tuple[str, ...]:
    """Todo ``work_id`` que el diario del motor haya visto, en orden de primera aparición.

    Misma función que :mod:`sirius_engine.seven_day_streak_cli` -no se
    importa de allí porque es privada a ese módulo.
    """
    vistos: list[str] = []
    for evento in store.list_events():
        if evento.aggregate_type is AggregateType.WORK_ITEM and evento.aggregate_id not in vistos:
            vistos.append(evento.aggregate_id)
    return tuple(vistos)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog=COMANDO,
        description=(
            "Refleja el desenlace real de GitHub en el almacén del motor: por cada "
            "WorkItem despachado y no terminal, aplica la secuencia mínima de "
            "transiciones que lo lleva a lo que su incidencia proyecta. Sin "
            "--ensayo, aplica de verdad."
        ),
    )
    parser.add_argument("--diario", default=None, help="ruta del diario durable del motor")
    parser.add_argument(
        "--ensayo",
        action="store_true",
        help="imprimir el plan de cada WorkItem despachado sin aplicar nada",
    )
    return parser


def main(
    argv: Sequence[str] | None = None,
    *,
    entorno: Mapping[str, str] | None = None,
    salida: object = None,
    ahora: datetime | None = None,
    store: WorkEngineStore | None = None,
    dispatch_journal: DispatchJournal | None = None,
    mirror: GitHubMirrorPort | None = None,
) -> int:
    """Punto de entrada de ``sirius-reflejar``.

    ``store``/``dispatch_journal``/``mirror`` son inyectables, igual que en
    ``sirius_engine.seven_day_streak_cli.main``, para que una prueba corra el
    comando entero sin diario real ni ``gh``.
    """
    args = _parser().parse_args(list(argv) if argv is not None else None)
    entorno = entorno if entorno is not None else os.environ
    escribir = getattr(salida, "write", None) or (lambda t: sys.stdout.write(t))
    ahora = ahora or datetime.now(UTC)

    def linea(texto: str = "") -> None:
        escribir(f"{texto}\n")

    diario = resolver_diario(argumento=args.diario, entorno=entorno)
    if store is None:
        store = DurableWorkEngineStore(diario)
    if dispatch_journal is None:
        dispatch_journal = DurableDispatchJournal(_diario_de_despacho(diario))
    if mirror is None:
        mirror = GitHubCliMirrorReader()

    if args.ensayo:
        linea(f"diario del motor:    {diario}")
        linea(f"diario de despacho:  {_diario_de_despacho(diario)}")
        linea("")
        linea("ENSAYO: no se aplica ningún paso. Quita --ensayo para reflejar de verdad.")
        linea("")

    aplicados_total = 0
    for work_id in _work_ids_conocidos(store):
        item = store.get_work_item(work_id)
        if item is None or item.estado in TERMINAL_STATES:
            continue
        if autoridad_de_clase(item.clase) is not Autoridad.INCIDENCIA:
            continue
        episodio = dispatch_journal.episode_for(work_id)
        if episodio is None:
            continue
        try:
            espejo = leer_y_proyectar_work_item(
                mirror, repo=episodio.repo, numero=episodio.numero_incidencia, ahora=ahora
            )
        except EspejoIlegibleError as error:
            linea(
                f"{work_id}: no pude leer la incidencia #{episodio.numero_incidencia} "
                f"({error}). No se refleja nada esta pasada."
            )
            continue

        resultado: ResultadoReflejo = reflejar_desenlace(item, espejo, episodio)

        if not resultado.pasos:
            if resultado.divergencia:
                linea(resultado.divergencia)
            continue

        if args.ensayo:
            pasos_texto = ", ".join(paso.kind for paso in resultado.pasos)
            linea(f"{work_id}: aplicaría {len(resultado.pasos)} paso(s): {pasos_texto}")
            continue

        aplicar_pasos(store, work_id, resultado.pasos, now=ahora)
        aplicados_total += len(resultado.pasos)
        pasos_texto = ", ".join(paso.kind for paso in resultado.pasos)
        linea(f"{work_id}: aplicados {len(resultado.pasos)} paso(s): {pasos_texto}")

    if not args.ensayo:
        linea("")
        linea(f"Pasos aplicados en total: {aplicados_total}.")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
