"""PA-0.2-REC-01: banco de 47 casos, línea base del pipeline actual (M7).

`tests/acceptance/fixtures/evidence_bank_47_casos.json` porta, sin
modificar ningún caso, resultado esperado ni adjudicación, el banco de 47
casos y sus 81 elementos esperados que PR #117 (`evidence/adr001-spikes`)
midió (Producto 0.2 §2.2/§3.2; Arquitectura Técnica 0.2 §6.5).

Este módulo ejecuta ese banco contra el pipeline de recuperación de `main`
tal como existe hoy — `RankRelevantKnowledgeUseCase.rank()` seguido de la
exclusión por precedencia que `ContextBuilder` ya aplica (B4e) — **sin**
índice de categoría (M8) ni filtro de relevancia (M9/M10). Lo que este
módulo fija es la medición: cuatro métricas agregadas sobre los 47 casos,
reportadas.

La incidencia #455 localizó, sobre este mismo pipeline, la causa por la que
el suelo de D1 (aciertos exactos ≥ 29/47) no se alcanzaba: `sanitize_fts5_query`
(B6a) unía todos los tokens de la consulta con `OR`, incluidas las palabras
vacías del castellano, así que casi cualquier consulta emparejaba con la
mayoría del canon (1/47, 2141 elementos de más). ADR-109 porta el
tratamiento léxico que cierra esa causa raíz
(`sirius.adapters.persistence.lexical_query_treatment`, desde
`experiments/adr002/candidates/adr002_a/lexical.py` en
`evidence/adr001-spikes`) y mide de nuevo: **10/47**, 218 elementos de más —
una mejora real y sustancial, pero todavía por debajo del suelo de D1. ADR-109
diagnostica, con desglose caso a caso, que la brecha restante no es ya de
cobertura (57/81, 70.4%) sino de precisión, y que cerrarla exige portar las
puertas `G1-G12` y la agrupación de equivalentes del motor por etapas del
laboratorio — fuera del alcance léxico que esa incidencia autoriza.

La incidencia #457 porta esas tres piezas —el resto del tratamiento léxico
(`polaridad_negativa`, `condicion_declarada`), las doce puertas
(`sirius.domain.staged_engine_gates`), la agrupación de equivalentes
(`sirius.domain.staged_engine_grouping`) y el motor que las orquesta
(`sirius.domain.staged_engine`)— y añade un segundo arnés,
`_ejecutar_banco_motor_portado`, que ejecuta el mismo banco con ese motor
activo (el mismo camino que `RankRelevantKnowledgeUseCase.
_rank_via_staged_engine` toma con la puerta D7 punto 6 abierta) en vez del
filtro-y-orden de M7. Con una política **uniforme** para las 47 consultas
(modo M1, cardinalidad EXHAUSTIVA, límite sin atar), mide: **11/47**, 186
elementos de más, 9 omisiones críticas, cobertura 60/81 (74.1%) — mejora
real en las cuatro métricas frente a M7, pero todavía muy por debajo de los
cuatro objetivos de la incidencia. ADR-110 diagnostica, con las cifras de
cada configuración probada, que la petición **por caso** (modo, permiso,
cardinalidad, límite) que el laboratorio usó para medir 29/47 vive en
ficheros (`experiments/adr002/benchmark/cases_v0_5.json`/
`references_v0_5.json`) y en un traductor
(`experiments/adr002/round/cases.py`) que el alcance permitido de la
incidencia #457 no autorizaba portar.

La incidencia #461 autoriza portar esa petición por caso: los campos
`peticion_p2` del fixture (verbatim de `cases_v0_5.json`/
`references_v0_5.json`), el traductor
(`tests/acceptance/staged_engine_case_translation.py`, portado de
`experiments/adr002/round/cases.py:334-366`), y el cableado de
`_ejecutar_banco_motor_portado` para construir la `Peticion` de cada caso
con esos campos en vez de la política uniforme de ADR-110. Mide: **23/47**,
90 elementos de más, 10 omisiones críticas, cobertura 63/81 (77.8%) — tres
de las cuatro métricas mejoran de forma sustancial frente a la política
uniforme (11/47, 186, 60/81), la cuarta (omisiones críticas) empeora en una
unidad (9 → 10); ninguna alcanza el suelo de D1 (aciertos exactos ≥ 29/47,
elementos de más ≤ 21, omisiones críticas ≤ 1). ADR-111 diagnostica, con
cita de fichero y línea, que la petición por caso ya es idéntica a la del
laboratorio (mismo traductor, mismos campos, mismo corpus) y que la brecha
restante no es de traducción: el propio 29/47 que la Definición de
Producto registra
(`docs/evolution/SIRIUS_PRODUCTO_0.2_MEMORIA_UTIL_v0.1_PROPUESTO.md:63-74`)
es el resultado conjunto del motor de búsqueda **con** el índice de
categoría (M8) **y** el filtro de relevancia con modelo local vía Ollama
(M9/M10) — "búsqueda sola" mide 24/47 en el laboratorio
(`experiments/adr002/modelo_local/filtro.py:76-89` en
`evidence/adr001-spikes`); el salto a 29/47 lo produce el filtro, no el
motor. Ninguna de esas dos piezas está en el alcance de esta incidencia ni
de la #457 anterior. Por eso D1/D2 siguen sin aserción de suelo aquí: D1 no
se alcanza con ninguno de los tres pipelines medidos (ADR-109/ADR-110/
ADR-111) y D2 es competencia de M11 sobre el pipeline íntegro que M8-M10
integren, no de este módulo — aunque la cifra de cobertura de este ADR
(63/81) ya alcanza, de forma aislada, el suelo provisional que D2 registra.

`criticidad.razon_segura` viaja en el fixture porque así la porta la rama de
evidencia, pero nunca se lee: el cargador que construye los `Memory`/
`Decision` reales (`_load_canon_item`) no toca `criticidad` en absoluto, y el
arnés de evaluación (`_es_critico`) solo lee `criticidad.nivel` para puntuar
la métrica de omisiones críticas. `test_el_cargador_no_lee_criticidad`
demuestra por construcción, no por convención, que el cargador nunca toca
`criticidad` (replica la garantía de
`experiments/adr002/candidates/test_adr002_categoria.py` en
`evidence/adr001-spikes`); `test_es_critico_lee_nivel_pero_nunca_razon_segura`
demuestra, con un caso controlado independiente de la ejecución real del
banco, que `_es_critico` lee `nivel` y nunca `razon_segura` — la ejecución
real del banco no siempre produce una omisión crítica (M12 puede cerrarlas
todas, ver `docs/evolution/SIRIUS_ARQUITECTURA_TECNICA_0.2_v0.1_PROPUESTO.md`
§8 M12), así que esa garantía no puede depender de que aparezca una.
"""

from __future__ import annotations

import json
import os
from collections.abc import Iterator, Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Final

import pytest
from staged_engine_case_translation import peticion_desde_caso
from staged_engine_category_and_relevance import (
    CATEGORIA_DE_MAXIMA_CRITICIDAD,
    VOCABULARIO_DE_CATEGORIA,
    activa_categoria_buscable,
    aplicar_candado,
    aplicar_regla_de_criticas_original,
    categoria_del_item,
    filtro_congelado_conserva,
    indice_de_categoria,
    siembra_de_contexto,
)

from sirius.adapters.ollama_relevance_filter import OllamaRelevanceFilterAdapter
from sirius.adapters.persistence import staged_engine_candidate
from sirius.adapters.persistence.database import build_engine, build_session_factory
from sirius.adapters.persistence.migrations import upgrade_to_head
from sirius.adapters.persistence.sqlite_decision_repository import (
    build_sqlite_decision_repository,
)
from sirius.adapters.persistence.sqlite_knowledge_search_repository import (
    build_sqlite_knowledge_search_repository,
)
from sirius.adapters.persistence.sqlite_memory_repository import build_sqlite_memory_repository
from sirius.adapters.persistence.sqlite_project_repository import build_sqlite_project_repository
from sirius.adapters.persistence.sqlite_unit_of_work import build_sqlite_unit_of_work
from sirius.adapters.persistence.staged_engine_port import StagedEnginePort
from sirius.application.approve_decision import ApproveDecisionUseCase
from sirius.application.archive_memory import ArchiveMemoryUseCase
from sirius.application.propose_decision import ProposeDecisionUseCase
from sirius.application.rank_relevant_knowledge import RankRelevantKnowledgeUseCase
from sirius.application.save_manual_memory import SaveManualMemoryUseCase
from sirius.domain.memory import Memory, MemoryRevision, MemoryStatus
from sirius.domain.precedence import find_prevailing_decision
from sirius.domain.relevance import KnowledgeKind, RankedKnowledge, category_matches_query
from sirius.domain.staged_engine import recuperar
from sirius.domain.staged_engine_contracts import (
    Ambito,
    Clase,
    Criticidad,
    CriticidadAplicada,
    EjesDeclarados,
)

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "evidence_bank_47_casos.json"

#: Medición actual publicada en el docstring de
#: `test_el_banco_se_ejecuta_contra_el_pipeline_actual_y_reporta_las_cuatro_metricas`
#: (M7, incidencia #455/ADR-109). CODEX-003: cotas unidireccionales de no
#: regresión, no el suelo de D1 (29/47) que esta incidencia no alcanza.
_MINIMO_ACIERTOS_EXACTOS_M7: Final[int] = 10
_MAXIMO_ELEMENTOS_DE_MAS_M7: Final[int] = 218
_MAXIMO_OMISIONES_CRITICAS_M7: Final[int] = 10
_MINIMO_ELEMENTOS_HALLADOS_M7: Final[int] = 57

#: Medición actual publicada en el docstring de
#: `test_el_banco_se_ejecuta_contra_el_motor_portado_y_reporta_las_cuatro_metricas`
#: (motor por etapas con petición por caso, categoría buscable, regla de las
#: críticas original y siembra al ensamblar contexto — incidencia #465,
#: ADR-113). Misma convención de cotas unidireccionales de no regresión, no
#: el suelo de D1 (29/47, ≤21, ≤1, ≥63/81) que ADR-113 diagnostica que
#: `aciertos_exactos` y `elementos_de_mas` todavía no alcanzan — aunque
#: `omisiones_criticas` y `cobertura` sí lo alcanzan (0 ≤ 1, 63/81 ≥ 63/81).
_MINIMO_ACIERTOS_EXACTOS_MOTOR: Final[int] = 27
_MAXIMO_ELEMENTOS_DE_MAS_MOTOR: Final[int] = 110
_MAXIMO_OMISIONES_CRITICAS_MOTOR: Final[int] = 0
_MINIMO_ELEMENTOS_HALLADOS_MOTOR: Final[int] = 63

pytestmark = [pytest.mark.acceptance, pytest.mark.integration]


def _fixture() -> Mapping[str, Any]:
    banco: Mapping[str, Any] = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    return banco


# -- Cargador: nunca toca `criticidad` ---------------------------------------


def _vigente(item: Mapping[str, Any]) -> bool:
    """Un item del canon es vigente si sus tres estados lo dicen a la vez.

    Nunca mira `criticidad`: la vigencia de un `Memory`/`Decision` real de
    Sirius es asunto de `confirmacion`/`validez`/`disponibilidad`, no de si
    el elemento importa. Mezclarlas dejaría un elemento crítico entrar solo
    por serlo, que es justo la trampa que D1 prohíbe.
    """
    return bool(
        item["confirmacion"] == "CONFIRMADA"
        and item["validez"] == "VIGENTE"
        and item["disponibilidad"] == "DISPONIBLE"
    )


def _load_canon_item(
    item: Mapping[str, Any],
    *,
    project_ids: Mapping[str, int],
    unit_of_work: Any,
) -> tuple[str, int] | None:
    """Crea el `Memory`/`Decision` real de un item del canon portado, o
    `None` si el canon lo declara sin contenido persistible (una memoria
    `PURGADA`/`NO_GUARDADA` porta texto vacío a propósito: nunca llegó a
    existir como contenido real, y `SaveManualMemoryUseCase` rechaza
    contenido vacío igual que rechazaría cualquier otro guardado en blanco).
    Ninguno de los dos casos del banco con texto vacío aparece en ningún
    `resultado_esperado`, así que no crearlos no cambia ninguna métrica.

    El cargador que alimenta el pipeline bajo prueba: solo lee `id`, `kind`,
    `project`, `text`, `confirmacion`, `validez` y `disponibilidad`. Nunca
    lee `criticidad` — ni `nivel` ni `razon_segura` — porque ninguno de los
    dos puertos reales (`MemoryRepository`/`DecisionRepository`) tiene ese
    campo hoy: solo el arnés de evaluación de más abajo lo necesita, y por
    separado.
    """
    project_name = item["project"]
    project_id = None if project_name == "PRJ-GLOBAL" else project_ids[project_name]
    text = item["text"]
    if item["kind"] == "MEMORIA":
        if not text.strip():
            return None
        memory = SaveManualMemoryUseCase(unit_of_work).save(text, project_id=project_id)
        if not _vigente(item):
            ArchiveMemoryUseCase(unit_of_work).archive(memory.id)
        return ("memory", memory.id)
    assert item["kind"] == "DECISION"
    assert project_id is not None
    decision = ProposeDecisionUseCase(unit_of_work).propose(text, project_id, text)
    if _vigente(item):
        ApproveDecisionUseCase(unit_of_work).approve(decision.id, confirmed=True)
    return ("decision", decision.id)


def _create_projects(database_path: Path, names: list[str]) -> dict[str, int]:
    """Un `Project` real por cada proyecto del canon (salvo `PRJ-GLOBAL`,
    que se traduce como `project_id=None`, ver `_load_canon_item`).

    Solo puede haber un proyecto `ACTIVE` a la vez, así que cada uno se
    completa antes de crear el siguiente; el último queda activo. Cuál quede
    activo no importa para las cuatro métricas: el pipeline de hoy nunca usa
    el proyecto activo para filtrar, solo como criterio de desempate en el
    orden (`sirius.domain.relevance._sort_key`), y ninguna de las cuatro
    métricas de este módulo mira el orden.
    """
    project_repository = build_sqlite_project_repository(database_path)
    project_repository.ensure_bootstrap_project()
    project_ids: dict[str, int] = {}
    for name in names:
        project = project_repository.create_project(
            name, "objetivo del banco portado", state_summary="", blockers=(), next_step=""
        )
        project_ids[name] = project.id
        if name != names[-1]:
            project_repository.complete_active_project(project.id)
    return project_ids


class _TrackingMapping(Mapping[str, Any]):
    """Envoltorio de solo lectura que registra qué claves se piden, incluso
    dentro de sub-diccionarios anidados (`criticidad.nivel` se registra como
    la ruta ``("criticidad", "nivel")``). Réplica del espía que
    `experiments/adr002/candidates/test_adr002_categoria.py` usa en
    `evidence/adr001-spikes` para demostrar la misma exclusión."""

    def __init__(
        self, data: Mapping[str, Any], log: list[tuple[str, ...]], prefix: tuple[str, ...] = ()
    ) -> None:
        self._data = data
        self._log = log
        self._prefix = prefix

    def __getitem__(self, key: str) -> Any:
        self._log.append((*self._prefix, key))
        value = self._data[key]
        if isinstance(value, Mapping):
            return _TrackingMapping(value, self._log, (*self._prefix, key))
        return value

    def __iter__(self) -> Iterator[str]:
        return iter(self._data)

    def __len__(self) -> int:
        return len(self._data)


# -- Arnés de evaluación: las cuatro métricas del §6.5 -----------------------


def _es_critico(item: Mapping[str, Any]) -> bool:
    """Si un item esperado es crítico. Único lugar del módulo que lee
    `criticidad`, y únicamente su `nivel`: `razon_segura` nunca se pide."""
    criticidad = item.get("criticidad")
    return criticidad is not None and criticidad["nivel"] == "CRITICO"


@dataclass(frozen=True, slots=True)
class _Metricas:
    aciertos_exactos: int
    elementos_de_mas: int
    omisiones_criticas: int
    elementos_hallados: int
    elementos_esperados_total: int

    @property
    def cobertura(self) -> float:
        return self.elementos_hallados / self.elementos_esperados_total


@dataclass(frozen=True, slots=True)
class _EjecucionDelBanco:
    metricas: _Metricas
    accesos_del_cargador: list[tuple[str, ...]] = field(default_factory=list)
    accesos_del_arnes: list[tuple[str, ...]] = field(default_factory=list)


def _ejecutar_banco(database_path: Path) -> _EjecucionDelBanco:
    banco = _fixture()
    upgrade_to_head(database_path)

    nombres_de_proyecto = sorted(
        {i["project"] for i in banco["items"] if i["project"] != "PRJ-GLOBAL"}
    )
    project_ids = _create_projects(database_path, nombres_de_proyecto)

    unit_of_work = build_sqlite_unit_of_work(database_path)
    accesos_del_cargador: list[tuple[str, ...]] = []
    real_a_canonico: dict[tuple[str, int], str] = {}
    for item in banco["items"]:
        vigilado = _TrackingMapping(item, accesos_del_cargador)
        real = _load_canon_item(vigilado, project_ids=project_ids, unit_of_work=unit_of_work)
        if real is None:
            continue
        real_a_canonico[real] = item["id"]

    use_case = RankRelevantKnowledgeUseCase(
        memory_repository=build_sqlite_memory_repository(database_path),
        decision_repository=build_sqlite_decision_repository(database_path),
        project_repository=build_sqlite_project_repository(database_path),
        knowledge_search_repository=build_sqlite_knowledge_search_repository(database_path),
    )
    decision_repository = build_sqlite_decision_repository(database_path)

    def excluido_por_precedencia(candidato: RankedKnowledge, decisiones: list[Any]) -> bool:
        """El mismo filtro que `ContextBuilder._excluded_by_precedence`
        (B4e) aplica hoy tras `rank()`: sin índice de categoría ni filtro de
        relevancia todavía, es la única etapa adicional que el pipeline
        actual de `main` añade sobre `rank()` puro."""
        if candidato.kind is not KnowledgeKind.MEMORY:
            return False
        memoria = candidato.item
        assert isinstance(memoria, Memory)
        if memoria.subject_key is None or memoria.project_id is None:
            return False
        return (
            find_prevailing_decision(memoria.subject_key, memoria.project_id, decisiones)
            is not None
        )

    accesos_del_arnes: list[tuple[str, ...]] = []
    items_por_id = {item["id"]: item for item in banco["items"]}

    aciertos_exactos = 0
    elementos_de_mas = 0
    omisiones_criticas = 0
    elementos_hallados = 0

    for caso in banco["casos"]:
        decisiones_vigentes = decision_repository.list_current_decisions()
        obtenido_ranked = tuple(
            candidato
            for candidato in use_case.rank(caso["consulta"])
            if not excluido_por_precedencia(candidato, decisiones_vigentes)
        )
        obtenido = {
            real_a_canonico[(candidato.kind.value, candidato.item_id)]
            for candidato in obtenido_ranked
        }
        esperado = set(caso["resultado_esperado"])

        if obtenido == esperado:
            aciertos_exactos += 1
        elementos_de_mas += len(obtenido - esperado)
        elementos_hallados += len(obtenido & esperado)
        for identidad in esperado - obtenido:
            vigilado = _TrackingMapping(items_por_id[identidad], accesos_del_arnes)
            if _es_critico(vigilado):
                omisiones_criticas += 1

    metricas = _Metricas(
        aciertos_exactos=aciertos_exactos,
        elementos_de_mas=elementos_de_mas,
        omisiones_criticas=omisiones_criticas,
        elementos_hallados=elementos_hallados,
        elementos_esperados_total=banco["conteos"]["elementos_esperados_total"],
    )
    return _EjecucionDelBanco(
        metricas=metricas,
        accesos_del_cargador=accesos_del_cargador,
        accesos_del_arnes=accesos_del_arnes,
    )


@pytest.fixture(scope="module")
def ejecucion_del_banco(tmp_path_factory: pytest.TempPathFactory) -> _EjecucionDelBanco:
    database_path = tmp_path_factory.mktemp("evidence_bank_47_casos") / "sirius.db"
    return _ejecutar_banco(database_path)


# -- Arnés del motor por etapas (incidencia #457/ADR-109) --------------------


#: Traducción cerrada del vocabulario de niveles del fixture (idéntica a la
#: que `experiments/adr002/projection/plane.py` aplica en
#: `evidence/adr001-spikes`, `NIVELES`): un nivel del fixture que no figure
#: aquí no debe traducirse "al más parecido". El fixture nunca declara el
#: nivel `ORDINARIO` explícito (`criticidad` es `None` para todo lo que no
#: es `IMPORTANTE` ni `CRITICO`), así que no hace falta esa entrada.
_NIVELES_DE_CRITICIDAD: Final[dict[str, Criticidad]] = {
    "IMPORTANTE": Criticidad.IMPORTANTE,
    "CRITICO": Criticidad.CRITICA,
}

#: Sustituto fijo, ajeno al corpus, del `razon_segura` que el motor exige
#: para construir `CriticidadAplicada` (incidencia #457: "el corpus sigue
#: intocable y criticidad.razon_segura sin leerse jamás"). El motor decide
#: por `nivel`, nunca por `razon_segura` (viaja íntegro solo hasta la
#: explicación/traza), así que este valor fijo no cambia ninguna métrica.
_RAZON_SEGURA_NO_LEIDA_DEL_CORPUS: Final[str] = (
    "no leído del corpus: incidencia #457 prohíbe leer criticidad.razon_segura"
)


def _identidad_del_motor(kind: str, real_id: int) -> str:
    """La identidad `CLASE:n` que `StagedEnginePort`/`ItemCanonico` usan,
    construida desde el mismo par `(kind, id)` que `_load_canon_item`
    devuelve y que `real_a_canonico` ya indexa."""
    clase = Clase.MEMORIA.value if kind == "memory" else Clase.DECISION.value
    return f"{clase}:{real_id}"


def _ejes_declarados(item: Mapping[str, Any]) -> EjesDeclarados:
    """Los ejes P2 que el ítem del corpus congelado declara (ver
    `ejes_p2` en el fixture, incidencia #457): el mismo eje que
    `staged_engine_gates` necesita, tal como el corpus lo fija."""
    ejes = item["ejes_p2"]
    return EjesDeclarados(
        confirmacion=item["confirmacion"],
        validez=item["validez"],
        disponibilidad=item["disponibilidad"],
        valid_from=ejes["valid_from"],
        valid_to=ejes["valid_to"],
        sensibilidad=ejes["sensibilidad"],
        autoridad=ejes["autoridad"],
        ambito=ejes["ambito"],
        no_usar_como_memoria=ejes["no_usar_como_memoria"],
        no_consolidable=ejes["no_consolidable"],
        procedencia=tuple(ejes["procedencia"]),
        # La única decisión `MULTI_PROYECTO_CERRADO` del banco (`DEC-001`)
        # no trae miembros resueltos: el corpus portado no declara la
        # membresía de listas cerradas del laboratorio (ver
        # "nota_incidencia_457" del fixture). `G4` la trata como lista sin
        # miembros y la descarta ("la duda no abre ámbito"), en vez de que
        # este arnés invente una membresía que no está en la fuente.
        miembros_de_ambito=(),
    )


class _PlanoDelBanco:
    """`PlanoComun` del arnés: `property_key` y criticidad aplicada, las
    dos leídas del corpus congelado (`ejes_p2.property_key`, `criticidad`)
    — nunca calculadas ni inferidas por este módulo."""

    def __init__(
        self,
        propiedades: Mapping[str, str | None],
        criticidad: Mapping[str, CriticidadAplicada],
    ) -> None:
        self._propiedades = propiedades
        self._criticidad = criticidad

    def property_key(self, identidad: str) -> str | None:
        return self._propiedades.get(identidad)

    def criticidad_aplicada(self, identidad: str) -> CriticidadAplicada | None:
        return self._criticidad.get(identidad)


def _ejecutar_banco_motor_portado(database_path: Path) -> _EjecucionDelBanco:
    """El mismo banco de 47 casos, con el motor por etapas (ADR-109) activo
    en el arnés — el mismo camino que
    `RankRelevantKnowledgeUseCase._rank_via_staged_engine` toma con la
    puerta D7 punto 6 abierta — en vez del filtro-y-orden de M7 que
    `_ejecutar_banco` mide.

    Construye el canon exactamente igual que `_ejecutar_banco` (mismos
    `Memory`/`Decision` reales, por los mismos casos de uso), y añade lo que
    el motor por etapas necesita y que el esquema real de Sirius 0.1 no
    persiste: los ejes P2, `property_key` y la criticidad aplicada, los tres
    leídos del corpus congelado que `evidence_bank_47_casos.json` porta
    (incidencia #457) — nunca inventados por este arnés.

    Cada caso interroga al motor con su propia petición **por caso**
    (incidencia #461/ADR-111): modo, propósito, permiso, cardinalidad,
    límite y tiempo objetivo, los mismos campos que
    `experiments/adr002/round/cases.py:334-366` traduce en el laboratorio,
    portados verbatim al fixture bajo `peticion_p2` y traducidos aquí por
    `tests.acceptance.staged_engine_case_translation.peticion_desde_caso` —
    no una política uniforme para las 47 consultas (la que ADR-110 medía).
    El ámbito sigue resolviéndose contra el propio caso
    (`caso["ambito"]`, portado desde `cases_v0_5.json` — `GLOBAL` o el
    nombre de un proyecto del banco), no un ámbito global uniforme: es la
    puerta `G4` la que debe decidir si un ítem de otro proyecto cuenta como
    elemento de más, no un filtro añadido por este arnés.

    Incidencia #463: tras lo que el motor admite, este arnés activa las dos
    piezas que el laboratorio usaba junto al motor para medir 29/47 — el
    índice de categoría (M9, §6.2) y el filtro de relevancia con su candado
    (M10, §6.3) —, ambas ya portadas a `main` como código de producto detrás
    de la misma puerta `category_matching_enabled` que ADR-109/110/111 ya
    citaban cerrada. Solo este arnés las invoca; la puerta sigue cerrada
    para `Memory`/`Decision` reales (`sirius.application.
    rank_relevant_knowledge`, sin cambios). Ver
    `tests.acceptance.staged_engine_category_and_relevance` para el porqué de
    cada pieza y ADR-112 para la medición y su diagnóstico.
    """
    banco = _fixture()
    upgrade_to_head(database_path)

    nombres_de_proyecto = sorted(
        {i["project"] for i in banco["items"] if i["project"] != "PRJ-GLOBAL"}
    )
    project_ids = _create_projects(database_path, nombres_de_proyecto)

    unit_of_work = build_sqlite_unit_of_work(database_path)
    real_a_canonico: dict[tuple[str, int], str] = {}
    for item in banco["items"]:
        real = _load_canon_item(item, project_ids=project_ids, unit_of_work=unit_of_work)
        if real is None:
            continue
        real_a_canonico[real] = item["id"]

    items_por_id = {item["id"]: item for item in banco["items"]}
    #: M9 (§6.2): la categoría de cada item vigente y realmente creado, por
    #: identidad canónica del corpus (no la del motor: el índice de
    #: categoría y el candado operan sobre el mismo espacio de identidades
    #: que `obtenido`/`esperado`). Solo vigentes: `RankRelevantKnowledgeUse
    #: Case._rank_via_staged_engine` amplía sobre `list_current_memories`/
    #: `list_current_decisions`, nunca sobre lo archivado o no aprobado.
    categoria_por_identidad: dict[str, str | None] = {
        corpus_id: categoria_del_item(items_por_id[corpus_id])
        for corpus_id in real_a_canonico.values()
        if _vigente(items_por_id[corpus_id])
    }
    #: Incidencia #465, causa 2 (siembra al ensamblar contexto): el proyecto
    #: de cada identidad vigente, en el mismo espacio de identidades que
    #: `categoria_por_identidad` — nunca calculado, leído del corpus.
    proyecto_por_identidad: dict[str, str] = {
        corpus_id: items_por_id[corpus_id]["project"]
        for corpus_id in real_a_canonico.values()
        if _vigente(items_por_id[corpus_id])
    }
    ejes_por_identidad: dict[str, EjesDeclarados] = {}
    propiedades: dict[str, str | None] = {}
    criticidad_aplicada: dict[str, CriticidadAplicada] = {}
    accesos_del_motor_portado: list[tuple[str, ...]] = []
    for (kind, real_id), corpus_id in real_a_canonico.items():
        identidad = _identidad_del_motor(kind, real_id)
        item = _TrackingMapping(items_por_id[corpus_id], accesos_del_motor_portado)
        ejes_por_identidad[identidad] = _ejes_declarados(item)
        propiedades[identidad] = item["ejes_p2"]["property_key"]
        nivel_bruto = item["criticidad"]["nivel"] if item["criticidad"] else None
        if nivel_bruto is not None:
            criticidad_aplicada[identidad] = CriticidadAplicada(
                nivel=_NIVELES_DE_CRITICIDAD[nivel_bruto],
                # incidencia #457: "el corpus sigue intocable y
                # criticidad.razon_segura sin leerse jamás" — este arnés
                # nunca pide item["criticidad"]["razon_segura"]; el motor
                # solo necesita el campo para construirse (ver
                # `CriticidadAplicada`), no para decidir nada (decide por
                # `nivel`), así que un valor fijo ajeno al corpus lo satisface.
                razon_segura=_RAZON_SEGURA_NO_LEIDA_DEL_CORPUS,
                fuente_de_politica=item["criticidad"]["fuente_de_politica"],
                regla_de_politica=item["criticidad"]["regla_de_politica"],
            )

    engine = build_engine(database_path)
    session_factory = build_session_factory(engine)
    puerto = StagedEnginePort(session_factory, engine, ejes_por_identidad=ejes_por_identidad)
    candidato = staged_engine_candidate.candidato()
    plano = _PlanoDelBanco(propiedades, criticidad_aplicada)

    #: "Un límite que no ata" (misma convención que
    #: `experiments/adr002/round/cases.py`): el tamaño del canon, para que
    #: nunca sea la causa de que algo se omita.
    limite_sin_atar = banco["conteos"]["items_del_canon"]

    aciertos_exactos = 0
    elementos_de_mas = 0
    omisiones_criticas = 0
    elementos_hallados = 0

    try:
        for caso in banco["casos"]:
            ambito_declarado = caso["ambito"]
            ambito = (
                Ambito(global_=True, proyectos=())
                if ambito_declarado == "GLOBAL"
                else Ambito(global_=False, proyectos=(str(project_ids[ambito_declarado]),))
            )
            peticion = peticion_desde_caso(
                caso,
                operation_id=f"banco:{caso['id']}",
                ambito=ambito,
                limite_sin_atar=limite_sin_atar,
            )
            recuperacion = recuperar(peticion, puerto, candidato, plano)
            obtenido_por_el_motor = {
                real_a_canonico[
                    (
                        "memory" if resultado.item.clase is Clase.MEMORIA else "decision",
                        int(resultado.item.id.partition(":")[2]),
                    )
                ]
                for resultado in recuperacion.resultados
            }
            # Incidencia #463/#465: índice de categoría (M9, con la
            # semántica de la «categoría buscable» de la PR #117, causa 1)
            # primero, ampliando sobre lo que el motor no admitió; siembra al
            # ensamblar contexto (causa 2) después, sobre lo que el índice de
            # categoría tampoco admitió; filtro de relevancia con la regla de
            # las críticas ORIGINAL del laboratorio (RF-25/RF-26, causa 1)
            # al final — mismo orden que `ContextBuilder._rank_related_
            # knowledge` (precedencia/motor, después M9 vía `rank()`,
            # después M10), con las dos piezas del arnés que #465 autoriza
            # en vez de la semántica estricta de M9 y el candado de M10.
            obtenido_tras_categoria = obtenido_por_el_motor | indice_de_categoria(
                consulta=caso["consulta"],
                ya_admitidos=obtenido_por_el_motor,
                categoria_por_identidad=categoria_por_identidad,
            )
            obtenido_tras_siembra = obtenido_tras_categoria | siembra_de_contexto(
                proposito=peticion.proposito,
                ambito_declarado=ambito_declarado,
                ya_admitidos=obtenido_tras_categoria,
                categoria_por_identidad=categoria_por_identidad,
                proyecto_por_identidad=proyecto_por_identidad,
            )
            obtenido = aplicar_regla_de_criticas_original(
                caso_id=caso["id"],
                candidatos=obtenido_tras_siembra,
                categoria_por_identidad=categoria_por_identidad,
            )
            esperado = set(caso["resultado_esperado"])

            if obtenido == esperado:
                aciertos_exactos += 1
            elementos_de_mas += len(obtenido - esperado)
            elementos_hallados += len(obtenido & esperado)
            for identidad in esperado - obtenido:
                if _es_critico(items_por_id[identidad]):
                    omisiones_criticas += 1
    finally:
        puerto.close()

    metricas = _Metricas(
        aciertos_exactos=aciertos_exactos,
        elementos_de_mas=elementos_de_mas,
        omisiones_criticas=omisiones_criticas,
        elementos_hallados=elementos_hallados,
        elementos_esperados_total=banco["conteos"]["elementos_esperados_total"],
    )
    return _EjecucionDelBanco(metricas=metricas, accesos_del_arnes=accesos_del_motor_portado)


@pytest.fixture(scope="module")
def ejecucion_del_banco_motor_portado(
    tmp_path_factory: pytest.TempPathFactory,
) -> _EjecucionDelBanco:
    database_path = tmp_path_factory.mktemp("evidence_bank_47_casos_motor") / "sirius.db"
    return _ejecutar_banco_motor_portado(database_path)


def test_el_fichero_de_forma_tiene_47_casos_y_81_elementos_esperados() -> None:
    banco = _fixture()
    casos = banco["casos"]
    assert len(casos) == 47
    assert len({caso["id"] for caso in casos}) == 47

    total_esperado = sum(len(caso["resultado_esperado"]) for caso in casos)
    assert total_esperado == 81
    assert banco["conteos"] == {
        "casos": 47,
        "elementos_esperados_total": 81,
        "items_del_canon": 97,
    }

    identidades_del_canon = {item["id"] for item in banco["items"]}
    for caso in casos:
        for identidad in caso["resultado_esperado"]:
            assert identidad in identidades_del_canon


#: ADR-111: los cinco casos cuyo dominio adjudicado declara `limite`.
_CASOS_CON_LIMITE_DECLARADO: Final[frozenset[str]] = frozenset(
    {"B04-CA-26", "B04-CA-30", "B04-CA-34", "B04-CA-38", "B04-CA-44"}
)


def test_el_fichero_de_forma_tiene_42_limites_null_y_5_declarados() -> None:
    """CODEX-001/CLAUDE-SIRIUS-461-001: la nota de procedencia del fixture
    (`metadata.nota_incidencia_461`) afirma que 42 de los 47 casos tienen
    `peticion_p2.limite` null. Fija ambos conteos en una prueba de forma
    para que la evidencia congelada no vuelva a contradecir su propia
    documentación: los cinco casos que sí lo declaran son, verbatim, los
    que ADR-111 nombra."""
    banco = _fixture()
    casos = banco["casos"]

    con_limite = {caso["id"] for caso in casos if caso["peticion_p2"]["limite"] is not None}
    assert con_limite == _CASOS_CON_LIMITE_DECLARADO
    assert len(casos) - len(con_limite) == 42


def test_peticion_desde_caso_propaga_objetivos_de_exacta() -> None:
    """CODEX-002: un caso de cardinalidad `EXACTA` con más de un elemento
    esperado debe transportar esa cuota a `Peticion.objetivos`, no
    quedarse en el valor por defecto (1) — si no,
    `_suficiente`/`evaluar_suficiencia` (`sirius.domain.staged_engine`)
    detienen la expansión en cuanto aparece el primer grupo semántico,
    aunque el caso pida más."""
    banco = _fixture()
    casos_por_id = {caso["id"]: caso for caso in banco["casos"]}
    ambito = Ambito(global_=True, proyectos=())
    limite_sin_atar = banco["conteos"]["items_del_canon"]

    casos_exacta_con_varios_objetivos = {
        "B04-CA-19": 3,
        "B04-CA-23": 2,
        "B04-CA-43": 2,
    }
    for identidad, objetivos_esperados in casos_exacta_con_varios_objetivos.items():
        caso = casos_por_id[identidad]
        assert caso["peticion_p2"]["cardinalidad"] == "EXACTA"
        assert len(caso["resultado_esperado"]) == objetivos_esperados
        peticion = peticion_desde_caso(
            caso, operation_id="test", ambito=ambito, limite_sin_atar=limite_sin_atar
        )
        assert peticion.objetivos == objetivos_esperados

    # Un caso EXACTA de un único objetivo sigue en el valor histórico (1).
    caso_unico = casos_por_id["B04-CA-01"]
    assert caso_unico["peticion_p2"]["cardinalidad"] == "EXACTA"
    assert len(caso_unico["resultado_esperado"]) == 1
    peticion_unica = peticion_desde_caso(
        caso_unico, operation_id="test", ambito=ambito, limite_sin_atar=limite_sin_atar
    )
    assert peticion_unica.objetivos == 1

    # Una cardinalidad no EXACTA no usa `objetivos` (`_suficiente` nunca lo
    # consulta fuera de EXACTA); el traductor conserva el valor por defecto.
    caso_exhaustiva = casos_por_id["B04-CA-02"]
    assert caso_exhaustiva["peticion_p2"]["cardinalidad"] == "EXHAUSTIVA"
    peticion_exhaustiva = peticion_desde_caso(
        caso_exhaustiva, operation_id="test", ambito=ambito, limite_sin_atar=limite_sin_atar
    )
    assert peticion_exhaustiva.objetivos == 1


#: CODEX-001: los diez casos `EXACTA` cuyo `resultado_esperado` está vacío.
_CASOS_EXACTA_SIN_RESULTADO_ESPERADO: Final[frozenset[str]] = frozenset(
    {
        "B04-CA-04",
        "B04-CA-09",
        "B04-CA-10",
        "B04-CA-12",
        "B04-CA-15",
        "B04-CA-18",
        "B04-CA-24",
        "B04-CA-35",
        "B04-CA-46",
        "B04-CA-49",
    }
)


def test_peticion_desde_caso_no_asigna_cuota_cero_a_exacta_sin_resultado() -> None:
    """CODEX-001: diez casos `EXACTA` declaran `resultado_esperado=[]`, no
    solo los tres multiobjetivo que ADR-111 describe. `len([])` los dejaría
    en `objetivos=0`, y `_suficiente`/`evaluar_suficiencia`
    (`sirius.domain.staged_engine`) declaran esa cuota cumplida de forma
    trivial (`0 >= 0`) nada más terminar la primera etapa, deteniendo la
    expansión antes de recorrer las etapas que sí recorre cualquier otro
    caso — una divergencia de `_traducir` (que nunca adjudica una cuota,
    ni cero) que ADR-111 no documentaba ni esta prueba cubría. El traductor
    conserva el suelo histórico (1) para estos diez casos en vez de
    `len(resultado_esperado)`."""
    banco = _fixture()
    casos_por_id = {caso["id"]: caso for caso in banco["casos"]}
    ambito = Ambito(global_=True, proyectos=())
    limite_sin_atar = banco["conteos"]["items_del_canon"]

    casos_exacta_sin_resultado = {
        caso["id"]
        for caso in banco["casos"]
        if caso["peticion_p2"]["cardinalidad"] == "EXACTA" and not caso["resultado_esperado"]
    }
    assert casos_exacta_sin_resultado == _CASOS_EXACTA_SIN_RESULTADO_ESPERADO

    for identidad in _CASOS_EXACTA_SIN_RESULTADO_ESPERADO:
        caso = casos_por_id[identidad]
        peticion = peticion_desde_caso(
            caso, operation_id="test", ambito=ambito, limite_sin_atar=limite_sin_atar
        )
        assert peticion.objetivos == 1


def test_el_banco_se_ejecuta_contra_el_pipeline_actual_y_reporta_las_cuatro_metricas(
    ejecucion_del_banco: _EjecucionDelBanco,
) -> None:
    """M7 pipeline, con el disparador FTS5 ya corregido (incidencia #455,
    ADR-109): ``sanitize_fts5_query`` limpia la consulta de palabras vacías
    del castellano y la empareja por raíces/variantes en vez de por ``OR`` de
    todos sus tokens. Medido: aciertos_exactos=10/47, elementos_de_mas=218,
    omisiones_criticas=10, cobertura=57/81 (70.4%) — una mejora real y
    sustancial frente a la línea base medida antes del porte (1/47, 2141, 21,
    51/81), pero todavía por debajo del suelo de D1 (aciertos exactos ≥ 29/47).

    El suelo de D1 **no** queda afirmado aquí como aserción dura: ADR-109
    diagnostica, con desglose caso a caso, que la brecha restante ya no es
    de cobertura sino de precisión (27 de los 37 casos fallidos encuentran
    el 100% de lo esperado y solo fallan por elementos de más), y que
    cerrarla exige portar las puertas `G1-G12` y la agrupación de
    equivalentes del motor por etapas del laboratorio —fuera del alcance
    léxico de la incidencia que corrigió `sanitize_fts5_query`—, no una
    corrección adicional de ese disparador. Afirmar 29/47 dejaría
    `uv run pytest` en rojo; debilitarlo a 10 falsearía la prueba
    declarando cumplido un suelo que D1 fija en 29, no en "lo que se mida"
    (a diferencia de D2). Queda medido y publicado, nunca exigido, hasta
    que el propietario decida cómo cerrar esa brecha (ADR-109)."""
    metricas = ejecucion_del_banco.metricas

    print(
        "\nPA-0.2-REC-01 (M7, disparador FTS5 corregido para la incidencia "
        "#455 (ADR-109); "
        "sin índice de categoría ni filtro de relevancia): "
        f"aciertos_exactos={metricas.aciertos_exactos}/47 "
        f"elementos_de_mas={metricas.elementos_de_mas} "
        f"omisiones_criticas={metricas.omisiones_criticas} "
        f"cobertura={metricas.elementos_hallados}/{metricas.elementos_esperados_total} "
        f"({metricas.cobertura:.1%})"
    )

    # CODEX-003: cotas unidireccionales de no regresión sobre la medición ya
    # publicada arriba (10/47, 218, 10, 57/81) — no el suelo de D1 (29/47),
    # que esta incidencia sigue sin alcanzar. Una modificación que rompiera
    # el pipeline debe dejar este banco en rojo, no en verde con cifras
    # falseadas.
    assert metricas.aciertos_exactos >= _MINIMO_ACIERTOS_EXACTOS_M7
    assert metricas.elementos_de_mas <= _MAXIMO_ELEMENTOS_DE_MAS_M7
    assert metricas.omisiones_criticas <= _MAXIMO_OMISIONES_CRITICAS_M7
    assert metricas.elementos_hallados >= _MINIMO_ELEMENTOS_HALLADOS_M7


def test_el_banco_se_ejecuta_contra_el_motor_portado_y_reporta_las_cuatro_metricas(
    ejecucion_del_banco_motor_portado: _EjecucionDelBanco,
) -> None:
    """Incidencia #457/#461/#463/#465/ADR-109/ADR-110/ADR-111/ADR-112/
    ADR-113: el mismo banco, con el motor por etapas
    (`sirius.domain.staged_engine.recuperar`), las doce puertas
    (`staged_engine_gates`), la agrupación de equivalentes
    (`staged_engine_grouping`), el índice de categoría con la semántica de
    la «categoría buscable» de la PR #117, la regla de las críticas original
    del laboratorio (RF-25/RF-26) y la siembra al ensamblar contexto activos
    en el arnés, en vez del filtro-y-orden de M7 que mide el test anterior.

    ADR-112 (incidencia #463) conectó el índice de categoría (M9) y el
    filtro de relevancia con el candado de M10, con la semántica estricta
    del producto: 23/47, 108 elementos de más, 9 omisiones críticas,
    cobertura 64/81 (79.0%). Diagnosticó, con cita de fichero y línea, dos
    causas por las que esa conexión no alcanza D1: (1) `category_matches_
    query` (`src/sirius/domain/relevance.py:142-171`) exige activación única
    y deja sin señal a 4 de las 5 consultas del banco con vocabulario; (2) el
    candado de M10 (`src/sirius/application/context.py:239-258`) protege el
    100% de los candidatos de este banco, así que el filtro nunca descarta
    nada. La incidencia #465 autoriza cerrar ambas causas —únicamente en
    este arnés— y portar una tercera pieza que ADR-112 dejó fuera de
    alcance: la siembra al ensamblar contexto.

    Medido, por causa, sobre el motor con petición por caso (ADR-111,
    23/47, 90, 10, 63/81) como línea base:

    | configuración | aciertos | de más | omisiones | hallados |
    |---|---|---|---|---|
    | 0. motor solo (ADR-111) | 23/47 | 90 | 10 | 63/81 |
    | 1. + categoría buscable (causa 1) | 20/47 | 153 | 4 | 69/81 |
    | 2. + regla RF-25/RF-26 (causa 1) | 27/47 | 102 | 4 | 59/81 |
    | 3. + siembra en contexto (causa 2) | 27/47 | 110 | 0 | 63/81 |

    La fila 3 es la medición final de este test. `omisiones_criticas` (0 ≤ 1)
    y `cobertura` (63/81 ≥ 63/81) alcanzan el suelo de D1/D2; `aciertos_
    exactos` (27 < 29) y `elementos_de_mas` (110 > 21) no.

    **Diagnóstico mecánico de la brecha restante, con fichero y línea**: la
    causa dominante de `elementos_de_mas` es que `indice_de_categoria`
    (`tests/acceptance/staged_engine_category_and_relevance.py`) —igual que
    la referencia de producto que replica,
    `RankRelevantKnowledgeUseCase._rank_via_staged_engine`'s `solo_por_
    categoria` (`src/sirius/application/rank_relevant_knowledge.py:
    243-280`)— no restringe por ámbito: activa la categoría, admite **todas**
    las identidades de máxima criticidad del banco, sin importar su
    proyecto. Con la activación única (ADR-112) solo una consulta
    (`B04-CA-02`) disparaba esa admisión sin ámbito; con la «categoría
    buscable» de la causa 1 la disparan cinco (`B04-CA-02/26/31/38/44`), lo
    que multiplica la contaminación de proyectos ajenos (comparación
    elemento a elemento contra el fixture: `B04-CA-02` sola aporta 18
    elementos de más, `B04-CA-31`/`B04-CA-44` 14 cada una, `B04-CA-35` 15).
    La regla RF-25/RF-26 (causa 1) sí filtra ese ruido —de ahí que
    `elementos_de_mas` baje de 153 a 102 al aplicarla—, pero no lo suficiente
    para bajar de 21 porque el filtro solo actúa sobre lo que la corrida
    congelada examinó para cada caso (`relevance_filter_frozen_run.json`) y
    falla abierto para el resto (`aplicar_regla_de_criticas_original`,
    mismo contrato que `filtro_congelado_conserva`). Esta incidencia no
    autoriza restringir `indice_de_categoria` por ámbito (ampliaría el
    diseño ya aprobado de `category_match`/`solo_por_categoria` por
    iniciativa propia, que `CLAUDE.md` prohíbe): queda medido, publicado y
    sin forzar, igual que ADR-109/110/111/112.

    El suelo de D1 **no** queda afirmado aquí como aserción dura sobre las
    cuatro métricas a la vez —dos de las cuatro no lo alcanzan—; las cotas
    de no regresión se actualizan a la medición de la fila 3
    (27/47, ≤110, ≤0, ≥63/81), nunca por debajo de lo medido."""
    metricas = ejecucion_del_banco_motor_portado.metricas

    print(
        "\nPA-0.2-REC-01 (motor por etapas portado con petición por caso, "
        "categoría buscable, regla de las críticas original y siembra en "
        "contexto, ADR-109/ADR-110/ADR-111/ADR-112/ADR-113/#463/#465; "
        "puertas G1-G12, agrupación de equivalentes activas en el arnés): "
        f"aciertos_exactos={metricas.aciertos_exactos}/47 "
        f"elementos_de_mas={metricas.elementos_de_mas} "
        f"omisiones_criticas={metricas.omisiones_criticas} "
        f"cobertura={metricas.elementos_hallados}/{metricas.elementos_esperados_total} "
        f"({metricas.cobertura:.1%})"
    )

    # CODEX-003: misma convención que el test anterior, sobre la medición ya
    # publicada arriba (27/47, 110, 0, 63/81).
    assert metricas.aciertos_exactos >= _MINIMO_ACIERTOS_EXACTOS_MOTOR
    assert metricas.elementos_de_mas <= _MAXIMO_ELEMENTOS_DE_MAS_MOTOR
    assert metricas.omisiones_criticas <= _MAXIMO_OMISIONES_CRITICAS_MOTOR
    assert metricas.elementos_hallados >= _MINIMO_ELEMENTOS_HALLADOS_MOTOR
    # Incidencia #465: dos de las cuatro métricas de D1/D2 sí se alcanzan
    # sobre esta medición, y se afirman como aserciones duras aparte de las
    # cotas de no regresión de arriba (D1: omisiones críticas ≤ 1; D1/D2:
    # cobertura ≥ 63/81) — nunca las otras dos, que quedarían falseadas.
    assert metricas.omisiones_criticas <= 1
    assert metricas.cobertura >= 63 / 81


def test_el_cargador_no_lee_criticidad(ejecucion_del_banco: _EjecucionDelBanco) -> None:
    rutas_del_cargador = {ruta[0] for ruta in ejecucion_del_banco.accesos_del_cargador}
    assert "criticidad" not in rutas_del_cargador

    # `razon_segura` nunca debe leerse, la produzca o no una omisión crítica
    # real esta ejecución concreta del banco (ver módulo: M12 puede cerrarlas
    # todas). Qué se lee cuando sí hay una omisión crítica lo demuestra, con
    # un caso controlado independiente, `test_es_critico_lee_nivel_pero_nunca_razon_segura`.
    rutas_del_arnes = set(ejecucion_del_banco.accesos_del_arnes)
    assert ("criticidad", "razon_segura") not in rutas_del_arnes


def test_el_arnes_del_motor_portado_no_lee_razon_segura(
    ejecucion_del_banco_motor_portado: _EjecucionDelBanco,
) -> None:
    """Igual que `test_el_cargador_no_lee_criticidad`, pero para el segundo
    arnés (incidencia #457): construir `CriticidadAplicada` para el motor
    portado exige `nivel`, `fuente_de_politica` y `regla_de_politica` del
    corpus, pero nunca `razon_segura` — ese campo llega al motor con
    `_RAZON_SEGURA_NO_LEIDA_DEL_CORPUS`, ajeno al fixture."""
    rutas = set(ejecucion_del_banco_motor_portado.accesos_del_arnes)
    assert ("criticidad", "razon_segura") not in rutas
    assert ("criticidad", "nivel") in rutas


def test_es_critico_lee_nivel_pero_nunca_razon_segura() -> None:
    """Acceso permitido y prohibido de `_es_critico`, con un caso controlado
    independiente de la ejecución real del banco: no depende de que esa
    ejecución concreta produzca una omisión crítica (ver módulo, M12)."""
    accesos: list[tuple[str, ...]] = []
    item = {"criticidad": {"nivel": "CRITICO", "razon_segura": "no debe leerse"}}
    vigilado = _TrackingMapping(item, accesos)

    assert _es_critico(vigilado) is True

    rutas = set(accesos)
    assert ("criticidad", "nivel") in rutas
    assert ("criticidad", "razon_segura") not in rutas


# -- Índice de categoría y filtro de relevancia (incidencia #463/#465) ------


def test_solo_una_consulta_del_banco_activa_category_matches_query_sin_ambiguedad() -> None:
    """CODEX-004: de las cinco consultas del banco que contienen alguna
    palabra del vocabulario congelado (`VOCABULARIO_DE_CATEGORIA`), cuatro
    contienen dos a la vez (`"esencial"` y `"restriccion"`) y quedan sin
    activación porque `category_matches_query` exige exactamente un término
    activado (`src/sirius/domain/relevance.py:142-171`) — diseño ya
    aprobado de M9, sin tocar por la incidencia #465. Fija el hallazgo como
    prueba de forma sobre la función de **producto**, en contraste directo
    con `test_las_cinco_consultas_del_banco_activan_la_categoria_buscable_
    del_arnes` de aquí abajo, que fija la semántica distinta que usa el
    arnés desde la incidencia #465."""
    banco = _fixture()
    activan_sin_ambiguedad = []
    activan_con_ambiguedad = []
    for caso in banco["casos"]:
        consulta = caso["consulta"].casefold()
        terminos = {t for t in VOCABULARIO_DE_CATEGORIA if t in consulta}
        if not terminos:
            continue
        if len(terminos) == 1:
            activan_sin_ambiguedad.append(caso["id"])
        else:
            activan_con_ambiguedad.append(caso["id"])

    assert activan_sin_ambiguedad == ["B04-CA-02"]
    assert set(activan_con_ambiguedad) == {"B04-CA-26", "B04-CA-31", "B04-CA-38", "B04-CA-44"}
    # La única activación sin ambigüedad debe ser, verbatim, el único término
    # que este arnés asigna como categoría — si no, ninguna coincidencia real
    # sería posible.
    caso_no_ambiguo = next(c for c in banco["casos"] if c["id"] == "B04-CA-02")
    assert category_matches_query(
        CATEGORIA_DE_MAXIMA_CRITICIDAD,
        caso_no_ambiguo["consulta"],
        VOCABULARIO_DE_CATEGORIA,
    )


def test_las_cinco_consultas_del_banco_activan_la_categoria_buscable_del_arnes() -> None:
    """Incidencia #465, causa 1: `activa_categoria_buscable` reproduce la
    «categoría buscable» de la PR #117 (indexación FTS5 de
    `experiments/adr002/lateral/categoria.py`, donde las cinco palabras del
    vocabulario son el mismo contenido para toda identidad no ordinaria), a
    diferencia de `category_matches_query` — así que, sobre las mismas cinco
    consultas del banco que fija el test anterior, las cinco activan aquí,
    incluidas las cuatro que quedaban sin señal por la regla de activación
    única del producto."""
    banco = _fixture()
    activan = [caso["id"] for caso in banco["casos"] if activa_categoria_buscable(caso["consulta"])]
    assert set(activan) == {"B04-CA-02", "B04-CA-26", "B04-CA-31", "B04-CA-38", "B04-CA-44"}

    # Una consulta en blanco, o sin ninguna palabra del vocabulario, no
    # activa nada — misma garantía que `category_matches_query`.
    assert activa_categoria_buscable("") is False
    assert activa_categoria_buscable("¿Cuál es el presupuesto de Beta?") is False


def test_el_doble_del_filtro_de_relevancia_reproduce_la_corrida_congelada() -> None:
    """El doble determinista (`filtro_congelado_conserva`) da, para cada
    identidad que la corrida congelada examinó en cada caso, la misma
    decisión (conservar/descartar) que esa corrida — la garantía que la
    incidencia #463 pide ("misma decisión por elemento que aquella
    corrida"), verificada directamente contra el fixture portado."""
    datos = json.loads(
        (Path(__file__).parent / "fixtures" / "relevance_filter_frozen_run.json").read_text(
            encoding="utf-8"
        )
    )
    casos = datos["casos"]
    assert len(casos) == 47

    comprobaciones = 0
    for caso_id, veredicto in casos.items():
        entraron = set(veredicto["entraron_al_filtro"])
        conservados = set(veredicto["conservados_por_el_modelo"])
        assert conservados <= entraron
        for identidad in entraron:
            esperado = identidad in conservados
            assert filtro_congelado_conserva(caso_id, identidad) is esperado
            comprobaciones += 1
    assert comprobaciones > 0

    # Identidad nunca examinada por la corrida congelada para ese caso: el
    # doble falla abierto, igual que `RelevanceFilterPort` ante cualquier
    # fallo real.
    assert filtro_congelado_conserva("B04-CA-01", "MEM-999") is True
    # Caso que la corrida congelada nunca adjudicó: también falla abierto.
    assert filtro_congelado_conserva("CASO-INEXISTENTE", "MEM-001") is True


def test_el_candado_protege_todo_candidato_de_este_banco() -> None:
    """ADR-112: con solo dos categorías posibles en este banco —la única
    categoría de máxima criticidad que el arnés deriva de la criticidad del
    canon, o ninguna—, el candado de M10 (`aplicar_candado`, misma unión de
    tres conjuntos que `ContextBuilder._apply_relevance_filter`,
    `src/sirius/application/context.py:239-258`) protege el 100 % de los
    candidatos de este banco, incluso frente a un filtro que dijera que no
    conserva nada. Es la razón exacta, fijada como prueba de forma, de que
    el filtro de relevancia nunca descarte nada en la medición del banco."""
    banco = _fixture()
    categoria_por_identidad = {item["id"]: categoria_del_item(item) for item in banco["items"]}
    assert set(categoria_por_identidad.values()) <= {CATEGORIA_DE_MAXIMA_CRITICIDAD, None}

    candidatos = list(categoria_por_identidad)
    protegido_de_todo = aplicar_candado(
        candidatos=candidatos,
        conserva_el_filtro=lambda _identidad: False,
        categoria_por_identidad=categoria_por_identidad,
    )
    assert protegido_de_todo == frozenset(candidatos)


def test_la_regla_de_criticas_original_si_descarta_a_diferencia_del_candado_de_m10() -> None:
    """Incidencia #465, causa 1: a diferencia de `aplicar_candado` (que
    protege el 100% de este banco, ver test anterior), la regla RF-25/RF-26
    (`aplicar_regla_de_criticas_original`) sí puede descartar: sobre
    `B04-CA-33`, la corrida congelada dice que el modelo, con `MEM-011` como
    único candidato examinado, declaró que ninguna responde
    (`entraron_al_filtro=["MEM-011"]`, `conservados_por_el_modelo=[]`,
    `tests/acceptance/fixtures/relevance_filter_frozen_run.json`) — RF-26:
    ese veredicto se respeta entero, sin rescate, aunque MEM-011 fuera de
    categoría no ordinaria (no lo es, pero la regla no consultaría su
    categoría en este caso de todas formas: no hay nada que rescatar cuando
    el conjunto conservado está vacío)."""
    resultado = aplicar_regla_de_criticas_original(
        caso_id="B04-CA-33",
        candidatos=["MEM-011"],
        categoria_por_identidad={"MEM-011": None},
    )
    assert resultado == frozenset()


def test_la_regla_de_criticas_original_rescata_una_critica_descartada_por_el_modelo() -> None:
    """RF-25: sobre `B04-CA-34`, la corrida congelada conserva `MEM-011` y
    descarta, entre otras, `MEM-014` — si `MEM-014` fuera de la categoría de
    máxima criticidad, la regla la rescata en vez de dejarla fuera, porque
    el modelo sí eligió algunas (no declaró ausencia total)."""
    resultado = aplicar_regla_de_criticas_original(
        caso_id="B04-CA-34",
        candidatos=["MEM-011", "MEM-914"],
        categoria_por_identidad={"MEM-011": None, "MEM-914": CATEGORIA_DE_MAXIMA_CRITICIDAD},
    )
    # MEM-011: conservado por el modelo. MEM-914: entró al filtro, el modelo
    # lo descartó (no está en `conservados_por_el_modelo` de B04-CA-34), pero
    # es de categoría no ordinaria: se rescata.
    assert resultado == frozenset({"MEM-011", "MEM-914"})


def test_la_regla_de_criticas_original_falla_abierto_para_lo_no_examinado() -> None:
    """Mismo contrato de apertura que `filtro_congelado_conserva`: un caso o
    candidato que la corrida congelada nunca examinó pasa intacto."""
    assert aplicar_regla_de_criticas_original(
        caso_id="CASO-INEXISTENTE", candidatos=["MEM-001"], categoria_por_identidad={}
    ) == frozenset({"MEM-001"})
    assert aplicar_regla_de_criticas_original(
        caso_id="B04-CA-01", candidatos=["MEM-999"], categoria_por_identidad={}
    ) == frozenset({"MEM-999"})


def test_la_siembra_en_contexto_la_confirman_solo_los_dos_casos_por_construccion() -> None:
    """PR #117, sobre la siembra al ensamblar contexto: «se escribió después
    de ver qué casos fallaban y los dos únicos casos con ese propósito son
    esos dos, de modo que el banco la confirmaría por construcción. Se
    sostiene por diseño, y una prueba deja ese hecho asertado». Esta prueba
    deja ese hecho asertado: `B04-CA-33` y `B04-CA-34` son, verbatim, los dos
    únicos casos del banco cuyo `peticion_p2.proposito` declara que ensambla
    contexto — el banco no puede confirmar `siembra_de_contexto` de forma
    independiente, solo por construcción. La salvedad (a) de la Definición
    §3.2 (ampliar el banco con casos independientes de la siembra, o
    retirarla) queda pendiente, registrada para el propietario; esta
    incidencia (#465) no la resuelve."""
    banco = _fixture()
    casos_de_contexto = {
        caso["id"] for caso in banco["casos"] if "contexto" in caso["peticion_p2"]["proposito"]
    }
    assert casos_de_contexto == {"B04-CA-33", "B04-CA-34"}


def test_siembra_de_contexto_respeta_el_ambito_declarado() -> None:
    """`siembra_de_contexto` solo admite identidades del proyecto que la
    petición declara (o de ámbito global, que `G4` admite siempre): una
    identidad de categoría no ordinaria de otro proyecto no entra, ni
    siquiera con propósito de contexto."""
    categoria_por_identidad = {
        "DEC-003": CATEGORIA_DE_MAXIMA_CRITICIDAD,
        "MEM-101": CATEGORIA_DE_MAXIMA_CRITICIDAD,
        "MEM-001": CATEGORIA_DE_MAXIMA_CRITICIDAD,
    }
    proyecto_por_identidad = {
        "DEC-003": "PRJ-ALFA",
        "MEM-101": "PRJ-GAMMA",
        "MEM-001": "PRJ-GLOBAL",
    }

    sembrado = siembra_de_contexto(
        proposito="ensamblar_contexto_b05",
        ambito_declarado="PRJ-ALFA",
        ya_admitidos=(),
        categoria_por_identidad=categoria_por_identidad,
        proyecto_por_identidad=proyecto_por_identidad,
    )
    # DEC-003 (mismo proyecto) y MEM-001 (ámbito global) entran; MEM-101
    # (otro proyecto) no.
    assert sembrado == frozenset({"DEC-003", "MEM-001"})

    # Sin propósito de contexto, no siembra nada.
    assert (
        siembra_de_contexto(
            proposito="consultar",
            ambito_declarado="PRJ-ALFA",
            ya_admitidos=(),
            categoria_por_identidad=categoria_por_identidad,
            proyecto_por_identidad=proyecto_por_identidad,
        )
        == frozenset()
    )


@pytest.mark.skipif(
    os.environ.get("SIRIUS_OLLAMA_LIVE_TESTS") != "1",
    reason=(
        "Modo opcional contra Ollama real en localhost (incidencia #463, "
        "mismo patrón de activación explícita que usará la futura medición "
        "de coincidencia de M11, SIRIUS-ARQ-0.2 §6.1 punto 6): se salta en "
        "CI salvo que SIRIUS_OLLAMA_LIVE_TESTS=1, porque exige un servidor "
        "Ollama real en http://localhost:11434."
    ),
)
def test_el_filtro_ollama_real_no_rompe_el_banco() -> None:
    """Sanity check opcional del adaptador real (`OllamaRelevanceFilterAdapter`,
    ya portado a `main`, M10) contra un puñado de casos del banco, con un
    modelo local de verdad en vez del doble determinista. No sustituye la
    medición determinista de arriba —el resultado de un modelo real no es
    reproducible entre corridas— y no afirma ninguna de las cuatro métricas
    de D1: solo confirma que el adaptador real, invocado con datos del
    banco, sigue cumpliendo su contrato de fallo abierto (nunca una
    excepción, siempre un subconjunto de lo recibido)."""
    banco = _fixture()
    items_por_id = {item["id"]: item for item in banco["items"]}
    ahora = datetime.now(UTC)

    def _memoria(item_id: str, numero: int) -> RankedKnowledge:
        item = items_por_id[item_id]
        revision = MemoryRevision(
            id=numero,
            memory_id=numero,
            version=1,
            content=item["text"],
            origin="banco de evidencia (incidencia #463)",
            source_event_id=None,
            created_at=ahora,
        )
        memoria = Memory(
            id=numero,
            status=MemoryStatus.CURRENT,
            current_revision=revision,
            created_at=ahora,
            updated_at=ahora,
        )
        return RankedKnowledge(
            kind=KnowledgeKind.MEMORY,
            item=memoria,
            subject_matches_query=False,
            project_matches_active=False,
            fts_match=True,
        )

    caso = next(c for c in banco["casos"] if c["id"] == "B04-CA-01")
    candidatos = (_memoria("MEM-001", 1),)

    adaptador = OllamaRelevanceFilterAdapter(model="llama3.2")
    conservados = adaptador.filter_candidates(caso["consulta"], candidatos)

    assert set(conservados) <= set(candidatos)
