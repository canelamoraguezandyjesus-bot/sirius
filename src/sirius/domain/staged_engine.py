"""El motor escalonado ``E0-E5``: la pieza que hace comparables a los
candidatos. Portado desde
``experiments/adr002/candidates/common/engine.py`` (rama
``evidence/adr001-spikes``, PR #117), incidencia #457/ADR-109.

ADR-109 diagnosticó que el porte del tratamiento léxico (#455/#456, 1/47 ->
10/47) cerraba la brecha de cobertura pero no la de precisión: la política
de ``sirius.domain.relevance.rank_relevant_knowledge`` ("cualquier acierto
FTS5 es relevante") no tiene ningún mecanismo de descarte. Ese mecanismo
vive aquí: una fuente de candidatas aporta señales cuando se le pregunta por
una etapa, pero no decide cuándo se le pregunta, ni si se continúa, ni con
qué puertas se filtra lo que aportó, ni cuándo se para — esa asimetría es
la que permite comparar alternativas midiendo quién recupera mejor, no quién
esquiva mejor el contrato.

Reglas que el motor hace cumplir por construcción:

- **Sin saltos.** Las etapas se recorren en el orden de ``ORDEN_DE_ETAPAS``.
- **Solo por insuficiencia.** Se avanza si la etapa anterior fue
  insuficiente y el siguiente espacio está autorizado.
- **Cada transición registra su causa.**
- **Puertas antes que ranking.** ``G1-G10`` filtran lo que cada etapa
  aporta; ``G11`` valida antes de ordenar; ``G12`` protege criticidad y
  límite.
- **Ningún crítico recuperado desaparece en silencio.**
- **Una parada, siempre.**
- **Determinismo.** Mismo puerto y misma petición producen el mismo orden.

Wiring de producto (D7 punto 6): ``sirius.application.rank_relevant_knowledge.
RankRelevantKnowledgeUseCase`` invoca ``recuperar`` solo cuando
``category_matching_enabled`` está activo — la misma puerta cerrada por
defecto que ya gobierna la categoría (M9). Con la puerta cerrada, este
módulo no se ejecuta nunca y el comportamiento del producto es idéntico al
de hoy.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from typing import Final

from sirius.domain import staged_engine_gates as gates
from sirius.domain import staged_engine_grouping as grouping
from sirius.domain import staged_engine_stops as stops
from sirius.domain.staged_engine_contracts import (
    ESTADO_EXTERNO_SIN_RESULTADO,
    ETAPAS_DE_EXPANSION,
    ORDEN_DE_CRITICIDAD,
    PLANO_COMUN_VACIO,
    Candidata,
    Cardinalidad,
    Cardinalidades,
    ContextoDeEtapa,
    Criticidad,
    Etapa,
    Explicacion,
    GrupoDeEquivalentes,
    Peticion,
    PlanoComun,
    PuertoDeRecuperacion,
    Resultado,
    SenalesDeCandidato,
    Suficiencia,
)
from sirius.domain.staged_engine_trace import PasoDeEtapa, Traza, explicar, traza_nueva

__all__ = ["Recuperacion", "RecuperacionInvalidaError", "recuperar"]


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
    #: Miembros elegibles que el límite duro dejó fuera. Se declaran; nunca
    #: se omiten en silencio y nunca amplían el límite.
    omitidos_por_limite: tuple[str, ...] = ()

    @property
    def ids(self) -> tuple[str, ...]:
        return tuple(r.item.id for r in self.resultados)


#: Razón de orden de ``_clave_de_orden``, en el mismo orden que la clave.
#: El representante no es uno de estos ejes (CODEX-002, incidencia #457,
#: tercera ronda): ``EJES_DE_ORDEN_DECLARADOS``/``PROMOCION_DE_
#: REPRESENTANTE_DECLARADA`` en ``staged_engine_trace.py`` documentan el
#: mismo orden en dos pasos para la traza pública.
EJES_DE_ORDEN: Final[tuple[str, ...]] = (
    "criticidad aplicada",
    "autoridad de la etapa de origen",
    "clave de sujeto",
    "identidad estable",
)


def _clave_de_orden(
    candidata: Candidata,
    criticidad_de: Callable[[str], Criticidad],
) -> tuple[int, int, str, str]:
    """Desempate estable y registrado.

    Por criticidad aplicada, luego por etapa de origen —la autoridad decrece
    de ``E1`` a ``E4``—, luego por sujeto e identidad estable. Nunca por el
    orden de llegada, que dependería del motor de base de datos.

    No compara si el elegible es representante de un grupo de equivalentes:
    esa prioridad la aplica ``_con_representante_al_frente`` aparte, después
    de este ordenamiento, precisamente para que nunca alcance a candidatos
    ajenos al grupo (CODEX-002, incidencia #457) — si estuviera aquí, un
    representante o suelto de cualquier grupo se antepondría a todo miembro
    no representante de cualquier otro grupo, no solo al suyo.
    """
    nivel = ORDEN_DE_CRITICIDAD.index(criticidad_de(candidata.item.id))
    autoridad = list(ETAPAS_DE_EXPANSION).index(candidata.etapa)
    return (
        -nivel,
        autoridad,
        candidata.item.subject_key or "",
        candidata.item.id,
    )


def _con_representante_al_frente(
    ordenadas: Sequence[Candidata],
    criticidad_de: Callable[[str], Criticidad],
    representante_de: Callable[[str], str | None],
) -> tuple[tuple[Candidata, ...], frozenset[str], frozenset[str]]:
    """``GrupoDeEquivalentes`` exige que "el representante encabeza": este
    paso, aparte de ``_clave_de_orden``, adelanta cada representante hasta
    justo delante del primero de sus propios miembros —en el mismo orden en
    que ``ordenadas`` ya los entrega— sin tocar la posición relativa de
    ningún otro par de candidatos. Solo actúa dentro del mismo nivel de
    criticidad, la única dimensión que ya dominaba el orden antes de esta
    corrección; ``G12`` protege el resto.

    Devuelve, junto al orden resultante, dos conjuntos de representantes
    (CODEX-001, incidencia #457, quinta y séptima ronda). El primero,
    ``representantes_promovidos``, son los que de verdad cambiaron de
    posición: compartir nivel de criticidad con el candidato es la
    condición que habilita el adelanto, no la prueba de que ocurrió — si el
    representante ya encabezaba a ese miembro, el ``insert`` de abajo nunca
    se ejecuta y no hay movimiento real que declarar. El segundo,
    ``representantes_con_adelanto_habilitado``, son los que llegaron a esa
    condición —al menos un miembro propio comparte su nivel de
    criticidad— con independencia de si el ``insert`` se ejecutó: sirve
    para que la traza distinga, sobre el propio representante, entre "no
    tiene ningún miembro en su nivel de criticidad" (mecanismo inaplicable)
    y "tiene uno, pero ya lo encabezaba" (mecanismo aplicable, sin
    movimiento).
    """
    resultado = list(ordenadas)
    representantes_con_adelanto_habilitado: set[str] = set()
    representantes_promovidos: set[str] = set()
    for candidata in ordenadas:
        representante = representante_de(candidata.item.id)
        if (
            representante is None
            or representante == candidata.item.id
            or representante in representantes_con_adelanto_habilitado
        ):
            continue
        if criticidad_de(representante) != criticidad_de(candidata.item.id):
            continue
        indice_representante = next(
            i for i, c in enumerate(resultado) if c.item.id == representante
        )
        indice_miembro = next(i for i, c in enumerate(resultado) if c.item.id == candidata.item.id)
        if indice_representante > indice_miembro:
            resultado.insert(indice_miembro, resultado.pop(indice_representante))
            representantes_promovidos.add(representante)
        representantes_con_adelanto_habilitado.add(representante)
    return (
        tuple(resultado),
        frozenset(representantes_promovidos),
        frozenset(representantes_con_adelanto_habilitado),
    )


def _estado_de_promocion(
    identidad: str,
    grupo: GrupoDeEquivalentes | None,
    criticidad_de: Callable[[str], Criticidad],
    representantes_promovidos: frozenset[str],
    representantes_con_adelanto_habilitado: frozenset[str],
) -> tuple[bool, bool]:
    """Refleja el movimiento que de verdad ejecutó
    ``_con_representante_al_frente`` (CODEX-001, incidencia #457, quinta y
    séptima ronda), no las condiciones que lo habilitan: sin grupo, o con el
    representante en otro nivel de criticidad, no hay promoción posible.
    Compartir nivel de criticidad con el representante tampoco basta por sí
    solo, porque el representante puede ya encabezar el orden sin que se
    haya ejecutado ningún ``insert`` — ese tercer caso (mismo grupo, misma
    criticidad, sin movimiento) es distinto de los dos anteriores y necesita
    su propia frase en ``explicar()``, no la de "no pertenece a un grupo o
    tiene otra criticidad", que sería falsa para él. Solo
    ``representantes_promovidos`` —el conjunto que ``_con_representante_al_
    frente`` devuelve cuando sí ejecuta el ``insert``— certifica que hubo
    movimiento. Es plomería de la traza, no una segunda fuente de verdad
    sobre el orden: ninguna llamada aquí puede cambiar qué posición ocupa
    nadie.

    Cuando ``identidad`` es el propio representante, comparar su criticidad
    contra la suya propia es una tautología —siempre coincide— y no dice
    nada sobre si el grupo tiene algún miembro en su nivel de criticidad.
    Por eso ese caso no usa la comparación de criticidad: usa
    ``representantes_con_adelanto_habilitado``, que solo contiene
    representantes con al menos un miembro propio en su mismo nivel.

    Devuelve ``(promocion_real, representante_ya_al_frente)``: como mucho
    uno de los dos es verdadero.
    """
    if grupo is None:
        return False, False
    if identidad == grupo.representante:
        if grupo.representante in representantes_promovidos:
            return True, False
        if grupo.representante in representantes_con_adelanto_habilitado:
            return False, True
        return False, False
    if criticidad_de(grupo.representante) != criticidad_de(identidad):
        return False, False
    if grupo.representante in representantes_promovidos:
        return True, False
    return False, True


def _suficiente(contadas: int, peticion: Peticion) -> bool:
    """Condición de insuficiencia entre etapas.

    ``contadas`` es la cardinalidad semántica: un grupo de equivalentes
    cuenta una vez. ``EXHAUSTIVA`` no se satisface por cuota.
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
    """Recorre ``E0-E5``. No mide: recupera.

    La fuente de candidatas solo interviene en ``candidatas()`` y
    ``leer()``. Todo lo demás —orden, puertas, insuficiencia,
    deduplicación, agrupación, límite, parada, explicación y traza— lo
    decide este motor, igual para toda fuente.
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
        if (bloqueo := stops.parada_por_modo(etapa, peticion)) is not None:
            parada = bloqueo
            break

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
    unicas, senales_fusionadas = grouping.deduplicar_por_identidad(semantico.admitidas)
    for identidad, senales in sorted(senales_fusionadas.items()):
        traza.registrar_deduplicacion(identidad, senales)

    agrupacion = grouping.agrupar_equivalentes(unicas, plano.property_key)
    for grupo in agrupacion.grupos:
        traza.registrar_agrupacion(
            grupo.representante, grupo.miembros, grupo.razon_del_representante, grupo.ejes
        )

    if set(agrupacion.miembros_totales) != {c.item.id for c in unicas}:
        msg = "la agrupacion perdio elegibles: los miembros no cubren lo admitido"
        raise RecuperacionInvalidaError(msg)

    grupo_por_item = {m: g for g in agrupacion.grupos for m in g.miembros}

    def representante_de(identidad: str) -> str | None:
        return grupo_por_item[identidad].representante if identidad in grupo_por_item else None

    ordenadas_por_criticidad = sorted(unicas, key=lambda c: _clave_de_orden(c, criticidad_de))
    (
        ordenadas,
        representantes_promovidos,
        representantes_con_adelanto_habilitado,
    ) = _con_representante_al_frente(ordenadas_por_criticidad, criticidad_de, representante_de)
    g12 = gates.aplicar_g12(ordenadas, peticion, criticidad_de, lambda i: i in grupo_por_item)
    traza.desbordamiento = g12.desbordamiento_declarado
    traza.desbordamiento_critico = g12.desbordamiento_critico
    traza.criticos_omitidos = g12.criticos_omitidos
    traza.miembros_omitidos = g12.miembros_omitidos

    entregados = {c.item.id for c in g12.dentro_del_limite}

    criticos_elegibles = {
        c.item.id for c in unicas if criticidad_de(c.item.id) is Criticidad.CRITICA
    }
    perdidos = sorted(criticos_elegibles - entregados - set(g12.criticos_omitidos))
    if perdidos:
        msg = f"criticos elegibles perdidos sin declarar desbordamiento: {', '.join(perdidos)}"
        raise RecuperacionInvalidaError(msg)

    grupos_truncados = tuple(
        g.identificador for g in agrupacion.grupos if not set(g.miembros) <= entregados
    )
    traza.grupos_truncados = grupos_truncados

    if grupos_truncados and (parada is None or parada.identificador == "S1"):
        omitidos = sum(1 for g in agrupacion.grupos for m in g.miembros if m not in entregados)
        parada = stops.parada_por_grupo_truncado(grupos_truncados[0], omitidos)
    if parada is None:
        if (riesgo := stops.parada_por_riesgo_semantico(conflictos)) is not None:
            parada = riesgo
        else:
            parada = stops.parada_por_agotamiento(peticion)

    def _explicacion_de(orden: int, candidata: Candidata) -> Explicacion:
        promocion_real, representante_ya_al_frente = _estado_de_promocion(
            candidata.item.id,
            grupo_por_item.get(candidata.item.id),
            criticidad_de,
            representantes_promovidos,
            representantes_con_adelanto_habilitado,
        )
        return explicar(
            candidata,
            peticion,
            orden,
            criticidad=plano.criticidad_aplicada(candidata.item.id),
            grupo=grupo_por_item.get(candidata.item.id),
            promocion_real=promocion_real,
            representante_ya_al_frente=representante_ya_al_frente,
        )

    resultados = tuple(
        Resultado(
            item=candidata.item,
            etapa_de_origen=candidata.etapa,
            lectura=candidata.lectura,
            explicacion=_explicacion_de(orden, candidata),
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
    """Necesidades distintas: los equivalentes cuentan una vez."""
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
    """Estado interno detallado por cardinalidad y taxonomía.

    ``PARCIAL`` gana a ``COMPLETA`` cuando el límite dejó fuera miembros de
    un grupo o desbordó un crítico: la necesidad no quedó cubierta aunque la
    cuota cuadrase.
    """
    if not resultados:
        return Suficiencia.NINGUNA_EN_AMBITO
    if g12.desbordamiento_critico or g12.miembros_omitidos:
        return Suficiencia.PARCIAL
    if todo_atribuido := all(r.item.clase_de_evidencia.value == "ATRIBUIDA" for r in resultados):
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
    """Ausencia y no-reportable comparten redacción externa."""
    if suficiencia in (Suficiencia.NINGUNA_EN_AMBITO, Suficiencia.NO_REPORTABLE):
        return ESTADO_EXTERNO_SIN_RESULTADO
    return suficiencia.value
