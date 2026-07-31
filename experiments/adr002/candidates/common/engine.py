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

from collections.abc import Sequence
from dataclasses import dataclass

from experiments.adr002.candidates.common import gates, stops
from experiments.adr002.candidates.common.contracts import (
    ESTADO_EXTERNO_SIN_RESULTADO,
    ETAPAS_DE_EXPANSION,
    Candidata,
    Cardinalidad,
    ContextoDeEtapa,
    Etapa,
    Peticion,
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

    @property
    def ids(self) -> tuple[str, ...]:
        return tuple(r.item.id for r in self.resultados)


def _clave_de_orden(candidata: Candidata) -> tuple[int, int, str, str]:
    """Desempate **estable y registrado** (``B04`` M-05, ``RF-22``).

    Por criticidad, luego por etapa de origen —la autoridad decrece de ``E1``
    a ``E4``—, luego por identidad estable. Nunca por el orden de llegada, que
    dependeria del motor de base de datos y no seria reproducible.
    """
    critica = 0 if candidata.item.criticidad.value == "CRITICA" else 1
    autoridad = list(ETAPAS_DE_EXPANSION).index(candidata.etapa)
    return (critica, autoridad, candidata.item.subject_key, candidata.item.id)


def _agrupar(candidatas: Sequence[Candidata], traza: Traza) -> list[Candidata]:
    """Deduplicacion de ``B04-RF-20``: solo si coinciden ambito **y** postura.

    Dos lecturas del mismo sujeto con polaridad distinta **no** se agrupan: se
    conservan ambas y el conflicto sale a la traza. Agruparlas seria resolver
    en silencio un conflicto que ``RF-21`` obliga a mostrar.
    """
    vistos: dict[tuple[str, str | None, str], Candidata] = {}
    agrupados: dict[tuple[str, str | None, str], list[str]] = {}
    for candidata in candidatas:
        clave = (
            candidata.item.subject_key,
            candidata.item.project_id,
            candidata.lectura.polaridad.value,
        )
        if clave in vistos:
            agrupados.setdefault(clave, []).append(candidata.item.id)
            continue
        vistos[clave] = candidata
    for clave, ids in agrupados.items():
        traza.registrar_agrupacion(vistos[clave].item.id, ids)
    return list(vistos.values())


def _suficiente(admitidas: Sequence[Candidata], peticion: Peticion) -> bool:
    """Condicion de insuficiencia entre etapas, explicita (``B04-RF-16``)."""
    if peticion.cardinalidad is Cardinalidad.EXHAUSTIVA:
        return False  # exhaustiva no se satisface por cuota: agota o para por S2-S7
    if peticion.cardinalidad is Cardinalidad.EXACTA:
        return len(admitidas) >= peticion.objetivos
    return len(admitidas) >= peticion.limite_objetivo


def recuperar(
    peticion: Peticion,
    puerto: PuertoDeRecuperacion,
    candidato: SenalesDeCandidato,
) -> Recuperacion:
    """Recorre ``E0-E5`` conforme a B04. **No mide**: recupera.

    El candidato solo interviene en ``candidatas()`` y ``leer()``. Todo lo
    demas —orden, puertas, insuficiencia, agrupacion, parada, explicacion y
    traza— lo decide este motor, igual para todos.
    """
    traza = traza_nueva(peticion, candidato.identificador)

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

        suficiente = _suficiente(admitidas, peticion)
        traza.registrar_etapa(PasoDeEtapa(etapa, causa, len(aportadas), len(nuevas), suficiente))

        # --- S1: suficiencia por cardinalidad, si la cardinalidad la admite.
        if (fin := stops.evaluar_suficiencia(admitidas, peticion)) is not None:
            parada = fin
            break
        # --- S4: limite duro alcanzado.
        if (tope := stops.parada_por_limite_duro(admitidas, peticion)) is not None:
            parada = tope
            break
        causa = f"{etapa.value} insuficiente: {len(admitidas)} elegibles tras puertas"

    # --- G11 antes de ordenar; el conflicto se conserva, no se fusiona.
    semantico = gates.aplicar_g11(admitidas, peticion)
    traza.registrar_descartes(semantico.descartes)
    conflictos = gates.conflictos_de_polaridad(semantico.admitidas)
    traza.conflictos = conflictos

    if parada is None:
        if (riesgo := stops.parada_por_riesgo_semantico(conflictos)) is not None:
            parada = riesgo
        else:
            parada = stops.parada_por_agotamiento(peticion)

    # ---- E5: agrupar, ordenar, aplicar limite y adjudicar suficiencia. ----
    agrupadas = _agrupar(semantico.admitidas, traza)
    ordenadas = sorted(agrupadas, key=_clave_de_orden)
    g12 = gates.aplicar_g12(ordenadas, peticion)
    traza.desbordamiento = g12.desbordamiento_declarado
    traza.criticos_omitidos = g12.criticos_omitidos

    resultados = tuple(
        Resultado(
            item=candidata.item,
            etapa_de_origen=candidata.etapa,
            lectura=candidata.lectura,
            explicacion=explicar(candidata, peticion, orden),
        )
        for orden, candidata in enumerate(g12.dentro_del_limite, start=1)
    )

    suficiencia = _adjudicar_suficiencia(resultados, peticion, parada)
    traza.registrar_etapa(
        PasoDeEtapa(Etapa.E5, "adjudicacion y salida", len(agrupadas), len(resultados), True)
    )
    traza.parada = (parada.identificador, parada.fundamento)
    traza.suficiencia = suficiencia.value

    return Recuperacion(
        resultados=resultados,
        suficiencia=suficiencia,
        estado_externo=_estado_externo(suficiencia),
        parada=parada,
        traza=traza,
        conflictos=conflictos,
    )


def _adjudicar_suficiencia(
    resultados: Sequence[Resultado], peticion: Peticion, parada: stops.Parada
) -> Suficiencia:
    """``B04-RF-25``: estado interno detallado por cardinalidad y taxonomia."""
    if not resultados:
        return Suficiencia.NINGUNA_EN_AMBITO
    if parada.identificador == "S1":
        return Suficiencia.COMPLETA
    if peticion.cardinalidad is Cardinalidad.EXACTA and len(resultados) >= peticion.objetivos:
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
