"""``sirius-despachar``: la costura entre una orden del propietario y la vía GitHub.

Las tres piezas ya existían y **ninguna llamaba a la siguiente**: la puerta de
intención (A5), la toma que crea el WorkItem (A5) y el despachador que escribe
en GitHub (C2). El bloque C2 dejó fuera este cableado a propósito -su encargo lo
declaraba como frontera- y lo hace por tanto una sesión interactiva (ADR-002).

    orden (texto)
      -> interpretar_intencion_v0   ->  IntentSignal
      -> decidir                    ->  DecisionPuerta
      -> aplicar_decision           ->  WorkItem ACTIVE
      -> dispatch_work_item         ->  incidencia + etiqueta de activación

Por qué es un comando aparte de ``sirius-motor`` y no un subcomando suyo: aquel
existe para conversar y consultar, y **declina las órdenes a propósito** -la
primera propiedad de A5 es que conversar no crea trabajo, y hay pruebas que la
fijan-. Meter aquí dentro un camino que sí crea trabajo borraría esa garantía
justo donde está escrita.

**El ensayo es lo que sale por defecto.** Sin ``--ejecutar`` no se escribe nada:
se enseña qué incidencia se crearía y se sale. Una orden mal entendida no puede
costar una incidencia de verdad, y de una incidencia de verdad cuelga un ciclo
entero -implementador, Quality, dos revisores-, así que el accidente no es
barato.
"""

from __future__ import annotations

import argparse
import os
import sys
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime

from sirius_engine.adapters.durable.store import DurableWorkEngineStore
from sirius_engine.adapters.github_cli_writer import GitHubCliWriter, MissingCredentialError
from sirius_engine.adapters.memory_dispatch_journal import InMemoryDispatchJournal
from sirius_engine.adapters.memory_store import InMemoryWorkEngineStore
from sirius_engine.cli import REPO, resolver_diario
from sirius_engine.dispatcher import dispatch_work_item
from sirius_engine.domain.dispatch import MARCADOR_ORDEN_PROPIETARIO
from sirius_engine.gate import ResultadoPuerta, decidir
from sirius_engine.intent_interpreter import interpretar_intencion_v0
from sirius_engine.issue_body_projection import generar_cuerpo_incidencia
from sirius_engine.ports.github_writer import GitHubWriterPort, IncidenciaCreada
from sirius_engine.ports.store import WorkEngineStore
from sirius_engine.profile_field import ProfileRef
from sirius_engine.work_intake import aplicar_decision

COMANDO = "sirius-despachar"

#: Perfil bajo el que se despacha por defecto: el implementador genérico, que es
#: el que atiende la clase ``programacion`` en la vía GitHub.
PERFIL_POR_DEFECTO = ProfileRef(ref="implementer", version=1)

#: Rama base sobre la que se pide el trabajo.
BASE_POR_DEFECTO = "main"

#: Prefijo de la referencia cuando la orden se dio por terminal y no hay URL que
#: citar: apunta al diario del motor, bajo el work_id que sigue.
_ORIGEN_CLI = "diario-del-motor:"


class _EscritorDeEnsayo:
    """Escritor que no escribe: deja al ensayo atravesar las guardas reales.

    Devuelve un número de incidencia imposible (0) a propósito. Si algún día
    este objeto se colara en un camino de verdad, lo que salga apuntará a
    ``issues/0`` -que no existe- en vez de a una incidencia ajena.
    """

    def crear_incidencia(
        self, *, repo: str, titulo: str, cuerpo: str, etiquetas: tuple[str, ...]
    ) -> IncidenciaCreada:
        return IncidenciaCreada(numero=0, url=f"https://github.com/{repo}/issues/0")

    def aplicar_etiqueta(self, *, repo: str, numero: int, etiqueta: str) -> None:
        return None


def _work_id(ahora: datetime) -> str:
    """Identificador del trabajo, derivado del instante de la orden.

    No se usa aleatoriedad: dos órdenes distintas en el mismo segundo son un
    caso que no se da con un comando que teclea una persona, y un identificador
    reproducible es más fácil de rastrear después en el diario.
    """
    return f"WI-{ahora.strftime('%Y%m%d-%H%M%S')}"


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog=COMANDO,
        description=(
            "Convierte una orden del propietario en una incidencia activada, "
            "por la misma vía que usaría él. Por defecto solo ENSAYA."
        ),
    )
    parser.add_argument("orden", help="La orden, tal cual. Por ejemplo: «Corrige …».")
    parser.add_argument(
        "--ejecutar",
        action="store_true",
        help="Escribir de verdad en GitHub. Sin esto solo se enseña qué se haría.",
    )
    parser.add_argument("--repo", default=REPO, help=f"Repositorio destino (por defecto {REPO}).")
    parser.add_argument("--bloque", default="ENCARGO", help="Etiqueta del bloque para el título.")
    parser.add_argument(
        "--orden-ref",
        default=None,
        help=(
            "Dónde consta la orden (p. ej. la URL del comentario del propietario). "
            "Sin esto se enlaza el propio diario del motor, donde queda su texto."
        ),
    )
    parser.add_argument("--diario", default=None, help="Ruta del diario durable del motor.")
    return parser


def main(
    argv: Sequence[str] | None = None,
    *,
    entorno: Mapping[str, str] | None = None,
    salida: object = None,
    ahora: datetime | None = None,
) -> int:
    args = _parser().parse_args(list(argv) if argv is not None else None)
    entorno = entorno if entorno is not None else os.environ
    escribir = getattr(salida, "write", None) or (lambda t: sys.stdout.write(t))
    ahora = ahora or datetime.now(UTC)

    def linea(texto: str = "") -> None:
        escribir(f"{texto}\n")

    señal = interpretar_intencion_v0(args.orden)
    decision = decidir(señal)

    if decision.resultado is ResultadoPuerta.NO_CREAR:
        linea("No he creado nada.")
        linea(f"  Motivo: {decision.motivo}")
        linea("")
        linea("La orden no se entendió como un encargo inequívoco. Quien interpreta")
        linea("hoy es un apaño provisional (ADR-043) que reconoce pocos verbos: para")
        linea("programación, «corrige» o «implementa» al principio de la frase.")
        return 2

    # Un ENSAYO no persiste nada. Si usara el almacén durable dejaría un
    # WorkItem ACTIVE que nadie va a despachar: exactamente el estado
    # inconsistente -trabajo activo sin nada que lo atienda- que el resto del
    # motor se cuida de no producir. El ensayo enseña qué pasaría; no lo hace
    # a medias.
    store: WorkEngineStore
    if args.ejecutar:
        store = DurableWorkEngineStore(resolver_diario(argumento=args.diario, entorno=entorno))
    else:
        store = InMemoryWorkEngineStore()
    work_id = _work_id(ahora)

    # El despachador se niega a activar un WorkItem cuya orden no se pueda
    # encontrar después (§12.1), y esta es la única capa que sabe de dónde vino.
    # Sin --orden-ref la referencia es el propio diario: ahí queda el texto
    # íntegro de la orden bajo este work_id, que es una respuesta real a "¿quién
    # pidió esto?" -no un relleno para pasar la guarda-.
    referencia_orden = args.orden_ref or f"{_ORIGEN_CLI}{work_id}"
    resultado = aplicar_decision(
        decision,
        store=store,
        work_id=work_id,
        peticion_original=args.orden,
        now=ahora,
        evidencia=(f"{MARCADOR_ORDEN_PROPIETARIO}{referencia_orden}",),
    )

    if decision.resultado is ResultadoPuerta.CREAR_Y_ESCALAR:
        linea("He creado el trabajo, pero NO lo he despachado: necesita tu decisión.")
        linea(f"  Trabajo: {work_id}")
        if resultado.escalada is not None:
            linea(f"  Causa:   {resultado.escalada.causa.value}")
        return 3

    assert resultado.work_item is not None
    work_item = resultado.work_item

    linea(f"Orden entendida como clase «{work_item.clase.value}».")
    linea(f"  Trabajo:    {work_id}")
    linea(f"  Objetivo:   {work_item.objetivo}")
    linea(f"  Entregable: {work_item.entregable}")
    linea(f"  Autoridad:  {resultado.autoridad.value if resultado.autoridad else '-'}")
    linea("")

    writer: GitHubWriterPort
    if args.ejecutar:
        try:
            writer = GitHubCliWriter()
        except MissingCredentialError as error:
            linea(f"No puedo escribir en GitHub: {error}")
            return 4
    else:
        # El ensayo atraviesa el MISMO despachador, con un escritor que no
        # escribe. Antes se cortaba justo antes de llamarlo, y por eso podía
        # decir "esto saldría" de un trabajo que el despachador habría
        # rechazado -que es exactamente lo que pasó con la orden no enlazada-.
        # Un ensayo que no pasa por las guardas no ensaya nada (H-12).
        writer = _EscritorDeEnsayo()

    desenlace = dispatch_work_item(
        work_item,
        writer=writer,
        journal=InMemoryDispatchJournal(),
        repo=args.repo,
        profile_ref=PERFIL_POR_DEFECTO,
        bloque=args.bloque,
        now=ahora,
        base_branch=BASE_POR_DEFECTO,
    )
    episodio = desenlace.episodio
    if not args.ejecutar:
        linea("ENSAYO: no se ha escrito nada en GitHub.")
        linea("El despachador aceptó el trabajo: con --ejecutar crearía la incidencia")
        linea(f"en {args.repo} con la etiqueta «{episodio.etiqueta}».")
        linea("")
        linea("--- cuerpo que llevaría la incidencia ---")
        linea(
            generar_cuerpo_incidencia(
                work_item,
                profile_ref=PERFIL_POR_DEFECTO,
                bloque=args.bloque,
                base_branch=BASE_POR_DEFECTO,
            )
        )
        return 0

    if desenlace.ya_despachado:
        linea(f"Ya estaba despachado: incidencia #{episodio.numero_incidencia}.")
    else:
        linea(f"Despachado: incidencia #{episodio.numero_incidencia}.")
        linea(f"  https://github.com/{episodio.repo}/issues/{episodio.numero_incidencia}")
        linea(f"  Etiqueta aplicada: {episodio.etiqueta}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
