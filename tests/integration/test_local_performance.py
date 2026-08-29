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
"""

from __future__ import annotations

import statistics
import time
from collections.abc import Callable, Iterator
from pathlib import Path

import pytest

from sirius.adapters.llm.token_counter import CharacterHeuristicTokenCounter
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
from sirius.application.context import ContextBuilder
from sirius.application.knowledge_overview import GetKnowledgeOverviewUseCase
from sirius.application.rank_relevant_knowledge import RankRelevantKnowledgeUseCase
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
