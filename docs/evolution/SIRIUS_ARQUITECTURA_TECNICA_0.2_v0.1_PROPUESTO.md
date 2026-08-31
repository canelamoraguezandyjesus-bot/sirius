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
- §7 Búsqueda mejorada y §8 Mejor recuperación — diseña la incorporación completa que
  decide el propietario en D1 (`docs/evolution/STATUS.md`): el índice de categoría
  determinista, el filtro de relevancia con modelo local vía Ollama, y el etiquetado
  automático de categoría que decide D7, con sus encargos de construcción (§8, M7–M12) y
  la forma de medirlos contra el presupuesto de latencia.
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
con ninguno de los dos, §10 numera los encargos de esta versión como `M1`…`M12`
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
     `LLMTextDelta` o de construir el `LLMCompleted`, `LLMCancelled` o `LLMError` final, de
     modo que ni un delta, ni `LLMCompleted.text`, ni `LLMCancelled.partial_text`
     (`src/sirius/ports/llm.py:41-49`) ni `LLMError.partial_text`
     (`src/sirius/ports/llm.py:69-79`) contienen jamás el delimitador ni la propuesta cruda.
     Esto no es una extensión opcional del contrato: `SendMessageUseCase` persiste
     `LLMCancelled.partial_text`/`LLMError.partial_text` tal cual, con estado `CANCELLED`/
     `FAILED`, en la misma llamada que los recibe, para trazabilidad
     (`src/sirius/application/send_message.py:188-210`), y esos mismos fragmentos ya se
     pintaron en pantalla mientras llegaban, exactamente igual que los de `LLMCompleted.text`
     (`src/sirius/presentation/main_window.py:1400-1413`); dejar sin sanear el turno cancelado
     o fallido reabriría, para esas dos rutas, el mismo defecto que CODEX-001 señaló para el
     turno completado.
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

## 6. Búsqueda mejorada y Mejor recuperación — diseño de la incorporación completa (D1) y del etiquetado de categoría (D7)

`docs/evolution/STATUS.md`, apartado «Decisiones del propietario registradas el 29 de
agosto de 2026», registra la decisión **D1**: la evidencia de la rama
`evidence/adr001-spikes` (PR #117, que permanece abierta y sin fusionar como archivo) se
incorpora a `main` **completa** — el índice de categoría determinista **y** el filtro de
relevancia con modelo local vía Ollama —, no mediante la fusión directa de esa PR sino
mediante encargos nuevos al Work Engine que porten ese trabajo como código de producto con
sus pruebas (§8, M7–M12). D1 exige respetar, sin reabrirlos, los dos puntos de integración
que la ronda anterior de este documento ya dejaba fijados sin elegir entre opciones: el
índice como cuarta señal de `RankedKnowledge` (§6.2) y el filtro como segundo filtro en
`ContextBuilder._rank_related_knowledge`, después de la exclusión por precedencia (§6.3).

La misma sección de `STATUS.md` registra, como continuación de ese mismo registro del 29 de
agosto de 2026 pero con fuente propia, la decisión **D7**: el comentario del propietario en
la incidencia #435 (2026-08-29T17:08:12Z), «Etiqueta el modelo local (Ollama),
automáticamente; el usuario corrige y su corrección manda». D7 resuelve el vacío que dejaba
bloqueados M8–M11 en la ronda anterior de este documento — de dónde sale, para un candidato
real de `main`, el dato de categoría que `category_match` (§6.2) y el candado de §6.3
necesitan —, y §6.1 traduce sus siete puntos a diseño. Ni D1 ni D7 se reabren en ningún
punto de este documento: ambas son hechos ya decididos por el propietario que este
documento incorpora desde el arranque, tal como exige la incidencia de origen de esta
ronda.

Este documento sigue sin leer `evidence/adr001-spikes` ni la PR #117 directamente (§0): lo
que sigue cita el registro de `STATUS.md` por el nombre de su decisión (D1, D2, D3, D7),
nunca por línea — una ronda anterior de este documento dejó ocho citas por línea a
`STATUS.md` apuntando al párrafo equivocado (incidencia #435, ronda 7), y citar por nombre
de decisión es inmune a que ese fichero, o este, vuelvan a desplazarse. Quienes construyan
los encargos de §8 sí pueden leer `evidence/adr001-spikes` para portar el trabajo
(instrucción explícita de la incidencia de origen de esta ronda).

### 6.1 Campo de categoría en `Memory`/`Decision`: etiquetado automático con Ollama (D7)

D7 fija, en sus siete puntos literales, la fuente y el ciclo de vida de la categoría de un
elemento real — el vacío que una ronda anterior de este documento dejaba sin resolver
porque ni `Memory` (`src/sirius/domain/memory.py:62-68`) ni `Decision`
(`src/sirius/domain/decision.py:86-93`) tienen hoy ese campo. Este apartado traduce los
siete puntos a diseño, uno por uno.

**1. Campo nuevo y vocabulario cerrado.** `Memory` y `Decision` ganan dos campos nuevos,
opcionales, en la propia entidad —no en su revisión, mismo patrón que
`subject_key`/`project_id` (`src/sirius/domain/memory.py:67-68`,
`src/sirius/domain/decision.py:87-88`), porque clasificar la categoría de un elemento no es
corregir su contenido—: `category: str | None = None` y `category_locked: bool = False`. El
vocabulario de `category` es exactamente el que porta el banco de 47 casos que M7 (§8)
versiona en `tests/acceptance/fixtures/evidence_bank_47_casos.json` (§6.5): este documento
no inventa categorías nuevas ni las enumera, para que las cifras medidas sigan siendo
comparables, tal como exige D7 punto 1.

**2. Etiquetado automático, asíncrono, diferido, sin bloquear el guardado.** Nuevo puerto
`CategoryClassifierPort` (`src/sirius/ports/category_classifier.py`), un `Protocol` con un
único método, `classify(content: str) -> str | None`, que devuelve un valor del vocabulario
cerrado o `None` si no puede decidir — declarado, por firma y documentación, para no
propagar jamás una excepción: cualquier fallo interno se traduce en `None`. Nuevo adaptador
`OllamaCategoryClassifierAdapter` (`src/sirius/adapters/ollama_category_classifier.py`) que
lo implementa contra el Ollama local, con la misma propiedad estructural que §6.3 exige
para el filtro: apunta en exclusiva a `localhost`, sin parámetro que permita un host
remoto, y falla abierto (Ollama no instalado, conexión rechazada, tiempo agotado o
respuesta fuera del vocabulario cerrado) devolviendo `None`, nunca una excepción.

La orquestación asíncrona y diferida reutiliza literalmente el patrón
`QRunnable`/`QThreadPool` que Sirius 0.1 ya usa para todo trabajo que no debe bloquear la
interfaz — `SendMessageWorker` (`src/sirius/presentation/conversation_worker.py:27`),
`CreateBackupWorker`/`ValidateBackupWorker`/`RestoreBackupWorker`
(`src/sirius/presentation/backup_worker.py:40`), `ExportWorker`
(`src/sirius/presentation/export_worker.py:36`) — sobre el mismo `self._thread_pool` que
`main_window.py` ya construye (`src/sirius/presentation/main_window.py:381`). Un nuevo
`CategoryTaggingWorker(QRunnable)` (`src/sirius/presentation/category_tagging_worker.py`)
se encola **después** de que el caso de uso de guardado (`SaveManualMemoryUseCase`,
`ConfirmMemorySuggestionUseCase`, `ProposeDecisionUseCase`) ya haya devuelto su resultado —
nunca dentro de esa misma llamada ni de su transacción de `UnitOfWork` (§0.1 punto 4
gobierna evento+estado en la misma transacción; etiquetar no es ninguno de los dos). El
worker llama, fuera del hilo de interfaz, a un nuevo caso de uso
`TagCategoryUseCase.tag(kind, item_id)`: lee el elemento —registrando, en ese mismo
instante y antes de invocar `classify()`, la versión de su revisión vigente
(`MemoryRevision.version`/`DecisionRevision.version`, §0.1) que está clasificando—, invoca
`CategoryClassifierPort.classify`, y si devuelve una categoría del vocabulario la escribe
mediante un método nuevo del repositorio
(`MemoryRepository.set_category`/`DecisionRepository.set_category`) — una actualización de
campo plano, nunca una revisión nueva, y una única sentencia condicional en el motor de
persistencia (`UPDATE ... SET category = ?, ... WHERE id = ? AND category_locked = 0 AND
<versión de revisión vigente> = ?`, o la transacción equivalente) que solo escribe si, en
ese mismo statement, `category_locked` sigue siendo `False` **y** la revisión vigente del
elemento sigue siendo la misma que se leyó antes de clasificar: comprobar y escribir son una
sola operación atómica de la base de datos, nunca una lectura en Python seguida de una
escritura separada, así que ninguna corrección del usuario que ocurra entre ambas puede
perderse ni ganarle la carrera al worker (punto 3). La misma condición de versión cierra
además una segunda carrera distinta, entre dos generaciones del propio etiquetado
automático: si este worker quedó en vuelo clasificando una revisión que una corrección
(`CorrectMemoryUseCase.correct()`, más abajo) ya sustituyó por una revisión nueva — que a su
vez ya encoló y dejó completar a otro `TagCategoryUseCase` sobre esa revisión nueva —, la
escritura tardía de este worker ya no encuentra ninguna fila cuya revisión vigente coincida
con la que leyó, y no sobrescribe con una clasificación obsoleta la que ya escribió el
worker más reciente; ninguna de las dos escrituras se cancela ni se vuelve síncrona para
lograrlo, solo se amplía la misma condición atómica del `UPDATE`. La escritura exitosa emite
además una señal Qt para que `KnowledgeWidget.refresh()` la muestre. Guardar nunca espera a
este worker: la llamada de guardado ya devolvió su resultado por su propio camino antes de
que el worker se encole.

**3. Etiqueta visible, editable, y definitiva si es del usuario.** `KnowledgeWidget`
(`_build_memories_section`, `src/sirius/presentation/knowledge_widget.py:318-355`;
`_build_decisions_section`, `src/sirius/presentation/knowledge_widget.py:485-519`) gana, por elemento, la categoría
visible y una acción para editarla, que llama a un nuevo
`SetCategoryUseCase.set(kind, item_id, category)`: escribe `category` **y** pone
`category_locked = True` en la misma llamada, siempre — a diferencia del punto 2, esta
escritura nunca está condicionada: la corrección del usuario manda incondicionalmente.
Desde ese momento, `TagCategoryUseCase` **nunca** vuelve a escribir sobre ese elemento — no
porque el caso de uso compruebe `category_locked` en un paso previo y separado (esa
comprobación en dos pasos es exactamente la carrera que dejaba perder una corrección del
usuario llegada entre medias), sino porque la sentencia condicional del punto 2 hace de la
comprobación y la escritura una sola operación: si el usuario corrige entre el `classify()`
del worker y el intento de escritura de `TagCategoryUseCase`, ese `UPDATE` condicional ya no
encuentra ninguna fila con `category_locked = 0` que actualizar y no escribe nada, sin
ninguna ventana en la que ambas escrituras puedan competir. El dominio de Sirius sigue sin
juicio semántico propio (§0.1 punto 3): la clasificación entera vive en el adaptador,
detrás del puerto, y ninguna regla determinista de `sirius.domain.precedence` cambia.

**4. Retroactivo.** `MemoryRepository`/`DecisionRepository` ganan una consulta de solo
lectura, `list_uncategorized()`, que devuelve todo elemento con `category is None` y
`category_locked is False`. Al arrancar la interfaz (o desde una acción explícita de
`KnowledgeWidget`, mismo patrón que `_handle_detect_conflicts_clicked`), esa lista se
encola en el mismo `self._thread_pool`, un `CategoryTaggingWorker` por elemento — mismo
mecanismo, mismo contrato de fallo abierto, sin tratamiento especial para datos antiguos,
en local y sin coste (D7 punto 4).

**Corrección de contenido y reetiquetado.** D7 fija el origen y ciclo de vida de la
categoría, pero no cubre por sí sola qué pasa con una categoría ya asignada cuando el
contenido que la originó cambia — `CorrectMemoryUseCase.correct()`
(`src/sirius/application/correct_memory.py:64-108`) sustituye el contenido vigente por una
revisión nueva (RF-022), y el contenido que `CategoryClassifierPort.classify` clasificó ya
no describe el elemento corregido. Si `category_locked` es `False` — la categoría vigente
la puso Ollama, no el usuario —, `correct()` limpia `category` a `None` en la misma
transacción de `UnitOfWork` que crea la revisión nueva (§0.1 punto 4): eso, limpiar el
campo, es todo el trabajo transaccional del caso de uso, y todo lo que `correct()` necesita
hacer. Encolar el `CategoryTaggingWorker` del punto 2 no es trabajo de `correct()` —ese
`QRunnable` y el `QThreadPool` que lo ejecuta pertenecen a `sirius.presentation`, y
`CorrectMemoryUseCase`, en `sirius.application`, no importa Qt ni lo conoce, igual que
ningún otro caso de uso de esta arquitectura (§0.1)—: es
`KnowledgeWidget._handle_correct_memory_clicked`
(`src/sirius/presentation/knowledge_widget.py:388-407`), la
misma función que ya llama a `correct()` de forma síncrona y luego refresca la vista, quien
lo encola justo después de que esa llamada devuelva, cuando el `Memory`/`Decision` que
`correct()` devolvió trae `category is None` **y** `category_locked is False` — la condición
de presentación nunca confía solo en `category is None`, comprueba también el candado, para
no encolar si algún otro camino llegara a devolver esa combinación con `category_locked` en
`True`, aunque la rama transaccional del punto anterior garantice que hoy no ocurre. Si
`category_locked` es `True` — el usuario ya la fijó o corrigió —, `correct()` no toca ni
`category` ni `category_locked`, y `_handle_correct_memory_clicked` no encola nada: corregir
el contenido nunca reabre una categoría que el usuario ya cerró (punto 3).
Ninguna de las dos ramas añade un campo nuevo: usa exactamente los que el punto 1 ya define.
M8 (§8) construye la rama transaccional de `CorrectMemoryUseCase` y la orquestación de
`_handle_correct_memory_clicked`, cada una con su prueba — incluida una prueba de
`_handle_correct_memory_clicked` con un doble de `CorrectMemoryUseCase` que devuelva
`category=None` y `category_locked=True`, que confirma que no se encola ningún
`CategoryTaggingWorker` en ese caso.

**5. El proveedor de pago no interviene.** Ninguno de los componentes anteriores llama a
`LLMProvider` (`src/sirius/ports/llm.py:106-119`) ni a ningún adaptador de pago:
`CategoryClassifierPort`/`OllamaCategoryClassifierAdapter` son los únicos implicados,
exactamente como §6.3 ya mantiene la llamada de Ollama del filtro fuera de la superficie
del proveedor de pago. Ninguna llamada nueva, ningún coste nuevo, ninguna superficie de
privacidad nueva (§7.2).

**6. Medición de coincidencia contra el banco, condición de aceptación.** Antes de fiarse
de esta señal contra `Memory`/`Decision` reales, M11 (§8) mide la coincidencia del
etiquetado automático de Ollama contra las etiquetas canónicas del banco de 47 casos de
§6.5 (Ollama etiqueta el corpus con `CategoryClassifierPort`, se compara el resultado con
el canon, se registra la cifra) — mismo patrón que D2 fija para el suelo de cobertura: el
umbral exigible lo registra el propietario a la vista de esa medición, no antes (§6.5, §9).

**7. Idea futura, fuera de alcance.** La detección semántica de contradicciones entre
recuerdos con el modelo local (dos textos distintos que afirman lo contrario) queda
registrada como idea futura, fuera del alcance de este paquete; hoy la cubre, en su forma
determinista, el panel de conflictos por asunto (§4). Este documento no la diseña ni la
asigna a ningún encargo.

**Migración.** Una sola migración aditiva añade `category`/`category_locked` a `memories` y
a `decisions` — mismo patrón que la migración `94418c79da9d` (§3.7) y que la de
`memory_suggestions` (§3.7): sin tocar ninguna columna existente, sin backfill necesario
(`category_locked` nace en `False`, así que todo elemento anterior a esta migración queda
inmediatamente elegible para el pase retroactivo del punto 4). M8 (§8) construye el
dominio, el puerto, el adaptador, la migración y los dos casos de uso
(`TagCategoryUseCase`, `SetCategoryUseCase`).

### 6.2 Índice de categoría determinista: cuarta señal de `RankedKnowledge`

`RankRelevantKnowledgeUseCase.rank()` (`src/sirius/application/rank_relevant_knowledge.py:47-86`)
construye, para cada `Memory`/`Decision` vigente, un `RankedKnowledge`
(`src/sirius/domain/relevance.py:59-74`) con tres señales estructurales ya existentes:
`subject_matches_query`, `project_matches_active`, `fts_match`
(`src/sirius/application/rank_relevant_knowledge.py:65-84`). El índice de categoría
determinista — la mitad del paquete de la PR #117 que no depende de Ollama, según la
Definición de Producto §2.2 (`docs/evolution/SIRIUS_PRODUCTO_0.2_MEMORIA_UTIL_v0.1_PROPUESTO.md:67-68`)
— se incorpora como una cuarta señal estructural en ese mismo punto: una nueva propiedad
`category_match: bool` de `RankedKnowledge`, calculada por el mismo caso de uso que ya
calcula las otras tres, sin tocar `ContextBuilder` ni `SendMessageUseCase` directamente.

`category_match` compara dos valores, ninguno calculado con un modelo en el momento de la
consulta: la categoría ya persistida del candidato (§6.1 — `False` si el candidato todavía
no tiene categoría, porque un elemento sin categoría no participa de esta señal y sigue
encontrándose por las otras tres, exactamente como exige el fallo abierto de D7 punto 2) y
la categoría que la consulta activa, derivada en el mismo `rank()`, en el mismo instante en
que ya calcula `subject_matches_query`/`fts_match`: una coincidencia de texto determinista
del `query_text` contra el mismo vocabulario cerrado que porta el banco (§6.1, §6.5) — sin
ninguna llamada a `CategoryClassifierPort` ni a Ollama en este cálculo. Esta es una
decisión de diseño de este documento, no del propietario: mantiene el carácter
«determinista, sin modelo» que la Definición de Producto §2.2 exige para el índice, incluso
después de que D7 decida que el origen de la categoría *del candidato* sí pase por un
modelo local — clasificar un candidato al guardarlo (§6.1) y comparar dos valores ya
calculados en tiempo de consulta (aquí) son dos operaciones distintas, y solo la primera
usa un modelo. Si la consulta no activa ninguna categoría del vocabulario, `category_match`
es `False` para todos los candidatos — no penaliza, simplemente no aporta señal, igual que
`subject_matches_query` cuando la consulta no nombra ningún asunto
(`src/sirius/domain/relevance.py:108-117`).

`rank_relevant_knowledge` (`src/sirius/domain/relevance.py:141`) consume `category_match`
como un cuarto término en la tupla de orden de `_sort_key`
(`src/sirius/domain/relevance.py:131-138`), insertado **después** de `fts_match` y
**antes** de la recencia: S7.5 no fija dónde entraría una señal de categoría en su lista de
prioridad (`src/sirius/domain/relevance.py:7-14`), así que este documento la fija aquí —
más débil que una coincidencia FTS5 explícita sobre la consulta del usuario, porque la
categoría del candidato deriva de una clasificación de guardado, no de la consulta en sí.
M9 (§8) construye esta señal.

### 6.3 Filtro de relevancia con modelo local vía Ollama: puerto, adaptador, fallo abierto y candado

El punto de integración es exactamente el que la ronda anterior ya fijaba: un paso
**posterior** a `RankRelevantKnowledgeUseCase.rank()` y **anterior** a
`apply_context_budget` (`src/sirius/application/context_budget.py:149-195`), dentro de
`ContextBuilder._rank_related_knowledge` (`src/sirius/application/context.py:210-221`), que
ya filtra el resultado de `rank()` una vez — la exclusión por precedencia
(`src/sirius/application/context.py:223-235`) — antes de pasarlo al presupuesto. El filtro
de relevancia por modelo local es un segundo filtro en ese mismo método, después del de
precedencia, nunca antes, para no evaluar con Ollama un candidato que la precedencia ya
habría excluido igualmente.

**Puerto.** `RelevanceFilterPort` (nuevo, `src/sirius/ports/relevance_filter.py`), un
protocolo con un único método, `filter_candidates(query_text, candidates) -> Sequence[RankedKnowledge]`,
que devuelve el subconjunto a **conservar** — nunca reordena; el orden sigue siendo
responsabilidad exclusiva de §6.2. El contrato del puerto declara, por firma y por
documentación, que **nunca propaga una excepción**: cualquier fallo interno se traduce en
devolver `candidates` sin modificar.

**Adaptador.** `OllamaRelevanceFilterAdapter` (nuevo, `src/sirius/adapters/ollama_relevance_filter.py`)
implementa ese puerto contra un modelo local vía Ollama — el mismo Ollama local que §6.1
usa para etiquetar, un segundo cliente del mismo servicio, nunca un segundo componente de
red. «Sin destino de red fuera del equipo» es una propiedad estructural del adaptador, no
una opción de configuración: apunta en exclusiva al Ollama local (`http://localhost:11434`,
el puerto por defecto de Ollama), sin parámetro que permita apuntarlo a un host remoto.
Falla abierto exactamente como exige la Definición de Producto §2.2
(`docs/evolution/SIRIUS_PRODUCTO_0.2_MEMORIA_UTIL_v0.1_PROPUESTO.md:69`): si Ollama no está
instalado, si la conexión se rechaza, si no responde dentro del presupuesto de tiempo que
M11 fija (§6.4), o si la respuesta no tiene la forma esperada, el adaptador captura ese
fallo internamente y devuelve `candidates` sin modificar — la construcción de contexto
continúa exactamente como hoy, sin excepción visible para `ContextBuilder` y sin descartar
nada.

**Candado.** La Definición de Producto §2.2 exige, además, «una regla en código... que
impida al filtro descartar un elemento crítico que la búsqueda trajo»
(`docs/evolution/SIRIUS_PRODUCTO_0.2_MEMORIA_UTIL_v0.1_PROPUESTO.md:70-71`). Ese candado no
vive en el adaptador —el filtro con modelo nunca decide solo— sino en
`ContextBuilder._rank_related_knowledge` mismo, inmediatamente después de invocar el
puerto: reutiliza el mismo campo `category` que §6.1/D7 ya persiste (la categoría de máxima
criticidad del vocabulario cerrado del banco, §6.5), y garantiza que todo candidato de esa
categoría, **y todo candidato sin `category` todavía**, sigue presente en el resultado,
calcule lo que calcule `RelevanceFilterPort.filter_candidates`. El candado es una unión de
tres conjuntos —el resultado del filtro, los candidatos de la categoría de máxima
criticidad, y los candidatos con `category is None`—, preservando el orden que §6.2 ya
fijó, no una segunda llamada al filtro ni una excepción a su criterio.

**La premisa que bloqueaba este candado ya está resuelta.** Una ronda anterior de este
documento dejaba aquí una decisión pendiente del propietario — de dónde sale, para
`Memory`/`Decision` reales, el dato de categoría o criticidad que el candado protege —,
porque ni `Memory` ni `Decision` tenían ese campo. D7 la resuelve: el campo `category` de
§6.1, etiquetado por Ollama de forma asíncrona y diferida, es la fuente para candidatos
reales, exactamente igual que para el índice de §6.2. Un candidato sin categoría todavía
(etiquetado pendiente, o Ollama nunca disponible) **también** queda protegido por el
candado, nunca expuesto al filtro destructivo: hoy `ContextBuilder` no aplica ningún filtro
de este tipo, y la Definición de Producto exige que ningún elemento crítico recuperado
pueda descartarse
(`docs/evolution/SIRIUS_PRODUCTO_0.2_MEMORIA_UTIL_v0.1_PROPUESTO.md:69-71`) — sin categoría
todavía no hay forma de excluir con seguridad que sea justo ese elemento crítico. Solo un
candidato ya clasificado por Ollama en una categoría que no es la de máxima criticidad
queda expuesto a `RelevanceFilterPort`; en cuanto `TagCategoryUseCase` (§6.1 punto 2) le
asigna esa categoría, el candidato pasa del conjunto protegido al conjunto expuesto (o se
mantiene protegido, si la categoría asignada es la de máxima criticidad), nunca antes de
que la clasificación exista. M10 (§8) construye el puerto, el adaptador y este candado, con
una prueba que demuestra que un candidato con `category=None` sobrevive al doble del filtro
aunque el doble lo excluya explícitamente.

**Puerta de activación pendiente contra datos reales (D7 punto 6).** Todo lo anterior — que
un candidato ya clasificado en una categoría no crítica quede expuesto a
`RelevanceFilterPort`, y que `category_match` (§6.2) compare la categoría de un candidato
real — presupone que la clasificación de Ollama es lo bastante fiable como para actuar sobre
ella; D7 punto 6 exige medir esa fiabilidad antes de confiar en la señal contra
`Memory`/`Decision` reales, y M11 (§8, §6.5) mide y publica la cifra sin fijar el umbral
exigible por su cuenta — lo registra el propietario a la vista de esa medición (§9). Hasta
que el propietario registre ese umbral en `STATUS.md`, esta arquitectura mantiene la puerta
cerrada con el fallback más seguro, que no consume la categoría de ningún candidato real: el
candado protege a **todo** candidato real, con categoría o sin ella, exactamente como si
ninguno tuviera todavía una clasificación no crítica, y `category_match` es `False` para
todo candidato real (§6.2) — ninguno de los dos deja de construirse ni de medirse contra el
banco de §6.5 mientras tanto, que tiene su propio canon y no depende de este umbral. Abrir la
puerta —dejar que una categoría no crítica exponga al candidato al filtro, y que
`category_match` compare categorías reales— es exclusivamente lo que el registro del umbral
en `STATUS.md` autoriza; M11 (§8) no la abre por sí solo con solo publicar la cifra.

**Fuente de activación que el runtime consume.** Registrar el umbral en `STATUS.md` es un
hecho documental: por sí solo no cambia ningún comportamiento en ejecución si ningún camino
de código lo lee, y una implementación conforme a solo lo anterior podría dejar la puerta
cerrada para siempre sin incumplir ninguna prueba. Esta arquitectura fija esa fuente
reutilizando el mecanismo ya existente para conmutar comportamiento en tiempo de
construcción según una decisión persistida — el mismo `sirius.config.settings`
(`load_settings()`/`save_settings()`, `src/sirius/config/settings.py`) que ya decide, por
ejemplo, qué `LLMProviderKind` construye `composition_root._build_llm_provider`
(`src/sirius/composition_root.py:189-233`) —, con una clave nueva,
`category_matching_enabled: bool`, ausente o `False` por defecto. `composition_root` la lee
una vez, igual que ya lee `llm_provider`, y la pasa como parámetro de construcción a
`RankRelevantKnowledgeUseCase`/`ContextBuilder`; con la clave en `False` o ausente,
`category_match` (§6.2) y el candado (§6.3) se comportan exactamente como el fallback
cerrado descrito arriba, sin ninguna rama de código adicional para el estado cerrado — es el
mismo camino que ya corre hoy. M11 (§8) construye ese parámetro de construcción y lo cablea
con su valor por defecto, `False`: escribir la clave a `True` en `settings.json` no es
trabajo de M11 ni de ningún otro encargo M1–M12 — es la acción separada, explícita y manual
que traduce el registro del umbral en `STATUS.md` a comportamiento real, y queda, igual que
las decisiones que §9 deja pendientes de un encargo futuro, asignada a quien registre el
umbral y confirme que la cifra medida lo alcanza, no a este documento ni a un número de
encargo fijado por adelantado; este documento no elige el valor del umbral ni decide cuándo
se cumple, solo el contrato de cómo esa decisión, una vez tomada, llega al runtime.

**La activación no puede perderse en un guardado posterior.** El propietario activa la
puerta editando `settings.json` directamente, no desde la interfaz (párrafo anterior); pero
`MainWindow._save_configuration()` ya construye hoy, para cualquier guardado desde el diálogo
de preferencias, un diccionario nuevo con solo las seis claves que esa vista conoce y se lo
pasa entero a `save_settings()` (`src/sirius/presentation/main_window.py:2476-2484`), que a
su vez sobrescribe `settings.json` por completo (`src/sirius/config/settings.py:27-34`):
guardar cualquier otro ajuste desde la interfaz después de activar la puerta la cerraría de
nuevo sin que nadie lo pidiera, porque `category_matching_enabled` no es una de esas seis
claves. Esta arquitectura exige que `_save_configuration()` deje de construir ese diccionario
desde cero y en su lugar parta de `load_settings()`, actualizando solo las claves que la
vista conoce y conservando cualquier otra clave ya presente en el fichero —
`category_matching_enabled` incluida, sin que `_save_configuration()` necesite conocer su
nombre ni su significado. Una activación explícita persiste así hasta otra desactivación
explícita, nunca hasta el próximo guardado de un ajuste no relacionado. M11 (§8) corrige
`_save_configuration()` en este sentido y añade la prueba que lo demuestra: activar la clave,
guardar un ajuste cualquiera desde `_save_configuration()`, y confirmar que la clave sigue en
`True` después.

### 6.4 Presupuesto de latencia: RNF-003 y metodología de medición de M11

Ninguno de los dos puntos de integración puede sacar a `ContextBuilder` de RNF-003, 300 ms
P95 (`docs/decisions/ADR-008-cargar-en-lote-las-revisiones-vigentes-al-listar.md:111-117`,
`docs/implementation/V8_EXECUTION.md:44-48`), ni requiere tocar `sirius.domain.precedence`
(§0.1 punto 3): ambos son puntos de **ranking o filtrado**, nunca de decisión de conflicto.
Hoy construir el contexto usa ~120,9 ms P95 medidos con el mismo conjunto de referencia del
Plan de Pruebas —5.000 mensajes, 500 recuerdos, 100 decisiones, 10 proyectos, 30
repeticiones—, misma máquina
(`docs/decisions/ADR-008-cargar-en-lote-las-revisiones-vigentes-al-listar.md:107-117`); B12e
registra esa cifra como el 40 % del presupuesto de 300 ms, bajado del 89–100 % anterior
(`docs/implementation/V8_EXECUTION.md:44-48`) — una **medición histórica**, no un requisito
adicional: el único límite exigible que este documento fija para §6.5/§6.6/M9-M11 es
RNF-003 (≤ 300 ms P95), nunca «mantenerse dentro del 40 %». Si M9 (el índice) sube el P95
medido a, por ejemplo, 140 ms — todavía muy por debajo de 300 ms pero ya por encima del
40 % histórico — esta arquitectura no lo rechaza por eso: registra la cifra nueva como el
dato vigente, igual que ADR-008 registró 120,9 ms como medición, no como techo.

El índice de categoría (§6.2) es una comparación en memoria del mismo orden de magnitud que
las tres señales estructurales que ya calcula `RankRelevantKnowledgeUseCase.rank()`, y la
clasificación de la consulta (§6.2) es una coincidencia de texto contra un vocabulario
cerrado, sin llamada a Ollama: ninguna de las dos exige una medición separada más allá de
volver a correr el benchmark de ADR-008 una vez construido (M9), con el mismo formato de
tabla, para confirmar que el P95 sigue ≤ 300 ms.

El etiquetado con Ollama (§6.1) nunca corre en el camino de `ContextBuilder`: es asíncrono
y diferido tras el guardado (D7 punto 2), así que no cuenta contra RNF-003 en absoluto — el
benchmark de ADR-008 mide construir contexto, no guardar un elemento. El filtro con Ollama
(§6.3) sí es el riesgo real de latencia dentro de ese camino, por ser una llamada fuera de
proceso, síncrona, dentro de `ContextBuilder.build()`. Cómo se mide, asignado a M11 (§8):

1. Medir el P95 de «construir contexto» con el mismo benchmark de ADR-008 justo antes de
   cablear el filtro (línea base con M7/M9 ya integrados, sin M10).
2. Fijar el presupuesto de tiempo (`timeout`) del adaptador de forma que, incluso en el
   peor caso —Ollama disponible pero lento, tardando el `timeout` completo—, el P95 total
   se mantenga ≤ 300 ms; el valor exacto del `timeout` lo decide la medición de M11, no
   este documento.
3. Repetir el benchmark de ADR-008 en **tres** escenarios, no solo los dos favorables — una
   ronda anterior de este documento solo medía ausencia de Ollama y respuesta disponible
   dentro del presupuesto, y una revisión (incidencia #435, hallazgo CODEX-003) señaló que
   eso no demuestra el peor caso real: una conexión rechazada falla de inmediato, pero un
   Ollama que **acepta la conexión y deja de responder** agota el `timeout` completo, que es
   el coste real que RNF-003 debe soportar. Los tres escenarios: (a) Ollama disponible,
   respondiendo dentro de su presupuesto; (b) Ollama ausente — conexión rechazada de
   inmediato, fallo abierto sin esperar; (c) Ollama acepta la conexión y no responde hasta
   agotar el `timeout` — un doble o servidor local de prueba que acepta y no contesta, no
   una ausencia — fallo abierto tras el `timeout` completo. Los tres tienen un coste que
   medir, ninguno se da por gratuito.
4. Publicar las tres filas en una tabla con el mismo formato que la de ADR-008
   (`docs/decisions/ADR-008-cargar-en-lote-las-revisiones-vigentes-al-listar.md:111-117`),
   como evidencia del encargo M11, antes de declararlo cerrado.

La Definición de Producto también cita «latencia dentro del presupuesto de 5 s»
(`docs/evolution/SIRIUS_PRODUCTO_0.2_MEMORIA_UTIL_v0.1_PROPUESTO.md` §2.2) — esa cifra es la
del banco de evidencia de la PR #117, no verificada contra `main` por esa misma Definición
de Producto. RNF-003 en `main` es 300 ms, no 5 s; M11 mide contra la fuente vigente
(`docs/implementation/V8_EXECUTION.md:47`), no contra el banco de la rama sin fusionar.

### 6.5 Banco versionado de 47 casos: dónde vive y qué mide la prueba automática

El corpus congelado de 47 casos y sus resultados esperados
(`docs/evolution/SIRIUS_PRODUCTO_0.2_MEMORIA_UTIL_v0.1_PROPUESTO.md:63-75`) se porta **sin
modificarse** (D1) a `tests/acceptance/fixtures/evidence_bank_47_casos.json`, siguiendo el
mismo patrón de fixture versionado que ya usa `tests/engine/fixtures/github_issue_186.json`.
Cada caso conserva su clasificación de criticidad tal como la porta la rama de evidencia,
incluido un campo `criticidad.razon_segura`: ese campo **nunca se lee ni se indexa** por
ningún camino de producción — ni el etiquetador de §6.1, ni el índice de categoría (§6.2),
ni el candado (§6.3), ni el cargador que la prueba automática usa para ejecutar el pipeline
lo deserializan; solo el arnés de evaluación que calcula las cuatro métricas (más abajo)
puede leer `criticidad.nivel` para puntuar, nunca `criticidad.razon_segura`. M7 (§8) incluye
una prueba dedicada que demuestra esa exclusión por construcción, no solo por convención. El
mismo corpus fija, además, el vocabulario cerrado de categorías que §6.1 (etiquetador), §6.2
(índice) y §6.3 (candado) reutilizan sin inventar ninguna nueva (D7 punto 1).

`tests/acceptance/test_pa_0_2_rec_01_banco_evidencia.py` (nuevo, M7) ejecuta, para cada uno
de los 47 casos, el mismo pipeline de recuperación que usa `ContextBuilder`
(`RankRelevantKnowledgeUseCase.rank()` → índice de categoría §6.2 → exclusión por
precedencia → filtro de relevancia §6.3, con un doble de prueba determinista del puerto,
nunca una llamada real a Ollama dentro de la suite) y mide, agregado sobre los 47 casos:

- **aciertos exactos**: casos cuyo resultado completo coincide exactamente con el esperado;
- **elementos de más**: elementos devueltos que el caso no esperaba, sumados across los 47;
- **omisiones críticas**: elementos esperados marcados como críticos (`criticidad.nivel`)
  que faltan en el resultado;
- **cobertura**: fracción de los elementos esperados (81 en total sobre los 47 casos,
  Definición de Producto §2.2) presentes en algún resultado.

Suelos exigidos por D1/D2, afirmados como aserciones duras que hacen fallar la prueba si se
incumplen: aciertos exactos no por debajo de 29/47; cobertura no por debajo de 63/81 — este
segundo suelo es **provisional**, no una cifra definitiva: D2 lo registra expresamente como
el piso más bajo de las dos cifras que cita la Definición de Producto, hasta que la primera
medición real de PA-0.2-REC-01 sobre `main` registre la cifra medida, momento en el que esa
cifra medida sustituye a este provisional sin necesidad de una nueva decisión del
propietario. M11 (§8) es quien ejecuta esa primera medición real; a partir de ahí la
aserción dura de esta prueba pasa a ser la cifra que M11 mida, no 63/81, y las ejecuciones
posteriores a M11 no pueden seguir pasando con 63/81 si la medición real fue distinta.
Omisiones críticas: el objetivo de PA-0.2-REC-01 es 0
(`docs/evolution/SIRIUS_PLAN_PRUEBAS_0.2_v0.1_PROPUESTO.md:145-157`); si M12 (§8/§6.6) no lo
alcanza, esta misma prueba se actualiza para afirmar explícitamente el conteo real medido —
nunca relajada en silencio— y PA-0.2-REC-01 permanece no superada, tal como exige D3.

**Medición de coincidencia del etiquetado (D7 punto 6).** Además de las cuatro métricas de
recuperación, M11 (§8) ejecuta `CategoryClassifierPort`/`OllamaCategoryClassifierAdapter`
(§6.1) sobre el contenido de los 47 casos del banco y compara el resultado contra la
categoría canónica que cada caso ya trae, publicando la cifra de coincidencia (aciertos/47)
como evidencia del encargo. El umbral exigible para fiarse de esta señal contra
`Memory`/`Decision` reales no lo fija este documento: lo registra el propietario a la vista
de esa medición, mismo patrón que D2 fija para el suelo de cobertura (§9).

**Prueba del adaptador contra una respuesta Ollama válida.** La prueba del banco
(`tests/acceptance/test_pa_0_2_rec_01_banco_evidencia.py`, arriba) y la de M10 (§8) sustituyen
`RelevanceFilterPort` por un doble determinista para no depender de Ollama real dentro de la
suite; ninguna de las dos, por tanto, atraviesa nunca el parseo de una respuesta HTTP real de
Ollama que hace `OllamaRelevanceFilterAdapter` — una implementación que siempre se comportara
como si hubiera fallado (devolviendo `candidates` sin modificar) pasaría igualmente esas
pruebas y la medición de latencia de §6.4/M11, dejando el filtro real inoperante sin que
ninguna prueba lo detecte. M10 (§8) añade, además de las pruebas con doble del puerto, una
prueba propia de `OllamaRelevanceFilterAdapter` contra un transporte o servidor HTTP local de
prueba (nunca Ollama real ni ningún proveedor externo) que entrega una respuesta válida con
la forma que Ollama produce, y verifica que el adaptador la parsea en el subconjunto y el
orden esperados.

### 6.6 Decisión D3: intento de cierre de la última omisión crítica

D3 decide que la omisión crítica por derivación léxica que la Definición de Producto
§3.2(b) caracteriza («preferencia de redacción» frente a «prefiere que redactes»,
`docs/evolution/SIRIUS_PRODUCTO_0.2_MEMORIA_UTIL_v0.1_PROPUESTO.md:107-108`) **se intenta
cerrar** dentro del mismo paquete de incorporación de D1, no se caracteriza sin más. M12
(§8) es ese intento, con salida explícita en los dos sentidos que D3 fija — ver el criterio
de aceptación de M12: si se cierra, el banco de §6.5 pasa a 0 omisiones críticas y la prueba
lo exige; si no se cierra dentro de los límites de latencia y sin un diccionario a medida no
acotado (Producto §3.3), queda documentada como abierta y aplazada por decisión del
propietario, sin bloquear M7–M11 ni el resto de Sirius 0.2, y PA-0.2-REC-01 permanece no
superada.

**Cerrar (o no) esa única omisión léxica no agota lo que Producto exige para «Mejor
recuperación».** La Definición de Producto §3.3-§3.4
(`docs/evolution/SIRIUS_PRODUCTO_0.2_MEMORIA_UTIL_v0.1_PROPUESTO.md:113-125`) y las
precondiciones que PA-0.2-REC-01 fija explícitamente
(`docs/evolution/SIRIUS_PLAN_PRUEBAS_0.2_v0.1_PROPUESTO.md:124-131,160-164`) exigen además dos
condiciones que ningún encargo M1–M12 asigna ni resuelve:

- Las dos puertas que ADR-002 (de la rama de evidencia, no `docs/decisions/ADR-002` de
  `main`) dejó **NO CONFORME**: recall crítico al 100 % en un caso, y conformidad de etapa
  14/46 (Producto §3.2(c)).
- La decisión sobre la «siembra al ensamblar contexto» (Producto §3.2(a)) — validarla con un
  banco ampliado que la ejercite, o retirarla del código —, que PA-0.2-REC-01 fija como su
  precondición 2 explícita: «sin esta precondición cumplida, esta PA no puede declararse
  superada» (`docs/evolution/SIRIUS_PLAN_PRUEBAS_0.2_v0.1_PROPUESTO.md:127-131`).

Ninguna de las dos entra en el paquete D1 que originó M7–M12 (§6, primer párrafo), y este
documento no las asigna a un encargo nuevo por la misma razón que no reabre D1: ampliar el
paquete es una decisión del propietario, no de este documento. Quedan, en su lugar,
explícitamente pendientes: **incluso si M12 cierra la omisión léxica, PA-0.2-REC-01 sigue
sin poder declararse superada** mientras estas dos condiciones no tengan encargo y criterio
propios, o una decisión explícita del propietario que las deje aplazadas — exactamente igual
que D3 ya deja aplazada la omisión léxica si M12 no la cierra. El cierre de M12, si ocurre,
no equivale al cierre de «Mejor recuperación» en su conjunto; ver también §9.

## 7. Impactos transversales

### 7.1 Migraciones

Dos migraciones nuevas en este documento: la tabla `memory_suggestions` (§3.7) y los campos
`category`/`category_locked` en `memories` y `decisions` (§6.1) — ambas aditivas, sin tocar
ninguna columna existente, mismo patrón que las migraciones aditivas ya mergeadas
(`migrations/versions/94418c79da9d_add_memory_subject_and_project.py`). §5 (proyectos
históricos) y §4 (conflictos asistidos) no requieren ninguna migración: ambos son consultas
o interfaz sobre columnas y tablas ya existentes.

### 7.2 Privacidad

Ninguno de los tres bloques diseñados en §3–§5 introduce una llamada de red nueva ni un
destino de datos nuevo: `MemorySuggestionRepository`, `ProjectRepository.list_completed_projects`
y la interfaz de resolución de conflictos son todas operaciones locales sobre el mismo
SQLite que ya usa Sirius 0.1 (`src/sirius/adapters/persistence/database.py`,
`src/sirius/ports/data_location.py`). De los bloques de §6, el etiquetador (§6.1) y el
filtro de relevancia (§6.3) son los únicos que introducen el único componente no-local que
contempla la Definición de Producto: un modelo local vía Ollama
(`docs/evolution/SIRIUS_PRODUCTO_0.2_MEMORIA_UTIL_v0.1_PROPUESTO.md` §2.2) — local a la
máquina, no un servicio remoto nuevo, y el mismo Ollama para ambos, nunca dos componentes de
red distintos. D1 adopta esa dependencia para el filtro, D7 la extiende al etiquetador;
ambas secciones (§6.1, §6.3) la diseñan con esa restricción como propiedad estructural de
sus adaptadores, no como opción de configuración: apuntan en exclusiva a `localhost`, sin
destino de red fuera del equipo del propietario, y ninguno de los dos llama jamás al
proveedor de pago (D7 punto 5).

### 7.3 Presupuesto de latencia de `ContextBuilder`

RNF-003 fija 300 ms P95 para construir el contexto (`docs/implementation/V8_EXECUTION.md:47`);
B12e registra ~120,9 ms medidos (el 40 % del presupuesto) como resultado histórico, no como
un requisito adicional (`docs/implementation/V8_EXECUTION.md:44-48`, §6.4). Los tres
bloques de §3–§5 no tocan `ContextBuilder.build()`
(`src/sirius/application/context.py:143-208`) en absoluto: §3 (sugerencias) vive fuera del
camino de construcción de contexto (una `MemorySuggestion` nunca se lee desde ahí, §3.5);
§4 (conflictos) es interfaz sobre una consulta ya excluida de `ContextBuilder`
(`src/sirius/application/detect_precedence_conflicts.py:14-16`); §5 (proyectos históricos)
usa un caso de uso separado que `ContextBuilder` no inyecta. Ninguno de los tres añade
coste. El etiquetado de §6.1 tampoco: corre asíncrono y diferido, nunca dentro de
`ContextBuilder.build()` (§6.4). El índice (§6.2) y el filtro (§6.3) sí tocan ese camino
directamente y son, por tanto, los que deben medirse contra RNF-003 — §6.4 fija cómo
(metodología de ADR-008, en los tres escenarios que fija esa sección) y asigna esa medición
a M11 (§8).

## 8. Orden de construcción propuesto

Encargos del tamaño de una vertical de Sirius 0.1 (ver §2 sobre la numeración `M1`…`M12`).
M1–M6 son independientes de los bloques de §6. M7–M12 (búsqueda mejorada y mejor
recuperación, decisiones D1 y D7) se añaden a continuación y dependen entre sí, en este
orden: M7 antes que M9 y M10 (necesita el pipeline de hoy como línea base antes de medir
cualquier cambio); M8 antes que M9 y M10 (ambos consumen el campo `category` que M8
construye); M9 y M10 antes que M11 (mide la integración completa, no cada pieza suelta);
M12 al final, porque su intento de cierre se apoya en el pipeline ya integrado por M7–M11.
A diferencia de una ronda anterior de este documento, ninguno de estos seis encargos queda
bloqueado a la espera de una decisión del propietario: D1 y D7 ya la resolvieron, y M8
(§6.1) es, precisamente, el encargo que construye la fuente de categoría que M9, M10 y M11
necesitan — el orden fija dependencias de secuencia de construcción, no una decisión
pendiente.

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
`CANCELLED` no dispara ninguna llamada, con un proveedor de prueba que ya empezó a emitir el
delimitador en la salida cruda antes de cancelar, y comprueba además que
`result.sirius_message.content` —el texto persistido con estado `CANCELLED`— no contiene el
delimitador ni la propuesta cruda; un resultado `FAILED` no dispara ninguna llamada, con el
mismo proveedor de prueba emitiendo el delimitador antes de fallar, y la misma comprobación
sobre `result.sirius_message.content` con estado `FAILED` — en los cuatro últimos casos, el
proveedor se invoca una sola vez por turno. El adaptador concreto de `LLMProvider` que
construya M6 añade, además, su propia prueba de que un delimitador partido entre dos
fragmentos consecutivos de la salida cruda del proveedor tampoco llega a `on_delta`, a
`LLMCompleted.text`, a `LLMCancelled.partial_text` ni a `LLMError.partial_text`: la
separación descrita en §3.2 no puede depender de que el delimitador llegue entero en un único
fragmento, ni de que el turno complete.

### M7 — Búsqueda mejorada: banco de evidencia portado y prueba automática

Portar el corpus de 47 casos y sus resultados esperados, sin modificarlos, desde
`evidence/adr001-spikes` a `tests/acceptance/fixtures/evidence_bank_47_casos.json` (§6.5);
`tests/acceptance/test_pa_0_2_rec_01_banco_evidencia.py`, que ejecuta ese banco contra el
pipeline de recuperación de `main` **tal como existe hoy** (antes de M8/M9/M10) y reporta la
línea base de aciertos exactos, elementos de más, omisiones críticas y cobertura.

**Criterio de aceptación:** una prueba de forma del fichero confirma 47 casos y 81
elementos esperados en total; la prueba automática de §6.5 existe, ejecuta y reporta las
cuatro métricas sin exigir todavía los suelos de D1/D2 (el pipeline de M7 es el de hoy, sin
campo de categoría, sin índice ni filtro, y puede no alcanzarlos aún — exigirlos es criterio
de M11); una prueba dedicada demuestra que `criticidad.razon_segura` no es leído por el
cargador que alimenta el pipeline bajo prueba, solo por el arnés de evaluación, y únicamente
para `criticidad.nivel`.

### M8 — Etiquetado de categoría: campo, migración, puerto y adaptador Ollama (D7)

Los siete puntos de D7 (§6.1): `category`/`category_locked` en `Memory` y `Decision`, su
migración aditiva; `CategoryClassifierPort` y `OllamaCategoryClassifierAdapter`;
`TagCategoryUseCase` y `CategoryTaggingWorker` sobre el `QThreadPool` ya existente, encolado
después del guardado, nunca dentro de su transacción; `SetCategoryUseCase` para la edición
del usuario, que fija `category_locked = True`; `list_uncategorized()` y el pase retroactivo
sobre elementos ya guardados; la rama transaccional de `CorrectMemoryUseCase.correct()` que
limpia `category` cuando no está bloqueada, y la orquestación en
`KnowledgeWidget._handle_correct_memory_clicked` que reencola el etiquetado tras el retorno
(§6.1, «Corrección de contenido y reetiquetado»).

**Criterio de aceptación:** prueba de dominio de que `category_locked` se fija al
establecer una categoría manual y de que, una vez fijado, ninguna llamada posterior de
`TagCategoryUseCase` lo sobrescribe (incluida una que llega después, simulando una
respuesta de Ollama en vuelo); una prueba de repositorio determinista que reproduce la
carrera exacta que motiva la escritura condicional (§6.1 punto 2) — pausar la ejecución de
`TagCategoryUseCase` justo después de invocar `CategoryClassifierPort.classify` y antes de
su intento de escritura, ejecutar `SetCategoryUseCase.set()` con una categoría distinta, y
solo entonces dejar que `TagCategoryUseCase` continúe — y confirma que la categoría final es
la del usuario, nunca la de Ollama, porque el `UPDATE ... WHERE category_locked = 0`
condicional no encuentra fila que actualizar; una segunda prueba de repositorio determinista
que reproduce la carrera distinta entre dos generaciones del propio etiquetado automático, la
que motiva atar esa misma escritura condicional a la revisión observada (§6.1 punto 2) —
sobre una memoria en su revisión 1, iniciar un primer `TagCategoryUseCase`, pausarlo justo
después de `classify()` y antes de su intento de escritura, corregir la memoria con
`CorrectMemoryUseCase.correct()` (que limpia `category` y crea la revisión 2), dejar que un
segundo `TagCategoryUseCase` clasifique y escriba sobre la revisión 2, y solo entonces dejar
que el primer `TagCategoryUseCase` —todavía anclado a la revisión 1— intente su escritura
tardía — y confirma que esa escritura tardía no encuentra fila que actualizar porque la
revisión vigente ya no es la 1, y que la categoría final es la que escribió el segundo
worker, nunca la del primero; prueba de integración de migración que sube y
baja las dos columnas nuevas en ambas tablas sin afectar ninguna existente; prueba de
`TagCategoryUseCase` con un doble del puerto que cubre categoría devuelta con éxito, Ollama
no disponible (`None`, sin excepción) y respuesta fuera del vocabulario cerrado (tratada
igual que `None`); prueba de que guardar una memoria o una decisión no espera nunca a que
el worker de etiquetado termine — el resultado de guardado ya está disponible antes de que
se resuelva el etiquetado, verificado con un doble del puerto que bloquea deliberadamente
hasta que la prueba lo libera; prueba de que `list_uncategorized()` no devuelve un elemento
ya etiquetado ni uno con `category_locked = True` aunque no tenga categoría; prueba de
`CorrectMemoryUseCase.correct()`, sin ningún doble ni importación de Qt, que confirma que
corregir el contenido de una memoria con `category_locked = False` limpia `category` a
`None` dentro de la misma transacción, y que corregir una memoria con `category_locked =
True` deja `category` y `category_locked` intactos; prueba de
`KnowledgeWidget._handle_correct_memory_clicked`, con un doble de `CorrectMemoryUseCase`,
que confirma que la interfaz encola un `CategoryTaggingWorker` nuevo sobre el elemento
corregido cuando el resultado devuelto trae `category is None`, y que no encola nada cuando
el resultado devuelto conserva `category_locked = True`.

### M9 — Búsqueda mejorada: índice de categoría determinista

`category_match` en `RankedKnowledge`, la función determinista que lo calcula en
`sirius.domain.relevance` — incluida la clasificación determinista de la consulta contra el
vocabulario cerrado, sin ninguna llamada a `CategoryClassifierPort` (§6.2) —, su cableado en
`RankRelevantKnowledgeUseCase.rank()` y su lugar en `_sort_key` (§6.2).

**Criterio de aceptación:** prueba unitaria de dominio con candidatos de categorías
distintas (usando el campo `category` que M8 ya persiste) que confirma el nuevo lugar de
`category_match` en la tupla de orden (después de `fts_match`, antes de la recencia),
incluidos los casos de consulta que no activa ninguna categoría del vocabulario
(`category_match` `False` para todos) y de candidato sin categoría todavía (`category_match`
`False` para ese candidato); re-ejecutar la prueba de M7 sobre el banco y comprobar que las
omisiones críticas bajan frente a la línea base de M7 (la cifra exacta es objetivo conjunto
de M7–M12, no de M9 aislado); volver a correr el benchmark de ADR-008 (§6.4) y publicar el
P95 medido.

### M10 — Búsqueda mejorada: filtro de relevancia con Ollama — puerto, adaptador y candado

`RelevanceFilterPort`, `OllamaRelevanceFilterAdapter` (local-only, con presupuesto de
tiempo configurable, fallo abierto) y el candado sobre el campo `category` que M8 persiste
(§6.3), protegiendo la categoría de máxima criticidad del vocabulario cerrado del banco.

**Criterio de aceptación:** pruebas unitarias con un doble de prueba del puerto que cubren
(i) filtro disponible que descarta candidatos no críticos, comprobando que el resultado
final los excluye; (ii) Ollama no instalado o conexión rechazada; (iii) Ollama acepta la
conexión y no responde hasta agotar su presupuesto de tiempo — un doble que acepta y no
contesta, no una ausencia (§6.4); (iv) respuesta con forma inesperada — en (ii)-(iv) el
resultado de `ContextBuilder._rank_related_knowledge` es idéntico al de antes de invocar el
filtro, sin ninguna excepción propagada fuera del adaptador; una prueba adicional confirma
que un candidato con `category` igual a la de máxima criticidad del canon (persistida por
M8) sobrevive aunque el doble de prueba del filtro intente descartarlo, y que un candidato
sin `category` todavía **también** sobrevive aunque el doble de prueba del filtro intente
descartarlo, hasta que `TagCategoryUseCase` le asigne una categoría que no sea la de máxima
criticidad. Además de las pruebas con doble, una prueba propia de
`OllamaRelevanceFilterAdapter` contra un transporte o servidor HTTP local de prueba (nunca
Ollama real) que entrega una respuesta válida, verificando que el adaptador la parsea en el
subconjunto y el orden esperados (§6.5).

### M11 — Búsqueda mejorada y Mejor recuperación: integración, medición de RNF-003 y de coincidencia del etiquetado

Cablear M9 y M10 en `ContextBuilder._rank_related_knowledge`; medir contra RNF-003 con la
metodología de ADR-008 en los tres escenarios que fija §6.4 (Ollama disponible dentro de su
presupuesto, Ollama ausente con fallo abierto inmediato, Ollama acepta la conexión y agota
el `timeout`); ajustar el `timeout` del adaptador hasta que los tres escenarios cumplan el
presupuesto; re-ejecutar la prueba de M7 con el pipeline ya integrado y confirmar el suelo
de D1 (aciertos exactos ≥ 29/47). Esta re-ejecución **es**, además, la primera medición real
de cobertura de PA-0.2-REC-01 sobre `main` que D2 exige para sustituir su suelo provisional
(§6.5): M11 registra el valor de cobertura que mida —no elige 64/81 ni ninguna otra cifra
por adelantado— y actualiza la aserción dura de la prueba de §6.5 a ese valor medido,
sustituyendo 63/81. Solo si la medición coincide con 63/81 el suelo queda literalmente
igual; en cualquier otro caso, 63/81 deja de ser el suelo desde este encargo en adelante.
M11 ejecuta además la medición de coincidencia del etiquetado que D7 punto 6 exige (§6.1,
§6.5): `CategoryClassifierPort` sobre los 47 casos del banco, comparado contra su categoría
canónica, publicando la cifra (aciertos/47) sin fijar un umbral por su cuenta. Cablear M9 y
M10 en `ContextBuilder._rank_related_knowledge` dentro de este mismo encargo no abre, por sí
solo, la puerta de activación contra datos reales que §6.3 deja cerrada por defecto: M11
construye el parámetro `category_matching_enabled` que §6.3 define y lo cablea con su valor
por defecto, `False` — el circuito completo queda armado con la puerta cerrada, la cifra
queda publicada, y es el propietario quien abre la puerta después, en dos pasos separados de
este encargo: registra el umbral en `STATUS.md` (§9) y, por separado, alguien fija
`category_matching_enabled = True` en `settings.json` (§6.3) — ninguno de los dos ocurre
dentro de M11. Lo que sí ocurre dentro de M11, para que esa activación manual sobreviva, es
la corrección de `MainWindow._save_configuration()` que §6.3 exige: partir de
`load_settings()` en vez de construir el diccionario desde cero, conservando cualquier clave
ajena a las seis que la vista conoce.

**Criterio de aceptación:** tabla de medición con el mismo formato que la de ADR-008
(`docs/decisions/ADR-008-cargar-en-lote-las-revisiones-vigentes-al-listar.md:111-117`), con
«construir contexto» P95 ≤ 300 ms en los tres escenarios, publicada como evidencia del
encargo; la prueba de M7, re-ejecutada, confirma el suelo de aciertos exactos (≥ 29/47) sin
exigir todavía 0 omisiones críticas (eso es M12); el suelo de cobertura que queda codificado
en la prueba tras este encargo es la cifra medida en esta primera ejecución real sobre
`main`, no 63/81 salvo que ambas coincidan; la cifra de coincidencia del etiquetado
(aciertos/47) queda publicada en la evidencia del encargo y registrada en `STATUS.md` junto
a D7, sin que este encargo fije por su cuenta el umbral exigible — eso queda para el
propietario, a la vista de la cifra (§9); una prueba adicional confirma que, con
`category_matching_enabled` ausente o `False` (puerta cerrada, el valor con el que M11
cablea el parámetro), un candidato real con categoría no crítica sigue protegido por el
candado y `category_match` es `False` para candidatos reales, exactamente el fallback que
§6.3 fija; una prueba simétrica, construyendo `RankRelevantKnowledgeUseCase`/`ContextBuilder`
con `category_matching_enabled=True`, confirma el estado abierto: un candidato real ya
clasificado en una categoría no crítica queda expuesto a `RelevanceFilterPort` (con un doble
de prueba del puerto que lo descarta) y el resultado final lo excluye, y `category_match`
compara la categoría real del candidato contra la que activa la consulta — esta prueba
verifica el contrato del parámetro en ambos valores, sin que M11 fije `True` en la
construcción con la que Sirius arranca por defecto; una última prueba cubre
`_save_configuration()` (§6.3): con `category_matching_enabled=True` ya en `settings.json`,
guardar cualquier otro ajuste desde ese método deja la clave intacta, en vez de perderla como
ocurre hoy.

### M12 — Mejor recuperación: intento de cierre de la última omisión crítica (D3)

Sobre el pipeline ya integrado por M7–M11, intentar cerrar la omisión crítica por
derivación léxica que la Definición de Producto §3.2(b) caracteriza («preferencia de
redacción» frente a «prefiere que redactes», ver §6.6), dentro del presupuesto de latencia
de §6.4 y sin construir un diccionario a medida no acotado (Producto §3.3).

**Criterio de aceptación — salida explícita en los dos sentidos, por decisión D3:**

- si se cierra: el caso del banco de M7 que hoy la registra como omisión pasa a acierto, la
  prueba de M7 se actualiza para exigir 0 omisiones críticas como suelo duro, y
  PA-0.2-REC-01 puede declararse superada si el resto de sus condiciones también lo están;
- si no se cierra dentro de esos límites: el encargo no falla por eso — cierra
  documentando el intento, las vías probadas y el motivo medido (no supuesto) por el que no
  se alcanzó, actualiza este documento (§6.6) y `docs/evolution/STATUS.md` dejando la
  omisión «abierta y aplazada por decisión del propietario», y actualiza la prueba de M7
  para afirmar explícitamente el conteo real de omisiones críticas medido — nunca relajado
  en silencio. PA-0.2-REC-01 permanece no superada en ese caso, tal como D3 exige
  literalmente, sin que eso bloquee M1–M11 ni el resto de Sirius 0.2.

## 9. Decisiones pendientes del propietario

Esta arquitectura no toma decisiones de producto, arquitectura o seguridad por su cuenta.
Las que la Definición de Producto dejaba abiertas para el bloque de este documento (§7.3 de
`docs/evolution/SIRIUS_PRODUCTO_0.2_MEMORIA_UTIL_v0.1_PROPUESTO.md`), más las que surgieron
durante la revisión de una ronda anterior de este documento, ya las resolvió el propietario,
registradas en `docs/evolution/STATUS.md` el 29 de agosto de 2026, y este documento las
traduce a diseño sin reabrirlas:

- **Fusionar o no la PR #117 como vía de entrada de su evidencia** — resuelta por D1: se
  incorpora completa, por encargos nuevos al Work Engine (M7–M12), no por fusión directa de
  esa PR.
- **La dependencia de Ollama en el filtro de relevancia** — resuelta por D1: se adopta;
  §6.3 diseña su puerto, su adaptador y el contrato de fallo abierto.
- **El origen y el ciclo de vida de la categoría de un candidato real** — resuelta por D7:
  un campo nuevo, opcional, en `Memory`/`Decision`, etiquetado automáticamente por Ollama de
  forma asíncrona y diferida, editable y definitivo si lo corrige el usuario, retroactivo,
  sin proveedor de pago (§6.1). Esto desbloquea, sin premisa pendiente, M8–M12 — una ronda
  anterior de este documento los dejaba bloqueados exactamente por este vacío.
- **La última omisión crítica de recuperación** caracterizada en la Definición de Producto
  §3.3 — resuelta por D3: se intenta cerrar dentro del mismo paquete de incorporación (M12,
  §6.6); si no se consigue, queda documentada como abierta y aplazada por decisión del
  propietario, sin bloquear el resto — nunca como defecto sin diagnosticar.
- **El umbral de coincidencia exigible al etiquetado automático de Ollama** — D7 punto 6
  fija que se mide, no que se decide ya: M11 (§8) mide la coincidencia contra el banco de 47
  casos y publica la cifra; el propietario registra el umbral exigible a la vista de esa
  medición, mismo patrón que D2 ya usó para el suelo de cobertura. Este documento no elige
  un umbral por su cuenta. Mientras ese umbral no esté registrado en `STATUS.md`, la puerta
  de activación que §6.3 deja cerrada por defecto permanece cerrada: `category_match` (§6.2)
  y el candado (§6.3) no consumen la categoría de ningún candidato real, solo la del banco de
  medición — M8–M11 se construyen y se miden igual mientras tanto, sin que esta puerta los
  bloquee (§6.3). Registrar el umbral en `STATUS.md` es la decisión; traducirla a
  comportamiento real es la clave `category_matching_enabled` de `settings.json` que §6.3
  define — fijarla a `True` es una acción separada del registro documental, no asignada a
  ningún encargo M1–M12, que corresponde a quien registre el umbral y confirme que la cifra
  medida lo alcanza.

Sigue sin resolver, fuera del alcance de esta actualización — §3.1 de este documento la deja
donde estaba, sin recaracterizarla:

- El origen de los estados `CANDIDATA`/`RECHAZADA` que una orden anterior daba por
  existentes (§3.1 de este documento).
- **Las dos puertas que ADR-002 (de la rama de evidencia, no `docs/decisions/ADR-002` de
  `main`) dejó NO CONFORME** — recall crítico al 100 % en un caso, y conformidad de etapa
  14/46 (Producto §3.2(c)) — **y la decisión sobre la «siembra al ensamblar contexto»**
  (Producto §3.2(a)), que PA-0.2-REC-01 fija como su precondición 2 explícita
  (`docs/evolution/SIRIUS_PLAN_PRUEBAS_0.2_v0.1_PROPUESTO.md:124-131`). Ningún encargo
  M1–M12 las asigna (§6.6): quedan pendientes de un encargo futuro o de una decisión del
  propietario que las aplace, igual que D3 aplaza la omisión léxica si M12 no la cierra.
  PA-0.2-REC-01 no puede declararse superada mientras sigan pendientes, con independencia de
  si M12 cierra o no la omisión léxica.

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

## 11. Ola de paridad en producción — M13 en adelante

> Ampliación añadida por la incidencia #478 (WI-20260831-104900), por orden del
> propietario del 31-08-2026 (referencia `sesion-cli`): «si recuerda 29 cosas de 47 a mí
> no me vale… necesito que lo recuerde bien». Este §11 se añade al final del documento, sin
> tocar una sola línea de §0-§10: cualquier cita externa a una línea de este fichero
> (`tests/acceptance/test_pa_0_2_rec_01_banco_evidencia.py:2139`,
> `tests/integration/test_local_performance.py:635`, entre otras) sigue apuntando
> exactamente a donde apuntaba. El registro de la decisión que este §11 desarrolla es
> `docs/decisions/ADR-119-disenar-la-ola-de-paridad-en-produccion-portar-la-semantica-del-arnes-tras-la-puerta-category-matching-enabled-la-peticion-de-contexto-real-y-el-plan-de-optimizacion-de-rnf-003-incidencia-478.md`
> (PROPUESTO); este apartado es su desarrollo de diseño, no una copia de su decisión.

### 11.0 Hechos de partida (cítalos, no se reinterpretan)

M11 (incidencias #471/#473, ADR-117, §8-M11 arriba) dejó completamente cableado el
circuito de la puerta `category_matching_enabled` —de `settings.json` a
`RankRelevantKnowledgeUseCase`/`ContextBuilder`, vía `composition_root`
(`src/sirius/composition_root.py:455-482`, `:602`)— pero con su criterio de suelo
explícitamente **NO aprobado**. Verificado contra `main` en el momento de esta
incidencia:

- Con la puerta abierta, el camino real de producción —`RankRelevantKnowledgeUseCase`/
  `ContextBuilder` construidos exactamente como `composition_root` los construiría, nunca
  el arnés de examen— mide **4/47** aciertos exactos, 609 elementos de más, 9 omisiones
  críticas y 59/81 de cobertura (ADR-117, tabla «Banco con la puerta abierta»), y P95 de
  «construir contexto» **438,8-496,1 ms** en los tres escenarios de RNF-003, medidos en el
  runner de ADR-117; el comentario del corrector en la incidencia #471 reprodujo la misma
  brecha en otro runner con P95 **718,5-778,2 ms** — la incidencia de origen de esta
  ampliación cita ese rango como «hoy ese camino mide 4/47 y P95 438-780 ms».
- El arnés de examen ya fusionado (`tests/acceptance/staged_engine_category_and_relevance.py`,
  ADR-109..ADR-115) blinda como aserción dura, sobre su propia traducción de laboratorio
  —que nunca se ejecuta en producción—, **aciertos exactos ≥ 29/47**, **omisiones críticas
  ≤ 1** y **cobertura ≥ 63/81**
  (`tests/acceptance/test_pa_0_2_rec_01_banco_evidencia.py:1148-1153`, función
  `test_el_banco_se_ejecuta_contra_el_motor_portado_y_reporta_las_cuatro_metricas`).
- La línea de llegada de esta ola ya existe como conocimiento ejecutable: dos pruebas
  `pytest.mark.xfail(strict=True)` que hoy fallan-como-se-espera sobre el camino real de
  producción —
  `tests/acceptance/test_pa_0_2_rec_01_banco_evidencia.py:2135`
  (`test_el_suelo_del_criterio_de_m11_aciertos_exactos_29_47_en_el_paquete_completo`,
  afirma `metricas.aciertos_exactos >= 29`, línea 2147) y
  `tests/integration/test_local_performance.py:631`
  (`test_el_suelo_de_rnf_003_p95_300ms_en_los_tres_escenarios_del_paquete_completo`, afirma
  `medicion.p95 <= LIMITE_OPERACION_MS` —300 ms, `tests/integration/test_local_performance.py:187`—
  en los tres escenarios, líneas 651-658)—, ambas citando ADR-117 en su `reason` (ADR-117
  §«Estado del hito: decisión»). Esta ola no termina solo con estas dos: §11.5 (M17) exige
  además, como aserciones duras propias del propio M17, que `omisiones_criticas <= 1` y
  `cobertura >= 63 / 81` pasen sobre el mismo camino real antes de declarar la ola cerrada
  (§11.5, M17).
- Ninguna de las piezas que faltan es trabajo nuevo por inventar: **todas están ya
  fusionadas en `main`**, viviendo en el arnés de examen
  (`tests/acceptance/staged_engine_category_and_relevance.py`,
  `tests/acceptance/staged_engine_case_translation.py`) o detrás de las reglas de
  producto más estrictas que M9/M10 ya construyeron (§6.2, §6.3 arriba): activación única
  de `category_matches_query` en vez de activación múltiple con restricción de ámbito
  (ADR-113/114/115), el candado-unión de `ContextBuilder._apply_relevance_filter` en vez
  de la regla de críticas original RF-25/RF-26 (ADR-112/113), la ausencia de siembra en
  contexto (ADR-113), y la política uniforme `_peticion_ordinaria` en vez de la petición
  por caso del laboratorio (ADR-110/111) que ninguna consulta real declara.

### 11.1 Diagnóstico: qué falta en el camino real, pieza por pieza

Las cinco piezas siguen exactamente el orden en que ADR-112..ADR-115 las midieron
necesarias en el arnés. Para cada una: dónde vive hoy (solo en el arnés), su equivalente
—o ausencia— en producción, y la cifra que ADR-112..ADR-115 le atribuyen.

1. **Activación de categoría múltiple, no única.** `activa_categoria_buscable`
   (`tests/acceptance/staged_engine_category_and_relevance.py:317-336`) activa la
   categoría si la consulta contiene **cualquiera** de las palabras del vocabulario del
   banco, sin exigir unicidad — réplica de que el índice lateral del laboratorio
   (`experiments/adr002/lateral/categoria.py`, rama `evidence/adr001-spikes`) indexa las
   palabras del vocabulario juntas como el mismo contenido para toda identidad no
   ordinaria. El equivalente de producto, `category_matches_query`
   (`src/sirius/domain/relevance.py:142-171`), exige activación única: `activated =
   {...}; if len(activated) != 1: return False` (líneas 168-169) — diseño deliberado de
   M9/PR #450, no un descuido. ADR-112 mide el coste de esa diferencia: de las cinco
   consultas del banco que activan alguna palabra del vocabulario, la activación única
   solo activa una; las otras cuatro contienen dos palabras a la vez y no activan nada
   (`docs/decisions/ADR-112-el-indice-de-categoria-y-el-filtro-de-relevancia-conectados-al-arnes-del-banco-incidencia-463-mejoran-cobertura-y-omisiones-criticas-pero-empeoran-los-elementos-de-mas-y-no-alcanzan-d1.md`,
   causa 1).
2. **Regla de críticas original (RF-25/RF-26), no el candado-unión de M10.**
   `aplicar_regla_de_criticas_original`
   (`tests/acceptance/staged_engine_category_and_relevance.py:472-513`) solo rescata una
   identidad descartada por el filtro si es de categoría de máxima criticidad **y** el
   filtro sí conservó algo de lo que le llegó para ese caso (RF-25); si el filtro declaró
   ausencia total, ese veredicto se respeta entero, sin rescate (RF-26). El candado-unión
   de M10 (`ContextBuilder._apply_relevance_filter`,
   `src/sirius/application/context.py:239-258`) protege, en cambio, **todo** candidato de
   la categoría de máxima criticidad y **todo** candidato sin categoría todavía,
   incondicionalmente — sobre un banco con solo dos estados de categoría posibles
   (`"restriccion"` o ninguna), esa unión protege al 100 % de los candidatos y neutraliza
   el filtro por completo
   (`docs/decisions/ADR-112-el-indice-de-categoria-y-el-filtro-de-relevancia-conectados-al-arnes-del-banco-incidencia-463-mejoran-cobertura-y-omisiones-criticas-pero-empeoran-los-elementos-de-mas-y-no-alcanzan-d1.md`,
   causa 2). ADR-113 mide que sustituir el candado por RF-25/RF-26 baja `elementos_de_mas`
   de 153 a 102 sobre su configuración intermedia.
3. **Siembra en contexto.** `siembra_de_contexto`
   (`tests/acceptance/staged_engine_category_and_relevance.py:412-444`), activada solo
   cuando `pide_contexto(proposito)` es cierto (`proposito` contiene la subcadena
   `"contexto"`, líneas 403-409), añade toda identidad no admitida de categoría de máxima
   criticidad dentro del ámbito declarado. No existe ningún equivalente en producción: ni
   `ContextBuilder` (`src/sirius/application/context.py`) ni
   `RankRelevantKnowledgeUseCase` (`src/sirius/application/rank_relevant_knowledge.py`)
   inspeccionan jamás el campo `proposito` de la `Peticion` para sembrar candidatos —
   `_peticion_ordinaria` fija `proposito` a un literal fijo
   (`_PROPOSITO_RECUPERACION_ORDINARIA`, `src/sirius/application/rank_relevant_knowledge.py:75`)
   que ninguna función de producción llega a inspeccionar con `pide_contexto`. Solo dos de
   los 47 casos del banco declaran ese propósito (`B04-CA-33`, `B04-CA-34`): el propio
   módulo del arnés documenta que esta regla se confirma «por construcción», no de forma
   independiente (docstring de `siembra_de_contexto`).
4. **Restricción por ámbito del índice de categoría.** `_en_ambito_declarado`
   (`tests/acceptance/staged_engine_category_and_relevance.py:339-356`) exige que el
   proyecto de la identidad coincida con el ámbito declarado de la petición, o que sea de
   ámbito global (`"PRJ-GLOBAL"`); la usan tanto `indice_de_categoria`
   (líneas 359-401) como `siembra_de_contexto`. El bloque `solo_por_categoria` de
   producción (`src/sirius/application/rank_relevant_knowledge.py:243-280`) no filtra por
   ámbito en ningún punto: itera `list_current_memories()`/`list_current_decisions()`
   completos y solo comprueba `category_match(...)`, nunca `project_id` contra la consulta
   — «`category_match` no es un filtro de alcance» es, hoy, el diseño de producto vigente
   (§6.2 arriba). ADR-114 mide que añadir esta restricción en el arnés baja
   `elementos_de_mas` de 110 a 62.
5. **Dos mitades de puerta (G8/G12) sobre la ampliación por categoría/siembra.**
   `vigente_en_tiempo_objetivo`
   (`tests/acceptance/staged_engine_category_and_relevance.py:516-540`) y
   `truncar_por_limite_duro` (líneas 544-574) reproducen, respectivamente, la mitad de
   vigencia temporal de `G8` (`src/sirius/domain/staged_engine_gates.py:194-210`, sin el
   corte de registro) y la mitad de límite de `G12`
   (`src/sirius/domain/staged_engine_gates.py:304-332`, sin la declaración de
   desbordamiento), aplicadas **solo** sobre el conjunto que `indice_de_categoria`/
   `siembra_de_contexto` añaden — nunca sobre lo que el motor por etapas genera por sí
   mismo, que ya pasa por `G8`/`G12` completas dentro de `recuperar()`
   (`src/sirius/domain/staged_engine.py:300`, `:357`). El bloque `solo_por_categoria` de
   producción tampoco pasa nunca por `G8`/`G12` del motor: el mismo hueco que ADR-115
   cerró en el arnés sigue abierto, sin cerrar, en el camino de producción. ADR-115 mide
   que cerrarlo en el arnés recupera 12 de los 62 `elementos_de_mas` de ADR-114 y alcanza
   el suelo D1 (29/47, ≤1 crítica, 63/81).
6. **Petición por caso, no política uniforme.** Ver §11.3 — se trata aparte porque, a
   diferencia de las cinco anteriores, no toda su brecha es igual de cerrable con
   información que una consulta real posee.

### 11.2 Decisión de diseño (a): activación de categoría e integridad de críticas con la puerta abierta

**Decisión (ADR-119): sí se sustituyen, exclusiva y únicamente cuando
`category_matching_enabled` es `True`.** El diseño anterior —`category_matches_query` de
activación única (§6.2) y el candado-unión de M10 (§6.3)— **se conserva literalmente, sin
cambiar una línea de comportamiento, como el estado-cerrado**: con la puerta cerrada (el
valor por defecto, `False` o ausente, y el único que `composition_root` fija hoy en la
construcción con la que Sirius arranca, `src/sirius/composition_root.py:455`), el camino
de producción sigue siendo exactamente el de hoy — las pruebas de identidad ya existentes
(`tests/unit/test_composition_root_relevance_gate.py`,
`tests/integration/test_rank_relevant_knowledge.py`,
`tests/integration/test_context_builder.py`) siguen intactas y en verde, tal como exige el
objetivo de esta incidencia, porque ningún encargo de §11.5 toca su código bajo ese
estado.

**Justificación, citando el coste que ADR-109..ADR-115 y ADR-117 ya midieron de no
sustituir:** ADR-111 mide 23/47 con la petición por caso ya portada pero sin estas cinco
piezas; ADR-112 mide que, conectadas sin más las piezas de producto ya existentes
(activación única + candado-unión), el candado protege el 100 % del banco y neutraliza el
filtro, sin mejorar `aciertos_exactos` (sigue en 23/47); y el camino real de producción,
que hoy tiene exactamente esas dos piezas vigentes tras la puerta, mide **4/47** — peor
que el 23/47 aislado de ADR-111 porque además le falta la petición por caso (§11.3). Sin
sustituir estas piezas, ningún encargo futuro puede acercar el camino real al suelo D1: es
la misma disyuntiva que ADR-117 dejó explícitamente para «la siguiente ola, del
propietario», y esta incidencia es esa ola.

**Lo que esta justificación no puede afirmar: que las cuatro piezas de abajo, solas y sin
la siembra en contexto, ya se midieron suficientes para 29/47, ≤1 crítica y 63/81.**
Ninguna medición existente aísla estas cuatro piezas de la quinta (la siembra): la fila
final de ADR-113 que primero llega a 0 omisiones críticas y 63/81 de cobertura ya incluye
la siembra (fila 3), y la fila final de ADR-115 que alcanza el suelo D1 completo, 29/47,
aplica G8/G12 sobre `obtenido_por_el_motor | categoria | siembra` — también con la siembra
dentro del conjunto. La fila 2 de ADR-113 (categoría + RF-25/RF-26) es una línea base
parcial sin siembra, no una medición de las cuatro piezas: le faltan las otras dos,
restricción de ámbito y G8/G12. Mide 27/47, 102 elementos de más, 4 omisiones críticas,
59/81 de cobertura — por debajo del suelo D1 en las cuatro métricas, no en tres; el
paquete completo de cuatro piezas no tiene medición propia hasta M16. Si estas cuatro
piezas bastan por sí solas es, por tanto, una pregunta abierta, no una cifra ya
establecida: M16 la mide por primera vez sobre el camino real (§11.5) y M17 la evalúa
contra el suelo D1, registrando el resultado real —alcanzado o no— sin maquillarlo.

**Qué se porta, detrás de la puerta abierta, en producción:**

- Un índice de categoría buscable de activación múltiple, paralelo a
  `category_matches_query` (que sigue existiendo, sin cambios, para el estado-cerrado):
  activa la categoría del candidato si la consulta contiene **cualquiera** de los
  términos del vocabulario cerrado (§6.1/§6.5), no exactamente uno — mismo comportamiento
  que `activa_categoria_buscable` demuestra en el arnés, ahora sobre el vocabulario real
  de producto en vez del vocabulario de cinco palabras del banco.
- Restricción por ámbito sobre esa activación: un candidato solo se admite por categoría
  si su `project_id` coincide con el proyecto activo de la petición, o si es de ámbito
  global — mismo criterio que `_en_ambito_declarado`. Sin esta restricción, ADR-114 ya
  midió que `elementos_de_mas` casi se duplica (62 → 110) sobre el banco; no hay razón
  para esperar que el efecto sea menor sobre datos reales con más de un proyecto.
- La regla de críticas original (RF-25/RF-26) sustituye al candado-unión como el mecanismo
  de integridad de críticas **cuando la puerta está abierta**: rescata una identidad
  descartada por `RelevanceFilterPort` solo si es de la categoría de máxima criticidad
  (`composition_root._MAX_CRITICALITY_CATEGORY`, `"salud"`,
  `src/sirius/composition_root.py:144`) **y** el filtro sí conservó algo de lo que le
  llegó para esa consulta; si el filtro declaró ausencia total para la consulta completa,
  ese veredicto se respeta sin rescate. Un candidato **sin categoría todavía** (D7 punto 2,
  etiquetado pendiente) sigue protegido siempre, sin condición — eso no lo cambia esta
  ola: la Definición de Producto exige que ningún elemento crítico recuperado pueda
  descartarse (§6.3 arriba), y un elemento sin clasificar todavía no puede excluirse con
  seguridad de ser justo ese elemento crítico.
- G8/G12 sobre la ampliación por categoría: antes de entregar el conjunto combinado
  (motor + categoría) a la regla de críticas, se descarta lo que no esté vigente en el
  tiempo objetivo de la petición (mitad de `G8`) y se trunca al límite duro de la petición
  ordenando por criticidad (mitad de `G12`) — mismo criterio que
  `vigente_en_tiempo_objetivo`/`truncar_por_limite_duro`, ahora también sobre datos reales
  y no solo sobre el banco.

**Siembra en contexto: aplazada, no se porta en esta decisión.** `siembra_de_contexto`
queda fuera de la sustitución anterior mientras su precondición documentada siga sin
resolverse (M15, más abajo, la nombra con su cita exacta): solo dos de los 47 casos del
banco la ejercitan y se confirma «por construcción», no de forma independiente. El plan de
pruebas fija como precondición de PA-0.2-REC-01 que se resuelva por una de dos vías
excluyentes entre sí, nunca ambas — ampliar el banco con casos independientes que la
ejerciten, o retirarla del código —, y las dos vías no llevan al mismo destino: ampliar el
banco resuelve la precondición dejando abierto que un encargo posterior reconsidere portar
`siembra_de_contexto` (condicionado a que el propietario registre esa reconsideración);
retirarla del código resuelve la precondición cerrando esa alternativa — no quedaría
`siembra_de_contexto` que portar, y ningún encargo posterior la porta. Este documento no
escoge por el propietario cuál de las dos vías se sigue; solo la deja fuera de la opción
(b) mientras la elección no se registre, igual que D3 (§6.6) deja aplazada la omisión
léxica hasta que se registre su propia decisión. Esta ola no la incluye en la opción (b)
que ADR-119 decide: la opción (b) se restringe, en esta incidencia, a las cuatro piezas de
arriba.

Estas cuatro piezas viven, con la puerta abierta, en el mismo punto de integración que §6.2
ya fijaba —dentro de `RankRelevantKnowledgeUseCase._rank_via_staged_engine`
(`src/sirius/application/rank_relevant_knowledge.py:153-282`), sustituyendo el bloque
`solo_por_categoria` actual (líneas 243-280)— y en `ContextBuilder._apply_relevance_filter`
(`src/sirius/application/context.py:239-258`), sustituyendo su candado-unión actual, sin
mover ninguno de los dos puntos de integración que D1 ya fijó.

### 11.3 La petición en producción (b): ámbito y propósito reales, y la parte de la brecha que no se cierra

Las consultas reales que llegan a `RankRelevantKnowledgeUseCase.rank()` no declaran
modo, propósito, cardinalidad ni límite: `_peticion_ordinaria`
(`src/sirius/application/rank_relevant_knowledge.py:84-105`) fija los cuatro a un valor
único y fijo para toda consulta — `Modo.M1_ORDINARIO`, un propósito literal fijo,
`Cardinalidad.EXHAUSTIVA`, y un límite que no ata (`_LIMITE_SIN_ATAR = 100_000`, línea 81)
— nunca una `Peticion` distinta por consulta, a diferencia de `peticion_desde_caso`
(`tests/acceptance/staged_engine_case_translation.py:120-153`), que construye una
`Peticion` propia para cada uno de los 47 casos del banco a partir de un campo del propio
fixture, `peticion_p2` (modo, propósito, permiso, cardinalidad, límite declarados por
caso). ADR-110 mide el coste de la política uniforme (11/47, sin petición por caso) frente
a ADR-111 (23/47, con petición por caso portada) — una ganancia de **+12/47** que ninguno
de los dos ADR atribuye a un campo aislado, porque ambos midieron el efecto combinado de
los cuatro campos a la vez.

**Diseño de la petición por defecto del producto:**

- **Ámbito**: se deriva del proyecto activo, información que `rank()` ya lee para calcular
  `project_matches_active` (`self._project_repository.get_active_project()`,
  `src/sirius/application/rank_relevant_knowledge.py:193-194`) — con un proyecto activo,
  `Ambito(global_=False, proyectos=(active_project_id,))`; sin proyecto activo,
  `Ambito(global_=True, proyectos=())`, igual que hoy. Esto no es información inventada:
  es la misma que ya existe y ya se usa para otra señal.
- **Propósito**: se declara honestamente que la llamada ensambla el contexto de un turno,
  porque eso es estructuralmente cierto para **toda** llamada real a `rank()` — la única
  que existe en producción ocurre desde `ContextBuilder._rank_related_knowledge`
  (`src/sirius/application/context.py:221-237`) para construir el `Context` que
  `SendMessageUseCase` envía al proveedor. A diferencia del ámbito o de la cardinalidad,
  esto no exige ningún dato nuevo del turno: es un hecho sobre quién llama, no sobre el
  contenido de la consulta, y permite que la siembra en contexto (§11.2) se active para
  toda consulta real, no solo para los dos casos del banco que la declaran expresamente.
- **Modo y cardinalidad**: se mantienen en `Modo.M1_ORDINARIO`/`Cardinalidad.EXHAUSTIVA`
  para toda consulta real. No hay ninguna señal en una consulta de conversación ordinaria
  que distinga «modo histórico» (`M2`, `admite_no_vigentes=True`) de un turno normal, ni
  ningún oráculo de cuántos resultados una consulta real «espera» —
  `Cardinalidad.EXACTA` exige `objetivos = max(1, len(caso["resultado_esperado"]))`
  (`tests/acceptance/staged_engine_case_translation.py:136-138`), un campo que solo existe
  porque el banco es un fixture de prueba con resultado esperado conocido de antemano.
- **Límite**: se mantiene sin atar (`_LIMITE_SIN_ATAR`). Ningún encargo de esta ola
  introduce un límite duro por consulta real: hacerlo exigiría una política de producto
  sobre cuántos elementos "basta" recuperar por turno, que ni la Definición de Producto ni
  esta incidencia piden diseñar — `apply_context_budget`
  (`src/sirius/application/context_budget.py:149-195`) ya recorta el resultado final por
  presupuesto de tokens, aguas abajo de este punto, sin necesidad de un límite duro aquí.

**Honestidad sobre lo que esta parte de la brecha no puede cerrar, cuantificado y
nombrado, no escondido:** de los +12/47 que ADR-110→ADR-111 miden al portar la petición
por caso completa, este documento no puede afirmar cuánto corresponde solo a declarar
ámbito y propósito reales (las dos piezas que sí se diseñan arriba) frente a declarar
`Cardinalidad.EXACTA`/límite `DURO` por caso (las dos que no se diseñan, porque exigirían
un oráculo de resultados esperados que ninguna consulta real tiene) — ninguno de los dos
ADR midió el efecto de cada campo por separado. Lo que sí se puede afirmar: **la parte de
la petición por caso que depende de conocer de antemano el resultado esperado de la
consulta (cardinalidad `EXACTA`, límite `DURO` declarado por caso) no tiene ningún
equivalente honesto en producción y esta ampliación no la diseña** — es una brecha
reconocida, no cerrada, que M17 (§11.5) debe cuantificar de nuevo, esta vez sobre datos
reales, si al medir el pipeline integrado con ámbito/propósito reales pero sin
cardinalidad/límite por caso el suelo D1 sigue sin alcanzarse por esta causa específica.

### 11.4 RNF-003 (c): presupuesto y plan de optimización para volver a ≤ 300 ms P95 con el paquete abierto

**Estado medido (ADR-117, sin remedir aquí — este documento es diseño, no medición):**
P95 de «construir contexto» con el paquete completo activo, 438,8-496,1 ms en los tres
escenarios de RNF-003 sobre el runner de ADR-117 (145-165 % del límite de 300 ms), y
718,5-778,2 ms sobre el runner que usó el corrector de la incidencia #471 — el rango
«438-780 ms» que cita el objetivo de esta incidencia. ADR-117 ya descarta que el coste
dominante sea el `timeout` del filtro de relevancia
(`composition_root._RELEVANCE_FILTER_TIMEOUT_SECONDS`, 50 ms,
`src/sirius/composition_root.py:157`): el escenario (b) —Ollama ausente, conexión
rechazada de inmediato, sin esperar ningún `timeout`— mide en la misma banda que (a)/(c),
así que bajar el `timeout` no cerraría la brecha (§6.4 arriba ya lo advertía en abstracto;
ADR-117 lo confirma con la medición).

**Diagnóstico de causa, por lectura directa del código (no una medición nueva de esta
incidencia):**

1. `_peticion_ordinaria` fija siempre `Cardinalidad.EXHAUSTIVA`
   (`src/sirius/application/rank_relevant_knowledge.py:102`), y `S1` —la parada temprana
   por cardinalidad— está deshabilitada por diseño bajo `EXHAUSTIVA`, sin excepción
   (`src/sirius/domain/staged_engine_stops.py:54-55`): «una búsqueda exhaustiva no puede
   declararse suficiente por cuota». En consecuencia, `recuperar()` recorre siempre las
   cuatro etapas de expansión `E1`-`E4` en cada llamada a `rank()`
   (`src/sirius/domain/staged_engine.py:292-323`, el bucle `for etapa in
   ETAPAS_DE_EXPANSION`), nunca para antes por haber encontrado ya suficiente.
2. Cada etapa dispara sus propias consultas al puerto de persistencia
   (`src/sirius/adapters/persistence/staged_engine_candidate.py:118-119`, `E1` llama a
   `por_clave_exacta` y `por_termino_lexico`; `:149` y `:175-176`, `E2`/`E3` llaman de
   nuevo a `por_termino_lexico`/`por_prefijo_de_sujeto`; `:219`, `E4` llama a
   `historial_y_fuentes`), y dos
   de esos métodos del puerto ejecutan **dos consultas SQL por cada clave o prefijo**,
   dentro de un bucle Python, en vez de una sola consulta por lote —
   `StagedEnginePort.por_clave_exacta`
   (`src/sirius/adapters/persistence/staged_engine_port.py:223-243`, el bucle `for clave
   in utiles`) y `por_prefijo_de_sujeto`
   (`src/sirius/adapters/persistence/staged_engine_port.py:267-296`, el bucle `for prefijo
   in utiles`) — a diferencia del patrón ya adoptado en ADR-008 para el listado de
   revisiones vigentes (`docs/decisions/ADR-008-cargar-en-lote-las-revisiones-vigentes-al-listar.md`),
   que sustituyó exactamente este tipo de bucle por una consulta en lote.
3. El bloque `solo_por_categoria` de `_rank_via_staged_engine`
   (`src/sirius/application/rank_relevant_knowledge.py:243-280`) recorre, además de lo que
   el motor por etapas ya recorrió por su cuenta, la totalidad de
   `list_current_memories()`/`list_current_decisions()` — un segundo barrido completo del
   corpus en cada llamada a `rank()` con la puerta abierta, sobre el mismo conjunto de
   referencia de 500 recuerdos/100 decisiones que ya usa ADR-008.

Sobre el conjunto de referencia de ADR-008 (5.000 mensajes, 500 recuerdos, 100 decisiones,
10 proyectos), estas tres causas son plausiblemente responsables de la mayor parte de la
diferencia entre los ~120,9 ms que B12e mide con la puerta cerrada
(`docs/implementation/V8_EXECUTION.md:270`) y los ~450-780 ms que ADR-117 mide con la
puerta abierta: ninguna de las tres depende de si Ollama está disponible (coherente con
que el escenario (b), sin Ollama, mida en la misma banda que (a)/(c)).

**Plan de optimización, por causa, cada uno asignado a un encargo de §11.5:**

1. **M13** — batch de consultas en `StagedEnginePort`: sustituir los bucles de
   `por_clave_exacta`/`por_prefijo_de_sujeto` por una sola consulta SQL con `IN (...)` (o
   `OR` encadenado) sobre todas las claves/prefijos de una llamada, mismo patrón que
   `_por_ids_mixtos` ya usa para ids (`src/sirius/adapters/persistence/staged_engine_port.py:201-219`,
   marcas de parámetro nombradas `:m0`, `:m1`, …).
2. **M13** (mismo encargo, misma causa) — evitar el segundo barrido completo del corpus en
   `solo_por_categoria`: sustituir `list_current_memories()`/`list_current_decisions()`
   (que ya se invocan una sola vez por llamada a `rank()` hoy — construir un índice en
   memoria a partir de esa misma llamada no reduce nada, sigue leyendo el corpus completo)
   por una consulta al puerto de persistencia filtrada por categoría, ejecutada en SQL
   (`WHERE category IN (...)`, mismo patrón por lote que el punto 1), que solo devuelve los
   candidatos de las categorías relevantes en vez de cargar el corpus completo en memoria
   para filtrarlo en Python.
3. **M17** (medición) mide si M13 basta para bajar de los ~450-780 ms actuales a ≤ 300 ms
   P95 en los tres escenarios; si no basta, M17 lo registra tal cual —igual que ADR-117
   registró el incumplimiento de M11— y esta arquitectura no promete de antemano que M13
   sea suficiente.

**Cómo se mide (sin cambios de metodología frente a §6.4/ADR-008/ADR-117):** el mismo
benchmark de ADR-008, mismo conjunto de referencia, misma máquina, los mismos tres
escenarios de RNF-003 que §6.4 ya fija (Ollama disponible dentro de presupuesto, Ollama
ausente con fallo abierto inmediato, Ollama acepta la conexión y agota el `timeout`), con
el paquete completo activo (M8-M12 más las piezas de §11.2 ya integradas) — exactamente lo
que `test_construir_contexto_con_el_paquete_completo_activo_en_los_tres_escenarios`
(`tests/integration/test_local_performance.py`) ya ejecuta hoy, y lo que
`test_el_suelo_de_rnf_003_p95_300ms_en_los_tres_escenarios_del_paquete_completo`
(`tests/integration/test_local_performance.py:631`) ya afirma como suelo `xfail(strict=True)`.

### 11.5 Encargos M13 en adelante (d)

Continúan la numeración de §8 (M1…M12); viven en este §11 por la restricción de evidencia
de esta incidencia (no desplazar ninguna línea de §0-§10, ver la nota al inicio de este
apartado), no porque rompan el orden de encargos. Dependencias: M13 y M14 son
independientes entre sí y pueden construirse en paralelo; M15 depende de M14 (la regla de
críticas original necesita el candidato ya expuesto por la activación múltiple de
categoría para poder rescatarlo o no); M16 depende de M14 y M15 (cablea ambos en
`RankRelevantKnowledgeUseCase`/`ContextBuilder`); M16 también depende de la petición de
producción (mismo encargo, ver más abajo); M17 depende de M13-M16 completos (mide el
paquete integrado, no piezas sueltas — mismo principio que ya fijaba M11 respecto de
M9/M10).

**M13 — Optimización de consultas del motor por etapas y de la ampliación por categoría**

`StagedEnginePort.por_clave_exacta`/`por_prefijo_de_sujeto` en consulta por lote (§11.4,
punto 1); eliminar el segundo barrido completo del corpus de `solo_por_categoria` (§11.4,
punto 2), sustituyendo `list_current_memories()`/`list_current_decisions()` por una
consulta al puerto de persistencia filtrada por categoría, ejecutada en SQL, que devuelve
solo los candidatos de las categorías relevantes en vez de cargar el corpus completo en
memoria para filtrarlo en Python.

**Criterio de aceptación:** una prueba de integración con un doble instrumentado del
puerto (o un contador de consultas SQL reales sobre SQLite) confirma que el número de
consultas ejecutadas por `por_clave_exacta`/`por_prefijo_de_sujeto` para *n* claves/prefijos
deja de crecer linealmente con *n* (una consulta por lote, no dos por clave); una prueba
sobre `_rank_via_staged_engine` con un repositorio instrumentado confirma que la ampliación
por categoría deja de enumerar la totalidad del corpus — contando las filas que el
repositorio devuelve (o las filas que SQLite lee) para un corpus con muchos más elementos
fuera de la categoría solicitada que dentro, y comprobando que ese número depende del
tamaño del subconjunto que coincide con la categoría, no del tamaño total de recuerdos o
decisiones vigentes; contar solo las invocaciones a `list_current_memories()`/
`list_current_decisions()` no basta, porque ambas ya se invocan una sola vez por llamada a
`rank()` antes de este encargo y esa cuenta no cambiaría aunque el corpus completo se
siguiera enumerando. Ninguna prueba de identidad existente
(`tests/integration/test_rank_relevant_knowledge.py`,
`tests/acceptance/test_pa_0_2_rec_01_banco_evidencia.py`, el arnés de examen) cambia de
resultado — la optimización no puede alterar qué se admite ni en qué orden, solo cuántas
filas cuesta calcularlo.

**M14 — Índice de categoría buscable de activación múltiple, con restricción de ámbito, tras la puerta**

El índice de activación múltiple de §11.2 (paralelo a `category_matches_query`, que sigue
existiendo sin cambios para el estado-cerrado) y la restricción por ámbito, cableados
**solo** cuando `category_matching_enabled` es `True`, sustituyendo el bloque
`solo_por_categoria` actual de `_rank_via_staged_engine`
(`src/sirius/application/rank_relevant_knowledge.py:243-280`).

**Criterio de aceptación:** una prueba de dominio con candidatos de categorías distintas
confirma que una consulta que activa dos o más términos del vocabulario a la vez sí activa
la categoría para toda identidad no ordinaria cuando la puerta está abierta —a diferencia
de `category_matches_query`, que sigue exigiendo activación única y que otra prueba
confirma sin cambios—; una prueba de integración con dos proyectos distintos confirma que
un candidato de categoría no ordinaria en el proyecto B no se admite por categoría cuando
la petición declara ámbito del proyecto A, ni al revés, y que sí se admite cuando el
candidato es de ámbito global; con la puerta cerrada, una prueba de identidad confirma que
`_rank_via_staged_engine` produce exactamente el mismo resultado que antes de este
encargo, byte a byte sobre el mismo caso de prueba.

**M15 — Regla de críticas original (RF-25/RF-26) y siembra en contexto, tras la puerta**

RF-25/RF-26 sustituyendo el candado-unión de `ContextBuilder._apply_relevance_filter`
**solo** cuando la puerta está abierta (§11.2); G8/G12 sobre el conjunto combinado
motor+categoría antes de aplicar RF-25/RF-26 (§11.2, último punto).

**Precondición pendiente sobre la siembra en contexto — no forma parte de este encargo
todavía:** la definición aprobada documenta que `siembra_de_contexto` se escribió tras
observar fallos y que solo dos de los 47 casos del banco la ejercitan, por lo que se
confirma «por construcción», no de forma independiente
(`docs/evolution/SIRIUS_PRODUCTO_0.2_MEMORIA_UTIL_v0.1_PROPUESTO.md:100-106`); el plan de
pruebas fija como precondición de PA-0.2-REC-01, antes de poder declarar superada esa PA,
que se resuelva por una de dos vías excluyentes entre sí — el banco se amplíe con casos
independientes que ejerciten la siembra, o la siembra se retire del código —
(`docs/evolution/SIRIUS_PLAN_PRUEBAS_0.2_v0.1_PROPUESTO.md:124-131`). M15 **no** porta la
siembra a producción mientras esa precondición siga sin resolverse: construye únicamente
RF-25/RF-26 y G8/G12 sobre el conjunto motor+categoría (sin siembra). Las dos vías no
llevan al mismo destino: si el propietario amplía el banco, la precondición queda resuelta
dejando `siembra_de_contexto` como alcance de un encargo posterior, condicionado a que el
propietario registre esa reconsideración; si el propietario la retira del código, la
precondición queda resuelta cerrando esa alternativa — no dejándola abierta a un encargo
posterior, porque no quedaría siembra que portar. Este encargo no escoge por el
propietario cuál de las dos vías se sigue, igual que D3 (§6.6) deja aplazada la omisión
léxica hasta que se registre su propia decisión.

**Criterio de aceptación:** una prueba con un doble determinista de `RelevanceFilterPort`
que descarta explícitamente una identidad de categoría de máxima criticidad confirma que
se rescata cuando el filtro sí conservó algo de la misma consulta, y que **no** se rescata
cuando el filtro declaró ausencia total para esa consulta (RF-26); una prueba confirma que
un candidato sin categoría todavía sigue protegido siempre, sin condición, igual que hoy;
una prueba confirma que una identidad admitida por categoría, pero no vigente en el tiempo
objetivo de la petición, se descarta (G8) y que el conjunto combinado se trunca al límite
duro de la petición ordenando por criticidad (G12) antes de que RF-25/RF-26 actúe; con la
puerta cerrada, una prueba de identidad confirma que
`ContextBuilder._apply_relevance_filter` produce exactamente el mismo resultado que antes
de este encargo. Ninguna prueba de este encargo ejercita `siembra_de_contexto`: esa
cobertura queda pendiente del encargo posterior que resuelva la precondición de arriba.

**M16 — Petición de producción: ámbito real, propósito real, cableado en `ContextBuilder`/`RankRelevantKnowledgeUseCase`**

`_peticion_ordinaria` gana ámbito derivado del proyecto activo y propósito honesto de
ensamblar contexto (§11.3), sin tocar modo, cardinalidad ni límite (siguen fijos, §11.3).
Cablea M14/M15 en el punto de integración real.

**Criterio de aceptación:** una prueba confirma que, con un proyecto activo configurado,
la `Peticion` que `rank()` construye declara `Ambito(global_=False, proyectos=(id,))` con
el id de ese proyecto, y `Ambito(global_=True, proyectos=())` sin proyecto activo — mismo
criterio que ya usa `project_matches_active`; una prueba confirma que el `proposito`
declarado por toda llamada real activa `pide_contexto`, y que una petición construida sin
pasar por `ContextBuilder` (si alguna existe en la suite) no se ve afectada porque el
propósito lo fija `rank()` mismo, no el llamador; re-ejecutar la prueba de M7/M11 sobre el
banco con las piezas de M13-M16 integradas y reportar las cuatro métricas —sin exigir
todavía el suelo D1 completo, eso es M17—; volver a correr el benchmark de ADR-008/§6.4/§11.4
y publicar el P95 medido con las piezas ya integradas. **Esta re-ejecución es la primera
medición de las cuatro piezas de §11.2 sin la siembra en contexto**: ningún ADR previo
(ADR-113/114/115) midió esa combinación exacta —sus cifras de 29/47, 0 críticas y 63/81
incluyen siempre la siembra dentro del conjunto—, así que su resultado no está
predeterminado por evidencia ya publicada; M17 lo evalúa contra el suelo D1 tal cual salga.

**M17 — Medición final: cierre de la ola**

Sobre el pipeline con M13-M16 integrados, ejecutar las dos pruebas `xfail(strict=True)` de
M11 (`tests/acceptance/test_pa_0_2_rec_01_banco_evidencia.py:2135`,
`tests/integration/test_local_performance.py:631`) y comprobar su resultado. Además, sobre
esa misma ejecución del banco, M17 añade dos aserciones duras nuevas, también bajo
`xfail(strict=True)`, que hoy no existen sobre el camino real: `omisiones_criticas <= 1` y
`cobertura >= 63 / 81` (mismo suelo que ADR-115 ya blinda en el arnés, §11.0). Ninguna de
las dos figura como aserción dura en las dos pruebas de M11 (§11.0 lo señala
explícitamente: solo afirman `aciertos_exactos >= 29` y `P95 <= 300 ms`), pero sí forman
parte de las cifras que el objetivo de esta ola fija como destino, así que M17 no se limita
a registrarlas como evidencia adicional: las convierte en la misma clase de aserción dura y
aplazable que las otras dos, para que un resultado incompleto (por ejemplo, las dos XPASS
de M11 pero `omisiones_criticas > 1` o `cobertura < 63/81`) no pueda cerrar la ola.

**Criterio de aceptación — exactamente el que fija el objetivo de la incidencia #478:**
las cuatro pruebas `xfail(strict=True)` — las dos ya existentes de M11 y las dos que M17
añade — pasan inesperadamente (XPASS) y, por `strict=True`, la suite falla hasta que se
retiren sus cuatro marcas; al retirarlas todas (sustituyendo cada
`@pytest.mark.xfail(strict=True, reason=...)` por una aserción ordinaria, sin debilitar
ningún umbral que afirman), la suite completa queda en verde. Si M13-M16 no bastan para
alcanzar alguno de los cuatro suelos —el propio §11.4 ya advierte que optimizar las causas
conocidas no garantiza llegar a 300 ms; la Producción de M14/M15 podría no cerrar el 29/47
ni las otras dos métricas si la parte no cerrable de §11.3 resulta ser la causa dominante;
y, como registra §11.2 arriba, ninguna medición previa aísla las cuatro piezas portadas de
la siembra en contexto que queda fuera, así que 29/47, ≤1 crítica y 63/81 tampoco están
garantizados solo con esas cuatro piezas—, M17 no fuerza el verde: registra la cifra real alcanzada para cada una de las
cuatro métricas, actualiza este documento y `docs/evolution/STATUS.md` con el resultado, y
dejar en pie las marcas `xfail` que no hayan pasado es la única salida honesta,
exactamente como D3 (§6.6) ya deja abierta y aplazada la omisión léxica si M12 no la
cierra. La ola no se declara cerrada por decisión de M17 mismo, ni de forma parcial sobre
solo dos de las cuatro métricas: se declara cerrada cuando las cuatro pruebas lo digan, no
antes.

### 11.6 Qué no decide esta ampliación

Registrar el umbral de coincidencia exigible del etiquetado automático de Ollama (D7 punto
6, §6.3/§9 arriba) sigue siendo una decisión del propietario **distinta** y **anterior**
en el tiempo a que esta ola tenga ningún efecto real: `category_matching_enabled` sigue
siendo la misma clave única (§6.3), y esta ampliación no cambia cuándo ni cómo se activa
—sigue exigiendo que el propietario registre ese umbral en `STATUS.md` y que alguien fije
la clave a `True` en `settings.json`, dos pasos separados y explícitos, ninguno asignado a
M13-M17—. Lo que esta ola sí hace es asegurar que, el día que esa puerta se abra de
verdad sobre datos reales, el camino que se activa alcance las cifras que el arnés ya
demostró posibles, en vez de degradar a 4/47. Optimizar el motor por etapas más allá de lo
que M13 diagnostica (por ejemplo, paralelizar etapas, cachear resultados entre llamadas, o
rediseñar el motor por etapas mismo) queda fuera de esta ampliación si M17 mide que M13 no
basta: esa decisión, de ocurrir, es de una ola posterior, del propietario, exactamente como
ADR-117 ya lo dejó dicho para la disyuntiva de la que esta ola nace.
