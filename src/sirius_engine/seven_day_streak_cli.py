"""``sirius-racha``: el ejecutor diario de D1a y el contador de los siete días (D1b, #268).

Costura entre tres piezas que ya existían y ninguna llamaba a la siguiente en
una sola pasada: el almacén durable del motor (A2), el diario del
despachador -que sabe a qué incidencia de GitHub corresponde cada
``work_id`` despachado, C2- y el verificador de proyección (D1a). Este
comando:

1. Para cada ``WorkItem`` no terminal cuya clase tenga autoridad
   ``incidencia`` (contrato §11.1, :func:`sirius_engine.domain.authority.autoridad_de_clase`)
   y que ya se haya despachado -el diario del despachador es quien sabe a qué
   incidencia corresponde-, lee su incidencia real y llama a
   :func:`~sirius_engine.projection_verifier.verificar_dia`.
2. Añade las líneas resultantes al registro versionado
   (:func:`sirius_engine.seven_day_streak.anadir_lineas`).
3. Evalúa la racha vigente de cada clase con autoridad ``incidencia``
   (:func:`sirius_engine.seven_day_streak.evaluar_racha`) y la publica por
   salida estándar.

**No conmuta nada** (contrato §11.3): ninguna llamada de este módulo toca
``sirius_engine.domain.authority`` ni ningún estado del motor. Publica y
registra; la conmutación, si algún día llega, es un acto aparte y de otro
bloque -así lo fija el objetivo de la incidencia #268.

Sin credencial de ``gh`` -o sin red- las incidencias despachadas que no se
puedan leer se informan y se saltan (misma disciplina que ADR-036: una
lectura caída no es una ausencia, así que no se registra una línea inventada
para ese ``work_id`` esa pasada).

Nada de esto engancha el comando a un horario: eso es automatización
(``.github/**``) y queda fuera de este bloque (ADR-002). El horario
recomendado -derivado, no elegido a ojo- lo calcula
:func:`sirius_engine.seven_day_streak.hora_recomendada_pasada` y lo expone
``--hora-recomendada`` (CODEX-003, ronda 2), sin ejecutar la pasada ni tocar
ningún ``schedule``; cablearlo a un ``cron`` real es trabajo de otra
incidencia.

**Esto cambió el 24-08-2026 y conviene leerlo entero.** Hasta D2, ningún
workflow ni script invocaba ningún comando de ``sirius_engine``, y por eso
ADR-074 documentó que el almacén del motor no era todavía la maquinaria que
hace avanzar el ciclo. Desde D2 existe ``motor-sirius.yml``, que invoca
``sirius-supervisar`` y confirma el diario en el repositorio.

Pero **el contador sigue sin poder contar de verdad**, y por un motivo
distinto al de antes: ese workflow arranca **solo a mano**, sin horario,
mientras se comprueba que da bien un turno. Un motor que no corre por su
cuenta no lleva el ciclo, así que una pasada real seguirá midiendo con
honestidad ``sin línea registrada`` o divergencias estructurales de fase;
nunca un falso verde. Lo que falta ya no es el cableado: es la cadencia, y es
la decisión siguiente de D2.
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
from sirius_engine.domain.work_item import TERMINAL_STATES, WorkItemClass
from sirius_engine.mirror_projection import leer_y_proyectar_work_item
from sirius_engine.ports.dispatch_journal import DispatchJournal
from sirius_engine.ports.github_mirror import GitHubMirrorPort
from sirius_engine.ports.store import WorkEngineStore
from sirius_engine.projection_verifier import (
    ContextoEjesDiarios,
    ventana_tolerancia_etiqueta_maquina,
    verificar_dia,
)
from sirius_engine.seven_day_streak import (
    DIAS_REQUERIDOS,
    anadir_lineas,
    evaluar_racha,
    hora_recomendada_pasada,
    leer_registro,
)

COMANDO = "sirius-racha"

#: Ruta del registro versionado y de ``.github/workflows``, relativas a la
#: raíz del repositorio que ``--raiz``/``SIRIUS_RACHA_RAIZ`` resuelvan
#: (CODEX-002, ronda 2): un ejecutable instalado no puede derivarlas de
#: ``__file__`` -en un wheel, eso cae bajo ``site-packages``, que no lleva
#: ni ``.github`` ni ``docs/operations``-.
_REGISTRO_RELATIVO = Path("docs") / "operations" / "racha_siete_dias.jsonl"
_WORKFLOWS_RELATIVO = Path(".github") / "workflows"

#: Variable de entorno con la que se puede fijar la raíz sin tocar código,
#: mismo patrón que ``SIRIUS_MOTOR_RAIZ`` en :mod:`sirius_engine.cli`
#: (ADR-055) -no se importa de allí porque cada punto de entrada resuelve su
#: propia raíz, igual que cada uno resuelve su propio diario.
VARIABLE_RAIZ = "SIRIUS_RACHA_RAIZ"


def resolver_raiz(*, argumento: str | None, entorno: Mapping[str, str]) -> Path:
    """``--raiz`` manda sobre ``SIRIUS_RACHA_RAIZ``, y este sobre el directorio actual.

    El directorio actual sirve de defecto razonable para quien ya está
    parado en un checkout -que es como corren hoy la CI y las pruebas-, pero
    un wheel o ejecutable instalado necesita que alguien lo diga: por eso
    ``sirius-racha`` nunca deriva esta ruta de ``__file__``.
    """
    if argumento:
        return Path(argumento).expanduser()
    del_entorno = entorno.get(VARIABLE_RAIZ)
    if del_entorno:
        return Path(del_entorno).expanduser()
    return Path.cwd()


def _diario_de_despacho(diario_del_motor: Path) -> Path:
    """El diario del despachador, hermano del diario del motor.

    Misma regla que ``sirius_engine.dispatch_cli._diario_de_despacho``
    (ADR-064): no se importa de allí -es privada a ese módulo- para no
    acoplar dos puntos de entrada por un detalle de un carácter.
    """
    return diario_del_motor.with_name(f"{diario_del_motor.stem}-despacho.jsonl")


def _work_ids_conocidos(store: WorkEngineStore) -> tuple[str, ...]:
    """Todo ``work_id`` que el diario del motor haya visto, en orden de primera aparición."""
    vistos: list[str] = []
    for evento in store.list_events():
        if evento.aggregate_type is AggregateType.WORK_ITEM and evento.aggregate_id not in vistos:
            vistos.append(evento.aggregate_id)
    return tuple(vistos)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog=COMANDO,
        description=(
            "Ejecuta una pasada diaria del verificador de proyección (D1a) sobre los "
            "trabajos despachados con autoridad de la incidencia, añade sus líneas al "
            "registro versionado y evalúa la racha de siete días por clase. No conmuta "
            "nada (contrato §11.3)."
        ),
    )
    parser.add_argument("--diario", default=None, help="ruta del diario durable del motor")
    parser.add_argument(
        "--registro",
        default=None,
        help=(
            f"ruta del registro versionado (por defecto {_REGISTRO_RELATIVO} bajo la raíz "
            "resuelta, ver --raiz)"
        ),
    )
    parser.add_argument(
        "--raiz",
        default=None,
        help=(
            "raíz del repositorio cuyos .github/workflows y registro versionado usar "
            f"(por defecto, ${VARIABLE_RAIZ} o el directorio actual)"
        ),
    )
    parser.add_argument(
        "--hora-recomendada",
        action="store_true",
        help=(
            "imprime la hora derivada para cablear este comando a un horario, y por qué, "
            "sin ejecutar la pasada (no conmuta ni crea ningún schedule)"
        ),
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
    """Punto de entrada de ``sirius-racha``.

    ``store``/``dispatch_journal``/``mirror`` son inyectables a propósito
    -igual que ``entrada``/``salida``/``entorno`` en :mod:`sirius_engine.cli`-
    para que una prueba pueda correr el comando entero sin diario real ni
    ``gh``: sin ellos, se construyen los Adapters de producción.
    """
    args = _parser().parse_args(list(argv) if argv is not None else None)
    entorno = entorno if entorno is not None else os.environ
    escribir = getattr(salida, "write", None) or (lambda t: sys.stdout.write(t))
    ahora = ahora or datetime.now(UTC)

    def linea(texto: str = "") -> None:
        escribir(f"{texto}\n")

    raiz = resolver_raiz(argumento=args.raiz, entorno=entorno)
    workflows_dir = raiz / _WORKFLOWS_RELATIVO

    if args.hora_recomendada:
        linea(hora_recomendada(workflows_dir))
        return 0

    diario = resolver_diario(argumento=args.diario, entorno=entorno)
    if store is None:
        store = DurableWorkEngineStore(diario)
    if dispatch_journal is None:
        dispatch_journal = DurableDispatchJournal(_diario_de_despacho(diario))
    if mirror is None:
        mirror = GitHubCliMirrorReader()
    registro = Path(args.registro) if args.registro else raiz / _REGISTRO_RELATIVO
    ventana_tolerancia = ventana_tolerancia_etiqueta_maquina(workflows_dir)

    lineas_nuevas = []
    for work_id in _work_ids_conocidos(store):
        item = store.get_work_item(work_id)
        if item is None or item.estado in TERMINAL_STATES:
            continue
        if autoridad_de_clase(item.clase) is not Autoridad.INCIDENCIA:
            continue
        episodio = dispatch_journal.episode_for(work_id)
        if episodio is None:
            linea(f"  {work_id}: aún sin despachar a GitHub, nada que comparar todavía.")
            continue
        try:
            espejo = leer_y_proyectar_work_item(
                mirror, repo=episodio.repo, numero=episodio.numero_incidencia, ahora=ahora
            )
        except EspejoIlegibleError as error:
            linea(
                f"  {work_id}: no pude leer la incidencia #{episodio.numero_incidencia} "
                f"({error}). No se registra línea esta pasada: no es que no hubiera nada."
            )
            continue
        lineas_nuevas.append(
            verificar_dia(
                motor=item,
                espejo=espejo,
                # Ningún proveedor de este comando conoce todavía cuándo se
                # aplicó la etiqueta de máquina vigente -el puerto del
                # espejo (`GitHubMirrorPort`) no expone esa lectura-, así
                # que la edad se declara desconocida. `verificar_dia` ya
                # trata una edad desconocida de forma segura: las ventanas
                # 1 y 4 (residencia normal de etiqueta) no protegen nada, y
                # una divergencia real sigue leyéndose como divergencia
                # (nunca como un verde inventado).
                contexto=ContextoEjesDiarios(edad_etiqueta_maquina=None),
                ventana_tolerancia=ventana_tolerancia,
                instante=ahora,
            )
        )

    anadidas = anadir_lineas(registro, lineas_nuevas)
    linea(f"Pasada registrada: {anadidas} línea(s) nueva(s) en {registro}.")
    linea("")

    lineas_totales = leer_registro(registro)
    eventos = store.list_events()
    for clase in WorkItemClass:
        if autoridad_de_clase(clase) is not Autoridad.INCIDENCIA:
            continue
        evaluacion = evaluar_racha(
            lineas=lineas_totales, eventos=eventos, clase=clase, hoy=ahora.date()
        )
        estado = "CUMPLE" if evaluacion.cumple else "no cumple"
        linea(f"{clase.value} ({DIAS_REQUERIDOS} días requeridos): {estado} — {evaluacion.motivo}")

    linea("")
    linea("Esta pasada no conmuta nada (contrato §11.3): solo mide y registra.")
    return 0


def hora_recomendada(workflows_dir: Path) -> str:
    """Texto informativo: la hora derivada para cablear este comando a un horario, y por qué.

    No engancha nada -eso es ADR-002 y otro bloque-: es lo que quien cablee
    el ``cron`` necesita para no elegir una hora a ojo. ``workflows_dir``
    viene siempre de la raíz ya resuelta (``--raiz``/``SIRIUS_RACHA_RAIZ``,
    CODEX-002): un ejecutable instalado no tiene ``.github/workflows`` bajo
    ``__file__``, así que esta función ya no lo asume por defecto.
    """
    hora, motivo = hora_recomendada_pasada(workflows_dir)
    return f"{hora.isoformat(timespec='minutes')} UTC — {motivo}"


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
