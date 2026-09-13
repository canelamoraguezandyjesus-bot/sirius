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
import shlex
import sys
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from pathlib import Path

from sirius_engine.adapters.durable.dispatch_journal import DurableDispatchJournal
from sirius_engine.adapters.durable.store import DurableWorkEngineStore
from sirius_engine.adapters.github_cli_writer import GitHubCliWriter, MissingCredentialError
from sirius_engine.adapters.memory_dispatch_journal import InMemoryDispatchJournal
from sirius_engine.adapters.memory_store import InMemoryWorkEngineStore
from sirius_engine.carriles_retirados import carril_retirado
from sirius_engine.cli import REPO, resolver_diario
from sirius_engine.dispatcher import TABLA_ACTIVACION, dispatch_work_item
from sirius_engine.domain.authority import autoridad_de_clase
from sirius_engine.domain.dispatch import MARCADOR_ORDEN_PROPIETARIO
from sirius_engine.domain.work_item import WorkItemClass
from sirius_engine.gate import ResultadoPuerta, decidir
from sirius_engine.intent_interpreter import (
    alcance_que_el_motor_no_puede_escribir,
    interpretar_intencion_v0,
)
from sirius_engine.issue_body_projection import generar_cuerpo_incidencia
from sirius_engine.ports.dispatch_journal import DispatchJournal
from sirius_engine.ports.github_writer import GitHubWriterPort, IncidenciaCreada
from sirius_engine.ports.store import WorkEngineStore
from sirius_engine.profile_field import ProfileRef
from sirius_engine.work_intake import ResultadoIntake, aplicar_decision

COMANDO = "sirius-despachar"

#: Perfil por clase de trabajo (mismo criterio que ``TABLA_ACTIVACION`` en
#: :mod:`sirius_engine.dispatcher` selecciona la etiqueta según §12.4): la
#: clase que se despacha decide qué perfil declara el cuerpo, no un único
#: valor fijo que ignoraría cuál guardián real va a atender la incidencia
#: (hallazgo CODEX-001, incidencia #256). Solo cubre las tres clases
#: despachables -``programacion``, ``auditoria`` y ``documentacion``
#: (ADR-088, incidencia #336)-: para cualquier otra, ``dispatch_work_item``
#: rechaza el despacho antes de que el perfil llegue a proyectarse en ningún
#: cuerpo real. El perfil ``documentalista`` es el que los workflows
#: (ADR-088) leen del campo ``Perfil:`` para elegir el prompt documental.
TABLA_PERFILES: dict[WorkItemClass, ProfileRef] = {
    WorkItemClass.PROGRAMACION: ProfileRef(ref="implementer", version=2),
    WorkItemClass.AUDITORIA: ProfileRef(ref="auditor", version=1),
    WorkItemClass.DOCUMENTACION: ProfileRef(ref="documentalista", version=2),
    # ADR-099 (B1). El perfil es la llave del reparto de ejecutores: el workflow
    # del implementador excluye `investigador` en su puerta y lo atiende
    # `investigar-orden.yml`, que corre el investigador medido de ADR-098.
    WorkItemClass.INVESTIGACION: ProfileRef(ref="investigador", version=2),
}

#: Perfil de repliegue cuando la clase no está en :data:`TABLA_PERFILES`. No
#: debería observarse nunca en un cuerpo real: ``dispatch_work_item`` ya
#: rechazó esa clase antes de usar el perfil para nada.
PERFIL_POR_DEFECTO = TABLA_PERFILES[WorkItemClass.PROGRAMACION]

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

    def buscar_incidencia_por_work_id(self, *, repo: str, work_id: str) -> IncidenciaCreada | None:
        # Un ensayo no tiene intención pendiente que adoptar: nunca se llama,
        # y si algún día se llamara, «no hay ninguna» es la única respuesta
        # que no inventa estado.
        return None


def _ruta_copiable(ruta: Path) -> str:
    """``ruta`` tal y como hay que teclearla en una consola, entrecomillada si hace falta.

    Sin esto, una ruta con espacios -«/tmp/Sirius motor/diario.jsonl»- se parte
    al copiar la instrucción: el intérprete da «/tmp/Sirius» a `--diario` y el
    resto al `mensaje` posicional, y `sirius-motor` abre otro diario sin
    protestar. `shlex.quote` deja la ruta intacta cuando no lo necesita, que es
    el caso corriente.
    """
    return shlex.quote(str(ruta))


def _diario_de_despacho(diario_del_motor: Path) -> Path:
    """El diario del despachador, hermano del del motor y en su mismo directorio.

    Diario propio y no el del motor por el mismo criterio que separó el del
    supervisor (ADR-061) y el del despachador (ADR-064): el diario de eventos
    del ``WorkEngineStore`` modela transiciones tipadas de ``WorkItem``/``Run``
    y no tiene sitio para «qué orden» ni «qué incidencia» nació de una
    activación.
    """
    return diario_del_motor.with_name(f"{diario_del_motor.stem}-despacho.jsonl")


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

    # H-17 (incidencia #308): el despachador solo atiende las clases de
    # TABLA_ACTIVACION -«programacion», «auditoria» y «documentacion»
    # (ADR-088, incidencia #336), la tabla cerrada del contrato §12.4-. Antes
    # esta comprobación llegaba tarde: aplicar_decision
    # ya había creado y activado el WorkItem, y dispatch_work_item levantaba
    # ClaseNoDespachableError SIN capturar, así que el proceso terminaba con
    # una traza y el WorkItem quedaba ACTIVE en el diario durable, huérfano
    # -ningún despachador atiende esa clase-. Repetir la orden no lo
    # idempotía: el work_id nace del instante, así que cada intento escribía
    # OTRO WorkItem huérfano y las entradas se acumulaban sin límite en un
    # diario append-only. Se comprueba aquí, contra la clase que YA se conoce
    # sin haber tocado ningún almacén, para que el rechazo ocurra antes de
    # crear nada -no después, cerrando lo ya creado.
    if (
        decision.resultado is ResultadoPuerta.CREAR_Y_ACTIVAR
        and decision.datos_trabajo is not None
        and decision.datos_trabajo.clase not in TABLA_ACTIVACION
    ):
        clase = decision.datos_trabajo.clase.value
        linea("No he creado nada.")
        linea(f"  Motivo: el despachador no gestiona la clase «{clase}»")
        linea("")
        linea("Solo las clases «programacion», «auditoria» y «documentacion» tienen")
        linea("despachador (contrato §12.4). Crear el WorkItem para una orden de una clase")
        linea("que nunca se va a despachar dejaría trabajo ACTIVE huérfano en el diario,")
        linea("así que el rechazo ocurre antes de escribir nada.")
        return 5

    # ADR-161/ADR-163: el carril de esa clase está retirado. Se rechaza en el
    # mismo sitio y por el mismo motivo que la comprobación de arriba -antes de
    # crear nada-, pero con mensaje propio: «esta clase nunca tuvo despachador»
    # y «lo tuvo y se retiró» son dos cosas distintas para quien lee, y el
    # segundo caso tiene que decir a dónde va ahora ese trabajo.
    if decision.resultado is ResultadoPuerta.CREAR_Y_ACTIVAR and decision.datos_trabajo is not None:
        retirado = carril_retirado(decision.datos_trabajo.clase)
        if retirado is not None:
            linea("No he creado nada.")
            linea("")
            for parrafo in retirado.explicacion().splitlines():
                linea(f"  {parrafo}")
            return 6

    # Un ENSAYO no persiste nada. Si usara el almacén durable dejaría un
    # WorkItem ACTIVE que nadie va a despachar: exactamente el estado
    # inconsistente -trabajo activo sin nada que lo atienda- que el resto del
    # motor se cuida de no producir. El ensayo enseña qué pasaría; no lo hace
    # a medias.
    # El diario del despachador es DURABLE al ejecutar de verdad. Con el de
    # memoria, la garantía «una sola activación por WorkItem» (C2-P3) no cruza
    # procesos: cada invocación nacía sin memoria de lo ya despachado, así que
    # repetir la orden creaba una segunda incidencia -y de una incidencia
    # cuelga un ciclo entero-. Era el hueco H-B de la incidencia #250: H-11
    # construyó el adaptador durable y este camino, el único de producción que
    # despacha, seguía sin usarlo.
    store: WorkEngineStore
    journal: DispatchJournal
    #: La ruta del diario donde de verdad queda el trabajo, o ``None`` en
    #: ensayo, donde no queda en ninguna. El mensaje de la parada la necesita
    #: para no prometer un sitio que no existe ni una ruta que no es la suya.
    diario_efectivo: Path | None = None
    if args.ejecutar:
        diario_efectivo = resolver_diario(argumento=args.diario, entorno=entorno)
        store = DurableWorkEngineStore(diario_efectivo)
        journal = DurableDispatchJournal(_diario_de_despacho(diario_efectivo))
    else:
        store = InMemoryWorkEngineStore()
        journal = InMemoryDispatchJournal()
    work_id = _work_id(ahora)

    # El despachador se niega a activar un WorkItem cuya orden no se pueda
    # encontrar después (§12.1), y esta es la única capa que sabe de dónde vino.
    # Sin --orden-ref la referencia es el propio diario: ahí queda el texto
    # íntegro de la orden bajo este work_id, que es una respuesta real a "¿quién
    # pidió esto?" -no un relleno para pasar la guarda-.
    referencia_orden = args.orden_ref or f"{_ORIGEN_CLI}{work_id}"

    # Repetir la misma orden es idempotente, no un error. El `work_id` se deriva
    # del instante de la orden, así que dos invocaciones seguidas comparten uno:
    # sin esto, `create_work_item` levantaba `DuplicateIdError` y la persona veía
    # una traza en vez de «ya estaba despachado». El trabajo ya existe; se
    # reutiliza y se deja que el despachador consulte su diario, que es quien
    # sabe si ya hubo activación.
    ya_existente = store.get_work_item(work_id)
    if ya_existente is not None:
        resultado = ResultadoIntake(
            work_item=ya_existente, autoridad=autoridad_de_clase(ya_existente.clase), escalada=None
        )
    else:
        resultado = aplicar_decision(
            decision,
            store=store,
            work_id=work_id,
            peticion_original=args.orden,
            now=ahora,
            evidencia=(f"{MARCADOR_ORDEN_PROPIETARIO}{referencia_orden}",),
        )

    # Una parada deja el trabajo anotado en `needs_decision` y SIN incidencia
    # detrás. Eso no es un residuo: es su situación real, y el diario es
    # append-only (ADR-026), así que no se borra ni se cancela por iniciativa
    # del comando -cancelar es una decisión del propietario, que es justo lo
    # que aquí falta-. Lo que sí faltaba es DECIRLO: el mensaje daba el
    # work_id y la causa y callaba dónde quedaba el trabajo y cómo volver a
    # él, así que quedaba huérfano por invisible, no por estado (ADR-184).
    #
    # Pero decirlo solo vale si es verdad, y esta rama se alcanza también en
    # ENSAYO, que es el modo POR DEFECTO: allí el almacén es el de memoria y no
    # se escribe nada, así que el texto durable prometería un sitio vacío -y el
    # aviso de ensayo queda más abajo, detrás de este `return`, o sea que quien
    # para en ensayo ni siquiera lo leía-. Cada modo dice lo suyo. Y cuando el
    # trabajo SÍ queda anotado, la instrucción de recuperación lleva la ruta
    # efectiva del diario: `sirius-motor` sin argumentos resuelve el suyo
    # (`resolver_diario`), que no tiene por qué ser este.
    if decision.resultado is ResultadoPuerta.CREAR_Y_ESCALAR:
        #: El prefijo que la orden pide tocar y el motor no puede escribir, o
        #: ``None``. Se pregunta aparte de la causa a propósito: la quinta causa
        #: comparte `permisos_o_credenciales_sensibles` con la tercera, que es
        #: léxica y no sabe nada de rutas, así que la causa sola no distingue
        #: cuál de las dos paró (ADR-188).
        prefijo_vetado = alcance_que_el_motor_no_puede_escribir(args.orden)
        linea("He creado el trabajo, pero NO lo he despachado: necesita tu decisión.")
        linea(f"  Trabajo: {work_id}")
        if resultado.escalada is not None:
            linea(f"  Causa:   {resultado.escalada.causa.value}")
        linea("")
        # ADR-188, la QUINTA causa. Esta parada tiene un motivo que ninguna de
        # las otras cuatro tiene -no es la orden lo que es peligroso, es que el
        # motor no llega a donde la orden apunta- y una salida concreta que
        # ADR-002 ya prescribió: hacerlo en sesión interactiva. Decirlo aquí no
        # es cortesía: sin esto, la parada dice «permisos_o_credenciales_
        # sensibles» y quien la lee no tiene forma de saber que el trabajo es
        # perfectamente legítimo y que solo cambia de sitio.
        if prefijo_vetado is not None:
            linea(f"El alcance declarado cae bajo «{prefijo_vetado}», y ahí el motor no puede")
            linea("escribir: ADR-002 decidió NO darle ese alcance a su credencial, así que")
            linea("GitHub rechaza el push. No es una precaución teórica: la incidencia #607")
            linea("se despachó al ciclo automático, el encargo hizo el trabajo entero -código,")
            linea("pruebas, ADR y validaciones en verde- y lo perdió al empujar, porque el")
            linea("commit vivía solo en el runner. Por eso la parada ocurre AQUÍ, antes de")
            linea("crear la incidencia, y no después.")
            linea("")
            linea("ADR-002 prescribe hacer este trabajo en sesión interactiva, donde el")
            linea("propietario tiene el alcance que al motor le falta. La orden, lista para")
            linea("copiar tal cual:")
            linea("")
            for parrafo in args.orden.splitlines() or [""]:
                linea(f"    {parrafo}")
            linea("")
            linea("Y si de verdad NO tocas esa carpeta -la orden solo la nombra para")
            linea("excluirla-, dilo con un negador delante y vuelve a despachar: «no toques")
            linea(f"{prefijo_vetado}**» se despacha como cualquier otra orden (ADR-184).")
            linea("")
        if diario_efectivo is None:
            linea("ENSAYO: no se ha escrito nada. El trabajo NO queda anotado en el")
            linea("diario -este ensayo usa un almacén en memoria- y muere con este")
            linea("proceso: no hay nada que listar ni a lo que volver.")
            linea("Repite la orden con «--ejecutar» para que quede anotado en estado")
            linea("«needs_decision» y puedas decidir sobre él más tarde.")
        else:
            linea("Queda anotado en el diario en estado «needs_decision», sin incidencia")
            linea("detrás. No se borra ni se cancela solo: el diario es append-only y")
            linea("cancelarlo es tu decisión, no la de este comando.")
            linea("Para verlo junto a todo lo demás que espera decisión, abre la sesión")
            linea(
                f"«sirius-motor --diario {_ruta_copiable(diario_efectivo)}» y teclea «/trabajos»."
            )
        return 3

    assert resultado.work_item is not None
    work_item = resultado.work_item
    perfil = TABLA_PERFILES.get(work_item.clase, PERFIL_POR_DEFECTO)

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
        journal=journal,
        repo=args.repo,
        profile_ref=perfil,
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
                profile_ref=perfil,
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
