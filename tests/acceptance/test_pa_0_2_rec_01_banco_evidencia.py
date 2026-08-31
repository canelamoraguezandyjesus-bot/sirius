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
    truncar_por_limite_duro,
    vigente_en_tiempo_objetivo,
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
    Peticion,
)

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "evidence_bank_47_casos.json"
#: Incidencia #469: corrida final por caso del laboratorio (fila "5. con
#: siembra en contexto"), portada verbatim — ver `documento`/`fuente` dentro
#: del propio fichero para la cita completa.
LAB_FINAL_RUN_ROW5_PATH = Path(__file__).parent / "fixtures" / "lab_final_run_row5.json"

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
#: críticas original, siembra al ensamblar contexto, restricción por ámbito
#: del índice de categoría y las dos puertas (G8/G12) que la ampliación del
#: arnés no heredaba — incidencias #465/#467/#469, ADR-113/ADR-114/ADR-115).
#: Misma convención de cotas unidireccionales de no regresión, no el suelo de
#: D1 (29/47, ≤21, ≤1, ≥63/81): `aciertos_exactos` alcanza su suelo (29/47) y
#: se afirma como aserción dura aparte, más abajo; `omisiones_criticas` y
#: `cobertura` también (0 ≤ 1, 63/81 ≥ 63/81). `elementos_de_mas` mide 50
#: sobre las 47 filas sin salvedad, por encima de 21 — pero el umbral D1
#: publicado de ≤21 lo fija la fuente sumando solo sobre los 31 `casos_con_
#: contenido` (CODEX-001): medido con esa misma población (`test_elementos_
#: de_mas_alcanza_el_suelo_d1_bajo_la_poblacion_del_umbral_publicado`, más
#: abajo), el arnés mide 21 y sí alcanza su suelo D1. `_MAXIMO_ELEMENTOS_DE_
#: MAS_MOTOR` (50) sigue siendo la cota de no regresión de la métrica sin esa
#: salvedad, que el arnés también reporta.
_MINIMO_ACIERTOS_EXACTOS_MOTOR: Final[int] = 29
_MAXIMO_ELEMENTOS_DE_MAS_MOTOR: Final[int] = 50
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
    #: Incidencia #469: `obtenido` final por caso, solo poblado por
    #: `_ejecutar_banco_motor_portado` — permite comprobar, sin reconstruir
    #: el motor una segunda vez, que cada `elementos_de_mas` restante es un
    #: elemento que el laboratorio también producía (`lab_final_run_row5.json`).
    obtenido_por_caso: Mapping[str, frozenset[str]] = field(default_factory=dict)


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

    #: Incidencia #469, grupo B: `indice_de_categoria`/`siembra_de_contexto`
    #: operan en el espacio de identidades del corpus (`MEM-101`, `DEC-003`),
    #: no en el del motor (`MEMORIA:18`, `DECISION:3`) que `ejes_por_
    #: identidad`/`criticidad_aplicada` indexan — necesaria para que
    #: `vigente_en_tiempo_objetivo`/`truncar_por_limite_duro` puedan mirar
    #: los mismos ejes que el motor ya mira para lo que genera él mismo.
    identidad_motor_por_canonico: dict[str, str] = {
        corpus_id: _identidad_del_motor(kind, real_id)
        for (kind, real_id), corpus_id in real_a_canonico.items()
    }

    def _criticidad_de(identidad_canonica: str) -> Criticidad:
        motor_id = identidad_motor_por_canonico.get(identidad_canonica)
        aplicada = criticidad_aplicada.get(motor_id) if motor_id is not None else None
        return Criticidad.ORDINARIA if aplicada is None else aplicada.nivel

    def _vigente_en_tiempo_objetivo(identidad_canonica: str, peticion: Peticion) -> bool:
        motor_id = identidad_motor_por_canonico.get(identidad_canonica)
        ejes = ejes_por_identidad.get(motor_id) if motor_id is not None else None
        if ejes is None:
            return True
        return vigente_en_tiempo_objetivo(
            valid_from=ejes.valid_from,
            valid_to=ejes.valid_to,
            tiempo_objetivo=peticion.ventana.tiempo_objetivo,
            admite_no_vigentes=peticion.admite_no_vigentes,
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
    obtenido_por_caso: dict[str, frozenset[str]] = {}

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
            categoria = indice_de_categoria(
                consulta=caso["consulta"],
                ya_admitidos=obtenido_por_el_motor,
                categoria_por_identidad=categoria_por_identidad,
                ambito_declarado=ambito_declarado,
                proyecto_por_identidad=proyecto_por_identidad,
            )
            obtenido_tras_categoria = obtenido_por_el_motor | categoria
            siembra = siembra_de_contexto(
                proposito=peticion.proposito,
                ambito_declarado=ambito_declarado,
                ya_admitidos=obtenido_tras_categoria,
                categoria_por_identidad=categoria_por_identidad,
                proyecto_por_identidad=proyecto_por_identidad,
            )
            # Incidencia #469, grupo B: la ampliación (índice de categoría +
            # siembra) nunca pasaba por G8 (vigencia temporal) ni G12
            # (límite duro) — las dos puertas que el motor ya aplica a lo
            # que genera él mismo (`sirius.domain.staged_engine.recuperar`,
            # vía `staged_engine_gates`). Sin esta corrección, la ampliación
            # podía admitir una identidad que la corrida congelada nunca
            # examinó porque el laboratorio nunca la generó: aún no vigente
            # en el tiempo objetivo (G8), o por encima del límite duro que
            # la petición declara (G12).
            ampliacion_vigente = frozenset(
                identidad
                for identidad in categoria | siembra
                if _vigente_en_tiempo_objetivo(identidad, peticion)
            )
            obtenido_tras_siembra = truncar_por_limite_duro(
                obtenido_por_el_motor | ampliacion_vigente,
                limite_duro=peticion.limite_duro,
                criticidad_de=_criticidad_de,
            )
            obtenido = aplicar_regla_de_criticas_original(
                caso_id=caso["id"],
                candidatos=obtenido_tras_siembra,
                categoria_por_identidad=categoria_por_identidad,
            )
            esperado = set(caso["resultado_esperado"])
            obtenido_por_caso[caso["id"]] = frozenset(obtenido)

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
    return _EjecucionDelBanco(
        metricas=metricas,
        accesos_del_arnes=accesos_del_motor_portado,
        obtenido_por_caso=obtenido_por_caso,
    )


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
    """Incidencia #457/#461/#463/#465/#467/#469/ADR-109/ADR-110/ADR-111/
    ADR-112/ADR-113/ADR-114: el mismo banco, con el motor por etapas
    (`sirius.domain.staged_engine.recuperar`), las doce puertas
    (`staged_engine_gates`), la agrupación de equivalentes
    (`staged_engine_grouping`), el índice de categoría con la semántica de
    la «categoría buscable» de la PR #117, restricción por ámbito, las dos
    puertas de vigencia temporal y límite duro que la ampliación heredaba
    del motor (`G8`/`G12`, incidencia #469), la regla de las críticas
    original del laboratorio (RF-25/RF-26) y la siembra al ensamblar
    contexto activos en el arnés, en vez del filtro-y-orden de M7 que mide
    el test anterior.

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
    alcance: la siembra al ensamblar contexto. ADR-113 midió el resultado
    conjunto (27/47, 110, 0, 63/81) y diagnosticó que la causa dominante de
    `elementos_de_mas` restante era que `indice_de_categoria` no restringía
    por ámbito; la incidencia #467 autoriza cerrar esa causa, únicamente en
    este arnés, reproduciendo la semántica de ámbito que el laboratorio
    aplicaba aguas abajo del índice de categoría
    (`experiments/adr002/lateral/categoria.py:46-49`/`:174-175`, rama
    `evidence/adr001-spikes` — ver
    `tests.acceptance.staged_engine_category_and_relevance`, sección
    "INCIDENCIA #467").

    Medido, por causa, sobre el motor con petición por caso (ADR-111,
    23/47, 90, 10, 63/81) como línea base:

    | configuración | aciertos | de más | omisiones | hallados |
    |---|---|---|---|---|
    | 0. motor solo (ADR-111) | 23/47 | 90 | 10 | 63/81 |
    | 1. + categoría buscable (causa 1) | 20/47 | 153 | 4 | 69/81 |
    | 2. + regla RF-25/RF-26 (causa 1) | 27/47 | 102 | 4 | 59/81 |
    | 3. + siembra en contexto (causa 2, ADR-113) | 27/47 | 110 | 0 | 63/81 |
    | 4. + índice de categoría por ámbito (#467, ADR-114) | 27/47 | 62 | 0 | 63/81 |
    | 5. + G8/G12 sobre la ampliación (#469) | **29/47** | **50** | 0 | 63/81 |

    La fila 5 es la medición final de este test. `aciertos_exactos` (29/47),
    `omisiones_criticas` (0 ≤ 1) y `cobertura` (63/81 ≥ 63/81) alcanzan su
    suelo D1/D2 sobre las 47 filas sin salvedad. `elementos_de_mas` mide 50
    sobre las 47 filas — por encima del ≤21 publicado si se compara sin más—,
    pero el umbral D1 de ≤21 lo fija la fuente sobre una población distinta
    (los 31 `casos_con_contenido`, no los 47): medido con esa misma
    población, el arnés mide exactamente 21 y sí alcanza su suelo D1
    (CODEX-001,
    `test_elementos_de_mas_alcanza_el_suelo_d1_bajo_la_poblacion_del_umbral_publicado`,
    más abajo). Las cuatro métricas D1/D2 quedan así alcanzadas por este
    arnés, cada una medida bajo la población que su propio umbral publicado
    usa — sin que eso cierre PA-0.2-REC-01 en `main`, que exige el pipeline
    de producto integrado (M8-M12), no este arnés de evaluación (ver
    docstring del módulo). `elementos_de_mas` baja además un 19% frente a la
    fila 4 (62 → 50) al cerrar la infidelidad de porte que ADR-114 dejó sin
    explicar.

    **Método de la incidencia #469**: para cada uno de los 62 elementos de
    más que ADR-114 nombró (elemento a elemento, agrupados A/B/C), comprobar
    contra la corrida final por caso del laboratorio
    (`tests/acceptance/fixtures/lab_final_run_row5.json`, fila "5. con
    siembra en contexto" de `resultado_modelo_local_v0.7.json`, rama
    `evidence/adr001-spikes`, portada ahora verbatim) si el laboratorio
    también lo producía:

    - **50 elementos — el laboratorio también los produce** (están en su
      `obtenido` de esa fila): no son infidelidad del porte, son parte de
      los `elementos_de_mas` propios del laboratorio. La fuente publica 21
      para esta fila, pero esa cifra excluye los 16 `casos_de_ausencia`
      (`resultado_esperado` vacío) y solo suma sobre los 31 `casos_con_
      contenido` (`experiments/adr002/modelo_local/medir.py:255-269`, rama
      `evidence/adr001-spikes`); incluyendo también los `casos_de_ausencia`
      (29 más) da exactamente 50 — CODEX-001,
      `test_la_corrida_del_laboratorio_reproduce_las_metricas_publicadas_de_la_fuente`,
      más abajo, lo comprueba mecánicamente contra el fixture, junto con
      `aciertos_exactos`/`cobertura` (que sí coinciden sin salvedad) y
      documenta por qué `omisiones_criticas` (1 en la fuente) tampoco se
      reproduce contra el banco portado. Se quedan, anotados —
      `test_los_elementos_de_mas_restantes_son_los_del_laboratorio`, más
      abajo, lo fija como prueba de forma sobre el banco completo. Grupo A
      completo (39: `sirius.domain.staged_engine.recuperar` los admite antes
      de que `indice_de_categoria`/`siembra_de_contexto` intervengan, fuera
      del alcance de #469 igual que lo estaba del de #467), grupo C completo
      (3: `B04-CA-02`/`26`/`31`, el precio de precisión de activar la
      categoría por cualquiera de las cinco palabras, ya diagnosticado por
      ADR-112/ADR-113) y 8 del grupo B (`B04-CA-33` 5, `B04-CA-34` 3, vía
      `siembra_de_contexto`, que nunca pasa por el filtro de relevancia
      porque el laboratorio tampoco lo hace pasar).
    - **12 elementos — el laboratorio NO los produce** (grupo B,
      `B04-CA-26`/`MEM-112`; `B04-CA-38`/`MEM-001,111,112`;
      `B04-CA-44`/`MEM-001,106..112`, todos vía `indice_de_categoria`): la
      pieza portada que traicionaba la regla del laboratorio era `indice_de_
      categoria`/`siembra_de_contexto`, que ampliaban el conjunto admitido
      por un camino que nunca pasaba por `G8` (tiempo:
      `experiments/adr002/candidates/common/gates.py:228-256`, portada en
      `src/sirius/domain/staged_engine_gates.py:194-210`) ni por `G12`
      (criticidad y límite duro: `experiments/adr002/candidates/common/
      gates.py:356-386`, portada en `src/sirius/domain/staged_engine_gates.py
      :304-332`) — las dos puertas que el motor ya aplica a lo que genera él
      mismo. `vigente_en_tiempo_objetivo`/`truncar_por_limite_duro`
      (`tests.acceptance.staged_engine_category_and_relevance`, sección
      "INCIDENCIA #469") reproducen la mitad de cada puerta que le faltaba a
      la ampliación, aplicadas sobre el conjunto combinado (motor más
      ampliación) antes de `aplicar_regla_de_criticas_original`. Al cerrar
      esta causa, `B04-CA-38` y `B04-CA-44` pasan a coincidir exactamente con
      lo esperado — los 2 aciertos exactos que suben `aciertos_exactos` de
      27 a 29/47, el suelo de D1 para esa métrica.

    Ningún elemento de los 62 queda sin explicar: 50 son del laboratorio, 12
    eran infidelidad del porte y ya están corregidos. Los 50 que quedan sobre
    las 47 filas sin salvedad (por encima del 21 publicado si se compara
    contra esa cifra sin restringir la población) no son un defecto de esta
    incidencia: son la diferencia irreducible entre lo que este arnés puede
    reproducir sin tocar el motor, la corrida congelada o la activación de la
    categoría buscable (grupos A/C, 42 elementos) y lo que el laboratorio
    consigue con esas piezas conectadas de otra forma — cerrarla exigiría
    autorización sobre piezas que #469 deja fuera de alcance, igual que #467
    ya lo declaró para el grupo A/C. Bajo la población que sí originó el
    umbral D1 (los 31 `casos_con_contenido`), esos mismos 50 se reparten en
    21 dentro de esa población y 29 en los 16 `casos_de_ausencia` que el
    umbral nunca contó — el suelo D1 de `elementos_de_mas` (≤21) sí se
    alcanza, medido así (CODEX-001, más abajo).

    Las cotas de no regresión se actualizan a la medición de la fila 5 sobre
    las 47 filas sin salvedad (≥29/47, ≤50, ≤0, ≥63/81), nunca por debajo de
    lo medido; `aciertos_exactos`, `omisiones_criticas` y `cobertura` se
    afirman además como aserción dura aparte, cada una sobre esa misma
    medición de 47 filas, que ya alcanza su suelo D1/D2 sin ninguna
    salvedad de población. `elementos_de_mas` no se afirma como aserción
    dura aquí frente a ≤21 sobre las 47 filas —esa comparación mezclaría
    poblaciones distintas, el defecto que corrige CODEX-001—; su suelo D1 se
    afirma como aserción dura por separado, sobre la población que lo
    origina, en
    `test_elementos_de_mas_alcanza_el_suelo_d1_bajo_la_poblacion_del_umbral_publicado`."""
    metricas = ejecucion_del_banco_motor_portado.metricas

    print(
        "\nPA-0.2-REC-01 (motor por etapas portado con petición por caso, "
        "categoría buscable con restricción por ámbito, G8/G12 sobre la "
        "ampliación, regla de las críticas original y siembra en contexto, "
        "ADR-109/ADR-110/ADR-111/ADR-112/ADR-113/ADR-114/#463/#465/#467/#469; "
        "puertas G1-G12, agrupación de equivalentes activas en el arnés): "
        f"aciertos_exactos={metricas.aciertos_exactos}/47 "
        f"elementos_de_mas={metricas.elementos_de_mas} "
        f"omisiones_criticas={metricas.omisiones_criticas} "
        f"cobertura={metricas.elementos_hallados}/{metricas.elementos_esperados_total} "
        f"({metricas.cobertura:.1%})"
    )

    # CODEX-003: misma convención que el test anterior, sobre la medición ya
    # publicada arriba (29/47, 50, 0, 63/81).
    assert metricas.aciertos_exactos >= _MINIMO_ACIERTOS_EXACTOS_MOTOR
    assert metricas.elementos_de_mas <= _MAXIMO_ELEMENTOS_DE_MAS_MOTOR
    assert metricas.omisiones_criticas <= _MAXIMO_OMISIONES_CRITICAS_MOTOR
    assert metricas.elementos_hallados >= _MINIMO_ELEMENTOS_HALLADOS_MOTOR
    # Incidencia #465/#469: de las cuatro métricas de D1/D2, tres se afirman
    # aquí como aserciones duras aparte de las cotas de no regresión de
    # arriba (D1: aciertos exactos ≥ 29/47, omisiones críticas ≤ 1; D1/D2:
    # cobertura ≥ 63/81) — nunca `metricas.elementos_de_mas <= 21` aquí, que
    # compararía las 47 filas sin salvedad (50) contra un umbral que la
    # fuente fija solo sobre los 31 `casos_con_contenido` (CODEX-001). El
    # suelo D1 de `elementos_de_mas` sí se afirma como aserción dura, sobre
    # esa misma población, en
    # `test_elementos_de_mas_alcanza_el_suelo_d1_bajo_la_poblacion_del_umbral_publicado`.
    assert metricas.aciertos_exactos >= 29
    assert metricas.omisiones_criticas <= 1
    assert metricas.cobertura >= 63 / 81


def test_la_corrida_del_laboratorio_reproduce_las_metricas_publicadas_de_la_fuente() -> None:
    """CODEX-001: antes de usar `lab_final_run_row5.json` como oráculo para
    diagnosticar `elementos_de_mas` (como hace el test siguiente), esta
    prueba comprueba que el propio fixture reproduce las cuatro métricas que
    ADR-112 cita como publicadas para esta fila (29/47, 21, 1, 63/81) —no
    solo que la traducción por caso coincide byte a byte con la fuente, que
    ya está verificado manualmente caso a caso.

    `aciertos_exactos` (29/47) y `cobertura` (63/81) se reproducen
    directamente, sumando sobre las 47 filas sin ninguna salvedad.
    `elementos_de_mas` NO se reproduce sin matiz: sumar `obtenido - esperado`
    sobre las 47 filas da 50, no 21. La razón no es un fallo del porte: la
    fuente (`experiments/adr002/modelo_local/medir.py:255-269`, rama
    `evidence/adr001-spikes` — `sobrantes = sum(... for v in con_contenido)`)
    excluye del cómputo los `casos_de_ausencia` (`resultado_esperado` vacío;
    16 de los 47) y solo suma sobre los 31 `casos_con_contenido`. Repitiendo
    ese mismo filtro sobre el fixture SÍ da 21; sumando también los 16 casos
    de ausencia (29 más) da 50 — el número que mide el arnés. ADR-112/ADR-115
    citaban el "21" de la fuente sin esa salvedad, dando la falsa impresión
    de que debía coincidir con el "50" del arnés bajo el mismo criterio;
    ahora queda comprobable en vez de solo afirmado en prosa.

    `omisiones_criticas` (1 en la fuente) tampoco se reproduce, y esta prueba
    no lo fuerza: de los elementos que faltan en `obtenido` a través de las
    47 filas, ninguno tiene `criticidad.nivel == "CRITICO"` en
    `evidence_bank_47_casos.json` (el más cercano, `MEM-001` en `B04-CA-30`,
    es `IMPORTANTE`). La fuente decide "crítico" contra su propia lista
    (`experiments/adr002/round/metrics.py:296-316`, rama
    `evidence/adr001-spikes`), no contra el campo `criticidad` que porta este
    banco — una diferencia de clasificación ya existente en
    `evidence_bank_47_casos.json` desde incidencias anteriores (#457/#461/
    #463), fuera del alcance de #469, que no autoriza tocar el banco ni sus
    `resultado_esperado`."""
    banco = _fixture()
    lab = json.loads(LAB_FINAL_RUN_ROW5_PATH.read_text(encoding="utf-8"))["casos"]
    items_por_id = {item["id"]: item for item in banco["items"]}

    casos_con_contenido = 0
    casos_de_ausencia = 0
    aciertos_exactos = 0
    elementos_de_mas_con_contenido = 0
    elementos_de_mas_ausencia = 0
    elementos_hallados = 0
    elementos_esperados_total = 0
    omisiones_criticas = 0

    for caso in banco["casos"]:
        esperado = set(caso["resultado_esperado"])
        obtenido = set(lab[caso["id"]]["obtenido"])
        elementos_esperados_total += len(esperado)
        elementos_hallados += len(obtenido & esperado)
        if obtenido == esperado:
            aciertos_exactos += 1
        de_mas = len(obtenido - esperado)
        if esperado:
            casos_con_contenido += 1
            elementos_de_mas_con_contenido += de_mas
        else:
            casos_de_ausencia += 1
            elementos_de_mas_ausencia += de_mas
        for identidad in esperado - obtenido:
            criticidad = items_por_id[identidad].get("criticidad")
            if criticidad is not None and criticidad["nivel"] == "CRITICO":
                omisiones_criticas += 1

    assert (casos_con_contenido, casos_de_ausencia) == (31, 16)
    assert aciertos_exactos == 29
    assert (elementos_hallados, elementos_esperados_total) == (63, 81)
    assert elementos_de_mas_con_contenido == 21
    assert elementos_de_mas_ausencia == 29
    assert elementos_de_mas_con_contenido + elementos_de_mas_ausencia == 50
    assert omisiones_criticas == 0


def test_los_elementos_de_mas_restantes_son_los_del_laboratorio(
    ejecucion_del_banco_motor_portado: _EjecucionDelBanco,
) -> None:
    """Incidencia #469: el método que pide la incidencia, fijado como prueba
    de forma sobre el banco completo — para cada uno de los 47 casos, todo
    elemento de más que el arnés produce (`obtenido - esperado`) también
    aparece en `obtenido` de la corrida final del laboratorio
    (`lab_final_run_row5.json`, fila "5. con siembra en contexto"). Si algún
    elemento de más NO estuviera en la corrida del laboratorio, sería
    infidelidad del porte todavía sin cerrar — exactamente lo que esta
    incidencia corrige para `B04-CA-26`/`B04-CA-38`/`B04-CA-44` (ver el
    docstring del test anterior). Se vio fallar antes del cambio: el arnés
    sin `vigente_en_tiempo_objetivo`/`truncar_por_limite_duro` producía
    `MEM-112` para `B04-CA-26` y `MEM-001`/`MEM-111`/`MEM-112` para
    `B04-CA-38`, ninguno en la corrida del laboratorio para esos casos."""
    banco = _fixture()
    lab = json.loads(LAB_FINAL_RUN_ROW5_PATH.read_text(encoding="utf-8"))["casos"]
    obtenido_por_caso = ejecucion_del_banco_motor_portado.obtenido_por_caso

    sin_explicar: dict[str, list[str]] = {}
    for caso in banco["casos"]:
        caso_id = caso["id"]
        esperado = set(caso["resultado_esperado"])
        de_mas = obtenido_por_caso[caso_id] - esperado
        del_laboratorio = set(lab[caso_id]["obtenido"])
        no_explicados = sorted(de_mas - del_laboratorio)
        if no_explicados:
            sin_explicar[caso_id] = no_explicados

    assert sin_explicar == {}


def test_elementos_de_mas_alcanza_el_suelo_d1_bajo_la_poblacion_del_umbral_publicado(
    ejecucion_del_banco_motor_portado: _EjecucionDelBanco,
) -> None:
    """CODEX-001: el umbral D1 publicado para `elementos_de_mas` (≤21) lo fija
    la fuente (`experiments/adr002/modelo_local/medir.py:255-269`) sumando
    `obtenido - esperado` solo sobre los 31 `casos_con_contenido`
    (`resultado_esperado` no vacío) — nunca sobre los 47. El `elementos_de_
    mas=50` que reporta `test_el_banco_se_ejecuta_contra_el_motor_portado_y_
    reporta_las_cuatro_metricas` suma sobre las 47 filas sin esa salvedad, así
    que compararlo contra ≤21 compara dos poblaciones distintas — el defecto
    que corrige esta prueba, midiendo la misma población que originó el
    umbral directamente sobre la ejecución real del arnés (`obtenido_por_
    caso`), no sobre el fixture del laboratorio.

    `test_la_corrida_del_laboratorio_reproduce_las_metricas_publicadas_de_la_
    fuente` ya demuestra que, sobre esa misma población, el laboratorio mide
    exactamente 21. `test_los_elementos_de_mas_restantes_son_los_del_
    laboratorio` demuestra que, para cada caso, los sobrantes del arnés
    (`obtenido - esperado`) son subconjunto de `obtenido` del laboratorio —y
    como ambos comparten el mismo `esperado` por caso, un sobrante del arnés
    nunca puede ser un elemento esperado, así que ese subconjunto cae dentro
    de `obtenido - esperado` del laboratorio, acotando el recuento de
    sobrantes del arnés por el recuento de sobrantes del laboratorio, caso a
    caso. Sumando esa cota sobre los 31 `casos_con_contenido`, el arnés no
    puede medir más de 21 bajo esta población — esta prueba lo confirma
    midiéndolo directamente en vez de solo derivarlo por cota, y lo mide en
    exactamente 21: bajo la definición de población que originó el umbral
    D1 de `elementos_de_mas`, el arnés SÍ lo alcanza (≤21), aunque el total
    sin esa salvedad sobre las 47 filas (50) siga por encima — son dos
    métricas distintas, no la misma con dos resultados."""
    banco = _fixture()
    obtenido_por_caso = ejecucion_del_banco_motor_portado.obtenido_por_caso

    elementos_de_mas_con_contenido = 0
    for caso in banco["casos"]:
        esperado = set(caso["resultado_esperado"])
        if not esperado:
            continue
        elementos_de_mas_con_contenido += len(obtenido_por_caso[caso["id"]] - esperado)

    assert elementos_de_mas_con_contenido == 21
    assert elementos_de_mas_con_contenido <= 21  # suelo D1, sobre la población publicada


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


def test_indice_de_categoria_respeta_el_ambito_declarado() -> None:
    """Incidencia #467: `indice_de_categoria` solo admite identidades del
    proyecto que la consulta declara (o de ámbito global, que `G4` admite
    siempre, `src/sirius/domain/staged_engine_gates.py:135-149`) — misma
    semántica de ámbito que `siembra_de_contexto` ya aplicaba (test
    anterior) y que el laboratorio aplicaba aguas abajo del índice de
    categoría (`experiments/adr002/lateral/categoria.py:46-49`, rama
    `evidence/adr001-spikes`: "la razon es el ambito: G4 filtra por proyecto
    antes de entregar, de modo que N1-31 se queda con los criticos de su
    ambito"; `categoria.py:174-175`: "El ambito hace el resto: G4 filtra por
    proyecto, de modo que entran las criticas de ese proyecto y no las de
    otro"). Una identidad de categoría no ordinaria de otro proyecto no
    entra, aunque la consulta active la categoría buscable."""
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

    admitido = indice_de_categoria(
        consulta="¿Cuáles son las restricciones esenciales?",
        ya_admitidos=(),
        categoria_por_identidad=categoria_por_identidad,
        ambito_declarado="PRJ-ALFA",
        proyecto_por_identidad=proyecto_por_identidad,
    )
    # DEC-003 (mismo proyecto) y MEM-001 (ámbito global) entran; MEM-101
    # (otro proyecto) no.
    assert admitido == frozenset({"DEC-003", "MEM-001"})

    # Ámbito GLOBAL: todas las identidades de máxima criticidad entran,
    # cualquiera que sea su proyecto.
    admitido_global = indice_de_categoria(
        consulta="¿Cuáles son las restricciones esenciales?",
        ya_admitidos=(),
        categoria_por_identidad=categoria_por_identidad,
        ambito_declarado="GLOBAL",
        proyecto_por_identidad=proyecto_por_identidad,
    )
    assert admitido_global == frozenset({"DEC-003", "MEM-101", "MEM-001"})

    # Sin activación de la categoría buscable, no admite nada, sin importar
    # el ámbito.
    assert (
        indice_de_categoria(
            consulta="¿Cuál es el presupuesto de Beta?",
            ya_admitidos=(),
            categoria_por_identidad=categoria_por_identidad,
            ambito_declarado="PRJ-ALFA",
            proyecto_por_identidad=proyecto_por_identidad,
        )
        == frozenset()
    )


def test_vigente_en_tiempo_objetivo_excluye_lo_aun_no_vigente() -> None:
    """Incidencia #469, grupo B (`B04-CA-26`/`MEM-112`): la mitad de
    aplicabilidad temporal de `G8` (`src/sirius/domain/staged_engine_gates.py
    :194-210`, `_g8`, portada de `experiments/adr002/candidates/common/
    gates.py:228-256`, rama `evidence/adr001-spikes`) que `indice_de_
    categoria`/`siembra_de_contexto` no heredaban al ampliar el conjunto
    admitido por fuera del motor. Se vio fallar antes del cambio: el banco
    medía `elementos_de_mas=62` porque `MEM-112` (`valid_from` 2026-05-01)
    entraba para `B04-CA-26` (tiempo objetivo 2026-04-01), algo que la
    corrida congelada del laboratorio nunca produjo."""
    assert (
        vigente_en_tiempo_objetivo(
            valid_from="2026-05-01T00:00:00Z",
            valid_to=None,
            tiempo_objetivo="2026-04-01T00:00:00Z",
            admite_no_vigentes=False,
        )
        is False
    )
    assert (
        vigente_en_tiempo_objetivo(
            valid_from="2026-01-05T00:00:00Z",
            valid_to=None,
            tiempo_objetivo="2026-04-01T00:00:00Z",
            admite_no_vigentes=False,
        )
        is True
    )
    # `valid_to` expirado en el tiempo objetivo excluye, salvo que la
    # petición admita lo no vigente — mismas dos ramas que `_g8`.
    assert (
        vigente_en_tiempo_objetivo(
            valid_from=None,
            valid_to="2026-02-01T00:00:00Z",
            tiempo_objetivo="2026-04-01T00:00:00Z",
            admite_no_vigentes=False,
        )
        is False
    )
    assert (
        vigente_en_tiempo_objetivo(
            valid_from=None,
            valid_to="2026-02-01T00:00:00Z",
            tiempo_objetivo="2026-04-01T00:00:00Z",
            admite_no_vigentes=True,
        )
        is True
    )
    # Sin ejes declarados, degrada a vigente (misma garantía de apertura que
    # el resto de la ampliación de este arnés).
    assert (
        vigente_en_tiempo_objetivo(
            valid_from=None,
            valid_to=None,
            tiempo_objetivo="2026-04-01T00:00:00Z",
            admite_no_vigentes=False,
        )
        is True
    )


def test_truncar_por_limite_duro_prioriza_criticidad_y_luego_identidad() -> None:
    """Incidencia #469, grupo B (`B04-CA-38`/`B04-CA-44`): la mitad de
    límite de `G12` (`src/sirius/domain/staged_engine_gates.py:304-332`,
    `aplicar_g12`, portada de `experiments/adr002/candidates/common/
    gates.py:356-386`, rama `evidence/adr001-spikes`) que `indice_de_
    categoria` no heredaba: seguía añadiendo identidades por encima del
    límite duro que la petición declara. Se vio fallar antes del cambio: el
    banco admitía `MEM-001` (IMPORTANTE), `MEM-111` y `MEM-112` (CRÍTICO,
    pero fuera del límite duro de 10) para `B04-CA-38`, algo que la corrida
    congelada nunca produjo — su límite duro ya los había excluido antes
    incluso del filtro de relevancia."""

    def criticidad_de(identidad: str) -> Criticidad:
        return {
            "MEM-001": Criticidad.IMPORTANTE,
            "MEM-101": Criticidad.CRITICA,
            "MEM-102": Criticidad.CRITICA,
            "MEM-111": Criticidad.CRITICA,
            "MEM-112": Criticidad.CRITICA,
        }[identidad]

    admitido = truncar_por_limite_duro(
        ["MEM-112", "MEM-001", "MEM-111", "MEM-101", "MEM-102"],
        limite_duro=2,
        criticidad_de=criticidad_de,
    )
    # Los dos críticos de identidad menor entran; el crítico de identidad
    # mayor y el importante quedan fuera, aunque `MEM-001` llegara antes en
    # el iterable de entrada: la criticidad manda sobre el orden de llegada.
    assert admitido == frozenset({"MEM-101", "MEM-102"})

    # Un límite que no ata (mayor que el conjunto) no descarta nada.
    assert truncar_por_limite_duro(
        ["MEM-112", "MEM-001"], limite_duro=97, criticidad_de=criticidad_de
    ) == frozenset({"MEM-112", "MEM-001"})


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
