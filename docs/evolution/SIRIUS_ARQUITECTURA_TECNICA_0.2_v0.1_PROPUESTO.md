# Arquitectura Técnica — Sirius 0.2 «Memoria útil»

**Identificador:** `SIRIUS-ARQ-0.2`
**Versión:** v0.1
**Estado:** PROPUESTO
**Fecha:** 29 de agosto de 2026
**Autoridad final:** usuario propietario del Proyecto Sirius

> La aprobación de este documento es la fusión de la Pull Request que lo introduce,
> por el propietario. Este documento **no autoriza implementación**: es una de las dos
> puertas de activación que `docs/evolution/RECTOR.md` §17 exige antes de construir una
> versión (`docs/evolution/RECTOR.md:282-290`); la otra es la Definición de Producto, ya
> propuesta (`docs/evolution/SIRIUS_PRODUCTO_0.2_MEMORIA_UTIL_v0.1_PROPUESTO.md`). Nada de
> lo aquí diseñado queda autorizado fuera de lo que registra
> `docs/evolution/STATUS.md`.

## 0. Origen y jerarquía

Este documento desarrolla `docs/evolution/RECTOR.md` §9.1 («Sirius 0.2 — Memoria útil»,
`docs/evolution/RECTOR.md:139-146`) y la Definición de Producto de esta versión
(`docs/evolution/SIRIUS_PRODUCTO_0.2_MEMORIA_UTIL_v0.1_PROPUESTO.md`, ya PROPUESTA), bajo
la jerarquía documental que fija `RECTOR.md` §16 (`docs/evolution/RECTOR.md:268-280`): el
Rector fija dirección y puertas; la Definición de Producto desarrolla el problema, el
alcance y la evidencia; esta Arquitectura Técnica traduce esa definición a diseño sobre la
arquitectura hexagonal existente, sin sustituir a ninguno de los dos documentos anteriores
y sin activarse por sí sola (`RECTOR.md` §17, `docs/evolution/RECTOR.md:282-290`).

Todas las afirmaciones sobre el estado actual de Sirius 0.1 que hace este documento se han
verificado directamente contra `main` (rama base `main`, sin leer `evidence/adr001-spikes`
ni la PR #117 — ver §7 de la Definición de Producto sobre por qué esa rama queda fuera).
La regla que sigue este documento es la misma que exige la incidencia que lo origina y que
ya siguió la Definición de Producto: cada afirmación comprobable cita fichero y línea
(ADR-001); lo que no se ha podido demostrar se marca como decisión pendiente, nunca se
inventa.

### 0.1 Principios transversales de diseño heredados de Sirius 0.1

Este documento diseña **sobre** la arquitectura hexagonal existente (dominio, aplicación,
adaptadores, presentación) y las ATD-001 a ATD-012 vigentes
(`docs/canonical/STATUS.md:12`); no las sustituye ni las reabre. Los principios que seguirá
cada bloque de diseño de este documento, ya establecidos en Sirius 0.1 y confirmados contra
`main`:

1. **Dirección de dependencias.** «presentación -> aplicación -> dominio; los adaptadores
   implementan puertos del dominio/aplicación» (`AGENTS.md:68`). Ningún diseño de este
   documento invierte esa dirección: la presentación nunca toca un puerto ni SQLAlchemy
   directamente, y el dominio nunca importa de aplicación, adaptadores o presentación.
2. **Ninguna capacidad nueva es automática por diseño.** `ProposeDecisionUseCase` y
   `SaveManualMemoryUseCase` documentan explícitamente que nada en `SendMessageUseCase`
   los invoca (`src/sirius/application/propose_decision.py:8-11`,
   `src/sirius/application/save_manual_memory.py:9-13`), y `SendMessageUseCase.send_message`
   (`src/sirius/application/send_message.py:138-218`) en efecto no importa ni llama a
   ninguno de los dos. Todo lo que este documento añade sigue exactamente ese contrato: una
   capacidad nueva es una llamada explícita y separada, nunca un efecto secundario de enviar
   un mensaje.
3. **Sirius no tiene juicio semántico propio.** `sirius.domain.precedence` lo declara sin
   ambigüedad: «Sirius has no semantic understanding of memory content (no LLM judgement,
   no embeddings, no classifier...)» (`src/sirius/domain/precedence.py:9-10`). Este
   documento respeta esa frontera: en ningún bloque diseña un mecanismo que decida por sí
   mismo, con juicio propio, qué guardar o qué es relevante; cuando el Producto pide algo que
   rozaría esa frontera (§2, §3), este documento se limita a señalar el punto de integración
   sin diseñar el juicio en sí, exactamente como exige el objetivo de esta incidencia.
4. **Evento y cambio en la misma transacción.** `UnitOfWork` (`src/sirius/ports/unit_of_work.py:34-85`)
   agrupa repositorios en una única transacción; todo caso de uso que escribe un evento y un
   cambio de estado a la vez (`ProposeDecisionUseCase`, `SaveManualMemoryUseCase`,
   `CorrectMemoryUseCase`) lo hace a través de él. Cada caso de uso nuevo de este documento
   sigue el mismo patrón.
5. **Proponer y confirmar son pasos separados, nunca el mismo caso de uso.** B4b ya separa
   `ProposeDecisionUseCase` (crea PROPOSED) de `ApproveDecisionUseCase` (transiciona a
   APPROVED) como dos casos de uso, dos eventos y dos llamadas explícitas
   (`src/sirius/application/propose_decision.py:34-77`,
   `src/sirius/application/approve_decision.py:46-89`). El bloque «Sugerencias
   confirmadas» (§4) reutiliza literalmente esta forma, no solo su espíritu.

## 1. Alcance de este documento

Cubre, en este orden, los cinco bloques de `RECTOR.md` §9.1
(`docs/evolution/RECTOR.md:143`):

- §4 Sugerencias confirmadas — diseño completo (dominio, aplicación, migración, interfaz).
- §5 Conflictos asistidos — diseño de las acciones de resolución sobre el panel ya
  existente, sin tocar `precedence.py`.
- §6 Proyectos históricos consultables — diseño completo (puerto, aplicación, interfaz).
- §7 Búsqueda mejorada y §8 Mejor recuperación — **no** diseña la incorporación de la
  evidencia de la PR #117 ni la dependencia de Ollama (decisión del propietario, ver
  `docs/evolution/SIRIUS_PRODUCTO_0.2_MEMORIA_UTIL_v0.1_PROPUESTO.md` §7.3); se limita a
  señalar los puntos de integración que el resto del diseño debe respetar.
- §9 Impactos transversales.
- §10 Orden de construcción propuesto, con criterio de aceptación por encargo.
- §11 Decisiones pendientes del propietario.

No modifica `docs/canonical/`, el Producto, la Arquitectura Técnica de 0.1 ni ninguna
decisión ATD. No cambia comportamiento de código: es diseño, no implementación.

## 2. Convención de nomenclatura de este documento

Sirius 0.1 numeró sus verticales `B1`…`B16` (`docs/implementation/V8_EXECUTION.md`); el
Sirius Work Engine usa su propio prefijo `C` para otra cosa (contradicciones de contrato,
`docs/implementation/SIRIUS_WORK_ENGINE_ARQUITECTURA_MINIMA.md:731-827`) y también `C` para
bloques de su plan de implementación
(`docs/implementation/SIRIUS_WORK_ENGINE_PLAN_IMPLEMENTACION.md:417-497`). Para no colisionar
con ninguno de los dos, §10 numera los encargos de esta versión como `M1`…`M6`
(«Memoria útil»); es una convención propia de este documento, no continúa la serie `B` de
0.1 ni la serie `C` del motor.

## 3. Sugerencias confirmadas

### 3.1 Qué cubre ya Sirius 0.1

Nada (`docs/evolution/SIRIUS_PRODUCTO_0.2_MEMORIA_UTIL_v0.1_PROPUESTO.md` §4.1, verificado
contra `main`). `DecisionStatus` tiene exactamente `PROPOSED`, `APPROVED`, `SUPERSEDED`,
`ARCHIVED` (`src/sirius/domain/decision.py:45-48`); `MemoryStatus` tiene exactamente
`CURRENT`, `ARCHIVED`, `DELETED` (`src/sirius/domain/memory.py:15-17`). Ninguno de los dos
modela una propuesta de memoria pendiente de confirmación.

Nota de contexto de la incidencia de origen, ya no repetida como hecho aquí: los estados
`CANDIDATA`/`RECHAZADA` que una orden anterior daba por existentes en el modelo de datos no
se han localizado en `main`; el origen de Sirius Work Engine (equipo de la sesión del
propietario) es la rama de evidencia sin fusionar, no el producto — ver §11.

### 3.2 Por qué esto no es una extensión de `precedence.py` ni un juicio nuevo de Sirius

`sirius.domain.precedence` compara únicamente memorias `CURRENT` y decisiones `APPROVED`
por `subject_key`/`project_id` explícitos (`src/sirius/domain/precedence.py:24-31`). Una
sugerencia pendiente **no es una memoria**: no debe entrar nunca en esa comparación, ni
mientras está pendiente ni si se rechaza. El diseño de este bloque no toca
`sirius.domain.precedence` en ningún punto — ni sus tipos ni sus funciones — porque una
sugerencia pendiente o rechazada nunca debe ser candidata a conflicto de precedencia; solo
lo que `ConfirmSuggestionUseCase` (§3.5) llega a materializar como `Memory` real entra,
desde ese momento, en el camino ya existente.

Quién decide *cuándo* proponer una sugerencia importa tanto como el resto del diseño. La
ronda anterior de este documento dejaba esto como decisión pendiente del propietario; el
propietario la resolvió explícitamente en la incidencia de origen (comentario del
propietario, 2026-08-29T02:24:52Z, «DECISIÓN DEL PROPIETARIO... resuelve CODEX-001, el
disparador de sugerencias»): **dos vías, no una**, que convergen en el mismo estado
`PENDING` y el mismo flujo de confirmación/rechazo de §3.5.

1. **Disparador automático tras la conversación.** Al completarse un turno, la superficie de
   interfaz de §3.6 —nunca `SendMessageUseCase` en sí (§0.1.2)— llama, además del flujo ya
   existente, a `ProposeMemorySuggestionUseCase.propose(...)` cuando la respuesta del
   proveedor trae una propuesta candidata. Redacta esa propuesta el mismo proveedor de IA que
   ya procesa la conversación en 0.1 (`LLMProvider`, `src/sirius/ports/llm.py:88-101`) —
   nunca un clasificador o heurística nuevos de `sirius.domain`: el juicio de qué proponer lo
   hace el proveedor externo que ya redacta la respuesta al usuario, el mismo que hoy produce
   `LLMCompleted.text` (`src/sirius/ports/llm.py:34-40`), no el dominio de Sirius, que sigue
   sin juicio semántico propio (§0.1.3, `src/sirius/domain/precedence.py:9-10`). Tres
   condiciones de diseño, tal como las fijó el propietario, que cualquier construcción de este
   bloque debe respetar sin excepción:
   - **Nunca se autoguarda.** El disparador automático solo *propone*: la propuesta queda
     `PENDING` hasta que el usuario la confirme o la rechace explícitamente (§3.5,
     `ConfirmMemorySuggestionUseCase`/`RejectMemorySuggestionUseCase`) — el mismo camino que ya
     recorre la vía manual. El juicio final sigue siendo del usuario.
   - **Ningún proveedor ni tercero nuevo.** Solo el `LLMProvider` ya configurado, el mismo que
     ya ve la conversación para generar la respuesta; la superficie de privacidad de §7.2 no
     cambia.
   - **Sin llamada adicional por conversación, y sin que la propuesta cruce nunca como texto
     visible o persistido.** El contenido de la propuesta viaja en la misma respuesta que ya
     produce el turno — nunca en una segunda llamada al proveedor — pero **nunca dentro de
     `text`/`LLMTextDelta`**: esto no es un detalle que este documento deje sin fijar, porque
     dejarlo sin fijar es exactamente el defecto que la revisión de esta PR señaló
     (CODEX-001) contra la ronda anterior. `SendMessageUseCase.send_message` persiste
     `event.text` mediante `append_message` en la misma llamada que lo recibe, antes de
     devolver `SendMessageResult` (`src/sirius/application/send_message.py:184-210`), y
     reenvía cada `LLMTextDelta.text` a `on_delta` según llega, fragmento a fragmento
     (`src/sirius/application/send_message.py:196-198`) — que a su vez ya se pinta en pantalla
     en cuanto llega (`src/sirius/presentation/main_window.py:1400-1413`). Cualquier
     extracción que ocurra después de que ese texto exista como `LLMTextDelta`/
     `LLMCompleted.text` —incluida una extracción hecha por la superficie de interfaz de
     §3.6— llega tarde: el fragmento con el delimitador o la propuesta cruda ya se mostró y,
     si formaba parte de `LLMCompleted.text`, ya quedó grabado en la conversación
     (`src/sirius/application/send_message.py:203-210`) y volverá a entrar en un contexto
     futuro (`src/sirius/application/context.py:169-174`). La separación solo puede ocurrir
     en la frontera del adaptador concreto de `LLMProvider`, antes de que ese texto exista
     como evento del puerto. Por eso `LLMCompleted` (`src/sirius/ports/llm.py:34-40`) gana un
     campo nuevo, `memory_suggestion: str | None = None`: el adaptador concreto —nunca
     `SendMessageUseCase`, nunca la superficie de interfaz— detecta el delimitador
     distinguible en la salida cruda del proveedor y lo separa antes de emitir un solo
     `LLMTextDelta` o de construir el `LLMCompleted` final, de modo que ni un delta ni
     `LLMCompleted.text` contienen jamás el delimitador ni la propuesta cruda.
     `SendMessageResult` (`src/sirius/application/send_message.py:50-63`) gana el campo
     espejo `memory_suggestion: str | None`, copiado de `LLMCompleted.memory_suggestion`
     únicamente cuando `outcome` es `COMPLETED` — `SendMessageUseCase` se limita a
     transportarlo sin interpretarlo ni llamar con él a `ProposeMemorySuggestionUseCase`
     (§0.1.2, §3.5): quien decide llamar sigue siendo la superficie de interfaz de §3.6, ahora
     leyendo este campo ya separado en vez de volver a analizar el texto que ya se mostró y
     persistió. Si separar el delimitador dentro del adaptador exigiera una segunda llamada al
     proveedor por conversación, quien construya M6 se detiene y vuelve a consultar al
     propietario (§9), porque el coste es su decisión, no una que este documento tome por él.

2. **Botón manual «Proponer guardar…»** (§3.6), la vía que esta arquitectura ya diseñaba en la
   ronda anterior, se conserva **además** de la automática, como vía complementaria iniciada
   por el propio usuario — para ideas de mejora, herramientas a evaluar o cualquier apunte que
   quiera proponer por sí mismo, sin esperar a que el proveedor lo sugiera.

Esta es una excepción explícita y acotada a esta única capacidad, decidida por el
propietario, no una relajación general: el principio §0.1.2 («ninguna capacidad nueva es
automática por diseño») sigue gobernando sin cambios todo lo demás que diseña este
documento — el disparador automático de sugerencias no lo reabre; lo autoriza el propietario
punto por punto, para este bloque y ningún otro.

### 3.3 Dominio nuevo: `MemorySuggestion`

Nuevo módulo `src/sirius/domain/memory_suggestion.py`, mirroring la forma de
`src/sirius/domain/memory.py` y `src/sirius/domain/decision.py`:

```python
class MemorySuggestionStatus(StrEnum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    REJECTED = "rejected"

@dataclass(frozen=True, slots=True)
class MemorySuggestion:
    id: int
    content: str
    status: MemorySuggestionStatus
    source_event_id: int | None
    created_at: datetime
    resolved_at: datetime | None
    resulting_memory_id: int | None = None
    subject_key: str | None = None
    project_id: int | None = None
```

Se elige deliberadamente **sin tabla de revisiones**: a diferencia de `Memory`/`Decision`,
una sugerencia no se corrige — su contenido queda fijado en el momento de proponerla y solo
tiene dos destinos posibles (confirmarse tal cual, o rechazarse); si el usuario quiere un
contenido distinto, la vía ya existente es rechazar y usar
`SaveManualMemoryUseCase` directamente, sin añadir una función de corrección que el Producto
no pide (§4.3/§4.4 de la Definición de Producto no mencionan corregir una sugerencia).

Reglas de transición (mismo patrón que `sirius.domain.memory.ensure_can_archive` /
`sirius.domain.decision.ensure_can_approve`):

```python
def ensure_can_confirm(suggestion: MemorySuggestion) -> None:
    """Solo una sugerencia PENDING puede confirmarse."""
    if suggestion.status is not MemorySuggestionStatus.PENDING:
        raise ValueError(...)

def ensure_can_reject(suggestion: MemorySuggestion) -> None:
    """Solo una sugerencia PENDING puede rechazarse."""
    if suggestion.status is not MemorySuggestionStatus.PENDING:
        raise ValueError(...)
```

No existe transición de vuelta a `PENDING` desde ninguno de los dos estados terminales —
mismo principio de monotonía que `DecisionStatus`
(`src/sirius/domain/decision.py:140-142`).

### 3.4 Puerto nuevo: `MemorySuggestionRepository`

Nuevo `src/sirius/ports/memory_suggestion_repository.py`, `Protocol` mirroring
`src/sirius/ports/memory_repository.py:10-16`:

```python
class MemorySuggestionRepository(Protocol):
    def create_suggestion(
        self, content: str, *, source_event_id: int | None = None,
        subject_key: str | None = None, project_id: int | None = None,
    ) -> MemorySuggestion: ...

    def get_suggestion(self, suggestion_id: int) -> MemorySuggestion: ...

    def list_pending_suggestions(self) -> list[MemorySuggestion]: ...

    def confirm_suggestion(
        self, suggestion_id: int, *, resulting_memory_id: int, resolved_at: datetime,
    ) -> MemorySuggestion: ...

    def reject_suggestion(
        self, suggestion_id: int, *, resolved_at: datetime,
    ) -> MemorySuggestion: ...
```

`UnitOfWork` (`src/sirius/ports/unit_of_work.py:34-85`) gana una propiedad
`memory_suggestion_repository`, igual que ya expone `memory_repository`/
`decision_repository`/`event_repository`/`conversation_repository`
(`src/sirius/ports/unit_of_work.py:46-64`): `ConfirmSuggestionUseCase` (§3.5) escribe a la
vez en `memory_repository` (crear la memoria real), `memory_suggestion_repository` (marcar
CONFIRMED) y `event_repository`, y las tres escrituras deben confirmarse o revertirse juntas
— el mismo requisito que ya obliga a S8.1 para evento + memoria
(`src/sirius/ports/unit_of_work.py:8-9`).

### 3.5 Aplicación: tres casos de uso, mirroring el patrón ya existente

**`ProposeMemorySuggestionUseCase`** (`src/sirius/application/propose_memory_suggestion.py`),
mirroring `ProposeDecisionUseCase` (`src/sirius/application/propose_decision.py:34-77`)
literalmente: valida contenido no vacío, abre un evento
`MEMORY_SUGGESTION_PROPOSED_EVENT_TYPE`, crea la sugerencia PENDING con
`source_event_id`, todo en una transacción de `UnitOfWork`. Nunca es llamado por
`SendMessageUseCase` (§0.1.2) — lo llama la superficie de interfaz descrita en §3.6.

**`ConfirmMemorySuggestionUseCase`** (`src/sirius/application/confirm_memory_suggestion.py`),
mirroring `SaveManualMemoryUseCase` (`src/sirius/application/save_manual_memory.py:48-104`)
para la parte de crear la memoria real: dentro de una única transacción de `UnitOfWork`,
obtiene la sugerencia, comprueba `ensure_can_confirm`, abre un evento
`MEMORY_SUGGESTION_CONFIRMED_EVENT_TYPE`, llama a
`memory_repository.create_memory(content=suggestion.content, origin="Sugerencia
confirmada por el usuario", source_event_id=event.id, subject_key=suggestion.subject_key,
project_id=suggestion.project_id)` (misma forma que
`src/sirius/application/save_manual_memory.py:95-101`), y por último
`memory_suggestion_repository.confirm_suggestion(suggestion_id,
resulting_memory_id=memory.id, resolved_at=...)`. Devuelve la `Memory` creada. Esto satisface
literalmente el criterio de comprobación de la Definición de Producto §4.4: «confirmarla la
deja como memoria... vigente con origen trazable (mismo patrón que
`SaveManualMemoryUseCase`/`ProposeDecisionUseCase`)».

**`RejectMemorySuggestionUseCase`** (`src/sirius/application/reject_memory_suggestion.py`):
dentro de una transacción de `UnitOfWork`, obtiene la sugerencia, comprueba
`ensure_can_reject`, abre un evento `MEMORY_SUGGESTION_REJECTED_EVENT_TYPE`, y llama a
`memory_suggestion_repository.reject_suggestion(suggestion_id, resolved_at=...)`. **Nunca**
crea una `Memory`, nunca escribe en `memory_repository`. Como ni `ContextBuilder`
(`src/sirius/application/context.py:143-208`) ni `RankRelevantKnowledgeUseCase`
(`src/sirius/application/rank_relevant_knowledge.py:47-86`) leen jamás
`MemorySuggestionRepository` — ninguno de los dos lo recibe como dependencia en este
diseño —, una sugerencia rechazada no puede aparecer en ningún contexto ordinario. Esto
satisface literalmente la otra mitad del criterio §4.4: «rechazarla no deja ningún rastro
en el contexto ordinario».

Tres nuevos tipos de evento en `src/sirius/domain/event.py`, junto a los ya existentes
(`src/sirius/domain/event.py:24-31`):

```python
MEMORY_SUGGESTION_PROPOSED_EVENT_TYPE = "memory_suggestion.proposed"
MEMORY_SUGGESTION_CONFIRMED_EVENT_TYPE = "memory_suggestion.confirmed"
MEMORY_SUGGESTION_REJECTED_EVENT_TYPE = "memory_suggestion.rejected"
```

### 3.6 Superficie de interfaz

**Proponer — dos vías, convergen en el mismo estado pendiente (§3.2).**

*Automática.* Al terminar un turno con `outcome` `COMPLETED`
(`SendMessageResult.outcome`, `src/sirius/application/send_message.py:50-63`) y con
`SendMessageResult.memory_suggestion` no nulo (§3.2 — el campo que `SendMessageUseCase`
transporta ya separado por el adaptador de `LLMProvider`, nunca extraído a posteriori de
`sirius_message.content` ni de los fragmentos ya mostrados por `on_delta`), la superficie
que ya orquesta el envío del mensaje —nunca `SendMessageUseCase` en sí— llama
automáticamente, sin que el usuario pulse nada, a
`ProposeMemorySuggestionUseCase.propose(result.memory_suggestion,
message_id=result.sirius_message.id)`. Si el turno no completa (`CANCELLED`/`FAILED`) o
`memory_suggestion` es `None`, no se llama a nada — igual que hoy no se persiste una
`Memory` cuando no hay guardado manual.

*Manual.* `MessageItemWidget` (`src/sirius/presentation/message_view.py:247-321`) ya
tiene, por mensaje, una fila de acciones (`copy_buttons`,
`src/sirius/presentation/message_view.py:319-321`); un turno de Sirius completado gana ahí
un botón «Proponer guardar…» que abre el mismo diálogo de texto que
`_handle_save_memory_clicked` ya usa para guardado manual
(`src/sirius/presentation/knowledge_widget.py:308-309` y su manejador), precargado con el
contenido del mensaje, editable antes de confirmarlo, y llama a
`ProposeMemorySuggestionUseCase.propose(content, message_id=...)`. Es una acción explícita
del usuario sobre un turno ya completado, complementaria a la automática y nunca su
sustituta (§3.2).

**Confirmar/rechazar.** `KnowledgeOverview` (`src/sirius/application/knowledge_overview.py:30-48`)
gana un campo `pending_suggestions: tuple[MemorySuggestion, ...]`, y
`GetKnowledgeOverviewUseCase.get_overview()` (`src/sirius/application/knowledge_overview.py:60-68`)
gana la dependencia `memory_suggestion_repository` y una llamada a
`list_pending_suggestions()`, exactamente como ya agrega `list_current_memories()` y
`list_proposed_decisions()`. `KnowledgeWidget` (`src/sirius/presentation/knowledge_widget.py:197-256`)
gana una tercera sección, «Sugerencias pendientes», con la misma forma que
`_build_memories_section`/`_build_decisions_section`
(`src/sirius/presentation/knowledge_widget.py:304-326`): una lista y dos botones,
«Confirmar» y «Rechazar», que llaman a `ConfirmMemorySuggestionUseCase.confirm(...)` y
`RejectMemorySuggestionUseCase.reject(...)` sobre la sugerencia seleccionada, seguido de
`self.refresh()` — mismo patrón que `_handle_archive_memory_clicked`
(`src/sirius/presentation/knowledge_widget.py:377-391`).

### 3.7 Migración

Una tabla nueva, aditiva, sin tocar ninguna existente — mismo patrón que la migración
`94418c79da9d` (`migrations/versions/94418c79da9d_add_memory_subject_and_project.py:21-46`):

```python
op.create_table(
    "memory_suggestions",
    sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
    sa.Column("content", sa.Text(), nullable=False),
    sa.Column("status", sa.String(length=16), nullable=False),
    sa.Column("subject_key", sa.Text(), nullable=True),
    sa.Column("project_id", sa.Integer(), sa.ForeignKey("projects.id"), nullable=True),
    sa.Column("source_event_id", sa.Integer(), sa.ForeignKey("events.id"), nullable=True),
    sa.Column("resulting_memory_id", sa.Integer(), sa.ForeignKey("memories.id"), nullable=True),
    sa.Column("created_at", sa.DateTime(), nullable=False),
    sa.Column("resolved_at", sa.DateTime(), nullable=True),
)
```

Sin índice de unicidad: a diferencia de `projects` (`uq_projects_single_active`,
`src/sirius/adapters/persistence/models.py:142-149`), nada impide varias sugerencias
pendientes a la vez, ni siquiera del mismo asunto — la ambigüedad entre sugerencias, si
llega a haberla, la resuelve el usuario confirmando o rechazando cada una, no una
restricción de esquema.

## 4. Conflictos asistidos

### 4.1 Qué cubre ya Sirius 0.1

Detección y presentación completas, solo lectura. `evaluate_subject_precedence`/
`find_subject_conflicts` (`src/sirius/domain/precedence.py:123-192`),
`DetectPrecedenceConflictsUseCase` (`src/sirius/application/detect_precedence_conflicts.py:28-46`),
y `KnowledgeWidget._build_conflicts_section`/`_handle_detect_conflicts_clicked`
(`src/sirius/presentation/knowledge_widget.py:627-669`) ya listan cada conflicto pendiente
sin elegir nunca un ganador.

Lo que falta, verificado contra `main`: la lista de conflictos
(`self.conflicts_list`, `src/sirius/presentation/knowledge_widget.py:631-641`) es de solo
lectura — no conecta con `_correct_memory_use_case`, `_archive_memory_use_case`,
`_approve_decision_use_case` ni `_supersede_decision_use_case`, que ya están inyectados en
el mismo widget (`src/sirius/presentation/knowledge_widget.py:228-235`) y ya tienen sus
propios botones sobre `memories_list`/`decisions_list`
(`_handle_correct_memory_clicked:356`, `_handle_archive_memory_clicked:377`,
`_handle_approve_decision_clicked:510`, `_handle_supersede_decision_clicked:533`,
`_handle_archive_decision_clicked:583`, todas en
`src/sirius/presentation/knowledge_widget.py`).

### 4.2 Diseño: cero cambios de dominio o aplicación

Este bloque es **exclusivamente interfaz**. No se añade ningún caso de uso nuevo, ningún
puerto nuevo, ninguna migración: los cuatro casos de uso de resolución
(`CorrectMemoryUseCase`, `ArchiveMemoryUseCase`, `ApproveDecisionUseCase`,
`SupersedeDecisionUseCase`) ya existen, ya están inyectados en `KnowledgeWidget`, y
`sirius.domain.precedence` permanece sin tocar — ni un solo símbolo de
`src/sirius/domain/precedence.py` cambia.

El único cambio: `conflicts_list` (`src/sirius/presentation/knowledge_widget.py:631`) deja
de construir una única línea de texto por conflicto
(`src/sirius/presentation/knowledge_widget.py:660-669`), porque esa única línea no permite
seleccionar un miembro concreto: representa a la vez a todos los `Memory`/`Decision` en
conflicto, y ninguno de los manejadores de resolución acepta una colección. Por cada
`SubjectPrecedenceResult` en `CONFLICT`, `_handle_detect_conflicts_clicked` añade primero un
`QListWidgetItem` de cabecera no seleccionable (sin el flag `Qt.ItemFlag.ItemIsSelectable`,
texto «Asunto «{subject_key}» (proyecto {project_id})»`, igual al que hoy construyen `parts`)
y a continuación un `QListWidgetItem` seleccionable por cada miembro individual de
`conflict.conflicting_memories`/`conflict.conflicting_decisions` — nunca uno por el conflicto
completo. Cada ítem hijo guarda, como dato asociado (`Qt.ItemDataRole.UserRole`), exactamente
un objeto `Memory` o `Decision` (nunca la tupla completa que trae el propio
`SubjectPrecedenceResult`, `src/sirius/domain/precedence.py:61-79`) — mismo patrón que ya usan
`memories_list`/`decisions_list` (`src/sirius/presentation/knowledge_widget.py:684-688` y
`src/sirius/presentation/knowledge_widget.py:690-698`).

Un nuevo `_selected_conflict_entity`, mirroring literalmente `_selected_memory`/
`_selected_decision` (`src/sirius/presentation/knowledge_widget.py:332-337` y
`src/sirius/presentation/knowledge_widget.py:473-478`), lee
`conflicts_list.currentItem()` y devuelve ese dato solo si es una instancia de `Memory` o de
`Decision`; la cabecera nunca lo produce, porque al no llevar `ItemIsSelectable` no puede
convertirse en `currentItem()`. Seleccionar uno de esos ítems hijos habilita, sobre la
entidad concreta que devuelve `_selected_conflict_entity`, **únicamente los botones que de
verdad pueden resolver el conflicto desde esa selección** — nunca los cuatro que ya existen
en el panel general:

- Para una `Memory`, solo `archive_memory_button`
  (`src/sirius/presentation/knowledge_widget.py:310-313`). `correct_memory_button` queda
  deshabilitado desde `conflicts_list`: `CorrectMemoryUseCase.correct()` solo crea una
  revisión nueva y conserva `status`, `subject_key` y `project_id`
  (`src/sirius/application/correct_memory.py:64-108`), así que una memoria corregida sigue
  siendo `CURRENT` del mismo asunto/proyecto y `find_subject_conflicts()`
  (`src/sirius/domain/precedence.py:166-192`) la sigue contando — el conflicto reaparece
  intacto. Solo `ArchiveMemoryUseCase`, al mover la memoria fuera de `CURRENT`, la retira de
  esa cuenta.
- Para una `Decision`, solo `supersede_decision_button` y `archive_decision_button` (mismos
  nombres que sus manejadores). `approve_decision_button` queda deshabilitado desde
  `conflicts_list`: toda decisión que aparece en `conflicting_decisions` ya es `APPROVED` —
  es la única condición que admite `_approved_decisions_for_subject`
  (`src/sirius/domain/precedence.py:98-108`) —, y `ApproveDecisionUseCase.approve()` solo
  transiciona una decisión `PROPOSED` (`src/sirius/application/approve_decision.py:55-79`);
  pulsar «Aprobar» sobre una decisión ya aprobada terminaría siempre en
  `InvalidDecisionStatusError`, nunca en una resolución.

Resolverlo (archivar una memoria, o archivar/sustituir una decisión) reutiliza literalmente
`_handle_archive_memory_clicked`, `_handle_supersede_decision_clicked` y
`_handle_archive_decision_clicked` ya escritos — llamando a los mismos métodos internos sobre
la entidad única seleccionada desde `conflicts_list` en vez de exigir que el usuario la
vuelva a buscar en `memories_list`/`decisions_list`. Esto exige separar, en cada manejador
afectado, la obtención de la entidad de la acción sobre ella: la lógica interna que archiva o
sustituye pasa a aceptar la entidad como parámetro explícito, y cada botón se la resuelve
desde la lista que lo originó —`conflicts_list` vía `_selected_conflict_entity`,
`memories_list`/`decisions_list` vía `_selected_memory`/`_selected_decision`—, de modo que
actuar desde `conflicts_list` nunca dependa de lo que esté seleccionado en el panel general.
`_handle_correct_memory_clicked` y
`_handle_approve_decision_clicked` siguen existiendo tal cual y siguen operando sobre
`memories_list`/`decisions_list` fuera de este flujo — este diseño no los elimina, solo no
los ofrece como resolución de un conflicto desde `conflicts_list`. Tras cualquier
resolución, `self.refresh()` (`src/sirius/presentation/knowledge_widget.py:673-679`) ya
vuelve a llamar a `GetKnowledgeOverviewUseCase` y `_handle_detect_conflicts_clicked` puede
volver a invocarse — una detección posterior ya no reporta el conflicto resuelto, porque
`find_subject_conflicts` (`src/sirius/domain/precedence.py:166-192`) vuelve a evaluarlo
sobre el estado ya actualizado, sin ningún cambio en esa función.

Esto satisface el criterio de comprobación de la Definición de Producto §5.4 sin invención
adicional: «Un conflicto real... aparece visible en la interfaz con las opciones de
resolución existentes..., y resolverlo hace que una detección posterior deje de
reportarlo».

## 5. Proyectos históricos consultables

### 5.1 Qué cubre ya Sirius 0.1

`ProjectStatus` ya distingue `ACTIVE`/`COMPLETED` (`src/sirius/domain/project.py:10-22`);
`ProjectModel.status`/`ProjectModel.completed_at` ya son columnas reales
(`src/sirius/adapters/persistence/models.py:151-168`);
`ProjectRepository.get_project(project_id)` ya puede devolver un proyecto completado por id
(`src/sirius/ports/project_repository.py:30-36`), y
`ProjectRepository.list_project_revisions(project_id)` ya devuelve su historial completo de
revisiones (`src/sirius/ports/project_repository.py:38-44`). Lo único que falta,
verificado por lectura completa del protocolo (`src/sirius/ports/project_repository.py:12-102`):
ningún método **lista** proyectos `COMPLETED` sin conocer de antemano su id — no hay vía
para descubrirlos.

### 5.2 Puerto: un método nuevo, cero migración

`ProjectRepository` (`src/sirius/ports/project_repository.py:12`) gana:

```python
def list_completed_projects(self) -> tuple[Project, ...]:
    """Return every COMPLETED project, most recently completed first.

    Never includes the ACTIVE project. Empty when none has been completed yet.
    """
    ...
```

`SqliteProjectRepository` (`src/sirius/adapters/persistence/sqlite_project_repository.py:138`)
lo implementa con la misma forma que `get_active_project`
(`src/sirius/adapters/persistence/sqlite_project_repository.py:171-176`):

```python
def list_completed_projects(self) -> tuple[Project, ...]:
    with session_scope(self._session_factory) as session:
        models = session.scalars(
            select(ProjectModel)
            .where(ProjectModel.status == ProjectStatus.COMPLETED)
            .order_by(ProjectModel.completed_at.desc())
        ).all()
        return tuple(_load_project(session, model) for model in models)
```

Sin migración: `status` y `completed_at` ya son columnas físicas
(`src/sirius/adapters/persistence/models.py:153-168`); esto es una consulta nueva sobre
datos ya persistidos, no un cambio de esquema.

### 5.3 Aplicación: un caso de uso de solo lectura

Nuevo `src/sirius/application/historical_projects.py`, mirroring
`ProjectContinuityUseCase` (`src/sirius/application/project_continuity.py:70-88`) en forma
pero exclusivamente de lectura — nunca crea, nunca modifica:

```python
class HistoricalProjectsUseCase:
    def __init__(self, project_repository: ProjectRepository) -> None:
        self._project_repository = project_repository

    def list_completed(self) -> tuple[Project, ...]:
        """Every COMPLETED project; never the ACTIVE one, never a side effect."""
        return self._project_repository.list_completed_projects()

    def get_revision_history(self, project_id: int) -> tuple[ProjectRevision, ...]:
        """Full revision history of one project, whatever its status."""
        return self._project_repository.list_project_revisions(project_id)
```

Ninguno de los dos métodos escribe nunca — igual que
`DetectPrecedenceConflictsUseCase.detect()` (`src/sirius/application/detect_precedence_conflicts.py:37-46`)
solo lee, este caso de uso solo lee, y no queda inyectado en `ContextBuilder`
(`src/sirius/application/context.py:117-141`) ni en `SendMessageUseCase`
(`src/sirius/application/send_message.py:119-127`): consultar el historial de un proyecto
cerrado nunca contamina el contexto del proyecto activo ni la conversación en curso.

### 5.4 Superficie de interfaz: vista separada, nunca mezclada con el proyecto activo

Nuevo `src/sirius/presentation/historical_projects_widget.py`, deliberadamente **distinto**
de `ProjectContinuityWidget` (`src/sirius/presentation/project_continuity_widget.py`), que
sigue mostrando en exclusiva el proyecto `ACTIVE`
(`src/sirius/application/project_continuity.py:77-88`, que lanza
`ProjectNotConfiguredError` si no hay uno). El widget nuevo:

- una lista de proyectos completados (nombre, fecha de cierre), poblada por
  `HistoricalProjectsUseCase.list_completed()`;
- al seleccionar uno, un panel de solo lectura con su historial de revisiones
  (objetivo, estado, bloqueos, siguiente paso por versión), poblado por
  `HistoricalProjectsUseCase.get_revision_history(project_id)`;
- sin ningún botón de edición, continuidad o reactivación — a diferencia de
  `ProjectContinuityWidget`, que sí ofrece actualizar el proyecto activo
  (`src/sirius/application/project_continuity.py:90-121`).

`main_window.py` monta este widget en una pestaña o panel propio, separado del que aloja
`ProjectContinuityWidget`, para que nunca compartan el mismo espacio de pantalla que el
proyecto vivo — satisface literalmente el criterio de comprobación de la Definición de
Producto §6.4: «la interfaz los presenta en una vista distinta de la del proyecto activo, y
consultarlos nunca modifica ni contamina el estado o el contexto del proyecto vivo».

## 6. Búsqueda mejorada y Mejor recuperación — puntos de integración, sin decidir

Por instrucción explícita de la incidencia de origen, este documento **no** diseña la
incorporación de la evidencia de la PR #117 ni decide la dependencia de Ollama — es la
decisión única del propietario, registrada en `docs/evolution/STATUS.md` cuando se tome
(ver Definición de Producto §2.3/§2.4/§3.3/§3.4/§7.3). Lo que sigue son los puntos exactos
de la arquitectura ya existente donde encajaría cada pieza, presentados como opciones, sin
elegir ninguna.

### 6.1 Dónde encajaría un índice lateral de categoría

`RankRelevantKnowledgeUseCase.rank()` (`src/sirius/application/rank_relevant_knowledge.py:47-86`)
construye, para cada `Memory`/`Decision` vigente, un `RankedKnowledge`
(`src/sirius/domain/relevance.py:59-74`) con tres señales estructurales ya existentes:
`subject_matches_query`, `project_matches_active`, `fts_match`
(`src/sirius/application/rank_relevant_knowledge.py:65-84`). Un índice de categoría
determinista (la mitad del paquete de la PR #117 que no depende de Ollama, según la
Definición de Producto §2.2) encajaría como una cuarta señal estructural en ese mismo punto
— una nueva propiedad de `RankedKnowledge` calculada, igual que las otras tres, sin tocar
`ContextBuilder` ni `SendMessageUseCase` directamente, y consumida por
`sirius.domain.relevance.rank_relevant_knowledge`
(`src/sirius/domain/relevance.py:141`) como un criterio adicional de orden.

### 6.2 Dónde encajaría un filtro de relevancia con modelo local

Si se decide adoptarlo, el punto de integración natural es un paso **posterior** a
`RankRelevantKnowledgeUseCase.rank()` y **anterior** a `apply_context_budget`
(`src/sirius/application/context_budget.py:149-195`), dentro de
`ContextBuilder._rank_related_knowledge`
(`src/sirius/application/context.py:210-221`), que ya filtra el resultado de `rank()` una
vez (la exclusión por precedencia, `src/sirius/application/context.py:223-235`) antes de
pasarlo al presupuesto. Un filtro de relevancia por modelo local sería un segundo filtro en
ese mismo método, después del de precedencia — nunca antes, para no descartar un elemento
que la precedencia ya habría excluido igualmente. La Definición de Producto §2.2 exige que
ese filtro «falle abierto» y que «una regla en código... impida al filtro descartar un
elemento crítico que la búsqueda trajo»: ese candado de código, si se construye, vive en el
mismo método, no en el filtro con modelo — el filtro nunca decide solo.

### 6.3 Restricción que ambos puntos deben respetar

Ninguno de los dos puntos de integración puede aumentar el coste por encima del presupuesto
de latencia de `ContextBuilder` (RNF-003, ver §9.3) ni requerir tocar
`sirius.domain.precedence` (§0.1.3): ambos son puntos de **ranking o filtrado**, nunca de
decisión de conflicto.

## 7. Impactos transversales

### 7.1 Migraciones

Una sola migración nueva en este documento (§3.7, tabla `memory_suggestions`), aditiva,
sin tocar ninguna tabla existente — mismo patrón que las migraciones aditivas ya mergeadas
(`migrations/versions/94418c79da9d_add_memory_subject_and_project.py`). §5 (proyectos
históricos) y §4 (conflictos asistidos) no requieren ninguna migración: ambos son consultas
o interfaz sobre columnas y tablas ya existentes.

### 7.2 Privacidad

Ninguno de los tres bloques diseñados aquí (§3, §4, §5) introduce una llamada de red nueva
ni un destino de datos nuevo: `MemorySuggestionRepository`, `ProjectRepository.list_completed_projects`
y la interfaz de resolución de conflictos son todas operaciones locales sobre el mismo
SQLite que ya usa Sirius 0.1 (`src/sirius/adapters/persistence/database.py`,
`src/sirius/ports/data_location.py`). Los dos bloques que este documento **no** diseña (§6)
son los únicos que, si el propietario decide incorporarlos, introducirían el único
componente no-local ya contemplado por la Definición de Producto: un modelo local vía
Ollama (`docs/evolution/SIRIUS_PRODUCTO_0.2_MEMORIA_UTIL_v0.1_PROPUESTO.md` §2.2) — local
a la máquina, no un servicio remoto nuevo, pero es exactamente la pieza que este documento
deja sin decidir (§11).

### 7.3 Presupuesto de latencia de `ContextBuilder`

RNF-003 fija 300 ms para construir el contexto; B12e ya deja ese coste en el 40 % del
presupuesto, bajado del 89–100 % anterior (`docs/implementation/V8_EXECUTION.md:44-48`).
Los tres bloques de este documento no tocan `ContextBuilder.build()`
(`src/sirius/application/context.py:143-208`) en absoluto: §3 (sugerencias) vive fuera del
camino de construcción de contexto (una `MemorySuggestion` nunca se lee desde ahí, §3.5);
§4 (conflictos) es interfaz sobre una consulta ya excluida de `ContextBuilder`
(`src/sirius/application/detect_precedence_conflicts.py:14-16`); §5 (proyectos históricos)
usa un caso de uso separado que `ContextBuilder` no inyecta. Ninguno de los tres añade
coste al 40 % ya medido. Los dos bloques no diseñados aquí (§6) sí tocarían ese camino
directamente (§6.1/§6.2) y son, por tanto, los que deben volver a medirse contra RNF-003
antes de incorporarse — la Definición de Producto ya lo exige («latencia dentro del
presupuesto de 5 s», `docs/evolution/SIRIUS_PRODUCTO_0.2_MEMORIA_UTIL_v0.1_PROPUESTO.md`
§2.2; nota: esa cifra de 5 s es la del banco de evidencia de la PR #117, no verificada
contra `main` por esa misma Definición de Producto — RNF-003 en `main` es 300 ms, no 5 s;
quien construya §6 debe conciliar ambas cifras contra la fuente vigente,
`docs/implementation/V8_EXECUTION.md:47`, no contra el banco de la rama sin fusionar).

## 8. Orden de construcción propuesto

Encargos del tamaño de una vertical de Sirius 0.1 (ver §2 sobre la numeración `M1`…`M6`).
Cada uno es independiente de los bloques no diseñados en §6, que quedan fuera de este orden
hasta que el propietario decida §11.

### M1 — Proyectos históricos: puerto y aplicación

`ProjectRepository.list_completed_projects()` (§5.2) + `SqliteProjectRepository` +
`HistoricalProjectsUseCase` (§5.3), con sus pruebas unitarias/integración.

**Criterio de aceptación:** una prueba automática crea un proyecto, lo completa
(`complete_active_project`), crea y completa un segundo, y comprueba que
`list_completed_projects()` devuelve ambos, más recientemente completado primero, y que
`get_active_project()` sigue sin devolver ninguno de los dos.

### M2 — Proyectos históricos: interfaz

`HistoricalProjectsWidget` (§5.4) montado en `main_window.py`, separado de
`ProjectContinuityWidget`.

**Criterio de aceptación:** con un proyecto activo configurado y al menos un proyecto
completado en la base, la vista histórica lista el proyecto completado y muestra su
historial de revisiones al seleccionarlo; la vista del proyecto activo no cambia su
contenido en ningún momento de esa interacción (prueba GUI en modo offscreen, mismo patrón
que `tests/gui/test_knowledge_widget.py`).

### M3 — Conflictos asistidos: acciones de resolución

Cambios de interfaz descritos en §4.2 sobre `KnowledgeWidget`. Sin cambios de dominio ni
aplicación.

**Criterio de aceptación:** una prueba GUI crea dos memorias vigentes del mismo
`subject_key`/`project_id` (conflicto), detecta el conflicto, archiva una de las dos
memorias en conflicto desde la selección de `conflicts_list`, vuelve a detectar y comprueba
que el conflicto ya no aparece — sin que `sirius.domain.precedence` haya cambiado una sola
línea. Una segunda prueba selecciona un miembro `Memory` y un miembro `Decision` de un
conflicto activo (dos decisiones `APPROVED` del mismo asunto/proyecto) y comprueba que
`correct_memory_button` y `approve_decision_button` quedan deshabilitados desde
`conflicts_list`, mientras que `archive_memory_button`, `supersede_decision_button` y
`archive_decision_button` sí lo están — cubriendo la ruta que «Corregir»/«Aprobar» no
resuelven (§4.2). Una tercera prueba deja seleccionada, a la vez, una `Decision` distinta en
`decisions_list` (el panel general) y la `Decision` en conflicto en `conflicts_list`; pulsa
`archive_decision_button` (o `supersede_decision_button`) con esa selección de
`conflicts_list` activa y comprueba que la decisión modificada es la que devuelve
`_selected_conflict_entity` —su `id` coincide con la del conflicto, no con la de
`_selected_decision()` sobre `decisions_list`— y que una detección posterior
(`_handle_detect_conflicts_clicked`) ya no reporta ese conflicto.

### M4 — Sugerencias confirmadas: dominio, puerto y migración

`src/sirius/domain/memory_suggestion.py` (§3.3), `MemorySuggestionRepository` (§3.4),
extensión de `UnitOfWork`, migración `memory_suggestions` (§3.7), adaptador SQLite.

**Criterio de aceptación:** pruebas unitarias de dominio para las cuatro transiciones
legales/ilegales de `MemorySuggestionStatus`; prueba de integración de migración
(`tests/integration/test_migrations.py`, mismo patrón que las migraciones ya cubiertas) que
sube y baja la tabla nueva sin afectar ninguna existente.

### M5 — Sugerencias confirmadas: aplicación

`ProposeMemorySuggestionUseCase`, `ConfirmMemorySuggestionUseCase`,
`RejectMemorySuggestionUseCase` (§3.5), tres tipos de evento nuevos.

**Criterio de aceptación:** prueba automática que propone una sugerencia, la confirma, y
comprueba que existe una `Memory` `CURRENT` con el mismo contenido y un origen trazable
(mismo mecanismo que `GetMemoryOriginUseCase`); una segunda prueba que propone y rechaza, y
comprueba que ninguna `Memory` se creó y que `ContextBuilder.build()` sobre esa misma base
no referencia la sugerencia rechazada en ningún campo de `Context`.

### M6 — Sugerencias confirmadas: interfaz

Botón «Proponer guardar…» en `MessageItemWidget` (§3.6), sección «Sugerencias pendientes»
en `KnowledgeWidget` con sus botones «Confirmar»/«Rechazar», y el contrato de la vía
automática de §3.2: extensión de `render_instructions()` para pedir al proveedor que, cuando
proceda, incluya una propuesta distinguible en su respuesta cruda mediante un delimitador
acordado; extensión del puerto `LLMCompleted` (`src/sirius/ports/llm.py:34-40`) con el campo
`memory_suggestion: str | None`, separado del delimitador por el adaptador concreto —nunca
por `SendMessageUseCase` ni por la superficie de interfaz— antes de que exista un solo
`LLMTextDelta` o el `LLMCompleted` final, de modo que ni `on_delta` ni
`sirius_message.content` contienen jamás el delimitador ni la propuesta cruda (§3.2); y el
campo espejo `SendMessageResult.memory_suggestion` (`src/sirius/application/send_message.py:50-63`)
que la superficie de interfaz de §3.6 lee, ya separado, para decidir si llama a
`ProposeMemorySuggestionUseCase.propose(...)`. Sin este contrato la vía automática no existe:
queda asignada a M6, no como un detalle sin dueño.

**Criterio de aceptación:** prueba GUI que, sobre un turno de conversación ya completado,
propone una sugerencia desde el botón del mensaje, la ve aparecer en «Sugerencias
pendientes», la confirma, y comprueba que aparece en la lista de recuerdos vigentes del
mismo panel tras `refresh()` — sin que en ningún punto de la prueba se haya invocado
`SendMessageUseCase` una segunda vez ni se haya bloqueado la primera. Además, cinco pruebas
sobre la vía automática (§3.2), sin interfaz, ejercitando directamente la superficie que
orquesta el envío de un turno con un `LLMProvider` de prueba que ya expone el contrato
separado (`LLMCompleted.text` limpio y `LLMCompleted.memory_suggestion` aparte, nunca el
delimitador mezclado en ninguno de los dos): una respuesta `COMPLETED` con
`memory_suggestion` no nulo dispara `ProposeMemorySuggestionUseCase.propose(...)`
exactamente una vez con ese contenido, y además `result.sirius_message.content` —el texto
realmente persistido— y la concatenación de todo lo recibido por `on_delta` —el texto
realmente mostrado— son ambos exactamente `LLMCompleted.text`, sin el delimitador ni la
propuesta cruda en ninguno de los dos, cerrando el hallazgo de revisión CODEX-001 de que una
prueba que solo cuenta llamadas a `propose()` acepta esa corrupción; una respuesta
`COMPLETED` con `memory_suggestion` nulo no dispara ninguna llamada; un resultado
`CANCELLED` no dispara ninguna llamada; un resultado `FAILED` no dispara ninguna llamada — en
los cuatro últimos casos, el proveedor se invoca una sola vez por turno. El adaptador
concreto de `LLMProvider` que construya M6 añade, además, su propia prueba de que un
delimitador partido entre dos fragmentos consecutivos de la salida cruda del proveedor
tampoco llega a `on_delta` ni a `LLMCompleted.text`: la separación descrita en §3.2 no puede
depender de que el delimitador llegue entero en un único fragmento.

## 9. Decisiones pendientes del propietario

Esta arquitectura no toma ninguna de las siguientes decisiones; quedan exactamente donde la
Definición de Producto ya las dejó (§7.3 de
`docs/evolution/SIRIUS_PRODUCTO_0.2_MEMORIA_UTIL_v0.1_PROPUESTO.md`), y este documento no
añade contenido nuevo a ninguna de ellas:

- Fusionar o no la PR #117 como vía de entrada de su evidencia.
- La dependencia de Ollama en el filtro de relevancia (§6.2 de este documento señala dónde
  encajaría, sin decidir si se adopta).
- La última omisión crítica de recuperación caracterizada en la Definición de Producto §3.3.
- El origen de los estados `CANDIDATA`/`RECHAZADA` que una orden anterior daba por
  existentes (§3.1 de este documento).

Ya resuelta, no pendiente: el disparador de sugerencias —si Sirius debía proponer solo por
una acción explícita del usuario, o también automáticamente tras la conversación— era, en la
ronda anterior de este documento, una quinta decisión pendiente que surgía de este diseño y
no estaba en la Definición de Producto. El propietario la resolvió explícitamente en la
incidencia de origen (comentario del propietario, 2026-08-29T02:24:52Z): las dos vías,
automática y manual, con las tres condiciones que fija §3.2. Se deja aquí la traza, no la
decisión: el diseño resultante vive en §3.2 y §3.6, no en este apartado.

## 10. Cierre

Este documento no autoriza ninguna implementación por sí solo (`RECTOR.md` §17,
`docs/evolution/RECTOR.md:282-290`): la autorización, cuando llegue, es la fusión de la
Pull Request que lo introduce, y queda registrada en `docs/evolution/STATUS.md` como
excepción explícita, igual que ya se registró la del Sirius Work Engine y la de la
Definición de Producto de esta misma versión
(`docs/canonical/STATUS.md:26`).
