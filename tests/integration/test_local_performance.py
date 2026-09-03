"""B12c — medición de rendimiento local sobre el conjunto de datos de referencia.

El Plan de Pruebas especifica PA-025 con precisión: 5.000 mensajes, 500
recuerdos, 100 decisiones versionadas y 10 proyectos históricos con uno solo
activo; mínimo 30 repeticiones; informe P50 y P95; inicio ≤3 s P95 y
operaciones locales ≤300 ms P95.

Esto **no es PA-025**. PA-025 se ejecuta en el Windows del usuario dentro de
V8.4. Esto mide lo mismo en el runner de CI, que es hardware compartido y
ajeno, y por eso ADR-007 fija qué se puede afirmar con esa medida:

- se afirma el límite del plan solo donde hay un orden de magnitud de holgura,
  porque entonces un fallo es una regresión y no un runner lento;
- donde no la hay, se mide y se registra, pero **no se afirma el requisito**:
  una prueba de rendimiento que vive pegada a su umbral falla de forma
  intermitente, y una prueba intermitente se acaba silenciando.

Medición del 10 de agosto de 2026, 30 repeticiones, tres pasadas del mismo
código sobre la misma máquina:

| Operación | P50 | P95 (tres pasadas) | Límite | Uso |
|---|---|---|---|---|
| inicio | 20,9 ms | 30,3 ms | 3.000 ms | 1 % |
| listar decisiones vigentes | ~22 ms | 25,4 / 22,8 / 25,8 ms | 300 ms | 9 % |
| cargar historial completo | ~54 ms | 99,1 / 123,1 / 120,1 ms | 300 ms | 40 % |
| listar recuerdos vigentes | ~109 ms | 117,4 / 122,5 / 115,3 ms | 300 ms | 38 % |
| resumen de conocimiento | ~133 ms | 154,5 / 132,0 / 136,3 ms | 300 ms | 45 % |
| **construir contexto** | **~221 ms** | **266,4 / 286,6 / 298,6 ms** | 300 ms | **89 a 100 %** |

Construir el contexto consume entre el 89 % y el **100 %** de su presupuesto
aprobado, y las tres pasadas del mismo código dan tres cifras distintas. Eso es
justo lo que ADR-007 previó: afirmar aquí los 300 ms habría producido una
prueba que pasa o falla según el minuto.

El término dominante estaba medido y localizado en el código, no supuesto:
`list_current_memories()` tardaba ~117 ms para 500 recuerdos porque
`_load_memory()` llamaba a `_get_current_revision_model()` **una vez por
recuerdo** — una consulta para la lista y otra por cada elemento.

**Corregido en B12e** (ADR-008, incidencia #148): `list_current_memories()`,
`list_archived_memories()`, `list_current_decisions()` y
`list_archived_decisions()` cargan ahora la revisión vigente del conjunto en
una sola consulta, sin cambiar qué devuelven. Medición del 11 de agosto de
2026, mismo conjunto de referencia y misma máquina, antes y después del
arreglo:

| Operación | P95 antes (B12c) | P95 después (B12e) | Límite | Uso después |
|---|---|---|---|---|
| listar decisiones vigentes | 20,3 ms | 2,2 ms | 300 ms | 1 % |
| listar recuerdos vigentes | 104,7 ms | 9,3 ms | 300 ms | 3 % |
| resumen de conocimiento | 125,4 ms | 12,6 ms | 300 ms | 4 % |
| cargar historial completo | 87,9 ms | 94,2 ms | 300 ms | 31 % |
| **construir contexto** | **239,8 ms** | **120,9 ms** | **300 ms** | **40 %** |

Construir el contexto pasa del 80 % al 40 % de su presupuesto. La prueba de
conteo de consultas que fija esto por máquina —para que no se deshaga en
silencio en un cambio futuro— vive en
`tests/integration/test_memory_decision_list_query_count.py`, no aquí: esta
prueba mide tiempo sobre el conjunto de referencia completo, aquella fija el
número de consultas de cada método de forma aislada y barata. Detalle
completo en ADR-008 y en la sección de rendimiento de
`docs/implementation/V8_EXECUTION.md`.

**Vuelto a correr en M9** (SIRIUS-ARQ-0.2 §6.2/§8-M9, incidencia #449): el
índice de categoría determinista añade una cuarta señal estructural a
`RankRelevantKnowledgeUseCase.rank()`, calculada con la misma puerta de
activación de D7 punto 6 cerrada por defecto (`category_matching_enabled=False`)
que este mismo banco usa al construir `ContextBuilder` — la línea base que
M11 (§6.4) necesita antes de cablear el filtro con Ollama. Medición del 30 de
agosto de 2026, mismo conjunto de referencia y misma máquina, tres pasadas del
mismo código:

| Operación | P95 (tres pasadas) | Límite | Uso |
|---|---|---|---|
| **construir contexto** | **129,1 / 120,6 / 121,9 ms** | **300 ms** | **40 a 43 %** |

Sigue en la misma banda que B12e (120,9 ms, 40 %): con la puerta cerrada,
`category_match` nunca compara nada (el `and` de
`RankRelevantKnowledgeUseCase.rank()` corta antes de llamar a
`category_matches_query`), así que el coste añadido es un `bool` extra por
candidato en la tupla de `_sort_key`, no una comparación nueva. Entre el 40 %
y el 43 % del límite queda en la banda del 10-100 % de ADR-007: se registra
la medida como evidencia, pero no se afirma aquí que RNF-003 se cumple —eso
lo comprueba PA-025 en la máquina real.

**M11 (SIRIUS-ARQ-0.2 §6.4, §8-M11, incidencia #471): RNF-003 con el paquete
completo activo.** `test_construir_contexto_con_el_paquete_completo_activo_en_
los_tres_escenarios`, más abajo, mide «construir contexto» con la puerta de
D7 punto 6 abierta —`RankRelevantKnowledgeUseCase` con el vocabulario real, el
motor por etapas (ADR-109) y `ContextBuilder` con `OllamaRelevanceFilterAdapter`
cableado de verdad, nunca Ollama real dentro de la suite— en los tres
escenarios que §6.4 exige (incidencia #435, hallazgo CODEX-003): (a) Ollama
disponible dentro de su presupuesto; (b) Ollama ausente, conexión rechazada
de inmediato; (c) Ollama acepta la conexión y no responde hasta agotar el
`timeout` completo, el peor caso real. `timeout_seconds` es
`composition_root._RELEVANCE_FILTER_TIMEOUT_SECONDS` — el valor real con el
que producción construye el adaptador (50 ms cuando se midió la tabla de
abajo; 30 s desde ADR-125, que suspende el límite de 300 ms en el camino del
filtro mientras se mide su coste real). Desde ADR-125 el doble del escenario
(c) ya no duerme la espera: falla al instante, cuenta las invocaciones y las
pruebas publican `coste medido + espera` — lo mismo que medía el doble que
dormía, sin pagar ~15 minutos de suite por una constante conocida (ver
`_TransporteQueAceptaYNuncaContesta`).

Medición del 31 de agosto de 2026, mismo conjunto de referencia y misma
máquina, tres pasadas del mismo código:

| Escenario | P95 (tres pasadas) | Límite | Uso |
|---|---|---|---|
| (a) Ollama disponible dentro del presupuesto | 447,4 / 438,9 / 446,7 ms | 300 ms | 146 a 149 % |
| (b) Ollama ausente (conexión rechazada) | 438,8 / 435,8 / 441,5 ms | 300 ms | 145 a 147 % |
| (c) Ollama acepta la conexión y agota el timeout | 493,8 / 494,0 / 496,1 ms | 300 ms | 165 % |

Las tres cifras superan ya los 300 ms de RNF-003 en este runner compartido —
muy por encima incluso del 100 % que B12c midió sin ninguna de las piezas de
M8-M11 activas—, y las tres, incluida (b) (conexión rechazada, sin ningún
coste de red del propio Ollama), están en la misma banda: el coste añadido no
lo paga el transporte HTTP del filtro, lo paga construir la petición del
motor por etapas y recorrer sus doce puertas (ADR-109) sobre el conjunto de
referencia de 500 recuerdos/100 decisiones, activado aquí por primera vez
(con la puerta cerrada, `rank()` nunca toma ese camino — ver la medición de
M9 arriba, 120-130 ms, sin el motor). ADR-007 exige un orden de magnitud de
holgura para afirmar aquí el límite del plan; sin ella, esta prueba solo
mide y registra el guardarraíl de disparate (1.500 ms), muy lejos de estas
cifras, y este docstring deja constancia explícita, junto con estas tres
filas, de que **RNF-003 no se cumple hoy con el paquete completo activo**
sobre este runner — evidencia que el propietario necesita antes de
decidir si abre la puerta de D7 punto 6 en `settings.json`, exactamente lo
que M11 (§8) exige publicar, sin afirmarlo como aserción dura porque D1/D2 lo
miden sobre el banco, no sobre este benchmark de latencia. La cifra real en
la máquina de un usuario (PA-025, V8.4) puede ser distinta: este runner de CI
es hardware compartido y ajeno (ver el encabezado de este módulo).
"""

from __future__ import annotations

import json
import statistics
import time
from collections.abc import Callable, Iterator
from pathlib import Path

import httpx
import pytest

from sirius.adapters.llm.token_counter import CharacterHeuristicTokenCounter
from sirius.adapters.ollama_relevance_filter import OllamaRelevanceFilterAdapter
from sirius.adapters.persistence.bootstrap import initialize_persistence
from sirius.adapters.persistence.sqlite_conversation_repository import (
    build_sqlite_conversation_repository,
)
from sirius.adapters.persistence.sqlite_decision_repository import (
    build_sqlite_decision_repository,
)
from sirius.adapters.persistence.sqlite_event_repository import build_sqlite_event_repository
from sirius.adapters.persistence.sqlite_identity_repository import (
    build_sqlite_identity_repository,
)
from sirius.adapters.persistence.sqlite_knowledge_search_repository import (
    build_sqlite_knowledge_search_repository,
)
from sirius.adapters.persistence.sqlite_memory_repository import build_sqlite_memory_repository
from sirius.adapters.persistence.sqlite_memory_suggestion_repository import (
    build_sqlite_memory_suggestion_repository,
)
from sirius.adapters.persistence.sqlite_project_repository import (
    build_sqlite_project_repository,
)
from sirius.adapters.persistence.staged_engine_candidate import candidato as staged_engine_candidato
from sirius.adapters.persistence.staged_engine_port import build_staged_engine_port
from sirius.application.context import ContextBuilder
from sirius.application.knowledge_overview import GetKnowledgeOverviewUseCase
from sirius.application.rank_relevant_knowledge import RankRelevantKnowledgeUseCase
from sirius.composition_root import (
    _CATEGORY_VOCABULARY,
    _CRITICALITY_VOCABULARY,
    _MAX_CRITICALITY_CATEGORY,
    _RELEVANCE_FILTER_MODEL,
    _RELEVANCE_FILTER_TIMEOUT_SECONDS,
)
from sirius.domain.conversation import MessageRole, MessageStatus
from sirius.infrastructure.paths import resolve_paths

# Conjunto de datos de referencia, tal y como lo fija el Plan de Pruebas.
MENSAJES = 5_000
RECUERDOS = 500
DECISIONES = 100
PROYECTOS = 10

REPETICIONES = 30

# Límites aprobados (RNF-002, RNF-003).
LIMITE_INICIO_MS = 3_000.0
LIMITE_OPERACION_MS = 300.0

# ADR-007: solo se afirma el límite del plan con al menos un orden de magnitud
# de holgura sobre la medida real.
HOLGURA_EXIGIDA = 10.0

# Guardarraíl para las operaciones que no alcanzan esa holgura. NO es el
# requisito: es un tope de disparate que caza una regresión de orden de
# magnitud sin volverse intermitente. El requisito de 300 ms lo comprueba
# PA-025 en la máquina real.
GUARDARRAIL_MS = 1_500.0


class Medicion:
    def __init__(self, nombre: str, muestras_ms: list[float]) -> None:
        self.nombre = nombre
        self.muestras_ms = sorted(muestras_ms)

    @property
    def p50(self) -> float:
        return statistics.median(self.muestras_ms)

    @property
    def p95(self) -> float:
        indice = max(0, int(len(self.muestras_ms) * 0.95) - 1)
        return self.muestras_ms[indice]

    def __str__(self) -> str:
        return (
            f"{self.nombre}: P50={self.p50:.1f} ms P95={self.p95:.1f} ms "
            f"({len(self.muestras_ms)} repeticiones)"
        )


def _medir(nombre: str, operacion: Callable[[], object]) -> Medicion:
    operacion()  # calentamiento: la primera pasada paga cachés que no se miden
    muestras = []
    for _ in range(REPETICIONES):
        inicio = time.perf_counter()
        operacion()
        muestras.append((time.perf_counter() - inicio) * 1000.0)
    return Medicion(nombre, muestras)


class BancoDePruebas:
    """El conjunto de referencia sembrado, con todo cableado sobre él."""

    def __init__(self, database_path: Path) -> None:
        self.database_path = database_path
        self.conversation_repository = build_sqlite_conversation_repository(database_path)
        self.memory_repository = build_sqlite_memory_repository(database_path)
        self.decision_repository = build_sqlite_decision_repository(database_path)
        self.project_repository = build_sqlite_project_repository(database_path)
        self.conversation = self.conversation_repository.get_or_create_main_conversation()
        rank = RankRelevantKnowledgeUseCase(
            memory_repository=self.memory_repository,
            decision_repository=self.decision_repository,
            project_repository=self.project_repository,
            knowledge_search_repository=build_sqlite_knowledge_search_repository(database_path),
        )
        self.context_builder = ContextBuilder(
            identity_repository=build_sqlite_identity_repository(database_path),
            project_repository=self.project_repository,
            memory_repository=self.memory_repository,
            conversation_repository=self.conversation_repository,
            decision_repository=self.decision_repository,
            rank_relevant_knowledge_use_case=rank,
            event_repository=build_sqlite_event_repository(database_path),
            token_counter=CharacterHeuristicTokenCounter(),
        )
        self.knowledge_overview = GetKnowledgeOverviewUseCase(
            memory_repository=self.memory_repository,
            decision_repository=self.decision_repository,
            memory_suggestion_repository=build_sqlite_memory_suggestion_repository(database_path),
        )


@pytest.fixture(scope="module")
def banco(tmp_path_factory: pytest.TempPathFactory) -> Iterator[BancoDePruebas]:
    """Siembra el conjunto de referencia una sola vez para todo el módulo.

    Se siembra a través de los repositorios reales, no con inserciones en
    bloque: las invariantes que el repositorio mantiene —el número de secuencia
    del mensaje, la revisión inicial, los disparadores FTS5— tendrían que
    reimplementarse aquí, y una siembra que diverge del producto mide otra cosa.
    Cuesta unos 15 s y ocurre una vez.

    **El aislamiento de rutas se hace aquí y no se hereda.** El
    `_isolate_platform_dirs` de `tests/conftest.py` es de ámbito función, y
    pytest construye las fixtures de mayor ámbito primero: cuando esta se
    ejecuta, aquel todavía no ha redirigido nada, así que `resolve_paths()`
    devolvería el directorio de datos **real** del usuario y esta fixture
    sembraría 5.000 mensajes dentro. Ocurrió de verdad durante el desarrollo de
    esta prueba, y por eso la comprobación de abajo no es defensiva: es la que
    lo hace imposible en vez de improbable.
    """
    raiz = tmp_path_factory.mktemp("rendimiento")
    with pytest.MonkeyPatch.context() as parche:
        parche.setenv("XDG_CONFIG_HOME", str(raiz))
        parche.setenv("XDG_DATA_HOME", str(raiz))
        parche.setenv("WIN_PD_OVERRIDE_LOCAL_APPDATA", str(raiz))
        yield _sembrar(raiz)


def _sembrar(raiz: Path) -> BancoDePruebas:
    paths = resolve_paths()
    if raiz not in paths.data_dir.parents and paths.data_dir != raiz:
        msg = (
            f"El aislamiento de rutas no está activo: resolve_paths() apunta a "
            f"{paths.data_dir}, fuera de {raiz}. Sembrar aquí escribiría el "
            "conjunto de referencia en los datos reales del usuario."
        )
        raise AssertionError(msg)
    initialize_persistence(paths)
    database_path = paths.data_dir / "sirius.db"

    conversation_repository = build_sqlite_conversation_repository(database_path)
    conversation = conversation_repository.get_or_create_main_conversation()
    project_repository = build_sqlite_project_repository(database_path)
    project_repository.ensure_bootstrap_project()
    build_sqlite_identity_repository(database_path).get_or_create_current_identity()

    # 10 proyectos históricos, uno solo activo: el dominio solo permite crear
    # el siguiente tras completar el anterior (B3c), así que se hace así.
    for indice in range(PROYECTOS - 1):
        historico = project_repository.create_project(
            f"Proyecto histórico {indice}",
            f"Objetivo del proyecto histórico {indice}",
            state_summary="cerrado",
            blockers=(),
            next_step="ninguno",
        )
        project_repository.complete_active_project(historico.id)
    activo = project_repository.create_project(
        "Proyecto activo de referencia",
        "Objetivo vigente del conjunto de referencia",
        state_summary="en curso",
        blockers=("un bloqueo registrado",),
        next_step="siguiente paso registrado",
    )

    for indice in range(MENSAJES):
        conversation_repository.append_message(
            conversation.id,
            MessageRole.USER if indice % 2 == 0 else MessageRole.SIRIUS,
            f"mensaje de referencia {indice} sobre despliegue, base de datos y arquitectura",
            operation_id=f"referencia-{indice}",
            status=MessageStatus.COMPLETED,
        )

    memory_repository = build_sqlite_memory_repository(database_path)
    for indice in range(RECUERDOS):
        memory_repository.create_memory(
            f"recuerdo de referencia {indice} sobre despliegue y preferencias de trabajo",
            origin="siembra del conjunto de referencia",
            subject_key=f"asunto-{indice % 50}",
            project_id=activo.id,
        )

    decision_repository = build_sqlite_decision_repository(database_path)
    for indice in range(DECISIONES):
        decision = decision_repository.create_proposal(
            f"asunto-de-decision-{indice}",
            activo.id,
            f"contenido de la decisión {indice} sobre arquitectura y despliegue",
        )
        decision_repository.approve_decision(decision.id)

    return BancoDePruebas(database_path)


def _operaciones_locales(banco: BancoDePruebas) -> list[Medicion]:
    return [
        _medir(
            "construir contexto",
            lambda: banco.context_builder.build("cómo vamos con el despliegue"),
        ),
        _medir(
            "cargar historial completo",
            lambda: banco.conversation_repository.list_messages(banco.conversation.id),
        ),
        _medir(
            "listar recuerdos vigentes",
            banco.memory_repository.list_current_memories,
        ),
        _medir(
            "listar decisiones vigentes",
            banco.decision_repository.list_current_decisions,
        ),
        _medir(
            "resumen de conocimiento",
            banco.knowledge_overview.get_overview,
        ),
    ]


@pytest.mark.integration
def test_el_conjunto_de_referencia_tiene_el_tamano_que_fija_el_plan(
    banco: BancoDePruebas,
) -> None:
    # Sin esta comprobación, un fallo al sembrar convertiría todas las
    # mediciones siguientes en tiempos sobre una base vacía: rapidísimos, y
    # sin ningún valor.
    assert len(banco.conversation_repository.list_messages(banco.conversation.id)) == MENSAJES
    assert len(banco.memory_repository.list_current_memories()) == RECUERDOS
    assert len(banco.decision_repository.list_current_decisions()) == DECISIONES


@pytest.mark.integration
def test_el_inicio_local_cumple_el_limite_aprobado(banco: BancoDePruebas) -> None:
    """Inicio ≤3 s P95 (RNF-002).

    Medido en 30,3 ms P95, el 1 % del límite. Con esa holgura, ADR-007 permite
    afirmar el requisito directamente: un fallo aquí no puede ser un runner
    lento, tendría que ser cien veces más lento.

    Mide el arranque determinista y sin interfaz —resolución de rutas,
    migraciones y apertura de los repositorios—. El pintado de la ventana de
    PySide6 en un runner sin pantalla no dice nada del arranque real y se
    comprueba en Windows dentro de B14.
    """

    def arrancar() -> None:
        initialize_persistence(resolve_paths())
        build_sqlite_conversation_repository(banco.database_path).get_or_create_main_conversation()
        build_sqlite_project_repository(banco.database_path).get_active_project()
        build_sqlite_identity_repository(banco.database_path).get_or_create_current_identity()

    medicion = _medir("inicio", arrancar)
    assert medicion.p95 <= LIMITE_INICIO_MS, (
        f"{medicion} supera el límite aprobado de {LIMITE_INICIO_MS:.0f} ms."
    )
    # La holgura es parte de lo que la prueba afirma: si desaparece, el
    # criterio de ADR-007 deja de sostener esta aserción y hay que revisarla.
    assert medicion.p95 * HOLGURA_EXIGIDA <= LIMITE_INICIO_MS, (
        f"{medicion} ya no guarda un orden de magnitud de holgura frente a "
        f"{LIMITE_INICIO_MS:.0f} ms. Es una regresión que todavía cumple el "
        "requisito, pero invalida el criterio con el que esta prueba lo afirma "
        "en CI (ADR-007). Revísese antes de seguir."
    )


@pytest.mark.integration
def test_las_operaciones_locales_no_se_disparan(banco: BancoDePruebas, capsys) -> None:  # type: ignore[no-untyped-def]
    """Guardarraíl, NO el requisito de 300 ms.

    La operación más lenta —construir el contexto— se midió en 266 ms P95, el
    89 % de su presupuesto. Sin un orden de magnitud de holgura, ADR-007
    prohíbe afirmar aquí el límite del plan: la prueba sería intermitente y
    acabaría silenciada.

    Así que se afirma un tope de disparate, declarado como tal, que caza una
    regresión de orden de magnitud. **El requisito de 300 ms lo comprueba
    PA-025 en la máquina del usuario, no esto.**
    """
    mediciones = _operaciones_locales(banco)
    with capsys.disabled():
        print("\n  Rendimiento local sobre el conjunto de referencia:")
        for medicion in mediciones:
            porcentaje = medicion.p95 / LIMITE_OPERACION_MS * 100
            print(f"    {medicion}  [{porcentaje:.0f} % del límite del plan]")

    excedidas = [m for m in mediciones if m.p95 > GUARDARRAIL_MS]
    assert not excedidas, (
        "Operaciones locales por encima del guardarraíl de "
        f"{GUARDARRAIL_MS:.0f} ms: {[str(m) for m in excedidas]}. Este tope no "
        f"es el requisito ({LIMITE_OPERACION_MS:.0f} ms): superarlo indica una "
        "regresión de orden de magnitud, no un runner lento."
    )


@pytest.mark.integration
def test_listar_decisiones_vigentes_cumple_el_limite_aprobado(banco: BancoDePruebas) -> None:
    """La única operación local con holgura suficiente para afirmar el límite.

    Medida en 25,4 ms P95, el 8 % de los 300 ms. Se afirma el requisito porque
    aquí sí se puede, y así al menos una operación local queda atada al número
    del plan y no solo al guardarraíl.
    """
    medicion = _medir(
        "listar decisiones vigentes", banco.decision_repository.list_current_decisions
    )
    assert medicion.p95 <= LIMITE_OPERACION_MS, (
        f"{medicion} supera el límite aprobado de {LIMITE_OPERACION_MS:.0f} ms."
    )


# --- M11 (SIRIUS-ARQ-0.2 §6.4, §8-M11): RNF-003 con el paquete completo -----
# --- activo, en los tres escenarios que §6.4 exige. -------------------------


def _build_context_builder_with_relevance_filter(
    database_path: Path, relevance_filter_port: OllamaRelevanceFilterAdapter
) -> ContextBuilder:
    """El mismo cableado que ``composition_root`` produce con la puerta de
    D7 punto 6 abierta (§6.3): ``RankRelevantKnowledgeUseCase`` con el
    vocabulario real, la puerta activa y el motor por etapas (ADR-109), y
    ``ContextBuilder`` con el filtro de relevancia y la categoría de máxima
    criticidad — reutiliza las mismas constantes de ``composition_root``
    para que esta medición mida de verdad lo que produciría la construcción
    de producción, no una aproximación.

    M16 (SIRIUS-ARQ-0.2 §11.4/§11.5, incidencia #504, ADR-124):
    ``category_matching_enabled=True`` también en ``ContextBuilder``, igual
    que ``composition_root`` (``src/sirius/composition_root.py:483``) pasa
    la misma bandera a los dos — antes de este encargo faltaba aquí, así
    que esta medición ejercitaba el candado de M10 en vez de RF-25/RF-26 y
    G8/G12 de M15, pese a que ``RankRelevantKnowledgeUseCase`` ya tenía la
    puerta abierta."""
    memory_repository = build_sqlite_memory_repository(database_path)
    decision_repository = build_sqlite_decision_repository(database_path)
    project_repository = build_sqlite_project_repository(database_path)
    rank_relevant_knowledge_use_case = RankRelevantKnowledgeUseCase(
        memory_repository=memory_repository,
        decision_repository=decision_repository,
        project_repository=project_repository,
        knowledge_search_repository=build_sqlite_knowledge_search_repository(database_path),
        category_vocabulary=_CATEGORY_VOCABULARY,
        criticality_vocabulary=_CRITICALITY_VOCABULARY,
        category_matching_enabled=True,
        staged_engine_port=build_staged_engine_port(database_path),
        staged_engine_candidate=staged_engine_candidato(),
    )
    return ContextBuilder(
        identity_repository=build_sqlite_identity_repository(database_path),
        project_repository=project_repository,
        memory_repository=memory_repository,
        conversation_repository=build_sqlite_conversation_repository(database_path),
        decision_repository=decision_repository,
        rank_relevant_knowledge_use_case=rank_relevant_knowledge_use_case,
        event_repository=build_sqlite_event_repository(database_path),
        token_counter=CharacterHeuristicTokenCounter(),
        relevance_filter_port=relevance_filter_port,
        max_criticality_category=_MAX_CRITICALITY_CATEGORY,
        category_matching_enabled=True,
    )


def _cliente_ollama_disponible_dentro_del_presupuesto(timeout_seconds: float) -> httpx.Client:
    """Escenario (a): Ollama responde con una latencia local realista, muy
    por debajo del ``timeout``, con una respuesta válida con la forma que
    Ollama produce de verdad."""

    def handler(request: httpx.Request) -> httpx.Response:
        time.sleep(min(0.02, timeout_seconds / 2))
        return httpx.Response(200, json={"response": json.dumps({"keep": []})})

    return httpx.Client(transport=httpx.MockTransport(handler), timeout=timeout_seconds)


def _cliente_ollama_ausente(timeout_seconds: float) -> httpx.Client:
    """Escenario (b): conexión rechazada de inmediato — nunca espera al
    ``timeout``, el fallo abierto más barato de los tres."""

    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("conexión rechazada (doble de prueba, M11 §6.4)", request=request)

    return httpx.Client(transport=httpx.MockTransport(handler), timeout=timeout_seconds)


class _TransporteQueAceptaYNuncaContesta:
    """Escenario (c) — incidencia #435, hallazgo CODEX-003: Ollama acepta la
    conexión y no responde hasta agotar el presupuesto de tiempo completo, a
    diferencia de un rechazo inmediato. Es el peor caso real que RNF-003 debe
    soportar, y el único de los tres cuyo coste incluye la espera entera.

    No duerme esa espera (ADR-125). Antes sí lo hacía: con 50 ms era barato;
    con los 30 s de producción, dormirla en cada una de las 31 llamadas de
    ``_medir`` costaría ~15 minutos para medir una constante ya conocida.
    Lo que el adaptador ve cuando Ollama agota la espera es un ``ReadTimeout``,
    y eso es lo que este doble lanza al instante; además **cuenta cada
    invocación**, porque lo que hay que comprobar en este escenario no es
    cuánto dura la espera —es una constante— sino que el filtro se llama de
    verdad. El coste de la espera se suma aparte en las pruebas:
    ``coste total = coste medido + espera``, exactamente lo que medía el
    doble que dormía, sin pagarlo en tiempo de suite."""

    def __init__(self) -> None:
        self.invocaciones = 0

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.invocaciones += 1
        raise httpx.ReadTimeout(
            "Ollama acepta la conexión y no responde (doble de prueba, M11 §6.4)", request=request
        )


def _cliente_ollama_acepta_y_agota_el_timeout(
    timeout_seconds: float,
) -> tuple[httpx.Client, _TransporteQueAceptaYNuncaContesta]:
    """Escenario (c): el cliente y su transporte, para poder leer las
    invocaciones después de medir."""
    transporte = _TransporteQueAceptaYNuncaContesta()
    client = httpx.Client(transport=httpx.MockTransport(transporte), timeout=timeout_seconds)
    return client, transporte


NOMBRE_DEL_ESCENARIO_C = "Ollama acepta la conexión y agota el timeout"

#: Los dos escenarios que no pagan la espera; el (c) se construye aparte con
#: ``_cliente_ollama_acepta_y_agota_el_timeout`` porque necesita exponer su
#: transporte.
_ESCENARIOS_RNF_003: tuple[tuple[str, Callable[[float], httpx.Client]], ...] = (
    ("Ollama disponible dentro del presupuesto", _cliente_ollama_disponible_dentro_del_presupuesto),
    ("Ollama ausente (conexión rechazada)", _cliente_ollama_ausente),
)


def _medir_escenario_c(
    banco: BancoDePruebas, timeout_seconds: float
) -> tuple[Medicion, _TransporteQueAceptaYNuncaContesta]:
    """Mide «construir contexto» en el escenario (c) sin dormir la espera y
    devuelve también el transporte, con el número de invocaciones."""
    client, transporte = _cliente_ollama_acepta_y_agota_el_timeout(timeout_seconds)
    adapter = OllamaRelevanceFilterAdapter(
        _RELEVANCE_FILTER_MODEL, timeout_seconds=timeout_seconds, client=client
    )
    builder = _build_context_builder_with_relevance_filter(banco.database_path, adapter)

    def _construir(builder: ContextBuilder = builder) -> object:
        return builder.build("cómo vamos con el despliegue")

    return _medir("construir contexto", _construir), transporte


@pytest.mark.integration
def test_construir_contexto_con_el_paquete_completo_activo_en_los_tres_escenarios(  # type: ignore[no-untyped-def]
    banco: BancoDePruebas, capsys
) -> None:
    """M11 (§6.4): con la puerta de D7 punto 6 abierta y el filtro de
    relevancia cableado de verdad —nunca Ollama real dentro de la suite, un
    doble determinista del transporte HTTP por escenario— mide «construir
    contexto» sobre el mismo conjunto de referencia de ADR-008 en los tres
    escenarios que §6.4 fija: ninguno se da por gratuito, ni siquiera el
    rechazo inmediato.

    ``timeout_seconds`` es ``composition_root._RELEVANCE_FILTER_TIMEOUT_SECONDS``
    — el valor real con el que producción construye el adaptador — para que
    esta medición sea la que de verdad decide ese valor (§6.4 punto 2), no
    una aproximación con un número distinto.

    ADR-125 suspende el límite de 300 ms en el camino del filtro mientras se
    mide su coste real y fija la espera en 30 s. El escenario (c) ya no duerme
    esa espera (ver ``_TransporteQueAceptaYNuncaContesta``): se mide el coste
    del motor con un doble que falla al instante y cuenta las invocaciones, se
    afirma que el filtro se invocó de verdad, y el coste total se publica como
    ``medido + espera``. El guardarraíl se afirma sobre el coste medido en los
    tres escenarios: la espera es una constante de política (ADR-125), no una
    regresión que este tope pueda cazar.
    """
    timeout_seconds = _RELEVANCE_FILTER_TIMEOUT_SECONDS
    espera_ms = timeout_seconds * 1000
    mediciones: list[tuple[str, Medicion, float]] = []
    for nombre, construir_cliente in _ESCENARIOS_RNF_003:
        adapter = OllamaRelevanceFilterAdapter(
            _RELEVANCE_FILTER_MODEL,
            timeout_seconds=timeout_seconds,
            client=construir_cliente(timeout_seconds),
        )
        builder = _build_context_builder_with_relevance_filter(banco.database_path, adapter)

        def _construir(builder: ContextBuilder = builder) -> object:
            return builder.build("cómo vamos con el despliegue")

        medicion = _medir("construir contexto", _construir)
        mediciones.append((nombre, medicion, medicion.p95))

    medicion_c, transporte_c = _medir_escenario_c(banco, timeout_seconds)
    mediciones.append((NOMBRE_DEL_ESCENARIO_C, medicion_c, medicion_c.p95 + espera_ms))

    with capsys.disabled():
        print(f"\n  M11 — RNF-003, paquete completo activo, timeout={espera_ms:.0f} ms:")
        print("  | Escenario | P95 medido | P95 total | Límite |")
        print("  |---|---|---|---|")
        for nombre, medicion, total in mediciones:
            print(
                f"  | {nombre} | {medicion.p95:.1f} ms | {total:.1f} ms "
                f"| {LIMITE_OPERACION_MS:.0f} ms |"
            )
        print(
            f"  (c): {transporte_c.invocaciones} invocaciones al filtro; el total suma "
            f"la espera de producción ({espera_ms:.0f} ms) sin dormirla (ADR-125)."
        )

    # El escenario (c) solo dice algo si el filtro se invocó de verdad: si una
    # regresión lo desconectara, su coste medido sería el de (b) y la espera
    # nunca se pagaría en producción tampoco — pero eso es un defecto, no una
    # mejora, y aquí se caza.
    assert transporte_c.invocaciones >= 1, (
        "el escenario (c) no llegó a invocar al filtro de relevancia: el filtro está "
        "desconectado del camino de construir contexto."
    )

    # Guardarraíl (ADR-007), no el requisito: el requisito de 300 ms lo
    # comprueba PA-025 en la máquina real; el margen sobre este conjunto de
    # referencia y esta máquina no llega al orden de magnitud que ADR-007
    # exige para afirmarlo aquí como aserción dura. La tabla impresa arriba
    # es la evidencia publicada del encargo M11. Se afirma sobre el coste
    # MEDIDO: la espera sumada en (c) es una constante de ADR-125.
    excedidas = [(nombre, m) for nombre, m, _total in mediciones if m.p95 > GUARDARRAIL_MS]
    assert not excedidas, (
        "Escenarios de RNF-003 por encima del guardarraíl de "
        f"{GUARDARRAIL_MS:.0f} ms: {[(n, str(m)) for n, m in excedidas]}."
    )


@pytest.mark.integration
@pytest.mark.xfail(
    strict=True,
    reason=(
        "M11 (incidencia #471, decisión del propietario del 31-08-2026 "
        "06:48, ADR-117 sección 'Estado del hito: decisión'): el suelo de "
        "RNF-003 en el camino integrado real (P95 <= 300 ms, "
        "LIMITE_OPERACION_MS, en los tres escenarios de la incidencia "
        "#435/CODEX-003) queda explícitamente NO aprobado -- hoy las tres "
        "cifras miden muy por encima de 300 ms (ADR-117). Esta prueba "
        "afirma el requisito tal cual está escrito (CODEX-003, "
        "https://github.com/canelamoraguezandyjesus-bot/sirius/pull/472#discussion_r3892166675) "
        "y falla-como-se-espera; el día que el motor por etapas baje de "
        "300 ms P95 en los tres escenarios, strict=True hará que pase "
        "inesperadamente y obligue a retirar la marca xfail -- el hito solo "
        "se aprueba cuando eso sea verdad."
    ),
)
def test_el_suelo_de_rnf_003_p95_300ms_en_los_tres_escenarios_del_paquete_completo(
    banco: BancoDePruebas,
) -> None:
    """Criterio de aceptación de RNF-003/§8-M11
    (`docs/evolution/SIRIUS_ARQUITECTURA_TECNICA_0.2_v0.1_PROPUESTO.md:1415-1418`),
    convertido en prueba ejecutable honesta por decisión del propietario
    (incidencia #471, comentario del 31-08-2026 06:48). Reconstruye los
    mismos tres escenarios que
    `test_construir_contexto_con_el_paquete_completo_activo_en_los_tres_escenarios`
    y afirma el límite real de RNF-003 (`LIMITE_OPERACION_MS`), no el
    guardarraíl de disparate (`GUARDARRAIL_MS`) que esa prueba usa -- ver el
    `reason` de arriba y ADR-117.

    El escenario (c) no duerme la espera de producción (ADR-125, ver
    ``_TransporteQueAceptaYNuncaContesta``): mide el coste del motor con un
    doble que falla al instante y cuenta las invocaciones, y afirma sobre el
    coste total ``medido + espera``. La espera solo se suma si el filtro se
    invocó de verdad: con el filtro cableado, (c) falla por construcción
    mientras la espera supere los 300 ms (sostiene el ``xfail``); si una
    regresión desconectara el filtro, no habría espera que sumar y el día que
    el motor baje de 300 ms esta prueba pasaría — el XPASS estricto que
    alerta del problema, igual que antes de ADR-125 y sin pagar 15 minutos.
    """
    timeout_seconds = _RELEVANCE_FILTER_TIMEOUT_SECONDS

    mediciones_ab: list[tuple[str, Medicion]] = []
    for nombre, construir_cliente in _ESCENARIOS_RNF_003:
        adapter = OllamaRelevanceFilterAdapter(
            _RELEVANCE_FILTER_MODEL,
            timeout_seconds=timeout_seconds,
            client=construir_cliente(timeout_seconds),
        )
        builder = _build_context_builder_with_relevance_filter(banco.database_path, adapter)

        def _construir(builder: ContextBuilder = builder) -> object:
            return builder.build("cómo vamos con el despliegue")

        mediciones_ab.append((nombre, _medir("construir contexto", _construir)))

    medicion_c, transporte_c = _medir_escenario_c(banco, timeout_seconds)
    espera_pagada_ms = timeout_seconds * 1000 if transporte_c.invocaciones else 0.0
    total_c = medicion_c.p95 + espera_pagada_ms

    for nombre, medicion in mediciones_ab:
        assert medicion.p95 <= LIMITE_OPERACION_MS, (
            f"{nombre}: {medicion} supera el límite aprobado de {LIMITE_OPERACION_MS:.0f} ms."
        )
    assert total_c <= LIMITE_OPERACION_MS, (
        f"{NOMBRE_DEL_ESCENARIO_C}: {medicion_c} + espera de producción "
        f"{espera_pagada_ms:.0f} ms = {total_c:.1f} ms supera el límite aprobado de "
        f"{LIMITE_OPERACION_MS:.0f} ms."
    )
