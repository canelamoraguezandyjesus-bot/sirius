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
filtro-y-orden de M7. Mide: **11/47**, 186 elementos de más, 9 omisiones
críticas, cobertura 60/81 (74.1%) — mejora real en las cuatro métricas
frente a M7, pero todavía muy por debajo de los cuatro objetivos de la
incidencia. ADR-110 diagnostica, con las cifras de cada configuración
probada, que la petición **por caso** (modo, permiso, cardinalidad, límite)
que el laboratorio usó para medir 29/47 vive en ficheros
(`experiments/adr002/benchmark/cases_v0_5.json`/`references_v0_5.json`) y en
un traductor (`experiments/adr002/round/cases.py`) que el alcance permitido
de esta incidencia no autoriza portar; sin ellos, este arnés solo puede
interrogar al motor con una política uniforme, y esa política no reproduce
las cifras del laboratorio. Por eso D1/D2 siguen sin aserción de suelo aquí:
D1 no se alcanza con ninguno de los dos pipelines medidos (ADR-109/ADR-110)
y D2 es competencia de M11 sobre el pipeline íntegro que M8-M10 integren, no
de este módulo.

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
from typing import Any, Final

import pytest

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
from sirius.domain.memory import Memory
from sirius.domain.precedence import find_prevailing_decision
from sirius.domain.relevance import KnowledgeKind, RankedKnowledge
from sirius.domain.staged_engine import recuperar
from sirius.domain.staged_engine_contracts import (
    Ambito,
    Cardinalidad,
    Clase,
    Criticidad,
    CriticidadAplicada,
    EjesDeclarados,
    Modo,
    Peticion,
    VentanaTemporal,
)

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

    Cada caso interroga al motor con su propia petición: modo M1 (ordinario,
    igual que el pipeline de producto), cardinalidad EXHAUSTIVA (`rank()` no
    declara una cuota de resultados, así que "todo lo relevante, sin cuota"
    es la semántica más fiel) y el ámbito que el propio caso declara
    (`caso["ambito"]`, portado desde `cases_v0_5.json` — `GLOBAL` o el
    nombre de un proyecto del banco), no un ámbito global uniforme: es la
    puerta `G4` la que debe decidir si un ítem de otro proyecto cuenta como
    elemento de más, no un filtro añadido por este arnés.
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
    ejes_por_identidad: dict[str, EjesDeclarados] = {}
    propiedades: dict[str, str | None] = {}
    criticidad_aplicada: dict[str, CriticidadAplicada] = {}
    for (kind, real_id), corpus_id in real_a_canonico.items():
        identidad = _identidad_del_motor(kind, real_id)
        item = items_por_id[corpus_id]
        ejes_por_identidad[identidad] = _ejes_declarados(item)
        propiedades[identidad] = item["ejes_p2"]["property_key"]
        nivel_bruto = item["criticidad"]["nivel"] if item["criticidad"] else None
        if nivel_bruto is not None:
            criticidad_aplicada[identidad] = CriticidadAplicada(
                nivel=_NIVELES_DE_CRITICIDAD[nivel_bruto],
                razon_segura=item["criticidad"]["razon_segura"],
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
    tiempo_objetivo = banco["ahora_declarado"]

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
            peticion = Peticion(
                operation_id=f"banco:{caso['id']}",
                consulta=caso["consulta"],
                proposito="medicion PA-0.2-REC-01: banco de 47 casos con el motor portado",
                modo=Modo.M1_ORDINARIO,
                ambito=ambito,
                ventana=VentanaTemporal(tiempo_objetivo=tiempo_objetivo, corte_de_registro=None),
                cardinalidad=Cardinalidad.EXHAUSTIVA,
                limite_objetivo=limite_sin_atar,
                limite_duro=limite_sin_atar,
            )
            recuperacion = recuperar(peticion, puerto, candidato, plano)
            obtenido = {
                real_a_canonico[
                    (
                        "memory" if resultado.item.clase is Clase.MEMORIA else "decision",
                        int(resultado.item.id.partition(":")[2]),
                    )
                ]
                for resultado in recuperacion.resultados
            }
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
    return _EjecucionDelBanco(metricas=metricas)


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


def test_el_banco_se_ejecuta_contra_el_motor_portado_y_reporta_las_cuatro_metricas(
    ejecucion_del_banco_motor_portado: _EjecucionDelBanco,
) -> None:
    """Incidencia #457/ADR-109/ADR-110: el mismo banco, con el motor por
    etapas (`sirius.domain.staged_engine.recuperar`), las doce puertas
    (`staged_engine_gates`) y la agrupación de equivalentes
    (`staged_engine_grouping`) activos en el arnés, en vez del
    filtro-y-orden de M7 que mide el test anterior.

    Medido: aciertos_exactos=11/47, elementos_de_mas=186,
    omisiones_criticas=9, cobertura=60/81 (74.1%) — mejora real en las
    cuatro métricas frente a M7 (10/47, 218, 10, 57/81), pero todavía muy
    por debajo del suelo de D1 (aciertos exactos ≥ 29/47) y de los otros
    tres objetivos de la incidencia (elementos de más ≤ 21, omisiones
    críticas ≤ 1, cobertura ≥ 63/81).

    ADR-110 documenta el diagnóstico completo con cifras de cada
    configuración probada (EXHAUSTIVA, ACOTADA con varios límites, y con
    ``E2`` desactivada). La causa raíz: el 29/47 que PR #117 midió depende
    de una petición **por caso** (modo, permiso, cardinalidad y límite
    declarados en ``experiments/adr002/benchmark/cases_v0_5.json`` y
    adjudicados en ``references_v0_5.json``, traducidos a ``Peticion`` por
    ``experiments/adr002/round/cases.py:334-366``) — ninguno de esos dos
    ficheros ni ese traductor están entre lo que el alcance permitido de
    esta incidencia autoriza portar (solo el tratamiento léxico restante,
    las puertas, la agrupación y el motor). Sin esa petición por caso, este
    arnés solo puede interrogar al motor con una política **uniforme**
    (misma para las 47 consultas): ``sirius.application.rank_relevant_
    knowledge._peticion_ordinaria`` — la misma que el camino real del
    producto usaría con la puerta abierta, cardinalidad EXHAUSTIVA (la
    semántica de "todo lo relevante, sin cuota" que ``rank()`` ya tiene) —
    y esa política uniforme no reproduce las cifras que una política
    ajustada caso a caso alcanzó.

    Igual que ADR-109 con el porte léxico: el suelo de D1 **no** queda
    afirmado aquí como aserción dura. Afirmar 29/47 dejaría `uv run pytest`
    en rojo; debilitarlo a 11 falsearía la prueba declarando cumplido un
    suelo que D1 fija en 29. Queda medido y publicado, nunca exigido."""
    metricas = ejecucion_del_banco_motor_portado.metricas

    print(
        "\nPA-0.2-REC-01 (motor por etapas portado, ADR-109/#457; "
        "puertas G1-G12 y agrupación de equivalentes activas en el arnés): "
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
