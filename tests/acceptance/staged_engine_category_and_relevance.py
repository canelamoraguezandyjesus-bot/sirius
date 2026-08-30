"""Índice de categoría (M9, §6.2) y filtro de relevancia (M10, §6.3),
conectados al arnés del banco de 47 casos — incidencia #463.

Las dos piezas ya están portadas a `main` como código de producto, ambas
detrás de la puerta de activación de D7 punto 6 (`category_matching_enabled`,
`False` por defecto): `sirius.domain.relevance.category_matches_query` (M9)
y el candado de `ContextBuilder._apply_relevance_filter`
(`src/sirius/application/context.py:239-258`, M10). Este módulo no toca
ninguna de las dos ni la puerta que las cierra: solo las invoca, con datos del
propio arnés, para que `_ejecutar_banco_motor_portado`
(`tests/acceptance/test_pa_0_2_rec_01_banco_evidencia.py`) mida qué producen
sobre el banco — nunca para abrir la puerta contra `Memory`/`Decision` reales.

ÍNDICE DE CATEGORÍA: VOCABULARIO Y CATEGORÍA, DERIVADOS DE LA CRITICIDAD
=========================================================================

`SIRIUS-ARQ-0.2 §6.1 punto 1` fija que "el vocabulario de `category` es
exactamente el que porta el banco de 47 casos" y que este documento "no
inventa categorías nuevas ni las enumera". El vocabulario que el banco porta
es el que el laboratorio ya congeló antes de medir, en
`experiments/adr002/lateral/categoria.py:72-78` (rama `evidence/adr001-spikes`,
`VOCABULARIO`) — las cinco palabras con las que alguien pediría la única
categoría que el laboratorio deriva de la criticidad del canon, nunca de un
modelo (`identidades_con_categoria`, `categoria.py:99-113`: todo elemento
cuya criticidad aplicada no sea `ORDINARIO` entra en esa única categoría,
leyendo solo `nivel`, nunca `razon_segura`).

`RankedKnowledge.category`/`category_matches_query` (`src/sirius/domain/
relevance.py:142-171`) no modelan "pertenece a la categoría de máxima
criticidad" como un conjunto de sinónimos: comparan la categoría persistida
del candidato, como cadena única, contra el **único** término del vocabulario
que la consulta activa — `len(activated) != 1` no cuenta como activación
(`test_category_matches_query_is_false_when_the_query_activates_more_than_one_category`,
`tests/unit/test_relevance_domain.py`). Por eso `CATEGORIA_DE_MAXIMA_
CRITICIDAD` aquí es literalmente `"restriccion"`, no un nombre nuevo: de las
cinco palabras del vocabulario congelado, es la única que activa sola (sin
`"esencial"` a la vez) en alguna consulta del banco (`B04-CA-02`, "¿Qué
restricciones de transporte tengo?"); las otras cuatro palabras nunca
aparecen solas en ninguna de las 47 consultas, así que asignarles la
categoría no habría activado ninguna coincidencia. Esta es una decisión de
este arnés, no del laboratorio (que indexaba las cinco palabras juntas sobre
FTS5 y no exigía activación única): documentada aquí y en ADR-112 porque
`category_matches_query` es la señal ya aprobada y no se modifica para esta
incidencia.

FILTRO DE RELEVANCIA: DOBLE DETERMINISTA DE LA CORRIDA CONGELADA
=================================================================

El laboratorio decide con un modelo local real (Ollama), que este arnés no
puede invocar en cada ejecución de CI y seguir siendo determinista. En vez de
reimplementar el modelo, este módulo porta **verbatim** el veredicto de la
corrida que produjo las cifras de D1
(`tests/acceptance/fixtures/relevance_filter_frozen_run.json`, portado de
`resultado_modelo_local_v0.7.json` en `evidence/adr001-spikes`, fila "4.
filtro con regla, con categoria") y lo reproduce como un doble: misma
decisión (conservar/descartar) por elemento y caso que aquella corrida.

El arnés de esta incidencia no comparte arquitectura de candidato con el
laboratorio (ADR-111 ya diagnosticó esa diferencia para la búsqueda sola), así
que puede presentarle al doble una identidad que la corrida congelada nunca
examinó para ese caso. El doble falla abierto en ese caso exacto — la misma
garantía contractual que `RelevanceFilterPort.filter_candidates` exige
(`src/sirius/ports/relevance_filter.py:19-40`): nunca descarta lo que no supo
decidir.

EL CANDADO (M10): LA MISMA UNIÓN DE TRES CONJUNTOS QUE `ContextBuilder`
=========================================================================

`aplicar_candado` reproduce exactamente la fórmula de
`ContextBuilder._apply_relevance_filter`
(`src/sirius/application/context.py:239-258`): el resultado del filtro, unido
a todo candidato de la categoría de máxima criticidad, unido a todo candidato
sin categoría todavía. Con solo dos estados posibles de categoría en este
arnés (`"restriccion"` o `None`, nunca una tercera categoría no crítica), el
candado protege, por construcción, a todo candidato: no hay ningún elemento
clasificado en una categoría no crítica al que este arnés pueda exponer el
veredicto del filtro. Esto no es un defecto de esta incidencia: es la lectura
literal de la fórmula aprobada sobre un banco que solo declara una categoría.
ADR-112 lo cita como el motivo exacto por el que el filtro no mueve ninguna
métrica más allá de lo que ya mueve el índice de categoría.
"""

from __future__ import annotations

import json
from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Final

from sirius.domain.relevance import category_matches_query

#: Portado sin modificar de ``experiments/adr002/lateral/categoria.py:72-78``
#: (rama ``evidence/adr001-spikes``): las palabras con las que alguien
#: pediría la categoría que el laboratorio deriva de la criticidad del canon.
VOCABULARIO_DE_CATEGORIA: Final[frozenset[str]] = frozenset(
    {
        "esencial",
        "restriccion",
        "critica",
        "obligatoria",
        "imprescindible",
    }
)

#: La única categoría que este arnés asigna (ver docstring del módulo: la
#: única palabra del vocabulario que activa sola, sin ambigüedad, en alguna
#: consulta del banco). También la categoría de máxima criticidad que
#: ``aplicar_candado`` protege.
CATEGORIA_DE_MAXIMA_CRITICIDAD: Final = "restriccion"

_FILTRO_FIXTURE_PATH = Path(__file__).parent / "fixtures" / "relevance_filter_frozen_run.json"


def categoria_del_item(item: Mapping[str, Any]) -> str | None:
    """La categoría canónica de un item del corpus congelado, derivada de su
    criticidad — nunca de ``razon_segura``, que esta función ni siquiera
    pide. Replica ``identidades_con_categoria``
    (``experiments/adr002/lateral/categoria.py:99-113``): todo item cuya
    criticidad aplicada no sea ``None`` (el banco no declara el nivel
    ``ORDINARIO`` explícito — ver ``test_pa_0_2_rec_01_banco_evidencia.py``)
    entra en la única categoría de este arnés."""
    return CATEGORIA_DE_MAXIMA_CRITICIDAD if item.get("criticidad") is not None else None


@dataclass(frozen=True, slots=True)
class _VeredictoCongelado:
    entraron_al_filtro: frozenset[str]
    conservados_por_el_modelo: frozenset[str]


def _cargar_filtro_congelado() -> Mapping[str, _VeredictoCongelado]:
    datos = json.loads(_FILTRO_FIXTURE_PATH.read_text(encoding="utf-8"))
    return {
        caso_id: _VeredictoCongelado(
            entraron_al_filtro=frozenset(valores["entraron_al_filtro"]),
            conservados_por_el_modelo=frozenset(valores["conservados_por_el_modelo"]),
        )
        for caso_id, valores in datos["casos"].items()
    }


#: Cargado una vez: el fixture es inmutable durante la ejecución del proceso
#: de pruebas, igual que ``evidence_bank_47_casos.json``.
FILTRO_CONGELADO: Final[Mapping[str, _VeredictoCongelado]] = _cargar_filtro_congelado()


def filtro_congelado_conserva(caso_id: str, identidad: str) -> bool:
    """El doble determinista del filtro de relevancia: la misma decisión
    (conservar/descartar) que la corrida congelada tomó para ``identidad``
    en ``caso_id``, antes de cualquier candado.

    Falla abierto —igual que ``RelevanceFilterPort``— para cualquier caso o
    identidad que la corrida congelada nunca examinó: este arnés puede
    construir candidatos que el laboratorio no vio (ADR-111), y el doble no
    tiene autoridad para inventar un veredicto sobre ellos.
    """
    veredicto = FILTRO_CONGELADO.get(caso_id)
    if veredicto is None or identidad not in veredicto.entraron_al_filtro:
        return True
    return identidad in veredicto.conservados_por_el_modelo


def indice_de_categoria(
    *,
    consulta: str,
    ya_admitidos: Iterable[str],
    categoria_por_identidad: Mapping[str, str | None],
) -> frozenset[str]:
    """La ampliación de M9 (§6.2): toda identidad no admitida todavía por el
    motor cuya categoría coincida con la que ``consulta`` activa —misma
    lógica de conjunto que ``RankRelevantKnowledgeUseCase._rank_via_staged_
    engine``'s ``solo_por_categoria`` (`src/sirius/application/
    rank_relevant_knowledge.py:243-280`), sin su reordenación posterior
    (irrelevante aquí: las cuatro métricas del banco comparan conjuntos, no
    orden). Como esa misma referencia, no restringe por ámbito: `category_
    match` es una señal de M9, no un filtro de alcance —esa es tarea de las
    puertas del motor, ya aplicadas antes de esta llamada."""
    ya_admitidos_set = frozenset(ya_admitidos)
    return frozenset(
        identidad
        for identidad, categoria in categoria_por_identidad.items()
        if identidad not in ya_admitidos_set
        and category_matches_query(categoria, consulta, VOCABULARIO_DE_CATEGORIA)
    )


def aplicar_candado(
    *,
    candidatos: Iterable[str],
    conserva_el_filtro: Callable[[str], bool],
    categoria_por_identidad: Mapping[str, str | None],
) -> frozenset[str]:
    """El candado de M10: la misma unión de tres conjuntos que
    ``ContextBuilder._apply_relevance_filter``
    (`src/sirius/application/context.py:239-258`) — lo que el filtro
    conservó, todo candidato de la categoría de máxima criticidad, y todo
    candidato sin categoría todavía —, nunca una segunda llamada al filtro."""
    return frozenset(
        identidad
        for identidad in candidatos
        if conserva_el_filtro(identidad)
        or categoria_por_identidad.get(identidad) is None
        or categoria_por_identidad.get(identidad) == CATEGORIA_DE_MAXIMA_CRITICIDAD
    )


__all__ = [
    "CATEGORIA_DE_MAXIMA_CRITICIDAD",
    "FILTRO_CONGELADO",
    "VOCABULARIO_DE_CATEGORIA",
    "aplicar_candado",
    "categoria_del_item",
    "filtro_congelado_conserva",
    "indice_de_categoria",
]
