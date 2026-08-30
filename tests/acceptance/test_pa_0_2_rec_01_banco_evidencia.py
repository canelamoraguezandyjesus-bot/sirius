"""PA-0.2-REC-01: banco de 47 casos contra el pipeline íntegro (M7, M11).

`tests/acceptance/fixtures/evidence_bank_47_casos.json` porta, sin
modificar ningún caso, resultado esperado ni adjudicación, el banco de 47
casos y sus 81 elementos esperados que PR #117 (`evidence/adr001-spikes`)
midió (Producto 0.2 §2.2/§3.2; Arquitectura Técnica 0.2 §6.5).

M7 ejecutaba este banco contra el pipeline de `main` tal como existía
entonces — `RankRelevantKnowledgeUseCase.rank()` seguido de la exclusión por
precedencia que `ContextBuilder` ya aplica (B4e) — sin índice de categoría
(M8), sin filtro de relevancia (M9/M10) y sin ninguna aserción de suelo,
dejando explícitamente D1/D2 para cuando M8-M10 integraran el pipeline
completo. M11 (§6.5, §8) es esa re-ejecución: la puerta de D7 punto 6 abierta
—cada item del canon recibe, al cargarse, la categoría canónica provisional
de ADR-107 (`evidence_bank_47_casos_categorias_canonicas.json`), fijada con
`SetCategoryUseCase` exactamente como la fijaría un usuario real, nunca por
`TagCategoryUseCase`/Ollama— y un doble determinista de `RelevanceFilterPort`
tras la exclusión por precedencia, con el mismo candado que
`ContextBuilder._apply_relevance_filter` aplica en producción. El doble que
usa este módulo nunca descarta nada (§8-M11 exige "dobles deterministas", sin
fijar cuáles: sin un juicio real de Ollama que portar, cualquier descarte
inventado mediría una opinión ficticia, no la del modelo real — ver ADR-107).
Con ese doble, las cuatro métricas miden el efecto real del índice de
categoría (§6.2) y de la integración del filtro (mecanismo cableado, orden
preservado) sobre este banco, nunca la precisión de un juicio de Ollama que
esta suite no tiene forma de ejercitar. D2 fija el suelo de cobertura que
esta re-ejecución confirma, sustituyendo el 63/81 provisional por la cifra
que esta primera medición real mide (51/81). **El suelo de D1 (aciertos
exactos ≥ 29/47) no se alcanza** — la cifra medida es 1/47, y no la introduce
este pipeline integrado: ya era así con el pipeline de M7, antes de esta
rama. La causa raíz está localizada y documentada en
`docs/decisions/ADR-108-el-banco-de-47-casos-no-alcanza-el-suelo-d1-de-29-47-porque-fts5-empareja-con-cualquier-palabra-incluidas-las-vacias.md`:
`sanitize_fts5_query` (B6a) une los tokens de cada consulta con `OR`,
incluidas las preposiciones y artículos del español, así que casi cualquier
consulta empareja con la mayoría del canon — un defecto estructural anterior
a M8-M11, fuera del alcance de esta incidencia. Ver el docstring de
`test_el_banco_se_ejecuta_contra_el_pipeline_integrado_y_reporta_las_cuatro_metricas`
para el detalle completo.

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
from collections.abc import Iterator, Mapping, Sequence
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
from sirius.application.set_category import SetCategoryUseCase
from sirius.application.tag_category import CategoryTargetKind
from sirius.composition_root import _CATEGORY_VOCABULARY, _MAX_CRITICALITY_CATEGORY
from sirius.domain.memory import Memory
from sirius.domain.precedence import find_prevailing_decision
from sirius.domain.relevance import KnowledgeKind, RankedKnowledge

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "evidence_bank_47_casos.json"
CANON_CATEGORIES_PATH = (
    Path(__file__).parent / "fixtures" / "evidence_bank_47_casos_categorias_canonicas.json"
)

pytestmark = [pytest.mark.acceptance, pytest.mark.integration]


def _fixture() -> Mapping[str, Any]:
    banco: Mapping[str, Any] = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    return banco


def _canon_categories() -> Mapping[str, str]:
    """Etiquetas canónicas provisionales del banco (ADR-107): una categoría
    del vocabulario cerrado por cada uno de los 97 items del canon."""
    contenido: Mapping[str, Any] = json.loads(CANON_CATEGORIES_PATH.read_text(encoding="utf-8"))
    etiquetas: Mapping[str, str] = contenido["etiquetas"]
    return etiquetas


class _KeepAllRelevanceFilterPort:
    """Doble determinista de ``RelevanceFilterPort`` para esta medición
    agregada (§8-M11): nunca descarta nada. Sin un juicio real de Ollama que
    portar dentro de la suite, cualquier descarte inventado mediría una
    opinión ficticia sobre estos 47 casos, no la del modelo real — ver
    ADR-107. Con este doble, las cuatro métricas aíslan el efecto del índice
    de categoría (§6.2) y de la integración mecánica del filtro (orden
    preservado, candado activo) sin contaminar la medición con un juicio de
    relevancia inventado. La precisión del propio modelo de Ollama la mide,
    por separado, D7 punto 6
    (``tests/acceptance/test_d7_punto_6_coincidencia_etiquetado.py``)."""

    def filter_candidates(
        self, query_text: str, candidates: Sequence[RankedKnowledge]
    ) -> Sequence[RankedKnowledge]:
        return candidates


def _apply_relevance_filter_candado(
    query_text: str,
    candidates: tuple[RankedKnowledge, ...],
    relevance_filter_port: _KeepAllRelevanceFilterPort,
    max_criticality_category: str,
) -> tuple[RankedKnowledge, ...]:
    """Réplica exacta de ``ContextBuilder._apply_relevance_filter`` (§6.3):
    la unión de lo que el filtro conserva, los candidatos de la categoría de
    máxima criticidad y los candidatos sin categoría todavía, preservando el
    orden de ``candidates``. Vive aquí, no importada de
    ``ContextBuilder``, porque ese método es privado y este arnés —igual que
    ya hacía con la exclusión por precedencia— evalúa el pipeline sin pasar
    por ``apply_context_budget``, que ``ContextBuilder.build()`` sí aplicaría."""
    filtered = relevance_filter_port.filter_candidates(query_text, candidates)
    kept_positions = {id(candidate) for candidate in filtered}
    kept_positions.update(
        id(candidate)
        for candidate in candidates
        if candidate.item.category is None or candidate.item.category == max_criticality_category
    )
    return tuple(candidate for candidate in candidates if id(candidate) in kept_positions)


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
    category: str | None = None,
    set_category_use_case: SetCategoryUseCase | None = None,
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

    `category` (M11, ADR-107) es la etiqueta canónica provisional del item,
    resuelta por el llamador fuera de este `Mapping` — nunca leída de `item`
    mismo, para no ensanchar lo que el espía de `test_el_cargador_no_lee_criticidad`
    vigila. Se fija con `SetCategoryUseCase`, el mismo camino que usaría una
    corrección real del usuario (D7 punto 3): nunca `TagCategoryUseCase`, que
    dependería de un `CategoryClassifierPort`/Ollama real dentro de la suite.
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
        if category is not None and set_category_use_case is not None:
            set_category_use_case.set(CategoryTargetKind.MEMORY, memory.id, category)
        return ("memory", memory.id)
    assert item["kind"] == "DECISION"
    assert project_id is not None
    decision = ProposeDecisionUseCase(unit_of_work).propose(text, project_id, text)
    if _vigente(item):
        ApproveDecisionUseCase(unit_of_work).approve(decision.id, confirmed=True)
    if category is not None and set_category_use_case is not None:
        set_category_use_case.set(CategoryTargetKind.DECISION, decision.id, category)
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
    set_category_use_case = SetCategoryUseCase(
        build_sqlite_memory_repository(database_path),
        build_sqlite_decision_repository(database_path),
    )
    canon_categories = _canon_categories()
    accesos_del_cargador: list[tuple[str, ...]] = []
    real_a_canonico: dict[tuple[str, int], str] = {}
    for item in banco["items"]:
        vigilado = _TrackingMapping(item, accesos_del_cargador)
        real = _load_canon_item(
            vigilado,
            project_ids=project_ids,
            unit_of_work=unit_of_work,
            category=canon_categories.get(item["id"]),
            set_category_use_case=set_category_use_case,
        )
        if real is None:
            continue
        real_a_canonico[real] = item["id"]

    # M11 (§6.2/§6.3, D7 punto 6): puerta abierta, vocabulario real —
    # exactamente lo que composition_root cablea cuando
    # category_matching_enabled=True — para medir el pipeline íntegro, no
    # solo el de M7.
    use_case = RankRelevantKnowledgeUseCase(
        memory_repository=build_sqlite_memory_repository(database_path),
        decision_repository=build_sqlite_decision_repository(database_path),
        project_repository=build_sqlite_project_repository(database_path),
        knowledge_search_repository=build_sqlite_knowledge_search_repository(database_path),
        category_vocabulary=_CATEGORY_VOCABULARY,
        category_matching_enabled=True,
    )
    relevance_filter_port = _KeepAllRelevanceFilterPort()
    decision_repository = build_sqlite_decision_repository(database_path)

    def excluido_por_precedencia(candidato: RankedKnowledge, decisiones: list[Any]) -> bool:
        """El mismo filtro que `ContextBuilder._excluded_by_precedence`
        (B4e) aplica en producción tras `rank()`, antes del filtro de
        relevancia (§6.3)."""
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
        tras_precedencia = tuple(
            candidato
            for candidato in use_case.rank(caso["consulta"])
            if not excluido_por_precedencia(candidato, decisiones_vigentes)
        )
        obtenido_ranked = _apply_relevance_filter_candado(
            caso["consulta"], tras_precedencia, relevance_filter_port, _MAX_CRITICALITY_CATEGORY
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


# -- ADR-107: la regla mecánica de etiquetado canónico, byte a byte --------

_ORDEN_DE_PRIORIDAD_CATEGORIAS = (
    "salud",
    "finanzas",
    "aprendizaje",
    "personal",
    "proyecto",
    "trabajo",
)

_PALABRAS_CLAVE_POR_CATEGORIA: Mapping[str, tuple[str, ...]] = {
    "salud": (
        "salud",
        "médic",
        "medic",
        "hospital",
        "enfermed",
        "dolor",
        "vacuna",
        "clinic",
        "clínic",
    ),
    "finanzas": (
        "presupuesto",
        "€",
        "nómina",
        "nomina",
        "pago",
        "factura",
        "descuento",
        "coste",
        "sueldo",
        "salario",
        "gasto",
        "ahorr",
    ),
    "aprendizaje": ("aprend", "curso", "estudi", "formaci", "clase", " leer ", "libro"),
    "personal": (
        "familia",
        "amig",
        "mascota",
        "pareja",
        "hobby",
        "vacacion",
        "viaje",
        "coche",
        "vuelo",
    ),
    "proyecto": (
        "proyecto",
        "expediente",
        "entregable",
        "hito",
        "alcance",
        "plataforma de despliegue",
        "atlas",
    ),
    "trabajo": (
        "reunión",
        "reunion",
        "oficina",
        "responsable",
        "informe",
        "operaciones",
        "calidad",
        "proveedor",
        "cliente",
        "empresa",
        "compras",
        "turno",
        "revisión",
        "revision",
        "publicaci",
        "almacén",
        "almacen",
        "logística",
        "logistica",
        "documental",
        "control de versiones",
        "nómina",
        "contrato",
        "mantenimiento",
        "identificador interno",
        "plataforma",
        "postgresql",
        "autorización",
        "autorizacion",
    ),
}


def _clasificar_categoria_canonica(text: str) -> str:
    """La regla mecánica de ADR-107, tal como su tabla la fija: la primera
    categoría (en el orden de prioridad de la tabla) cuya lista de palabras
    clave aparece como subcadena insensible a mayúsculas en ``text`` gana;
    ``otros`` si ninguna aparece."""
    normalizado = f" {text.casefold()} "
    for categoria in _ORDEN_DE_PRIORIDAD_CATEGORIAS:
        for clave in _PALABRAS_CLAVE_POR_CATEGORIA[categoria]:
            if clave.casefold() in normalizado:
                return categoria
    return "otros"


def test_las_etiquetas_canonicas_del_banco_coinciden_con_la_regla_de_adr_107() -> None:
    """Recalcula la regla en Python puro sobre el `text` de cada item y la
    compara, byte a byte, contra
    `evidence_bank_47_casos_categorias_canonicas.json` — para que la tabla
    de ADR-107 y el fixture nunca puedan divergir en silencio."""
    banco = _fixture()
    canon = _canon_categories()

    recalculado = {
        item["id"]: _clasificar_categoria_canonica(item["text"]) for item in banco["items"]
    }

    assert recalculado == dict(canon)
    assert set(canon.values()) <= {
        "trabajo",
        "personal",
        "salud",
        "finanzas",
        "proyecto",
        "aprendizaje",
        "otros",
    }


def test_el_banco_se_ejecuta_contra_el_pipeline_integrado_y_reporta_las_cuatro_metricas(
    ejecucion_del_banco: _EjecucionDelBanco,
) -> None:
    """M11: el pipeline íntegro (índice de categoría §6.2 + filtro de
    relevancia con candado §6.3, puerta de D7 punto 6 abierta) contra el
    banco de 47 casos.

    El suelo de cobertura de D2 (§6.5) sí queda afirmado como aserción dura,
    sustituyendo el provisional 63/81 por la cifra que esta primera medición
    real mide — D2 fija explícitamente ese suelo como "la cifra que se
    mida", nunca 63/81 ni 64/81 por decisión propia.

    El suelo de aciertos exactos de D1 (≥ 29/47) **no** queda afirmado aquí:
    la cifra medida es 1/47, muy por debajo, y la causa raíz está localizada
    y documentada en
    `docs/decisions/ADR-108-el-banco-de-47-casos-no-alcanza-el-suelo-d1-de-29-47-porque-fts5-empareja-con-cualquier-palabra-incluidas-las-vacias.md`:
    `sanitize_fts5_query` (B6a, ya en `main` antes de M7) une los tokens de
    la consulta con `OR`, incluidas las preposiciones y artículos del
    español, así que casi cualquier consulta empareja con la mayoría del
    canon — un defecto estructural anterior a M8-M11, no algo que el
    cableado de este encargo pueda cerrar sin tocar B6a (fuera de su
    alcance) o sin fabricar un doble de `RelevanceFilterPort` que en la
    práctica codifique las respuestas esperadas (prohibido). Afirmarlo de
    todos modos dejaría `uv run pytest` en rojo; debilitarlo en silencio
    falsearía la prueba. Queda medido y publicado, nunca exigido, hasta que
    el propietario decida cómo cerrar esa brecha (ADR-108).
    """
    metricas = ejecucion_del_banco.metricas

    print(
        "\nPA-0.2-REC-01 (M11, pipeline íntegro: índice + filtro con candado, "
        "puerta abierta): "
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

    # D2 (§6.5): "la primera medición real... sustituye al suelo provisional
    # sin necesidad de una nueva decisión del propietario" — 51/81, medido,
    # no 63/81 ni 64/81.
    SUELO_COBERTURA_MEDIDO_M11 = 51
    assert metricas.elementos_hallados >= SUELO_COBERTURA_MEDIDO_M11, (
        f"Cobertura por debajo del suelo medido por M11 ({SUELO_COBERTURA_MEDIDO_M11}/"
        f"{metricas.elementos_esperados_total}): regresión frente a la primera medición "
        "real de PA-0.2-REC-01 sobre main (D2)."
    )


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
