"""El motor escalonado ``E0-E5``: la pieza que hace comparables a los candidatos.

El motor **posee el bucle**. Un candidato aporta senales cuando se le pregunta
por una etapa, pero no decide cuando se le pregunta, ni si se continua, ni con
que puertas se filtra lo que aporto, ni cuando se para. Esa asimetria es
deliberada: si el candidato controlase el orden, «saltar a recuperacion
amplia» —lo que ``B04-RF-14`` prohibe— seria una decision suya, y comparar
alternativas mediria quien esquiva mejor el contrato.

Reglas que el motor hace cumplir por construccion:

- **Sin saltos.** Las etapas se recorren en el orden de ``ORDEN_DE_ETAPAS``.
- **Solo por insuficiencia.** Se avanza si la etapa anterior fue insuficiente
  —cardinalidad no satisfecha o criticos pendientes— **y** el siguiente
  espacio esta autorizado (``B04-RF-16``, ``B04-Q10``).
- **Cada transicion registra su causa.** Una transicion sin causa es un fallo.
- **Puertas antes que ranking.** ``G1-G10`` filtran lo que cada etapa aporta;
  ``G11`` valida antes de ordenar; ``G12`` protege criticidad y limite.
- **Una parada, siempre.** Ninguna ejecucion termina sin adjudicar ``S1-S7``.
- **Determinismo.** Mismo puerto y misma peticion producen el mismo orden: el
  desempate es estable y explicito, nunca el del diccionario.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from typing import Final

from experiments.adr002.candidates.common import gates, grouping, stops
from experiments.adr002.candidates.common.contracts import (
    ESTADO_EXTERNO_SIN_RESULTADO,
    ETAPAS_DE_EXPANSION,
    ORDEN_DE_CRITICIDAD,
    PLANO_COMUN_VACIO,
    Candidata,
    Cardinalidad,
    Cardinalidades,
    ContextoDeEtapa,
    Criticidad,
    CriticidadAplicada,
    Etapa,
    GrupoDeEquivalentes,
    Peticion,
    PlanoComun,
    PuertoDeRecuperacion,
    Resultado,
    SenalesDeCandidato,
    Suficiencia,
)
from experiments.adr002.candidates.common.trace import PasoDeEtapa, Traza, explicar, traza_nueva


class RecuperacionInvalidaError(RuntimeError):
    """El motor no puede continuar sin violar el contrato."""


@dataclass(frozen=True, slots=True)
class Recuperacion:
    """Lo que el motor entrega: resultados ordenados, estado y plan."""

    resultados: tuple[Resultado, ...]
    suficiencia: Suficiencia
    estado_externo: str
    parada: stops.Parada
    traza: Traza
    conflictos: tuple[str, ...]
    grupos: tuple[GrupoDeEquivalentes, ...] = ()
    cardinalidades: Cardinalidades = field(default_factory=lambda: Cardinalidades(0, 0))
    #: Miembros elegibles que el limite duro dejo fuera. Se declaran; nunca se
    #: omiten en silencio y nunca amplian el limite.
    omitidos_por_limite: tuple[str, ...] = ()

    @property
    def ids(self) -> tuple[str, ...]:
        return tuple(r.item.id for r in self.resultados)

    @property
    def handoff_a_b05(self) -> dict[str, CriticidadAplicada]:
        """Criticidad aplicada de cada resultado, **integra**, para ``B05``.

        Los cuatro campos viajan tal como el plano comun los congelo. Es el
        unico consumidor externo autorizado; ningun candidato la ve.
        """
        return {r.item.id: r.criticidad for r in self.resultados if r.criticidad is not None}


#: Razon de orden, en el mismo orden que la clave. La explicacion la cita en
#: vez de inventar una frase distinta de la comparacion realmente aplicada.
EJES_DE_ORDEN: Final[tuple[str, ...]] = (
    "criticidad aplicada",
    "autoridad de la etapa de origen",
    "clave de sujeto",
    "identidad estable",
)


def _clave_de_orden(
    candidata: Candidata, criticidad_de: Callable[[str], Criticidad]
) -> tuple[int, int, str, str]:
    """Desempate **estable y registrado** (``B04`` M-05, ``RF-22``).

    Por criticidad aplicada —la del plano comun, no un campo del item—, luego
    por etapa de origen —la autoridad decrece de ``E1`` a ``E4``—, luego por
    sujeto e identidad estable. Nunca por el orden de llegada, que dependeria
    del motor de base de datos y no seria reproducible.

    La comparacion es por **posicion en el orden de criticidad**, no por
    literal de cadena: comparar cadenas hacia que un nivel intermedio nuevo
    quedase silenciosamente del lado ordinario.
    """
    nivel = ORDEN_DE_CRITICIDAD.index(criticidad_de(candidata.item.id))
    autoridad = list(ETAPAS_DE_EXPANSION).index(candidata.etapa)
    return (-nivel, autoridad, candidata.item.subject_key or "", candidata.item.id)


def _suficiente(contadas: int, peticion: Peticion) -> bool:
    """Condicion de insuficiencia entre etapas, explicita (``B04-RF-16``).

    ``contadas`` es la cardinalidad **semantica**: un grupo de equivalentes
    cuenta una vez. ``EXHAUSTIVA`` no se satisface por cuota; agota o para por
    ``S2-S7``.
    """
    if peticion.cardinalidad is Cardinalidad.EXHAUSTIVA:
        return False
    if peticion.cardinalidad is Cardinalidad.EXACTA:
        return contadas >= peticion.objetivos
    return contadas >= peticion.limite_objetivo


def recuperar(
    peticion: Peticion,
    puerto: PuertoDeRecuperacion,
    candidato: SenalesDeCandidato,
    plano: PlanoComun = PLANO_COMUN_VACIO,
) -> Recuperacion:
    """Recorre ``E0-E5`` conforme a B04. **No mide**: recupera.

    El candidato solo interviene en ``candidatas()`` y ``leer()``. Todo lo
    demas —orden, puertas, insuficiencia, deduplicacion, agrupacion, limite,
    parada, explicacion y traza— lo decide este motor, igual para todos.

    ``plano`` es el canal lateral de la capa comun: ``property_key`` y
    criticidad aplicada. **No se le pasa al candidato en ningun momento**, ni
    dentro de ``ContextoDeEtapa`` ni de ninguna otra estructura, de modo que un
    candidato no tiene por donde alcanzarlo. Su valor por defecto no determina
    nada: sin canal lateral no se agrupa y nada es critico.
    """
    traza = traza_nueva(peticion, candidato.identificador)

    def criticidad_de(identidad: str) -> Criticidad:
        aplicada = plano.criticidad_aplicada(identidad)
        return Criticidad.ORDINARIA if aplicada is None else aplicada.nivel

    # ---- E0: preparacion segura. No genera candidatos todavia. -----------
    if not peticion.proposito.strip():
        bloqueo_e0 = stops.parada_por_ambiguedad(
            "proposito no declarado: no se ejecuta recuperacion"
        )
        traza.registrar_etapa(PasoDeEtapa(Etapa.E0, "peticion recibida", 0, 0, False))
        traza.parada = (bloqueo_e0.identificador, bloqueo_e0.fundamento)
        traza.suficiencia = Suficiencia.NO_REPORTABLE.value
        return Recuperacion(
            (), Suficiencia.NO_REPORTABLE, ESTADO_EXTERNO_SIN_RESULTADO, bloqueo_e0, traza, ()
        )
    traza.registrar_etapa(
        PasoDeEtapa(Etapa.E0, "peticion ejecutable: G1-G10 parametrizadas", 0, 0, False)
    )

    admitidas: list[Candidata] = []
    ya: set[str] = set()
    parada: stops.Parada | None = None
    causa = "E0 no genera candidatos: la expansion empieza por la etapa exacta"

    for etapa in ETAPAS_DE_EXPANSION:
        # --- S2: el modo debe autorizar el espacio ANTES de consultarlo.
        if (bloqueo := stops.parada_por_modo(etapa, peticion)) is not None:
            parada = bloqueo
            break

        # Las semillas son lo admitido hasta aqui. Entregarlas permite a una
        # etapa tardia expandir DESDE lo recuperado con consultas dirigidas,
        # en vez de enumerar un espacio entero y filtrar despues.
        contexto = ContextoDeEtapa(peticion, puerto, etapa, frozenset(ya), tuple(admitidas))
        aportadas = list(candidato.candidatas(contexto))

        filtrado = gates.aplicar_previas(aportadas, peticion)
        traza.registrar_descartes(filtrado.descartes)
        nuevas = [c for c in filtrado.admitidas if c.item.id not in ya]
        admitidas.extend(nuevas)
        ya.update(c.item.id for c in nuevas)

        semantica = _cardinalidad_semantica(admitidas, plano)
        suficiente = _suficiente(semantica, peticion)
        traza.registrar_etapa(PasoDeEtapa(etapa, causa, len(aportadas), len(nuevas), suficiente))

        # --- S1: suficiencia por cardinalidad, si la cardinalidad la admite.
        if (
            fin := stops.evaluar_suficiencia(
                admitidas,
                peticion,
                criticidad_de=criticidad_de,
                cardinalidad_semantica=semantica,
            )
        ) is not None:
            parada = fin
            break
        # --- S4: limite duro alcanzado. Se cuenta por unidad DOCUMENTAL: el
        # limite se aplica sobre resultados entregables, no sobre necesidades.
        if (tope := stops.parada_por_limite_duro(admitidas, peticion)) is not None:
            parada = tope
            break
        causa = f"{etapa.value} insuficiente: {len(admitidas)} elegibles tras puertas"

    # --- G11 antes de ordenar; el conflicto se conserva, no se fusiona.
    semantico = gates.aplicar_g11(admitidas, peticion)
    traza.registrar_descartes(semantico.descartes)
    conflictos = gates.conflictos_de_polaridad(semantico.admitidas)
    traza.conflictos = conflictos

    # ---- E5: deduplicar, agrupar, ordenar, G12 sobre TODOS los miembros. ---
    #
    # El orden importa y no es intercambiable: la deduplicacion por identidad
    # va primero porque una identidad repetida no es un grupo; la agrupacion
    # despues, porque necesita cada identidad una sola vez; y ``G12`` al final
    # pero **sobre la lista completa de miembros**, no sobre representantes.
    unicas, senales_fusionadas = grouping.deduplicar_por_identidad(semantico.admitidas)
    for identidad, senales in sorted(senales_fusionadas.items()):
        traza.registrar_deduplicacion(identidad, senales)

    agrupacion = grouping.agrupar_equivalentes(unicas, plano.property_key)
    for grupo in agrupacion.grupos:
        traza.registrar_agrupacion(
            grupo.representante, grupo.miembros, grupo.razon_del_representante, grupo.ejes
        )

    # Invariante de §7.9: nada desaparece dentro de un grupo.
    if set(agrupacion.miembros_totales) != {c.item.id for c in unicas}:
        msg = "la agrupacion perdio elegibles: los miembros no cubren lo admitido"
        raise RecuperacionInvalidaError(msg)

    ordenadas = sorted(unicas, key=lambda c: _clave_de_orden(c, criticidad_de))
    grupo_por_item = {m: g for g in agrupacion.grupos for m in g.miembros}
    g12 = gates.aplicar_g12(ordenadas, peticion, criticidad_de, lambda i: i in grupo_por_item)
    traza.desbordamiento = g12.desbordamiento_declarado
    traza.desbordamiento_critico = g12.desbordamiento_critico
    traza.criticos_omitidos = g12.criticos_omitidos
    traza.miembros_omitidos = g12.miembros_omitidos

    entregados = {c.item.id for c in g12.dentro_del_limite}
    grupos_truncados = tuple(
        g.identificador for g in agrupacion.grupos if not set(g.miembros) <= entregados
    )
    traza.grupos_truncados = grupos_truncados

    # --- Precedencia de §7.7 regla 9: S1 no se adjudica si el limite parte un
    # grupo que computa en la cuota, ni si quedan criticos pendientes.
    if grupos_truncados and (parada is None or parada.identificador == "S1"):
        omitidos = sum(1 for g in agrupacion.grupos for m in g.miembros if m not in entregados)
        parada = stops.parada_por_grupo_truncado(grupos_truncados[0], omitidos)
    if parada is None:
        if (riesgo := stops.parada_por_riesgo_semantico(conflictos)) is not None:
            parada = riesgo
        else:
            parada = stops.parada_por_agotamiento(peticion)

    resultados = tuple(
        Resultado(
            item=candidata.item,
            etapa_de_origen=candidata.etapa,
            lectura=candidata.lectura,
            explicacion=explicar(
                candidata,
                peticion,
                orden,
                criticidad=plano.criticidad_aplicada(candidata.item.id),
                grupo=grupo_por_item.get(candidata.item.id),
            ),
            posicion=orden,
            grupo=grupo_por_item.get(candidata.item.id),
            criticidad=plano.criticidad_aplicada(candidata.item.id),
        )
        for orden, candidata in enumerate(g12.dentro_del_limite, start=1)
    )

    cardinalidades = Cardinalidades(
        semantica=len(
            {grupo_por_item[r.item.id].identificador for r in resultados if r.grupo}
            | {r.item.id for r in resultados if not r.grupo}
        ),
        documental=len(resultados),
    )
    suficiencia = _adjudicar_suficiencia(resultados, peticion, parada, cardinalidades, g12)
    traza.registrar_etapa(
        PasoDeEtapa(Etapa.E5, "adjudicacion y salida", len(unicas), len(resultados), True)
    )
    traza.parada = (parada.identificador, parada.fundamento)
    traza.suficiencia = suficiencia.value
    traza.cardinalidad_semantica = cardinalidades.semantica
    traza.cardinalidad_documental = cardinalidades.documental

    return Recuperacion(
        resultados=resultados,
        suficiencia=suficiencia,
        estado_externo=_estado_externo(suficiencia),
        parada=parada,
        traza=traza,
        conflictos=conflictos,
        grupos=agrupacion.grupos,
        cardinalidades=cardinalidades,
        omitidos_por_limite=tuple(sorted({c.item.id for c in ordenadas} - entregados)),
    )


def _cardinalidad_semantica(admitidas: Sequence[Candidata], plano: PlanoComun) -> int:
    """Necesidades distintas: los equivalentes cuentan **una vez**.

    Contarlos por separado permitiria satisfacer una cuota que pide necesidades
    semanticas distintas repitiendo equivalentes, que es lo que la regla 7 de
    ``§7.7`` prohibe expresamente.
    """
    unicas, _ = grouping.deduplicar_por_identidad(admitidas)
    agrupacion = grouping.agrupar_equivalentes(unicas, plano.property_key)
    return len(agrupacion.grupos) + len(agrupacion.sueltos)


def _adjudicar_suficiencia(
    resultados: Sequence[Resultado],
    peticion: Peticion,
    parada: stops.Parada,
    cardinalidades: Cardinalidades,
    g12: gates.ResultadoG12,
) -> Suficiencia:
    """``B04-RF-25``: estado interno detallado por cardinalidad y taxonomia.

    ``PARCIAL`` gana a ``COMPLETA`` en dos casos que antes se perdian: cuando
    el limite dejo fuera miembros de un grupo y cuando desbordo un critico. En
    los dos, la necesidad no quedo cubierta aunque la cuota cuadrase.
    """
    if not resultados:
        return Suficiencia.NINGUNA_EN_AMBITO
    if g12.desbordamiento_critico or g12.miembros_omitidos:
        return Suficiencia.PARCIAL
    if todo_atribuido := all(r.item.clase_de_evidencia.value == "ATRIBUIDA" for r in resultados):
        # Solo evidencia atribuida: no es ausencia, pero tampoco es canon.
        return Suficiencia.SOLO_HISTORICO if todo_atribuido else Suficiencia.PARCIAL
    if parada.identificador == "S1":
        return Suficiencia.COMPLETA
    if (
        peticion.cardinalidad is Cardinalidad.EXACTA
        and cardinalidades.semantica >= peticion.objetivos
    ):
        return Suficiencia.COMPLETA
    return Suficiencia.PARCIAL


def _estado_externo(suficiencia: Suficiencia) -> str:
    """``RF-26``: ausencia y no-reportable comparten redaccion externa.

    Distinguirlas fuera filtraria existencia, que es exactamente el canal
    lateral que la puerta de indistinguibilidad persigue.
    """
    if suficiencia in (Suficiencia.NINGUNA_EN_AMBITO, Suficiencia.NO_REPORTABLE):
        return ESTADO_EXTERNO_SIN_RESULTADO
    return suficiencia.value


__all__ = ["Recuperacion", "RecuperacionInvalidaError", "recuperar"]
