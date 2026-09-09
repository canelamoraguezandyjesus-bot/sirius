"""El intérprete que convierte la pregunta en una ``Peticion`` propia
(ADR-164, palanca 1 de ADR-148).

POR QUÉ EXISTE
==============

Hasta ADR-164, producción interrogaba al motor por etapas con **una sola
política para toda pregunta**: modo ``M1``, cardinalidad ``EXHAUSTIVA``,
tiempo objetivo «ahora», sin corte de registro y un propósito fijo
(``_peticion_ordinaria``, ``sirius.application.rank_relevant_knowledge``).
El banco de 47 casos, en cambio, lleva su petición POR CASO —modo, permiso,
cardinalidad, límite, tiempo objetivo y corte de registro— y el motor ya
honra esos campos (``sirius.domain.staged_engine_gates``: ``G1`` el
propósito, ``G6``/``G7`` el modo, ``G8`` el tiempo y el corte). ADR-148 midió
el salto de inyectar la petición del caso, sin tocar nada más y sin filtro:
las exactas pasan de 0/47 a 16/47 y el ruido de 487 a 162.

QUÉ INFIERE EL MODELO Y QUÉ NO
==============================

- **El modelo local** (``QueryIntentClassifierPort``) infiere lo que la
  pregunta declara: modo, cardinalidad, límite y tiempo (objetivo y corte de
  registro). Es lo que depende de entender la frase.
- **Las reglas del producto** deciden el **permiso** y el **propósito**. El
  permiso gobierna qué se puede mirar: no puede depender de lo que un modelo
  crea entender de una frase, porque una frase persuasiva ampliaría entonces
  lo que Sirius se autoriza a leer. La regla es la misma que el traductor
  del banco declara (``tests/acceptance/staged_engine_case_translation.py``):
  ``Peticion`` no tiene campo de permiso, y un permiso sin autorizar se
  traduce como **propósito vacío**, que ``G1`` bloquea antes de recuperar.

RESPALDO
========

Sin clasificador, o cuando el clasificador contesta ``None`` («no he podido
decidir»), el intérprete produce **exactamente** la petición uniforme de
antes de ADR-164. Es la razón de que este módulo pueda sustituir a
``_peticion_ordinaria`` sin cambiar el comportamiento de ningún llamador que
no cablee un modelo: el respaldo no es un camino nuevo, es el de siempre.
"""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Final

from sirius.domain.query_intent import IntencionDeConsulta
from sirius.domain.staged_engine_contracts import (
    Ambito,
    Cardinalidad,
    Modo,
    Peticion,
    VentanaTemporal,
)
from sirius.ports.clock import Clock
from sirius.ports.query_intent_classifier import QueryIntentClassifierPort

__all__ = [
    "INTENCION_ORDINARIA",
    "LIMITE_SIN_ATAR",
    "PROPOSITO_RECUPERACION_ORDINARIA",
    "InterpreteDePeticion",
    "PermisoDeRecuperacion",
    "ambito_de_recuperacion",
    "proposito_efectivo",
]

#: Propósito declarado de una recuperación de contexto ordinaria: ``E0``
#: exige uno no vacío (``G1``). Contiene la subcadena ``"contexto"`` a
#: propósito, la misma condición que ``pide_contexto`` exige para la siembra
#: de M20 (ADR-129), porque la única llamada real al caso de uso (hoy
#: ``rank_con_cupo()``, ADR-169) ocurre desde
#: ``ContextBuilder._rank_related_knowledge`` para ensamblar el contexto de
#: un turno — un hecho estructural sobre quién llama, no una adivinanza
#: sobre la consulta. Estaba en ``rank_relevant_knowledge`` hasta ADR-164 y
#: se mueve aquí sin cambiar una letra.
PROPOSITO_RECUPERACION_ORDINARIA: Final = "recuperacion de contexto relevante (B6b)"

#: Límite que "no ata" (misma convención que
#: ``experiments/adr002/round/cases.py``: "los casos que no declaran limite
#: reciben un limite que no ata"): mayor que cualquier canon real de Sirius
#: 0.1 hoy, así que nunca es la causa de que algo se omita.
LIMITE_SIN_ATAR: Final = 100_000


class PermisoDeRecuperacion(StrEnum):
    """Permiso de la operación que pide recuperar, decidido por reglas.

    Los dos valores del banco (``peticion_p2.permiso``). No lo infiere el
    modelo: lo declara quien llama, a partir de qué operación es — en Sirius
    0.1 la única llamada real al caso de uso (hoy ``rank_con_cupo()``,
    ADR-169) es el ensamblado de contexto de un
    turno que el propietario mismo ha iniciado sobre sus propios datos
    locales, y por eso producción declara ``AUTORIZADO``.
    """

    AUTORIZADO = "AUTORIZADO"
    NO_AUTORIZADO = "NO_AUTORIZADO"


#: La intención que reproduce la política uniforme anterior a ADR-164: el
#: respaldo cuando no hay modelo o el modelo no supo decidir.
INTENCION_ORDINARIA: Final = IntencionDeConsulta(
    modo=Modo.M1_ORDINARIO,
    cardinalidad=Cardinalidad.EXHAUSTIVA,
    limite=None,
    tiempo_objetivo=None,
    corte_de_registro=None,
)


def ambito_de_recuperacion(active_project_id: int | None) -> Ambito:
    """El ámbito real de una recuperación, derivado del proyecto activo.

    M16 (SIRIUS-ARQ-0.2 §11.3/§11.5, incidencia #504): con proyecto activo,
    ``Ambito(global_=False, proyectos=(id,))``; sin él, ``Ambito(global_=True,
    proyectos=())``. ``Ambito.proyectos`` exige cadenas
    (``src/sirius/domain/staged_engine_contracts.py:136``, el mismo formato
    con que el motor ya persiste los ids de proyecto,
    ``src/sirius/adapters/persistence/staged_engine_port.py:129-133``), de
    ahí ``str(active_project_id)``.
    """
    if active_project_id is None:
        return Ambito(global_=True, proyectos=())
    return Ambito(global_=False, proyectos=(str(active_project_id),))


def proposito_efectivo(permiso: PermisoDeRecuperacion, proposito_declarado: str) -> str:
    """La regla del permiso, calcada del traductor del banco.

    ``Peticion`` no tiene campo de permiso: lo que ``E0`` comprueba es que el
    propósito esté declarado (``G1``), y un propósito no declarado bloquea
    antes de recuperar. Un permiso sin autorizar se traduce, por tanto, como
    **propósito vacío** —``tests/acceptance/staged_engine_case_translation.py``,
    ``proposito = "" if permiso == PERMISO_SIN_AUTORIZAR else …``—, y no como
    un propósito distinto ni como una excepción.
    """
    if permiso is PermisoDeRecuperacion.NO_AUTORIZADO:
        return ""
    return proposito_declarado


class _RelojDelSistema:
    """El reloj real, el único que este módulo usa fuera de las pruebas."""

    def utc_now(self) -> datetime:
        return datetime.now(UTC)


class InterpreteDePeticion:
    """Convierte una consulta en la ``Peticion`` que el motor recibirá.

    ``intent_classifier`` es opcional: sin él, ``interpretar`` produce la
    misma petición uniforme que ``_peticion_ordinaria`` producía antes de
    ADR-164, de modo que construir el intérprete nunca cambia por sí solo el
    comportamiento de nadie. ``clock`` se inyecta por la razón de siempre
    (SIRIUS-ARQ-0.1 S4): una prueba que dependiera del reloj real mediría la
    máquina, y la medición del banco necesita fijar su propio «ahora»
    (``ahora_declarado`` del fixture) para que el tiempo objetivo sea
    comparable campo a campo.
    """

    def __init__(
        self,
        *,
        intent_classifier: QueryIntentClassifierPort | None = None,
        clock: Clock | None = None,
    ) -> None:
        self._intent_classifier = intent_classifier
        self._clock: Clock = clock if clock is not None else _RelojDelSistema()

    def interpretar(
        self,
        query_text: str,
        operation_id: str,
        *,
        active_project_id: int | None,
        permiso: PermisoDeRecuperacion = PermisoDeRecuperacion.AUTORIZADO,
        proposito: str = PROPOSITO_RECUPERACION_ORDINARIA,
    ) -> Peticion:
        """La ``Peticion`` de esta consulta concreta.

        El modelo decide modo, cardinalidad, límite y tiempo; las reglas
        deciden permiso y propósito; el ámbito sale del proyecto activo
        (M16). Nada más entra: ``objetivos`` se queda en 1 porque la cuota de
        ``EXACTA`` que el banco usa
        (``max(1, len(caso["resultado_esperado"]))``) es **adjudicación** —el
        número de elementos que alguien ya decidió que el caso espera—, y
        producción no la tiene ni puede inventarla.
        """
        intencion = self._intencion(query_text)
        objetivo, duro = _limites(intencion.limite)
        return Peticion(
            operation_id=operation_id,
            consulta=query_text,
            proposito=proposito_efectivo(permiso, proposito),
            modo=intencion.modo,
            ambito=ambito_de_recuperacion(active_project_id),
            ventana=VentanaTemporal(
                tiempo_objetivo=(
                    intencion.tiempo_objetivo
                    if intencion.tiempo_objetivo is not None
                    else _ahora_como_lo_declara_el_corpus(self._clock.utc_now())
                ),
                corte_de_registro=intencion.corte_de_registro,
                # El extremo inicial solo viaja si el final vino con él
                # (ADR-168). Con un intervalo medio ilegible —el modelo
                # contesta "2026-01-10/loquesea" y solo el inicio es una
                # fecha— el final sería el «ahora» del respaldo, y la
                # ventana resultante, `[2026-01-10, ahora]`, sería una que
                # nadie declaró. Sin los dos extremos no hay intervalo.
                tiempo_objetivo_desde=(
                    intencion.tiempo_objetivo_desde
                    if intencion.tiempo_objetivo is not None
                    else None
                ),
            ),
            cardinalidad=intencion.cardinalidad,
            limite_objetivo=objetivo,
            limite_duro=duro,
            admite_no_vigentes=intencion.modo is Modo.M2_HISTORICO,
        )

    def _intencion(self, query_text: str) -> IntencionDeConsulta:
        """Lo que el modelo infirió, o la intención ordinaria si no hay
        modelo o no supo decidir. El puerto nunca lanza (su contrato), así
        que aquí no hay ``try``/``except``: un ``None`` ya ES la respuesta a
        cualquier fallo interno suyo."""
        if self._intent_classifier is None:
            return INTENCION_ORDINARIA
        inferida = self._intent_classifier.classify_intent(query_text)
        return inferida if inferida is not None else INTENCION_ORDINARIA


def _ahora_como_lo_declara_el_corpus(momento: datetime) -> str:
    """El «ahora» del respaldo, escrito con el sufijo ``Z``.

    Misma forma que la del tiempo objetivo interpretado
    (``ollama_query_intent_classifier._tiempo_objetivo``) y que la del corpus
    que puebla ``valid_from``/``valid_to``, porque ``G8`` los compara como
    CADENAS: con ``+00:00`` el veredicto se invertiría en la frontera exacta
    (el ``+`` ordena antes que la ``Z``). No es cosmética, y por eso el
    respaldo se alinea también y no solo la rama interpretada.
    """
    return momento.isoformat().replace("+00:00", "Z")


def _limites(limite: int | None) -> tuple[int, int]:
    """``(objetivo, duro)``. Sin límite declarado, uno que no ata.

    Un límite inferido de la frase entra como **objetivo**, nunca como duro:
    ``G12`` trunca por el límite duro (``truncate_to_hard_limit``), y este
    campo lo mantiene fuera de esa puerta. Lo que ya no puede afirmarse es la
    consecuencia que aquí se daba —que la cifra inferida no descarta nada—:
    ADR-169 reutiliza ``limite_objetivo`` como cupo del filtro de relevancia
    para ``ACOTADA``, así que hoy sí descarta, no en ``G12`` sino en el filtro,
    con RF-25/RF-26 y la protección de los candidatos sin categoría como único
    recurso (una candidata ordinaria con categoría por debajo del cupo se
    pierde). Esa reversión la ordena la incidencia #579 y está registrada en
    ADR-169. El banco distingue ``DURO`` de ``OBJETIVO`` porque es
    adjudicación declarada, no inferencia; producción no la tiene.
    Un límite no positivo se descarta como si no se hubiera declarado: una
    cuota de 0 vaciaría la respuesta entera.
    """
    if limite is None or limite <= 0:
        return LIMITE_SIN_ATAR, LIMITE_SIN_ATAR
    return limite, LIMITE_SIN_ATAR
