"""``sirius-decidir``: la salida que a una parada de la puerta le faltaba.

La puerta de sensibilidad (A5, :func:`sirius_engine.gate.decidir`) para un
trabajo **antes** de crear la incidencia y lo deja anotado en
``NEEDS_DECISION``, sin incidencia detrás. ADR-184 hizo que la parada dijera
dónde queda el trabajo y ADR-188 que dijera por qué; lo que no existía era una
**salida**. Medido el 13-09-2026 sobre el diario de la rama ``estado-del-motor``
(635 sucesos): las cuatro paradas que el diario contiene siguen las cuatro en
``NEEDS_DECISION``, cada una con un solo suceso en su historia y ninguna con
incidencia detrás; la más antigua llevaba diez días.

Por qué no podían salir: de ``NEEDS_DECISION`` sale una sola arista,
``resolve_decision`` (§3.2, y el dominio la tiene), y su único llamante de
producción era el reflector, que **necesita una incidencia que mirar** -sin
episodio de despacho se salta el trabajo (``reflect_cli``: «no consta
despachado a ninguna incidencia; no se refleja»)-. Así que cada vez que la
puerta acertaba dejaba un trabajo inmortal (ADR-189).

    trabajo en NEEDS_DECISION, sin incidencia
      --terminar  -> resolve_decision(continuar=False) -> CANCELLED, terminal
      --continuar -> resolve_decision(continuar=True)  -> ACTIVE
                     Y dispatch_work_item              -> incidencia + etiqueta

**Reanudar es despachar en el mismo gesto, y eso es la mitad de la decisión.**
``resolve_decision(continuar=True)`` a secas deja el trabajo en ``ACTIVE`` sin
incidencia detrás, y ahí nadie lo atiende: sería cambiar una fuga por otra. Por
eso todo lo que puede impedir el despacho -la quinta causa de ADR-188, la clase
fuera de :data:`~sirius_engine.dispatcher.TABLA_ACTIVACION`, el carril retirado,
la orden no enlazada, la credencial que falta- se comprueba **antes** de tocar el
almacén, y si algo falta no se reanuda nada.

**El ensayo es lo que sale por defecto**, igual que en ``sirius-despachar`` y por
el mismo motivo: una decisión sobre el identificador equivocado no es barata. Y
el ensayo atraviesa el despachador de verdad con un escritor que no escribe
(H-12), porque un ensayo que se corta antes de las guardas no ensaya nada.

**Solo resuelve paradas SIN incidencia detrás.** Con incidencia, el desenlace lo
acredita GitHub y lo aplica el reflector (ADR-173, ADR-176, ADR-147): este
comando se niega y lo dice. Es un comando de consola y ningún workflow lo
invoca; la decisión sigue siendo un gesto del propietario.
"""

from __future__ import annotations

import argparse
import os
import sys
from collections.abc import Callable, Mapping, Sequence
from datetime import UTC, datetime
from pathlib import Path

from sirius_engine.adapters.durable.dispatch_journal import DurableDispatchJournal
from sirius_engine.adapters.durable.store import DurableWorkEngineStore
from sirius_engine.adapters.github_cli_writer import (
    GitHubCliWriter,
    GitHubWriteError,
    MissingCredentialError,
)
from sirius_engine.adapters.memory_dispatch_journal import InMemoryDispatchJournal
from sirius_engine.carriles_retirados import carril_retirado
from sirius_engine.cli import REPO, resolver_diario

# ``_EscritorDeEnsayo`` es el escritor que no escribe del ensayo de
# ``sirius-despachar``, y se reutiliza tal cual: mismo propósito -atravesar las
# guardas reales sin tocar GitHub- y una segunda copia solo podría envejecer
# distinto. Se importa con su nombre privado porque no es una pieza pública del
# motor: es el doble de un ensayo.
from sirius_engine.dispatch_cli import (
    BASE_POR_DEFECTO,
    PERFIL_POR_DEFECTO,
    TABLA_PERFILES,
    _EscritorDeEnsayo,
    diario_de_despacho,
    ruta_copiable,
)
from sirius_engine.dispatcher import TABLA_ACTIVACION, dispatch_work_item
from sirius_engine.domain.dispatch import orden_enlazada
from sirius_engine.domain.work_item import WorkItem, WorkItemState
from sirius_engine.intent_interpreter import alcance_que_el_motor_no_puede_escribir
from sirius_engine.ports.dispatch_journal import DispatchJournal
from sirius_engine.ports.github_writer import GitHubWriterPort
from sirius_engine.ports.store import WorkEngineStore
from sirius_engine.profile_field import project_perfil_field

COMANDO = "sirius-decidir"

#: Los estados desde los que este comando puede hacer algo, y por qué solo
#: estos dos:
#:
#: - ``NEEDS_DECISION`` es la parada: es el caso para el que existe el comando.
#: - ``ACTIVE`` **sin episodio de despacho** es una reanudación que se quedó a
#:   medias -se aplicó la transición y la escritura en GitHub no llegó a
#:   grabarse-, y ahí ``--continuar`` retoma el despacho en vez de atascarse.
#:   Es la lección de ADR-176 aplicada aquí: se mira el estado en el que el
#:   motor ESTÁ, no el que se esperaba que tuviera. Sin esto, un corte entre las
#:   dos escrituras dejaría exactamente el trabajo inmortal que este comando
#:   viene a evitar.
_ESTADOS_QUE_CONTINUAN = frozenset({WorkItemState.NEEDS_DECISION, WorkItemState.ACTIVE})


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog=COMANDO,
        description=(
            "Resuelve un trabajo que la puerta paró y dejó sin incidencia detrás: "
            "continúa (y lo despacha) o lo da por terminado. Por defecto solo ENSAYA."
        ),
    )
    parser.add_argument(
        "work_id", help="El identificador del trabajo. Por ejemplo: WI-20260903-030529."
    )
    decision = parser.add_mutually_exclusive_group(required=True)
    decision.add_argument(
        "--continuar",
        action="store_true",
        help="El trabajo continúa: se reanuda Y se despacha, en el mismo gesto.",
    )
    decision.add_argument(
        "--terminar",
        action="store_true",
        help="El trabajo se da por terminado: queda cancelado, que es terminal.",
    )
    parser.add_argument(
        "--ejecutar",
        action="store_true",
        help="Aplicar la decisión de verdad. Sin esto solo se enseña qué se haría.",
    )
    parser.add_argument("--repo", default=REPO, help=f"Repositorio destino (por defecto {REPO}).")
    parser.add_argument("--bloque", default="ENCARGO", help="Etiqueta del bloque para el título.")
    parser.add_argument("--diario", default=None, help="Ruta del diario durable del motor.")
    return parser


def _la_salida_que_queda(work_item: WorkItem) -> tuple[str, ...]:
    """A dónde va el trabajo cuando «--continuar» lo rechaza, según DÓNDE está.

    `--terminar` solo es una salida desde `needs_decision`: `_terminar` exige ese
    estado y sale con 4 sin tocar nada, porque el dominio no tiene arista
    `ACTIVE -> CANCELLED` (§3.2). Este comando admite a propósito los dos estados
    de partida (`_ESTADOS_QUE_CONTINUAN`), así que ofrecer «--terminar» a un
    trabajo `active` sería cerrarle las dos puertas con un texto que promete una
    que no existe -la misma familia de «prometer lo que no va a ocurrir» que
    ADR-184 y ADR-188 cerraron para los otros mensajes-. El dominio no se toca:
    lo que se corrige es el TEXTO.
    """
    if work_item.estado is WorkItemState.NEEDS_DECISION:
        return ("La salida que sí tiene es «--terminar».",)
    return (
        f"Y «--terminar» tampoco: «{work_item.work_id}» ya está reanudado -«active»-, y",
        "de ahí el dominio no admite cancelar (§3.2), así que saldría con 4 sin tocar",
        "nada. Este trabajo queda como asunto del propietario en sesión interactiva.",
    )


def _no_se_puede_despachar(work_item: WorkItem) -> tuple[str, ...] | None:
    """Por qué ``--continuar`` no puede despachar ``work_item``, o ``None`` si puede.

    Las mismas guardas que :func:`~sirius_engine.dispatcher.dispatch_work_item`
    comprueba, consultadas **antes** de tocar el almacén. No sobran por estar
    dos veces: allí levantan una excepción cuando el trabajo ya está en
    ``ACTIVE``, y lo que hace falta aquí es no llegar a reanudarlo. Es el mismo
    motivo por el que H-17 subió la comprobación de clase de ``sirius-despachar``
    a antes de crear nada: el rechazo tiene que ocurrir antes del efecto que
    habría que deshacer -y aquí no se puede deshacer, porque el diario es
    append-only (ADR-026)-.
    """
    if work_item.clase not in TABLA_ACTIVACION:
        return (
            f"la clase «{work_item.clase.value}» no tiene despachador (contrato §12.4).",
            "Reanudarlo lo dejaría ACTIVE sin nada que lo atienda, así que no se reanuda.",
            *_la_salida_que_queda(work_item),
        )
    retirado = carril_retirado(work_item.clase)
    if retirado is not None:
        return (*retirado.explicacion().splitlines(), *_la_salida_que_queda(work_item))
    if orden_enlazada(work_item) is None:
        return (
            "su evidencia no enlaza ninguna orden del propietario (contrato §12.1),",
            "así que el despachador se negaría a activarlo. No se reanuda.",
            *_la_salida_que_queda(work_item),
        )
    return None


def _bloque_de_la_quinta_causa(work_item: WorkItem) -> tuple[str, ...] | None:
    """El motivo por el que una parada con alcance vetado no se reanuda por aquí.

    ADR-188 movió esta parada a ANTES de crear la incidencia porque despachar el
    trabajo lo mataba en el push: el alcance que la orden declara cae donde la
    credencial del motor no llega (ADR-002), y la #607 hizo el trabajo entero
    para perderlo. ``--continuar`` es, literalmente, despachar: reanudar por aquí
    reproduciría esa pérdida, así que se rechaza y se remite a la sesión
    interactiva, que es la vía que ADR-002 prescribe.

    La pregunta que gobierna el rechazo es «¿el alcance declarado cae donde el
    motor no puede escribir?» (``alcance_que_el_motor_no_puede_escribir``), y NO
    «¿paró la quinta causa?» (``paro_la_quinta_causa``). No son la misma
    pregunta, y el propio repositorio lo fija por escrito: las cuatro causas
    anteriores GANAN a la quinta cuando una orden dispara las dos cosas -«Corrige
    el arranque y borra ``.github/workflows/quality.yml``» sale por destructiva-,
    y el alcance vetado sigue ahí. El push muere por el alcance, no por la causa,
    así que es el alcance lo que decide. La ATRIBUCIÓN de la causa no cambia por
    esto: quien la emite es el bloque de ADR-188 de ``dispatch_cli``, que sigue
    preguntando por la quinta (CLAUDE-REV-612-001).
    """
    prefijo = alcance_que_el_motor_no_puede_escribir(work_item.peticion_original)
    if prefijo is None:
        return None
    return (
        f"el alcance declarado cae bajo «{prefijo}», y ahí el motor no puede escribir:",
        "ADR-002 decidió NO darle ese alcance a su credencial, así que GitHub rechaza",
        "el push. Despacharlo es exactamente lo que ADR-188 vino a impedir: la #607",
        "hizo el trabajo entero -código, pruebas, ADR y validaciones en verde- y lo",
        "perdió al empujar. Reanudarlo por aquí repetiría esa pérdida.",
        "",
        "ADR-002 prescribe hacer este trabajo en sesión interactiva, donde el",
        "propietario tiene el alcance que al motor le falta. La orden, tal cual:",
        "",
        *(f"    {parrafo}" for parrafo in work_item.peticion_original.splitlines() or [""]),
        "",
        *(
            ("Y si aquí ya no hay nada que hacer, «--terminar» lo da por terminado.",)
            if work_item.estado is WorkItemState.NEEDS_DECISION
            else _la_salida_que_queda(work_item)
        ),
    )


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

    diario: Path = resolver_diario(argumento=args.diario, entorno=entorno)
    # Construir el almacén durable solo LEE el diario (`replay`): no lo crea ni
    # lo toca, así que el ensayo puede atravesar el mismo camino que la
    # ejecución de verdad sin dejar rastro.
    store: WorkEngineStore = DurableWorkEngineStore(diario)
    diario_despacho = diario_de_despacho(diario)
    registro_despachos: DispatchJournal = DurableDispatchJournal(diario_despacho)

    work_item = store.get_work_item(args.work_id)
    if work_item is None:
        linea(f"No consta ningún trabajo «{args.work_id}» en el diario.")
        linea(f"  Diario consultado: {diario}")
        linea("")
        linea("Para ver los que hay -y en qué estado está cada uno-, abre la sesión")
        linea(f"«sirius-motor --diario {ruta_copiable(diario)}» y teclea «/trabajos».")
        return 2

    episodio_previo = registro_despachos.episode_for(args.work_id)
    if episodio_previo is not None:
        linea(f"«{args.work_id}» SÍ tiene incidencia detrás: #{episodio_previo.numero_incidencia}.")
        linea("")
        linea("Este comando resuelve las paradas que se quedaron sin incidencia, y esta no")
        linea("es una. Con incidencia, el desenlace lo acredita GitHub -su cierre, sus")
        linea("etiquetas, el permiso escrito del propietario- y lo aplica el reflector")
        linea("(ADR-173, ADR-176, ADR-147): «sirius-reflejar». Decidirlo aquí dejaría la")
        linea("incidencia abierta contando otra cosa.")
        return 3

    if args.terminar:
        return _terminar(work_item, store=store, ahora=ahora, ejecutar=args.ejecutar, linea=linea)
    return _continuar(
        work_item,
        store=store,
        registro_despachos=registro_despachos,
        repo=args.repo,
        bloque=args.bloque,
        ahora=ahora,
        ejecutar=args.ejecutar,
        linea=linea,
    )


def _terminar(
    work_item: WorkItem,
    *,
    store: WorkEngineStore,
    ahora: datetime,
    ejecutar: bool,
    linea: Callable[[str], None],
) -> int:
    if work_item.estado is WorkItemState.CANCELLED:
        linea(f"«{work_item.work_id}» ya estaba terminado: cancelled.")
        linea("No hay nada que aplicar; repetir la orden no cambia nada.")
        return 0
    if work_item.estado is not WorkItemState.NEEDS_DECISION:
        linea(
            f"«{work_item.work_id}» no está en «needs_decision», sino en "
            f"«{work_item.estado.value}»."
        )
        linea("")
        linea("Este comando resuelve una parada de la puerta, y aquí no hay ninguna que")
        linea("resolver. No se toca nada: inventar una transición que el dominio no")
        linea("admite (§3.2) sería peor que no hacer nada.")
        return 4

    if not ejecutar:
        linea(f"ENSAYO: no se ha aplicado nada. «{work_item.work_id}» sigue en")
        linea("«needs_decision».")
        linea("")
        linea("Con «--ejecutar» quedaría «cancelled», que es terminal: el trabajo se da")
        linea("por terminado y no vuelve a salir en lo que espera decisión.")
        return 0

    resuelto = store.resolve_work_item_decision(work_item.work_id, continuar=False, now=ahora)
    linea(f"Terminado: «{work_item.work_id}» queda en «{resuelto.estado.value}».")
    linea("")
    linea("Es un estado terminal (§3.2): la parada ya no espera ninguna decisión. El")
    linea("diario conserva su historia entera -es append-only (ADR-026)-, así que lo")
    linea("que se pidió y por qué se paró siguen ahí.")
    return 0


def _continuar(
    work_item: WorkItem,
    *,
    store: WorkEngineStore,
    registro_despachos: DispatchJournal,
    repo: str,
    bloque: str,
    ahora: datetime,
    ejecutar: bool,
    linea: Callable[[str], None],
) -> int:
    if work_item.estado not in _ESTADOS_QUE_CONTINUAN:
        linea(
            f"«{work_item.work_id}» no está en «needs_decision», sino en "
            f"«{work_item.estado.value}»."
        )
        linea("")
        linea("Este comando resuelve una parada de la puerta, y aquí no hay ninguna que")
        linea("resolver. No se toca nada.")
        return 4

    # --- Todo lo que puede impedir el despacho, ANTES de tocar el almacén -----
    #
    # El orden es la mitad de la decisión (ADR-189): si algo de esto se
    # comprobara después de `resolve_decision`, el trabajo quedaría en ACTIVE sin
    # incidencia detrás -y de ahí no sale nadie, porque el reflector necesita una
    # incidencia que mirar-. Cambiar una fuga por otra es peor que no arreglar
    # nada.
    bloqueo = _bloque_de_la_quinta_causa(work_item)
    if bloqueo is not None:
        linea(f"NO he reanudado «{work_item.work_id}»: no puedo despacharlo.")
        linea("")
        for texto in bloqueo:
            linea(texto)
        return 5
    impedimento = _no_se_puede_despachar(work_item)
    if impedimento is not None:
        linea(f"NO he reanudado «{work_item.work_id}»: no puedo despacharlo.")
        linea("")
        for texto in impedimento:
            linea(texto)
        return 5

    perfil = TABLA_PERFILES.get(work_item.clase, PERFIL_POR_DEFECTO)

    writer: GitHubWriterPort
    registro_efectivo: DispatchJournal
    if ejecutar:
        try:
            writer = GitHubCliWriter()
        except MissingCredentialError as error:
            linea(f"NO he reanudado «{work_item.work_id}»: no puedo escribir en GitHub.")
            linea(f"  {error}")
            linea("")
            # El estado se NOMBRA, no se fija en el texto: este comando admite dos
            # estados de partida (`_ESTADOS_QUE_CONTINUAN`), y al retomar un
            # despacho cortado el trabajo está en «active». Decir «needs_decision»
            # ahí es falso justo cuando el propietario necesita saber dónde quedó
            # el trabajo -la familia que abrió ADR-184-. El ensayo de más abajo
            # ya lo hacía bien.
            if work_item.estado is WorkItemState.NEEDS_DECISION:
                linea("Reanudar sin poder despachar dejaría el trabajo ACTIVE sin incidencia")
                linea("detrás, y de ahí no sale: sigue en «needs_decision», intacto.")
            else:
                linea(f"No se ha tocado nada: sigue en «{work_item.estado.value}», sin incidencia")
                linea("detrás. El despacho que quedó a medias se retoma repitiendo esta misma")
                linea("orden con la credencial puesta.")
            return 6
        registro_efectivo = registro_despachos
    else:
        # El ensayo atraviesa el despachador DE VERDAD con un escritor que no
        # escribe y un diario en memoria (H-12): un ensayo que se corta antes de
        # las guardas diría «esto saldría» de un trabajo que el despachador
        # rechazaría. Y el WorkItem se reanuda **en memoria** -el dominio es
        # inmutable, así que `resolve_decision` devuelve otro objeto y el
        # almacén no se entera de nada-.
        writer = _EscritorDeEnsayo()
        registro_efectivo = InMemoryDispatchJournal()

    reanudado: WorkItem
    if work_item.estado is WorkItemState.NEEDS_DECISION and ejecutar:
        reanudado = store.resolve_work_item_decision(work_item.work_id, continuar=True, now=ahora)
    elif work_item.estado is WorkItemState.NEEDS_DECISION:
        # En ensayo la reanudación es solo del objeto: `WorkItem` es inmutable,
        # así que esto devuelve otro y el almacén no se entera de nada.
        reanudado = work_item.resolve_decision(continuar=True, now=ahora)
    else:
        # ACTIVE sin episodio: la transición ya está aplicada y lo que falta es
        # el despacho. No se vuelve a pedir -el dominio la rechazaría- y no hace
        # falta: se retoma desde donde está (ADR-176).
        reanudado = work_item

    try:
        desenlace = dispatch_work_item(
            reanudado,
            writer=writer,
            journal=registro_efectivo,
            repo=repo,
            profile_ref=perfil,
            bloque=bloque,
            now=ahora,
            base_branch=BASE_POR_DEFECTO,
        )
    except GitHubWriteError as error:
        # El único hueco que queda abierto, y se dice en voz alta en vez de
        # dejarlo callado: la transición ya está grabada y la escritura falló, así
        # que el trabajo está ACTIVE sin incidencia. Repetir la MISMA orden lo
        # retoma -`_ESTADOS_QUE_CONTINUAN` incluye ACTIVE por esto- y la adopción
        # por work_id de H-29 evita que se cree una segunda incidencia.
        linea(f"«{work_item.work_id}» quedó reanudado y el despacho FALLÓ.")
        linea(f"  {error}")
        linea("")
        linea("Está en «active» y todavía sin incidencia detrás. Repite esta misma orden")
        linea("para retomar el despacho: no creará una segunda incidencia -si la primera")
        linea("llegó a existir, la adopta por su work_id-.")
        return 7

    episodio = desenlace.episodio
    if not ejecutar:
        linea(f"ENSAYO: no se ha aplicado nada. «{work_item.work_id}» sigue en")
        linea(f"«{work_item.estado.value}» y no se ha escrito nada en GitHub.")
        linea("")
        linea("El despachador aceptó el trabajo. Con «--ejecutar» quedaría «active» y se")
        linea(f"crearía la incidencia en {repo} con la etiqueta «{episodio.etiqueta}».")
        linea(f"  Clase:    {work_item.clase.value}")
        linea(f"  {project_perfil_field(perfil)}")
        linea(f"  Objetivo: {work_item.objetivo}")
        return 0

    if desenlace.ya_despachado:
        linea(f"Ya estaba despachado: incidencia #{episodio.numero_incidencia}.")
        return 0
    linea(f"Continúa: «{work_item.work_id}» queda en «active» y despachado.")
    linea(f"  Incidencia #{episodio.numero_incidencia}:")
    linea(f"  https://github.com/{episodio.repo}/issues/{episodio.numero_incidencia}")
    linea(f"  Etiqueta aplicada: {episodio.etiqueta}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
