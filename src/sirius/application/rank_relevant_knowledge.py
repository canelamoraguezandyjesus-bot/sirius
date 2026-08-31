"""Read-only, checkable relevance ranking over vigente knowledge (B6b;
SIRIUS-ARQ-0.1 S7.5; D-11).

Combines the structured filters (proyecto activo, decisión vigente cuyo
asunto coincide) with a real FTS5 ``MATCH`` against ``knowledge_fts`` (B6a)
purely through ``sirius.domain.relevance.rank_relevant_knowledge``: this use
case only fetches the vigente candidates and the explicit booleans that
function needs per candidate (subject match, FTS5 hit), computed once here
so the pure domain function never has to know about a repository.

Read-only: never mutates a memory, a decision, or an index. Not called by
``SendMessageUseCase`` or ``ContextBuilder`` — connecting either to this
retrieval is budget/trim (B6c) and context assembly (B6d), not this cut.

M9 (SIRIUS-ARQ-0.2 §6.2, D7) adds ``category_match``, the fourth structural
signal, computed here exactly like the other three. It stays behind the D7
point 6 activation gate — ``category_matching_enabled``, ``False`` by
default — that §6.2/§6.3 and ``docs/evolution/STATUS.md`` fix: until the
owner registers the matching threshold there, the gate must stay closed, and
``category_match`` is inert for every real candidate (never computed from
``category``/``query_text`` at all, so it can never accidentally reorder
anything) — the safest fallback the design describes. Wiring the real
category vocabulary and flipping the gate from persisted settings is M11's
job (``composition_root``), not this one: both constructor parameters below
default to the closed state, so every existing caller keeps building the
exact same behaviour it has today.

Incidencia #457/ADR-109: la misma puerta cerrada por defecto también
gobierna el motor por etapas portado desde el laboratorio
(``sirius.domain.staged_engine.recuperar``), que ADR-109 diagnosticó
necesario para cerrar la brecha de precisión que el tratamiento léxico
(#455/#456) por sí solo no cierra. Con la puerta cerrada —el estado por
defecto de todo caller existente, incluido este mismo repositorio hasta que
M11 (incidencia #453, bloqueada) decida abrirla desde ajustes— ``rank()``
sigue exactamente el camino de siempre, sin ejecutar ni importar nada del
motor. ``staged_engine_port``/``staged_engine_candidate`` son opcionales
porque un caller que nunca abre la puerta no tiene por qué construirlos.
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, datetime

from sirius.domain.relevance import (
    KnowledgeKind,
    RankedKnowledge,
    candidate_in_declared_scope,
    category_index_activated,
    category_matches_query,
    rank_relevant_knowledge,
    subject_matches_query,
)
from sirius.domain.staged_engine import recuperar
from sirius.domain.staged_engine_contracts import (
    PLANO_COMUN_VACIO,
    Ambito,
    Cardinalidad,
    Clase,
    Modo,
    Peticion,
    PuertoDeRecuperacion,
    SenalesDeCandidato,
    VentanaTemporal,
)
from sirius.ports.decision_repository import DecisionRepository
from sirius.ports.knowledge_search_repository import KnowledgeSearchRepository
from sirius.ports.memory_repository import MemoryRepository
from sirius.ports.project_repository import ProjectRepository

__all__ = ["RankRelevantKnowledgeUseCase"]

#: Propósito declarado de toda petición al motor por etapas: E0 exige uno no
#: vacío (G1) y Sirius 0.1 no tiene hoy un permiso explícito por llamada —
#: cada llamada a ``rank()`` es, por construcción, una recuperación de
#: contexto ordinaria.
_PROPOSITO_RECUPERACION_ORDINARIA = "recuperacion de contexto relevante (B6b)"

#: Límite que "no ata" (misma convención que
#: ``experiments/adr002/round/cases.py``: "los casos que no declaran limite
#: reciben un limite que no ata"): mayor que cualquier canon real de Sirius
#: 0.1 hoy, así que nunca es la causa de que algo se omita.
_LIMITE_SIN_ATAR = 100_000


def _peticion_ordinaria(query_text: str, operation_id: str) -> Peticion:
    """La política uniforme con la que ``rank()`` interroga al motor.

    Modo M1 (ordinario), ámbito global (``rank()`` nunca restringió por
    proyecto: ``project_matches_active`` es una señal de orden, no un
    filtro) y cardinalidad EXHAUSTIVA — la misma semántica de "todo lo
    relevante, sin cuota" que la política de hoy ya tiene, y la que menos
    depende de un objetivo de resultados que ninguna llamada a ``rank()``
    declara.
    """
    ahora = datetime.now(UTC).isoformat()
    return Peticion(
        operation_id=operation_id,
        consulta=query_text,
        proposito=_PROPOSITO_RECUPERACION_ORDINARIA,
        modo=Modo.M1_ORDINARIO,
        ambito=Ambito(global_=True, proyectos=()),
        ventana=VentanaTemporal(tiempo_objetivo=ahora, corte_de_registro=None),
        cardinalidad=Cardinalidad.EXHAUSTIVA,
        limite_objetivo=_LIMITE_SIN_ATAR,
        limite_duro=_LIMITE_SIN_ATAR,
    )


class RankRelevantKnowledgeUseCase:
    """Ordena el conocimiento vigente relacionado con una consulta (S7.5)."""

    def __init__(
        self,
        memory_repository: MemoryRepository,
        decision_repository: DecisionRepository,
        project_repository: ProjectRepository,
        knowledge_search_repository: KnowledgeSearchRepository,
        *,
        category_vocabulary: frozenset[str] = frozenset(),
        category_matching_enabled: bool = False,
        staged_engine_port: PuertoDeRecuperacion | None = None,
        staged_engine_candidate: SenalesDeCandidato | None = None,
    ) -> None:
        self._memory_repository = memory_repository
        self._decision_repository = decision_repository
        self._project_repository = project_repository
        self._knowledge_search_repository = knowledge_search_repository
        self._category_vocabulary = category_vocabulary
        self._category_matching_enabled = category_matching_enabled
        self._staged_engine_port = staged_engine_port
        self._staged_engine_candidate = staged_engine_candidate

    def rank(self, query_text: str) -> tuple[RankedKnowledge, ...]:
        """Return every vigente memory/decision related to ``query_text``,
        ordered by S7.5's explicit criteria tuple plus M9's category_match.

        A blank or all-punctuation ``query_text`` never raises: it simply
        matches nothing via FTS5, and any candidate that also has no
        matching subject is filtered out as "no relacionado" (see
        ``sirius.domain.relevance``) — an empty result, never an error.

        Con la puerta D7 punto 6 abierta y un puerto/candidato del motor por
        etapas configurados, delega en ``_rank_via_staged_engine`` (ADR-109)
        en vez de en el filtro-y-orden de siempre.
        """
        if (
            self._category_matching_enabled
            and self._staged_engine_port is not None
            and self._staged_engine_candidate is not None
        ):
            return self._rank_via_staged_engine(query_text)
        return self._rank_via_current_pipeline(query_text)

    def _rank_via_staged_engine(self, query_text: str) -> tuple[RankedKnowledge, ...]:
        """ADR-109: recuperación por ``E0-E5`` con las doce puertas y la
        agrupación de equivalentes, en vez del filtro-y-orden de S7.5.

        Traduce cada ``Resultado`` (identidad canónica ``CLASE:n``) de
        vuelta al ``Memory``/``Decision`` real por el mismo id, y construye
        ``RankedKnowledge`` con las mismas cuatro señales estructurales que
        el camino de siempre calcula, para que el orden final sea el mismo
        tipo de dato pase lo que pase por la puerta.

        El motor por etapas nunca genera un candidato solo por su
        categoría: sus etapas de expansión buscan por asunto exacto y FTS5,
        nunca por ``category``. M9 (§6.2) exige que ``category_match`` por sí
        solo siga bastando para que un candidato se encuentre
        (``rank_relevant_knowledge.is_related``) y para que decida su orden
        frente a la recencia — ninguna de las dos cosas que el motor por sí
        mismo puede dar, porque nunca ve esos candidatos. Por eso, tras
        traducir lo que el motor sí admitió, esta función completa la
        ampliación por separado: recorre el conocimiento vigente que el
        motor no admitió y añade el que coincide por categoría.

        M14 (§11.2/§11.5, incidencia #486) sustituye la regla de esa
        ampliación: en vez de la activación única de ``category_matches_query``
        sin restricción de ámbito que M9 portaba aquí, usa el índice de
        categoría buscable de activación múltiple (cualquier término del
        vocabulario, no uno único) con restricción por ámbito
        (``candidate_in_declared_scope`` — el proyecto activo de la petición
        más el ámbito global siempre admitido), réplica de
        ``indice_de_categoria``/``activa_categoria_buscable``/
        ``_en_ambito_declarado`` del arnés
        (``tests/acceptance/staged_engine_category_and_relevance.py``,
        ADR-113/114). ``category_matches_query`` sigue existiendo sin
        cambios, tanto para el estado-cerrado (``_rank_via_current_pipeline``)
        como para la señal ``category_match`` de los candidatos que el motor
        ya admitió arriba — solo la ampliación de este bloque cambia.

        M13 (§11.5, incidencia #489) optimiza cómo se calcula esa
        ampliación, sin tocar qué admite: en vez de recorrer la totalidad de
        ``list_current_memories()``/``list_current_decisions()`` en Python
        para filtrar candidato a candidato con
        ``category_index_matches_query``, primero decide en Python — sin
        tocar el repositorio — si la consulta activa el índice en absoluto
        (``category_index_activated``, la misma condición que
        ``category_index_matches_query`` exige junto con
        ``category is not None``); si no lo activa, el resultado es vacío
        sin ejecutar ninguna consulta, igual que antes. Si lo activa,
        interroga el repositorio pasándole ``self._category_vocabulary``
        únicamente como puerta de activación (D7 punto 1) —
        ``list_current_memories_by_category``/``list_current_decisions_by_category``
        no filtran en SQL por ese vocabulario, sino por
        ``category IS NOT NULL`` (CODEX-001, ronda 2, incidencia #489): una
        categoría persistida heredada, fuera del vocabulario cerrado, sigue
        siendo estado alcanzable —``SetCategoryUseCase`` no valida lo que
        escribe, y el vocabulario es una constante provisional que un
        milestone posterior puede sustituir— y también debe ampliar el
        match por categoría, no perderse silenciosamente. El resultado es
        exactamente la subcondición que ``category_index_matches_query``
        comprueba candidato a candidato (``category is not None``, sin
        comparar contra un término concreto), ahora resuelta en SQL en vez
        del corpus completo. La restricción de ámbito
        (``candidate_in_declared_scope``) sigue aplicándose en Python sobre
        ese subconjunto ya filtrado, no en SQL: es sobre filas que ya dejaron
        de depender del tamaño del corpus.

        Las puertas y la agrupación del motor (qué se admite y qué se
        trunca por ``limite_duro``) no se tocan: ``ranked`` es exactamente
        lo que el motor admitió, en el orden que ya le adjudicó —
        criticidad, representante del grupo y autoridad de etapa
        (``staged_engine.py``), ninguno de los cuales conoce
        ``rank_relevant_knowledge``. Por eso el bloque de M9 nunca se
        intercala volviendo a ordenar ``ranked`` entero por el criterio
        S7.5/M9 (sujeto, proyecto activo, FTS5, categoría, recencia): eso
        sustituiría la prioridad del motor por la de M9 incluso entre dos
        elementos que el motor ya admitió (CODEX-001, incidencia #457,
        tercera ronda). En vez de eso, ``_intercalar_por_categoria`` decide,
        candidato por candidato del bloque de categoría, dónde encaja
        respecto de ``ranked`` según ese mismo criterio S7.5/M9 — sin tocar
        jamás la posición relativa de dos elementos de ``ranked`` entre sí,
        y sin la ceguera a las demás señales que una simple concatenación de
        bloques produciría.
        """
        assert self._staged_engine_port is not None
        assert self._staged_engine_candidate is not None
        active_project = self._project_repository.get_active_project()
        active_project_id = active_project.id if active_project is not None else None

        peticion = _peticion_ordinaria(query_text, operation_id=f"rank:{query_text[:64]}")
        recuperacion = recuperar(
            peticion, self._staged_engine_port, self._staged_engine_candidate, PLANO_COMUN_VACIO
        )

        def category_match(category: str | None) -> bool:
            return self._category_matching_enabled and category_matches_query(
                category, query_text, self._category_vocabulary
            )

        ranked: list[RankedKnowledge] = []
        admitidos_por_el_motor: set[tuple[KnowledgeKind, int]] = set()
        for resultado in recuperacion.resultados:
            clase, _, numero = resultado.item.id.partition(":")
            item_id = int(numero)
            if clase == Clase.MEMORIA.value:
                memory = self._memory_repository.get_memory(item_id)
                admitidos_por_el_motor.add((KnowledgeKind.MEMORY, item_id))
                ranked.append(
                    RankedKnowledge(
                        kind=KnowledgeKind.MEMORY,
                        item=memory,
                        subject_matches_query=False,
                        project_matches_active=(
                            active_project_id is not None and memory.project_id == active_project_id
                        ),
                        fts_match=True,
                        category_match=category_match(memory.category),
                    )
                )
            else:
                decision = self._decision_repository.get_decision(item_id)
                admitidos_por_el_motor.add((KnowledgeKind.DECISION, item_id))
                ranked.append(
                    RankedKnowledge(
                        kind=KnowledgeKind.DECISION,
                        item=decision,
                        subject_matches_query=subject_matches_query(decision.subject, query_text),
                        project_matches_active=(
                            active_project_id is not None
                            and decision.project_id == active_project_id
                        ),
                        fts_match=True,
                        category_match=category_match(decision.category),
                    )
                )

        solo_por_categoria: list[RankedKnowledge] = []
        if self._category_matching_enabled and category_index_activated(
            query_text, self._category_vocabulary
        ):
            categorias = tuple(self._category_vocabulary)
            for memory in self._memory_repository.list_current_memories_by_category(categorias):
                if (KnowledgeKind.MEMORY, memory.id) in admitidos_por_el_motor:
                    continue
                if candidate_in_declared_scope(
                    memory.project_id, active_project_id=active_project_id
                ):
                    solo_por_categoria.append(
                        RankedKnowledge(
                            kind=KnowledgeKind.MEMORY,
                            item=memory,
                            subject_matches_query=False,
                            project_matches_active=(
                                active_project_id is not None
                                and memory.project_id == active_project_id
                            ),
                            fts_match=False,
                            category_match=True,
                        )
                    )
            for decision in self._decision_repository.list_current_decisions_by_category(
                categorias
            ):
                if (KnowledgeKind.DECISION, decision.id) in admitidos_por_el_motor:
                    continue
                if candidate_in_declared_scope(
                    decision.project_id, active_project_id=active_project_id
                ):
                    solo_por_categoria.append(
                        RankedKnowledge(
                            kind=KnowledgeKind.DECISION,
                            item=decision,
                            subject_matches_query=subject_matches_query(
                                decision.subject, query_text
                            ),
                            project_matches_active=(
                                active_project_id is not None
                                and decision.project_id == active_project_id
                            ),
                            fts_match=False,
                            category_match=True,
                        )
                    )

        return _intercalar_por_categoria(ranked, solo_por_categoria)

    def _rank_via_current_pipeline(self, query_text: str) -> tuple[RankedKnowledge, ...]:
        """El filtro-y-orden de S7.5/M9, sin cambios: lo que ``rank()``
        ejecutaba antes de esta incidencia y lo que sigue ejecutando con la
        puerta D7 punto 6 cerrada."""
        active_project = self._project_repository.get_active_project()
        active_project_id = active_project.id if active_project is not None else None

        fts_hits = self._knowledge_search_repository.search_knowledge(query_text)

        def category_match(category: str | None) -> bool:
            # D7 point 6's activation gate (§6.2/§6.3): closed by default,
            # and closed until docs/evolution/STATUS.md registers the
            # matching threshold — category_match must stay False for every
            # real candidate while it is, never compared at all.
            return self._category_matching_enabled and category_matches_query(
                category, query_text, self._category_vocabulary
            )

        candidates: list[RankedKnowledge] = [
            RankedKnowledge(
                kind=KnowledgeKind.MEMORY,
                item=memory,
                subject_matches_query=False,
                project_matches_active=(
                    active_project_id is not None and memory.project_id == active_project_id
                ),
                fts_match=(KnowledgeKind.MEMORY, memory.id) in fts_hits,
                category_match=category_match(memory.category),
            )
            for memory in self._memory_repository.list_current_memories()
        ]
        candidates.extend(
            RankedKnowledge(
                kind=KnowledgeKind.DECISION,
                item=decision,
                subject_matches_query=subject_matches_query(decision.subject, query_text),
                project_matches_active=(
                    active_project_id is not None and decision.project_id == active_project_id
                ),
                fts_match=(KnowledgeKind.DECISION, decision.id) in fts_hits,
                category_match=category_match(decision.category),
            )
            for decision in self._decision_repository.list_current_decisions()
        )

        return rank_relevant_knowledge(candidates)


def _intercalar_por_categoria(
    ranked: Sequence[RankedKnowledge], solo_por_categoria: Sequence[RankedKnowledge]
) -> tuple[RankedKnowledge, ...]:
    """Combina lo admitido por el motor por etapas con la ampliación de M9
    (CODEX-001, incidencia #457, tercera ronda) sin alterar la precedencia
    relativa que el motor ya adjudicó a ``ranked``.

    ``solo_por_categoria`` se ordena primero por su cuenta con el criterio
    S7.5/M9 de siempre. Después, una fusión de dos punteros recorre ambos
    bloques y en cada paso decide cuál va primero comparando únicamente el
    candidato actual de cada lado con ese mismo criterio
    (``rank_relevant_knowledge`` sobre el par) — nunca compara dos elementos
    de ``ranked`` entre sí, así que su orden de entrada nunca cambia. En
    empate gana ``ranked``: ``rank_relevant_knowledge`` es una ordenación
    estable y el par siempre se le pasa con el elemento de ``ranked``
    primero.
    """
    categoria = list(rank_relevant_knowledge(tuple(solo_por_categoria)))
    motor = list(ranked)
    intercalado: list[RankedKnowledge] = []
    i = j = 0
    while i < len(motor) and j < len(categoria):
        primero = rank_relevant_knowledge((motor[i], categoria[j]))[0]
        if primero is motor[i]:
            intercalado.append(motor[i])
            i += 1
        else:
            intercalado.append(categoria[j])
            j += 1
    intercalado.extend(motor[i:])
    intercalado.extend(categoria[j:])
    return tuple(intercalado)
