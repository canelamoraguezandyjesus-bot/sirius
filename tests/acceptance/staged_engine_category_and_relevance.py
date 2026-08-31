"""Índice de categoría (M9, §6.2), filtro de relevancia (M10, §6.3) y las
dos causas que ADR-112 dejó nombradas con fichero y línea — conectados al
arnés del banco de 47 casos, incidencia #463 y su cierre, incidencia #465.

Las dos piezas de producto ya están portadas a `main`, ambas detrás de la
puerta de activación de D7 punto 6 (`category_matching_enabled`, `False` por
defecto): `sirius.domain.relevance.category_matches_query` (M9) y el candado
de `ContextBuilder._apply_relevance_filter`
(`src/sirius/application/context.py:239-258`, M10). Este módulo no toca
ninguna de las dos ni la puerta que las cierra. Lo que sí hace, únicamente en
este arnés (nunca contra `Memory`/`Decision` reales), es reproducir la
semántica que el laboratorio medía y que ADR-112 diagnosticó que el producto,
tal como está aprobado, no puede reproducir sobre este banco concreto — las
dos causas que la incidencia #465 autoriza a cerrar aquí, sin ampliar ningún
diseño de producto.

CAUSA 1 — ÍNDICE DE CATEGORÍA: LA «CATEGORÍA BUSCABLE» DE LA PR #117
=========================================================================

`SIRIUS-ARQ-0.2 §6.1 punto 1` fija que "el vocabulario de `category` es
exactamente el que porta el banco de 47 casos". El vocabulario que el banco
porta es el que el laboratorio ya congeló antes de medir, en
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
`tests/unit/test_relevance_domain.py`). Es diseño ya aprobado (PR #450, M9) y
sigue intacto, sin tocar, detrás de la puerta — esta incidencia no lo toca.

ADR-112 diagnosticó, con esa cita de fichero y línea, que esa regla de
activación única deja sin señal a cuatro de las cinco consultas del banco que
contienen alguna palabra del vocabulario (`B04-CA-26/31/38/44` activan
`"esencial"` y `"restriccion"` a la vez). El laboratorio no tenía esa
restricción: indexaba las cinco palabras juntas sobre una tabla FTS5 lateral
(`experiments/adr002/lateral/categoria.py:construir`, `palabras_de_categoria`)
como el **mismo contenido** para toda identidad no ordinaria, así que
cualquier coincidencia con **cualquiera** de las cinco palabras activaba la
categoría para todas ellas — nunca "el único término que activa la consulta".
Esa es la pieza que PR #117 llama **la categoría buscable** ("medida, sin
modelo... por sí sola lleva las omisiones de 11 a 5. No requiere Ollama").

La incidencia #465 autoriza reproducir ESA semántica —únicamente en el
camino de este arnés, nunca en `category_matches_query` ni en ninguna pieza
de producto, que sigue siendo la regla estricta ya aprobada— con
`activa_categoria_buscable`: activa la categoría si la consulta contiene
**cualquiera** de las cinco palabras del vocabulario, sin exigir que sea la
única. `indice_de_categoria` la usa en vez de `category_matches_query`.

CAUSA 1 (CONTINUACIÓN) — LA REGLA DE LAS CRÍTICAS ORIGINAL (RF-25/RF-26)
=========================================================================

ADR-112 también diagnosticó, con cita de fichero y línea
(`src/sirius/application/context.py:239-258`), que el candado de M10 protege
la unión de "conservado por el filtro", "categoría de máxima criticidad" y
"sin categoría todavía" — y que, con solo dos estados de categoría posibles
en este banco (`"restriccion"` o `None`), esa unión cubre el 100% de los
candidatos: el filtro de relevancia queda neutralizado por completo,
cualquiera que sea su veredicto (`aplicar_candado`, más abajo, y
`test_el_candado_protege_todo_candidato_de_este_banco` lo fijan como prueba).

La incidencia #465 autoriza, para este arnés y en su lugar, la regla de las
críticas ORIGINAL del laboratorio — la primera de las tres piezas que PR
#117 declara "medida y confirmada": «si el filtro conserva algunas, no puede
descartar una crítica [`RF-25`]; si declara que ninguna responde, ese
veredicto se respeta entero [`RF-26`]» (`experiments/adr002/modelo_local/
filtro.py:filtrar`, docstring del módulo y de la función). A diferencia del
candado de M10 (que protege TODO lo no clasificado en una categoría no
crítica, sin mirar el veredicto del filtro), esta regla solo protege lo que
el canon ya marca como no ordinario, y solo cuando el filtro sí actuó
seleccionando algo — nunca cuando declaró ausencia total, que se respeta sin
rescate. `aplicar_regla_de_criticas_original` la reproduce sobre el doble
determinista de la corrida congelada.

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
decidir. `aplicar_regla_de_criticas_original` hereda esa misma apertura: una
identidad que la corrida congelada nunca examinó para el caso pasa intacta.

EL CANDADO (M10): LA MISMA UNIÓN DE TRES CONJUNTOS QUE `ContextBuilder`
=========================================================================

`aplicar_candado` sigue reproduciendo, sin cambios, la fórmula de
`ContextBuilder._apply_relevance_filter`
(`src/sirius/application/context.py:239-258`): el resultado del filtro, unido
a todo candidato de la categoría de máxima criticidad, unido a todo candidato
sin categoría todavía. Se conserva en este módulo, con su prueba de forma,
como la evidencia exacta de por qué ADR-112 diagnosticó la causa 2 —pero
`_ejecutar_banco_motor_portado` ya no la invoca: usa
`aplicar_regla_de_criticas_original` en su lugar, según autoriza la
incidencia #465.

CAUSA 2 — LA SIEMBRA AL ENSAMBLAR CONTEXTO
=========================================================================

La tercera pieza que PR #117 declara, con estatuto propio: «se escribió
después de ver qué casos fallaban y los dos únicos casos con ese propósito
son esos dos, de modo que el banco la confirmaría por construcción. Se
sostiene por diseño, y una prueba deja ese hecho asertado» —portada de
`experiments/adr002/lateral/categoria.py:_pide_contexto` (rama
`evidence/adr001-spikes`): si la petición declara, en su propio campo
`proposito`, que ensambla el contexto de un proyecto
(`PROPOSITO_DE_CONTEXTO in proposito`), se suman al conjunto admitido todas
las identidades vigentes de categoría no ordinaria dentro del ámbito de la
petición (más las de ámbito global, que `G4` admite siempre,
`src/sirius/domain/staged_engine_gates.py:_g4`) — nunca fuera de él.
`siembra_de_contexto` lo reproduce en este arnés.

**Estatuto, sin ocultarlo**: de las 47 consultas del banco, únicamente
`B04-CA-33` y `B04-CA-34` declaran ese propósito
(`test_la_siembra_en_contexto_la_confirman_solo_los_dos_casos_por_
construccion`,
`tests/acceptance/test_pa_0_2_rec_01_banco_evidencia.py`) — los mismos dos
que PR #117 nombra. El banco no puede confirmar esta regla de forma
independiente: la confirma por construcción, porque se escribió después de
ver que esos dos casos fallaban. La salvedad (a) de la Definición §3.2
(ampliar el banco con casos independientes de la siembra, o retirarla) queda
citada aquí como pendiente registrada del propietario para la declaración
formal de PA-0.2-REC-01 — esta incidencia no la resuelve.

INCIDENCIA #467 — RESTRICCIÓN POR ÁMBITO DEL ÍNDICE DE CATEGORÍA
=========================================================================

ADR-113 diagnosticó, con cita de fichero y línea, que `indice_de_categoria`
era la causa dominante de `elementos_de_mas`: admitía **todas** las
identidades de máxima criticidad del banco en cuanto la consulta activaba la
«categoría buscable», sin mirar su proyecto — la misma falta de restricción
de `RankRelevantKnowledgeUseCase._rank_via_staged_engine`'s `solo_por_
categoria` (`src/sirius/application/rank_relevant_knowledge.py:243-280`,
diseño ya aprobado de producto: "`category_match` es una señal de M9, no un
filtro de alcance"). La incidencia #467 autoriza cerrar esa causa
**únicamente en este arnés**, reproduciendo la semántica de ámbito que el
laboratorio aplicaba aguas abajo del índice de categoría —nunca dentro de
`categoria.py` mismo, que no filtra por ámbito porque no es su trabajo—:
`experiments/adr002/lateral/categoria.py:46-49` (rama
`evidence/adr001-spikes`): "la razon es el ambito: `G4` filtra por proyecto
antes de entregar, de modo que `N1-31` se queda con los criticos **de su
ambito**"; y `categoria.py:174-175`, en `_pide_contexto`: "El ambito hace el
resto: `G4` filtra por proyecto, de modo que entran las criticas de ese
proyecto y no las de otro". Es la **misma** fuente y la **misma** cita que
ya sostenía `siembra_de_contexto` (incidencia #465, causa 2, más arriba): el
laboratorio nunca tuvo dos reglas de ámbito distintas para el índice de
categoría y para la siembra, tuvo una sola —`G4`, aguas abajo de ambas—, así
que `indice_de_categoria` y `siembra_de_contexto` comparten aquí el mismo
criterio de ámbito, `_en_ambito_declarado`: dentro del proyecto que la
petición declara, o de ámbito global (`PRJ-GLOBAL`), que `G4` admite siempre
(`src/sirius/domain/staged_engine_gates.py:135-152`, la clase
`AMBITO_GLOBAL` de la puerta).

**Resultado medido** (ADR-114): `elementos_de_mas` baja de 110 a 62;
`aciertos_exactos` (27/47), `omisiones_criticas` (0) y `cobertura` (63/81)
no se mueven. D1 (aciertos exactos ≥ 29/47, elementos de más ≤ 21) sigue sin
alcanzarse; ADR-114 diagnostica, elemento a elemento contra el fixture, las
dos causas residuales que quedan tras cerrar esta.
"""

from __future__ import annotations

import json
from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Final

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

#: Portado de ``experiments/adr002/lateral/categoria.py:_pide_contexto``
#: (rama ``evidence/adr001-spikes``): el propósito que declara que la
#: petición ensambla el contexto de un proyecto (incidencia #465, causa 2).
PROPOSITO_DE_CONTEXTO: Final = "contexto"

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


def activa_categoria_buscable(
    consulta: str, vocabulario: frozenset[str] = VOCABULARIO_DE_CATEGORIA
) -> bool:
    """La «categoría buscable» de la PR #117, réplica de la indexación FTS5
    de ``experiments/adr002/lateral/categoria.py`` (rama
    ``evidence/adr001-spikes``): el índice no guarda, por identidad, el
    término único que la activa — guarda **las cinco palabras del
    vocabulario juntas** como el mismo contenido para toda identidad no
    ordinaria (``palabras_de_categoria``, `categoria.py:88-101`), así que
    cualquier coincidencia de la consulta con **cualquiera** de ellas activa
    la categoría para todas. Una consulta con dos o más términos a la vez
    sigue contando — a diferencia de la regla de activación única que
    ``category_matches_query`` exige para el producto real
    (`src/sirius/domain/relevance.py:142-171`, PR #450/M9, sin tocar aquí:
    esta función nunca la llama ni reproduce su restricción). Incidencia
    #465, causa 1."""
    normalizada = consulta.strip().casefold()
    if not normalizada:
        return False
    return any(termino.casefold() in normalizada for termino in vocabulario)


def _en_ambito_declarado(
    identidad: str,
    *,
    ambito_declarado: str,
    proyecto_por_identidad: Mapping[str, str],
) -> bool:
    """Si ``identidad`` cae dentro del ámbito que la petición declara:
    ``ambito_declarado`` es ``GLOBAL`` (entra todo), la identidad pertenece
    al mismo proyecto que ``ambito_declarado``, o la identidad es de ámbito
    global (``PRJ-GLOBAL``) — la misma clase de ámbito que `G4`
    (`src/sirius/domain/staged_engine_gates.py:135-152`) admite siempre,
    cualquiera que sea el ámbito de la petición. Compartido por
    ``indice_de_categoria`` (incidencia #467) y ``siembra_de_contexto``
    (incidencia #465, causa 2), que ya aplicaba este mismo criterio."""
    if ambito_declarado == "GLOBAL":
        return True
    proyecto = proyecto_por_identidad.get(identidad)
    return proyecto in ("PRJ-GLOBAL", ambito_declarado)


def indice_de_categoria(
    *,
    consulta: str,
    ya_admitidos: Iterable[str],
    categoria_por_identidad: Mapping[str, str | None],
    ambito_declarado: str,
    proyecto_por_identidad: Mapping[str, str],
) -> frozenset[str]:
    """La ampliación de M9 (§6.2) con la semántica del laboratorio: toda
    identidad no admitida todavía por el motor, de la categoría de máxima
    criticidad y dentro del ámbito declarado de la consulta (más las de
    ámbito global, que `G4` admite siempre), si ``consulta`` activa la
    «categoría buscable» (``activa_categoria_buscable``, incidencia #465
    causa 1) — misma lógica de conjunto que ``RankRelevantKnowledgeUseCase.
    _rank_via_staged_engine``'s ``solo_por_categoria`` (`src/sirius/
    application/rank_relevant_knowledge.py:243-280`), sin su reordenación
    posterior (irrelevante aquí: las cuatro métricas del banco comparan
    conjuntos, no orden) y sin su ausencia de restricción de ámbito, que
    sigue intacta como diseño de producto detrás de la puerta
    (`solo_por_categoria` no filtra por ámbito porque `category_match` "no
    es un filtro de alcance"; esta función del arnés sí lo hace, porque la
    incidencia #467 autoriza reproducir aquí, únicamente en este arnés, la
    semántica de ámbito que el laboratorio aplicaba aguas abajo del índice
    de categoría: `experiments/adr002/lateral/categoria.py:46-49` y
    `:158-159` (rama `evidence/adr001-spikes`) — "la razon es el ambito: G4
    filtra por proyecto antes de entregar" / "El ambito hace el resto: G4
    filtra por proyecto, de modo que entran las criticas de ese proyecto y
    no las de otro")."""
    if not activa_categoria_buscable(consulta):
        return frozenset()
    ya_admitidos_set = frozenset(ya_admitidos)
    return frozenset(
        identidad
        for identidad, categoria in categoria_por_identidad.items()
        if identidad not in ya_admitidos_set
        and categoria == CATEGORIA_DE_MAXIMA_CRITICIDAD
        and _en_ambito_declarado(
            identidad,
            ambito_declarado=ambito_declarado,
            proyecto_por_identidad=proyecto_por_identidad,
        )
    )


def pide_contexto(proposito: str) -> bool:
    """Réplica de ``experiments/adr002/lateral/categoria.py:_pide_contexto``
    (rama ``evidence/adr001-spikes``): si ``proposito`` —el campo propio de
    la petición, nunca una adivinanza sobre el texto de la consulta—
    declara que se ensambla el contexto de un proyecto. Incidencia #465,
    causa 2 («la siembra al ensamblar contexto»)."""
    return PROPOSITO_DE_CONTEXTO in proposito.casefold()


def siembra_de_contexto(
    *,
    proposito: str,
    ambito_declarado: str,
    ya_admitidos: Iterable[str],
    categoria_por_identidad: Mapping[str, str | None],
    proyecto_por_identidad: Mapping[str, str],
) -> frozenset[str]:
    """La tercera pieza de la PR #117 («se sostiene por diseño, y una prueba
    deja ese hecho asertado»): si ``proposito`` declara que la petición
    ensambla contexto (``pide_contexto``), siembra toda identidad vigente de
    categoría no ordinaria dentro del ámbito declarado —más las de ámbito
    global, que ``G4`` admite siempre
    (`src/sirius/domain/staged_engine_gates.py:_g4`)—, nunca fuera de él.
    Sin propósito de contexto, no siembra nada: ``frozenset()``.

    **Estatuto, sin ocultarlo** (ver docstring del módulo): el banco solo
    tiene dos casos con este propósito (`B04-CA-33`, `B04-CA-34`), así que
    no puede confirmar esta regla de forma independiente — la confirma por
    construcción, tal como PR #117 lo declara. Incidencia #465, causa 2."""
    if not pide_contexto(proposito):
        return frozenset()
    ya_admitidos_set = frozenset(ya_admitidos)
    return frozenset(
        identidad
        for identidad, categoria in categoria_por_identidad.items()
        if identidad not in ya_admitidos_set
        and categoria == CATEGORIA_DE_MAXIMA_CRITICIDAD
        and _en_ambito_declarado(
            identidad,
            ambito_declarado=ambito_declarado,
            proyecto_por_identidad=proyecto_por_identidad,
        )
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
    candidato sin categoría todavía —, nunca una segunda llamada al filtro.

    Conservada como evidencia de ADR-112 (causa 2): ``_ejecutar_banco_motor_
    portado`` ya no la invoca, usa ``aplicar_regla_de_criticas_original`` en
    su lugar (incidencia #465)."""
    return frozenset(
        identidad
        for identidad in candidatos
        if conserva_el_filtro(identidad)
        or categoria_por_identidad.get(identidad) is None
        or categoria_por_identidad.get(identidad) == CATEGORIA_DE_MAXIMA_CRITICIDAD
    )


def aplicar_regla_de_criticas_original(
    *,
    caso_id: str,
    candidatos: Iterable[str],
    categoria_por_identidad: Mapping[str, str | None],
) -> frozenset[str]:
    """La regla de las críticas ORIGINAL del laboratorio
    (``experiments/adr002/modelo_local/filtro.py:filtrar``, RF-25/RF-26),
    en lugar del candado de M10 (incidencia #465, causa 1): si el filtro
    conserva algunas, no puede descartar una crítica (se rescata); si
    declara que ninguna responde, ese veredicto se respeta entero, sin
    rescate. Solo protege lo que el canon ya marca como no ordinario
    (``categoria_por_identidad`` == ``CATEGORIA_DE_MAXIMA_CRITICIDAD``), a
    diferencia del candado de M10 que protege también lo sin categoría.

    Falla abierto —misma garantía que ``filtro_congelado_conserva``— para
    cualquier caso, o candidato, que la corrida congelada nunca examinó:
    ese candidato pasa intacto, nunca se descarta sin veredicto."""
    candidatos_set = frozenset(candidatos)
    veredicto = FILTRO_CONGELADO.get(caso_id)
    if veredicto is None:
        return candidatos_set

    entraron = veredicto.entraron_al_filtro & candidatos_set
    no_entraron = candidatos_set - entraron
    if not entraron:
        return candidatos_set

    conservados = veredicto.conservados_por_el_modelo & entraron
    if not conservados:
        # RF-26: el modelo declara ausencia total. Se respeta entera, sin
        # rescate — lo que no entró al filtro sigue intacto.
        return no_entraron

    # RF-25: el modelo eligió algunas. No puede tirar una crítica: se
    # rescata lo que el canon marca como no ordinario y el modelo descartó.
    rescatadas = frozenset(
        identidad
        for identidad in entraron - conservados
        if categoria_por_identidad.get(identidad) == CATEGORIA_DE_MAXIMA_CRITICIDAD
    )
    return no_entraron | conservados | rescatadas


__all__ = [
    "CATEGORIA_DE_MAXIMA_CRITICIDAD",
    "FILTRO_CONGELADO",
    "PROPOSITO_DE_CONTEXTO",
    "VOCABULARIO_DE_CATEGORIA",
    "activa_categoria_buscable",
    "aplicar_candado",
    "aplicar_regla_de_criticas_original",
    "categoria_del_item",
    "filtro_congelado_conserva",
    "indice_de_categoria",
    "pide_contexto",
    "siembra_de_contexto",
]
