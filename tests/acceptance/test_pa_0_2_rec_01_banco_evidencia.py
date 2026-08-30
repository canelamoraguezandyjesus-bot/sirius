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
laboratorio — fuera del alcance léxico que esa incidencia autoriza. Por eso
D1/D2 siguen sin aserción de suelo aquí: D1 no se alcanza (ADR-109) y D2 es
competencia de M11 sobre el pipeline íntegro que M8-M10 integren, no de
este módulo.

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
from collections.abc import Iterator, Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pytest

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
from sirius.application.approve_decision import ApproveDecisionUseCase
from sirius.application.archive_memory import ArchiveMemoryUseCase
from sirius.application.propose_decision import ProposeDecisionUseCase
from sirius.application.rank_relevant_knowledge import RankRelevantKnowledgeUseCase
from sirius.application.save_manual_memory import SaveManualMemoryUseCase
from sirius.domain.memory import Memory
from sirius.domain.precedence import find_prevailing_decision
from sirius.domain.relevance import KnowledgeKind, RankedKnowledge

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "evidence_bank_47_casos.json"

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

    assert 0 <= metricas.aciertos_exactos <= 47
    assert metricas.elementos_de_mas >= 0
    assert metricas.omisiones_criticas >= 0
    assert 0 <= metricas.elementos_hallados <= metricas.elementos_esperados_total


def test_el_cargador_no_lee_criticidad(ejecucion_del_banco: _EjecucionDelBanco) -> None:
    rutas_del_cargador = {ruta[0] for ruta in ejecucion_del_banco.accesos_del_cargador}
    assert "criticidad" not in rutas_del_cargador

    # `razon_segura` nunca debe leerse, la produzca o no una omisión crítica
    # real esta ejecución concreta del banco (ver módulo: M12 puede cerrarlas
    # todas). Qué se lee cuando sí hay una omisión crítica lo demuestra, con
    # un caso controlado independiente, `test_es_critico_lee_nivel_pero_nunca_razon_segura`.
    rutas_del_arnes = set(ejecucion_del_banco.accesos_del_arnes)
    assert ("criticidad", "razon_segura") not in rutas_del_arnes


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
